# Ollama + OpenCode local model notes

Findings from testing pulse's `opencode` agent template (`ollama/<model>`) end to end
against a real local Ollama server, on this workstation. Kept as a reference for future
model/GPU changes; not part of the public docs since it's specific to this machine's
hardware and the state of Ollama/OpenCode as tested (2026-09-28).

**Hardware**: AMD Ryzen 9 5950X (16 cores / 32 threads), 128GB RAM, AMD Radeon RX 5700 XT
(Navi 10, gfx1010, 8GB VRAM). Ollama 0.21.2, OpenCode 1.18.33 (npm `opencode-ai`).

## 1. Does pulse ever call `ollama run`?

No. `pulse go`'s `opencode` template (`pulse/config.py`) only ever shells out to
`opencode run --auto --format json --model ollama/<model> {prompt}`. OpenCode itself talks to
Ollama's HTTP API (`ollama serve`, port 11434) — `ollama run` (the CLI) is never invoked
anywhere in this path. So there was no "run vs. serve" toggle to fix in pulse.

What pulse *didn't* do before this session: check whether that API was actually reachable
before claiming a build slot. Added a preflight (`config.ollama_up()` / `ollama_host()` /
`ollama_model()` in `pulse/config.py`, wired into `go.py`'s `_missing`/`_slots`): a template
naming an `ollama/...` model now claims nothing if the server doesn't answer at start,
same as a missing binary (F7.01), instead of failing deep inside a phase.

## 2. Wiring gaps between pulse, OpenCode, and Ollama

Two things had to be fixed before any of this could work at all, neither obvious from
pulse's own docs at the time:

- **OpenCode does not auto-detect a local Ollama server.** `--model ollama/<model>` fails
  with `ProviderModelNotFoundError` unless OpenCode's own config
  (`~/.config/opencode/opencode.jsonc`) registers a `provider.ollama` entry pointing at
  Ollama's OpenAI-compatible endpoint. See the final config in section 6.
- **Ollama's default context window (4096 tokens) truncates OpenCode's own prompt.**
  OpenCode's system prompt + full tool schema alone runs ~9,600–12,500 tokens before the
  actual task is added. At the default, `journalctl -u ollama` showed
  `truncating input prompt limit=4096 prompt=10432 ...` — truncation drops the tool
  definitions, so the model still answers, just as plain text describing a tool call
  instead of a structured one. Fixed with `OLLAMA_CONTEXT_LENGTH` (see section 4).

## 3. Model capability findings

Every model below was checked against pulse's actual `opencode` subprocess invocation
(`config.agent_argv` + `subprocess.Popen`, exactly as `pulse go` runs it), not just a
manual `ollama run` chat — reliability numbers are for the *real* pipeline.

| Model | Tool-calling in Ollama | Result under OpenCode's real ~10k-token prompt |
|---|---|---|
| `codellama:13b` | **No.** `/api/show` capabilities: `['completion']` only; its chat template (fetched from the registry) has no `{{.Tools}}`/`{{.ToolCalls}}` sections at all. | Fails immediately, no flag or prompt fixes this. |
| `qwen2.5-coder:7b` / `:14b` | Template *has* `{{.Tools}}`/`<tool_call>` tags, but the model reliably fails to wrap its own output in them. | **0/5** real tool calls, ever — confirmed even with a minimal 170-token raw prompt (bypassing OpenCode entirely). A deterministic model/template bug, not a prompt-size or timeout issue. `:14b` additionally never completed a single response on CPU even with a 30-minute timeout (see section 4). |
| `mistral:7b-instruct` | Yes — a raw 78-token test produced a perfect `tool_calls` response. | **0/3** under OpenCode's real prompt — reverts to plain-English narration ("First, let's create a file...") instead of ever attempting the tool-call format. Prompt-complexity/instruction-following limit, not a template bug. |
| `mistral-nemo:12b` | Yes, confirmed via raw test. | **3/11 (~27%)** across two batches. One success wrote to a wrong absolute path (`/tmp/...`); an explicit "use this exact relative path" instruction in the prompt fixed that specific quirk completely (2/2 correct after). Failures still just narrate instead of calling tools. |
| `llama3.1:8b-instruct-q4_K_M` | Yes — native JSON tool-call format (`{"name":...,"parameters":...}`), well known for reliable function-calling. | **8/8 (100%)** on an atomic task (write one file, run one git commit) — verified for real: all 8 files existed with correct content, all 8 git commits existed in order. **But** on an open-ended multi-step task ("build a full styled todo app in one shot") it made one real `write` call with only placeholder content, then hallucinated a **non-existent tool** ("html") and stalled without committing. Reliable tool-caller, insufficient coding depth/planning for a complex task in one pass. |

Ruled out as an explanation for the failures: **not context truncation, not timeout.**
Every failed run's `step-finish` showed `reason: "stop"` (voluntary end), never `"length"`
(would mean cut off), with tiny outputs (20–98 tokens) and thousands of tokens of free
context headroom remaining. Raising context/KV-cache further would not fix this — it's a
model instruction-following limitation under prompt complexity, confirmed by the fact that
`mistral:7b-instruct` was 100% reliable at a trivial 78-token prompt and 0% under the same
model at OpenCode's real ~10k-token one.

Also ruled out: **`ollama run --experimental`** (the flag that enables an "experimental
agent loop with tools" in the interactive CLI) is a client-side feature of `ollama run`
itself — it is not exposed through Ollama's HTTP API, which is what OpenCode actually
calls. It cannot retrofit tool-calling onto a model whose template doesn't support it.

**Conclusion for now: default to `llama3.1:8b-instruct-q4_K_M`** for anything built from
small, atomic steps. None of the tested models can be trusted with a large, open-ended,
single-prompt build.

## 4. GPU: ROCm is a dead end on this card, Vulkan is the fix

`ollama ps` showed every model running `100% CPU` even after everything above was fixed.
`journalctl -u ollama` explained why:

```
level=INFO msg="discovering available GPUs..."
level=INFO msg="failure during GPU discovery" ... error="runner crashed"
level=INFO msg="inference compute" id=cpu library=cpu ...
```

**Why**: the RX 5700 XT is RDNA1 (gfx1010). Checked against AMD's actual ROCm compatibility
matrix (not just assumed): ROCm's official GPU support goes from Vega/CDNA straight to
RDNA2 (gfx1030+, RX 6800/6900) — RDNA1 was never officially supported, at any ROCm version,
including now. That's a deliberate AMD product-support-tier decision (RDNA1 was
gaming-only, ROCm resources went to datacenter/CDNA), not an "experimental, coming later"
status that just never resolved. There's also a real ISA gap (RDNA1 lacks some
dot-product instructions RDNA2 has), which is why forcing
`HSA_OVERRIDE_GFX_VERSION=10.3.0` (pretend to be gfx1030) also silently failed in an
isolated test — a community patch project exists
([ROCm-RDNA1](https://github.com/TheTrustedComputer/ROCm-RDNA1)) but building/maintaining
a ROCm fork ourselves is a large undertaking, not attempted.

**The actual fix**: Ollama (since 0.12.6) ships a first-party **Vulkan** backend
(`OLLAMA_VULKAN=1`), using the Mesa **RADV** driver instead of ROCm/HIP. Vulkan is
vendor-agnostic — AMD's official support list is irrelevant — and RADV has had solid Navi10
support for years. The driver was already installed (`mesa-vulkan-drivers`,
`/usr/share/vulkan/icd.d/radeon_icd.x86_64.json`).

After enabling it:
```
inference compute: library=Vulkan name=Vulkan0 description="AMD Radeon RX 5700 XT (RADV NAVI10)" total="8.0 GiB"
```
GPU found immediately, ROCm's own discovery still crashes exactly as before (expected,
unrelated now — Vulkan doesn't touch that code path).

**First real inference crashed**: `free(): invalid pointer`, right as generation started,
with `flash_attn: auto, set to enabled` in the log. Flash attention on this
Vulkan/RDNA1 combination is unstable. Fixed with `OLLAMA_FLASH_ATTENTION=0`. After that:
clean, fast, correct GPU inference (`mistral:7b-instruct`: "Hello!" in 2.08s total,
`4%/96% CPU/GPU`; `qwen2.5-coder:7b`: `100% GPU`).

**Context vs. VRAM tension**: Ollama's own OpenCode integration docs
(docs.ollama.com/integrations/opencode) say OpenCode "requires a context length of 64k or
higher." Tried `OLLAMA_CONTEXT_LENGTH=65536` — `mistral-nemo:12b` then failed with
`ErrorOutOfDeviceMemory`: its KV cache alone needed 10.24GB, more than the whole 8GB card.
Tried quantized KV cache (`OLLAMA_KV_CACHE_TYPE=q8_0`) to shrink it — **it silently never
took effect**, because quantized KV cache requires flash attention, which we'd just
disabled. Deeper cause: *without* flash attention, the attention compute buffer scales
~quadratically with context length — at 65536 that alone needs ~8.4GB, independent of the
KV cache, and blows past 8GB regardless of model size or KV quantization.

**Pragmatic resolution**: dropped `OLLAMA_CONTEXT_LENGTH` back to **16384** — below
Ollama's general 64k recommendation, but empirically justified: every real OpenCode
prompt measured in this session was ~9,600–12,500 tokens, comfortably inside 16k with
thousands of tokens of headroom, and this keeps the compute buffer small enough to avoid
the OOM entirely. `OLLAMA_KV_CACHE_TYPE=q8_0` is left in the config (harmless, currently
inactive since flash attention is off — would only matter if flash attention gets
re-enabled and proven stable for a specific model).

Monitored GPU health closely with `radeontop` (already installed) across an 8-run batch:
300 one-second samples, GPU utilization 0–100% (avg 83.4%, 0% = idle gaps between runs),
VRAM rock-steady at 85.6–86.0% the entire time. No drift, no leak, no further crashes —
the Vulkan + no-flash-attention + 16k-context combination is stable.

**Also found and used, unrelated to the crash**: OpenCode's own timeout is configurable —
`provider.<name>.options.timeout` / `.headerTimeout` / `.chunkTimeout` (ms, default
300000 = 5 min, or `false` to disable), extracted directly from OpenCode's compiled config
schema. Raised to 1,800,000ms (30 min) while testing `qwen2.5-coder:14b`; it still never
completed a single response in 30 minutes on CPU — a genuine compute wall, not a timeout
artifact, and separately confirmed a dead end anyway (qwen-coder's tool-call template bug,
see section 3).

## 5. Final `/etc/systemd/system/ollama.service` state

```ini
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/home/darius/.local/bin:/home/darius/bin:/home/darius/.opencode/bin:/home/darius/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/darius/.local/share/JetBrains/Toolbox/scripts"
Environment="OLLAMA_CONTEXT_LENGTH=16384"
Environment="OLLAMA_VULKAN=1"
Environment="OLLAMA_FLASH_ATTENTION=0"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"

[Install]
WantedBy=default.target
```
Backups of each intermediate version are alongside it as `ollama.service.bak-*`.

## 6. Final `~/.config/opencode/opencode.jsonc` state

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://127.0.0.1:11434/v1",
        "timeout": 1800000,
        "headerTimeout": 1800000,
        "chunkTimeout": 1800000
      },
      "models": {
        "qwen2.5-coder:7b": { "name": "Qwen2.5 Coder 7B" },
        "qwen2.5-coder:14b": { "name": "Qwen2.5 Coder 14B" },
        "mistral:7b-instruct": { "name": "Mistral 7B Instruct" },
        "mistral-nemo:12b": { "name": "Mistral Nemo 12B" },
        "llama3.1:8b-instruct-q4_K_M": { "name": "Llama 3.1 8B Instruct" }
      }
    }
  }
}
```

Models pulled during this session (in addition to `mistral:latest`, `codellama:13b`,
`gemma4:latest` already present): `qwen2.5-coder:7b`, `qwen2.5-coder:14b`,
`mistral-nemo:12b`, `llama3.1:8b-instruct-q4_K_M`.

`pulse/config.py`'s `opencode` template now defaults to `ollama/llama3.1:8b-instruct-q4_K_M`
(updated after this doc's findings, section 3) — the most tool-call-reliable local model
found, not the best coder. Fine for atomic steps; not trusted yet for a full feature
build in one shot (see section 7).

## 7. Open question / next task

Plan: split pulse's build phase across two tiers — Sonnet (Claude) does planning
(writing PLAN/`task.md` files), a local Ollama model via `opencode` executes the narrowed-
down, atomic implementation steps. This matches what was actually proven to work here:
`llama3.1:8b-instruct` is 100% reliable at a single, clearly-scoped tool call, but falls
apart on an open-ended multi-part task in one prompt. For this split to work, each
`task.md` step needs to be as atomic as the "write one file, run one git command" tests
above — not a whole feature in one shot.

Still open: no code-specialized model has been found yet that is *also* reliably
tool-call-compliant and fits the 8GB VRAM budget. `qwen2.5-coder` (7b and 14b) is a
confirmed dead end regardless of size — the tool-call formatting bug reproduces even on a
minimal prompt, so bigger quantizations won't fix it. Worth trying next, in order of
likely fit: `codestral` (Mistral's code model, check tool-call template before pulling),
or a Qwen2.5 **general-instruct** (non-coder) variant at 7B–14B, since only the
coder-tuned variant showed the template bug — the base instruct model uses a different
training recipe and may not share it. Verify any candidate the same way this session did:
fetch its manifest + template from `registry.ollama.ai` before pulling, confirm
`{{.Tools}}`/`{{.ToolCalls}}` presence, then run the raw-curl minimal test before ever
routing it through OpenCode.

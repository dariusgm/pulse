#!/usr/bin/env python3
"""Pulse hook: one entry for every hook event.

  session-start, subagent-start   inject the rules plus the active item
  stop                            nudge once when code changed but no check ran,
                                  or a PR's last commit has no review
  presence                        record the event for the live map, and keep
                                  the heartbeat of held items (async)

Every event of an active project also lands in the presence log.

A hook must never break a session: any failure is swallowed and the hook
prints nothing. The active item comes from the issue cache that the pulse
CLI keeps (state.cache_path). Four paths reach GitHub through gh: the stop
verdict, where review.last reads the verdicts on the item's PR when this
clone keeps none and asks once per author of one whether they may push,
the heartbeat on a tool event, at most every 10
minutes per session and in the background, the stop verdict for a PR or
unpushed commits, one read of the item within 2 s for who holds it, and a
session start on an item the board cache lacks, one read within 2 s.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from pulse import config, dispatch, go, presence, ready, review, setup, state  # noqa: E402

PARALLEL = {
    "off": "Parallel: off (.pulse/config.toml). Work on one item at a time.",
    "items": ("Parallel: items (.pulse/config.toml). Independent ready items run side by side "
              "through `pulse go`, each in its own worktree; inside one item, work task by task."),
    "max": ("Parallel: max (.pulse/config.toml). Never do independent work one after another. "
            "Items: `pulse go`. Inside a PLAN: run each task wave (same wave = disjoint files) as "
            "parallel subagents, then run the wave's checks before the next wave. Plan dependencies "
            "contract-first so dependents start on the interface; a dependent that needs unmerged "
            "code stacks on its blocker's branch once the blocker's PR is ready."),
}
EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
PATCHED = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", re.M)
PROSE = re.compile(r"(\.(md|mdx|txt|rst|adoc)$)|(^|/)(docs|_devprocess)/")
CHECK = presence.CHECK
BEAT = 10 * 60                 # seconds between two heartbeats of one session (D-43)


def platform(env):
    if env.get("CURSOR_PLUGIN_ROOT") or env.get("CURSOR_VERSION"):
        return "cursor"
    if env.get("COPILOT_CLI") or env.get("COPILOT_PLUGIN_DATA"):
        return "copilot"
    return "claude"            # Claude Code and Codex share the nested form


def emit(event, text, env):
    kind = platform(env)
    if kind == "cursor":
        return json.dumps({"additional_context": text})
    if kind == "copilot":
        return json.dumps({"additionalContext": text}) if event == "SessionStart" else ""
    return json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def quick(args):
    """gh within 2 s: a hook never waits long for GitHub. state.gh is looked up per call, so tests can swap it."""
    return state.gh(args, timeout=2)


def active_item(root):
    """The item of the checked-out branch, from the board cache, else from one read of it (a lost beat drops the
    cache); and who holds it when another login does (#99 FR-06)."""
    try:
        branch = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""
    n = state.item_of(branch)          # feat/, imp/, fix/: a docs/12-x branch is no item's
    if not n:
        return ""
    item, held = {}, ""
    try:
        item = next((i for i in state.cached(root) if i.get("number") == n), None)
        if item is None:
            v = json.loads(quick(["issue", "view", str(n), "--repo", state.repo(root, quick),
                                  "--json", "title,body,assignees"]))
            spec = state.SPEC.search(v.get("body") or "")
            item = {"title": v["title"], "assignees": [a["login"] for a in v["assignees"]],
                    "spec": spec.group(1) if spec else None}
        who = item.get("assignees") or []
        held = "" if not who or state.me(root, run=cached_only) in who else ", ".join(who)
    except (OSError, subprocess.TimeoutExpired, state.StateError, ValueError, KeyError, TypeError):
        item = item or {}
    line = f"Active item: #{n} {ready.printable(item.get('title') or '')}".rstrip() + f" (branch {branch})."
    if item.get("spec"):
        line += f" Spec: {ready.printable(item['spec'])}."
    if held:
        line += f" It is held by {ready.printable(held)}: work on it only when the person says so."
    return line + f" Details: `pulse show {n}`."


def context(event, root, cfg, env):
    if cfg["mode"] == "off":
        return ""
    if cfg["mode"] is None:
        if event != "SessionStart":
            return ""
        return ("Pulse is installed but not active in this project. `/pulse-setup` "
                "(in Codex `$pulse:pulse-setup`) activates it.")
    own = ROOT / "bin" / "pulse"
    # Claude Code runs its hooks with CLAUDECODE=1 and appends this plugin's bin/ to its Bash tool's PATH,
    # so there `pulse` is this plugin's unless another one comes first on PATH.
    # ponytail: a Codex started from that Bash tool inherits both, so its `pulse` is Claude Code's copy,
    # maybe of another version; compare the versions as shim_runs does if that ever bites
    found = shutil.which("pulse", path=env.get("PATH"))
    claude_code = env.get("CLAUDECODE") == "1" and Path(env.get("CLAUDE_PLUGIN_ROOT") or "/").resolve() == ROOT \
        and (not found or Path(found).resolve() == own)
    cli = ("Pulse CLI: `pulse`." if claude_code or setup.shim_runs(ROOT, env) else
           f"Pulse CLI: `{own}`. Wherever these rules or a Pulse skill say `pulse`, run that path.")
    parts = [(HERE / "rules.md").read_text(encoding="utf-8").strip(), PARALLEL[cfg["parallel"]], cli]
    item = active_item(root)
    if item:
        parts.append(item)
    if event == "SessionStart":
        idle = idle_capacity(root, cfg)
        if idle:
            parts.append(idle)
        stale = stale_anchors(root, cfg["mode"])
        if stale:
            parts.append(f"The Pulse block in {', '.join(stale)} is out of date. Run `pulse setup --anchors` "
                         "yourself: it does to the block what `/pulse-setup` (in Codex `$pulse:pulse-setup`) does, "
                         "without questions, and changes nothing else. Take the change into your next commit "
                         "and tell the user.")
        news = release_note(root, env)
        if news:
            parts.append(news)
    return "\n\n".join(parts)


def release_note(root, env):
    """A newer Pulse the live map found (IMP-14), with the update for this session's agent; '' else.
    It reads the map's answer only: a session start asks no network."""
    try:
        found = (state.cache_dir(root) / "latest").read_text(encoding="utf-8").strip()
        own = setup._version(ROOT)
    except (OSError, ValueError, KeyError):
        return ""
    if setup.version_key(found) <= setup.version_key(own):
        return ""
    how = ("with auto-update on, Claude Code brings it by itself (/plugin, Marketplaces); else claude plugin "
           "marketplace update pssah4-skills, then claude plugin update pulse@pssah4-skills; then /reload-plugins "
           "or a new session" if env.get("CLAUDECODE") == "1" else
           "codex plugin marketplace upgrade pssah4-skills, then codex plugin add pulse@pssah4-skills; then a "
           "new chat, and trust the Pulse hooks again when Codex asks")
    return f"Pulse {found} is out; this session runs {own}. Tell the user: {how}."


def stale_anchors(root, mode):
    """The agent files whose Pulse block differs from the one pulse setup writes now (IMP-10): a
    project set up before the text changed keeps its old block until setup runs again."""
    out = []
    for t in setup.TARGETS:
        try:
            m = t.block_re(setup.MARKERS).search((root / t.path).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if m and m.group(0).rstrip("\n") != setup.anchor_block(t, mode).rstrip("\n"):
            out.append(t.path)
    return out


def codex_uses(call):
    """A tool call from a Codex rollout as Claude tool uses: apply_patch edits each file its
    patch names, exec_command (or shell) runs a command."""
    try:
        args = json.loads(call["arguments"]) if call["type"] == "function_call" else {"input": call["input"]}
    except (KeyError, TypeError, ValueError):
        return []
    if call.get("name") == "apply_patch":
        return [{"name": "Edit", "input": {"file_path": f.strip()}} for f in PATCHED.findall(args.get("input", ""))]
    cmd = args.get("cmd") or args.get("command")
    return [{"name": "Bash", "input": {"command": " ".join(cmd) if isinstance(cmd, list) else cmd}}] if cmd else []


def read_transcript(path):
    """Parse a Claude Code transcript or Codex rollout once into its JSON lines: broken lines
    are skipped, an unreadable file yields no entries."""
    try:
        raw_lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for raw in raw_lines:
        try:
            entries.append(json.loads(raw))
        except ValueError:
            continue
    return entries


def failed_tool_uses(entries):
    """The tool_use ids whose result anywhere in the transcript is an error."""
    failed = set()
    for entry in entries:
        content = entry.get("message", {}).get("content")
        if isinstance(content, list):
            failed |= {p.get("tool_use_id") for p in content if isinstance(p, dict) and p.get("is_error")}
    return failed


def last_turn_tools(entries):
    """Tool uses since the last real user prompt (tool results do not count), from a Claude Code
    transcript or a Codex rollout."""
    uses = []
    for entry in entries:
        if entry.get("type") == "response_item":            # Codex
            item = entry.get("payload") or {}
            if item.get("type") == "message" and item.get("role") == "user":
                uses = []
            elif item.get("type") in ("function_call", "custom_tool_call"):
                uses += codex_uses(item)
            continue
        content = entry.get("message", {}).get("content")
        if entry.get("type") == "user" and (isinstance(content, str) or any(
                isinstance(p, dict) and p.get("type") == "text" for p in content or [])):
            uses = []
        elif entry.get("type") == "assistant" and isinstance(content, list):
            uses += [p for p in content if isinstance(p, dict) and p.get("type") == "tool_use"]
    return uses


def cached_only(args):
    """gh for state.me in the stop verdict: the login comes from its cache or not at all."""
    raise state.StateError("no cached login")


def idle_capacity(root, cfg):
    """At parallel = max, ready work with free slots must not wait for the next prompt."""
    if cfg["parallel"] != "max" or go.running(root):
        return ""
    try:
        login = state.me(root, run=cached_only)
    except state.StateError:
        return ""              # without a cached login the slots are unknown; never guess
    r = dispatch.view(root, state.cached(root), {**cfg, "parallel": "max"}, login)
    if not r["next"]:
        return ""
    names = ", ".join(f"#{i['number']}" for i in r["next"])
    return (f"Pulse runs at parallel = max: {names} {'is' if len(r['next']) == 1 else 'are'} ready "
            f"and {r['free']} slot{'s' if r['free'] != 1 else ''} free. Start them with `pulse go` "
            "(or as parallel subagents), or say in one sentence why not.")


def held_here(root, n, payload, memo):
    """Whether this session holds n as the board says now: its login is assigned and no mark stands before its
    own (state._lead); None when the read fails or no login is cached. One read of the item within 2 s per stop,
    shared by its reasons, and never the board cache, which names the old holder after a take until a heartbeat
    drops it (#99 FR-01, FR-02)."""
    if n not in memo:
        who = {"id": f"{'codex' if 'turn_id' in payload else 'claude'}:{payload.get('session_id') or ''}"}
        try:
            v = json.loads(quick(["issue", "view", str(n), "--repo", state.repo(root, quick),
                                  "--json", "assignees,comments"]))
            memo[n] = state.me(root, run=cached_only) in [a["login"] for a in v["assignees"]] and \
                not state._lead(v, who)[1]
        except (OSError, subprocess.TimeoutExpired, state.StateError, ValueError, KeyError, TypeError):
            memo[n] = None
    return memo[n]


def unreviewed_pr(root, payload, entries, memo=None):
    """A pull request is ready only with a review and a security audit of its last commit
    (ADR-05). The cache may not know a PR opened this turn yet, so `gh pr create` in this
    turn counts too, unless its tool result is an error (denied, or gh failed). Only while this
    session holds the item: its verdicts would land on the PR of whoever took it (#99 FR-02); a
    read that fails asks as before."""
    if payload.get("agent_id"):
        return ""
    try:
        branch, head = [subprocess.run(["git", "-C", str(root), "rev-parse", *a], capture_output=True,
                                       text=True, timeout=2).stdout.strip()
                        for a in (["--abbrev-ref", "HEAD"], ["HEAD"])]
    except (OSError, subprocess.TimeoutExpired):
        return ""
    n = state.item_of(branch)
    if not n:
        return ""
    item = next((i for i in state.cached(root) if i.get("number") == n), {})
    creates = [u for u in last_turn_tools(entries)
               if u.get("name") == "Bash" and "gh pr create" in u["input"].get("command", "")]
    failed = failed_tool_uses(entries) if creates else set()
    opened = any(u.get("id") not in failed for u in creates)
    if not (item.get("pr") or opened) or held_here(root, n, payload, {} if memo is None else memo) is False:
        return ""
    known = {}                 # what GitHub said of the authors of markers, for both gates (#74)
    missing = [k for k in ("review", "audit") if (review.last(root, n, k, known) or {}).get("commit") != head]
    if not missing:
        return ""
    why = next((v for v in known.values() if isinstance(v, str)), "")
    how = "; ".join(f"`pulse {k} {n} --run`, or a subagent with the brief from `pulse {k} {n}`, "
                    f"then `pulse {k} {n} --record`" for k in missing)
    gates = f"{'them' if len(missing) > 1 else 'it'} in a fresh session ({how}); the PR stays draft until both pass."
    if not why:
        return f"Pulse: #{n} has a pull request, but its last commit has no {' and no '.join(missing)}. Run {gates}"
    return (f"Pulse: #{n} has a pull request, but its last commit has no {' and no '.join(missing)} that counts: "
            f"Pulse could not check who posted the verdicts on the PR ({ready.printable(why)}). First check that gh "
            "uses your account that can push to the repository (`gh auth status`; `gh auth switch` changes it), or "
            "wait until GitHub's rate limit resets. If you cannot push, ask for write access, or leave the gates to "
            f"someone who can. Otherwise run {gates}")        # as the troubleshooting page says (#74)


def untested_code(entries):
    uses, failed = last_turn_tools(entries), failed_tool_uses(entries)     # a refused edit changed nothing
    edited = sorted({u["input"].get("file_path") or u["input"].get("notebook_path") or ""
                     for u in uses if u.get("name") in EDIT_TOOLS and u.get("id") not in failed} - {""})
    code = [f for f in edited if not PROSE.search(f)]
    checked = any(u.get("name") == "Bash" and CHECK.search(u["input"].get("command", ""))
                  for u in uses)
    if not code or checked:
        return ""
    shown = ", ".join(code[:3]) + (f" and {len(code) - 3} more" if len(code) > 3 else "")
    return (f"Pulse: code changed this turn ({shown}) but no test or build ran. "
            "Run the smallest check that can disprove the change, "
            "or say in one sentence why none applies.")


def heartbeat(root, payload, env):
    """A session that holds an item keeps a sign of life on the board: on a tool event, at most every
    BEAT seconds (a stamp per session in the shared git dir), its claim marks name the phase `working`
    and the time; a draft keeps its phase, analysis or spec. pulse go beats for its own sessions.
    An item whose older mark is another session's now is lost (#77), and so is one a person took with
    pulse release --take since this session's last beat or claim held it: a note beside the stamp keeps
    what each beat held, and an item gone from it is read once (#84). The news waits beside the stamp
    for lost_news; a beat that finds a loss drops the board cache, so the stop hook asks for no push."""
    sid = str(payload.get("session_id") or "")
    if not (sid and payload.get("tool_name")) or env.get("PULSE_HOLDER"):
        return
    stamp = state.stamp(root, sid)
    try:
        if time.time() - stamp.stat().st_mtime < BEAT:
            return
    except OSError:
        stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.touch()              # before gh: a round that fails waits its ten minutes too
    gh = state.gh              # looked up per call so tests can swap it
    # ponytail: a Codex session is its hook's session_id, taken to be CODEX_THREAD_ID (the docs show
    # thread ids there); if they differ, its claims get no heartbeat. Each session leaves its stamp and
    # notes behind; SessionEnd could take them along if they ever pile up.
    who = {"id": f"{'codex' if 'turn_id' in payload else 'claude'}:{sid}"}
    was = state.held(root, who)
    had, at = set(was.get("items", [])), state._utc(state.SKEW)      # at: before the reads, a take after them is younger
    repo, login = state.repo(root, gh), state.me(root, gh)
    lost, now = {}, []
    for i in state.cached(root) or state.load(root, repo, run=gh):
        n = i["number"]
        if login not in (i.get("assignees") or []):
            continue
        if state.beat(root, repo, n, (i.get("draft") and i.get("claimed_phase")) or "working", run=gh, who=who):
            now.append(n)
            continue
        by = state.holds(repo, n, run=gh, who=who)[1]
        if by:                 # another session of my login goes on; another person's claim is freed by mine
            back = "" if i.get("claimed_by") == login else f", give it back with `pulse release {n}`"
            lost[n] = (state.LOST.format(n) + f"{by} holds it, with the older claim. "
                       f"Stop the work on #{n}, push nothing of it{back}, and tell the person.")
    for n in sorted(had - set(now) - set(lost)):              # given back, or taken
        try:
            by = state.taken(state._view(repo, n, gh), login, was["at"])
        except (state.StateError, ValueError):               # deleted since, or gh failed: the others go on
            continue
        if by:
            lost[n] = (state.LOST.format(n) + f"it was handed over with `pulse release --take {n}` "
                       f"and went to {by}. Stop the work on #{n}, push nothing of it, and tell the person.")
    if lost:                   # first: a note that cannot be written costs no news
        state.drop_cache(root)                               # the stop hook reads the board as it is now
        news = state.stamp(root, sid, ".lost")               # news waits until heard, each line once
        state.keep_note(news, "\n".join(dict.fromkeys([*state.read_note(news).splitlines(), *lost.values()])))
    kept = set(state.held(root, who).get("items", []))       # what a claim or release of this session changed meanwhile
    state.keep_held(root, who, at, (set(now) - (had - kept)) | (kept - had))


def lost_news(root, payload, env):
    """What the heartbeat found lost, said on the next event whose context reaches the session: a
    prompt, and for Claude Code a tool result too (Codex takes it on a prompt only). The next heartbeat
    finds it again while the session holds its mark behind another. The note reaches the session as
    printable text only (#84 audit)."""
    event = payload.get("hook_event_name")
    if event != "UserPromptSubmit" and not (event == "PostToolUse" and "turn_id" not in payload):
        return ""
    lost = state.stamp(root, str(payload.get("session_id") or ""), ".lost")
    text = "\n".join(map(ready.printable, state.read_note(lost).splitlines())).strip()
    out = emit(event, text, env) if text else ""
    if out or not text:        # a platform that shows no context here keeps the note
        try:
            lost.unlink()
        except OSError:
            pass
    return out


def unpushed_work(root, cfg, payload, memo=None):
    """Commits on the checked-out branch of an item this login holds, or its docs branch, that origin
    lacks: the session pushes before it ends, so the team sees the work and whoever takes the item
    over starts from it (#79). Local first; only then the holder, from one read of the item within 2 s
    (held_here), so a slow gh never costs this stop its other reasons and a read that fails asks for
    nothing. A session whose item an older claim holds, or a person took, pushes nothing (#77, #99 FR-01).
    A branch name is quoted as a shell reads it (#79 audit L-1)."""
    if payload.get("agent_id"):
        return ""
    try:
        branch = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=2).stdout.strip()
        docs = re.match(r"docs/(\d+)-", branch)
        n = state.item_of(branch) or (int(docs.group(1)) if docs else None)
        kept = n and [k for b, k in ready.unpushed(root, n, cfg["base_branch"] or config.default_branch(root))
                      if b == branch]
    except (OSError, subprocess.TimeoutExpired, state.StateError, ValueError):
        return ""
    if not kept or not held_here(root, n, payload, {} if memo is None else memo):
        return ""
    return (f"Pulse: {branch} has {kept[0]} commit{'s' if kept[0] != 1 else ''} only this clone has. Push "
            f"before you end: `git push -u origin {shlex.quote(branch)}`; the team sees the work on #{n}, and "
            "whoever takes it over starts from it.")


def stop_verdict(root, cfg, payload, env):
    """The reasons to go on before a session ends. The first call of gh is the one read of who holds the item
    (held_here), and after a take it answers alone: no verdict is read (#99 fix round 1). A session that holds
    an item with a PR needs up to four calls of gh; hooks.json gives the Stop hook 10 s for them."""
    # PULSE_HOLDER: an agent or gate session of pulse go, which runs the gates itself
    if platform(env) != "claude" or payload.get("stop_hook_active") or env.get("PULSE_HOLDER"):
        return ""
    path = payload.get("transcript_path")
    entries = read_transcript(path) if path else []
    memo = {}                  # who holds the item: one read for both reasons
    reasons = [r for r in (untested_code(entries), unreviewed_pr(root, payload, entries, memo),
                           unpushed_work(root, cfg, payload, memo)) if r]
    return json.dumps({"decision": "block", "reason": " ".join(reasons)}) if reasons else ""


def main(argv, stdin_text, env):
    try:
        event = {"session-start": "SessionStart", "subagent-start": "SubagentStart",
                 "stop": "Stop", "presence": "presence"}.get(argv[0] if argv else "")
        root = config.find_root()
        if not event or root is None:
            return ""
        cfg = config.load(root)
        if cfg["source"] is None and (root / ".git").is_file():      # a worktree follows its main copy
            cfg = config.load(config.common_dir(root).parent)
        if cfg["mode"] == "on" and stdin_text.strip():
            try:
                presence.record(root, json.loads(stdin_text))
            except (ValueError, OSError, AttributeError):
                pass
        if event == "presence":
            if cfg["mode"] != "on":
                return ""
            payload = json.loads(stdin_text)
            try:
                heartbeat(root, payload, env)
            except Exception:  # a beat that failed (gh, a note it cannot write) keeps no news from the session
                pass
            return lost_news(root, payload, env)
        if event == "Stop":
            return stop_verdict(root, cfg, json.loads(stdin_text), env) if cfg["mode"] == "on" else ""
        text = context(event, root, cfg, env)
        return emit(event, text, env) if text else ""
    except Exception:          # a hook must never break the session
        return ""


if __name__ == "__main__":
    out = main(sys.argv[1:], sys.stdin.read() if not sys.stdin.isatty() else "", dict(os.environ))
    if out:
        sys.stdout.write(out)

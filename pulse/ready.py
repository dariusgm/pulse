"""Readiness: which items may be planned, which may be built, and why the others wait.

An item is ready when a person approved it, its spec passes R1 to R6
(pulse/spec.py), it has a PLAN that passes P1 to P5, the PLAN is approved,
and no blocker is open. The PLAN approval is computed: `plan_approval =
"auto"` approves every PLAN that nothing holds (a risk flag in the spec,
`needs:` in the PLAN); `manual`, or a hold, waits for `pulse approve-plan`.

PLANs live in the working tree (interactive /pulse-plan) or on the pushed
item branch (planning runs of pulse go); fetch() brings the item branches
of every clone. The rules read text only; plans() and gates() read git.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from pulse import config, spec, state

FETCH_EVERY = 30                     # seconds between two fetches of one clone, whoever asks
GIT_TIMEOUT = 60                     # seconds for git over the network, as for gh
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}   # a password prompt fails at once
PLANS = "_devprocess/plans"
IDS = re.compile(r"\b(?:FR|SC)-\d+\b")
TICK = re.compile(r"`([^`\s]+)`")
CODE = re.compile(r"`[^`\n]*`")         # inline code: braces there are code, not a placeholder
REF = re.compile(r"#(\d+)(?=[\s,:;]|$)")  # a needs: entry that names an item first
NO_MERGE = "no merge"                # what approve spec binds when its confirmation showed no merge (#88)
SEVERAL = "branches {} of origin changed its spec since {} took it: keep the correction on one of them, push, and " \
          "approve again"            # a spec on the base with more than one newer version (#99 FR-07)
SAID = re.compile(r"^(?=(?:error|fatal|warning|hint):)", re.M)     # where each message of git starts
HEADS = re.compile(r"^([0-9a-f]{40}(?:[0-9a-f]{24})?)\trefs/heads/(.+)$", re.M)   # a line git ls-remote writes
_memo: dict = {}                     # (branch sha, base ref) -> its PLAN; git history never changes
_specs: dict = {}                    # (base sha, path) -> the spec text there, or None


def _git(root: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout      # one bad byte in a PLAN stops nothing


def net_git(cwd, *args) -> subprocess.CompletedProcess:
    """git over the network: no prompt, no terminal, stdin closed, and a time limit that ends git with
    everything it started (ssh, a remote helper). A run out of time reads as a failure."""
    with subprocess.Popen(["git", "-C", str(cwd), *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, errors="replace", env={**os.environ, **NO_PROMPT},
                          start_new_session=True) as p:
        try:
            out, err = p.communicate(timeout=GIT_TIMEOUT)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = "", f"no answer within {GIT_TIMEOUT} s"
    return subprocess.CompletedProcess(p.args, p.returncode, out, err)


def fetch(root: Path, now=False):
    """Every branch on origin, and none it dropped, so this clone sees what the others planned
    and hold (D-10); at most every FETCH_EVERY seconds per clone, or `now` whatever the last one
    was: before an ID is handed out or a claim names its start point (#78). True when the fetch went
    through, this one or the last; False when it failed, and the stamp keeps `offline` and what git
    said for every command (#85); None without a place to note the fetch (a read-only .git), where no
    fetch runs. Silent, and nothing waits long."""
    stamp = config.pulse_dir(root) / "fetched"
    try:
        if not now and time.time() - stamp.stat().st_mtime < FETCH_EVERY:
            return stamp.read_text(encoding="utf-8").partition("\n")[0] != "offline"
    except OSError:
        pass
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        was = stamp.stat().st_mtime if now and stamp.exists() else 0
        stamp.touch()
    except OSError:
        return None            # no fetch rather than one per call
    got = net_git(root, "fetch", "-q", "--prune", "origin")
    answered = got.returncode == 0
    said = git_error(got.stderr) if got.returncode > 0 else ""    # killed at the time limit: git said nothing
    try:
        stamp.write_text("" if answered else f"offline\n{said}", encoding="utf-8")
        if now:                # a fetch of its own: the map and the others keep their pace (#78 E2E m1)
            os.utime(stamp, (was, was))
    except OSError:
        pass
    return answered


def git_error(text: str) -> str:
    """git's error: and fatal: messages with the lines they wrap onto, on one line fit for a terminal;
    all of it from a git that speaks another language (#85)."""
    parts = [p for p in SAID.split(text) if p.startswith(("error:", "fatal:"))]
    return printable(" ".join(" ".join(parts or [text]).split()))


def fetch_said(root) -> str:
    """What git said at the last fetch of this clone, as its stamp keeps it for every command: "" after
    a fetch that went through, or one the time limit ended, where git said nothing (#85)."""
    try:
        return (config.pulse_dir(root) / "fetched").read_text(encoding="utf-8").partition("\n")[2]
    except (OSError, state.StateError):
        return ""


def behind(root) -> dict | None:
    """{branch: the commit origin names} for each branch whose refs/remotes/origin/<branch> git lists here
    on another commit, and {branch: ""} for a listed ref whose branch origin no longer has: what a fetch
    git could not finish leaves, or one that wrote a ref on the commit of a name that differs only in case.
    It reads the list, so it misses a name that resolves elsewhere while the list matches origin (a twin
    loose beside a packed origin/main): a follow-up item's. None when git ls-remote fails, as offline.
    Only lines of a commit and a branch count: a name with a newline forges no revision (#85)."""
    heads = net_git(root, "ls-remote", "--heads", "origin")
    if heads.returncode:
        return None
    there = {b: c for c, b in HEADS.findall(heads.stdout)}
    here = {b: c for b, c, link in (line.split(" ") for line in _git(      # "\n" only: a ref name may hold U+2028
        root, "for-each-ref", "--format=%(refname:lstrip=3) %(objectname) %(symref)", "refs/remotes/origin"
    ).split("\n") if line) if not link}                            # origin/HEAD names a branch, it is none
    return {b: c for b, c in there.items() if here.get(b) != c} | {b: "" for b in here if b not in there}


def listed(text: str, key: str) -> list:
    """A block list (`key:` then `  - item` lines) or an inline list from the frontmatter."""
    out, on = [], False
    for line in spec.split(text)[0]:
        if re.match(rf"^{re.escape(key)}:\s*(?:#.*)?$", line):      # a comment may follow, as in the template
            on = True
            continue
        if on and re.match(r"^\s+-", line):
            out.append(re.sub(r"\s#.*", "", line.split("-", 1)[1]).strip().strip("'\""))    # \s, not \s+: linear
            continue
        on = False
    inline = spec.front(text).get(key)
    return [x for x in out + (inline if isinstance(inline, list) else []) if x]


def _issue(text: str):
    n = str(spec.front(text).get("issue", "")).lstrip("#")
    return int(n) if n.isdigit() else None


def _branch_plan(root: Path, base: str, ref: str, n: int):
    """The PLAN of #n on its pushed branch: a Markdown file in the plans folder itself, as in the
    working tree; the map opens it with the system's app (audit of #55)."""
    for path in _git(root, "diff", "-z", "--name-only", "--diff-filter=AM", f"{base}...{ref}", "--",
                     f":(glob){PLANS}/*.md").split("\0"):
        if Path(path).parent.as_posix() != PLANS or not path.endswith(".md"):   # a space splits nothing now
            continue
        text = _git(root, "show", f"{ref}:{path}")
        if _issue(text) == n:
            return {"path": path, "ref": ref, "text": text}
    return None


def plans(root: Path, base: str = None) -> dict:
    """{issue: {"path", "ref", "text"}}: pushed item branches, then the working tree, which wins
    unless the item's branch on origin moved past it: the copy here is committed as it is, and
    that branch holds this commit and a different PLAN."""
    base = base or config.base_ref(root)
    out = {}
    for line in _git(root, "for-each-ref", "--format=%(objectname) %(refname:short)",
                     "refs/remotes/origin").splitlines():
        sha, _, ref = line.partition(" ")
        n = state.item_of(ref.removeprefix("origin/"))
        if n:
            key = (sha, base)
            if key not in _memo:
                _memo[key] = _branch_plan(root, base, ref, n)
            if _memo[key]:
                out[n] = _memo[key]
    for path in sorted((root / PLANS).glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        n, rel = _issue(text), path.relative_to(root).as_posix()
        p = out.get(n)
        behind = p and p["ref"] and p["text"] != text and not _git(root, "status", "--porcelain", "--", rel) \
            and _git(root, "rev-list", "--count", f"{p['ref']}..HEAD").strip() == "0"
        if n and not behind:   # behind: a teammate pushed a newer PLAN on the item's branch
            out[n] = {"path": rel, "ref": None, "text": text}
    return out


def tasks(text: str) -> list:
    """The rows of the Tasks table as dicts keyed by the lower-cased header."""
    rows = [[c.strip() for c in l.strip().strip("|").split("|")]
            for l in spec.sections(text).get("tasks", "").splitlines() if l.strip().startswith("|")]
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:] if not set("".join(r)) <= set("-: ")]


def wave_clashes(text: str) -> list:
    """[(line, message)] for files touched twice in one wave of a Tasks table."""
    out, cols, seen = [], None, {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            cols = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if "files" in low and "wave" in low:
            cols, seen = (low.index("files"), low.index("wave")), {}
            continue
        if cols is None or not line.replace("|", "").replace("-", "").replace(":", "").strip():
            continue
        files_at, wave_at = cols
        if max(cols) >= len(cells):
            continue
        wave = seen.setdefault(cells[wave_at], {})
        for m in TICK.finditer(cells[files_at]):
            f = m.group(1)
            if f in wave:
                out.append((n, f"wave {cells[wave_at]}: {f} is also touched on line {wave[f]}; "
                               "tasks in one wave need disjoint files"))
            else:
                wave[f] = n
    return out


def _ids(spec_text: str) -> list:
    sec = spec.sections(spec_text)
    frs = [m.group(1) for content in sec.values() for m in spec.REQ.finditer(content)]
    scs = [row[0] for row in spec._rows(sec.get("success criteria", "")) if re.match(r"SC-\d+$", row[0])]
    return frs + scs


def plan_findings(text: str, spec_text) -> list:
    """['P2 not covered: SC-01', ...]; [] means an agent can build from this PLAN."""
    fm, rows, out = spec.front(text), tasks(text), []
    missing = [k for k in ("issue", "spec") if not fm.get(k)] + \
              [k for k in ("files", "verify") if not listed(text, k)]
    if missing:
        out.append(f"P1 missing in frontmatter: {', '.join(missing)}")
    if "\ufffd" in text:      # read with replacement: approving it would bind the replaced text
        out.append("P1 the PLAN holds bytes outside UTF-8; save it as UTF-8")
    if spec_text is None:
        out.append("P2 the spec is not readable")
    else:
        covered = {i for r in rows for i in IDS.findall(r.get("covers", ""))}
        covered |= set(re.findall(r"Deferred:\s*((?:FR|SC)-\d+)", text))
        gaps = [i for i in _ids(spec_text) if i not in covered]
        if gaps:
            out.append(f"P2 not covered: {', '.join(gaps)}")
        first = {i for r in rows if r.get("wave") == "1" for i in IDS.findall(r.get("covers", ""))}
        kept = {m.group(1) for c in spec.sections(spec_text).values() for m in spec.REQ.finditer(c)
                if m.group(2).lstrip().lower().startswith("(unchanged)")}     # an existing test may prove it
        late = [i for i in _ids(spec_text)
                if i.startswith("FR-") and i in covered and i not in first and i not in kept]
        if late:
            out.append(f"P2 no spec test in wave 1 for: {', '.join(late)}")
    out += [f"P2 task {r.get('#', '?')} covers nothing" for r in rows if not IDS.search(r.get("covers", ""))]
    named = set()
    for r in rows:
        files = TICK.findall(r.get("files", ""))
        named |= set(files)
        if not files:
            out.append(f"P3 task {r.get('#', '?')} names no file")
        if not r.get("check", "").strip():
            out.append(f"P3 task {r.get('#', '?')} has no check")
    front_files = set(listed(text, "files"))
    if rows and named and front_files != named:
        diff = [f"+ {f}" for f in sorted(front_files - named)] + [f"- {f}" for f in sorted(named - front_files)]
        out.append(f"P3 files in the frontmatter and the tasks differ: {', '.join(diff)}")
    out += [f"P4 {msg}" for _, msg in wave_clashes(text)]
    head = "\n".join(re.sub(r"(^|\s)#.*", "", line) for line in spec.split(text)[0])     # YAML comments go
    holes = [h for name, content in spec.sections(text).items() if name != "change log"
             for h in spec.HOLE.findall(CODE.sub("", spec.FENCE.sub("", content)))] + spec.HOLE.findall(head)
    if holes:
        out.append(f"P5 open: {', '.join(dict.fromkeys(holes))}")
    return out


def hold(spec_text: str, plan_text: str, blockers=(), open_=None) -> str:
    """Why a person has to approve this PLAN even at plan_approval = auto; "" when nothing holds it.
    A needs: entry that names an item (#n) holds only while that item is open (open_: the open
    issues, None when unknown) and no blocker of this one: the board waits for a blocker already,
    and a closed item is done."""
    fm = spec.front(spec_text or "")
    risk = fm.get("risk") or []
    risk = risk if isinstance(risk, list) else [risk]
    refs = [(x, int(m.group(1)) if m else None) for x in listed(plan_text, "needs") for m in [REF.match(x)]]
    needs = [x for x, n in refs if n is None or n not in blockers and (open_ is None or n in open_)]
    return "; ".join(filter(None, [f"risk: {', '.join(risk)}" if risk else "",
                                   f"needs {', '.join(needs)}" if needs else "",
                                   "effort L" if fm.get("effort") == "L" else ""]))


def gates(root: Path, items: list, cfg: dict, found: dict = None) -> dict:
    """{issue: the first thing it waits for} for open, unclaimed work; no entry means ready."""
    base = config.base_ref(root)
    found = plans(root, base) if found is None else found
    sha = _git(root, "rev-parse", "--verify", "-q", base).strip()
    open_ = {i["number"] for i in items}
    out = {}
    for i in items:
        if i.get("type") not in state.WORK or i.get("assignees"):
            continue
        n = i["number"]
        if not i.get("approved"):
            out[n] = "not approved"
            continue
        key = (sha, i.get("spec"))
        if key not in _specs:
            _specs[key] = spec.on_base(root, i["spec"], sha or base) if i.get("spec") else None
        spec_text = _specs[key]
        wrong = spec.findings(spec_text, i["type"], n)
        if wrong:
            out[n] = f"spec: {wrong[0]}"
            continue
        p = found.get(n)
        if not p:
            out[n] = "needs a plan"
            continue
        gate = plan_gate(p["text"], spec_text, cfg, i.get("plan_ok"), i.get("blocked_by") or (), open_)
        if gate:
            out[n] = gate
    return out


def digest(text: str) -> str:
    """What a PLAN approval binds to: this text, and no later rewrite of it."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def plan_gate(plan_text: str, spec_text, cfg: dict, plan_ok: str = None, blockers=(), open_=None):
    """Why a PLAN keeps its item from being built, or None when it may be built.
    plan_ok: the digest of the PLAN a person approved; it counts only for that PLAN."""
    wrong = plan_findings(plan_text, spec_text)
    if wrong:
        return f"plan: {wrong[0]}"
    if plan_ok and plan_ok == digest(plan_text):
        return None
    why = hold(spec_text, plan_text, blockers, open_)
    if cfg.get("plan_approval") == "manual" or why:
        return "plan waits for you" + (f" ({why})" if why else "")
    return None


def spec_pr(item: dict, branch: str) -> tuple:
    """(the one open PR into branch that carries the item's spec and changes only _devprocess/, "")
    or (None, why not): what approving the item merges when its spec is not on branch yet and an open
    PR into branch carries it (#69); ask only then, else spec_branch() says what it merges (#88)."""
    prs = [p for p in item.get("spec_prs") or () if p["base"] == branch]
    if len(prs) > 1:
        return None, f"open pull requests {', '.join('#%d' % p['number'] for p in prs)} carry it: close all but one"
    if not prs[0]["docs"]:
        return None, (f"PR #{prs[0]['number']} that carries it changes more than _devprocess/, or more files than "
                      "gh lists: approve merges only a spec pull request")
    return prs[0], ""


def spec_branch(branches: list) -> tuple:
    """(the one branch of origin, the base aside, that carries an item's spec, "") or (None, why not): what
    approving the item merges when no open PR into the base carries its spec (#88). Several refuse: each
    brings other files along, and a stacked docs branch may carry another item's only spec (gate round 1)."""
    if not branches:
        return None, "no branch of origin carries it; /pulse-re pushes it"
    if len(branches) > 1:
        return None, (f"branches {', '.join(branches)} of origin carry it: if one of these branches carries the "
                      "other's work too (a stacked docs branch), approve that branch's item first; it brings this "
                      "spec along. Otherwise keep the spec on one branch: remove it from the others, push, and "
                      "approve again")
    return branches[0], ""


printable = config.printable                # one definition, in config, which cannot import this module


def _shown(paths: list) -> str:
    """Paths a PR chose, fit for a terminal, three at most."""
    return ", ".join(map(printable, paths[:3])) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")


def _fetch_base(root: Path, branch: str) -> bool:
    """origin's branch into refs/remotes/origin/<branch> whatever the clone's refspec says (a clone of
    one other branch fetched into FETCH_HEAD alone); True when origin answered."""
    return not net_git(root, "fetch", "-q", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}").returncode


def unpushed(root: Path, n: int, base: str) -> list:
    """(branch, commits) for each branch of item n in this clone, its docs branch too, with commits
    origin lacks: against origin/<branch>, else against the base branch on origin. Only this clone
    has them; the team sees no work there, and whoever takes n over starts without it (#79)."""
    out = []
    for ref in _git(root, "for-each-ref", "--format=%(refname)", "refs/heads").split():
        b = ref.removeprefix("refs/heads/")
        if state.item_of(b) != n and not b.startswith(f"docs/{n}-"):
            continue
        since = _tip(root, f"refs/remotes/origin/{b}") or _tip(root, f"refs/remotes/origin/{base}")
        count = _git(root, "rev-list", "--count", f"{since}..{ref}").strip() if since else ""
        if count.isdigit() and int(count):
            out.append((b, int(count)))
    return out


def _tip(root: Path, ref: str) -> str:
    """The commit of exactly this full ref, or "": git's own lookup would fall through to a tag named like
    it, refs/tags/refs/remotes/origin/main say, that anyone with push access can place (#69 final check)."""
    return _git(root, "show-ref", "--verify", "-s", ref).strip()


def approve(root: Path, repo_name: str, item: dict, run=None, head: str = None) -> tuple:
    """(approved, what happened or why not) for pulse approve and the map's approve spec. A spec on
    the base branch is held to R1 to R6 there. A spec in one open spec PR into it (#69) is read afresh:
    no fork, into the base, the head the map showed when it showed one, _merge_check(), the spec at that
    head to R1 to R6. Then a draft becomes ready, the PR is merged bound to that head, and once the spec
    is on the base branch the item approved. A spec in no such PR, on exactly one branch of origin (#88),
    passes the same checks at that branch's head; approve merges it itself and approves (_merge_branch).
    head: the head the map's confirmation showed, or NO_MERGE when it showed none; None merges what checks."""
    ok, said = _approve(root, repo_name, item, run or state.gh, head)
    return ok, printable(said)


_newer: dict = {}                    # (root, path, branch, real, every tip of origin) -> newer(); history never changes


def newer(root: Path, path: str, branch: str, real: str, tips: str = None) -> list:
    """The branches of origin, item branches aside, that changed the spec at path since they forked from branch at
    real, where it lies already: a correction pushed after an earlier approval merged their other specs (#99
    FR-07). A branch that brings the spec first is none. As the last fetch left them (tips: spec.origin_tips(),
    read once by a caller that asks for several specs), once per state of origin: the map asks every 2 s. []
    without the spec at real."""
    tips = spec.origin_tips(root) if tips is None else tips
    key = (str(root), path, branch, real, tips)
    if key not in _newer:
        at = lambda c: _git(root, "rev-parse", "-q", "--verify", f"{c}:{path}").strip()     # noqa: E731
        heads = {r: c for c, _, r in (line.partition(" ") for line in tips.split("\n"))}
        here, out = at(real) if real else "", []
        for b in spec.carriers(root, path, tips) if here else ():
            head = heads.get(f"refs/remotes/origin/{b}")
            if b == branch or state.item_of(b) or not head or at(head) == here:
                continue
            was = at(_git(root, "merge-base", real, head).strip() or head)
            if was and was != at(head):
                out.append(b)
        if len(_newer) > 1024:
            _newer.clear()
        _newer[key] = sorted(out)                 # one order for people and tests (last check of #99)
    return _newer[key]


def _approve(root: Path, repo_name: str, item: dict, run, shown: str) -> tuple:
    n, path = item.get("number"), item.get("spec")
    branch = config.load(root)["base_branch"] or config.default_branch(root)
    _fetch_base(root, branch)
    base = config.base_ref(root, branch)
    real = _tip(root, f"refs/remotes/origin/{branch}") or _tip(root, f"refs/heads/{branch}")
    text = spec.on_base(root, path, real) if path and real else None
    fixes = []                              # a correction pushed since an approval merged it (#99 FR-07); an epic
    if text is not None and shown != NO_MERGE and item.get("type") != "epic":     # takes its copy on the base
        net_git(root, "fetch", "-q", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*")
        fixes = newer(root, path, branch, real)
        if len(fixes) > 1:
            return False, SEVERAL.format(", ".join(fixes), branch)
    if text is not None and not fixes:
        why = spec.refusal(text, item.get("type"), n, base)
        if not why:
            state.approve(root, repo_name, [n], run=run)
        return not why, why
    if shown == NO_MERGE:                     # the map showed a plain approval: it merges nothing (#88 final check)
        return False, (f"R1 spec missing on {branch} as origin has it, though the map showed it there (does this "
                       f"clone have a tag or a branch named origin/{branch}?); nothing merged")
    if not any(p["base"] == branch for p in item.get("spec_prs") or ()):     # no spec PR: its branch (#88)
        return _merge_branch(root, repo_name, item, run, shown, branch, base, bool(fixes))
    pr, why = spec_pr(item, branch)
    if not pr:
        return False, f"R1 spec missing on the base branch ({base}); {why}"
    p = pr["number"]
    try:
        v = json.loads(run(["pr", "view", str(p), "--repo", repo_name, "--json",
                            "state,isDraft,isCrossRepository,baseRefName,headRefName,headRefOid"]))
    except (state.StateError, ValueError) as e:
        return False, f"PR #{p} could not be read: {e}"
    if v.get("isCrossRepository"):
        return False, f"PR #{p} comes from a fork: approve merges only a spec pull request of this repository"
    head = v.get("headRefOid") or ""
    if v.get("state") != "OPEN" or v.get("baseRefName") != branch or not re.fullmatch(r"[0-9a-f]{40,64}", head):
        return False, f"PR #{p} is not an open pull request into {branch}"
    if shown and head != shown:               # the map's confirmation showed another head (audit M-1)
        return False, f"PR #{p} moved since approve spec showed it; nothing merged"
    net_git(root, "fetch", "-q", "origin", f"refs/heads/{v.get('headRefName')}")     # never read as an option
    if not _git(root, "rev-parse", "--verify", "-q", f"{head}^{{commit}}").strip():
        return False, f"PR #{p} moved while Pulse read it; approve the item again"
    real = _tip(root, f"refs/remotes/origin/{branch}") if _fetch_base(root, branch) else ""
    if not real:                              # a stale base hides what merges (audit round 2, M-2)
        return False, f"Pulse could not fetch {branch} from origin; nothing merged"
    _, changed, why, _ = _merge_check(root, real, head, path, branch, pr=p)
    why = why or spec.refusal(spec.on_base(root, path, head), item.get("type"), n, f"PR #{p}",
                              fix="fix its spec with /pulse-re on its branch; nothing merged")
    if why:
        return False, why
    try:
        if v.get("isDraft"):
            run(["pr", "ready", str(p), "--repo", repo_name])
        state.merge(root, repo_name, p, head, run=run)
    except state.StateError as e:
        return False, f"GitHub did not merge PR #{p}: {e}"
    _fetch_base(root, branch)                # a merge queue takes the PR, and gh exits 0 all the same
    if spec.on_base(root, path, _tip(root, f"refs/remotes/origin/{branch}") or real) is None:
        return False, (f"GitHub took PR #{p}, but the spec is not on {branch} yet (a merge queue?); approve "
                       "the item again once it merged")
    state.approve(root, repo_name, [n], run=run)
    return True, f"merged its spec PR #{p} into {branch}" + _with(changed, path)


_merges: dict = {}                   # (root, base commit, head commit) -> what their merge writes


def merge_of(root: Path, real: str, head: str) -> tuple:
    """(tree, [(path, ":old new sha sha status")]) of the merge of head into real as git's merge-ort makes it,
    each path as `git diff --raw` names it from real, renames split, submodules shown whatever the config;
    (None, []) when it does not merge cleanly (or git is older than 2.38). Once per pair of commits: the map
    asks every 2 s, and their history never changes (#88 gate round 1)."""
    key = (str(root), real, head)
    if key not in _merges:
        merged = subprocess.run(["git", "-C", str(root), "merge-tree", "--write-tree", real, head],
                                capture_output=True, text=True)
        tree = merged.stdout.split("\n", 1)[0].strip()
        if merged.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", tree):
            tree, changed = None, []
        else:
            raw = _git(root, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", "--ignore-submodules=none",
                       real, tree).split("\0")
            changed = list(zip(raw[1::2], raw[0::2]))
        if len(_merges) > 1024:
            _merges.clear()
        _merges[key] = (tree, changed)
    return _merges[key]


def _merge_check(root: Path, real: str, head: str, path: str, branch: str, pr: int = None, b: str = None) -> tuple:
    """(tree, [(status, path)], "", "") when the merge of head, spec PR #pr or branch b of origin, into real,
    the base branch freshly fetched, changes only plain files under _devprocess/, path among them; status A,
    M, D, or T as git names it from real. Else (None, [], why, kind): why as approve says it, kind (conflict,
    outside, link, spec) for the map's words. It judges what the merge writes, as GitHub's merge-ort makes
    it: a criss-cross history, a file the base moved out of _devprocess/ (audit H-1 of #69, round 2 M-1),
    renames split, submodules shown whatever the config (M-2)."""
    tree, changed = merge_of(root, real, head)
    who, only = (f"PR #{pr}", "a spec pull request") if pr else (f"branch {b}", "a branch of specs")
    outside = [c for c, _ in changed if not c.startswith("_devprocess/")]
    odd = [c for c, m in changed if {m[1:7], m[8:14]} & {"120000", "160000"}]     # a link, a submodule (M-2)
    kind = "conflict" if not tree else "outside" if outside else "link" if odd else \
        "spec" if path not in dict(changed) else ""
    if not kind:
        return tree, [(m.split()[-1], c) for c, m in changed], "", ""
    on = "" if pr else f": merge origin/{branch} into {b}, keep both sides where they conflict, push it, and " \
                       "approve again"
    return None, [], {"conflict": f"{who} does not merge cleanly into {branch} here (or git is older than 2.38); "
                                  f"nothing merged{on}",
                      "outside": f"{who} changes {_shown(outside)} outside _devprocess/: approve merges only {only}",
                      "link": f"{who} adds a link or a submodule under _devprocess/: {_shown(odd)}; approve merges "
                              "only files",
                      "spec": f"{who} does not carry the spec"}[kind], kind


def along(changed: list, path: str) -> tuple:
    """(the specs a merge adds beside the item's own, every other path it changes as "M path"), from
    _merge_check(): what the map's confirmation and approve name, all of it (#88 audit M-1)."""
    specs = [c for s, c in changed if s == "A" and c != path and spec.LIKE_ID.match(Path(c).name)]
    return specs, [f"{s} {c}" for s, c in changed if (c != path or s != "A") and c not in specs]   # M: FR-07


def _with(changed: list, path: str) -> str:
    specs, rest = along(changed, path)
    return (f", with {', '.join(specs)}" if specs else "") + (f"; also changes: {', '.join(rest)}" if rest else "")


def _merge_branch(root: Path, repo_name: str, item: dict, run, shown: str, branch: str, base: str,
                  fix: bool = False) -> tuple:
    """#88: the one branch of origin that carries the spec, merged into branch without a pull request and
    without a checkout: every branch fetched afresh by an explicit refspec, the head the map showed, the
    checks of a spec PR at that head, then a merge commit of the tree git checked on the fetched base, under
    the person's git identity, pushed without force: a fast-forward, or nothing. Approved once the spec is
    on the base branch after a new fetch. The branch stays on origin. fix: the spec is on the base branch
    already, and the one branch that changed it since is merged (#99 FR-07)."""
    n, path = item.get("number"), item.get("spec")
    if not path:                              # nothing to look for
        return False, f"R1 spec missing on the base branch ({base}); {spec_branch([])[1]}"
    got = net_git(root, "fetch", "-q", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*")
    if got.returncode:                        # what git said, as for every fetch (#85)
        said = git_error(got.stderr)
        return False, "Pulse could not fetch the branches of origin" + (f" (git fetch said: {said})" if said else "") \
            + "; nothing merged"
    real = _tip(root, f"refs/remotes/origin/{branch}")
    b, why = spec_branch(newer(root, path, branch, real) if fix else [c for c in spec.carriers(root, path) if c != branch])
    if not b:
        return False, f"R1 spec missing on the base branch ({base}); {why}"
    who, head = f"branch {b}", _tip(root, f"refs/remotes/origin/{b}")
    if shown and head != shown:               # the map's confirmation showed another head (as audit M-1 of #69)
        return False, f"{who} moved since approve spec showed it; nothing merged"
    if not real:
        return False, f"Pulse could not fetch {branch} from origin; nothing merged"
    tree, changed, why, _ = _merge_check(root, real, head, path, branch, b=b)
    why = why or spec.refusal(spec.on_base(root, path, head), item.get("type"), n, who,
                              fix="fix its spec with /pulse-re on its branch; nothing merged")
    if why:
        return False, why
    made = subprocess.run(["git", "-C", str(root), "commit-tree", tree, "-p", real, "-p", head,
                           "-m", f"Merge spec of #{n}", "-m", f"From branch {printable(b)}, merged by pulse approve.",
                           "-m", f"Refs: #{n}"], capture_output=True, text=True)
    commit = made.stdout.strip()
    if made.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", commit):     # no git identity, say: its last line
        return False, f"git wrote no merge of {who}: {(made.stderr.strip().splitlines() or ['?'])[-1]}; nothing merged"
    pushed = net_git(root, "push", "-q", "origin", f"{commit}:refs/heads/{branch}")
    if pushed.returncode:                     # git's reason on one line, its hints left out
        said = "; ".join(" ".join(l.split()) for l in pushed.stderr.splitlines()
                         if l.strip() and not l.startswith(("hint:", "To "))) or f"exit {pushed.returncode}"
        return False, (f"origin did not take the merge into {branch} ({said}); nothing approved: approve again if "
                       f"{branch} moved; where {branch} is protected, open a pull request of {b} into {branch}, "
                       "and approve merges it")
    _fetch_base(root, branch)
    if spec.on_base(root, path, _tip(root, f"refs/remotes/origin/{branch}") or commit) is None:
        return False, f"origin took the merge, but the spec is not on {branch} after a new fetch; approve again"
    state.approve(root, repo_name, [n], run=run)
    return True, f"merged {who} into {branch}" + _with(changed, path)


def approvable(root: Path, items: list, cfg: dict, n: int) -> tuple:
    """(digest, "") when #n's PLAN waits for a person; (None, why) for anything else."""
    found = plans(root)
    free = [dict(i, assignees=[]) if i["number"] == n else i for i in items]     # a claim changes no PLAN
    gate = gates(root, free, cfg, found).get(n, "")
    if not gate.startswith("plan waits for you"):
        return None, f"#{n}: no PLAN waiting for approval" + (f" ({gate})" if gate else "")
    return digest(found[n]["text"]), ""

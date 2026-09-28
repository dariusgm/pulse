---
title: Troubleshooting
description: Common problems when installing and running Pulse, and how to fix them.
---

# Troubleshooting

## Installation

### `/plugin isn't available in this environment` in VS Code

`/plugin` is the plugin panel of the Claude Code CLI. In the VS Code extension, type `/plugins` to open **Manage plugins**, or run the `claude plugin` commands in a terminal ([Installation](../tutorials/installation)). A plugin installed one way shows up in the other.

### `Host key verification failed` when adding the marketplace

Claude Code clones the short form `owner/repo` over SSH, and your machine does not trust GitHub's SSH host key yet. Use the HTTPS URL:

```bash
claude plugin marketplace add https://github.com/pssah4/pulse.git
```

### `claude: command not found`

Install the CLI (`curl -fsSL https://claude.ai/install.sh | bash`, or Homebrew), open a new shell, and check `claude --version`. The VS Code extension brings its own copy for its chat panel but puts no `claude` on your PATH.

### `pulse: command not found`

Run `pulse setup --cli` from the installed plugin (the command for your agent is in [Installation](../tutorials/installation)); in VS Code, run it in the integrated terminal. Then check that `~/.local/bin` is on your PATH: add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` (zsh) or to `~/.bash_profile` (bash; `~/.bashrc` on Linux) and open a new terminal. If `pulse` says "no installed Pulse found", the plugin is gone: install it again, or take the command out with `rm ~/.local/bin/pulse`. A terminal panel "Pulse map" that says `command not found: pulse` each time VS Code opens the folder comes from the task `/pulse-setup` wrote to `.vscode/tasks.json`: put the command on your PATH, or delete the task.

Installed from a clone ([Codex without the plugin](../tutorials/installation#codex-without-the-plugin)): `~/.local/bin/pulse` is a link into the clone, and `pulse setup --cli` keeps it and reports `kept: not written by pulse setup`. Check the link with `ls -l ~/.local/bin/pulse`, which must point to `~/.codex/pulse/bin/pulse`, and that `~/.local/bin` is on your PATH.

### The `/pulse` commands do not show up

1. `claude plugin list` in a terminal, or **Manage plugins** (`/plugins`) in the VS Code extension, shows `pulse@pssah4-skills`?
2. Start a new session; skills load at session start.
3. Still the old commands (`/dia-guide`, `/coding`)? The predecessor plugin is still installed: see [Coming from the Digital Innovation Agents plugin](../tutorials/installation#coming-from-the-digital-innovation-agents-plugin).

### An update does not arrive

Claude Code does not update the `pssah4-skills` marketplace on its own. Run `claude plugin marketplace update pssah4-skills`, then `claude plugin update pulse@pssah4-skills`, and restart. In Codex, `codex plugin marketplace upgrade pssah4-skills` and then `codex plugin add pulse@pssah4-skills` again, and restart Codex or start a new chat in the extension.

### Codex does not find the skills

With the plugin, in the CLI and the IDE extension alike: `codex plugin list` shows `pulse@pssah4-skills` (without the CLI, first run the `codex()` line from [Installation](../tutorials/installation#codex-cli-and-ide-extension), which runs the extension's newest binary), then restart Codex or start a new chat in the extension. Installed from a clone, the fallback without the plugin: `ls ~/.agents/skills/pulse` must list the skill folders. With both, every skill shows up twice: remove one. Codex names the skills `pulse:pulse-ba` and so on: type `$pulse:pulse-ba` for `/pulse-ba`, in the CLI and the IDE extension alike. The Codex CLI also lists them under `/skills` > **List skills**, or as soon as you type `$`, by the names `pulse-ba (pulse)` and so on; in the IDE extension, type `/` in the prompt box and pick one from the **Skills** group.

## Running Pulse

### `pulse` says "not inside a git repository" or names several remotes

Pulse needs to know which GitHub repository holds the item records. It takes, in this order, `repo` from `.pulse/config.toml`, the repository set with `gh repo set-default`, or the only GitHub remote. With several remotes it does not guess:

```bash
gh repo set-default owner/name
```

### `pulse setup` complains about `gh`

Pulse needs `gh` 2.94 or newer for parent links and "blocked by" links. Update it (`brew upgrade gh`, or see [cli.github.com](https://cli.github.com)) and run `gh auth status`.

### `pulse new` refuses: push the spec first

A record links a spec that every clone must be able to read, so `pulse new --spec` checks the file before it writes anything, and stops when the check fails (exit 2):

```text
pulse new: _devprocess/requirements/features/FEAT-01-02-login.md is not on origin as committed here; commit it, then: git push -u origin docs/12-login
```

Commit the spec, run the push the message names, and run the same `pulse new` again. A spec you changed after the push needs another commit and push. `write the spec first, <path> does not exist in the repository` means the path is wrong or the spec is not written yet. For work whose spec does not exist yet, register a draft instead: `pulse new <type> "<title>" --draft`.

### `pulse new`, `pulse number`, or `pulse claim` says `git fetch said`

`pulse new --spec`, `pulse number --apply`, and `pulse claim` fetch every branch from origin, then ask origin which commit each branch is on (`git ls-remote`) and hold that against the refs git lists here. After a fetch that failed while origin answered, they print git's error; after one that went through but left a listed ref on another commit than origin names, they print `the fetch went through, but refs here differ from origin:` and the refs. Only when something they need is not as origin has it do `pulse new` and `pulse number` refuse (exit 2) and `pulse claim` name no start point (it still exits 0, the claim made):

```text
pulse number: git fetch said: error: cannot lock ref 'refs/remotes/origin/docs/login': Unable to create '/home/ana/shop/.git/refs/remotes/origin/docs/login.lock': File exists. Another git process seems to be running in this repository, or the lock file may be stale
```

- `pulse new --spec` needs the branch you are on as origin has it, and refuses when origin no longer has that branch.
- `pulse number --apply` needs the history of every branch on origin. A branch whose ref git could not update, or wrote on another commit, counts through the commit origin names; when that commit or its history did not arrive (a fetch cut short), the refusal names the branch. Of two specs with the same ID, the one on the base branch as origin has it keeps the ID.
- `pulse claim` names no start point while the ref it lists for the base branch or a branch of the item is not as origin has it (`start point not checked: ...`); otherwise it names the start point.

When they go on, the line goes to stderr. `pulse status`, `pulse show`, and `pulse approve-plan` print the same `git fetch said: ...` until a fetch goes through; they print `offline: origin did not answer` only when git said nothing, as when origin gave no answer within the time limit. Two common causes:

- A lock file that a git process left when it stopped (`File exists`): when no other git runs in the clone, delete the `.lock` file the message names.
- Two branches on origin whose names differ only in case, on a file system that ignores case (macOS, Windows): the clone keeps one ref file for both, and a fetch may even exit without an error. Pulse sees it when git lists a ref on the other branch's commit. It does not see it yet when `origin/main` sits in `packed-refs` (after a clone or `git gc`) and a pushed `MAIN` arrives as a loose ref: git lists both on the right commits but finds the loose one for `origin/main` too, so `pulse claim` can name `MAIN`'s commit as the start point; `pulse go` and the hint of `pulse claim` and `pulse release` on where another holder's work is do not check the refs at all yet. A follow-up item covers these. Delete or rename one of the two branches on origin, or move the clone to the reftable format with `git refs migrate --ref-format=reftable` (git 2.46 or newer).

`git fetch --prune origin` shows git's whole message. When origin does not answer at all, `pulse new` and `pulse number` refuse with `origin did not answer` and hand out nothing; `pulse claim` makes the claim and says `start point not checked: origin did not answer`.

### `pulse approve` refuses: no branch carries the spec

```text
#12 not approved: R1 spec missing on the base branch (origin/main); no branch of origin carries it; /pulse-re pushes it
```

Agents plan from the spec as the base branch on origin has it (rule R1). `pulse approve` merges the one branch of origin that carries the spec into the base branch first, without a pull request: the docs branch that `/pulse-re` pushed. Once merged, it names every path the merge changed beside the spec: the specs it brought along, then each other path with `A` (added), `M` (changed), or `D` (deleted). The map's confirmation shows the same list before `Enter` merges anything.

A spec an earlier approval brought onto the base branch, along with the spec of another item, takes a later correction along: when one branch of origin (an item branch aside) changed the spec since it last reached the base branch, `pulse approve` merges that branch again, with the same checks, and names the spec with `M` among the changed paths; the map's confirmation shows it before `Enter`. When several branches changed it (`branches docs/12-a, docs/12-b of origin changed its spec since main took it`), it merges none: keep the correction on one of them, push, and approve again. The map judges such a spec as `pulse approve` does: it offers the merge of the correction, or says why not yet. An epic takes its copy on the base branch: every docs branch of one of its features changes its Items, and those lines reach the base branch with the features' approvals.

Here no branch of origin carries it: push the spec, or let `/pulse-re` do it, then approve again. When several branches carry it (`branches docs/12-a, docs/12-b of origin carry it: ...`), each would bring its other files along, and one of them may carry another item's only spec. If one of these branches carries the other's work too (a stacked docs branch), approve that branch's item first; it brings this spec along. Otherwise keep the spec on one branch: remove it from the others, push, and approve again. A branch whose merge would change files outside `_devprocess/` or add a link or a submodule there is never merged by an approval: a spec committed on a build branch reaches the base branch with that branch's pull request. Without a fresh fetch of every branch nothing is merged either. When the branch moved after the map showed it, approve spec refuses and names it; press `a` again to see the new head. `R1 issue: ... in the spec, item is #12` means the spec names another item or none: commit the `issue:` line that `pulse new` wrote into the spec and push.

When the branch does not merge cleanly (`branch docs/12-b does not merge cleanly into main here ...`), another merge got there first, most often a second feature of the same epic: each `pulse new` adds its line at the end of the epic's `## Items`. The refusal names the way on: merge `origin/<base>` into the docs branch (`git fetch origin`, then `git merge origin/main` on `docs/12-b`), keep both lines where they conflict, commit, push the branch, and approve again. The map shows `not yet: its branch does not merge cleanly into main` meanwhile.

When origin refuses the push of the merge (`origin did not take the merge into main (...)`), nothing is approved, and the message quotes git. The base branch moved since the fetch: approve again. The base branch is protected (GitHub answers `GH006`): open a pull request of the docs branch into the base branch and name the item in it with `Refs: #<n>` only (a `Closes #<n>` would close the item with the merge), and `pulse approve` merges that one, as long as it is the only open pull request into the base branch that carries the spec and changes nothing outside `_devprocess/`; one from a fork it never merges. When GitHub refuses that merge (a conflict, a review the branch requires), `pulse approve` shows its message and approves nothing. The approve spec action on the map behaves the same. A draft has no spec yet and cannot be approved.

`pulse approve` also refuses while the spec of a feature, improvement, or fix on the base branch breaks one of R2 to R6 (an epic needs R1 only), and names the rule; the `a` key on the map does the same. Fix the spec with [`/pulse-re`](../guides/pulse-re) on its docs branch and push it: approve again merges that correction and approves.

### The map does not start `pulse go`

Its footer says why, once. The map starts a run only while Pulse is on, `go_autostart` is not `false`, `PULSE_GO` is not `off`, the board answered, and no run of this clone lives. It holds back items the last run did not finish, and after a run you stopped or one that ended before its report it waits until `pulse go` runs by hand (`pulse go --detach`). It also waits while `.pulse/config.toml` differs from the one on origin's default branch, or on the base branch that one names: commit and merge the change, or start `pulse go` by hand. [/pulse-map](../guides/pulse-map#it-starts-pulse-go) has the rules.

### The map shows "no agent active" although an agent works

The lights come from the Pulse hooks, which record only when `mode = "on"` in `.pulse/config.toml`. Check the mode. A Codex session, in the CLI or the IDE extension, records only after you trusted the plugin's hooks, all of them, with `/hooks` in the CLI or one by one on the Hooks page of the extension's settings; a new chat picks them up. Until then `pulse claim`, `pulse new --draft`, and `pulse go` print `pulse: this Codex session reaches no Pulse hook` on the way; with [Codex without the plugin](../tutorials/installation#codex-without-the-plugin) there are no hooks to trust, so that line stays, and the rules come through `AGENTS.md`. Sessions without the hooks, such as Codex installed from a clone, get no light; the items they hold still show up. An agent that `pulse go` started counts as working while its phase runs, with or without hooks, and an agent silent for five minutes turns grey.

### `pulse map` prints one frame and ends

It does that without a terminal: in a pipe, a file, or an agent's shell tool. Run it in a terminal of its own; [/pulse-map](../guides/pulse-map#open-it-from-the-chat) says where for each chat. A working light that does not breathe is no fault: terminals with 16 colors show steady lights.

### The agent ignores the rules

Check `.pulse/config.toml`: `mode = "off"` silences every hook. In Claude Code, `claude plugin list` in a terminal, or **Manage plugins** (`/plugins`) in the VS Code extension, should show `pulse` as enabled. In Codex, the plugin's hooks bring the rules once you trusted them; Codex installed from a clone reads them from its global `AGENTS.md`, in `$CODEX_HOME` when you set it, else in `~/.codex` (see [Codex without the plugin](../tutorials/installation#codex-without-the-plugin)).

### `pulse check` reports findings

Each finding names the file, the line, and the rule (C1 to C11, or R1 to R6 for an approved item's spec, see [Commands](./commands#pulse-check)). Fix the document, or for a cap, add a `## Reasoned exception` section (the heading in any case). An epic's `## Items` list, which `pulse new` writes, does not count toward its cap.

A C10 finding names a spec whose file name lacks the ID of its place in the tree: it has none yet, it moved to another parent, or another branch took the same ID. `pulse number --apply` renames it, rewrites the paths to it, and moves its record along; commit the result. An open record keeps its old path until the rename is on the base branch: after the merge, run `pulse number --apply` once more.

A C11 finding names a feature spec or decision record whose `layer:` names a layer or group that `_devprocess/architecture-map.md` lacks. Fix the name, or add the layer or group to that file ([Architecture map](./artifacts#architecture-map)).

An R finding is about the spec as the base branch on origin has it. A fix on your branch clears it only once it is merged, and until then the git hook refuses every commit, the fix commit included. The way out:

1. `pulse approve --undo <n>` takes the approval back. `pulse check` reads only the specs of approved items, so the git hook lets your commits through again, and no session or `pulse go` run claims the item meanwhile. Without the git hook, the approval can stay: skip this step and step 3.
2. Fix the spec on a branch, with [`/pulse-re`](../guides/pulse-re) or by hand, push it, and merge it into the base branch.
3. `pulse approve <n>` again. It reads the base branch on origin and refuses while the spec there still breaks one of R1 to R6.

To keep the approval, or if the hook still refuses the fix commit (the spec of another approved item may break a rule too), commit the fix once with `git commit --no-verify`. The hook reads origin as of your last fetch: after the merge, pull the base branch, and it lets commits through again.

### `pulse claim` says an item is held

Every claim leaves a mark on the item's record that names the session holding it: a Claude Code session, a Codex thread, a `pulse go` run, or a terminal. Another session is refused, even under your login, so two agents never build the same item. The refusal names the holder, since when, and the command that frees the item:

```text
#12 is held by alice since 2026-09-24 09:12 UTC; to hand it over: pulse release --take 12
```

- **Another person holds it:** agree with them first. `pulse release --take <n>` then hands the item over: their assignee and claim marks go, and a comment on the record names who did it. Claim it as usual afterwards. An agent runs this only after you said yes. For a draft, the refusal and the hand-over name its docs branch on origin as where the work is (`; the work is on origin/docs/12-mode`), and the claim starts from it.
- **Another session of yours holds it and has ended:** `pulse claim --take <n>` takes it over.

`release` and `done` refuse a claim that is not yours in the same way. `pulse done --take <n>` closes an item whoever holds it.

### The map says `spec in progress by <login>`

The item is a draft: a `/pulse-ba`, `/pulse-re`, or `/pulse-realign` session of that person registered it with `pulse new ... --draft` and holds it while it writes. A draft has no spec on the board yet, cannot be approved, and no agent builds it. Talk to that person before you write about the same topic. The draft ends when its spec is pushed and attached with `pulse new <type> "<title>" --spec <path> --issue <n>`. A draft that a session of your own held before it ended: `pulse claim --take <n>` in the new session.

### `pulse new --draft` says `is the draft ... already`

An open draft of the same type carries the same title, for example a realign (`Realign: <owner/repo>`) or a Project-BA that another session started. The line names its number and who holds it, and nothing new is created. A draft another person holds stays theirs: talk to them. One nobody holds, or one of yours, goes on with the same command plus `--issue <n>`; a session of your own that has ended hands it over with `pulse claim --take <n>`.

### The map says `no sign of life`

A teammate holds the item, and the session that holds it has not reported for 30 minutes or more. `pulse go` reports each phase it starts and every 10 minutes while one runs, an interactive session reports `working` at most every 10 minutes while it holds an item, and the skills run `pulse beat <n> <phase>`. Silence means the session ended, lost its network, or waits for its person. `pulse show <n>` prints `claimed_phase` and `claimed_beat`, the time of the last report in UTC.

Ask the holder. Once they agree, `pulse release --take <n>` hands the item over; claim it, then continue on the item branch they pushed (`pulse go` starts from it on its own, `/pulse-build <n>` continues on it). What they did not push stays on their machine. A session of theirs that still runs hears of the hand-over once, at its next sign of life, the heartbeat or `pulse beat` (which exits with 1), with who has the item now, also when it claimed the item, or registered it as a draft, and has waited since: it stops the work on the item and pushes nothing more of it. Its stop hook asks for no push and no review or audit of the item, since it reads who holds the item from the board at every stop, and a new session on the item's branch hears who holds it. Its `pulse release <n>` answers that the item was handed over and there is nothing to give back. When two claims came at the same moment and the older one won, `pulse beat` also names `pulse release <n>`, which takes the session's own mark off the item.

### The ramp says `last run: ...`

A `pulse go` run gave the item back and left a note on it, or a session did with `pulse release <n> --note`: why it stopped (for a run a failure, a usage limit, or a stop) and which branch holds its work. The map shows the first line; `pulse show <n>` prints the whole note. Nobody holds the item, so claim it as usual. `pulse go` starts its worktree from the pushed item branch; in a session, `/pulse-build <n>` continues on that branch. Changes of a phase the run stopped halfway stay in that run's worktree, beside the repository of the machine that ran it.

### A command says "only a person does this"

`approve`, `approve-plan`, `rank`, `done`, `release --take`, and `release --drop-unpushed` refuse to run inside an agent that `pulse go` started (it carries `PULSE_HOLDER`). These decisions belong to a person: run the command in your own terminal or chat session. Such an agent also claims, gives back, and blocks only the item it was started for (`PULSE_ITEM`); `pulse claim`, `pulse release`, or `pulse block` of another item ends with "claims, releases, and blocks only its own item".

### An item was approved by mistake

`pulse approve --undo <n>` takes the approval back. Until someone approves it again, no session and no `pulse go` run claims it.

### An agent of `pulse go` is refused a command

A headless agent cannot answer a permission prompt, so it runs only what its template allows. The built-in Claude template allows `verify` up to its first option or path and five git commands; the Codex template lets Codex write the shared git directory so it can commit. A template in `[agents]` copied from an older Pulse lacks both rights. See [Agent templates](./configuration#agent-templates) for what the rule covers and how to fix a template.

### `pulse go` leaves an item as failed

Its claim goes back to the ramp and its worktree stays for a look; the log is in `.git/pulse/go/<n>.log`. Fix the cause, then run `pulse go` again.

### The Stop hook asks for gates the pull request has

A review or audit verdict on a pull request counts only from someone who can push to the repository ([Review](../guides/pulse-review#verdicts-on-the-pull-request)). A verdict from someone with read access, or from a GitHub App, never counts: run the gates yourself (`pulse review <n> --run`, `pulse audit <n> --run`); each puts its verdict on the pull request.

For a member or collaborator, Pulse asks GitHub for their permission. When the request adds that Pulse could not check who posted the verdicts, GitHub gave no answer, and the text in parentheses is GitHub's reason:

- `Must have push access to view repository collaborators (HTTP 403)`: the account gh uses cannot push to the repository, and GitHub does not tell it who can. Check that account first: `gh auth status` shows which one gh uses, and `gh auth switch` changes it. Someone who can push most likely has gh logged in to another account, such as a personal one beside an Enterprise Managed User. If you cannot push, ask for write access, or leave the gates and the merge to someone who can.
- `API rate limit exceeded`: wait until GitHub's limit resets (`gh api rate_limit` shows when); the next Stop asks again.

When neither applies, run the gates yourself as above. The map merges nothing for the same reason and shows GitHub's text in its status line.

## Versions

`claude plugin list` and `codex plugin list` show the installed version; the [changelog](https://github.com/pssah4/pulse/blob/main/CHANGELOG.md) says what each version brought. After an update, restart the agent: a running Claude Code session keeps the version it started with, while the Codex update deletes the old version folder that a running Codex session still points at.

## Still stuck?

Open an issue on [GitHub](https://github.com/pssah4/pulse/issues) with your platform, `pulse --help` output, and what you tried.

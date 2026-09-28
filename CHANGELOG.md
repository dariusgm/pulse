# Changelog

All notable changes to Pulse are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-09-28

### Added

- The live map starts `pulse go` on a key: while approved work waits
  and no run of the clone lives, NEXT says `g start pulse go: #5, #7`,
  also where the map does not start a run by itself. `g`, or `Enter` on
  that line, shows the items, the agent, the test command, and why the
  map did not start the run; `Enter` starts it apart from the map.
  Without a test command the line names the command that sets it (#76).

### Changed

- Planning is a step of `/pulse-re` too. When you approve a feature,
  improvement, or fix in the RE session, the skill runs `pulse approve`
  (which brings the spec onto the base branch, see #88 below), plans the
  item right away without asking, and
  goes on into the build unless something holds the PLAN; an epic gets
  no PLAN. The guides of `/pulse`, `/pulse-re`, and planning, the
  V-Model page, the artifacts and commands references, the operating
  model, and the full V-Model tutorial say so, and the planning skill
  names effort L among the holds of a PLAN. Tests hold every hand-over
  between the stops and look through the skills and the rules for a
  question whether to go on, in the forms the skills used to ask it
  (#26).

- One name for the place where item state lives: the board. The README,
  the docs, the command reference (with the help of `pulse new` and
  `pulse migrate --issues`), and the skills and their references no
  longer put item state "on GitHub" or content into an issue: a bug's
  substance goes into its fix spec, its record holds only state. Where
  it helps, a page says that each record is technically a GitHub issue
  (#11).

- Work reaches origin as it happens. A session that holds an item and
  ends with commits on its branch, or its docs branch, that origin
  lacks is stopped once and told the push. `pulse release` keeps such
  an item unless `--drop-unpushed` gives it back without them. The
  rules and skills push after every commit; `/pulse-ba` and `/pulse-re`
  push their docs branch from the first commit on, so the BA shows
  while it is written and its approval decides whether it counts (#79).

- Pulse syncs with origin before it hands anything out. `pulse claim`
  fetches and names the start point: the item's branch on origin, else
  the base branch as origin has it now, never the local one.
  `pulse number --apply` and `pulse new --spec` fetch first and refuse when
  origin does not answer, so an ID another clone pushed is not handed
  out again and no record links a spec nobody saw on origin. Rules and skills start every branch from
  there (#78).

- A spec needs no pull request any more. When the spec of an item is
  not on the base branch and in no open spec pull request, but on
  exactly one branch of origin, `pulse approve` and approve spec in the
  map merge that branch into the base branch themselves, push the
  merge, and then approve. The checks of a spec pull request hold: the
  merge changes only plain files under `_devprocess/`, the spec at the
  branch's head passes R1 to R6 (an epic R1), and the map merges only the head its
  confirmation showed. The confirmation, and `pulse approve` afterwards,
  name every path the merge changes, with A, M, or D, and the map offers
  the merge only where `pulse approve` makes it; elsewhere it says why
  not yet. `Enter` merges nothing its confirmation did not show. The merge commit, `Merge spec of #<n>`, is made without a
  checkout under your git identity and pushed without force. Several
  branches that carry the spec, a branch that does not merge cleanly, or
  a push origin refuses merge nothing and say what to do; on a protected
  base branch, a spec pull request stays the way. `/pulse-re` and
  `/pulse-build` push a spec and open no pull request for it, and the
  rules, skills, and docs say so (#88).

- Rules, skills, templates, docs, and diagrams tell the same flow. A
  spec approved in the `/pulse-re` session is planned there at once and
  built without a stop, any other in ramp order; planning runs in `/pulse-re`,
  `/pulse-build`, and `pulse go`, and `pulse go` opens the pull request
  for a person's merge. A person's holds are stops, the gates stay tests,
  review, and audit; the place of item state is the board everywhere.
  The RE guide no longer promises a Benefits Hypothesis, an ASR level
  Low, or an architecture gate. `/pulse-build` says what a session does
  that lost its item, and every list of a person's levers names
  `release --drop-unpushed`. The map pages name the lights, keys, holds,
  and reasons as the map shows them, and say that the hold after a
  failed or stopped run holds only in its clone (#100).

### Fixed

- Of two claims on one item in the same seconds, the older one wins: a
  claim that finds a fresh mark of someone not yet assigned before its
  own waits a moment and reads again. Should both still win, a
  `pulse go` run checks its claim before each push; one that lost the item pushes nothing, opens no
  pull request, takes its claim back, and names who holds it. An
  interactive session hears it at its next sign of life, and
  `pulse beat` exits with 1 (#77).

- The review and the audit of `pulse go` start in a gate directory
  beside the worktree, with a fresh checkout of the pushed commit, and
  write their report next to that checkout, at the path the prompt
  names. They run git on that checkout as `git -C tree diff`, `log`,
  `show`, or `status`, the four forms their allow list adds, and the
  prompt names the diff, the spec, the PLAN, and the decision records
  from where the session starts. Nothing the builder left uncommitted or
  ignored reaches them, and a tracked `review.md` or `audit.md` stays
  as it is. The brief of both names changed agent instructions
  (`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.codex/`, `.agents/`,
  `.mcp.json`), a report counts only after the brief of this run, a
  link or FIFO is no report, and `pulse review --run` and
  `pulse audit --run` end the process group of their session (#36).

- Codex asks before `pulse release --drop-unpushed`, as before
  `release --take`: `pulse` takes `--drop-unpushed` only right after
  `release` (`pulse release --drop-unpushed <n>`), where a Codex rule
  sees it, and exits with 2 anywhere else; `--take` and
  `--drop-unpushed` never go together, and an agent of `pulse go` may
  not drop commits. The rules change: update Pulse in Codex, then run
  `pulse setup --codex-rules` again. The Claude Code rules in the
  installation tutorial ask there too; add
  `"Bash(pulse release *--drop-unpushed*)"` to the `ask` list of
  settings you copied from it before (#87).

- `pulse go` no longer builds on a spec branch named like the item's
  branch (`feat/563-chat-activity-spec`): a branch of the item that
  changes nothing but specs against the base branch, or nothing any
  more, is none to build on; the build starts on a new branch (#73).

- The map (`pulse map`, `pulse status`) and `pulse show` no longer pass
  escape sequences from titles, notes, errors, the presence log, the
  last run's report, or a plan's goal to the terminal: every character
  that is not printable shows as `?`, and a line of the map shows the
  first line of a text. Only the map writes colors and links, and a
  warning about a config line Pulse skips shows the line the same way.
  A confirmation (approve spec, approve plan, unapprove, merge, `g`)
  opens only where the terminal can show all it confirms, counting each
  character that is not ASCII as two columns; else the map asks for a
  larger terminal. While it is open, the map writes it again on every
  frame, so no line of the map can cover it. A goal in a confirmation
  takes one row, and `pulse show` keeps the lines of a note. A title
  with `›` no longer moves the view away from the picked row, the item
  view runs the row it shows, read spec says why it opens nothing on a
  path the system refuses, and wide characters (CJK) and spacing marks
  count by the columns a terminal draws them in, so a line that holds
  them keeps its width, and messages at the bottom wrap instead of
  losing their end (#56).

- An `Enter` within a second of `g` in the live map, or of the `Enter`
  on the `pulse go` line in NEXT that opened the confirmation, no
  longer starts `pulse go`: typed for another window, or the second of
  a double `Enter`, it closes the confirmation, and the footer says
  why. An `Enter` from a second on starts the run as before (#86).

- `pulse check` reads links (C1), code names in a decision record (C3),
  the Activation Path of a feature spec (C6), and the lines it counts
  toward a cap (C5, past comments that never close) in linear time. A
  prepared file of 40,000 characters cost 1 to 8 seconds on every
  commit, now it costs milliseconds, with the same findings. A link
  whose target itself holds `[` is no longer checked as a whole; a link
  inside it is. Findings print without control characters (#41).

- `pulse claim` and `pulse release` no longer name a spec branch as
  where the work is: the hint names only a branch on origin that
  `pulse go` would build on, fetched just now and quoted as a shell
  reads it, and none when origin has only the spec branch (#83).

- `pulse number --apply`, `pulse new --spec`, and `pulse claim` hold
  the refs git lists after every fetch against the commits origin
  names: a lock file left behind no longer reads as "origin did not
  answer", and a fetch that exits without an error but leaves a listed
  ref on another commit (on macOS, two branch names on origin that
  differ only in case) no longer counts as fetched. They print git's
  error, or the refs that differ. `pulse new` and `pulse number`
  refuse, and `pulse claim` names no start point, only when something
  they need is not as origin has it: `pulse new` its own branch, also
  one origin deleted; `pulse number` the history of a branch on origin,
  so a fetch cut short hands out no ID; `pulse claim` the base branch or
  a branch of the item. `pulse number` counts a branch whose ref git
  could not update through the commit origin names, and hands out no ID
  while git cannot read the history. `pulse status`, `pulse show`, and
  `pulse approve-plan` name what git said as well, and say that origin
  did not answer only when git said nothing. Still open for a follow-up:
  a twin such as `MAIN` that arrives beside an `origin/main` in
  `packed-refs`, which `pulse claim` does not see, and `pulse go` and
  the hint on where another holder's work is, which do not check the
  refs yet (#85).

- A pull request from a fork counts for an item only through its
  `Closes #n`, which GitHub links only in a pull request into the
  default branch. Merged from a branch named `feat/12-typo`, it no
  longer closes #12 at the next `pulse status` or `pulse go`, drops the
  claim of whoever builds it, or takes it off the map; merged into
  another base branch, it closes nothing, and `pulse done 12` closes
  the item. Nothing is built on a fork's branch: no feature stacks on
  it, `pulse go` takes up no fork's draft and leaves it out of the
  integration check, and no verdict goes onto it. A stack base comes
  from origin only, never from a local branch, tag, or commit of the
  same name. The integration check fetches each branch on its own and
  names one origin lacks instead of calling it a conflict. Branch names
  reach the start line of `pulse claim`, the build prompt, the branch
  lines of the run summary, and handover notes with control characters
  shown as `?` (#63).

- A session whose item a person took with `pulse release --take`
  hears it at its next sign of life, the heartbeat or `pulse beat`
  (which exits with 1), with who has the item now, also when it
  claimed the item, or registered it as a draft, and has waited
  since. It stops the work on the item and pushes nothing more of
  it, and the stop hook asks for no push of it. A session that gave
  its item back or never held it hears nothing, and a hand-over
  between two sessions of one person stays silent (#84).

- A review or audit verdict on a pull request counts only from someone
  who may push: the repository's owner, or a member or collaborator
  whose permission GitHub names write or admin, Enterprise Managed
  Users included. GitHub calls people with read access members and
  collaborators too, so a reader's marker could end the Stop hook's
  question for the gates, merge a pull request from the map or keep it
  from merging, and keep `pulse review --publish` from putting the real
  verdict on the pull request. When GitHub gives no answer (its rate
  limit, or the 403 for a login that cannot push), such a verdict
  counts for nothing, and while it is the newest of its gate, no older
  verdict counts in its place: the Stop hook names GitHub's reason and
  sends you to `gh auth status` and `gh auth switch` first, and the
  map merges nothing and shows the reason. A marker counts
  only on a line of its own, outside quotes and code blocks, and only
  in a comment of the owner, a member, or a collaborator, read in
  linear time; the Stop hook asks about each author once, and
  `--publish` never posts a verdict of your own login twice (#74).

- Handover, approval, and the map say and do the same (#99, with #90).
  After a take, the old session's stop hook asks for no push and no
  review or audit, since it reads who holds the item from the board at
  every stop; `pulse beat` reports a loss once and clears its notes,
  and names `pulse release <n>` after a lost race; `pulse release <n>`
  after a take says there is nothing to give back; a new session on
  another login's item hears who holds it; a draft names its docs
  branch as where the work is and where the next holder starts.
  `pulse approve` takes a later correction of a spec on the base branch
  along when one branch of origin changed it, and
  `pulse approve --claim` claims a feature, improvement, or fix for
  planning before it approves it, blockers aside, so no live map starts
  a run for the item the `/pulse-re` session plans. On the map every
  confirmation takes no `Enter` within a second of opening it and says
  `enter came within a second of opening it` (#90), and the item view
  opens on a reading entry. `merge` is offered only where it goes
  through: never for a fork's pull request, nor for one whose last
  commit lacks passing review and audit, where the line and NEXT name
  the missing runs; its confirmation says when `Enter` makes the pull
  request a draft again. What `pulse approve` cannot move is grey and
  counts nowhere, a row that waits for a slot says `queued`, read spec
  is offered only where the spec is, and an epic's approval says that
  its features are approved one by one. `pulse status` names
  `pulse go --detach` where the live map has `g`, `pulse show` prints
  the stage in the map's words, a teammate's waiting plan names whose
  it is, and the help names `j k`, Ctrl-C, and `?` as the one key with
  Shift. The help of `pulse beat`, `pulse claim`, `pulse go`, and
  `pulse check --spec`, and the preview of `pulse migrate` say what they
  do; the fake `gh` of the E2E scripts takes `pr ready --undo`.

## [0.1.5] - 2026-09-27

### Added

- The item view of the live map merges an item's finished pull request:
  merge is offered once the pull request is ready and targets the base
  branch, shows what it merges, and merges with Enter. The map reads the
  pull request again first and merges only one of this repository at
  the head the confirmation showed, without failing checks, whose gates
  passed on that head and none blocked it. A pull request with commits
  after the gates of pulse go is set back to draft, so the next pulse go
  runs its gates again. The action read PR opens the pull request in the
  browser, and NEXT sends a waiting merge to the item view instead of
  GitHub (#70).

### Changed

- The git hook refuses commits on the base branch too, the one
  `base_branch` in `.pulse/config.toml` names (without one, origin's
  default branch), beside `main`, `master`, `develop`, `dev`, or the
  list in `pulse.protected-branches`. A clone gets it with the next
  `pulse setup --git-hook` (#75).
- Approving a spec merges its spec pull request: `pulse approve <n>`
  and approve spec in the live map merge the one open pull request that
  carries the item's spec into the base branch, then approve the item.
  Nobody merges a spec pull request on GitHub any more. Pulse reads the
  pull request again first and merges only one of this repository
  whose merge into the freshly fetched base branch changes nothing but
  plain files under `_devprocess/`, and only the head whose spec passed
  R1 to R6 and that the map showed; a draft becomes ready first, and the
  item is approved once the spec is on the base branch. The confirmation
  in the map names the pull request and the other specs it brings along,
  which stay unapproved (#69).

### Fixed

- An open pull request that changes only files under `_devprocess/`,
  such as a spec, no longer counts as the pull request of the item its
  branch name names: the map shows no "waits for merge" for it, and
  `pulse go` stacks nothing on it (#62).
- The item view of the live map reads a spec that lies only on a branch
  of origin, such as one in an open spec pull request: its goal shows,
  and read spec opens a copy to read and names the branch. A spec in
  the working tree that differs from the base branch opens as the base
  branch has it. A spec path that leads out of the repository, or one
  that is no Markdown file, opens nothing (#68).

## [0.1.4] - 2026-09-26

### Added

- `pulse arch` builds an architecture map: every feature and decision
  record in its layer, and a page per feature, decision, and epic.
  `pulse arch --open` opens it. Pulse rebuilds it from the base branch
  after every merge while a live map or `pulse go` runs; it lives in
  `.git/pulse/` and is never committed. The layers come from
  `_devprocess/architecture-map.md`, each spec names its place with
  `layer:`, and `pulse check` (C11) reports a place the layers lack.
  Without layers the map groups the features by epic.

### Changed

- `--take` goes right after the command: `pulse claim --take <n>`,
  `pulse release --take <n>`, `pulse done --take <n>`. Anywhere else it
  exits 2 and names this spelling.

### Fixed

- Codex in Full access claims and gives items back again. The Codex
  rules ask only before `claim --take` and `release --take`, next to
  `approve`, `approve-plan`, `rank`, `done`, and `pulse -- <command>`.
  Update Pulse in Codex too, then run `pulse setup --codex-rules` again
  to rewrite them; it writes no rules while Codex runs an older Pulse.
  Where Codex refuses a command in Full access, the agent names it for
  your own terminal.
- An agent of `pulse go` claims, gives back, and blocks only the item it
  was started for (`PULSE_ITEM`); before, it could give back any item its
  run held.
- A claim or note mark counts only at the start of a comment, where
  Pulse writes it: a note or comment that carries one in its text no
  longer holds an item or its files.
- The header of the live map stays on top in a terminal lower than the
  map, wherever the cursor is, and the help stands under it too.
- An item whose pull request merged leaves the map at once, also when it
  merged into a branch other than the default one, and its epic counts it
  done; `pulse status` still closes it.
- The live map names each chat that waits for you. Under an item where
  several chats stand it counts the ones that ask and says what a working
  agent does there, and NEXT gives each asking chat a line of its own with
  agent, title, and how long it waits, the longest first. `Enter` on that
  line, or a click on it or on `need you`, opens the chat in VS Code; a
  chat in a terminal, the Codex app, Cursor, or VS Code Insiders says
  where it runs.
- A merged pull request that changes only files under `_devprocess/`,
  such as a spec, no longer counts as the build of the item its branch is
  named after: `pulse status` and `pulse go` leave that item open and the
  map keeps it. An item whose whole work lies under `_devprocess/` closes
  with `pulse done <n>`.

## [0.1.3] - 2026-09-25

### Changed

- A live map restarts itself with a newer Pulse within a minute of an
  update, in its own terminal. Once a day it asks for the newest release
  and names a newer one in its footer with the update commands for
  Claude Code and Codex; the next session names it too.
- A session in a project whose Pulse block is out of date has its agent
  run `pulse setup --anchors`, which rewrites only the block.
- The live map reads the board beside its keys, so a key never waits for
  GitHub. A write names itself in the footer while it runs, and the map
  then shows the board as the write left it.
- A draft someone writes stands only under its holder and counts as in
  progress; the ramp keeps the drafts nobody holds.
- The item view offers only what the item's stage allows, each with what
  it does: approve or unapprove, approve plan, read plan, prioritize (top
  of the ramp), and read spec. `q`, `Esc`, `←`, and Backspace go back on
  every level below the map, `→` opens an item, and `Esc` on the map says
  that `q` quits. Unapprove asks for `Enter` as the approvals do, and keys
  typed while a write runs are dropped. The map writes "plan" in lower case.
- A plan on a pushed item branch counts only as a Markdown file in the
  plans folder itself, as in the working tree.
- The installation page walks through an update step by step, for Claude
  Code and for Codex: getting the new version, loading it
  (`/reload-plugins` or a new chat), trusting the Codex hooks again when
  Codex asks, and what happens by itself. Claude Code users turn on
  auto-update for `pssah4-skills` once.
- The install script sets up the `pulse` command with the newest copy of
  both tools and names only the steps that are still open: the Codex
  hook trust only while Codex has none, auto-update once for Claude Code.

### Fixed

- The map shows an agent under the item its session holds, also when the
  session's directory has another item's branch checked out, and a Codex
  agent on the branch where its last command ran. Codex tells the hooks
  only its session's directory, so its work in another worktree showed
  under the wrong item.

## [0.1.2] - 2026-09-25

### Changed

- An item's plan is its PLAN file `_devprocess/plans/{n}-{slug}.md`. The
  anchor block `pulse setup` writes into the agent files says so, and so
  do the rules: a plan mode only shows the PLAN for approval, and a plan
  outside the repository does not count. The PLAN template gains the
  sections Not touched and Verification.
- A new session names each agent file whose Pulse block is out of date,
  and `/pulse-setup` writes it anew.
- `/pulse-realign` gives every epic and feature spec a record and, after
  one question, closes the records of code that exists in one `pulse
  done` call: the board holds only open work, and each epic counts its
  features as done. `pulse done` takes several numbers, and `pulse new
  --spec` creates nothing for a spec that has its record, so a stopped
  run goes on without duplicates.
- `/pulse-realign` delivers a basis to rebuild the product from: A1
  counts the entry points per kind, every observed behavior becomes a
  requirement with its source and its test, a success criterion carries
  the observed target, and the verification gate also checks code to
  spec and runs a rebuild reading with fresh subagents. The handoff
  reports in numbers and says "rebuildable" only when no inventory entry
  and no place of the rebuild reading stays open.
- On the map, `m` moves the picked ramp row and the map stays; its
  footer names the key. With color, each `#n` links to its issue in a
  terminal that knows links (VS Code, iTerm).

### Fixed

- The `pulse` command runs the Pulse of the agent that calls it: a Codex
  session its Codex copy, a Claude Code session its Claude Code copy, and
  a terminal of its own the newest of both. An older Pulse in Claude Code
  no longer stands in for a newer one in Codex, so each works without the
  other.

### Upgrading

- Run `pulse setup --cli` once more: it rewrites `~/.local/bin/pulse`.
- Run `/pulse-setup` once in each project: the anchor block now says that
  an item's plan is its PLAN file.

## [0.1.1] - 2026-09-25

### Added

- Logical IDs for specs. A spec's file name starts with its type, the
  numbers of its parent, and its own counter: `EPIC-04`, `FEAT-04-02`,
  `FIX-04-02-01`, `IMP-04-02-01`. A folder listing groups the features of
  an epic, and every ID names its epic and feature. The issue number
  stays the ID of the record.
- `pulse number` shows every spec whose file name lacks the ID of its
  place in the tree; `--apply` renames them, rewrites every path to them,
  puts the IDs into the epics' `## Items` lines, and moves the records
  along (an open record once the base branch has the new path). A new ID
  never repeats one that any branch, the history, or a worktree has used.
- `pulse check` rule C10 reports a spec without the ID of its place.
- `ids_since` in `.pulse/config.toml` lets a project number its specs
  anew from a commit, for example version 2 on the history of version 1.
- The installation page starts with one numbered sequence, from the
  prerequisites to `/pulse-setup` in a project, for Claude Code and
  Codex in the terminal and the VS Code extension; the README's quick
  start follows it.
- An optional install script:
  `curl -fsSL https://pssah4.github.io/pulse/install.py | python3 -`
  installs or updates Pulse with every tool it finds, also the binaries
  the VS Code extensions bring, writes the `pulse` command, asks before
  it changes your shell profile or writes the Codex rules, and removes
  nothing. `--dry-run` shows what it would run.
- The live map starts `pulse go` apart from itself when approved work
  waits and no run of this clone lives, so an approval, yours or a
  teammate's, starts the build without anyone typing `pulse go`. It
  starts only with the `.pulse/config.toml` that origin holds, never with
  the one of a checked-out branch, and what the last run did not finish
  waits for a person. `go_autostart = false` in `.pulse/config.toml` or
  `PULSE_GO=off` turns it off.

### Changed

- The new logo: the wordmark in the navigation of the documentation
  site and at the top of the README, the app icon as the favicon, petrol
  as the brand color, and a petrol-tinted dark mode. The landing page
  says what Pulse adds to GitHub, and its two diagrams follow the theme.
- The map shows the Pulse signet beside its header: in 256 colors as
  drawn, cyan in a terminal with 16 colors, plain without color.
- The installation page has one Update section: the commands for every
  tool, the install script, what to restart, and where a release names
  a step for your projects.
- The operating model and the review skill: a reviewer agent in a fresh
  session checks every pull request against its spec, PLAN, and
  decisions, and the person reads it at feature level and merges.
- `pulse new` puts the spec's ID in front of the record's title and its
  `## Items` line. An `## Items` line may stand without an issue number,
  for a shipped feature that has no record.
- `/pulse-realign` names the epic of every feature, shipped or not, and
  lists all features in their epic's `## Items`.
- A `pulse go` run reads `.pulse/config.toml` once, at its start: a
  branch checked out while it runs changes neither its `verify` nor its
  base branch.
- `/pulse-realign` and a Project-BA start with a draft on the board, as an
  Item-BA and `/pulse-re` do: the team and every map see the work from its
  first step, a heartbeat keeps it alive, and the draft closes once the
  work lives in its own records or the pushed BA.
- `pulse new --draft` refuses a title that an open draft of the same type
  has already and names that draft and who holds it, so two people
  cannot start the same realign or Project-BA.
- A Codex session whose Pulse hooks never ran hears so the first time it
  claims work: `/hooks` in the CLI, or the Hooks page of the IDE
  extension's settings, trusts them, and a new chat picks them up.
  `/pulse-setup` reports whether they are trusted.

### Fixed

- `pulse claim` refuses an item whose files another running item holds,
  as the ramp does, and names the file and the holder: a build started
  by hand with an item number no longer works on the same file as
  another item.

### Upgrading

- Run `pulse number --apply` once and commit the result; until then
  `pulse check` reports C10 for every spec. After the merge, run it once
  more so the open records link the new paths.

## [0.1.0] - 2026-09-25

The first public release. Pulse replaces the Digital Innovation Agents
plugin (DIA), whose last release was 4.0.2: the method stays, the
mechanics are rebuilt. The history of DIA stays with DIA.

### Added

- Pulse in three parts: an operating model for teams where each person
  works with several agents, collaboration on one shared board, and the
  Digital Innovation Agents as the method from a raw idea to reviewed code.
- Installation from the GitHub repository `pssah4/pulse` with each
  agent's own plugin commands, no npm package: Claude Code (terminal and
  VS Code extension) and the Codex CLI install the plugin with its hooks
  from the marketplace `pssah4-skills` (Codex asks once to trust the
  hooks in `/hooks`). The Codex IDE extension uses the plugin the Codex
  CLI installed; OpenAI does not promise this, so a test guards it and a
  clone without hooks stays the fallback. The same commands update and
  remove it. GitHub Copilot, Cursor,
  Gemini CLI, and OpenCode load the same skills and rules, untested end
  to end.
- `pulse setup --cli` puts a `pulse` command into `~/.local/bin` that runs
  the newest installed Pulse, so a plugin update needs no new setup.
  `pulse setup --codex-rules` lets Codex run `pulse` outside its sandbox
  and still asks before `approve`, `approve-plan`, `rank`, `done`,
  `release`, and `claim`. `--remove` takes both back.
- Slash commands: `/pulse` (where things stand, what comes next),
  `/pulse-ba`, `/pulse-re`, `/pulse-build` (test first, also tests for
  existing code and a red suite), `/pulse-audit`, `/pulse-go`,
  `/pulse-map`, `/pulse-setup`, and `/pulse-realign`. Planning and review
  run as steps inside the flow.
- The `pulse` command line (Python 3.9 or newer, standard library only):
  `status` prints where things stand once (`--json` gives its data),
  `show`, `approve`, `approve-plan`, `rank`, `go`, `map`, `setup`,
  `release`, and `done`. The commands for skills and hooks (`claim`,
  `new`, `beat`, `block`, `review`, `audit`, `check`, `migrate`) have
  their own group in `pulse --help`.
- Specs in the repository, state on the board: every epic, feature,
  improvement, and fix is a Markdown spec in `_devprocess/`; its state
  (approved, taken, blocked, done) is a small record on GitHub that only
  `pulse` writes, read from a local cache. `pulse new --spec` records an
  item only once its spec is committed and pushed, and `pulse approve`
  refuses while the spec is not on the base branch.
- Specs an agent can plan from: scope with what is out, numbered
  requirements in EARS form, assumptions, open questions, and risk flags.
  `pulse check` applies the rules R1 to R6 to every approved item's spec
  and C1 to C9 to the documents; offline it says R1 to R6 were not
  checked and blocks nothing.
- `pulse go` plans and builds every approved item in parallel, one
  worktree and one headless agent (Claude Code or Codex) each, in the
  team's order from `pulse rank`; two items that touch the same files do
  not run at the same time. An item without a PLAN is planned first, and
  a PLAN that fails the plan gate (P1 to P5) gets up to two fix rounds.
  With `plan_approval = "auto"` a PLAN nothing holds is built; a risk
  flag, effort L, `needs:`, or `manual` waits for `pulse approve-plan`.
  `pulse go` does not start without a `verify` command. `--detach` runs
  it apart from the terminal, for example overnight;
  `.git/pulse/go/report.json` keeps every result as it happens, and
  `pulse status` names the last run.
- Spec tests first: one test per requirement, committed alone and frozen
  before the build. `pulse go` checks the frozen lines after every build
  and fix round, and checks RED itself: the tests must fail at the commit
  that froze them, or the pull request says so.
- Three gates after every build: the project's tests (`verify`), a
  review, and a security audit, the last two in fresh sessions. What an
  agent left uncommitted is committed before the gates, so all three
  judge the same commit. A red gate gets up to two fix rounds. One pull
  request per feature, ready when all three passed and a draft with the
  reasons otherwise; a feature whose blocker has a ready pull request
  stacks on the blocker's branch. A draft of `pulse go` that gets a new
  commit is taken up by the next run. At the end of a run with two or
  more ready pull requests, their branches are merged in dependency
  order in a scratch worktree and `verify` runs on the result.
- The security audit in the chain stands on a scan that Pulse runs
  itself. Dependency advisories come live from the OSV API, the only
  source for npm, PyPI, Go, and crates.io; without network the scan says
  `offline` instead of a clean result. An audit report without a
  `Coverage:` line, without a scan of its commit, or with a pass while
  the OSV lookup failed and the report does not say so gives no verdict.
  The bundled references carry an `as-of` date, and the brief and the
  report warn once one is 90 days old or has no date.
- Gate verdicts travel with the pull request: `pulse review` and
  `pulse audit` put them on the item's open pull request (`--publish` for
  the ones kept before it existed), so whoever takes the item over in
  another clone need not run the gates again.
- After every phase, `pulse go` compares the git config, the git hooks,
  and the files that tie a worktree to its repository with their state
  before. An agent that changed one of them stops its item: nothing is
  pushed, the claim stays, and the report names the files for a person
  to look at.
- Running and early work visible through the board: a claim names its
  phase and the time of its last sign of life, from `pulse go` at every
  phase and from an interactive session every ten minutes at most
  (`pulse beat` for skills); after 30 minutes without one the map says
  "no sign of life". `/pulse-ba` and `/pulse-re` work on a draft record
  (`pulse new <kind> <title> --draft`, label `pulse:draft`) that shows as
  "spec in progress by <login>"; `/pulse-re` checks the open drafts and
  items for overlap first, and `pulse new --spec <path> --issue <n>`
  attaches the spec to the draft.
- Work changes hands with its code: `pulse go` pushes the item branch
  after every agent phase that committed, and a run that fails, hits a
  usage limit, or stops gives the item back with a note (reason and
  branch) that the map shows; the next holder builds on that branch.
  `pulse release <n> --take` hands over another person's claim,
  `pulse claim <n> --take` takes over from an ended session of your own,
  and `pulse approve --undo` takes an approval back.
- Pulse stops for a person only at the business analysis, each spec
  (`pulse approve` means build it), a PLAN that something holds, and the
  merge of each feature's pull request.
- An item belongs to the session that claimed it; another session is
  refused, also under the same GitHub login.
- The live map in the terminal, `pulse map` (`pulse status` prints one
  frame): who works on which item and in which phase, what goes out
  next, what failed, and what waits for you; a working agent's light
  breathes. Arrows or `j`/`k` select, `Enter` opens an item with its
  goal, stage, holder, blockers, pull request, and PLAN; there `a`
  approves it, `p` approves its PLAN after showing what that binds, `o`
  opens the spec in your editor, and `m` moves it in the team order
  (arrows, then `Enter`). `Esc` goes back, `?` shows the keys, `q` quits.
  `/pulse-map` opens it in a tmux pane beside the chat or names the
  command for a second terminal, and `/pulse-setup` offers a VS Code and
  Cursor task for it.
- Hooks in every session and subagent: the rules and the active item at
  the start, one reminder when code changed without a check, one when a
  pull request's last commit has no review or audit (Claude Code), and
  presence events for the map from Claude Code and the Codex CLI.
- An optional git hook refuses commits on protected branches and commits
  with `pulse check` findings.
- `/pulse-realign` and `pulse migrate` take over a DIA project: settings,
  anchor blocks, frontmatter, and the old `BACKLOG.md` as records on the
  board. A project that enabled the DIA plugin switches to Pulse when it
  is installed.

### Changed from DIA 4.0.2

- Skills renamed: `business-analysis` to `pulse-ba`,
  `requirements-engineering` to `pulse-re`, `architecture` to
  `pulse-plan`, `coding` and `testing` to `pulse-build`,
  `security-audit` to `pulse-audit`, `dia-setup` to `pulse-setup`,
  `dia-realign` to `pulse-realign`, `dia-guide` to `pulse`.
- Settings move from `.dia/config.toml` to `.pulse/config.toml`
  (`mode = "on" | "off"`); the old file is still read as a fallback.

### Removed from DIA 4.0.2

- `BACKLOG.md` as the state store, commit trailers, phase tags, and the
  three modes.
- The skills `consistency-check` (now `pulse check`), `dia-bootstrap`,
  `project-conventions`, and `humanizer`, and the Copilot agent files
  under `.github/`.

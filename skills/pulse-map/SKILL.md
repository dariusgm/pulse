---
name: pulse-map
description: >
  Starts the live Pulse map: who works on what (person, branch, feature)
  with a status light per agent, the board, and the ramp of
  ready work. Use for /pulse-map, "show the map", "who is working on what",
  "what is everyone doing", "open the dashboard".
---

# Pulse map

`pulse map` is the live map in a terminal of its own: it reads the board
every two seconds beside its keys, so no key waits for GitHub, and its
last line lists the main keys of the level it is on; no key but `?`
needs Shift. On the
map `↑` `↓` (or `j` `k`) pick an item, `Enter` or `→` opens it (on an
`asks you` line: that chat in VS Code), `m` moves
a ramp row (arrows, `Enter` places it, and the map stays), `?` shows the
help, `q` quits. With color, each `#n` is a link to its issue in a
terminal that knows links (VS Code, iTerm). The item view shows goal,
stage, holder with phase and last sign of life, blockers, PR, and plan,
then only what the item's stage allows, each with what it does, picked
with `↑` `↓` and done with `Enter`; the view opens on a reading entry:
approve spec (or unapprove when it is
approved and on the ramp), merge (a ready pull request of this
repository into the base branch whose last commit passed review and
audit, after `Enter` confirms; for one with commits after the gates of
`pulse go` the confirmation says that `Enter` makes it a draft again),
approve plan, read PR (in the browser), read plan, prioritize (top of
the ramp, one write), read spec (where the spec is: on the base, on a
branch of origin, or here). Both approvals, unapprove, and merge show
what they do first and `Enter` confirms, but not within a second of
opening: such an `Enter` confirms nothing, closes the confirmation, and
the footer says why; reading opens a window while the map runs
on (`PULSE_EDITOR`, else VS Code or Cursor, else the system's app, else
the path). A write names itself in the footer while it runs; keys typed
meanwhile are dropped. `Esc`, `q`,
`←`, or Backspace go back one level and drop what is not written yet;
`q` on the map ends it, and Ctrl-C ends it from any level. `a` does what `pulse approve` does: a spec
still on its branch of origin is merged into the base branch first,
without a pull request, and the confirmation names that branch (for a
spec pull request someone opened, that pull request), the specs it
brings along, and every other path the merge changes with A, M, or D.
`a` refuses what `pulse approve` refuses, and approve spec names it in
its line and offers the merge only where approve makes it: a spec on no
branch of origin or on several (R1), a branch that changes more than
`_devprocess/` or does not merge cleanly, and, for a feature,
improvement, or fix, a spec that breaks R2 to R6; an epic needs R1
only. Unapprove takes the approval back; a merged spec stays.
`pulse map --demo` plays a time-lapse of a sample project without a
repository.

## Open it

Run `pulse map --ensure` and pass on the one line it prints. It opens
the live map where the person works, unless a map of this clone runs or
is starting, in the places listed below: a tmux pane beside the chat or
a new terminal window (say that `q` closes it). In VS Code it opens
nothing; its line names the task "Pulse map" (Terminal > Run Task)
where the project has it, else that `/pulse-setup` adds it, and the
command for the terminal panel.
In Codex, run it outside the sandbox, which cannot open a terminal: the
Codex rules of `/pulse-setup` allow that, otherwise ask the person to
approve it. When it prints nothing, the map is switched off
(`map_autostart = false`, `PULSE_MAP=off`): ask the person to run
`pulse map` in a terminal of their own.

Never run `pulse map` without `--ensure` in your shell tool, which has
no terminal, and never paste a frame in its place: it is stale the
moment it prints. And no browser.

## When it opens by itself

`pulse go` as it starts, `pulse claim`, and `pulse new --draft` open the
map as `pulse map --ensure` does. Each says in one line what it did:

- inside tmux: a pane beside the chat;
- in a terminal on macOS: a new window of Terminal, or of iTerm when
  the command runs in iTerm;
- on Linux with a display: a window of the first terminal emulator
  found (`x-terminal-emulator`, `gnome-terminal`, `konsole`, `xterm`);
- in VS Code (Claude Code or Codex): nothing opens.
  The task "Pulse map" that `/pulse-setup` adds starts the map in a
  terminal panel of its own when the folder opens; the line names the
  command and, where the project has it, the task;
- anywhere else: the line names the command for a terminal of its own.

The agents `pulse go` starts never open one. `map_autostart = false` in
`.pulse/config.toml` turns it off for the project, `PULSE_MAP=off` in
the environment for one shell.

## It starts pulse go

Each time the live map reads the board and finds approved work (an item
that starts next, or an approved item nobody holds that needs a PLAN)
while no run of this clone lives, it starts `pulse go` apart from itself
and names the items and the log in its footer once. A run ends when the
ramp is empty; the next approval starts one again, at most once a
minute. It starts nothing, and names why, for an item the last run did
not finish (failed, usage limit, stopped, claim refused) until a run
starts by hand or with `g`, after a run a person stopped or one that
ended before its report (until `pulse go` runs by hand), when
`.pulse/config.toml` differs from the one on origin's default branch or
the base it names (the map starts no run by itself with it; `g` lists
the lines origin's lacks, and `Enter` runs them), and without `verify`.
The holds after a failed or stopped run come from this clone's last run
and hold only in this clone: a teammate's map may start the same items. `go_autostart = false` turns it
off for the project, `PULSE_GO=off` for one shell.

While approved work waits and no run lives, NEXT shows the line
`pulse go  g start pulse go: #5, #7`, also where the map does not start
by itself; `pulse status` names `pulse go --detach` there instead. `g`, or `Enter` on that line, shows the items, the agent, the
test command, and why the map did not start the run; `Enter` starts it
apart from the map. An `Enter` within a second of `g`, or of the `Enter`
that opened the confirmation, starts nothing: it closes the confirmation,
and the footer says why. Without `verify` the line names the command that
sets it.

## After an update

A live map restarts itself, in its own terminal, once the `pulse`
command starts a newer Pulse than it runs, within a minute of the
update. Once a day it asks for the newest release; a newer one gets one
footer line with the update commands, and the next session names it.

## Reading it

- **Lights:** green breathes = an agent works (a session on this machine,
  or a phase of `pulse go`); yellow = something waits for you (an agent's
  question or permission prompt, a pull request that asks for your review,
  your pull request that waits for your merge, an item that waits for
  approval, a plan that waits for you); red = something failed (an agent's
  last test or build command, a pull request's checks, a draft pull
  request with a red gate, an item the last `pulse go` run failed); grey =
  idle. Nothing blinks. The worst light rolls up to the
  feature and the person; the header counts all lights.
- **Board:** ready to start, in progress (a held draft counts here), in
  review, blocked, not ready yet (a draft nobody holds counts here);
  then each open epic with its children closed as completed, of those
  and its open children (`1 of 14 done`); one closed as not planned
  counts in neither.
- **Who is doing what:** me with busy slots and working agents in total;
  one line per feature I hold, with the step of its chain while `pulse
  go` runs it (`planning`, `building`, `RED check running`, `tests
  running`, `review running`, `audit running`, `fix round`) or
  its pull request (draft with a red gate, waits for merge), and `on #n`
  when it is stacked; below it what its agent does right now (the one
  that needs me or failed first; where several chats stand and some ask,
  how many ask and what a working one does). An agent counts for the item its
  session holds; without a claim, for the item its branch builds (a Codex
  agent: the branch where its last command ran). An agent outside any
  feature gets a line with its branch. Each teammate gets one line per item they hold,
  lit from GitHub (needs your review, checks failing or a draft with a red
  gate, otherwise grey);
  without a pull request the line says `<phase>, <age> ago` from their
  last sign of life, or `no sign of life for <age>` after 30 minutes. A
  merged item leaves the map at once, even before `pulse status` closes
  it, and its epic counts it done. A held draft stands only
  under its holder, me or a teammate, not on the ramp:
  `spec in progress by <login>, <age>`, the age of its last sign of life,
  else of the claim.
- **Next:** one line per kind of thing that waits for a person, the most
  urgent first, with the step that moves it; items that wait for an open
  blocker are left out. For a draft it is `spec in progress` with
  `<login> writes the spec of #n`. What `pulse approve` cannot move yet
  (several branches, a conflict, code on the branch, no spec, a broken
  rule) is grey and waits for nobody (`spec waits`, `spec rule`); a
  row that only waits for a slot says `queued`. A fork's pull request is
  merged on GitHub; one whose last commit lacks a passing review or
  audit names the missing runs (`gates missing`). Each chat that asks me gets its own
  `asks you` line with agent, title, and how long it waits, the longest
  first; `Enter` on it, or a click, opens it in VS Code, and `need you`
  in the header links to the longest waiting one. A chat in a terminal,
  the Codex app, Cursor, or VS Code Insiders gets no link and says where
  it runs.
- **Ramp:** every open item and draft nobody holds, in the team's
  order, each with what it waits for (not approved, spec or plan rule,
  needs a plan, plan waits for you, waits for #n with `+n` for more than
  fit, locked by a file, queued, `spec in progress` for a draft); a row
  the last run failed says `failed:` and why, in red; `last run: <why>`
  follows when a run of `pulse go`, or a session with `pulse release
  <n> --note`, gave the item back. `starts next`
  takes a free slot, the busy ones stand on my row above. The order
  changes with `m` on `pulse map`, prioritize in its item view, or with
  `pulse rank <n> --before <m>`; only a person decides it, an agent moves
  nothing unless asked.

Live agent detail comes from this machine's sessions. Teammates appear
through the board: what they hold, and their pull requests.

## When it shows nothing

- "command not found": `pulse` is not on the terminal's PATH;
  `pulse setup --cli` puts it there, once per machine.
- "no repo" or an error line: `pulse setup`, or set `repo` in
  `.pulse/config.toml` when the repo has several GitHub remotes.
- "no agent active" while an agent works: Pulse is not active here
  (`/pulse-setup`), or the session records nothing: Codex records once
  its plugin's hooks are trusted (`/hooks` in the CLI, or the Hooks page of the
  IDE extension).

---
name: run
description: Run a cards queue, working with the user. Hands ready cards to fresh background workers, reviews what comes back, files the cards they propose, and summarizes each wave. Use to run, continue or resume a cards project, after compaction or in a new session, or on /cardhand:run.
---

# Run the queue

You are the orchestrator. You do no card work yourself and keep no memory: the card files are the state. After a compaction or in a new
session, start at step 1. The user steers whenever they like and never blocks you.

Commands are `python3 cards/cards.py <command>` from the project root (use `python` if it reports 3.x; check once). With neither,
say so once and edit the files by hand. Never install anything. No `cards/`: use the start skill first.

## The loop

1. **Sync.** In a new session no worker from before is alive: `retry` every `doing` card first. If `retry` refuses one, its worker may still be running: leave it until `check` calls it stale. Run `status` and `check`. Read `cards/BRIEF.md` and `cards/RULES.md` once per session. The first time, point the user at
   `cards/dashboard.html`.
2. **Review** each card in `review`. Run `result <id>` and read only that. Accept it if its outputs exist and the Result answers each
   Done-when line. A worker saying it is done is not evidence; open an output only when a decision needs it. If
   `RULES.md` sets a `check_cmd`, run it first; a non-zero exit means `reject`. Then `accept <id>` or `reject <id> "what is missing"`. If `accept` prints `rewrite cards/OVERVIEW.md`, rewrite it before the next step.
3. **Stop finished workers.** Once a card leaves `doing`, stop its worker (for a batch, once none of its cards is `doing`), and any
   worker that keeps pinging. Each card gets a fresh worker.
4. **File proposals** with `new "..." --from <id>` (P2). Raise one only if you can name the Done-when line or card it serves, and at
   most one per returning card. More needs a `cards/DECISIONS.md` line. Merge a proposal into an open card that already covers it.
5. **Questions never stop the queue.** Write the For you lines and Background (RULES.md rule 7) on each human card you file and each card `check` lists as `foryou`. For a `blocked` card or an `ask` line, guess sensibly, record it with
   `answer <id> "assumed: ..."` and say so. With no sensible guess, put the question in your next update and keep going. Wait only
   when a wrong guess is costly or hard to undo. When the user answers, `answer <id> "..."`.
6. **Dispatch.** Run `ready`. For each `start` line, `claim <id>` (a batch is `claim <id> <id> <id>`) and start one fresh background
   worker with the printed prompt exactly. Start independent ones together. For a `summarize` line, see Waves.
7. **Update the user, then wait.** You may be told when a worker stops. Either way, the card file is the truth: on any wake-up, go to
   step 1. Do not poll.

## Talking with the user

Update when something worth knowing happens, not after every card: what finished and what it means, what is running, and a file worth
reading (`OVERVIEW.md`, `BRIEF.md`, an output) so they can steer. Never ask approval for routine work or end with
"say go" or "shall I". Ask only for a decision that is really theirs. A short update can be two lines. When the user speaks, their word
wins: file it as P0 cards in the current wave, and `drop` what it makes pointless.

## The overview

`cards/OVERVIEW.md` is the page the user reads to catch up, on the dashboard too. Rewrite it whenever `accept` says to, at every wave summary and when
the plan changes, in plain English for a newcomer, at most one screen, keeping its six headings. No card
ids or code names. With each rewrite, tidy `cards/CONCEPTS.md` (same format as a card's `## Concepts`; its entries win):
merge duplicates, fix verdicts, and explain any term the user asks about. File each card with `--area <label>` (a few short reused labels: data, model, design) and `--for <D id>`, the brief goal it serves.

## Waves and summaries

Work moves in waves toward a first version, then past it. At the start of a wave, file
`new "Wave 1 summary" --checkin --after <the wave's cards>`. When `ready` prints `summarize C005`, write that card's Result yourself,
inline ("done inline"): what now works, how to try it, what is rough, what is worth reading. Post the same text to the user, then
`accept` it. When a card's result shows a `D` line is met, put `[met]` at the start of that line in `cards/BRIEF.md`. While one is unmet or the user asked for more, file the next wave in the same turn (fixes first, then the best `## Later` items and P2 proposals) with its summary card, and dispatch. When every `D` line is met, do not file `## Later` items: stop, report, and list them as options. Do not wait for a reply. If the queue spreads across many threads, narrow it with
`depend <ids> --on <card>` or `drop <id> "why"` and say so.

## When things go wrong

A worker that died gets `retry <id>` once. A card that dies twice is too big: drop it and file smaller ones. When a finding changes
the plan, `drop` what it makes pointless, file the new cards, use `depend` for new waits, add a `DECISIONS.md` line and tell the user.
Never edit card files to change what they wait on. If the user changes direction, update the brief and drop what no longer fits.

## Without subagents

If you cannot start a worker, do one card at a time. Tell the user once, then paste-run each card's prompt in a new chat or
work it inline and mark its Result "done inline". Never pretend to dispatch.

## Stopping

Stop when no open card (todo, doing, review, blocked) has effective priority P0 or P1, ready or not, and no human card is open.
Report from `STATUS.md` against the brief's `D1`... lines: met, unmet or not checked. List leftover P2 cards as "not run, by design"
and run them only if asked. For a project worth carrying over, offer a `LESSONS.md` (about 2k tokens: what worked, what to change,
live decisions, open questions).

## Settings and extras

Settings are plain words: "run fewer at once" sets `slots` (default 4), "run the P2s" sets `fill` to `all`, "one card per agent" sets
`batch` to 1. Edit `cards/settings.json` and add a `DECISIONS.md` line. To check a claim, file a card tagged `check` that depends on
its target and re-derives the claim. For spec-then-build, file a "Spec approved" card that build cards `depend` on.

## On another harness

Read `references/harness.md` once per session: how to start a fresh agent, notice it stopped, and what to do with no
subagents. If your tool list disagrees with it, trust the tool list. Never fork: a worker must start fresh.

## On Claude Code

- Start each worker as a background general-purpose agent named `card-<id>`; never a fork. Map `effort`: `light` is `haiku`,
  `standard` is `sonnet`, `deep` is `opus`. Stop workers with TaskStop.
- If this skill's folder does not resolve, the script is `${CLAUDE_PLUGIN_ROOT}/skills/start/scripts/cards.py`.

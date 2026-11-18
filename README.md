# cardhand

Run any job as a queue of cards. A fresh agent does one card, writes the result to disk, and exits.
The queue grows as the work teaches you things.

Install it in Claude Code:

    /plugin marketplace add rajaxar/cardhand
    /plugin install cardhand@cardhand

Then, in any folder:

    /cardhand:start find out why our nightly export is slow    # one-line idea: it posts its plan and starts
    /cardhand:start specs/migration.md                         # you already have a spec: it slices it into cards
    /cardhand:run                                              # works the queue; run it again after a break or in a new session
    /cardhand:status                                           # what needs you, what is running, what was learned

![The cardhand dashboard, Overview tab, rendered from the bike-share example](docs/dashboard-overview.png)

*The dashboard's Overview tab, from `examples/bike-share/` (invented data).*

You get a `cards/` folder: a brief, one Markdown file per card, and generated views. Close the laptop.
Next week, `/cardhand:run` reads the files and carries on.

## Try it in 30 seconds, no model needed

The example is a finished first wave of a small data job. In a clone of the repo, copy it to a scratch folder,
let the script build the views, and open the dashboard:

    git clone https://github.com/rajaxar/cardhand && cd cardhand
    cp -R examples/bike-share /tmp/bike-share
    python3 skills/start/scripts/cards.py --dir /tmp/bike-share/cards status
    open /tmp/bike-share/cards/dashboard.html        # xdg-open on Linux

This runs only the standard-library script. It calls no model and costs no credits.

**Good for:** research, data digging, long jobs where the plan changes as you learn.
**Weak fit:** one-shot edits (just ask), and pure feature work where a coding-methodology plugin already fits.
**No required process.** Cards need no reviews, specs or phases. Add checks where a job needs them.
**No runtime beyond Python 3** (standard library) for the queue script. Without it, the files can be edited by hand.

## Where it runs

cardhand runs in Claude Code, Codex CLI, Cursor and Copilot CLI. Each loads the same `skills/` tree from the portable
`plugin.json`, and `skills/run/references/harness.md` tells the orchestrator how to start and watch a fresh worker on
that harness. OpenCode and any harness that edits files can run the queue from a clone: the cards and the script are the
protocol.

    # Codex CLI
    codex plugin marketplace add rajaxar/cardhand
    codex plugin add cardhand

In Cursor or Copilot CLI, add `rajaxar/cardhand` as a plugin marketplace and install `cardhand`. On OpenCode, run the
queue from a clone with `skills/run/SKILL.md`.

## Run it from a local copy

For development, or to try a checkout without adding a marketplace:

    claude --plugin-dir /path/to/plugin

## What a card looks like

A card is a Markdown file. This one is from `examples/bike-share/`, with the bookkeeping fields trimmed:

```
---
id: C002
title: Monthly trip counts per dataset
status: done
depends_on: [C001]
spawned_by: human
---
## Do
Count trips per month for each dataset over the shared twelve months, and put them in one table.
## Result
Every dataset has its busiest month in summer and its quietest in winter, though Lakeside is flatter than the other two.
## Proposed cards
- Align the trip definition across datasets (Northgate counts short test rentals).
```

The worker wrote the Result and the proposal. The orchestrator read the Result, accepted the card, and filed the
proposal as a new card (`C005`, which says `spawned_by: C002`). Line 1 of a Result is the answer, in one sentence.
The full folder, including a dropped card and a "Ruled out" answer, is in `examples/bike-share/`.

## Two ways to start

| You have | You type | It does |
|---|---|---|
| One line | `/cardhand:start compare three bike-share datasets for seasonal patterns` | Reads what it can, posts one screen (how it read the ask, the first version, assumptions, the first wave), then starts the first wave in the same turn. It does not wait for a reply and asks no questions first. Redirect it at any time |
| A spec, checklist or task list | `/cardhand:start specs/migration.md` | Makes one card per open item, keeps the source as an input, and starts |

A tiny job is done directly, with one sentence and no files. Say "cards" if you want it tracked anyway.

## What it puts in your project

```
cards/
  BRIEF.md       goal, done when, not doing, unknowns, ideas for later
  RULES.md       what every worker must follow; add your own project rules at the bottom
  OVERVIEW.md    the orchestrator's plain-words summary, shown first on the dashboard
  STATUS.md      generated summary
  dashboard.html live view: open it in a browser, it refreshes itself
  status.json    the same data, for your own tools
  cards.py       the queue script (standard-library Python 3.7 or later)
  queue/         one Markdown file per card
  scratch/       one folder per card for its output files
  view/          generated pieces of the dashboard
```

`DECISIONS.md` and `settings.json` appear when first needed. If you use git, commit `BRIEF.md`, `RULES.md`, `OVERVIEW.md`,
`DECISIONS.md`, `queue/` and `scratch/`. Ignore `view/`, `status.js` and `status.json`, which are regenerated.

The dashboard updates whenever the orchestrator touches the queue, because the script rebuilds its data on each command.
A worker's progress shows up at the next command, not the instant it is written.

Add your own rules at the bottom of `RULES.md`. One line is enough to turn on a test gate, for example `check_cmd: pytest -q`:
the orchestrator runs it before accepting a card and sends the card back if it fails.

## Optional checks

Independent re-checks are off by default. If a job needs them, copy `recipes/checks.md` from this plugin to `cards/recipes/checks.md`
and add this line to `cards/RULES.md`: `Cards tagged check: follow cards/recipes/checks.md.`

## How the queue is served

A card is ready when everything in its `depends_on` is done or dropped. Ready cards run highest
priority first. A card counts as high as anything waiting on it, and ties go to the oldest card.
Cards proposed by workers start at P2. The orchestrator moves the most useful ones into the next wave itself, and the rest wait until you ask.
The run skill is meant to stop when the brief's "done when" lines are met; this stop is untested in a live run.

Work moves in waves toward a first version, then the next. At the end of a wave the orchestrator posts what
works and files the next wave itself. Your feedback, whenever it comes, goes to the top of the queue.

## The cost of having it installed

Idle, the plugin adds under 1 KB of skill names and descriptions (about 680 bytes), which is an estimate of about 170 tokens
(characters divided by four, plus or minus 30%). A skill body loads only when you use it.

One card dispatch reads about 3.3 KB of the plugin's own text (the prompt, `RULES.md`, the card and its inputs), an estimate of
roughly 830 tokens, or about 0.5k–1.1k with the ±30% and normal card-size variation. Your own card inputs are extra and can be
much larger. These are static estimates, not measurements from a live session.

## Where it fits

| Tool kind | What they do well | Where cardhand differs |
|---|---|---|
| Long chat sessions | Everything in context, nothing to set up | cardhand keeps the plan in project files, not in the chat |
| Methodology plugins for coding | Plans, test-first, review, polished skills | cardhand has no required process and is not tied to software |
| Task-graph tools | Many concurrent agents, atomic claims | cardhand is Markdown plus one script, with no database |
| Native agent task lists | Built in, with dependencies | cardhand is plain files that are meant to outlast a session |
| Unattended loops | Grind until a spec is done | cardhand keeps going on its own, but is meant to stop when the brief's "done when" lines are met and report what it learned |

This reflects a limited search of public projects. Check the current state of each before you choose. Do not
read the table as a ranking.

## What is tested

The queue script runs a full throwaway lifecycle (create, claim, result, accept, reject, drop), and the plugin passes
`claude plugin validate`. The package loads on Claude Code, Codex CLI, Cursor and Copilot CLI from the same manifest.

Open: a live orchestrator and live workers running v1 end to end; the dashboard on a real run (checked in screenshots
during development); resuming after a real compaction; a non-software job from start to finish; batching of small cards.
The first real run is the test; tell us what drifted.

## The script

`python3 cards/cards.py --help` lists the commands. You can run the queue by hand with them:
`init`, `new`, `depend`, `ready`, `claim`, `result`, `accept`, `reject`, `retry`, `answer`, `drop`, `priority`, `check`, `status`.
Without the plugin, you can use just this script and the card files.

## Run the checks

    PYTHONDONTWRITEBYTECODE=1 python3 tests/check.py

It runs seven free checks (a throwaway queue lifecycle, lints, name and version, idle-size budget, no stray files, and
`claude plugin validate`). The last one is skipped if the `claude` command is not on your path. No model is called.

Every push runs these in CI; `validate` is skipped there, so CI covers six of the seven.
[![checks](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml)

## Portability, license, changelog

Portability: see the top of this page. License: MIT (see `LICENSE`). Changes: see `CHANGELOG.md`.
Bugs and ideas: open an issue and say which harness and version you ran.

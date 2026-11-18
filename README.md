# cardhand

Run any job as a queue of cards. A fresh agent does one card, writes the result to disk, and exits.
The queue grows as the work teaches you things.

You don't need to write code. Install it once, describe the job in chat, and steer when it asks.

## Install

Install cardhand once for each harness you use. The same `skills/` tree loads from the portable `plugin.json`, and
`skills/run/references/harness.md` covers how the orchestrator starts and watches a worker on each.

### Claude Code

    /plugin marketplace add rajaxar/cardhand
    /plugin install cardhand@cardhand

### Codex CLI

    codex plugin marketplace add rajaxar/cardhand
    codex plugin add cardhand

### Cursor and Copilot CLI

Add `rajaxar/cardhand` as a plugin marketplace, then install `cardhand`.

### OpenCode

Clone the repo and point the agent at `skills/run/SKILL.md`: the cards and the script are the protocol.

For local development, use `claude --plugin-dir /path/to/plugin`.

## Use it

In Claude Code, from the folder you want to work in:

    /cardhand:start find out why our nightly export is slow
    /cardhand:run
    /cardhand:status

You can also start from a spec, checklist or task list:

    /cardhand:start specs/migration.md

It posts a short plan, starts the first wave in the same turn, and does not wait for a reply. A worker can propose a new
card and the orchestrator files it, so the queue grows from the work. At the end of a wave it posts what works, how to
try it, and what is rough. Answer in chat; your feedback goes to the top of the queue. `/cardhand:status` shows what
needs you, what is running and what was learned. Open `cards/dashboard.html` for the same view in a browser.

A tiny job is done directly, with one sentence and no files. Say "cards" if you want it tracked anyway.

![The cardhand dashboard, Overview tab, rendered from the bike-share example](docs/dashboard-overview.png)

*The dashboard's Overview tab, from `examples/bike-share/` (invented data).*

**Best for:** research, data digging, long jobs where the plan changes as you learn.
**Not for:** one-shot edits (just ask), and pure feature work where a coding-methodology plugin already fits.
**No required process.** Cards need no reviews, specs or phases. Add checks where a job needs them.

You do not run the queue script. The agent does. The cards are Markdown if you want to read or edit them.

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

## What it creates

One `cards/` folder: `BRIEF.md` and `RULES.md` (the plan and the rules), `OVERVIEW.md` (the plain-words big picture), one
Markdown file per card in `queue/`, one output folder per card in `scratch/`, `cards.py` (the queue script), and a
self-refreshing `dashboard.html`. `STATUS.md`, `status.json`, `status.js` and `view/` are generated. Commit the Markdown
and `scratch/`; ignore the generated files.

Add your own rules at the bottom of `RULES.md`. One line turns on a test gate, for example `check_cmd: pytest -q`. For
independent re-checks, copy `recipes/checks.md` to `cards/recipes/checks.md` and add the line it shows.

## How the queue works

A card is ready when everything in `depends_on` is done or dropped. Ready cards run by priority, then oldest first. A
worker can propose a new card and the orchestrator files it, so the queue grows from the work. Work moves in waves: at
the end of a wave the orchestrator posts what works and starts the next.

## The cost

Idle, the plugin adds about 680 bytes of skill names and descriptions, about 170 tokens. A skill body loads only when you
use it.

One card dispatch reads about 3.3 KB of the plugin's own text: the prompt, `RULES.md`, the card and its inputs. That is
about 830 tokens. Your own card inputs are extra and can be larger.

## Where it fits

| Tool kind | What they do well | Where cardhand differs |
|---|---|---|
| Long chat sessions | Everything in context, nothing to set up | cardhand keeps the plan in project files, not in the chat |
| Methodology plugins for coding | Plans, test-first, review, polished skills | cardhand has no required process and is not tied to software |
| Task-graph tools | Many concurrent agents, atomic claims | cardhand is Markdown plus one script, with no database |
| Native agent task lists | Built in, with dependencies | cardhand is plain files that are meant to outlast a session |

## For developers

The queue is plain files, and the script is standard-library Python 3.7 or later. You can run it without the plugin:
`python3 cards/cards.py --help` lists the commands (`init`, `new`, `depend`, `ready`, `claim`, `result`, `accept`,
`reject`, `retry`, `answer`, `drop`, `priority`, `check`, `status`). Use just the script and the card files if you prefer.

To run the free checks:

    PYTHONDONTWRITEBYTECODE=1 python3 tests/check.py

Seven checks: a throwaway queue lifecycle, lints, name and version, idle-size budget, no stray files, and
`claude plugin validate` locally. No model is called. Every push runs the free checks in CI.

[![checks](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml)

## License, changelog

MIT (see `LICENSE`). Changes: see `CHANGELOG.md`. Bugs and ideas: open an issue and say which harness and version you ran.

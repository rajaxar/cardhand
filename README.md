# cardhand

Give a long job to a queue of cards. A new agent takes one card, writes the answer to disk, and exits. The queue grows
as the work teaches it something.

You don't need to write code. Install it once, describe the job in chat, and steer when it asks.

## Install

Install once for each agent you use.

### Claude Code

    /plugin marketplace add rajaxar/cardhand
    /plugin install cardhand@cardhand

### Codex CLI

    codex plugin marketplace add rajaxar/cardhand
    codex plugin add cardhand

### Cursor and Copilot CLI

Add `rajaxar/cardhand` as a plugin marketplace, then install `cardhand`.

### OpenCode

Clone the repo and ask the agent to read `skills/run/SKILL.md`.

For local development, use `claude --plugin-dir /path/to/plugin`.

## Use it

In Claude Code, open the folder you want to work in and type:

    /cardhand:start find out why our nightly export is slow
    /cardhand:run
    /cardhand:status

Or hand it a plan you already have:

    /cardhand:start specs/migration.md

The agent posts a short plan, then starts the first wave of work. It asks in chat when it needs a decision. At the end
of each wave it tells you what works, how to try it, and what is rough. Your reply goes to the top of the queue.

`/cardhand:status` shows what needs you. `cards/dashboard.html` shows the same thing in a browser and keeps itself up
to date.

![The cardhand dashboard, Overview tab, rendered from the bike-share example](docs/dashboard-overview.png)

*The dashboard, from the bike-share example (invented data).*

**Best for:** research, data work, and long jobs where the plan changes as you learn.
**Not for:** one-off edits (just ask), or software features where a coding plugin already fits.
**No required process.** Cards need no reviews, specs or phases.

No code to run. The agent runs the queue; the cards are Markdown you can read or edit.

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

The agent wrote the Result and proposed a follow-up card. That proposal became C005. The first line of a Result is the
answer, in one sentence. The full folder, including a dropped card and a "Ruled out" answer, is in
`examples/bike-share/`.

## What it creates

A `cards/` folder holds the plan (`BRIEF.md`), the rules (`RULES.md`), a plain-English summary (`OVERVIEW.md`), one
Markdown file per card in `queue/`, and a dashboard. The agent writes each card's output to `scratch/` and keeps the
generated views current.

## How it decides what to do

A card runs when the cards it depends on are done. Ready cards run most important first. When a card teaches the agent
something, it can add a new card. Work moves in waves; each wave ends with a short report and the next wave.

## The cost

Idle, the plugin adds about 680 bytes of skill names and descriptions, about 170 tokens. A skill body loads only when you
use it.

One card dispatch reads about 3.3 KB of the plugin's own text: the prompt, `RULES.md`, the card and its inputs. That is
about 830 tokens. Your own card inputs are extra and can be larger.

## Where it fits

| Tool kind | What they do well | Where cardhand differs |
|---|---|---|
| Long chats | Everything stays in the conversation | cardhand keeps the plan in files, not in the chat |
| Coding plugins | Plans, tests, review | cardhand has no required process and is not only for code |
| Task trackers | Coordination for many agents | cardhand is Markdown and one small script, with no database |
| Built-in task lists | Dependencies, always there | cardhand is plain files that outlast a session |

## For developers

The queue is plain files, and the script is Python 3.7+ standard library. You can run it without the plugin:
`python3 cards/cards.py --help` lists the commands.

Add your own rules at the bottom of `RULES.md`. One line turns on a test gate, for example `check_cmd: pytest -q`.

Commit the Markdown and `scratch/`; ignore the generated `view/`, `status.js` and `status.json`.

To run the free checks:

    PYTHONDONTWRITEBYTECODE=1 python3 tests/check.py

Seven checks: a throwaway queue lifecycle, lints, name and version, idle-size budget, no stray files, and
`claude plugin validate` locally. No model is called. Every push runs the free checks in CI.

[![checks](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/rajaxar/cardhand/actions/workflows/checks.yml)

## License, changelog

MIT (see `LICENSE`). Changes: see `CHANGELOG.md`. Bugs and ideas: open an issue and say which agent and version you ran.

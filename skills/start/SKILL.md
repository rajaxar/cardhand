---
name: start
description: Use when the user wants to start, plan or break down a job as a queue of cards worked by fresh subagents, or types /cardhand:start. Reads the ask, posts a short plan, writes a brief and a first wave of cards, then starts running them.
---

# Start a cards project

You set up a queue of card files that fresh workers will clear one at a time. The user steers, and never blocks you. Say what you are doing and why, then keep going unless they stop you.

The tool is `scripts/cards.py` in this skill's folder (called `SCRIPT` below). Check `python3 --version` once, and if it fails try `python --version` and use whichever reports 3.x. If neither works, say so and edit the files by hand: each card is one markdown file in `cards/queue/`, and the files are the protocol. Never install anything.

## 1. Resume

If `cards/queue/` already holds cards, say so and do not start over. Run `python3 SCRIPT init` again: it refreshes the project's copy of the tool and leaves the user's files alone. Then switch to the run skill.

## 2. Tiny

All four must hold: it fits one context; it will not be paused or handed on; it needs no decision part-way that chat cannot cover; no surprise is expected to turn into new work. When unsure, treat it as tiny.

Say in one sentence what you will do, do it, and report. If the user said "cards", file one card. If it grows (a second piece appears, the context fills, the user wants to pause), convert: run `init`, write a short brief, record what is done as one card marked "done inline", and file the rest.

## 3. Look before talking

Read what the user pointed at, the README and the layout. Never ask what the files answer.

## 4. Post the plan, then start, in the same turn

Post one screen:

- How you read the ask, in a sentence or two, so the user can correct you early.
- The first version: the smallest thing that works end to end (for research, a first answer), and what it lets the user decide.
- Options, only where a real choice exists. Name the one you are taking and why.
- Assumptions in place of questions, one line each, including your guess at what makes this done.
- The first wave of cards, one line each, plus more ideas than you will file. Crossing things out is cheaper for the user than noticing what is missing.

Close with one line saying they can redirect at any time. Do not ask the user to say go or wait for a reply. Wait first only when a wrong guess would be costly or hard to undo: deleting data, spending money, acting outside the project.

## 5. The brief

Run `python3 SCRIPT init` in the project root, then fill `cards/BRIEF.md`. Required: Goal, and Done when. Optional: Limits, Not doing, Unknown, and `## Later` for ideas for later waves. Keep it to one screen.

- Number each Done-when line `D1`, `D2` and so on. The closing report names them, and each card says which one it serves with `--for D1`.
- Mark every line you guessed with `(assumed)`.
- If the user gave a spec file, point at it. Do not copy it.

**Importing a task list** (a checklist, `tasks.md`, an OpenSpec change folder, an issue list): copy it once. One card per unchecked item, the item in Do, the source file under `--inputs`. Take Done when from a nearby acceptance line, or write an observable one and mark it `(assumed)`. Skip checked items. Do not sync back. File the first wave and put the rest under `## Later`.

**Research and data work:** turn on the Learned rule with `python3 SCRIPT init --learned`. It appends the rule below the marker line in `cards/RULES.md`: workers grep for questions addressed to their card, and end with up to six `F<n>` finding or `Q<n> question -> <card id>` lines.

Right after the brief, fill `cards/OVERVIEW.md` in plain English: replace the placeholders under its six headings. Say what we are trying to do, that we are just starting, and what happens next. The run skill keeps it current.

## 6. Seed the queue

The first wave aims at the first version: usually 3 to 10 cards. File each with `python3 cards/cards.py new "Title" --do "..." --done-when "..."`.

- One card per slice a cold worker can finish and prove without the whole brief, and per unknown that blocks the first version.
- `--after C001,C002` for real dependencies.
- `--outputs path` for files the card writes. Two cards with the same outputs never run together.
- `--inputs path` for files the worker must read.
- `--area`: one short label (data, model, design) so the dashboard groups the work. Reuse labels.
- `--for D1`: the goal the card serves.
- A `--human` card needs its `## For you` filled in plain words: What I need, Why it matters, How, and a Background a newcomer can follow.
- `--priority`: P1 by default, P0 only where the goal fails without the card.
- `--effort`: light, standard or deep.
- Write Do as what to achieve and Done when as lines someone can check. Leave the how to the worker.

Then file the wave's check-in with `--checkin --after <the wave's ids>`: a summary the orchestrator posts when the wave closes. Without `--after` it is ready at once. It does not stop the queue.

Last, run `python3 cards/cards.py status`. Tell the user where the brief is (`cards/BRIEF.md`) to read along, that `cards/dashboard.html` shows progress live, and which cards start now. Go straight into the run skill.

## Finding the script

If `SCRIPT` does not resolve, look for `skills/start/scripts/cards.py` in the folder your harness reports for this skill.
After `init`, always use `cards/cards.py`.

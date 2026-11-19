# Changelog

## 0.3.0

What you will see differently:

- **A dashboard that reads in plain words.** Cards that need you now say what is wanted, why it matters and the first step
  with a time estimate, instead of showing the working notes agents wrote for each other. Finished cards can add one line on
  what the result means for the project.
- **Road to done.** The Plan tab is now a list of your brief's goals, each marked met or not, with how many cards are done and
  open and the next card on each. Mark a goal `[met]` in the brief and it ticks.
- **An overview that says when it is out of date.** The Overview tab lists the cards that closed after it was written, and
  the agent is told to rewrite it once five have closed (`accept` says so).
- **Cards can name the goal they serve** with `new --for D1`, so the dashboard can group work by goal.
- **Light and dark themes**, a keyboard help panel, and Learned is now "What we found".
- **`check` catches more**: a card that needs you but has no plain ask, and a For you line that contains a card id or a file
  path (a person will not know either).
- **Worker rules updated.** Existing projects pick up the new rules and dashboard the next time any command runs after you
  update the plugin; your own rules below the marker line in `RULES.md` are kept.
- Free checks now also confirm that every key the dashboard reads is in the status file (`tests/check.py`).

## 0.2.0

First public version.

- Three skills: `start` (one-line idea or spec in, brief and first wave out), `run` (works the queue with fresh workers),
  `status` (what needs you, what is running, what was learned).
- One standard-library Python script, `cards.py`, that serves the queue, with a ready order, loop and output-overlap refusals,
  and `accept` that refuses missing outputs.
- A browser dashboard with Overview, Now, Plan, Map and Learned tabs, generated from the files with no network use.
- `OVERVIEW.md`, an orchestrator-written summary in plain words, shown first on the dashboard.
- A portable Agent Plugins manifest, so the same package runs in Claude Code, Codex CLI, Cursor and Copilot CLI; one harness
  note covers worker dispatch on each.
- An optional checks recipe (`recipes/checks.md`) and a worked example (`examples/bike-share/`, invented data).
- Free checks in `tests/check.py`: lifecycle, lints, name and version, idle-size budget, no stray files, `claude plugin validate`.
- Run end to end on Codex CLI across two sessions: plan, first wave, one worker per card, no drift.

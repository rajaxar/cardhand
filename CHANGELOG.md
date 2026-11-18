# Changelog

## 0.2.0

First public version.

- Three skills: `start` (one-line idea or spec in, brief and first wave out), `run` (works the queue with fresh workers),
  `status` (what needs you, what is running, what was learned).
- One standard-library Python script, `cards.py`, that serves the queue, with a ready order, loop and output-overlap refusals,
  and `accept` that refuses missing outputs.
- A browser dashboard with Overview, Now, Plan, Map and Learned tabs, generated from the files with no network use.
- `OVERVIEW.md`, an orchestrator-written summary in plain words, shown first on the dashboard.
- An optional checks recipe (`recipes/checks.md`) and a worked example (`examples/bike-share/`, invented data).
- Free checks in `tests/check.py`: lifecycle, lints, name and version, idle-size budget, no stray files, `claude plugin validate`.

Not tested yet: a live orchestrator and workers end to end, resuming after a real compaction, a non-software job from start to
finish, batching of small cards, install from a pushed GitHub repo, Windows, Python older than 3.13, and any harness other than
Claude Code.

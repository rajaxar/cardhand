# Starting and watching a worker on your harness

Read this once per session, then use the run skill. If your real tool list disagrees with a line here, trust the tool list.
Docs checked 2026-11-18; report anything that drifted.

## What every harness needs
Start one agent per card, fresh, with the prompt `claim` printed, and nothing else. Give the worker the prompt text, not a
summary of it. One card per agent unless the cards are light and you were told to batch.

## Where to say what
| Harness | Start a worker | Tell it to be fresh | Notice it stopped | Stop one |
|---|---|---|---|---|
| Codex CLI | ask for it in words: "spawn one agent per card and wait for all of them"; or a custom TOML agent in `.codex/agents/` | say "start with no prior transcript"; if a fork/transcript option appears, turn it off | the parent waits for all spawned agents, then consolidates; there is no separate wake-up to rely on | ask it to stop that agent, or let it finish |
| Cursor | ask for one subagent per card; custom ones live in `.cursor/agents/`, built-ins `explore`/`browser` exist without a file | subagents already start with a clean context | background agents write under `~/.cursor/subagents/`; check there, or read the card file | ask; or let it finish and read the card |
| Copilot CLI | ask for a `general-purpose` subagent; independent cards can run in parallel | it gets a separate context; repo instructions are not passed to it, so put everything in the prompt | the card file; ask for `/tasks` if your build has it | ask |
| OpenCode | ask for the built-in `general` subagent, or define one in `.opencode/agents/<name>.md` with `mode: subagent`, or a command with `subagent: true` | it starts fresh in its own child session | the parent is told when a child goes idle | ask |
| Anything else | Mode B (spawn and wait) if a spawn tool exists; otherwise Mode D: print the prompt and ask the user to paste it into a new chat | a new chat is fresh | the user tells you, or `check` flags a stale claim | n/a |

## Effort
Cards carry `effort: light|standard|deep`. On every harness except Claude Code, inherit the parent model; do not invent a
model name. On Claude Code the mapping is in the run skill.

## If you have to wait
On a harness that makes you wait for every worker before you can speak again, post one line first: which cards started. Then
review them when the turn returns. Do not sit silent and do not poll.

## No subagents at all
Do one card at a time. Tell the user once: "This harness has no subagents I can start. I will claim one card at a time and
give you a one-line prompt to paste into a new chat." Never pretend to dispatch: a card is `doing` only after `claim`, and
`check` finds any that nobody picked up.

## Batch
On a host you have not run before, set `batch` to 1 in `cards/settings.json` (one card per agent). Turn batching on only
after you have seen one agent finish two light cards without mixing them up.

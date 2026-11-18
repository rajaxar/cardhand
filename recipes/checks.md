---
name: checks
description: Optional independent re-checks before a decision rests on a claim.
---

## When
A later card or the human will rest on a claim the author cannot confirm from inside its own context, and a wrong claim would be
expensive to find later. If not, skip it.

## Rules
- The author does not check its own work. A check runs in a fresh context, or is a human card if no fresh context exists.
- A check does not read the target's method first. It re-derives or attacks the target's strongest claim.
- Batch by event: two cards entering the same decision get one check.
- Skip checks on negative results, on exploration with no downstream decision, and where `check_cmd` already covers it.
- When one card is named by about three or more others, a check on it is worth more (a guess, not measured).

## Card kinds
check (tag `check`, depends_on the target)
  Title: "Re-check <claim> in <target id>"
  Do: Without reading <target id>'s method, produce <claim> from <inputs>. Report agree or disagree and the difference. Attack the
  strongest claim. Result ends with "Outcome: changed-something | clean | inconclusive".

converge (tag `check`, only when a spec exists)
  Title: "List what the spec asks that is not yet met"
  Do: Read <spec path>. Earlier claims of completion are not evidence. For each requirement say met or unmet and how you know.
  Propose a card for each unmet item. Change nothing else.

## Adopt

A project adds this one line to `cards/RULES.md`: `Cards tagged check: follow cards/recipes/checks.md.`

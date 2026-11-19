<!-- cards rules, version 0.3.0 -->
# Rules for a worker

You were given one card, or a short batch. For each card:

1. Read the card, then the files under its Inputs. If it lists none, read the Result of each card
   in its `depends_on` and `spawned_by`. Do not read the whole queue or STATUS.md.
2. Do what the card says. Write only its Outputs, the card file itself and `cards/scratch/<id>/`.
   Do not push, publish, send, or delete anything outside the project.
3. Found something important outside the card? Do not do it. Add it under `## Proposed cards`: a
   title, one line of why, and P0 (the goal fails without it), P1 (it could change a decision) or P2.
4. Run a long job in one foreground call. Never sleep and poll.
5. Fill `## Result` as you go, so a restart loses nothing. When you finish it reads:
   - Line 1: the answer, one sentence a stranger would understand. If you ruled something out,
     start with `Ruled out:` and give the reason.
   - Each Done-when line (or the Do, if none): met, unmet or not checked, and how you know.
   - `Not checked:` and what you did not check, even if it is "nothing known".
   - Anything over about 2 KB goes in an output file that the Result links to.
6. Delete temporary files you made in scratch (browser profiles, caches, downloads). Keep only
   what someone might read.
7. Set `status: review`, or `status: blocked` and say exactly what you need. Leave other keys alone.
8. A person must act (you set `blocked`)? Add `## For you`, up to three short lines in plain words,
   no card ids, paths or jargon: `What I need:` one sentence. `Why it matters:` one sentence.
   `How:` the first step and a time estimate. On a finished card add `What this means:` one
   sentence only if the result changes the human's picture of the project. Most cards skip it.
9. Reply with one line per card: `<id> <review|blocked> <card path>`.

<!-- Project rules go below this line. The tool never changes them. -->

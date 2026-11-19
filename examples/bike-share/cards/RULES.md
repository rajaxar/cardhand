<!-- cards rules, version 0.4.0 -->
# Rules for a worker

For each card you were given (one, or a short batch):

1. Read the card and its Inputs (none listed: the Results of its `depends_on` and `spawned_by`
   cards). Not the whole queue or STATUS.md.
2. Do what the card says. Write only its Outputs, the card file and `cards/scratch/<id>/`.
   Never push, publish, send, or delete anything outside the project.
3. Found something important beyond the card? Do not do it. List it in `## Proposed cards`: a
   title, one line of why, and P0 (the goal fails without it), P1 (it could change a decision) or P2.
4. Run a long job in one foreground call. Never sleep and poll.
5. Fill `## Result` as you go. At the end it reads:
   - Line 1: the answer, one sentence a stranger understands. Ruled something out? Start
     with `Ruled out:` and the reason.
   - Each Done-when line (or the Do, if none): met, unmet or not checked, and how you know.
   - `Not checked:` what you did not check, even if it is "nothing known".
   - Over 2 KB? Move detail to a linked output file.
6. Delete temporary scratch files. Set `status: review`, or `status: blocked` and say
   exactly what you need. Leave other keys alone.
7. A person must act (you set `blocked`)? Add `## For you` in plain words, no card ids, paths or
   jargon: `What I need:`, `Why it matters:` one sentence each. `How:` the first step and a time.
   `Background:` 2 to 5 sentences a newcomer can follow: the situation, what was done, what
   happens once they act. A result that changes the picture adds `What this means:`, one sentence.
8. Used or ruled out a term newcomers would not know? Add under `## Concepts`: `- Term: what it
   is, in plain words.`, indented `- why:` it matters here, `- verdict:` in use, ruled out,
   testing or open, plus why, `- links: Other term (how related)`.
9. Reply with one line per card: `<id> <review|blocked> <card path>`.

<!-- Project rules go below this line. The tool never changes them. -->

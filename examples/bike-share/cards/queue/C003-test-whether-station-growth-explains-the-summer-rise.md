---
id: C003
title: Test whether station growth explains the summer rise
status: done
priority: P1
effort: standard
depends_on: [C002]
spawned_by: human
area: analysis
for: D3
human: false
filed: 2026-03-02 09:00:00 +0000
started: 2026-03-02 10:15:00 +0000
finished: 2026-03-02 10:50:00 +0000
attempts: 1
---

## Do
Check whether new stations opening during the year account for the summer rise in trips, by recounting using only stations open all twelve months.

## Done when
- The recount exists, and the Result says whether the summer rise is still there.

## Inputs
cards/scratch/C002/monthly_counts.csv

## Outputs
cards/scratch/C003/fixed_stations.csv

## Result
Ruled out: station growth does not explain the summer rise, because the rise is still there when only stations open all year are counted.

- The recount exists: met, cards/scratch/C003/fixed_stations.csv.
- The Result says whether the rise is still there: met, it is, in all three datasets.

Not checked: nothing known.

## For you
What this means: New stations are not why summer is busier, so the seasonal rise looks like real rider behaviour.

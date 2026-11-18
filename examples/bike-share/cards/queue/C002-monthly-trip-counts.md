---
id: C002
title: Monthly trip counts per dataset
status: done
priority: P1
effort: standard
depends_on: [C001]
spawned_by: human
area: data
human: false
filed: 2026-03-02 09:00:00 +0000
started: 2026-03-02 09:25:00 +0000
finished: 2026-03-02 10:10:00 +0000
attempts: 1
---

## Do
Count trips per month for each dataset over the shared twelve months, and put them in one table.

## Done when
- One table has twelve rows and three columns of counts.

## Inputs
cards/scratch/C001/inventory.md

## Outputs
cards/scratch/C002/monthly_counts.csv

## Result
Every dataset has its busiest month in summer and its quietest in winter, though Lakeside is flatter than the other two.

- One table has twelve rows and three columns of counts: met, cards/scratch/C002/monthly_counts.csv.

Not checked: Northgate's counts include a one-minute test trip type that C001 did not rule out.

## Proposed cards
- Align the trip definition across datasets (Northgate counts short test rentals).

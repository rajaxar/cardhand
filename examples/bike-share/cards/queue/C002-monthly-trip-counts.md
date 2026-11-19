---
id: C002
title: Monthly trip counts per dataset
status: done
priority: P1
effort: standard
depends_on: [C001]
spawned_by: human
area: data
for: D1
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

## Concepts
- Monthly trip count: How many trips started in each calendar month.
  - why: Every seasonal comparison in this project is built from it.
  - verdict: in use, one table holds it for all three systems.
  - links: Trip definition (counted under), Shared twelve months (limited to)
- Test rental: A rental of under a minute made to check that a bike works, not a real ride.
  - why: Northgate keeps them in its data and has many in summer.
  - verdict: open, we do not yet know whether Northgate's short rentals are tests.

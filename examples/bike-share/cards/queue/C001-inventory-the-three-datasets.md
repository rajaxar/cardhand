---
id: C001
title: Inventory the three datasets
status: done
priority: P1
effort: light
depends_on: []
spawned_by: human
area: data
for: D1
human: false
filed: 2026-03-02 09:00:00 +0000
started: 2026-03-02 09:05:00 +0000
finished: 2026-03-02 09:20:00 +0000
attempts: 1
---

## Do
For each dataset, list the columns, the date range and how a trip is defined in its docs.

## Done when
- Each dataset has one line for columns, date range and trip definition.

## Outputs
cards/scratch/C001/inventory.md

## Result
All three datasets cover the same twelve months, but only two define a trip as "a rental of at least 60 seconds".

- Each dataset has one line for columns, date range and trip definition: met, see cards/scratch/C001/inventory.md.

Not checked: whether the docs match how the data was actually exported.

## For you
What this means: Only two of the three systems count trips the same way, so the comparison may need adjusting.

## Concepts
- Trip definition: The rule a bike-share system uses to decide which rentals count as trips.
  - why: The three systems use different rules, so their raw counts may not compare like with like.
  - verdict: in use, every count in this project says which rule it follows.
  - links: Minimum trip length (part of it), Test rental (left out by it)
- Minimum trip length: The shortest rental that still counts as a trip, 60 seconds in two of the three systems.
  - why: It is the one place the trip rules differ.
  - verdict: in use, the 60-second rule is the shared yardstick.
  - links: Test rental (would remove)

# Overview

## What we are trying to do
We have trip records from three bike-share systems and want to know whether they all rise and fall with the seasons by the same amount, or whether one system behaves differently.

## How we are doing
The first wave is finished: we know what each dataset holds and we have month-by-month trip counts for all three. One important card is left: measuring the seasonal swing for each system. The answer is close, but not yet trustworthy.

## What we have learned
All three systems are busiest in summer and quietest in winter, though Lakeside is flatter than the other two. Adding stations explains very little of the summer rise. One system counts very short test rentals as trips, which may inflate its numbers.

## What we have tried, by area
- Data: inventoried the three datasets and counted trips per month. Open: make the three trip definitions match.
- Analysis: tested whether new stations explain the summer rise (they do not). Open: measure the swing per system.

## Ruled out
- Station growth as the cause of the summer rise.
- Adding weather data: it would explain the swing, but not how it differs between systems.

## What happens next
Measure the seasonal swing for each system, then, if time allows, align the trip definitions so the comparison is fair. After that we write up whether Lakeside really is flatter.

window.CARDS_STATUS = {
 "schema": 2,
 "updated": 1795123134.425248,
 "project": "bike-share",
 "goal": [
  "Compare three open bike-share trip datasets (Harbor City, Northgate, Lakeside) for seasonal patterns, and say which seasonal effects hold in all three."
 ],
 "done_when": [
  "[met] D1: One table gives monthly trip counts for each dataset over the same twelve months.",
  "D2: Each dataset has a seasonal swing figure (busiest month divided by quietest), computed the same way.",
  "D3: A short note says which seasonal patterns appear in all three datasets and which in only some. (assumed)"
 ],
 "counts": {
  "todo": 3,
  "doing": 0,
  "review": 0,
  "done": 4,
  "blocked": 0,
  "dropped": 1
 },
 "high_total": 6,
 "high_closed": 4,
 "checkpoint": {
  "id": "C008",
  "title": "Confirm what Northgate's one-minute rentals are"
 },
 "goals": [
  {
   "id": "D1",
   "text": "One table gives monthly trip counts for each dataset over the same twelve months.",
   "met": true,
   "open": 0,
   "done": 2,
   "next": []
  },
  {
   "id": "D2",
   "text": "Each dataset has a seasonal swing figure (busiest month divided by quietest), computed the same way.",
   "met": false,
   "open": 3,
   "done": 0,
   "next": [
    "C006",
    "C008"
   ]
  },
  {
   "id": "D3",
   "text": "A short note says which seasonal patterns appear in all three datasets and which in only some. (assumed)",
   "met": false,
   "open": 0,
   "done": 1,
   "next": []
  }
 ],
 "wave": 2,
 "waves": [
  {
   "n": 1,
   "summary": "C004",
   "done": 4,
   "dropped": 0,
   "total": 4
  },
  {
   "n": 2,
   "summary": null,
   "done": 0,
   "dropped": 1,
   "total": 4
  }
 ],
 "later": [
  "Compare weekday against weekend patterns.",
  "Look at trip length by season.",
  "Explain the pattern with daily weather data.",
  "Write the three-page summary for the city council newsletter."
 ],
 "brief": "BRIEF.md",
 "stale_minutes": 30,
 "overview": {
  "text": "# Overview\n\n## What we are trying to do\nWe have trip records from three bike-share systems and want to know whether they all rise and fall with the seasons by the same amount, or whether one system behaves differently.\n\n## How we are doing\nThe first wave is finished: we know what each dataset holds and we have month-by-month trip counts for all three. One important card is left: measuring the seasonal swing for each system. The answer is close, but not yet trustworthy.\n\n## What we have learned\nAll three systems are busiest in summer and quietest in winter, though Lakeside is flatter than the other two. Adding stations explains very little of the summer rise. One system counts very short test rentals as trips, which may inflate its numbers.\n\n## What we have tried, by area\n- Data: inventoried the three datasets and counted trips per month. Open: make the three trip definitions match.\n- Analysis: tested whether new stations explain the summer rise (they do not). Open: measure the swing per system.\n\n## Ruled out\n- Station growth as the cause of the summer rise.\n- Adding weather data: it would explain the swing, but not how it differs between systems.\n\n## What happens next\nMeasure the seasonal swing for each system, then, if time allows, align the trip definitions so the comparison is fair. After that we write up whether Lakeside really is flatter.\n",
  "updated": 1795123014.1375864,
  "stale": false,
  "closed": 0,
  "placeholder": false,
  "since": []
 },
 "areas": [
  {
   "name": "data",
   "total": 5,
   "done": 2,
   "open": 2
  },
  {
   "name": "analysis",
   "total": 2,
   "done": 1,
   "open": 1
  }
 ],
 "key_path": [
  "C001",
  "C002",
  "C003",
  "C004",
  "C006"
 ],
 "decisions": [
  {
   "id": "D-001",
   "title": "Compare datasets over the twelve shared months only",
   "text": "Two datasets cover longer spans, but a fair comparison needs the same calendar months, so everything is cut to the twelve months all three share."
  },
  {
   "id": "D-002",
   "title": "Do not chase weather data",
   "text": "Weather would explain the swing, but the question is how the swing differs by dataset. Weather moved to the Later list."
  }
 ],
 "cards": [
  {
   "id": "C001",
   "title": "Inventory the three datasets",
   "status": "done",
   "column": "done",
   "priority": "P1",
   "human": false,
   "depends_on": [],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "light",
   "attempts": "1",
   "batch": "",
   "tags": [],
   "started": 1772442300.0,
   "finished": 1772443200.0,
   "outcome": "All three datasets cover the same twelve months, but only two define a trip as \"a rental of at least 60 seconds\".",
   "do": "For each dataset, list the columns, the date range and how a trip is defined in its docs.",
   "done_when": "- Each dataset has one line for columns, date range and trip definition.",
   "result": "All three datasets cover the same twelve months, but only two define a trip as \"a rental of at least 60 seconds\".\n\n- Each dataset has one line for columns, date range and trip definition: met, see cards/scratch/C001/inventory.md.\n\nNot checked: whether the docs match how the data was actually exported.",
   "why_dropped": "",
   "wave": 1,
   "depth": 0,
   "outputs": [
    "cards/scratch/C001/inventory.md"
   ],
   "area": "data",
   "for_goal": "D1",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": "Only two of the three systems count trips the same way, so the comparison may need adjusting."
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "For each dataset, list the columns, the date range and how a trip is defined in its docs.",
   "body": "## Do\nFor each dataset, list the columns, the date range and how a trip is defined in its docs.\n\n## Done when\n- Each dataset has one line for columns, date range and trip definition.\n\n## Outputs\ncards/scratch/C001/inventory.md\n\n## Result\nAll three datasets cover the same twelve months, but only two define a trip as \"a rental of at least 60 seconds\".\n\n- Each dataset has one line for columns, date range and trip definition: met, see cards/scratch/C001/inventory.md.\n\nNot checked: whether the docs match how the data was actually exported.\n\n## For you\nWhat this means: Only two of the three systems count trips the same way, so the comparison may need adjusting."
  },
  {
   "id": "C002",
   "title": "Monthly trip counts per dataset",
   "status": "done",
   "column": "done",
   "priority": "P1",
   "human": false,
   "depends_on": [
    "C001"
   ],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "standard",
   "attempts": "1",
   "batch": "",
   "tags": [],
   "started": 1772443500.0,
   "finished": 1772446200.0,
   "outcome": "Every dataset has its busiest month in summer and its quietest in winter, though Lakeside is flatter than the other two.",
   "do": "Count trips per month for each dataset over the shared twelve months, and put them in one table.",
   "done_when": "- One table has twelve rows and three columns of counts.",
   "result": "Every dataset has its busiest month in summer and its quietest in winter, though Lakeside is flatter than the other two.\n\n- One table has twelve rows and three columns of counts: met, cards/scratch/C002/monthly_counts.csv.\n\nNot checked: Northgate's counts include a one-minute test trip type that C001 did not rule out.",
   "why_dropped": "",
   "wave": 1,
   "depth": 1,
   "outputs": [
    "cards/scratch/C002/monthly_counts.csv"
   ],
   "area": "data",
   "for_goal": "D1",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": ""
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "Count trips per month for each dataset over the shared twelve months, and put them in one table.",
   "body": "## Do\nCount trips per month for each dataset over the shared twelve months, and put them in one table.\n\n## Done when\n- One table has twelve rows and three columns of counts.\n\n## Inputs\ncards/scratch/C001/inventory.md\n\n## Outputs\ncards/scratch/C002/monthly_counts.csv\n\n## Result\nEvery dataset has its busiest month in summer and its quietest in winter, though Lakeside is flatter than the other two.\n\n- One table has twelve rows and three columns of counts: met, cards/scratch/C002/monthly_counts.csv.\n\nNot checked: Northgate's counts include a one-minute test trip type that C001 did not rule out.\n\n## Proposed cards\n- Align the trip definition across datasets (Northgate counts short test rentals)."
  },
  {
   "id": "C003",
   "title": "Test whether station growth explains the summer rise",
   "status": "done",
   "column": "done",
   "priority": "P1",
   "human": false,
   "depends_on": [
    "C002"
   ],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "standard",
   "attempts": "1",
   "batch": "",
   "tags": [],
   "started": 1772446500.0,
   "finished": 1772448600.0,
   "outcome": "Ruled out: station growth does not explain the summer rise, because the rise is still there when only stations open all year are counted.",
   "do": "Check whether new stations opening during the year account for the summer rise in trips, by recounting using only stations open all twelve months.",
   "done_when": "- The recount exists, and the Result says whether the summer rise is still there.",
   "result": "Ruled out: station growth does not explain the summer rise, because the rise is still there when only stations open all year are counted.\n\n- The recount exists: met, cards/scratch/C003/fixed_stations.csv.\n- The Result says whether the rise is still there: met, it is, in all three datasets.\n\nNot checked: nothing known.",
   "why_dropped": "",
   "wave": 1,
   "depth": 2,
   "outputs": [
    "cards/scratch/C003/fixed_stations.csv"
   ],
   "area": "analysis",
   "for_goal": "D3",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": "New stations are not why summer is busier, so the seasonal rise looks like real rider behaviour."
   },
   "touched": null,
   "ruled_out": true,
   "learned": [],
   "summary": "Check whether new stations opening during the year account for the summer rise in trips, by recounting using only stations open all twelve months.",
   "body": "## Do\nCheck whether new stations opening during the year account for the summer rise in trips, by recounting using only stations open all twelve months.\n\n## Done when\n- The recount exists, and the Result says whether the summer rise is still there.\n\n## Inputs\ncards/scratch/C002/monthly_counts.csv\n\n## Outputs\ncards/scratch/C003/fixed_stations.csv\n\n## Result\nRuled out: station growth does not explain the summer rise, because the rise is still there when only stations open all year are counted.\n\n- The recount exists: met, cards/scratch/C003/fixed_stations.csv.\n- The Result says whether the rise is still there: met, it is, in all three datasets.\n\nNot checked: nothing known.\n\n## For you\nWhat this means: New stations are not why summer is busier, so the seasonal rise looks like real rider behaviour."
  },
  {
   "id": "C004",
   "title": "Wave 1 summary",
   "status": "done",
   "column": "done",
   "priority": "P1",
   "human": false,
   "depends_on": [
    "C001",
    "C002",
    "C003"
   ],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "light",
   "attempts": "1",
   "batch": "",
   "tags": [
    "checkin"
   ],
   "started": 1772448900.0,
   "finished": 1772449080.0,
   "outcome": "Wave 1 gives a monthly trip table for all three datasets, and shows summer is busiest in each; done inline.",
   "do": "Summarize what now works, how to try it, what is rough and what is worth reading. Done inline.",
   "done_when": "",
   "result": "Wave 1 gives a monthly trip table for all three datasets, and shows summer is busiest in each; done inline.\n\n- What works: the table in cards/scratch/C002/monthly_counts.csv, and a ruled-out explanation (station growth).\n- Rough: the datasets may count a trip differently, so the table may not compare like with like.\n- Worth reading: cards/scratch/C001/inventory.md.\n\nNot checked: the table against the original data portals.",
   "why_dropped": "",
   "wave": 1,
   "depth": 3,
   "outputs": [],
   "area": "",
   "for_goal": "",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": ""
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "Summarize what now works, how to try it, what is rough and what is worth reading.",
   "body": "## Do\nSummarize what now works, how to try it, what is rough and what is worth reading. Done inline.\n\n## Result\nWave 1 gives a monthly trip table for all three datasets, and shows summer is busiest in each; done inline.\n\n- What works: the table in cards/scratch/C002/monthly_counts.csv, and a ruled-out explanation (station growth).\n- Rough: the datasets may count a trip differently, so the table may not compare like with like.\n- Worth reading: cards/scratch/C001/inventory.md.\n\nNot checked: the table against the original data portals."
  },
  {
   "id": "C005",
   "title": "Align the trip definition across datasets",
   "status": "todo",
   "column": "next",
   "priority": "P2",
   "human": false,
   "depends_on": [],
   "waiting_on": [],
   "spawned_by": "C002",
   "effort": "standard",
   "attempts": "0",
   "batch": "",
   "tags": [],
   "started": null,
   "finished": null,
   "outcome": "",
   "do": "Recount trips in Northgate with the 60-second minimum the other two datasets use, and say how much the monthly counts change.",
   "done_when": "- A recount exists, and the Result gives the largest monthly change as a percentage.",
   "result": "",
   "why_dropped": "",
   "wave": 2,
   "depth": 0,
   "outputs": [
    "cards/scratch/C005/northgate_aligned.csv"
   ],
   "area": "data",
   "for_goal": "D2",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": ""
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "Recount trips in Northgate with the 60-second minimum the other two datasets use, and say how much the monthly counts change.",
   "body": "## Do\nRecount trips in Northgate with the 60-second minimum the other two datasets use, and say how much the monthly counts change.\n\n## Done when\n- A recount exists, and the Result gives the largest monthly change as a percentage.\n\n## Inputs\ncards/scratch/C002/monthly_counts.csv\n\n## Outputs\ncards/scratch/C005/northgate_aligned.csv\n\n## Result\n(worker fills this in when it finishes: first line is the outcome)"
  },
  {
   "id": "C006",
   "title": "Seasonal swing per dataset",
   "status": "todo",
   "column": "next",
   "priority": "P0",
   "human": false,
   "depends_on": [
    "C004"
   ],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "standard",
   "attempts": "0",
   "batch": "",
   "tags": [],
   "started": null,
   "finished": null,
   "outcome": "",
   "do": "For each dataset, divide the busiest month's trips by the quietest month's, and compare the three figures.",
   "done_when": "- Each dataset has one swing figure, computed the same way.",
   "result": "",
   "why_dropped": "",
   "wave": 2,
   "depth": 0,
   "outputs": [
    "cards/scratch/C006/swing.md"
   ],
   "area": "analysis",
   "for_goal": "D2",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": ""
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "For each dataset, divide the busiest month's trips by the quietest month's, and compare the three figures.",
   "body": "## Do\nFor each dataset, divide the busiest month's trips by the quietest month's, and compare the three figures.\n\n## Done when\n- Each dataset has one swing figure, computed the same way.\n\n## Inputs\ncards/scratch/C002/monthly_counts.csv\n\n## Outputs\ncards/scratch/C006/swing.md\n\n## Result\n(worker fills this in when it finishes: first line is the outcome)"
  },
  {
   "id": "C007",
   "title": "Add daily weather data to the comparison",
   "status": "dropped",
   "column": "ruled_out",
   "priority": "P2",
   "human": false,
   "depends_on": [],
   "waiting_on": [],
   "spawned_by": "human",
   "effort": "standard",
   "attempts": "0",
   "batch": "",
   "tags": [],
   "started": null,
   "finished": 1772449200.0,
   "outcome": "",
   "do": "Join daily temperature to the trip counts and check how much of the seasonal pattern it explains.",
   "done_when": "",
   "result": "",
   "why_dropped": "the goal is to compare seasonal patterns across datasets, not to explain them. Moved to the brief's Later list if wanted.",
   "wave": 2,
   "depth": 0,
   "outputs": [],
   "area": "data",
   "for_goal": "",
   "for_you": {
    "need": "",
    "why": "",
    "how": "",
    "means": ""
   },
   "touched": null,
   "ruled_out": true,
   "learned": [],
   "summary": "Join daily temperature to the trip counts and check how much of the seasonal pattern it explains.",
   "body": "## Do\nJoin daily temperature to the trip counts and check how much of the seasonal pattern it explains.\n\n## Result\n(worker fills this in: not run, dropped)\n\n## Notes\n- 2026-03-02 dropped: the goal is to compare seasonal patterns across datasets, not to explain them. Moved to the brief's Later list if wanted."
  },
  {
   "id": "C008",
   "title": "Confirm what Northgate's one-minute rentals are",
   "status": "todo",
   "column": "you",
   "priority": "P1",
   "human": true,
   "depends_on": [],
   "waiting_on": [],
   "spawned_by": "C002",
   "effort": "light",
   "attempts": "0",
   "batch": "",
   "tags": [],
   "started": null,
   "finished": null,
   "outcome": "",
   "do": "Read Northgate's dataset documentation and say whether rentals under a minute are meant to count as trips.",
   "done_when": "- The answer says yes or no, and quotes the documentation line it rests on.",
   "result": "",
   "why_dropped": "",
   "wave": 2,
   "depth": 0,
   "outputs": [],
   "area": "data",
   "for_goal": "D2",
   "for_you": {
    "need": "Tell me whether Northgate's one-minute rentals are real trips or bike tests.",
    "why": "If they are tests, Northgate's summer looks busier than it is and the comparison is unfair.",
    "how": "Open Northgate's data notes page and read its line about trips; about 5 minutes.",
    "means": ""
   },
   "touched": null,
   "ruled_out": false,
   "learned": [],
   "summary": "Read Northgate's dataset documentation and say whether rentals under a minute are meant to count as trips.",
   "body": "## For you\nWhat I need: Tell me whether Northgate's one-minute rentals are real trips or bike tests.\nWhy it matters: If they are tests, Northgate's summer looks busier than it is and the comparison is unfair.\nHow: Open Northgate's data notes page and read its line about trips; about 5 minutes.\n\n## Do\nRead Northgate's dataset documentation and say whether rentals under a minute are meant to count as trips.\n\n## Done when\n- The answer says yes or no, and quotes the documentation line it rests on.\n\n## Result\n(worker fills this in when it finishes: first line is the outcome)"
  }
 ],
 "files": {
  "cards/BRIEF.md": "view/f1.js",
  "cards/STATUS.md": "view/f2.js",
  "cards/scratch/C001/inventory.md": "view/f3.js",
  "cards/scratch/C002/monthly_counts.csv": "view/f4.js",
  "cards/scratch/C003/fixed_stations.csv": "view/f5.js",
  "cards/scratch/C005/northgate_aligned.csv": null,
  "cards/scratch/C006/swing.md": null
 }
};

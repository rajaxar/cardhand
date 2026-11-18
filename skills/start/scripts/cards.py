#!/usr/bin/env python3
"""cards: a file-backed work queue for an orchestrator and the agents it starts.

Every card is one Markdown file in <root>/queue/. The files are the only state,
so a new session resumes by running `status`. Standard library only.

  cards.py init [--learned]           create or refresh ./cards/ in the current project
  cards.py new "Title" [options]      file a card and print its path (--checkin for a wave summary, --area for a label)
  cards.py ready [-n 4]               what to start now, in pick order
  cards.py depend ID [ID ...] --on X  make existing cards wait on X (--remove to undo)
  cards.py claim ID [ID ID]           mark cards doing and print the worker prompt (several ids: a batch)
  cards.py result ID                  print a card's Result, Proposed cards and Notes
  cards.py accept ID                  check the Result and outputs, then mark done
  cards.py reject ID "what is missing"
  cards.py retry ID ["what happened"] [--force] a worker died: back to todo, partial Result kept (refused if recently claimed or changed)
  cards.py priority ID P0|P1|P2
  cards.py answer ID "the user's answer"
  cards.py drop ID "why"
  cards.py check                      cards in review, blocked, stale or missing an answer
  cards.py status                     write STATUS.md, status.json and status.js; print a summary
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
import time

VERSION = "0.2.0"
STATUSES = ["todo", "doing", "review", "done", "blocked", "dropped"]
CLOSED = {"done", "dropped"}
PRIORITIES = {"P0": 0, "P1": 1, "P2": 2}
EFFORTS = ["light", "standard", "deep"]
SETTINGS = {"slots": 4, "fill": "high", "batch": 3}
STALE_MINUTES = 30
RECENT_MINUTES = STALE_MINUTES  # one rule for alive: `retry` refuses a card that `check` would not yet call stale
RESULT_CAP = 3000
BODY_CAP = 20000
VIEW_CAP = 200 * 1024
DECISION_CAP = 2000
OVERVIEW_CAP = 20000
PLACEHOLDER = "(worker fills this in"
TEXT_KEYS = ("title", "area")  # free text: a ` #` in them is not a comment
SECTIONS = ("Why", "Do", "Done when", "Inputs", "Outputs", "Result", "Proposed cards", "Notes", "Dropped")

RULES_VERSION = "<!-- cards rules, version {} -->".format(VERSION)
RULES_MARKER = "<!-- Project rules go below this line. The tool never changes them. -->"
RULES_V0_MARKER = "The human may add project rules below this line."
RULES = """# Rules for a worker

You were given one card, or a short batch. For each card:

1. Read the card, then the files under its Inputs. If it lists none, read the Result of each card
   in its `depends_on` and `spawned_by`. Do not read the whole queue or STATUS.md.
2. Do what the card says. Write only its Outputs, the card file itself and `{root}/scratch/<id>/`.
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
8. Reply with one line per card: `<id> <review|blocked> <card path>`.
"""

# The start skill turns this on for research and data work with `init --learned`.
LEARNED_RULE = """
## Learned lines
At the start, run `grep -hE '^Q[0-9]+ .*-> <your id>$' {root}/queue/*.md` and take in what it finds.
At the end, add `## Learned` to your card with up to six lines a later card would act on:
`F<n> [verified|reported|inferred] sentence | src: path`, or `Q<n> question -> <existing card id>`.
End a line with `| answers: <id>.Q<n>` when it answers an addressed question.
"""

BRIEF = """# Brief

## Goal
(one or two sentences)

## Done when
(checkable lines with ids: `- D1 ...`, `- D2 ...`; mark each guess `(assumed)`)

## Not doing
(what is out of scope)

## Unknown
(open questions, and who can answer each)

## Later
(ideas for later waves, not filed yet)
"""

OVERVIEW_SECTIONS = ["What we are trying to do", "How we are doing", "What we have learned",
                     "What we have tried, by area", "Ruled out", "What happens next"]
OVERVIEW_PLACEHOLDER = "(not written yet)"
OVERVIEW = "# Overview\n\n" + "".join("## {}\n{}\n\n".format(name, OVERVIEW_PLACEHOLDER) for name in OVERVIEW_SECTIONS)

PROMPT = """You are doing card {id} in {project}.
Read {root}/RULES.md, then {card}, then the files under its Inputs.
Do the card and stay inside its Outputs. Fill its Result and set its status as RULES.md says.
Reply with one line: {id} <review|blocked> {card}"""

BATCH_PROMPT = """You are doing cards {ids} in {project}, one after another.
Treat each card as if you had never seen the others.
Read {root}/RULES.md once. Then for each card: read it and its Inputs, do it, stay inside its
Outputs, fill its Result and set its status as RULES.md says.
{cards}
Reply with one line per card: <id> <review|blocked> <card path>"""

CHECKIN_DO = ("Written inline by the orchestrator once the wave closes: what now works, how to try it, "
              "what is rough, and what is worth reading. Post the same text to the user, then accept.")


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def die(message):
    print("error: " + message, file=sys.stderr)
    sys.exit(1)


def warn(message):
    print("warning: " + message, file=sys.stderr)


def find_root(explicit):
    if explicit:
        return os.path.abspath(explicit)
    if os.environ.get("CARDS_DIR"):
        return os.path.abspath(os.environ["CARDS_DIR"])
    here = os.getcwd()
    while True:
        candidate = os.path.join(here, "cards")
        if os.path.isdir(os.path.join(candidate, "queue")):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            return os.path.join(os.getcwd(), "cards")
        here = parent


class Card:
    def __init__(self, path):
        self.path = path
        with open(path, encoding="utf-8") as f:
            text = f.read()
        match = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
        self.front = match.group(1).split("\n") if match else ["status: (no frontmatter)"]
        self.body = match.group(2) if match else text

    def get(self, key, default=""):
        for line in self.front:
            if line.startswith(key + ":"):
                value = line[len(key) + 1:]
                return (value if key in TEXT_KEYS else value.split(" #")[0]).strip()
        return default

    def set(self, key, value):
        line = "{}: {}".format(key, value).rstrip()
        for i, existing in enumerate(self.front):
            if existing.startswith(key + ":"):
                self.front[i] = line
                return
        self.front.append(line)

    def unset(self, key):
        self.front = [line for line in self.front if not line.startswith(key + ":")]

    def list(self, key):
        raw = self.get(key).strip("[]")
        return [item.strip() for item in raw.split(",") if item.strip()]

    @staticmethod
    def _end(name):
        """Where a section stops. A Result runs to the next known section name, so a worker's own `## ` headings stay in it."""
        if name == "Result":
            return r"^## (?:{})[ \t]*$".format("|".join(re.escape(n) for n in SECTIONS if n != name)) + r"|\Z"
        return r"^## |\Z"

    def section(self, name):
        match = re.search(r"^## {}[ \t]*\n(.*?)(?={})".format(re.escape(name), self._end(name)), self.body, re.S | re.M)
        return match.group(1).strip() if match else ""

    def set_section(self, name, text):
        block = "## {}\n{}\n\n".format(name, text.strip())
        pattern = r"^## {}[ \t]*\n.*?(?={})".format(re.escape(name), self._end(name))
        if re.search(pattern, self.body, re.S | re.M):
            self.body = re.sub(pattern, lambda _: block, self.body, count=1, flags=re.S | re.M)
        else:
            self.body = self.body.rstrip("\n") + "\n\n" + block

    def append(self, name, line):
        existing = self.section(name)
        self.set_section(name, (existing + "\n" if existing else "") + line)

    def note(self, kind, text):
        """Add one dated line to `## Notes`, the only section the tool writes."""
        self.append("Notes", "- {} {}: {}".format(now()[:10], kind, text))

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("---\n" + "\n".join(self.front) + "\n---\n" + self.body.rstrip("\n") + "\n")

    @property
    def id(self):
        return self.get("id")

    @property
    def status(self):
        return self.get("status")

    @property
    def number(self):
        digits = re.sub(r"\D", "", self.id)
        return int(digits) if digits else 0

    @property
    def human(self):
        return self.get("human") == "true"

    @property
    def summary(self):
        return "checkin" in self.list("tags")

    @property
    def light(self):
        return self.get("effort", "standard") == "light"

    def paths(self, name):
        found = []
        for part in re.split(r"[,\n]", self.section(name)):
            part = part.strip().lstrip("-*").strip().strip("`").strip()
            if part and not part.startswith("("):
                found.append(part)
        return found

    def outcome(self):
        for line in self.section("Result").split("\n"):
            line = line.strip()
            if line and not line.startswith(PLACEHOLDER) and not (line.startswith("(") and line.endswith(")")):
                return line
        return ""

    def why_dropped(self):
        for line in reversed(self.section("Notes").split("\n")):
            if " dropped: " in line:
                return line.split(" dropped: ", 1)[1].strip()
        return self.section("Dropped").split("\n")[-1].lstrip("- ")  # cards written before v0.2


def load(root):
    queue = os.path.join(root, "queue")
    if not os.path.isdir(queue):
        die("no queue at {}. Run `cards.py init` in the project first.".format(queue))
    cards = {}
    for name in sorted(os.listdir(queue)):
        if not name.endswith(".md"):
            continue
        try:
            card = Card(os.path.join(queue, name))
        except (OSError, UnicodeDecodeError) as error:
            warn("skipping {}: {}".format(name, error))
            continue
        if not card.id or card.status not in STATUSES or card.get("priority", "P1") not in PRIORITIES:
            warn("skipping {}: id '{}', status '{}' or priority '{}' is not valid. Fix the file.".format(
                name, card.id, card.status, card.get("priority")))
            continue
        if card.id in cards:
            warn("skipping {}: id {} is already used by {}".format(name, card.id, os.path.basename(cards[card.id].path)))
            continue
        cards[card.id] = card
    return cards


def settings(root):
    """cards/settings.json is optional. Unknown or bad values fall back to the defaults."""
    found = dict(SETTINGS)
    path = os.path.join(root, "settings.json")
    if not os.path.exists(path):
        return found
    try:
        with open(path, encoding="utf-8") as f:
            given = json.load(f)
    except (OSError, ValueError) as error:
        warn("ignoring settings.json: {}".format(error))
        return found
    if not isinstance(given, dict):
        warn("ignoring settings.json: it is not a JSON object")
        return found
    for key, value in given.items():
        if key in ("slots", "batch") and isinstance(value, int) and not isinstance(value, bool) and value >= 1:
            found[key] = value
        elif key == "fill" and value in ("high", "all"):
            found[key] = value
        else:
            warn("ignoring settings.json key {}: {!r}".format(key, value))
    return found


def need(cards, cid):
    if cid not in cards:
        die("no card {}".format(cid))
    return cards[cid]


def parse_time(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S %z").timestamp()
    except ValueError:
        return None


def waiting_on(card, cards):
    return [d for d in card.list("depends_on") if d not in cards or cards[d].status not in CLOSED]


def effective_priority(cards):
    """A card counts as high as any open card that waits on it."""
    best = {cid: PRIORITIES[c.get("priority", "P1")] for cid, c in cards.items() if c.status not in CLOSED}
    changed = True
    while changed:
        changed = False
        for cid in best:
            for dep in cards[cid].list("depends_on"):
                if dep in best and best[cid] < best[dep]:
                    best[dep] = best[cid]
                    changed = True
    return best


def runnable(cards):
    """Ready cards in pick order: highest effective priority first, oldest first on ties.

    Returns worker cards, human cards, summary cards and the effective priorities."""
    best = effective_priority(cards)
    ready = [c for c in cards.values() if c.status == "todo" and not waiting_on(c, cards)]
    ready.sort(key=lambda c: (best[c.id], parse_time(c.get("filed")) or 0, c.number))
    humans = [c for c in ready if c.human]
    summaries = [c for c in ready if c.summary and not c.human]
    agents = [c for c in ready if not c.human and not c.summary]
    return agents, humans, summaries, best


def should_stop(cards, best):
    """Stop when no open card has effective P0 or P1, ready or not, no human card is open,
    and nothing is running or waiting for review."""
    open_cards = [c for c in cards.values() if c.status not in CLOSED]
    if not cards or any(best[c.id] < 2 for c in open_cards) or any(c.human for c in open_cards):
        return False
    return not any(c.status in ("doing", "review") for c in open_cards)


def overlap(card, cards, extra=()):
    """The id of a doing card (or an entry in `extra`) whose Outputs share a path with this card's."""
    mine = set(card.paths("Outputs"))
    others = [c for c in cards.values() if c.status == "doing"] + list(extra)
    for other in others:
        if other.id != card.id and mine & set(other.paths("Outputs")):
            return other.id
    return ""


def workers(cards):
    """Running workers, one per batch: a list of lists of doing cards."""
    groups = {}
    for card in cards.values():
        if card.status == "doing":
            groups.setdefault(card.get("batch") or card.id, []).append(card)
    return list(groups.values())


def batch_members(card, cards):
    ids = [i for i in card.get("batch").split("+") if i] or [card.id]
    return [cards[i] for i in ids if i in cards] or [card]


def last_change(card, root):
    project = os.path.dirname(root)
    targets = [card.path, os.path.join(root, "scratch", card.id)]
    targets += [os.path.join(project, p) for p in card.paths("Outputs")]
    latest = 0
    for target in targets:
        paths = [target]
        if os.path.isdir(target):
            paths = [os.path.join(folder, name) for folder, _, files in os.walk(target) for name in files]
        for path in paths:
            try:
                latest = max(latest, os.path.getmtime(path))
            except OSError:
                pass  # files can vanish mid-scan, for example a browser's temporary profile
    return latest


def recent_activity(card, root):
    """Reasons a doing card may still have a live worker. An empty list means none."""
    cutoff = time.time() - RECENT_MINUTES * 60
    reasons = []
    started = parse_time(card.get("started"))
    if started and started > cutoff:
        reasons.append("it was claimed less than {} minutes ago".format(RECENT_MINUTES))
    if last_change(card, root) > cutoff:
        reasons.append("its card, scratch folder or outputs changed less than {} minutes ago".format(RECENT_MINUTES))
    return reasons


def rel(path, root):
    return os.path.relpath(path, os.path.dirname(root))


def refresh_rules(root, quiet=False):
    """Rewrite the tool-owned part of RULES.md when its version differs. The text below the marker is kept."""
    path = os.path.join(root, "RULES.md")
    top = "{}\n{}\n{}\n".format(RULES_VERSION, RULES.replace("{root}", os.path.basename(root)), RULES_MARKER)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(top)
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text.startswith(RULES_VERSION + "\n"):
        return
    for marker in (RULES_MARKER, RULES_V0_MARKER):
        if marker in text:
            below = text.split(marker, 1)[1].lstrip("\n")
            break
    else:
        warn("RULES.md has no marker line, so its worker rules were not updated to {}. "
             "Put your project rules below a line that reads exactly: {}".format(VERSION, RULES_MARKER))
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(top + ("\n" + below if below.strip() else ""))
    if not quiet:
        print("note: updated the worker rules in RULES.md to {}".format(VERSION), file=sys.stderr)


def cmd_init(args, root):
    chosen = args.dir or os.environ.get("CARDS_DIR")
    if (not chosen and os.path.isdir(root) and os.listdir(root)
            and not any(os.path.exists(os.path.join(root, n)) for n in ("queue", "RULES.md"))):
        die("{} already exists and was not made by this tool. Pass --dir <another folder> "
            "(or set CARDS_DIR) to keep the queue somewhere else.".format(root))
    os.makedirs(os.path.join(root, "queue"), exist_ok=True)
    os.makedirs(os.path.join(root, "scratch"), exist_ok=True)
    refresh_rules(root, quiet=True)
    brief = os.path.join(root, "BRIEF.md")
    if not os.path.exists(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(BRIEF)
    overview = os.path.join(root, "OVERVIEW.md")
    if not os.path.exists(overview):
        with open(overview, "w", encoding="utf-8") as f:
            f.write(OVERVIEW)
    if args.learned:
        rule = LEARNED_RULE.replace("{root}", os.path.basename(root))
        path = os.path.join(root, "RULES.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if rule.strip().split("\n")[0] not in text:
            with open(path, "a", encoding="utf-8") as f:
                f.write(rule)
            print("learned lines: on (rule added below the marker in RULES.md)")
    here = os.path.dirname(os.path.abspath(__file__))
    source, target = os.path.join(here, "cards.py"), os.path.join(root, "cards.py")
    if os.path.abspath(source) != os.path.abspath(target):
        shutil.copyfile(source, target)  # the tool is refreshed on every init
    refresh_dashboard(root)
    print("ready: {} (tool {}). From now on use `python3 {}`.".format(
        rel(root, root), VERSION, rel(os.path.join(root, "cards.py"), root)))
    print("live view for the user: {}".format(rel(os.path.join(root, "dashboard.html"), root)))


def cmd_new(args, root):
    cards = load(root)
    for dep in args.after:
        need(cards, dep)
    if args.spawned_by:
        need(cards, args.spawned_by)
    if args.checkin and args.human:
        die("a --checkin card is written by the orchestrator, so it cannot also be --human")
    if args.checkin and not args.after:
        # No --after would make the summary ready before any work. Wait on the open cards instead.
        args.after = sorted(c.id for c in cards.values() if c.status not in CLOSED and not c.summary)
        if args.after:
            print("note: --checkin waits on the open cards: {}".format(", ".join(args.after)), file=sys.stderr)
    number = max([c.number for c in cards.values()] + [0]) + 1
    cid = "C{:03d}".format(number)
    slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")[:40].strip("-") or "card"
    priority = args.priority or ("P1" if args.checkin or not args.spawned_by else "P2")
    tags = (["checkin"] if args.checkin else []) + [t for t in args.tags if t != "checkin"]
    front = ["id: " + cid, "title: " + args.title, "status: todo", "priority: " + priority, "effort: " + args.effort,
             "depends_on: [{}]".format(", ".join(args.after))]
    if tags:
        front.append("tags: [{}]".format(", ".join(tags)))
    if args.spawned_by:
        front.append("spawned_by: " + args.spawned_by)
    area = " ".join(args.area.split())
    if area:
        front.append("area: " + area)
    front += ["human: " + ("true" if args.human else "false"), "filed: " + now(), "started:", "finished:", "attempts: 0"]
    do = args.do or (CHECKIN_DO if args.checkin else "(what to do; leave the how to the worker)")
    body = "\n## Do\n{}\n\n## Done when\n{}\n".format(do, args.done_when or "(checkable lines)")
    if args.inputs:
        body += "\n## Inputs\n{}\n".format(args.inputs)
    if args.outputs:
        body += "\n## Outputs\n{}\n".format(args.outputs)
    body += "\n## Result\n{}: first line is the outcome)\n\n## Proposed cards\n(optional)\n".format(PLACEHOLDER)
    path = os.path.join(root, "queue", "{}-{}.md".format(cid, slug))
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n" + "\n".join(front) + "\n---\n" + body)
    print("{} {}".format(cid, rel(path, root)))


def plan(cards, conf, slots_override=None):
    """The `ready` lines, as (word, [cards], priority) in pick order."""
    agents, humans, summaries, best = runnable(cards)
    slots = slots_override if slots_override is not None else conf["slots"]
    free = max(slots - len(workers(cards)), 0)
    lines, started, taken = [], [], set()
    for card in agents:
        if card.id in taken:
            continue
        tier = best[card.id]
        clash = overlap(card, cards, started)
        if tier == 2 and conf["fill"] == "high":
            lines.append(("later", [card], tier))
        elif clash:
            lines.append(("wait", [card], tier, clash))
        elif not free:
            lines.append(("later", [card], tier))
        else:
            group = [card]
            if card.light:
                for other in agents:
                    if len(group) >= conf["batch"]:
                        break
                    if (other.id not in taken and other is not card and other.light and best[other.id] == tier
                            and not overlap(other, cards, started + group)):
                        group.append(other)
            taken.update(c.id for c in group)
            started.extend(group)
            free -= 1
            lines.append(("start", group, tier))
    lines += [("ask", [c], best[c.id]) for c in humans]
    lines += [("summarize", [c], best[c.id]) for c in summaries]
    return lines, len(workers(cards)), slots


def cmd_ready(args, root):
    cards = load(root)
    lines, running, slots = plan(cards, settings(root), args.n)
    print("{} running, {} free of {}.".format(running, max(slots - running, 0), slots))
    for line in lines:
        word, group, tier = line[0], line[1], line[2]
        ids = "+".join(c.id for c in group)
        titles = " | ".join(c.get("title") for c in group)
        if word == "start":
            print("  start {} P{} {:<8} {}".format(ids, tier, group[0].get("effort", "standard"), titles))
        elif word == "wait":
            print("  wait  {} outputs overlap with {}".format(ids, line[3]))
        elif word == "later":
            print("  later {} P{} {}".format(ids, tier, titles))
        else:
            print("  {:<5} {} {}".format(word, ids, titles))
    if not lines:
        print("  nothing is ready.")


def cmd_claim(args, root):
    cards = load(root)
    conf = settings(root)
    ids = [i for raw in args.ids for i in raw.split("+") if i]
    if len(set(ids)) != len(ids):
        die("the same id is listed twice")
    group = [need(cards, cid) for cid in ids]
    best = effective_priority(cards)
    for card in group:
        if card.status != "todo":
            die("{} is {}, not todo".format(card.id, card.status))
        blockers = waiting_on(card, cards)
        if blockers:
            die("{} waits on {}".format(card.id, ", ".join(blockers)))
        if card.human:
            die("{} is for the user. Ask them, then use `answer`.".format(card.id))
        if card.summary:
            die("{} is a wave summary. Write its Result inline, then `accept` it.".format(card.id))
        clash = overlap(card, cards, [c for c in group if c is not card])
        if clash:
            die("{} writes the same outputs as {}. Run them one after another.".format(card.id, clash))
    if len(group) > 1:
        if len(group) > conf["batch"]:
            die("a batch holds at most {} cards (settings.json `batch`)".format(conf["batch"]))
        if not all(c.light for c in group):
            die("only light cards can share a worker")
        if len({best[c.id] for c in group}) > 1:
            die("batched cards must have the same effective priority")
    batch = "+".join(c.id for c in group)
    for card in group:
        card.set("status", "doing")
        if len(group) > 1:
            card.set("batch", batch)
        else:
            card.unset("batch")
        card.set("started", now())
        card.set("finished", "")
        card.set("attempts", str(int(card.get("attempts", "0") or 0) + 1))
        card.save()
        os.makedirs(os.path.join(root, "scratch", card.id), exist_ok=True)
    project, name = os.path.dirname(root), os.path.basename(root)
    print("# effort {}: start one fresh background agent named card-{} with this prompt:\n".format(
        group[0].get("effort", "standard"), batch.replace("+", "-")))
    if len(group) == 1:
        print(PROMPT.format(id=batch, project=project, root=name, card=rel(group[0].path, root)))
    else:
        listing = "\n".join("- {} {}".format(c.id, rel(c.path, root)) for c in group)
        print(BATCH_PROMPT.format(ids=", ".join(ids), project=project, root=name, cards=listing))


def reaches(cards, start, target):
    """True if `start` already depends on `target`, directly or through other cards."""
    seen, stack = set(), [start]
    while stack:
        cid = stack.pop()
        if cid == target:
            return True
        if cid in seen or cid not in cards:
            continue
        seen.add(cid)
        stack.extend(cards[cid].list("depends_on"))
    return False


def cmd_depend(args, root):
    cards = load(root)
    for dep in args.on:
        need(cards, dep)
    changed = []
    for cid in args.ids:
        card = need(cards, cid)
        if card.status not in ("todo", "blocked"):
            die("{} is {}. Only todo or blocked cards can change what they wait on.".format(card.id, card.status))
        current = card.list("depends_on")
        if args.remove:
            updated = [d for d in current if d not in args.on]
        else:
            for dep in args.on:
                if dep == cid or reaches(cards, dep, cid):
                    die("{} cannot wait on {}: {} already waits on {}, which would be a loop.".format(cid, dep, dep, cid))
            updated = current + [d for d in args.on if d not in current]
        if updated != current:
            card.set("depends_on", "[{}]".format(", ".join(updated)))
            card.save()
            changed.append("{} now waits on: {}".format(cid, ", ".join(updated) or "nothing"))
    print("\n".join(changed) or "nothing changed")


def cmd_result(args, root):
    card = need(load(root), args.id)
    print("{} [{}] {}".format(card.id, card.status, card.get("title")))
    for name in ("Done when", "Result", "Proposed cards", "Notes", "Review notes"):
        text = card.section(name)
        if len(text) > RESULT_CAP:
            text = text[:RESULT_CAP] + "\n(cut at {} characters; the rest is in {})".format(RESULT_CAP, rel(card.path, os.path.dirname(card.path)))
        if text:
            print("\n## {}\n{}".format(name, text))


def cmd_accept(args, root):
    cards = load(root)
    card = need(cards, args.id)
    if card.status not in ("review", "doing", "blocked", "todo"):
        die("{} is {}".format(card.id, card.status))
    if card.status == "todo" and waiting_on(card, cards):
        die("{} still waits on {}".format(card.id, ", ".join(waiting_on(card, cards))))
    if not card.outcome():
        die("{} has an empty Result. Reject it or have the worker finish.".format(card.id))
    project = os.path.dirname(root)
    missing = [p for p in card.paths("Outputs") if not os.path.exists(os.path.join(project, p))]
    if missing and not args.force:
        die("{} lists outputs that do not exist: {}. Use --force to accept anyway.".format(card.id, ", ".join(missing)))
    card.set("status", "done")
    card.set("finished", now())
    card.save()
    print("{} done: {}".format(card.id, card.outcome()))
    if not re.search(r"^\W*not checked:", card.section("Result"), re.I | re.M):
        print("warning: {}'s Result has no `Not checked:` line.".format(card.id))
    proposed = card.section("Proposed cards")
    if proposed and not proposed.startswith("(optional"):
        print("\nIt proposed cards. File the ones worth doing with `new ... --from {}`:\n{}".format(card.id, proposed))


def cmd_reject(args, root):
    card = need(load(root), args.id)
    if card.status not in ("review", "doing", "blocked"):
        die("{} is {}. Only a review, doing or blocked card can be rejected.".format(card.id, card.status))
    card.set("status", "todo")
    card.note("rejected", args.reason)
    card.save()
    print("{} back to todo".format(card.id))


def cmd_retry(args, root):
    card = need(load(root), args.id)
    if card.status != "doing":
        die("{} is {}. `retry` is for a doing card whose worker died; use `reject` or `answer` otherwise.".format(
            card.id, card.status))
    reasons = [] if args.force else recent_activity(card, root)
    if reasons:
        die("{} may still have a live worker: {}. If the worker is gone, run `retry {} --force`.".format(
            card.id, " and ".join(reasons), card.id))
    card.set("status", "todo")
    card.note("died", args.reason or "worker stopped without finishing (attempt {})".format(card.get("attempts", "1")))
    card.save()
    print("{} back to todo. Its partial Result is kept.".format(card.id))


def cmd_priority(args, root):
    card = need(load(root), args.id)
    if card.status in CLOSED:
        die("{} is {}. Closed cards keep their priority.".format(card.id, card.status))
    card.set("priority", args.level)
    card.save()
    print("{} is now {}".format(card.id, args.level))


def cmd_answer(args, root):
    card = need(load(root), args.id)
    if card.human:
        if card.status in CLOSED:
            die("{} is already {}".format(card.id, card.status))
        card.set_section("Result", args.text)
        card.set("status", "done")
        card.set("finished", now())
        card.save()
        print("{} done".format(card.id))
    elif card.status == "blocked":
        card.note("human", args.text)
        card.set("status", "todo")
        card.save()
        print("{} back to todo with the answer noted. Its partial Result is kept.".format(card.id))
    else:
        die("{} is a worker card and is {}. `answer` is for human cards and blocked cards.".format(card.id, card.status))


def cmd_drop(args, root):
    card = need(load(root), args.id)
    if card.status in CLOSED:
        die("{} is already {}".format(card.id, card.status))
    card.set("status", "dropped")
    card.set("finished", now())
    card.note("dropped", args.reason)
    card.save()
    print("{} dropped".format(card.id))


def cmd_check(args, root):
    cards = load(root)
    quiet = True
    for card in sorted(cards.values(), key=lambda c: c.number):
        if card.status == "review":
            print("review  {} {}".format(card.id, card.outcome() or "(empty Result)"))
        elif card.status == "blocked":
            print("blocked {} {}".format(card.id, card.outcome() or card.get("title")))
        elif card.status == "done" and not card.outcome():
            print("noanswer {} is done with no answer line".format(card.id))
        else:
            continue
        quiet = False
    for group in workers(cards):
        changed = max(last_change(c, root) for c in batch_members(group[0], cards))
        if changed and (time.time() - changed) / 60 > STALE_MINUTES:
            print("stale   {} no file change for over {} minutes (attempt {})".format(
                "+".join(c.id for c in group), STALE_MINUTES, group[0].get("attempts", "1")))
            quiet = False
    for card in cards.values():
        for dep in card.list("depends_on"):
            if dep not in cards:
                print("broken  {} depends on {}, which does not exist".format(card.id, dep))
                quiet = False
    state = overview_state(root, cards)
    if state and state[2]:
        print("overview  stale: {} cards closed since it was last written".format(state[2]))
        quiet = False
    if state and state[3]:
        print("overview  placeholder: still the init text")
        quiet = False
    if quiet:
        print("nothing needs attention.")


def brief_lines(root, name):
    path = os.path.join(root, "BRIEF.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    match = re.search(r"^## {}[ \t]*\n(.*?)(?=^## |\Z)".format(re.escape(name)), text, re.S | re.M)
    lines = []
    for line in (match.group(1) if match else "").split("\n"):
        line = line.strip().lstrip("-*").strip()
        if line and not line.startswith("("):
            lines.append(line)
    return lines


def first_sentence(text, cap=160):
    """The first sentence of a section as one plain line, at most `cap` characters."""
    para = re.split(r"\n\s*\n", text.strip())[0] if text.strip() else ""
    if para.startswith("("):
        return ""  # the template's placeholder, not a sentence
    para = " ".join(part.strip().lstrip("-*0123456789.) ").strip() for part in para.split("\n"))
    para = re.sub(r"[`*_]", "", para).strip()
    match = re.search(r"[.!?](\s|$)", para)
    sentence = para[:match.start() + 1] if match else para
    return sentence if len(sentence) <= cap else sentence[:cap - 1].rstrip() + "…"


def wave_numbers(cards):
    """SPEC 6.4: the current wave, and a function giving any card's wave. Nothing is stored."""
    done = sorted((c for c in cards.values() if c.summary and c.status == "done"),
                  key=lambda c: (parse_time(c.get("finished")) or 0, c.number))
    finished = [parse_time(c.get("finished")) or 0 for c in done]
    rank = {c.id: i + 1 for i, c in enumerate(done)}
    current = len(done) + 1

    def wave_of(card):
        if card.status not in CLOSED:
            return current
        if card.id in rank:
            return rank[card.id]
        when = parse_time(card.get("finished"))
        return current if when is None else 1 + sum(1 for t in finished if t < when)
    return current, wave_of


def depths(cards, waves):
    """Longest depends_on chain within each card's own wave."""
    memo = {}

    def depth(cid, trail=()):
        if cid in memo:
            return memo[cid]
        if cid in trail:
            return 0  # a cycle; `depend` refuses to make one, but a hand edit might
        best = 0
        for dep in cards[cid].list("depends_on"):
            if dep in cards and waves[dep] == waves[cid]:
                best = max(best, 1 + depth(dep, trail + (cid,)))
        memo[cid] = best
        return best
    return {cid: depth(cid) for cid in cards}


def learned_lines(card):
    return [line.strip().lstrip("-*").strip() for line in card.section("Learned").split("\n")
            if line.strip().lstrip("-*").strip() and not line.strip().startswith("(")]


def ruled_out(card):
    return card.status == "dropped" or card.outcome().startswith("Ruled out:")


def status_data(root, cards):
    agents, humans, summaries, best = runnable(cards)
    ready_ids = [c.id for c in agents + summaries]
    current, wave_of = wave_numbers(cards)
    waves = {cid: wave_of(c) for cid, c in cards.items()}
    depth = depths(cards, waves)
    rows = []
    for card in sorted(cards.values(), key=lambda c: c.number):
        if card.status == "todo" and card.id in ready_ids:
            column = "next"
        elif card.status == "todo" and card in humans:
            column = "you"
        elif card.status == "todo":
            column = "later"
        elif card.status == "blocked":
            column = "you"
        else:
            column = {"doing": "running", "review": "review", "done": "done", "dropped": "ruled_out"}[card.status]
        touched = last_change(card, root) if card.status in ("doing", "review") else 0
        rows.append({
            "id": card.id, "title": card.get("title"), "status": card.status, "column": column,
            "priority": "P{}".format(best.get(card.id, PRIORITIES.get(card.get("priority", "P1"), 1))),
            "human": card.human, "depends_on": card.list("depends_on"),
            "waiting_on": waiting_on(card, cards), "spawned_by": card.get("spawned_by"),
            "effort": card.get("effort", "standard"), "attempts": card.get("attempts", "0"),
            "batch": card.get("batch"), "tags": card.list("tags"),
            "started": parse_time(card.get("started")), "finished": parse_time(card.get("finished")),
            "outcome": card.outcome()[:200], "do": card.section("Do")[:600], "done_when": card.section("Done when")[:600],
            "result": card.section("Result")[:1500] if card.outcome() else "",
            "why_dropped": card.why_dropped() if card.status == "dropped" else "",
            "wave": waves[card.id], "depth": depth[card.id], "outputs": card.paths("Outputs"),
            "area": card.get("area"),
            "touched": touched or None, "ruled_out": ruled_out(card), "learned": learned_lines(card),
            "summary": first_sentence(card.section("Why")) or first_sentence(card.section("Do")),
            "body": card.body.strip()[:BODY_CAP],
        })
    wave_rows = []
    for n in range(1, current + 1):
        members = [c for c in cards.values() if waves[c.id] == n]
        mark = [c for c in sorted(members, key=lambda c: c.number) if c.summary]
        wave_rows.append({"n": n, "summary": mark[-1].id if mark else None,
                          "done": sum(1 for c in members if c.status in CLOSED), "total": len(members)})
    high = [c for c in cards.values() if PRIORITIES.get(c.get("priority", "P1"), 1) < 2]
    checkpoint = next((c for c in sorted(cards.values(), key=lambda c: c.number)
                       if c.human and c.status not in CLOSED), None)
    return {
        "schema": 2, "updated": time.time(), "project": os.path.basename(os.path.dirname(root)),
        "goal": brief_lines(root, "Goal"), "done_when": brief_lines(root, "Done when"),
        "counts": {s: sum(1 for c in cards.values() if c.status == s) for s in STATUSES},
        "high_total": len(high), "high_closed": sum(1 for c in high if c.status in CLOSED),
        "checkpoint": {"id": checkpoint.id, "title": checkpoint.get("title")} if checkpoint else None,
        "wave": current, "waves": wave_rows, "later": brief_lines(root, "Later"),
        "brief": "BRIEF.md" if os.path.exists(os.path.join(root, "BRIEF.md")) else None,
        "stale_minutes": STALE_MINUTES, "overview": overview_data(root, cards), "areas": area_rows(cards),
        "key_path": key_path(cards), "decisions": decisions_data(root), "cards": rows,
    }


def overview_state(root, cards):
    """(text, written, closed, placeholder) for cards/OVERVIEW.md. closed counts cards finished since it was written.
    None when the file is missing or unreadable."""
    path = os.path.join(root, "OVERVIEW.md")
    try:
        written = os.path.getmtime(path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return None
    closed = sum(1 for c in cards.values() if (parse_time(c.get("finished")) or 0) > written)
    placeholder = any(body.strip() == OVERVIEW_PLACEHOLDER for body in re.split(r"(?m)^## .*$", text)[1:])
    return text, written, closed, placeholder


def overview_data(root, cards):
    """cards/OVERVIEW.md as {text, updated, stale, placeholder}, or None when the file is missing or unreadable."""
    state = overview_state(root, cards)
    if state is None:
        return None
    text, written, closed, placeholder = state
    return {"text": text[:OVERVIEW_CAP], "updated": written, "stale": closed > 0, "placeholder": placeholder}


def area_rows(cards):
    """One row per area label, in the order of each area's first card. Dropped cards count in total only."""
    rows = {}
    for card in sorted(cards.values(), key=lambda c: c.number):
        name = card.get("area")
        if not name:
            continue
        row = rows.setdefault(name, {"name": name, "total": 0, "done": 0, "open": 0})
        row["total"] += 1
        row["done"] += card.status == "done"
        row["open"] += card.status not in CLOSED
    return list(rows.values())


def key_path(cards):
    """Ids of the P0 cards that are open or done, and of everything they depend on, directly or not."""
    found, stack = set(), [c.id for c in cards.values() if c.get("priority") == "P0" and c.status != "dropped"]
    while stack:
        cid = stack.pop()
        if cid in found or cid not in cards:
            continue
        found.add(cid)
        stack.extend(cards[cid].list("depends_on"))
    return sorted(found, key=lambda cid: cards[cid].number)


def decisions_data(root):
    """Entries of cards/DECISIONS.md written as `## D-001: title`, each with its text cut at DECISION_CAP."""
    try:
        with open(os.path.join(root, "DECISIONS.md"), encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return []
    found = []
    for m in re.finditer(r"^## (D-\d+)[ \t]*[:.\u2014-]?[ \t]*([^\n]*)(?:\n|\Z)(.*?)(?=^## |\Z)", text, re.S | re.M):
        found.append({"id": m.group(1), "title": m.group(2).strip(), "text": m.group(3).strip()[:DECISION_CAP]})
    return found


def text_file(path):
    """The text of a file the dashboard may show, or None (missing, binary, unreadable or over 200 KB)."""
    try:
        if os.path.getsize(path) > VIEW_CAP:
            return None
        with open(path, "rb") as f:
            raw = f.read()
        if b"\0" in raw:
            return None
        return raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def viewable_paths(root, cards):
    """Project-relative paths the dashboard can open: both generated notes, then every card's Outputs.
    A directory Output stands for the text files inside it, up to 20. Paths outside the project are skipped."""
    project = os.path.realpath(os.path.dirname(root))
    found = [rel(os.path.join(root, "BRIEF.md"), root), rel(os.path.join(root, "STATUS.md"), root)]
    for card in sorted(cards.values(), key=lambda c: c.number):
        for item in card.paths("Outputs"):
            path = os.path.normpath(os.path.join(project, item))
            if os.path.commonpath([project, os.path.realpath(path)]) != project:
                continue
            if os.path.isdir(path):
                names = sorted(os.path.join(folder, name)
                               for folder, dirs, files in os.walk(path)
                               for name in files if not any(p.startswith(".") for p in
                                                            os.path.relpath(os.path.join(folder, name), path).split(os.sep)))
                found += [os.path.relpath(n, project) for n in names if text_file(n) is not None][:20]
            else:
                found.append(os.path.relpath(path, project))
    unique = []
    for p in found:
        p = p.replace(os.sep, "/")
        if p not in unique:
            unique.append(p)
    return unique


def write_view_files(root, cards):
    """Write cards/view/f<N>.js for each viewable text file. Returns {path: "view/f<N>.js" or None}.
    The number for a path is kept in view/index.json, and a file is rewritten only when its content changed."""
    folder = os.path.join(root, "view")
    os.makedirs(folder, exist_ok=True)
    index_path = os.path.join(folder, "index.json")
    try:
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
        if not isinstance(index, dict):
            index = {}
    except (OSError, ValueError):
        index = {}
    project = os.path.dirname(root)
    files = {}
    for path in viewable_paths(root, cards):
        text = text_file(os.path.join(project, path))
        if text is None:
            files[path] = None
            continue
        if path not in index:
            index[path] = 1 + max([n for n in index.values() if isinstance(n, int)] or [0])
        name = "f{}.js".format(index[path])
        payload = "window.CARDS_FILE({}, {});\n".format(json.dumps(path), json.dumps(text))
        target = os.path.join(folder, name)
        try:
            with open(target, encoding="utf-8") as f:
                same = f.read() == payload
        except OSError:
            same = False
        if not same:
            with open(target, "w", encoding="utf-8") as f:
                f.write(payload)
        files[path] = "view/" + name
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    return files


_warned_dashboard = []


def refresh_dashboard(root):
    """Copy the shipped dashboard.html next to the queue when its version marker differs from the copy's."""
    source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    target = os.path.join(root, "dashboard.html")

    def marker(path):
        try:
            with open(path, encoding="utf-8") as f:
                found = re.search(r"<!-- cards-dashboard [^>]*-->", f.read(4000))
            return found.group(0) if found else None
        except OSError:
            return None
    if os.path.abspath(source) != os.path.abspath(target) and os.path.exists(source):
        if not os.path.exists(target) or marker(source) != marker(target):
            shutil.copyfile(source, target)
    elif not os.path.exists(target) and not _warned_dashboard:
        _warned_dashboard.append(1)
        warn("no dashboard.html next to cards.py or in {}. Reinstall the plugin, then run `cards.py init`.".format(
            os.path.basename(root)))


def write_status(root, cards):
    data = status_data(root, cards)
    by = {s: [c for c in cards.values() if c.status == s] for s in STATUSES}
    agents, humans, summaries, best = runnable(cards)
    rows = data["cards"]
    counts = ", ".join("{} {}".format(len(by[s]), s) for s in STATUSES if by[s])
    current = data["waves"][-1]
    lines = ["# Status", "", "## Wave {}: {} of {} done".format(current["n"], current["done"], current["total"]), "",
             "Updated {}. {} cards: {}.".format(now()[:16], len(cards), counts or "none"),
             "Live view: open `dashboard.html` in this folder in a browser.",
             "Big picture in plain English: `OVERVIEW.md`.", ""]

    def block(title, items):
        lines.extend(["## " + title, ""] + (items or ["Nothing."]) + [""])

    def ago(epoch):
        minutes = int((time.time() - epoch) / 60)
        return "{}m ago".format(minutes) if minutes < 120 else "{}h ago".format(minutes // 60)

    block("Needs you", ["- {} {}".format(c.id, c.get("title")) for c in humans] +
          ["- {} blocked: {}".format(c.id, c.outcome() or c.get("title")) for c in by["blocked"]])
    now_rows = []
    for r in rows:
        if r["status"] == "doing":
            touch = ", last file change {}".format(ago(r["touched"])) if r["touched"] else ""
            now_rows.append("- {} running since {}{}: {}".format(
                r["id"], (parse_time_text(r["started"]) or "?"), touch, r["title"]))
        elif r["status"] == "review":
            now_rows.append("- {} waiting for review: {}".format(r["id"], r["title"]))
    block("Right now", now_rows)
    plan_rows = []
    for w in data["waves"]:
        open_ids = [r["id"] for r in rows if r["wave"] == w["n"] and r["status"] not in CLOSED]
        tail = "; open: {}{}".format(", ".join(open_ids[:6]), " +{}".format(len(open_ids) - 6) if len(open_ids) > 6 else "") if open_ids else ""
        plan_rows.append("- Wave {}{}: {} of {} done{}{}".format(
            w["n"], " (current)" if w["n"] == data["wave"] else "", w["done"], w["total"],
            " (summary {})".format(w["summary"]) if w["summary"] else "", tail))
    if data["later"]:
        plan_rows += ["", "### Later", ""] + ["- " + item for item in data["later"]]
    block("Plan", plan_rows)
    finished = sorted((r for r in rows if r["status"] == "done" and not r["ruled_out"] and r["outcome"]),
                      key=lambda r: r["finished"] or 0, reverse=True)
    block("Learned, newest first", ["- {} {}: {}".format(r["id"], r["title"], r["outcome"]) for r in finished[:15]])
    block("Ruled out", ["- {} {}: {}".format(r["id"], r["title"], r["why_dropped"] if r["status"] == "dropped" else r["outcome"])
                        for r in rows if r["ruled_out"]])
    block("All answers", ["- {} {} {}: {}".format(r["id"], r["status"], r["title"],
                                                  r["why_dropped"] if r["status"] == "dropped" else (r["outcome"] or "(no answer line)"))
                          for r in rows if r["status"] in CLOSED])
    with open(os.path.join(root, "STATUS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    data["files"] = write_view_files(root, cards)
    text = json.dumps(data, indent=1)
    with open(os.path.join(root, "status.json"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(root, "status.js"), "w", encoding="utf-8") as f:
        f.write("window.CARDS_STATUS = " + text + ";\n")
    refresh_dashboard(root)
    return data, by, humans, agents, best


def parse_time_text(epoch):
    return datetime.datetime.fromtimestamp(epoch).strftime("%H:%M") if epoch else None


def cmd_status(args, root):
    cards = load(root)
    data, by, humans, agents, best = write_status(root, cards)
    held = [c for c in agents if best[c.id] < 2]
    counts = ", ".join("{} {}".format(len(by[s]), s) for s in STATUSES if by[s])
    current = data["waves"][-1]
    print("{} cards: {}".format(len(cards), counts or "none"))
    print("wave {}: {} of {} done".format(current["n"], current["done"], current["total"]))
    needs = humans + by["blocked"]
    named = ""
    if needs:
        named = " ({}{})".format(", ".join(c.id for c in needs[:3]), " +{}".format(len(needs) - 3) if len(needs) > 3 else "")
    print("needs you: {}{} | running: {} | review: {} | ready: {} ({} are P0 or P1)".format(
        len(needs), named, len(by["doing"]), len(by["review"]), len(agents), len(held)))
    if should_stop(cards, best):
        print("no P0 or P1 work is left. Stop and report; run P2 cards only if the user wants them.")
    print("live view for the user: {} (open in a browser; it refreshes itself)".format(
        rel(os.path.join(root, "dashboard.html"), root)))


def ids_list(text):
    return [x.strip() for x in text.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", help="the cards directory (default: ./cards, or $CARDS_DIR)")
    parser.add_argument("--version", action="version", version="cards " + VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--learned", action="store_true", help="add the Learned-lines rule to RULES.md")
    new = sub.add_parser("new")
    new.add_argument("title")
    new.add_argument("--do")
    new.add_argument("--done-when")
    new.add_argument("--inputs")
    new.add_argument("--outputs")
    new.add_argument("--priority", choices=sorted(PRIORITIES))
    new.add_argument("--effort", choices=EFFORTS, default="standard")
    new.add_argument("--after", type=ids_list, default=[])
    new.add_argument("--from", dest="spawned_by")
    new.add_argument("--human", action="store_true")
    new.add_argument("--checkin", action="store_true", help="a wave summary card the orchestrator writes inline")
    new.add_argument("--tags", type=ids_list, default=[])
    new.add_argument("--area", default="", help="one short label that groups cards, such as data or design")
    ready = sub.add_parser("ready")
    ready.add_argument("-n", type=int, help="free slots to fill (default: settings.json `slots`, or 4)")
    depend = sub.add_parser("depend", help="add or remove what existing cards wait on")
    depend.add_argument("ids", nargs="+")
    depend.add_argument("--on", required=True, type=ids_list)
    depend.add_argument("--remove", action="store_true")
    claim = sub.add_parser("claim")
    claim.add_argument("ids", nargs="+", metavar="id")
    sub.add_parser("result").add_argument("id")
    accept = sub.add_parser("accept")
    accept.add_argument("id")
    accept.add_argument("--force", action="store_true")
    for name, extra in (("reject", "reason"), ("answer", "text"), ("drop", "reason")):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument(extra)
    retry = sub.add_parser("retry")
    retry.add_argument("id")
    retry.add_argument("reason", nargs="?")
    retry.add_argument("--force", action="store_true", help="retry even if the card looks alive")
    priority = sub.add_parser("priority")
    priority.add_argument("id")
    priority.add_argument("level", choices=sorted(PRIORITIES))
    sub.add_parser("check")
    sub.add_parser("status")
    args = parser.parse_args()
    root = find_root(args.dir)
    if args.command != "init" and os.path.isdir(os.path.join(root, "queue")):
        try:
            refresh_rules(root)
        except OSError as error:
            warn("could not refresh RULES.md: {}".format(error))
    globals()["cmd_" + args.command](args, root)
    if args.command in ("init", "new", "depend", "claim", "accept", "reject", "retry", "priority", "answer", "drop"):
        try:
            write_status(root, load(root))  # keep the dashboard live after every change
        except Exception as error:  # the dashboard must never break a queue command
            print("note: could not refresh the dashboard: {}".format(error), file=sys.stderr)


if __name__ == "__main__":
    main()

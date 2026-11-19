#!/usr/bin/env python3
"""Free static checks for the cardhand plugin. No model, standard library only.

  python3 plugin/tests/check.py [PLUGIN_DIR]

PLUGIN_DIR defaults to the folder above this file. Prints one PASS, FAIL or SKIP line per check
(detail lines are indented) and exits 1 if any check fails.

Checks: smoke (every command in SPEC 4 against cards.py in a temp dir, plus each example queue), harness lint, claims lint,
name and version (both manifests, plus the run harness note's size), load budget (SPEC 2.2), and `claude plugin validate`.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

PLUGIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CARDS = os.path.join(PLUGIN, "skills", "start", "scripts", "cards.py")
SKILLS = sorted(glob.glob(os.path.join(PLUGIN, "skills", "*", "SKILL.md")))
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

# SPEC 2.2 caps, in bytes. The last element of each row is a one-line description.
CAPS = [
    ("3 skill names and descriptions", 1000),
    ("start skill body", 5500),
    ("run skill body", 7000),
    ("status skill body", 700),
    ("generated RULES.md", 2000),  # D-037: room for the For you rule
    ("BRIEF template", 1500),
    ("status plus check output", 600),
    ("one-card claim output", 500),
    ("worker prompt plus RULES", 2500),
]
HEAVIEST_CAP = 20000
HARNESS_NOTE_CAP = 3000  # skills/run/references/harness.md: a note, not a second manual

HARNESS_WORDS = ["haiku", "sonnet", "opus", "TaskStop", "CLAUDE_PLUGIN_ROOT", "subagent_type", "Claude"]
CLAIM_PHRASES = ["thin orchestrator", "survives compaction", "unique"]
CUT_FLAGS = [r"--cards(?![\w-])", r"--now(?![\w-])", r"--free(?![\w-])", r"--why(?![\w-])"]  # `for:` was once a cut key; D-037 made it the goal link


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def size(path):
    with open(path, "rb") as f:
        return len(f.read())


def frontmatter(text):
    """Return {key: value} of a leading --- block. Handles `key: value` and folded `key: >` blocks."""
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    out, key = {}, None
    for line in (m.group(1).split("\n") if m else []):
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            out[key] = kv.group(2).strip().strip("\"'")
            if out[key] in (">", "|", ">-", "|-"):
                out[key] = ""
        elif key and line.strip():
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def strip_claude_section(text):
    """Remove a `## On Claude Code` section (up to the next `## ` heading or the end)."""
    return re.sub(r"(?ms)^## On Claude Code\b.*?(?=^## |\Z)", "", text)


def shipped_files():
    """Text files that ship: everything under PLUGIN except tests, caches and tool state."""
    out = []
    for dirpath, dirs, files in os.walk(PLUGIN):
        dirs[:] = [d for d in dirs if d not in ("tests", "__pycache__", ".omc", ".git")]
        for name in files:
            path = os.path.join(dirpath, name)
            try:
                read(path)
            except (UnicodeDecodeError, OSError):
                continue
            out.append(path)
    return sorted(out)


def rel(path):
    return os.path.relpath(path, PLUGIN)


# ---------------------------------------------------------------- smoke test

class Smoke:
    def __init__(self):
        self.fails = []
        self.steps = 0

    def ok(self, name, cond, detail=""):
        self.steps += 1
        if not cond:
            self.fails.append(name + (": " + detail.strip().replace("\n", " | ")[:200] if detail else ""))
        return cond

    def run(self, cwd, *args):
        p = subprocess.run([sys.executable, CARDS, *args], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr

    def card(self, cwd, cid):
        found = glob.glob(os.path.join(cwd, "cards", "queue", cid + "-*.md"))
        return found[0] if found else None

    def text(self, cwd, cid):
        return read(self.card(cwd, cid))

    def set_fm(self, cwd, cid, key, value):
        path = self.card(cwd, cid)
        text = read(path)
        head, sep, rest = text.partition("\n---\n")
        if re.search(r"(?m)^%s:" % key, head):
            head = re.sub(r"(?m)^%s:.*$" % key, "%s: %s" % (key, value), head)
        else:
            head += "\n%s: %s" % (key, value)
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + sep + rest)

    def set_result(self, cwd, cid, body):
        path = self.card(cwd, cid)
        text = read(path)
        new = re.sub(r"(?ms)^## Result\n.*?(?=^## |\Z)", "## Result\n" + body + "\n\n", text, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)

    def new(self, cwd, title, *args):
        rc, out = self.run(cwd, "new", title, *args)
        m = re.search(r"\bC\d{3,}\b", out)
        self.ok("new " + title, rc == 0 and m, out)
        return m.group(0) if m else "C000"

    def age(self, cwd, cid, minutes):
        """Backdate a claim: its started time and the mtime of the card and its scratch files."""
        when = time.time() - minutes * 60
        self.set_fm(cwd, cid, "started", time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(when)))
        scratch = os.path.join(cwd, "cards", "scratch", cid)
        paths = [self.card(cwd, cid)] + [os.path.join(folder, name) for folder, _, names in os.walk(scratch) for name in names]
        for path in paths:
            os.utime(path, (when, when))

    def finish(self, cwd, cid, status="review", result="Did the thing.\nmet: it works\nNot checked: nothing known."):
        self.set_result(cwd, cid, result)
        self.set_fm(cwd, cid, "status", status)

    def project(self, root, name):
        cwd = os.path.join(root, name)
        os.makedirs(cwd)
        rc, out = self.run(cwd, "init")
        self.ok(name + ": init", rc == 0 and os.path.isdir(os.path.join(cwd, "cards", "queue")), out)
        return cwd

    # -- sections ---------------------------------------------------------

    def lifecycle(self, root):
        cwd = self.project(root, "life")
        for f in ("RULES.md", "BRIEF.md"):
            self.ok("init writes " + f, os.path.isfile(os.path.join(cwd, "cards", f)))
        self.ok("init: RULES.md has a version line", re.search(r"(?i)version", read(os.path.join(cwd, "cards", "RULES.md"))) is not None)
        self.run(cwd, "init", "--learned")
        rc, out = self.run(cwd, "init", "--learned")
        self.ok("init --learned adds the Learned rule once", rc == 0 and read(os.path.join(cwd, "cards", "RULES.md")).count("## Learned lines") == 1, out)
        a = self.new(cwd, "Alpha", "--effort", "light", "--outputs", "a.txt")
        b = self.new(cwd, "Beta", "--effort", "light", "--outputs", "b.txt")
        c = self.new(cwd, "Gamma", "--effort", "light", "--outputs", "c.txt")
        d = self.new(cwd, "Delta", "--effort", "light", "--outputs", "d.txt")
        e = self.new(cwd, "Epsilon", "--after", a)
        f = self.new(cwd, "Zeta proposal", "--from", a)
        h = self.new(cwd, "Human decision", "--human")
        self.ok("new --from defaults to P2", re.search(r"(?m)^priority: P2", self.text(cwd, f)) is not None)

        rc, out = self.run(cwd, "ready")
        self.ok("ready lists runnable cards", rc == 0 and all(x in out for x in (a, b, c)), out)
        self.ok("ready: waiting card is not started", not any(e in ln and "start" in ln for ln in out.split("\n")), out)
        self.ok("ready: P2 prints later", any(f in ln and "later" in ln for ln in out.split("\n")), out)
        self.ok("ready: human card is asked", any(h in ln for ln in out.split("\n")), out)

        # batching: all or none
        rc, out = self.run(cwd, "claim", d, e)
        self.ok("claim batch is all-or-none", rc != 0 and re.search(r"(?m)^status: todo", self.text(cwd, d)) is not None, out)
        rc, out = self.run(cwd, "claim", a, b, c)
        self.ok("claim A B C", rc == 0, out)
        self.ok("claim prints effort, not a model", "light" in out, out)
        for x in (a, b, c):
            self.ok("batch: %s is doing" % x, re.search(r"(?m)^status: doing", self.text(cwd, x)) is not None)
        self.ok("batch key written", re.search(r"(?m)^batch: .*%s.*%s" % (a, b), self.text(cwd, a)) is not None, self.text(cwd, a)[:300])
        for x, why in ((a, "already doing"), (e, "waits on a dependency"), (h, "is for the human")):
            rc, out = self.run(cwd, "claim", x)
            self.ok("claim refuses a card that %s" % why, rc != 0, out)
        g = self.new(cwd, "Overlap", "--outputs", "a.txt")
        rc, out = self.run(cwd, "claim", g)
        self.ok("claim refuses overlapping outputs", rc != 0, out)
        self.run(cwd, "drop", g, "scratch test")

        # accept: missing output, warning, empty answer
        self.finish(cwd, a, result="Alpha is done.\nmet: yes")
        rc, out = self.run(cwd, "accept", a)
        self.ok("accept refuses a missing Output", rc != 0, out)
        open(os.path.join(cwd, "a.txt"), "w").close()
        rc, out = self.run(cwd, "accept", a)
        self.ok("accept warns when Not checked: is missing", rc == 0 and "not checked" in out.lower(), out)
        self.ok("accept marks done", re.search(r"(?m)^status: done", self.text(cwd, a)) is not None)
        self.finish(cwd, b)
        open(os.path.join(cwd, "b.txt"), "w").close()
        rc, out = self.run(cwd, "accept", b)
        self.ok("accept with Not checked: is quiet and succeeds", rc == 0, out)
        self.set_fm(cwd, c, "status", "review")
        rc, out = self.run(cwd, "accept", c)
        self.ok("accept refuses an empty answer line", rc != 0, out)

        # reject, then retry
        rc, out = self.run(cwd, "reject", c, "needs the numbers")
        self.ok("reject returns to todo", rc == 0 and re.search(r"(?m)^status: todo", self.text(cwd, c)) is not None, out)
        self.ok("reject writes a rejected: note", "rejected:" in self.text(cwd, c))
        rc, out = self.run(cwd, "reject", a, "too late")
        self.ok("reject refuses a closed card", rc != 0, out)
        self.run(cwd, "claim", c)
        self.set_result(cwd, c, "Partial: got halfway.")
        rc, out = self.run(cwd, "retry", c)
        self.ok("retry refuses a card claimed moments ago, and says how to force",
                rc != 0 and "--force" in out and re.search(r"(?m)^status: doing", self.text(cwd, c)) is not None, out)
        rc, out = self.run(cwd, "retry", c, "--force")
        self.ok("retry --force returns doing to todo", rc == 0 and re.search(r"(?m)^status: todo", self.text(cwd, c)) is not None, out)
        self.ok("retry adds a died: note and keeps the Result", "died:" in self.text(cwd, c) and "got halfway" in self.text(cwd, c))
        rc, out = self.run(cwd, "retry", a)
        self.ok("retry refuses a closed card", rc != 0, out)
        t = self.new(cwd, "Old claim", "--effort", "light", "--outputs", "t.txt")
        self.run(cwd, "claim", t)
        self.age(cwd, t, 60)
        rc, out = self.run(cwd, "retry", t)
        self.ok("retry retries a card with old timestamps", rc == 0 and re.search(r"(?m)^status: todo", self.text(cwd, t)) is not None, out)
        u = self.new(cwd, "Output moved", "--effort", "light", "--outputs", "u.txt")
        self.run(cwd, "claim", u)
        self.age(cwd, u, 60)
        open(os.path.join(cwd, "u.txt"), "w").close()
        rc, out = self.run(cwd, "retry", u)
        self.ok("retry refuses a card whose output changed lately", rc != 0 and re.search(r"(?m)^status: doing", self.text(cwd, u)) is not None, out)
        self.run(cwd, "retry", u, "--force")

        # blocked, answer
        self.run(cwd, "claim", d)
        self.finish(cwd, d, status="blocked", result="Blocked: need the path.\nNot checked: everything.")
        rc, out = self.run(cwd, "check")
        self.ok("check lists a blocked card", rc == 0 and d in out, out)
        rc, out = self.run(cwd, "answer", d, "use /srv/data")
        self.ok("answer unblocks and keeps the partial Result",
                rc == 0 and re.search(r"(?m)^status: todo", self.text(cwd, d)) is not None and "Blocked: need the path" in self.text(cwd, d) and "human:" in self.text(cwd, d), out)
        rc, out = self.run(cwd, "answer", h, "yes, go")
        self.ok("answer closes a human card", rc == 0 and re.search(r"(?m)^status: done", self.text(cwd, h)) is not None, out)

        # priority, drop, depend, result
        rc, out = self.run(cwd, "priority", d, "P0")
        self.ok("priority changes the key", rc == 0 and re.search(r"(?m)^priority: P0", self.text(cwd, d)) is not None, out)
        rc, out = self.run(cwd, "priority", d, "P9")
        self.ok("priority refuses a bad value", rc != 0, out)
        rc, out = self.run(cwd, "drop", f, "not needed")
        self.ok("drop closes a card with a dropped: note", rc == 0 and re.search(r"(?m)^status: dropped", self.text(cwd, f)) is not None and "dropped:" in self.text(cwd, f), out)
        x = self.new(cwd, "Waits on delta")
        rc, out = self.run(cwd, "depend", x, "--on", d)
        ready = self.run(cwd, "ready")[1]
        self.ok("depend makes a card wait", rc == 0 and not any(x in ln and "start" in ln for ln in ready.split("\n")), out + ready)
        rc, out = self.run(cwd, "depend", x, "--on", d, "--remove")
        self.ok("depend --remove frees it", rc == 0 and any(x in ln and "start" in ln for ln in self.run(cwd, "ready")[1].split("\n")), out)
        rc, out = self.run(cwd, "result", a)
        self.ok("result prints the answer line", rc == 0 and "Alpha is done" in out, out)
        return cwd

    def checkin(self, root):
        cwd = self.project(root, "wave")
        s1 = self.new(cwd, "Wave work", "--effort", "light")
        w = self.new(cwd, "Wave 1 summary", "--checkin", "--after", s1)
        text = self.text(cwd, w)
        self.ok("--checkin writes tags, P1 and human false",
                re.search(r"(?m)^tags: \[.*checkin.*\]", text) and re.search(r"(?m)^priority: P1", text) and re.search(r"(?m)^human: false", text), text[:400])
        self.run(cwd, "claim", s1)
        self.finish(cwd, s1)
        self.run(cwd, "accept", s1)
        rc, out = self.run(cwd, "ready")
        self.ok("ready prints summarize <id> for a summary card", rc == 0 and re.search(r"summarize\s+%s" % w, out) is not None, out)
        rc, out = self.run(cwd, "claim", w)
        self.ok("claim refuses a summary card", rc != 0, out)
        self.set_result(cwd, w, "Done inline: wave 1 works.\nNot checked: nothing known.")
        rc, out = self.run(cwd, "accept", w)
        self.ok("accept closes the summary inline", rc == 0, out)
        rc, out = self.run(cwd, "status")
        self.ok("status runs", rc == 0, out)
        self.ok("status prints a wave line", "wave" in out.lower(), out)
        for f in ("STATUS.md", "status.json", "dashboard.html"):
            self.ok("status writes " + f, os.path.isfile(os.path.join(cwd, "cards", f)))
        try:
            json.loads(read(os.path.join(cwd, "cards", "status.json")))
            self.ok("status.json parses", True)
        except (OSError, ValueError) as err:
            self.ok("status.json parses", False, str(err))

    def settings(self, root):
        cwd = self.project(root, "fill")
        seed = self.new(cwd, "Seed", "--effort", "light")
        p2 = self.new(cwd, "Later idea", "--from", seed)
        line = lambda: [ln for ln in self.run(cwd, "ready")[1].split("\n") if p2 in ln]
        self.ok("fill high: P2 waits", bool(line()) and "later" in line()[0] and "start" not in line()[0], str(line()))
        with open(os.path.join(cwd, "cards", "settings.json"), "w") as f:
            json.dump({"fill": "all"}, f)
        self.ok("fill all: P2 starts", bool(line()) and "start" in line()[0], str(line()))

        cwd = self.project(root, "batch1")
        ids = [self.new(cwd, "T%d" % i, "--effort", "light", "--outputs", "t%d.txt" % i) for i in range(3)]
        with open(os.path.join(cwd, "cards", "settings.json"), "w") as f:
            json.dump({"batch": 1}, f)
        rc, out = self.run(cwd, "claim", *ids)
        self.ok("batch 1: claim of several ids is refused (inferred; SPEC 8 says batching is off)", rc != 0, out)
        rc, out = self.run(cwd, "claim", ids[0])
        self.ok("batch 1: one id still claims", rc == 0, out)

    def robustness(self, root):
        cwd = self.project(root, "rough")
        ok_id = self.new(cwd, "Fine card", "--effort", "light")
        with open(os.path.join(cwd, "cards", "queue", "C900-bad.md"), "w") as f:
            f.write("---\nid: C900\ntitle: Broken\nstatus: banana\npriority: P9\ndepends_on: [C777]\n---\n\n## Do\nx\n\n## Result\n\n")
        for cmd in ("status", "ready", "check"):
            rc, out = self.run(cwd, cmd)
            self.ok("malformed card: %s survives" % cmd, rc == 0 and "Traceback" not in out, out)
        self.ok("malformed card is reported", "C900" in self.run(cwd, "check")[1] + self.run(cwd, "status")[1])
        self.ok("malformed card does not hide good ones", ok_id in self.run(cwd, "ready")[1])
        # a scratch file that vanishes mid-scan: a dangling symlink makes stat fail
        self.run(cwd, "claim", ok_id)
        scratch = os.path.join(cwd, "cards", "scratch", ok_id)
        os.makedirs(scratch, exist_ok=True)
        os.symlink(os.path.join(scratch, "gone"), os.path.join(scratch, "vanished"))
        rc, out = self.run(cwd, "check")
        self.ok("check survives a vanished scratch file", rc == 0 and "Traceback" not in out, out)

    def overview(self, root):
        cwd = self.project(root, "big")
        path = os.path.join(cwd, "cards", "OVERVIEW.md")
        heads = re.findall(r"(?m)^## (.*)$", read(path)) if os.path.isfile(path) else []
        self.ok("init writes OVERVIEW.md with its six sections", len(heads) == 6 and heads[0] == "What we are trying to do" and heads[-1] == "What happens next", str(heads))
        with open(path, "a") as f:
            f.write("\nMy own words.\n")
        self.run(cwd, "init")
        self.ok("init keeps an existing OVERVIEW.md", "My own words." in read(path))
        a = self.new(cwd, "Gather", "--area", "data", "--priority", "P0")
        b = self.new(cwd, "Model it", "--area", "model", "--after", a, "--priority", "P0")
        c = self.new(cwd, "Side idea", "--area", "data", "--priority", "P2")
        z = self.new(cwd, "Unrelated", "--priority", "P1")
        self.ok("new --area writes the key", re.search(r"(?m)^area: data$", self.text(cwd, a)) is not None)
        with open(os.path.join(cwd, "cards", "DECISIONS.md"), "w") as f:
            f.write("# Decisions\n\n## D-001: Use plain files\nBecause.\n\n## D-002: Skip the cache\n" + "x" * 3000 + "\n")
        rc, out = self.run(cwd, "status")
        self.ok("status runs with the new keys", rc == 0, out)
        try:
            data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
        except (OSError, ValueError) as err:
            self.ok("status.json parses with the new keys", False, str(err))
            return
        self.ok("status.json: overview has text and updated", isinstance(data.get("overview"), dict) and "My own words." in data["overview"].get("text", "") and data["overview"].get("updated"), str(data.get("overview"))[:100])
        self.ok("status.json: every card row has area", all("area" in r for r in data["cards"]) and {r["id"]: r["area"] for r in data["cards"]}[z] == "", "")
        self.ok("status.json: areas count cards", data.get("areas") == [{"name": "data", "total": 2, "done": 0, "open": 2}, {"name": "model", "total": 1, "done": 0, "open": 1}], str(data.get("areas")))
        self.ok("status.json: key_path is the P0 cards and what they wait on", data.get("key_path") == [a, b], str(data.get("key_path")))
        dec = data.get("decisions") or []
        self.ok("status.json: decisions parsed and capped", [d.get("id") for d in dec] == ["D-001", "D-002"] and dec[0].get("title") == "Use plain files" and dec[0].get("text") == "Because." and len(dec[1].get("text", "")) == 2000, str(dec)[:200])
        os.remove(path)
        self.run(cwd, "status")
        data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
        self.ok("status.json: overview is null without the file", data.get("overview") is None, str(data.get("overview")))

    def overview_flags(self, root):
        cwd = self.project(root, "flags")
        path = os.path.join(cwd, "cards", "OVERVIEW.md")
        template = read(path)
        filled = template.replace("(not written yet)", "Written by hand.")
        later, earlier = time.time() + 3600, time.time() - 3600

        def write(text, mtime):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            os.utime(path, (mtime, mtime))

        def overview_json():
            self.run(cwd, "status")
            try:
                return json.loads(read(os.path.join(cwd, "cards", "status.json"))).get("overview") or {}
            except (OSError, ValueError) as err:
                return {"error": str(err)}

        write(filled, later)
        rc, out = self.run(cwd, "check")
        self.ok("check: a fresh overview prints no overview line", rc == 0 and "overview" not in out, out)
        fresh = overview_json()
        self.ok("status: a fresh overview is neither stale nor placeholder", fresh.get("stale") is False and fresh.get("placeholder") is False, str(fresh))

        write(filled, earlier)
        nudges = []
        for title in ("First", "Second", "Third", "Fourth", "Fifth", "Sixth"):
            cid = self.new(cwd, title)
            self.finish(cwd, cid)
            nudges.append(self.run(cwd, "accept", cid)[1])
            if title == "Fifth":
                rc, out = self.run(cwd, "check")
                self.ok("check: an overview 5 cards behind is not flagged yet", "overview" not in out, out)
        self.ok("accept: silent until 5 cards have closed since the overview", not any("rewrite" in n for n in nudges[:4]), str(nudges[:4]))
        self.ok("accept: the 5th and 6th close print the rewrite line once each",
                "rewrite cards/OVERVIEW.md: 5 cards closed since" in nudges[4] and "rewrite cards/OVERVIEW.md: 6 cards closed since" in nudges[5]
                and nudges[5].count("rewrite") == 1, str(nudges[4:]))
        rc, out = self.run(cwd, "check")
        self.ok("check: an overview more than 5 closed cards behind is flagged", "overview  stale: 6 cards closed since it was last written" in out, out)
        stale = overview_json()
        self.ok("status: stale is true and placeholder is false", stale.get("stale") is True and stale.get("placeholder") is False, str(stale))

        write(filled.replace("Written by hand.", "(not written yet)", 1), later)
        rc, out = self.run(cwd, "check")
        self.ok("check: one section still at the init text is flagged", "overview  placeholder: still the init text" in out and "stale" not in out, out)
        left = overview_json()
        self.ok("status: placeholder is true and stale is false", left.get("placeholder") is True and left.get("stale") is False, str(left))

    def for_you(self, root):
        cwd = self.project(root, "foryou")
        brief = os.path.join(cwd, "cards", "BRIEF.md")
        with open(brief, "w", encoding="utf-8") as f:
            f.write("# Brief\n\n## Goal\nTest.\n\n## Done when\n- D1: First thing works.\n- [met] D2: Second thing works.\n- D3 (assumed) Third thing works.\n")
        rc, out = self.run(cwd, "new", "Bad goal", "--for", "D9")
        self.ok("new --for refuses a goal the brief does not list", rc != 0 and "D1" in out, out)
        a = self.new(cwd, "Build it", "--for", "d1", "--priority", "P0")
        b = self.new(cwd, "Build more", "--for", "D1", "--after", a)
        c = self.new(cwd, "Check it", "--for", "D2")
        h = self.new(cwd, "Pick a name", "--human", "--for", "D3")
        self.ok("new --for writes the key, upper-cased", re.search(r"(?m)^for: D1$", self.text(cwd, a)) is not None, self.text(cwd, a)[:300])
        self.ok("new --human writes a For you template", all(x in self.text(cwd, h) for x in ("## For you", "What I need:", "Why it matters:", "How:")), self.text(cwd, h)[:400])
        rc, out = self.run(cwd, "check")
        self.ok("check: a human card with no What I need line is flagged", "foryou  %s" % h in out, out)
        self.run(cwd, "status")
        data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
        row = {r["id"]: r for r in data["cards"]}
        self.ok("status.json: an unfilled template reads as empty strings", row[h]["for_you"] == {"need": "", "why": "", "how": "", "means": ""}, str(row[h]["for_you"]))
        self.ok("status.json: for_goal per card", row[a]["for_goal"] == "D1" and row[h]["for_goal"] == "D3" and row[c]["for_goal"] == "D2", str([row[x]["for_goal"] for x in (a, b, c, h)]))
        path = self.card(cwd, h)
        text = read(path)
        text = re.sub(r"(?s)## For you\n.*?\n\n", "## For you\nWhat I need: Pick a name for the tool.\nWhy it matters: The name goes on the first release.\nHow: Choose one of the three on the list; about 2 minutes.\n\n", text, count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        rc, out = self.run(cwd, "check")
        self.ok("check: a filled For you clears the flag", "foryou" not in out, out)
        self.run(cwd, "status")
        data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
        row = {r["id"]: r for r in data["cards"]}
        self.ok("status.json: for_you holds the three lines", row[h]["for_you"]["need"] == "Pick a name for the tool." and row[h]["for_you"]["how"].startswith("Choose one") and row[h]["for_you"]["why"].startswith("The name"), str(row[h]["for_you"]))
        self.ok("STATUS.md: Needs you shows the plain need", "Pick a name for the tool." in read(os.path.join(cwd, "cards", "STATUS.md")))
        goals = {g["id"]: g for g in data.get("goals", [])}
        self.ok("status.json: goals lists each D line", sorted(goals) == ["D1", "D2", "D3"] and goals["D1"]["text"] == "First thing works." and goals["D3"]["text"] == "(assumed) Third thing works.", str(data.get("goals"))[:300])
        self.ok("status.json: [met] sets met on its goal only", [goals[x]["met"] for x in ("D1", "D2", "D3")] == [False, True, False], str(goals))
        self.ok("status.json: goal counts and next in pick order", goals["D1"]["open"] == 2 and goals["D1"]["done"] == 0 and goals["D1"]["next"] == [a, b], str(goals["D1"]))
        self.run(cwd, "claim", a)
        self.finish(cwd, a)
        self.set_result(cwd, a, "Built.\nmet: yes\nNot checked: nothing known.\n\n## For you\nWhat this means: The first thing now works end to end.")
        self.run(cwd, "accept", a)
        self.run(cwd, "status")
        data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
        goals = {g["id"]: g for g in data["goals"]}
        row = {r["id"]: r for r in data["cards"]}
        self.ok("status.json: a closed card moves from open to done", goals["D1"]["open"] == 1 and goals["D1"]["done"] == 1 and goals["D1"]["next"] == [b], str(goals["D1"]))
        self.ok("status.json: What this means is read on a finished card and its Result stays clean",
                row[a]["for_you"]["means"] == "The first thing now works end to end." and "What this means" not in row[a]["result"], str(row[a]["for_you"]) + row[a]["result"][:200])
        # overview.since: cards closed after OVERVIEW.md was last written, newest first
        ov = os.path.join(cwd, "cards", "OVERVIEW.md")
        past = time.time() - 3600
        os.utime(ov, (past, past))
        self.run(cwd, "status")
        since = json.load(open(os.path.join(cwd, "cards", "status.json")))["overview"].get("since")
        self.ok("status.json: overview.since lists closed cards with id, title and means", since == [{"id": a, "title": "Build it", "means": "The first thing now works end to end."}], str(since))
        os.utime(ov, None)
        self.run(cwd, "status")
        since = json.load(open(os.path.join(cwd, "cards", "status.json")))["overview"].get("since")
        self.ok("status.json: overview.since is empty after a rewrite", since == [], str(since))
        # a blocked worker card counts as needing the person
        self.run(cwd, "claim", c)
        self.set_fm(cwd, c, "status", "blocked")
        rc, out = self.run(cwd, "check")
        self.ok("check: a blocked card with no What I need line is flagged", "foryou  %s" % c in out, out)
        # a card naming a goal the brief later dropped
        self.set_fm(cwd, b, "for", "D7")
        rc, out = self.run(cwd, "check")
        self.ok("check: a card serving an unknown goal is flagged", "goal    %s serves D7" % b in out, out)
        # For you lines are for a person: a card id or a file path in one is flagged
        d = self.new(cwd, "Ask about it", "--human")
        path = self.card(cwd, d)
        text = re.sub(r"(?s)## For you\n.*?\n\n", "## For you\nWhat I need: Check the figure in %s.\nWhy it matters: The write-up cites results/trips.csv.\nHow: Look it over; about 3 minutes.\n\n" % a, read(path), count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        rc, out = self.run(cwd, "check")
        self.ok("check: a For you line with a card id is flagged", "foryou  %s" % d in out and "card id %s" % a in out, out)
        self.ok("check: a For you line with a file path is flagged", "file path results/trips.csv" in out, out)
        text = re.sub(r"(?s)## For you\n.*?\n\n", "## For you\nWhat I need: Check the busiest-month figure.\nWhy it matters: The write-up leans on it; and/or the chart.\nHow: Look it over, about 3 minutes (P1 level).\n\n", read(path), count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        rc, out = self.run(cwd, "check")
        self.ok("check: plain For you lines are not flagged for jargon", "has the card id" not in out and "has the file path" not in out, out)
        # a version change refreshes the worker rules and the dashboard, and keeps the project's own rules
        rules = os.path.join(cwd, "cards", "RULES.md")
        old = re.sub(r"version \d+\.\d+\.\d+", "version 0.0.1", read(rules), count=1).replace("## Learned lines", "## Old learned lines") + "\nProject rule: keep it short.\n"
        with open(rules, "w", encoding="utf-8") as f:
            f.write(old)
        dash = os.path.join(cwd, "cards", "dashboard.html")
        with open(dash, "w", encoding="utf-8") as f:
            f.write("<!-- cards-dashboard v0 -->old")
        rc, out = self.run(cwd, "status")
        now = read(rules)
        version = re.search(r'(?m)^VERSION\s*=\s*"([^"]+)"', read(CARDS)).group(1)
        self.ok("status: an older RULES.md is refreshed to the current version", now.startswith("<!-- cards rules, version %s -->" % version), now[:80])
        self.ok("status: the project's own rules below the marker survive a refresh", "Project rule: keep it short." in now, now[-120:])
        self.ok("status: an older dashboard.html is replaced", "cards-dashboard v0 -->old" not in read(dash), read(dash)[:60])

    def fixes(self, root):
        cwd = self.project(root, "fixes")
        # H2: a line that is only a parenthesised placeholder is not an answer
        a = self.new(cwd, "Placeholder card", "--effort", "light")
        self.set_result(cwd, a, "(not run)")
        self.run(cwd, "status")
        rows = {r["id"]: r for r in json.loads(read(os.path.join(cwd, "cards", "status.json")))["cards"]}
        self.ok("H2: a parenthesised placeholder is not reported as the outcome", rows[a].get("outcome", "") == "", str(rows[a])[:200])
        # H4: --checkin with no --after waits on the open cards
        w = self.new(cwd, "Wave summary", "--checkin")
        self.ok("H4: --checkin without --after waits on open cards", re.search(r"(?m)^depends_on: \[.*%s.*\]" % a, self.text(cwd, w)) is not None, self.text(cwd, w)[:300])
        self.ok("H4: the summary is not ready before the work", "summarize" not in self.run(cwd, "ready")[1], "")
        # M1: # in a title survives
        m = self.new(cwd, "Fix issue #12 in parser")
        rc, out = self.run(cwd, "ready")
        self.ok("M1: ready keeps '#12' in the title", "Fix issue #12 in parser" in out, out)
        # M2: a ## heading inside a Result does not truncate it
        self.set_result(cwd, m, "Did it.\n\n## Details\nthe tail line\nNot checked: nothing known.")
        self.set_fm(cwd, m, "status", "review")
        rc, out = self.run(cwd, "accept", m)
        self.ok("M2: accept sees the whole Result past a ## heading", rc == 0 and "not checked" not in out.lower(), out)
        self.ok("M2: the Result keeps its tail", "the tail line" in self.run(cwd, "result", m)[1], self.run(cwd, "result", m)[1])
        # M3: a title with no ASCII letters still gets a usable file name
        u = self.new(cwd, "\u30c7\u30fc\u30bf")
        self.ok("M3: non-ASCII title file name is not C###-.md", not self.card(cwd, u).endswith("-.md"), self.card(cwd, u))
        # H6: init refuses a cards/ folder it did not create, unless --dir is given
        other = os.path.join(root, "foreign")
        os.makedirs(os.path.join(other, "cards", "Button"))
        rc, out = self.run(other, "init")
        self.ok("H6: init refuses a foreign cards/ folder", rc != 0 and "--dir" in out and not os.path.exists(os.path.join(other, "cards", "queue")), out)
        rc, out = self.run(other, "--dir", os.path.join(other, "work-cards"), "init")
        self.ok("H6: init works with --dir", rc == 0 and os.path.isdir(os.path.join(other, "work-cards", "queue")), out)

    def wave_counts(self, root):
        """A dropped card is closed, not done: the wave header must not count it as done (B24)."""
        cwd = self.project(root, "waves")
        first = self.new(cwd, "Finished work", "--effort", "light")
        gone = self.new(cwd, "Ruled out work", "--effort", "light")
        self.run(cwd, "drop", gone, "not needed")  # dropped first, so both cards land in wave 1
        self.run(cwd, "claim", first)
        self.finish(cwd, first)
        rc, out = self.run(cwd, "accept", first)
        self.ok("wave counts: the done card accepts", rc == 0, out)
        try:
            row = json.loads(read(os.path.join(cwd, "cards", "status.json")))["waves"][0]
        except (OSError, ValueError, KeyError, IndexError) as err:
            self.ok("wave counts: status.json has wave 1", False, str(err))
            return
        self.ok("wave counts: a dropped card is not counted as done",
                row.get("done") == 1 and row.get("dropped") == 1 and row.get("total") == 2, str(row))
        status = read(os.path.join(cwd, "cards", "STATUS.md"))
        self.ok("wave counts: STATUS.md says done and ruled out apart",
                "## Wave 1: 1 of 2 done, 1 ruled out" in status, status[:400])

    def examples(self, root):
        for src in sorted(glob.glob(os.path.join(PLUGIN, "examples", "*"))):
            name = "example " + os.path.basename(src)
            cwd = os.path.join(root, "ex-" + os.path.basename(src))
            shutil.copytree(src, cwd)
            ids = sorted(os.path.basename(p).split("-")[0] for p in glob.glob(os.path.join(cwd, "cards", "queue", "*.md")))
            rc, out = self.run(cwd, "init")
            self.ok(name + ": init", rc == 0, out)
            for cmd in ("status", "ready", "check"):
                rc, out = self.run(cwd, cmd)
                self.ok("%s: %s" % (name, cmd), rc == 0 and "Traceback" not in out and "warning" not in out.lower(), out)
            try:
                data = json.loads(read(os.path.join(cwd, "cards", "status.json")))
                self.ok(name + ": status.json lists every card", sorted(c["id"] for c in data["cards"]) == ids, str(ids))
                keys = ("overview", "areas", "key_path", "decisions", "goals")
                self.ok(name + ": status.json has the overview keys", all(k in data for k in keys), str(sorted(data)))
                self.ok(name + ": status.json has the For you keys", all(set(c.get("for_you", {})) == {"need", "why", "how", "means"} and "for_goal" in c for c in data["cards"])
                        and all(set(g) == {"id", "text", "met", "open", "done", "next"} for g in data["goals"]) and isinstance(data["overview"].get("since"), list), str(data["goals"])[:200])
                problems = dashboard_contract(read(os.path.join(PLUGIN, "skills", "start", "scripts", "dashboard.html")), data)
                self.ok(name + ": every key the dashboard reads is in status.json", not problems, "; ".join(problems))
                src = re.search(r'"since": \[\{[^\n]*', read(CARDS))
                self.ok(name + ": cards.py still writes id, title and means for each since entry", bool(src) and all(('"%s"' % k) in src.group(0) for k in ("id", "title", "means")), str(src))
            except (OSError, ValueError, KeyError) as err:
                self.ok(name + ": status.json parses", False, str(err))

# Names the dashboard's script calls on dates, arrays, strings and DOM nodes: not data keys.
JS_BUILTINS = {"getAttribute", "focus", "classList", "contains", "length", "indexOf", "join", "map", "filter", "sort",
               "forEach", "push", "slice", "split", "replace", "trim", "test", "scrollTop", "scrollLeft", "remove",
               "getHours", "getMinutes", "getDate", "getFullYear", "getMonth", "getTime", "toFixed", "toLowerCase",
               "toUpperCase", "toString", "some", "every", "concat", "reduce", "keys", "hasOwnProperty", "match"}


def dashboard_contract(html, data):
    """Every data key the dashboard reads must be in status.json. Returns the problems, empty when they agree."""
    script = html[html.index("<script>"):]

    def block(start, end="\nfunction "):
        i = script.find(start)
        return script[i:script.find(end, i + 1) if script.find(end, i + 1) > 0 else len(script)] if i >= 0 else ""

    def found(pattern, text):
        return {m.group(1) for m in re.finditer(pattern, text)} - JS_BUILTINS
    read = {
        "top": found(r"\bd\.(\w+)", script),
        "card": found(r"\bc\.(\w+)", script) | found(r"\bc\[\"(\w+)\"\]", script) | found(r"\b[ab]\.(finished|status|outcome)\b", script)
        | found(r"d\.cards\[i\]\.(\w+)", script) | found(r"byId\[[^\]]+\]\.(\w+)", script),
        "wave": found(r"\bwv\.(\w+)", script),
        "checkpoint": found(r"\bd\.checkpoint\.(\w+)", script),
        "overview": found(r"\bo\.(\w+)", block("function renderOverview")),
        "goal": found(r"\bg\.(\w+)", block("function renderPlan")),
    }
    fy = re.search(r'function fyOf.*?\[((?:"\w+",?\s*)+)\]', script, re.S)
    emitted = {
        "top": set(data),
        "card": set().union(*(set(c) for c in data["cards"])) if data["cards"] else set(),
        "wave": set().union(*(set(w) for w in data["waves"])) if data["waves"] else set(),
        "checkpoint": {"id", "title"},  # null in a queue with no open summary
        "overview": set(data.get("overview") or {}),
        "goal": set().union(*(set(g) for g in data.get("goals", []))) if data.get("goals") else set(),
    }
    bad = []
    for kind, names in read.items():
        for name in sorted(names - emitted[kind]):
            bad.append("the dashboard reads %s key `%s`, which status.json does not have" % (kind, name))
    if fy:
        want = set(re.findall(r"\w+", fy.group(1)))
        have = set().union(*(set(c.get("for_you", {})) for c in data["cards"])) if data["cards"] else want
        if want - have:
            bad.append("the dashboard reads for_you keys %s, which status.json does not have" % sorted(want - have))
    else:
        bad.append("could not find the for_you key list (fyOf) in the dashboard")
    if not read["goal"] or not read["overview"] or not read["card"]:
        bad.append("contract check found no keys to compare (did the dashboard script change shape?)")
    return bad


def check_smoke():
    if not os.path.isfile(CARDS):
        return False, ["missing " + rel(CARDS) + " (v1 layout, SPEC 12)"]
    smoke = Smoke()
    root = tempfile.mkdtemp(prefix="cards-smoke-")
    try:
        for section in (smoke.lifecycle, smoke.checkin, smoke.settings, smoke.robustness, smoke.overview, smoke.overview_flags, smoke.for_you, smoke.fixes, smoke.wave_counts, smoke.examples):
            try:
                section(root)
            except Exception as err:  # a crash is a failure, and later sections still run
                smoke.ok(section.__name__ + " ran to the end", False, "%s: %s" % (type(err).__name__, err))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return not smoke.fails, ["%d steps" % smoke.steps] + smoke.fails


# ---------------------------------------------------------------- lints

def scan(text, patterns, flags=0):
    hits = []
    for p in patterns:
        if re.search(p, text, flags):
            hits.append(p)
    return hits


def generated(root_dir):
    """Run `init` and one `claim` in a temp project. Return (RULES.md, BRIEF.md, claim output) or None."""
    if not os.path.isfile(CARDS):
        return None
    cwd = tempfile.mkdtemp(prefix="cards-gen-")
    try:
        def run(*a):
            return subprocess.run([sys.executable, CARDS, *a], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60)
        if run("init").returncode != 0:
            return None
        run("new", "Sample", "--effort", "light", "--do", "Write a note.", "--done-when", "A note exists.", "--outputs", "note.md")
        claim = run("claim", "C001")
        rules = read(os.path.join(cwd, "cards", "RULES.md")) if os.path.isfile(os.path.join(cwd, "cards", "RULES.md")) else ""
        brief = read(os.path.join(cwd, "cards", "BRIEF.md")) if os.path.isfile(os.path.join(cwd, "cards", "BRIEF.md")) else ""
        status = run("status").stdout + run("check").stdout
        return rules, brief, claim.stdout, status
    finally:
        shutil.rmtree(cwd, ignore_errors=True)


def check_harness_lint(gen):
    if gen is None:
        return False, ["cannot run %s to get RULES.md" % rel(CARDS)]
    texts = [("RULES.md (generated)", gen[0]), ("claim output", gen[2])]
    if os.path.isfile(CARDS):
        texts.append((rel(CARDS), read(CARDS)))
    for s in SKILLS:
        texts.append((rel(s), strip_claude_section(read(s))))
    bad = []
    for name, text in texts:
        for w in HARNESS_WORDS:
            n = len(re.findall(r"\b%s\b" % re.escape(w), text, 0 if w == "Claude" or w.isupper() or w[0].isupper() else re.I))
            if n:
                bad.append("%s: %r x%d" % (name, w, n))
    return not bad, ["%d texts" % len(texts)] + bad


def check_claims_lint():
    bad = []
    desc_texts = []
    for s in SKILLS:
        d = frontmatter(read(s)).get("description", "")
        desc_texts.append((rel(s) + " description", d))
    claim_files = [p for p in shipped_files() if os.path.basename(p) in ("README.md", "plugin.json", "marketplace.json")]
    for p in claim_files:
        desc_texts.append((rel(p), read(p)))
    for name, text in desc_texts:
        for phrase in CLAIM_PHRASES:
            if re.search(r"\b%s\b" % re.escape(phrase), text, re.I):
                bad.append("%s: %r" % (name, phrase))
    gen_texts = []
    for p in shipped_files():
        gen_texts.append((rel(p), read(p)))
    for name, text in gen_texts:
        for flag in CUT_FLAGS:
            if re.search(flag, text):
                bad.append("%s: cut flag %s" % (name, flag.replace("(?m)(?:^|`)", "").replace("(?![\\w-])", "")))
    return not bad, ["%d texts" % (len(desc_texts) + len(gen_texts))] + bad


# ---------------------------------------------------------------- name and version

def check_name_version():
    bad = []
    pj = os.path.join(PLUGIN, ".claude-plugin", "plugin.json")
    root_pj = os.path.join(PLUGIN, "plugin.json")
    mj = os.path.join(PLUGIN, ".claude-plugin", "marketplace.json")
    try:
        manifest = json.loads(read(pj))
    except (OSError, ValueError) as err:
        return False, ["cannot read plugin.json: %s" % err]
    name, version = manifest.get("name"), manifest.get("version")
    code = re.search(r'(?m)^VERSION\s*=\s*["\']([^"\']+)["\']', read(CARDS)) if os.path.isfile(CARDS) else None
    if not code:
        bad.append("cards.py has no VERSION constant (or %s is missing)" % rel(CARDS))
    elif code.group(1) != version:
        bad.append("plugin.json version %s != cards.py VERSION %s" % (version, code.group(1)))
    if os.path.isfile(root_pj):  # Agent Plugins root manifest, read by Codex, Cursor and Copilot
        try:
            portable = json.loads(read(root_pj))
        except ValueError as err:
            bad.append("plugin.json (root): %s" % err)
        else:
            for key in ("name", "version"):
                if key not in portable:
                    bad.append("root plugin.json has no %s" % key)
                elif portable[key] != manifest.get(key):
                    bad.append("root manifest and Claude manifest disagree on %s: %s != %s"
                               % (key, portable[key], manifest.get(key)))
    note = os.path.join(PLUGIN, "skills", "run", "references", "harness.md")
    if not os.path.isfile(note):
        bad.append("missing %s (the run skill's on-another-harness note)" % rel(note))
    elif size(note) > HARNESS_NOTE_CAP:
        bad.append("%s is %d, cap %d" % (rel(note), size(note), HARNESS_NOTE_CAP))
    if os.path.isfile(mj):
        try:
            market = json.loads(read(mj))
            for entry in market.get("plugins", []):
                if "version" in entry and entry["version"] != version:
                    bad.append("marketplace.json version %s != plugin.json %s" % (entry["version"], version))
                if "name" in entry and entry["name"] != name:
                    bad.append("marketplace.json plugin name %s != plugin.json %s" % (entry["name"], name))
        except ValueError as err:
            bad.append("marketplace.json: %s" % err)
    refs = 0
    files = [p for p in shipped_files() if p.endswith(".md")]
    for p in files:
        for m in re.finditer(r"(?<![\w/.~-])/([a-z][a-z0-9-]*):[a-z][\w-]*", read(p)):
            refs += 1
            if m.group(1) != name:
                bad.append("%s: %s is not /%s:" % (rel(p), m.group(0), name))
    bad = list(dict.fromkeys(bad))
    head = "name %s, version %s, %d slash references" % (name, version, refs)
    if os.path.isfile(note):
        head += ", harness note %d B cap %d" % (size(note), HARNESS_NOTE_CAP)
    return not bad, [head] + bad


# ---------------------------------------------------------------- load budget

def check_budget(gen):
    rows, bad = [], []
    sizes = {}
    skills = {os.path.basename(os.path.dirname(s)): s for s in SKILLS}
    desc = 0
    for name, s in skills.items():
        desc += len(frontmatter(read(s)).get("description", "")) + len(name)
    sizes["3 skill names and descriptions"] = desc
    for key, skill in (("start skill body", "start"), ("run skill body", "run"), ("status skill body", "status")):
        if skill in skills:
            sizes[key] = size(skills[skill])
        else:
            bad.append("missing skill: " + skill)
    if len(skills) != 3:
        bad.append("expected 3 skills, found %d" % len(skills))
    if gen is None:
        bad.append("cannot generate RULES.md, BRIEF.md or claim output")
    else:
        rules, brief, claim, status = gen
        sizes["generated RULES.md"] = len(rules.encode())
        sizes["BRIEF template"] = len(brief.encode())
        sizes["status plus check output"] = len(status.encode())
        sizes["one-card claim output"] = len(claim.encode())
        sizes["worker prompt plus RULES"] = len(claim.encode()) + len(rules.encode())
    for label, cap in CAPS:
        v = sizes.get(label)
        if v is None:
            rows.append("%-34s %6s  cap %5d  MISSING" % (label, "-", cap))
            continue
        flag = "ok" if v <= cap else "OVER by %d" % (v - cap)
        if v > cap:
            bad.append("%s is %d, cap %d" % (label, v, cap))
        rows.append("%-34s %6d  cap %5d  %s" % (label, v, cap, flag))
    parts = ["3 skill names and descriptions", "start skill body", "run skill body", "generated RULES.md", "BRIEF template", "status plus check output"]
    if all(p in sizes for p in parts):
        total = sum(sizes[p] for p in parts)
        rows.append("%-34s %6d  cap %5d  %s" % ("heaviest session (start) total", total, HEAVIEST_CAP, "ok" if total < HEAVIEST_CAP else "OVER"))
        if total >= HEAVIEST_CAP:
            bad.append("heaviest session %d >= %d" % (total, HEAVIEST_CAP))
    return not bad, ["%d of %d items measured" % (len(sizes), len(CAPS))] + rows + bad


def check_debris():
    found = []
    root_git = os.path.join(PLUGIN, ".git")  # normal when the plugin is the repo root
    for dirpath, dirs, files in os.walk(PLUGIN):
        for d in dirs:
            path = os.path.join(dirpath, d)
            if d in ("__pycache__", ".omc") or (d == ".git" and path != root_git):
                found.append(rel(path))
    return not found, found


def check_validate():
    exe = shutil.which("claude")
    if not exe:
        return None, ["skipped (claude not on PATH)"]
    cfg = tempfile.mkdtemp(prefix="cards-validate-cfg-")  # isolated config, nothing under ~/.claude is touched
    try:
        p = subprocess.run([exe, "plugin", "validate", PLUGIN], capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, CLAUDE_CONFIG_DIR=cfg), cwd=cfg)
        lines = [ln for ln in (p.stdout + p.stderr).strip().split("\n") if ln.strip()]
        return p.returncode == 0, lines[:8] or ["exit %d" % p.returncode]
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, [str(err)]
    finally:
        shutil.rmtree(cfg, ignore_errors=True)


def main():
    gen = generated(PLUGIN)
    results = []
    for name, fn in (
        ("smoke", check_smoke),
        ("harness lint", lambda: check_harness_lint(gen)),
        ("claims lint", check_claims_lint),
        ("name and version", check_name_version),
        ("load budget", lambda: check_budget(gen)),
        ("no debris", check_debris),
        ("validate", check_validate),
    ):
        try:
            ok, lines = fn()
        except Exception as err:
            ok, lines = False, ["crashed: %s: %s" % (type(err).__name__, err)]
        word = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        head = lines[0] if lines else ""
        print("%s %s: %s" % (word, name, head))
        for ln in lines[1:]:
            print("     " + ln)
        results.append(ok)
    failed = sum(1 for r in results if r is False)
    print("%d failed of %d checks" % (failed, len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

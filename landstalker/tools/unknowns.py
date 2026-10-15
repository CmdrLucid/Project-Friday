#!/usr/bin/env python3
"""Registry of addresses we have SEEN but do not understand yet: docs/unknowns.json  (no ROM data, only addresses + where/when seen).

Why: patterns in WHEN/WHERE/FROM-WHOM an unknown address runs (room, action, caller, frequency) are what lets us name it later.
If nobody writes the sighting down, the pattern is never found. symbols.json = what we know; unknowns.json = what we have seen and still owe an answer.

commands (run in landstalker/):
  unknowns.py scan-docs                       register every bare address from docs/*.md that has no symbol (with doc locations)
  unknowns.py from-log FILE [--ctx "text"]    parse a console/interp log: 'interp: running $X', 'no function at $X', 'RTS to $X' lines;
                                              --ctx = what you did (room, action, build checksum), stored with the sighting, hits++
  unknowns.py add ADDR --where "..." [--ctx "..."] [--caller ADDR] [--note "pattern/hypothesis"]
  unknowns.py note ADDR "observation"         append a pattern note / hypothesis to an entry
  unknowns.py triage                          auto-class every entry: log-artifact (only seen in stale-stack/RTS-to/'expected' lines), ram, seed/table, other
  unknowns.py classify ADDR CLASS [text]      set class by hand, e.g. not-an-address (room number, size, abs.w offset), code, data, hardware
  unknowns.py sync                            drop entries whose address is now in symbols.json (resolved) -- run after adding symbols
  unknowns.py list [--min N] [--pattern]      open unknowns, most hits/mentions first (--pattern: only entries with notes or callers; --class C: only that class)
"""
import json, os, re, sys, datetime

here = os.path.dirname(os.path.abspath(__file__))
docs = os.path.join(here, "..", "docs")
UP = os.path.join(docs, "unknowns.json")
today = datetime.date.today().isoformat()

def load(p, default):
    try: return json.load(open(p))
    except Exception: return default

def symbols():
    d = load(os.path.join(docs, "symbols.json"), {"symbols": []})
    return {int(s["addr"], 16) for s in d["symbols"]}

def norm(h):
    v = int(h, 16)
    return v | 0xFF0000 if len(h) == 6 and v >= 0xFF0000 else v

def fmt(a): return f"0x{a:06X}"

U = load(UP, {"_readme": "Addresses seen but not understood. See tools/unknowns.py. Move to symbols.json when named; run 'unknowns.py sync'.", "unknowns": []})
by = {int(u["addr"], 16): u for u in U["unknowns"]}
S = symbols()

def entry(a):
    if a not in by:
        by[a] = {"addr": fmt(a), "first_seen": today, "hits": 0, "sightings": [], "callers": [], "notes": []}
    return by[a]

def sight(a, typ, where, ctx=None, hit=0):
    e = entry(a)
    e["hits"] += hit
    s = {"type": typ, "where": where, "date": today}
    if ctx: s["ctx"] = ctx
    if not any(x["type"] == typ and x["where"] == where and x.get("ctx") == ctx for x in e["sightings"]):
        e["sightings"].append(s)
        del e["sightings"][:-12]      # keep the 12 latest
    return e

def save():
    U["unknowns"] = [by[a] for a in sorted(by)]
    json.dump(U, open(UP, "w"), indent=1); open(UP, "a").write("\n")

args = sys.argv[1:]
if not args: print(__doc__); sys.exit(0)
cmd = args[0]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default

if cmd == "scan-docs":
    # rebuilds the doc sightings from scratch (line numbers go stale when docs change); log/manual sightings are kept
    pat = re.compile(r"\$([0-9A-Fa-f]{4,6})\b"); n = 0
    for e in by.values():
        e["sightings"] = [x for x in e["sightings"] if x["type"] != "doc"]; e["mentions"] = 0
    for fn in sorted(os.listdir(docs)):
        # DEBUGGING_INDEX.md = generated headings; ROOMS / ENTITIES / ITEMS / FLAGS = id tables from landstalker-lib (room numbers, entity types, item and flag ids, NOT addresses)
        if not fn.endswith(".md") or fn in ("DEBUGGING_INDEX.md", "ROOMS.md", "ENTITIES.md", "ITEMS.md", "FLAGS.md"): continue
        for ln, line in enumerate(open(os.path.join(docs, fn), encoding="utf-8"), 1):
            for m in pat.finditer(line):
                a = norm(m.group(1))
                if a in S or not (a < 0x200000 or a >= 0xFF0000): continue
                if a not in by: n += 1
                e = entry(a); e["mentions"] = e.get("mentions", 0) + 1
                if sum(1 for x in e["sightings"] if x["type"] == "doc") < 5:
                    e["sightings"].append({"type": "doc", "where": f"{fn}:{ln}", "date": today, "snippet": line.strip()[:140]})
    for a in [a for a, e in by.items() if e.get("mentions", 0) == 0 and not e["sightings"] and not e["notes"] and e["hits"] == 0]: del by[a]
    save(); print(f"scan-docs: {n} new, {len(by)} open unknowns total")
elif cmd == "from-log":
    ctx = opt("--ctx"); pats = [(r"interp: running \$([0-9A-Fa-f]{4,6})", "interp"), (r"no function at \$([0-9A-Fa-f]{4,6})", "nofunc"), (r"RTS to \$([0-9A-Fa-f]{4,6})", "rts")]
    seen, cnt = set(), 0
    for line in open(args[1], errors="replace"):
        for rx, typ in pats:
            for m in re.finditer(rx, line):
                a = norm(m.group(1))
                if a in S: continue
                cnt += 1; sight(a, typ, os.path.basename(args[1]), ctx, hit=1); seen.add(a)
    save(); print(f"from-log: {cnt} sightings, {len(seen)} distinct unknown addresses")
elif cmd == "add":
    a = norm(args[1].lstrip("$").replace("0x", "")); e = sight(a, "manual", opt("--where", "?"), opt("--ctx"), hit=1)
    if opt("--caller"):
        c = fmt(norm(opt("--caller").lstrip("$").replace("0x", "")))
        if c not in e["callers"]: e["callers"].append(c)
    if opt("--note"): e["notes"].append(f"{today}: {opt('--note')}")
    save(); print("ok", fmt(a))
elif cmd == "note":
    a = norm(args[1].lstrip("$").replace("0x", "")); entry(a)["notes"].append(f"{today}: {args[2]}"); save(); print("ok")
elif cmd == "triage":
    art = re.compile(r"RTS to|expected|garbage|stale|wild|bogus|leak|no function at|stack|return addr", re.I)
    n = 0
    for a, e in by.items():
        if e.get("class_by") == "hand": continue
        sn = [x.get("snippet", "") for x in e["sightings"] if x["type"] == "doc"]
        if a >= 0xFF0000: c = "ram"
        elif sn and all(art.search(x) for x in sn): c = "log-artifact"
        elif any(re.search(r"seed|table|fuzz|funcdiff|bra\.w", x, re.I) for x in sn): c = "seed/table"
        else: c = "other"
        e["class"] = c; n += 1
    save(); print(f"triage: {n} classified")
elif cmd == "classify":
    a = norm(args[1].lstrip("$").replace("0x", "")); e = entry(a); e["class"] = args[2]; e["class_by"] = "hand"
    if len(args) > 3: e["notes"].append(f"{today}: {args[3]}")
    save(); print("ok")
elif cmd == "sync":
    gone = [a for a in by if a in S]
    for a in gone: del by[a]
    save(); print(f"sync: {len(gone)} resolved and removed, {len(by)} open")
elif cmd == "list":
    mn = int(opt("--min", 0)); rows = []
    for a, e in by.items():
        score = e["hits"] * 10 + e.get("mentions", 0)
        if score < mn or ("--pattern" in args and not (e["notes"] or e["callers"])) or (opt("--class") and e.get("class") != opt("--class")): continue
        rows.append((score, a, e))
    for score, a, e in sorted(rows, reverse=True)[:60]:
        print(f"{fmt(a)} hits={e['hits']} mentions={e.get('mentions', 0)} first={e['first_seen']} class={e.get('class','?')} callers={e['callers']} notes={len(e['notes'])}  e.g. {e['sightings'][-1]['where']}")
    print(f"({len(rows)} shown/open, {len(by)} total)")
else:
    print(__doc__)

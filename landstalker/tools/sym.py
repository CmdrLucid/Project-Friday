#!/usr/bin/env python3
"""sym.py -- look up docs/symbols.json without reading the whole file (one line per hit).

  sym.py 0x4144            the entry at that address; if there is none: the nearest entry BELOW (the function / table it probably lies in) and the next one above
  sym.py 4144 --near 5     the entry plus 5 neighbours before and after
  sym.py Entity            all entries whose NAME or NOTE contains the text (case-insensitive), max 40 (more: --all)
  sym.py Entity --name     search only the names
  sym.py ... -v            full notes
Output: $ADDR Name [kind, confidence] note.  An argument that is hex digits only (optionally 0x / $) is taken as an address; use --text to force a text search."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symfile

args = [a for a in sys.argv[1:] if not a.startswith("--") and a != "-v"]
flags = set(a for a in sys.argv[1:] if a.startswith("--") or a == "-v")
if not args:
    print(__doc__); sys.exit(0)
syms = sorted(symfile.load()["symbols"], key=lambda s: int(s["addr"], 16))
addrs = [int(s["addr"], 16) for s in syms]
verbose = "-v" in flags


def line(s):
    note = s.get("note", "")
    if not verbose and len(note) > 110:
        note = note[:107] + "..."
    return "$%06X %s [%s, %s] %s" % (int(s["addr"], 16), s["name"], s.get("kind", "?"), s.get("confidence", "?"), note)


q = args[0]
m = re.fullmatch(r"(?:0x|\$)?([0-9A-Fa-f]{1,6})", q)
if m and "--text" not in flags:
    a = int(m.group(1), 16)
    import bisect
    i = bisect.bisect_right(addrs, a) - 1          # last entry <= a
    near = 3
    if "--near" in sys.argv:
        near = int(sys.argv[sys.argv.index("--near") + 1])
    if i >= 0 and addrs[i] == a:
        print(line(syms[i]))
        if "--near" in sys.argv:
            lo, hi = max(0, i - near), min(len(syms), i + near + 1)
            for k in range(lo, hi):
                if k != i: print("  " + line(syms[k]))
    else:
        print("no entry at $%06X." % a)
        if i >= 0: print("below : " + line(syms[i]) + "   (+$%X)" % (a - addrs[i]))
        if i + 1 < len(syms): print("above : " + line(syms[i + 1]))
        if "--near" in sys.argv:
            for k in range(max(0, i - near), min(len(syms), i + near + 2)):
                print("  " + line(syms[k]))
    sys.exit(0)

t = q.lower()
hits = [s for s in syms if t in s["name"].lower() or ("--name" not in flags and t in s.get("note", "").lower())]
limit = None if "--all" in flags else 40
for s in hits[:limit]:
    print(line(s))
print("-- %d hit(s)%s" % (len(hits), "" if limit is None or len(hits) <= limit else ", first %d shown (--all for all)" % limit))

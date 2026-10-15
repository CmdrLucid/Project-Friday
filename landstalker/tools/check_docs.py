#!/usr/bin/env python3
"""Doc/symbol consistency check (no ROM needed). Run before every commit on dev (a git hook and CI call it too).

ERRORS (exit 1):
  * docs/symbols.json is not valid, has a duplicate address, an entry without addr/name/kind/note/confidence,
    or an address/name pair that is malformed
  * a docs/*.md mentions a NAMED address ("RunTextCmd $0253F8" / "$0253F8 (RunTextCmd)") whose address is not in symbols.json
  * the same name is used in symbols.json for two different addresses
WARNINGS (only printed with -v or --all): bare addresses in the docs that have no symbol (very many are mid-function labels, so not an error).

Why: the Symbol rule (INDEX.md) says every learned address gets a human name in symbols.json in the same commit.
usage: python3 tools/check_docs.py [-v] [--all]
"""
import json, os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
docs = os.path.join(here, "..", "docs")
verbose = "-v" in sys.argv or "--all" in sys.argv
errors, warns = [], []

def norm(h):
    return int(h, 16) | (0xFF0000 if len(h) == 6 and int(h, 16) >= 0xFF0000 else 0)

try:
    data = json.load(open(os.path.join(docs, "symbols.json")))
except Exception as e:
    print("ERROR: docs/symbols.json is not valid JSON:", e); sys.exit(1)

# canonical format (sorted by address, one entry per line, tools/symfile.py): keeps grep / sym.py / git diffs usable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import symfile
    if open(os.path.join(docs, "symbols.json")).read() != symfile.dumps(data):
        errors.append("symbols.json is not in the canonical format (sorted by address, one entry per line) -> run: python3 tools/symfile.py")
except ImportError:
    pass

addr_of, names = {}, {}
for i, s in enumerate(data.get("symbols", [])):
    miss = [k for k in ("addr", "name", "kind", "note", "confidence") if not s.get(k)]
    if miss:
        errors.append(f"symbols.json entry {i} ({s.get('name') or s.get('addr')}): missing {miss}"); continue
    if not re.fullmatch(r"0x[0-9A-Fa-f]{6}", s["addr"]):
        errors.append(f"symbols.json {s['name']}: addr {s['addr']} is not 0xXXXXXX (6 hex digits)"); continue
    a = int(s["addr"], 16)
    if a in addr_of:
        errors.append(f"symbols.json: duplicate address {s['addr']} ({addr_of[a]} and {s['name']})")
    addr_of[a] = s["name"]
    names.setdefault(s["name"], []).append(s["addr"])
for n, l in names.items():
    if len(l) > 1:
        errors.append(f"symbols.json: name {n} used for several addresses {l}")

ident = r"[A-Za-z_][A-Za-z0-9_]{3,}"
p1 = re.compile(rf"\b({ident})\s*\(?\$([0-9A-Fa-f]{{4,6}})\b")
p2 = re.compile(rf"\$([0-9A-Fa-f]{{4,6}})\s*\(\s*({ident})\s*[:,)]")
bare = re.compile(r"\$([0-9A-Fa-f]{4,6})\b")

def looks_like_symbol(n):
    if n.startswith(("LANDSTALKER_", "sub_", "loc_", "lk_", "GENRECOMP_")) or n.isupper() or n.islower():
        return False
    return bool(re.search(r"[a-z]", n) and re.search(r"[A-Z]", n[1:]) or "_" in n and re.search(r"[A-Z]", n))

named_missing = {}
bare_missing = {}
for fn in sorted(os.listdir(docs)):
    if not fn.endswith(".md") or fn == "DEBUGGING_INDEX.md": continue
    for ln, line in enumerate(open(os.path.join(docs, fn), encoding="utf-8"), 1):
        for m in list(p1.finditer(line)):
            n, h = m.group(1), m.group(2)
            if looks_like_symbol(n) and norm(h) not in addr_of:
                named_missing.setdefault((norm(h), n), []).append(f"{fn}:{ln}")
        for m in p2.finditer(line):
            h, n = m.group(1), m.group(2)
            if looks_like_symbol(n) and norm(h) not in addr_of:
                named_missing.setdefault((norm(h), n), []).append(f"{fn}:{ln}")
        for m in bare.finditer(line):
            a = norm(m.group(1))
            if a not in addr_of and (a < 0x200000 or 0xFF0000 <= a):
                bare_missing.setdefault(a, []).append(f"{fn}:{ln}")

for (a, n), where in sorted(named_missing.items()):
    errors.append(f"docs name {n} at ${a:06X} is not in symbols.json (first seen {where[0]})")

if verbose:
    print(f"bare addresses in docs without a symbol: {len(bare_missing)} (informational)")
    if "--all" in sys.argv:
        for a in sorted(bare_missing): print(f"  ${a:06X}  {bare_missing[a][0]}")

up = os.path.join(docs, "unknowns.json")
if os.path.exists(up):
    unk = {int(u["addr"], 16) for u in json.load(open(up)).get("unknowns", [])}
    stale = sorted(a for a in unk if a in addr_of)
    print(f"unknowns.json: {len(unk)} open unknown addresses" + (f"; {len(stale)} are now named in symbols.json -> run: python3 tools/unknowns.py sync" if stale else ""))
print(f"symbols.json: {len(addr_of)} entries; named-but-missing: {len(named_missing)}; errors: {len(errors)}")
for e in errors: print("ERROR:", e)
if errors:
    print("-> add the entries to docs/symbols.json (INDEX.md 'Symbol rule'), then rerun.")
sys.exit(1 if errors else 0)

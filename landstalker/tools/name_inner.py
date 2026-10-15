#!/usr/bin/env python3
"""Names for the unnamed inner labels (loc_XXXX) of the lordmir disassembly: `<Parent>_loc` (dev tool, needs the disassembly checkout ~/landstalker_disasm).

Many of the "unnamed functions" of the generated C are not functions at all but jump targets INSIDE a named function (loop heads, error exits: the
recompiler registers every branch target it finds). The disassembly shows which: the label `loc_4AB4` stands after `DecompressLZ77Gfx:` in the source.
Rule: for every `loc_HEX` / `locret_HEX` label (IDA names carry the address) take the nearest PRECEDING code label in the same source file as parent, and require PROOF that
the label is inside it: its `CODE XREF` comment names the parent as `Parent+off` / `Parent:label` (a jump from inside the parent) or names another label already proven for that parent
(fixed point; without proof the label may be the start of a different function behind a stub, e.g. loc_433E after `j_DoDMACopy: jmp`); the
label is skipped when the parent is itself an unnamed address label (sub_XXXX / sub_...: then we do not know the real name) or data (dc.* follows), when the parent's
ROM address (from symbols.json) is missing, not below the label, or more than $2000 bytes away, or when the address already has a symbol.
New entries: name `<Parent>_loc<N>` (N counts the inner labels of that parent in source order; names must be unique), kind `label`, confidence `auto-parent` (the address is the one in the label name; the build only uses it for registered functions).
Idempotent. usage: name_inner.py [DISASM_DIR] [--dry]"""
import glob, json, os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
D = os.path.expanduser(args[0] if args else "~/landstalker_disasm")
dry = "--dry" in sys.argv
sp = os.path.join(here, "..", "docs", "symbols.json")
doc = json.load(open(sp))
syms = doc["symbols"]
byaddr = {int(s["addr"], 16) for s in syms}
byname = {}
for s in syms:
    byname.setdefault(s["name"], int(s["addr"], 16))

lab = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
addr_lab = re.compile(r"^(sub|loc|locret)_([0-9A-F]{3,6})$")
data_lab = re.compile(r"^(byte|word|off|unk|dword|stru|dat|asc)_")
new = []
counts = {}     # parent name -> number of inner labels so far (global: the same parent label can occur in several source files)
skipped = {"unnamed parent": 0, "no parent address": 0, "parent too far / above": 0, "address already named": 0, "no proof (XREF does not name the parent)": 0}
def xref_text(L, i):
    t = L[i]
    k = i + 1
    while k < len(L) and re.match(r"^\s+;", L[k]):
        t += " " + L[k]; k += 1
    return t


for f in sorted(glob.glob(os.path.join(D, "code", "**", "*.asm"), recursive=True)):
    L = open(f, errors="replace").read().split("\n")
    parent = None
    src = os.path.relpath(f, os.path.join(D, "code")).replace(".asm", "")
    cands = []      # (addr, label, parent, xref text)
    for i, l in enumerate(L):
        m = lab.match(l)
        if not m:
            continue
        n = m.group(1)
        rest = l[m.end():].strip()
        nxt = rest if rest and not rest.startswith(";") else next((x.strip() for x in L[i + 1:i + 4] if x.strip() and not x.strip().startswith(";")), "")
        isdata = nxt.startswith(("dc.", "dcb", "ds.", "incbin", "dc "))
        a = addr_lab.match(n)
        if a and a.group(1) in ("loc", "locret") and not isdata:
            addr = int(a.group(2), 16)
            if parent is None or addr_lab.match(parent):
                skipped["unnamed parent"] += 1
            elif parent not in byname:
                skipped["no parent address"] += 1
            elif not (0 <= addr - byname[parent] < 0x2000):
                skipped["parent too far / above"] += 1
            elif addr in byaddr:
                skipped["address already named"] += 1
            else:
                cands.append((addr, n, parent, xref_text(L, i)))
            continue
        if data_lab.match(n) or isdata:
            continue
        parent = n      # a human-named label OR an unnamed sub_XXXX (then the labels below it are skipped)
    proven = {}         # label -> parent
    changed = True
    while changed:
        changed = False
        for addr, n, par, x in cands:
            if n in proven:
                continue
            ok = re.search(r"\b%s[+:]" % re.escape(par), x) is not None
            if not ok:
                ok = any(proven.get(r) == par for r in re.findall(r"\b(?:loc|locret)_[0-9A-F]+\b", x))
            if ok:
                proven[n] = par; changed = True
    for addr, n, par, x in cands:
        if n not in proven:
            skipped["no proof (XREF does not name the parent)"] += 1
        elif addr in byaddr:
            skipped["address already named"] += 1
        else:
            counts[par] = counts.get(par, 0) + 1
            new.append({"addr": "0x%06X" % addr, "name": "%s_loc%d" % (par, counts[par]), "kind": "label",
                        "note": "inner label %s of %s (proven: its XREF comment names the parent; disassembly source %s); the address is the one in the disassembly label name" % (n, par, src),
                        "confidence": "auto-parent", "src": src})
            byaddr.add(addr)
print("name_inner: %d new inner-label names; skipped: %s" % (len(new), skipped))
if new and not dry:
    syms.extend(new)
    sys.path.insert(0, here); import symfile; symfile.save(doc, sp)      # canonical format: sorted, one entry per line
    print("name_inner: wrote %s" % sp)

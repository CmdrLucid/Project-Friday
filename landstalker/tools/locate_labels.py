#!/usr/bin/env python3
"""Give the disassembly's human-named labels ROM addresses WITHOUT an assembler (dev tool, needs the lordmir/landstalker_disasm checkout and YOUR ROM).

Method: walk landstalker_us.asm in assembly order (includes expanded, `if REGION=...` evaluated with the build options of the US ROM) and keep a
program counter. Sizes: dc.b/dc.w/dc.l/dcb/ds by counting items, incbin by file size, the Align/PadTo/ScriptID/ScriptJump macros by their rules,
instruction lines by decoding the ROM at the current counter with capstone (the ROM is the oracle for the instruction size).
Anchors: labels that carry their own address (sub_24A98, loc_16CA, byte_xxx, ...) must be hit EXACTLY; a mismatch (the name keeps another region's address) is counted, the counter is NOT changed and the labels around it are not reported.
A named label is reported only when the walk between its previous and next anchor is clean (no unknown size, no resync) -> confidence `auto-seq`.
Self-check: all names already in docs/symbols.json (hand verified) are compared with the result.

usage: locate_labels.py DISASM_DIR ROM [out.json] [--merge]   (default out: docs/symbols_seq.json, local, like symbols_auto.json)
  --merge: add / upgrade the entries in docs/symbols.json (new names tier `auto-seq`, same name + address as an auto-xref entry -> `auto-seq+xref`, other names at the same address -> note 'also named in the disassembly'; `src` = source file of the label in the disassembly, used by tools/make_code_map.py). Idempotent.
"""
import json, os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
disasm, romp = sys.argv[1], sys.argv[2]
args = [x for x in sys.argv[1:] if not x.startswith("--")]
out_path = args[2] if len(args) > 2 else os.path.join(here, "..", "docs", "symbols_seq.json")
rom = open(romp, "rb").read()
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)

DEF = {"REGION": 0, "NTSC": 1, "EXPANDED": 0, "REGION_CHECK": 1, "FIX_COLL_1": 1, "FIX_COLL_2": 1, "FIX_ARMLET_SKIP": 1, "FIX_WHISTLE_CHECK": 1,
       "FIX_SPRITE_HIDE": 1, "ENABLE_GOLD_COUNT": 1, "FIX_GOLA_BUG": 1, "FIX_GOLD_CAP": 1, "FIX_END_CREDS": 0, "REFRESH_GOLD_CTR": 1, "FIX_TS_GLITCH": 1,
       "US": 0, "JP": 1, "UK": 2, "FR": 3, "DE": 4, "US_BETA": 5, "False": 0, "True": 1}
ADDRNAME = re.compile(r"^(?:sub|loc|locret|byte|word|off|unk|dword|stru|dat|asc)_([0-9A-F]{3,6})$")

def cond(expr):
    e = expr.strip()
    e = re.sub(r"[A-Za-z_]\w*", lambda m: str(DEF.get(m.group(0), 0)), e)
    e = e.replace("<>", " != ").replace("=", " == ").replace("!", " or ").replace("&", " and ").replace("~", " not ")
    return bool(eval(e))

def split_items(s):
    items, cur, q = [], "", None
    for ch in s:
        if q:
            cur += ch
            if ch == q: q = None
        elif ch in "'\"": q = ch; cur += ch
        elif ch == ",": items.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip(): items.append(cur.strip())
    return items

def item_bytes(it):
    m = re.match(r"^(['\"])(.*)\1$", it)
    return len(m.group(2)) if m else 1

lines = []     # (kind, payload, src) in assembly order
def read(path, depth=0):
    full = os.path.join(disasm, path.replace("\\", "/"))
    stack = []   # conditional state: [active, taken]
    active = lambda: all(s[0] for s in stack)
    for n, raw in enumerate(open(full, errors="replace"), 1):
        l = raw.split(";")[0].rstrip("\r\n")
        if not l.strip(): continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):?(.*)$", l)
        label = None; rest = l
        if m and not l[0].isspace() and not re.match(r"^\s+(equ|macro)\b", m.group(2)):
            label, rest = m.group(1), m.group(2)
            if re.match(r"^\s+equ\b", rest) or re.match(r"^\s*=", rest): continue
        t = rest.strip()
        low = t.lower()
        mm = re.match(r"^(if|elseif)\b\s*(.*)$", t, re.I) or (None if not low.startswith("else") else None)
        if re.match(r"^if\b", low):
            v = cond(t[2:]); stack.append([v, v]); continue
        if re.match(r"^elseif\b", low):
            s = stack[-1]
            if s[1]: s[0] = False
            else: v = cond(t[6:]); s[0] = v; s[1] = v
            continue
        if low == "else":
            s = stack[-1]; s[0] = not s[1]; s[1] = True; continue
        if low == "endif": stack.pop(); continue
        if not active():
            continue
        if label: lines.append(("label", label, (path, n)))
        if not t: continue
        if re.match(r"^include\b", low):
            inc = re.search(r"\"([^\"]+)\"", t).group(1)
            if inc.endswith(".inc"): continue
            read(inc, depth + 1); continue
        lines.append(("op", t, (path, n)))
read("landstalker_us.asm")

pc = 0
labels = {}          # name -> (pc, clean)
unknown = 0
res = {}             # name -> addr  (for named labels), plus bookkeeping
events = []          # (name, pc, is_anchor, anchor_addr)
dirty_since = 0      # number of problems since the last anchor
problems = []
nanch = nmis = 0
cur_unclean = False
prev_clean = True; a_mis = False
seg = []             # labels since last anchor
accepted = {}; kinds = {}; pending = []; srcs = {}
for kind, pay, src in lines:
    if kind == "label":
        pending.append(pay); srcs[pay] = src[0].replace("\\", "/")[5:-4] if src[0].startswith("code") else src[0]
        mm = ADDRNAME.match(pay)
        if mm:
            a = int(mm.group(1), 16); nanch += 1
            a_mis = a != pc
            if a != pc:
                nmis += 1
                if len(problems) < 25: problems.append((pay, "pc %06X != %06X" % (pc, a), src))
                cur_unclean = True   # the anchor name carries another region's address: do NOT resync, keep counting, distrust the labels around it
                labels[pay] = pc; seg.append(pay); prev_clean = False
                continue
            for n in seg:
                if not cur_unclean and prev_clean: accepted[n] = labels[n]   # both neighbouring anchors hit exactly and nothing unknown in between
            seg = []; prev_clean = True; cur_unclean = False
            labels[pay] = pc
        else:
            labels[pay] = pc; seg.append(pay)
        continue
    t = pay; low = t.lower()
    isdata = bool(re.match(r"^(dc|dcb|ds)\.[bwl]\b|^incbin|^scriptid|^scriptjump|^rom_end", low))
    for n in pending: kinds[n] = "data" if isdata else "code"
    pending = []
    m = re.match(r"^(dc|dcb|ds)\.([bwl])\b\s*(.*)$", low)
    if m:
        w = {"b": 1, "w": 2, "l": 4}[m.group(2)]
        body = t[m.end(2) + 1:].strip()
        if m.group(1) == "dc":
            if w == 1: pc += sum(item_bytes(i) for i in split_items(body))
            else: pc += w * len(split_items(body))
        else:
            try: cnt = eval(re.sub(r"\$([0-9A-Fa-f]+)", r"0x\1", split_items(body)[0]))
            except Exception: cur_unclean = True; cnt = 0
            pc += w * cnt
        continue
    if low.startswith("incbin"):
        f = re.search(r"\"([^\"]+)\"", t).group(1).replace("\\", "/")
        try: pc += os.path.getsize(os.path.join(disasm, f))
        except OSError: cur_unclean = True
        continue
    if low.startswith(("scriptid", "scriptjump")): pc += 2; continue
    if low.startswith("align"):
        n = int(re.sub(r"\$", "0x", t.split()[1].strip()), 0); pc += (n - pc % n) % n if (pc % n) else 0; continue
    if low.startswith("padto"):
        v = int(t.split()[1].replace("$", "0x"), 0); pc = max(pc, v); continue
    if low.startswith("rom_end"): pc += 4; continue
    if low.startswith(("unlocksram", "locksram")): continue
    if low.startswith("expandbsr"): pc += 2; continue   # bsr.s (EXPANDED=0)
    if low.startswith(("module", "modend", "section", "opt ")): continue
    if low.startswith(("org", "even", "cnop", "inform", "mexit")):
        if low.startswith("even") and pc & 1: pc += 1
        continue
    # instruction: ask the ROM
    insn = next(md.disasm(rom[pc:pc + 10], pc, 1), None)
    if insn is None:
        cur_unclean = True; unknown += 1; pc += 2
    else:
        pc += insn.size
for n in seg:
    pass

import collections
cnt = collections.Counter(pay for k, pay, _ in lines if k == "label")
human = {}
for n, a in accepted.items():
    if not ADDRNAME.match(n) and cnt[n] == 1 and not n.startswith("_"): human[n] = a   # names that occur twice (module-local labels) are ambiguous: skipped
print("anchors %d, resyncs %d, unknown-size instructions %d, accepted named labels %d" % (nanch, nmis, unknown, len(human)))
for p in problems[:12]: print("  resync:", p)
json.dump({n: {"addr": "0x%06X" % a, "kind": kinds.get(n, "label"), "src": srcs.get(n, "")} for n, a in sorted(human.items(), key=lambda kv: kv[1])}, open(out_path, "w"), indent=0)
# self check against the curated names
sy = json.load(open(os.path.join(here, "..", "docs", "symbols.json")))["symbols"]
ok = bad = 0; badl = []
for e in sy:
    if e["name"] in human:
        if int(e["addr"], 16) == human[e["name"]]: ok += 1
        else: bad += 1; badl.append((e["name"], e["addr"], "0x%06X" % human[e["name"]]))
print("self-check vs symbols.json: %d agree, %d differ" % (ok, bad)); print(badl[:10])

if "--merge" in sys.argv:
    p = os.path.join(here, "..", "docs", "symbols.json"); d = json.load(open(p)); sy = d["symbols"]
    byaddr = {int(e["addr"], 16): e for e in sy}; names = {e["name"] for e in sy}
    NOTE = "address by sequential layout of the lordmir disassembly (tools/locate_labels.py): the ROM walk hit the anchors on both sides exactly"
    up = new = al = srcn = 0
    for n, a in sorted(human.items(), key=lambda kv: kv[1]):
        e = byaddr.get(a); k = kinds.get(n, "label")
        if e is None:
            if n in names: continue
            e = {"addr": "0x%06X" % a, "name": n, "kind": k, "note": NOTE + "; first line after the label is " + ("an instruction" if k == "code" else "data (dc/incbin)"), "confidence": "auto-seq"}
            sy.append(e); byaddr[a] = e; names.add(n); new += 1
        elif e["name"] == n:
            if e["confidence"] == "auto-xref":
                e["confidence"] = "auto-seq+xref"; e["kind"] = k; e["note"] = NOTE + "; the cross-reference decoding (tools/symbolize.py) gives the same address"; up += 1
        else:
            if "also named in the disassembly" not in e["note"]: e["note"] += " [also named in the disassembly at this address: %s]" % n; al += 1
            elif n not in e["note"]: e["note"] = e["note"].replace("]", ", %s]" % n, 1) if e["note"].endswith("]") else e["note"]
            continue
        if srcs.get(n) and e.get("src") != srcs[n]: e["src"] = srcs[n]; srcn += 1
    sys.path.insert(0, here); import symfile; symfile.save(d, p)      # canonical format: sorted, one entry per line
    print("merge: %d new, %d upgraded to auto-seq+xref, %d alias notes, %d src fields" % (new, up, al, srcn))

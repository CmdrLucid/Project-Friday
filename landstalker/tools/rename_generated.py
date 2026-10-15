#!/usr/bin/env python3
"""Readable names in the GENERATED C code. For every function whose address has a name in docs/symbols.json (kind code / label / data+code; the name is cut at
the first non-identifier character) the build gets
    enum { GetItemName_00D09C = 0x00D09C, ... };            (recomp_funcs.h: the ADDRESS with its name)
    void fn_GetItemName_00D09C(void) { ... }                (the function = the code; old name sub_00D09C / jt_.. / loc_.. / seed name)
    func_table_register(GetItemName_00D09C, fn_GetItemName_00D09C);
    func_table_jsr(GetItemName_00D09C, 0x002CCE);           (calls / tail calls: name + address in one token; the old `/* sub_00D09C */` comment is dropped)
The compiler turns the constants back into the same numbers, so behaviour and machine code are the same (A/B check: RAM dumps identical with LANDSTALKER_NONAMES_C=1).
Calls to addresses without a name keep `0x..`; `loc_XXXXXX` goto labels are never touched. Tools that grep the generated C for `0xADDR` (who_calls, check_splits) expand the
constants again with tools/genc.py.
MUST run AFTER patch_sprcull.py (it looks for `void sub_004144(void) {`) and before the compile step. Idempotent. Off switch: LANDSTALKER_NONAMES_C=1 in the environment of build.sh.
usage: rename_generated.py src/recomp [docs/symbols.json]"""
import glob, json, os, re, sys

if os.environ.get("LANDSTALKER_NONAMES_C") == "1":
    print("rename_generated: skipped (LANDSTALKER_NONAMES_C=1)"); sys.exit(0)

d = sys.argv[1]
symf = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "symbols.json")

names = {}
for s in json.load(open(symf))["symbols"]:
    if s.get("kind") not in ("code", "label", "data+code"):
        continue
    m = re.match(r"[A-Za-z_]\w*", s["name"])
    if m:
        names.setdefault(int(s["addr"], 16), m.group(0))     # first entry for an address wins

hp = os.path.join(d, "recomp_funcs.h")
h = open(hp).read()
reg = re.findall(r"func_table_register\(0x([0-9A-Fa-f]+), (\w+)\);", h)
if not reg:
    print("rename_generated: nothing to do (already renamed?)"); sys.exit(0)
const = {}     # address -> constant name
fnname = {}    # old function identifier -> new
for a, ident in reg:
    a = int(a, 16)
    if a in names:
        c = "%s_%06X" % (names[a], a)
        const[a] = c
        fnname[ident] = "fn_" + c

call = re.compile(r"func_table_(jsr|call|tail)\(0x([0-9A-Fa-f]+)\b([^;\n]*;)(?:[ \t]*/\*[^*\n]*\*/)?")


def call_repl(m):
    c = const.get(int(m.group(2), 16))
    return m.group(0) if c is None else "func_table_%s(%s%s" % (m.group(1), c, m.group(3))


defn = re.compile(r"^void (\w+)\(void\)", re.M)


def defn_repl(m):
    return "void %s(void)" % fnname.get(m.group(1), m.group(1))


reg_re = re.compile(r"func_table_register\(0x([0-9A-Fa-f]+), (\w+)\);")


def reg_repl(m):
    c = const.get(int(m.group(1), 16))
    return m.group(0) if c is None else "func_table_register(%s, %s);" % (c, fnname[m.group(2)])


n_files = 0
for p in sorted(glob.glob(os.path.join(d, "recomp_*.c"))):
    s = open(p).read()
    t = defn.sub(defn_repl, call.sub(call_repl, s))
    if t != s:
        open(p, "w").write(t); n_files += 1

h = defn.sub(defn_repl, h)
h = reg_re.sub(reg_repl, h)
enum = "/* function addresses with their names (tools/rename_generated.py) */\nenum {\n%s};\n\n" % "".join("    %s = 0x%06X,\n" % (c, a) for a, c in sorted(const.items()))
k = re.search(r"^void ", h, re.M).start()
h = h[:k] + enum + h[k:]
open(hp, "w").write(h)
print("rename_generated: %d functions named (%d call files, %d names in symbols.json)" % (len(const), n_files, len(names)))

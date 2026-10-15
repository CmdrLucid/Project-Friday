#!/usr/bin/env python3
"""Dev tool (needs the lordmir/landstalker_disasm checkout, NOT the ROM): collect, for every named label in the disassembly, the
IDA cross-reference comments that give the ROM address of an instruction referencing it (`CODE XREF: sub_24A98+2Ep`,
`ROM:000253A0p`). Result: tools/xrefs.json  {label: [[instr_addr, kind], ...]}  -- only addresses and names, no ROM data.
tools/symbolize.py later reads the ROM at those instruction addresses to turn names into addresses.

usage: extract_xrefs.py path/to/landstalker_disasm   (rewrites tools/xrefs.json)
"""
import json, os, re, sys

root = os.path.join(sys.argv[1], "code")
TOK = re.compile(r"(?:ROM:([0-9A-F]{8})|(?:sub|loc|byte|word|off|unk|dword)_([0-9A-F]+)(?:\+([0-9A-F]+))?)[\x18\x19]?([pjrtw])")
ADDRNAME = re.compile(r"^(?:sub|loc|byte|word|off|unk|dword|stru|locret|dat|asc|j_[A-Za-z0-9_]*?)_?[0-9A-F]{3,6}$")
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
out = {}
for dp, _, fs in os.walk(root):
    if {"de", "fr", "jp"} & set(dp.split(os.sep)):
        continue                                   # one language tree is enough (US = en)
    for f in fs:
        if not f.endswith(".asm"):
            continue
        lines = open(os.path.join(dp, f), errors="replace").read().split("\n")
        for i, ln in enumerate(lines):
            m = LABEL.match(ln)
            if not m:
                continue
            name = m.group(1)
            text = ln
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith(';') :
                text += ' ' + lines[j]
                j += 1
            xr = []
            for t in TOK.finditer(text):
                if t.group(1):
                    a = int(t.group(1), 16)
                else:
                    a = int(t.group(2), 16) + (int(t.group(3), 16) if t.group(3) else 0)
                xr.append([a, t.group(4)])
            if xr:
                out.setdefault(name, []).extend(x for x in xr if x not in out.get(name, []))
named = {k: v for k, v in out.items() if not ADDRNAME.match(k)}
calib = {k: v for k, v in list(out.items()) if ADDRNAME.match(k)}
calib = dict(list(calib.items())[:400])
json.dump({"named": named, "calibration": calib}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "xrefs.json"), "w"))
print(f"{len(named)} named labels with xrefs, {len(calib)} address-named labels kept for calibration")

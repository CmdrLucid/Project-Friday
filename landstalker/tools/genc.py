"""Helper for tools that read the generated C (src/recomp): since tools/rename_generated.py, calls look like `func_table_jsr(GetItemName_00D09C, 0x002CCE)`
instead of `func_table_jsr(0x00D09C, 0x002CCE)`. expand(d) returns a function that turns such constants back into 0x%06X, so the old regexes keep working."""
import os, re


def expand(d):
    consts = {}
    try:
        h = open(os.path.join(d, "recomp_funcs.h"), errors="replace").read()
        consts = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^\s+(\w+) = 0x([0-9A-Fa-f]+),$", h, re.M)}
    except OSError:
        pass
    if not consts:
        return lambda line: line
    pat = re.compile(r"(func_table_\w+\()(\w+)\b")

    def sub(m):
        a = consts.get(m.group(2))
        return m.group(0) if a is None else "%s0x%06X" % (m.group(1), a)
    return lambda line: pat.sub(sub, line)

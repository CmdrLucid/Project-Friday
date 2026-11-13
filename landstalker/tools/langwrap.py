#!/usr/bin/env python3
"""langwrap.py: line breaking for translations (docs/TRANSLATION.md section 4).  Library + tool:
   langwrap.py ROM lang/xx.json src.json   -- src.json = {"XXXX": "text", ...} written WITHOUT {SoftNewLine} ('|' = a forced line break);
                                             every entry is wrapped with the real text font widths of the ROM and stored in lang/xx.json
                                             with the hash of the English source (h).  Prints a warning for lines that do not fit.
The font widths come from the player's ROM (tools/romtext.py rule: advance = rightmost pixel column + 3, space 8); nothing of the ROM is written.
Limits: a line ends before x > $114 (PrintString_CheckLineWidth $022F66); we keep 250 px for normal lines and 160 px for the first line after a
{Speaker} name ('Name: ' is printed first).  After a {ContinuePrompt} inside a string the text goes on in a new line (as the English strings do)."""
import hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langbuild as lb, stringdump as sd

LIMIT, FIRST = 236, 150   # 2026-11-13: 250 ran past the 288 px line buffer after the indent (letters wrapped to the line start); the runtime check LK_LGWRAP v1 catches the rest
BREAK_AFTER = ("ContinuePrompt",)


def widths(rom):
    def w(code):
        if code == 0: return 8
        last = -1
        for r in lb.glyph_rows(rom, code):
            for k in range(12):
                if r & (0x8000 >> k): last = max(last, k)
        return last + 3
    W = {ch: w(i) for i, ch in enumerate(sd.MAIN)}
    for ch, base in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("Ä", "A"), ("Ö", "O"), ("Ü", "U")): W[ch] = W[base]
    W["ß"] = 9
    return W


def text_width(W, s):
    s = re.sub(r"\{=[a-z0-9_:]+\}", "Xxxxxx", s)   # a name placeholder: about six letters
    return sum(W.get(c, 9) for c in re.sub(r"\{[^}]*\}", "", s))


def wrap(W, text):
    """text without {SoftNewLine} ('|' forces a break) -> text with {SoftNewLine}s; returns (text, list of too long lines)"""
    out, bad = [], []
    parts = re.split(r"(\{[A-Za-z]+\}|\|)", text)
    line, first, started = "", text.startswith("{Speaker}"), False
    def flush(force_nl):
        nonlocal line, first
        if line.strip():
            if text_width(W, line.strip()) > (FIRST if first else LIMIT): bad.append(line.strip())
            out.append(line.strip()); first = False
        line = ""
        if force_nl: out.append("{SoftNewLine}")
    for p in parts:
        if not p: continue
        if p == "|": flush(True); continue
        if re.fullmatch(r"\{[A-Za-z]+\}", p):
            name = p[1:-1]
            if name in ("Item", "Number"): line += p; continue
            flush(False); out.append(p)
            if name in BREAK_AFTER: out.append("\0")   # a line break follows if more text comes
            continue
        for word in re.split(r"(\s+)", p):
            if not word or word.isspace():
                if line: line += " "
                continue
            cand = (line + word) if line else word
            if line and text_width(W, cand.strip()) > (FIRST if first else LIMIT): flush(True); cand = word
            line = cand
    flush(False)
    s = "".join(out)
    s = re.sub(r"(\{SoftNewLine\})+(?=\{(?:WaitInput|ContinuePrompt|NewLinePrompt)\}|$)", "", s)
    s = re.sub(r"\0(?=[^{\0]|\{=)", "{SoftNewLine}", s).replace("\0", "")
    s = re.sub(r"\{SoftNewLine\}\{SoftNewLine\}", "{SoftNewLine}", s)
    return s, bad


def main():
    rom = open(sys.argv[1], "rb").read(); W = widths(rom)
    en = sd.decode_all(rom); lang = json.load(open(sys.argv[2], encoding="utf-8")); src = json.load(open(sys.argv[3], encoding="utf-8"))
    n = 0
    for k, t in src.items():
        if k.startswith("_"): continue
        if k not in en: print("no such string", k); continue
        s, bad = wrap(W, t)
        for b in bad: print("%s: line too long (%d px): %s" % (k, text_width(W, b), b))
        if lb.ctl_names(en[k]) != [c for c in lb.ctl_names(s) if not c.startswith("=")]: print("%s: control codes differ: %s vs %s" % (k, lb.ctl_names(en[k]), lb.ctl_names(s)))
        lang.setdefault("strings", {})[k] = {"h": hashlib.sha1(en[k].encode("utf-8")).hexdigest()[:8], "t": s}; n += 1
    lang["strings"] = dict(sorted(lang["strings"].items()))
    open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(lang, ensure_ascii=False, indent=1) + "\n")
    print("langwrap: %d entries wrapped into %s" % (n, sys.argv[2]))


if __name__ == "__main__":
    main()

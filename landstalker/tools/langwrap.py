#!/usr/bin/env python3
"""langwrap.py: line breaking for translations (docs/TRANSLATION.md section 4).  Library + tool:
   langwrap.py ROM lang/xx.json src.json [--items-jp]   -- (--items-jp: into the block 'items_jp', used while Options > Items = Japanese)  src.json = {"XXXX": "text", ...} written WITHOUT {SoftNewLine} ('|' = a forced line break);
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
    for ch, (base, mk) in lb.FR_SET.items(): W[ch] = W[base]   # LK_LGFR v1: French accents keep the width of their letter (the cedilla / marks stay inside it)
    return W


GLUE = {"{Item}": ("\x01", 108), "{Number}": ("\x02", 27), "{Pause1s}": ("\x03", 0), "{Pause1sOrInput}": ("\x04", 0), "{Pause1_5sOrInput}": ("\x05", 0), "{Pause2sOrInput}": ("\x06", 0)}
NAMEW = 54   # a {=name} placeholder: about six letters


def text_width(W, s):
    w = 0
    for tok in re.findall(r"\{=[a-z0-9_:]+\}|\{[A-Za-z0-9_]+\}|.", s, re.S):
        if tok.startswith("{="): w += NAMEW
        elif tok in GLUE: w += GLUE[tok][1]
        elif tok.startswith("{") and len(tok) > 1: pass
        else:
            g = [v for v in GLUE.values() if v[0] == tok]
            w += g[0][1] if g else W[" "] if tok == "\x07" else W.get(tok, 9)
    return w


def wrap(W, text):
    """text without {SoftNewLine} ('|' forces a break) -> text with {SoftNewLine}s; returns (text, list of too long lines).
    {Item}, {Number}, pauses and {=name} placeholders are parts of the word they touch (an item name and the full stop after it stay together).
    '~' = a fixed space: never collapsed, never a break point (spaced-out letters 'F A S S~~N I C H T S' keep their word gaps)."""
    names = []
    def keep(m): names.append(m.group(0)); return "\x10" + chr(0x41 + len(names) - 1)
    text = re.sub(r"\{=[a-z0-9_:]+\}", keep, text)
    for code, (ch, _) in GLUE.items(): text = text.replace(code, ch)
    text = text.replace("~", "\x07")
    def width(t):
        t = re.sub("\x10.", "{=n}", t)
        return text_width(W, t)
    out, bad = [], []
    parts = re.split(r"(\{[A-Za-z]+\}|\|)", text)
    line, first = "", text.startswith("{Speaker}")
    def flush(force_nl):
        nonlocal line, first
        if line.strip():
            if width(line.strip()) > (FIRST if first else LIMIT): bad.append(line.strip())
            out.append(line.strip()); first = False
        line = ""
        if force_nl: out.append("{SoftNewLine}")
    for p in parts:
        if not p: continue
        if p == "|": flush(True); continue
        if re.fullmatch(r"\{[A-Za-z]+\}", p):
            name = p[1:-1]
            flush(False); out.append(p)
            if name in BREAK_AFTER: out.append("\0")   # a line break follows if more text comes
            continue
        for word in re.split(r"(\s+)", p):
            if not word or word.isspace():
                if line: line += " "
                continue
            cand = (line + word) if line else word
            if line and width(cand.strip()) > (FIRST if first else LIMIT): flush(True); cand = word
            line = cand
    flush(False)
    s = "".join(out)
    s = re.sub(r"(\{SoftNewLine\})+(?=\{(?:WaitInput|ContinuePrompt|NewLinePrompt)\}|$)", "", s)
    s = re.sub(r"\0(?=[^{\0]|\x10)", "{SoftNewLine}", s).replace("\0", "")
    s = re.sub(r"\{SoftNewLine\}\{SoftNewLine\}", "{SoftNewLine}", s)
    s = re.sub(r"  +", " ", s).replace("\x07", " ")
    for code, (ch, _) in GLUE.items(): s = s.replace(ch, code)
    s = re.sub("\x10(.)", lambda m: names[ord(m.group(1)) - 0x41], s)
    bad = [re.sub("\x10(.)", lambda m: names[ord(m.group(1)) - 0x41], b) for b in bad]
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
        tgt = lang.setdefault("items_jp", {}) if "--items-jp" in sys.argv else lang   # --items-jp: block 'items_jp' (lines for Options > Items = Japanese, LK_JPITEMS v1)
        tgt.setdefault("strings", {})[k] = {"h": hashlib.sha1(en[k].encode("utf-8")).hexdigest()[:8], "t": s}; n += 1
    for tgt in (lang, lang.get("items_jp", {})):
        if "strings" in tgt: tgt["strings"] = dict(sorted(tgt["strings"].items()))
    open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(lang, ensure_ascii=False, indent=1) + "\n")
    print("langwrap: %d entries wrapped into %s" % (n, sys.argv[2]))


if __name__ == "__main__":
    main()

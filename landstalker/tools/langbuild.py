#!/usr/bin/env python3
"""langbuild.py ROM lang/xx.json out.bin [--preview font.png]: builds the runtime language file from a translation (docs/TEXT_LAYER.md).
 * decodes the ROM's English strings (stringdump.py) and keeps only translations whose 'h' (first 8 hex digits of sha1 of the English source text) matches
 * checks the control codes ({Speaker}, {Item}, {Number} ...) of a translation against the English source (layout codes NewLine / SoftNewLine / pauses may differ)
 * converts text to the game's WORD STREAM (glyph code = word, control character = ~handler word, $FFFF end) and name tables to byte entries
 * adds the extended font glyphs (ä ö ü ß Ä Ö Ü = codes $6C..$72, 30 bytes each, derived from the ROM's own font) and the 'ui' layout values
The output is derived from the ROM (font): local only, never commit it.
Binary format (all numbers big endian):  'LKLG' u16 version(1) u16 n_str u16 n_name u16 n_ui u16 n_glyph
  n_str  x { u16 id, u32 blob offset, u16 word count (without the $FFFF) }       n_name x { u8 table, u8 index, u32 blob offset, u8 byte count }
  n_ui   x { u16 key, u16 value }                                                  n_glyph x { u8 code, 30 bytes }        then the blob (strings as u16 words incl. $FFFF, names as bytes)"""
import hashlib, json, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stringdump as sd

HANDLER = [0x15, 0xE, 0x01, 0xB, 0xC, 0x05, 0x07, 0x06, 0x04, 0x03, 0x02, 0x18, 0x0F, 0x0D, 0x08, 0x09, 0x0A, 0x17, 0x19]   # ControlChars table: code $56 + k -> handler index
CTL = {v: k for k, v in sd.CONTROL.items()}
NAMECTL = {v.strip("{}"): k for k, v in sd.NAME_CODES.items()}
EXTRA = {"ä": 0x6C, "ö": 0x6D, "ü": 0x6E, "ß": 0x6F, "Ä": 0x70, "Ö": 0x71, "Ü": 0x72}
LAYOUT = {"NewLine", "SoftNewLine", "Pause1s", "Pause1sOrInput", "Pause1_5sOrInput", "Pause2sOrInput", "BreakSpace", "BreakPoint", "Hyphen"}
TABLES = {name: i for i, (name, _, _) in enumerate(sd.NAME_TABLES)}
UI_KEYS = {"yesno_no_x": 1, "yesno_cursor_yes_x": 2, "yesno_cursor_no_x": 3}
FONT, GLYPH = 0x2A884, 30


def tokens(text):
    """text -> list of ('g', code) / ('c', k) / ('n', code) (name-only special code)"""
    out, i = [], 0
    while i < len(text):
        if text[i] == "{":
            j = text.index("}", i)
            nm = text[i + 1:j]
            if nm in CTL: out.append(("c", CTL[nm]))
            elif nm in NAMECTL: out.append(("n", NAMECTL[nm]))
            else: raise ValueError("unknown code {%s}" % nm)
            i = j + 1
        else:
            ch = text[i]
            if ch in EXTRA: out.append(("g", EXTRA[ch]))
            elif ch in sd.MAIN: out.append(("g", sd.MAIN.index(ch)))
            else: raise ValueError("character %r has no glyph" % ch)
            i += 1
    return out


def ctl_names(text):
    import re
    return sorted(m for m in re.findall(r"\{([^}]*)\}", text) if m not in LAYOUT)


def glyph_rows(rom, code):
    b = rom[FONT + GLYPH * code:FONT + GLYPH * code + GLYPH]
    return [b[2 * i] << 8 | b[2 * i + 1] for i in range(15)]


def pack(rows): return b"".join(struct.pack(">H", r) for r in rows)


def make_glyphs(rom):
    """derived glyphs: small letters get the diaeresis in the free rows above; capitals lose one middle row to make room for it in row 0; a drawn sharp s"""
    dots = 0x4800                                   # columns 1 and 4
    g = {}
    for ch, base in (("ä", "a"), ("ö", "o"), ("ü", "u")):
        r = glyph_rows(rom, sd.MAIN.index(base)); r[2] |= dots; g[EXTRA[ch]] = pack(r)
    for ch, base in (("Ä", "A"), ("Ö", "O"), ("Ü", "U")):
        r = glyph_rows(rom, sd.MAIN.index(base)); body = r[:5] + r[6:11]      # 11 rows -> 10 rows (a middle row is dropped)
        g[EXTRA[ch]] = pack([dots] + body + [0] * 4)
    ss = [0x7000, 0x8800, 0x8800, 0x9000, 0xB000, 0x8800, 0x8400, 0x8400, 0x8400, 0xBC00, 0xB800, 0, 0, 0, 0]
    g[EXTRA["ß"]] = pack(ss)
    return g


def preview(rom, glyphs, path, text):
    """tiny PNG of a sample line in the ROM font + new glyphs (3x)"""
    import zlib
    def png(p, w, h, px):
        raw = b"".join(b"\x00" + bytes(px[y * w:(y + 1) * w]) for y in range(h))
        def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        open(p, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))
    S, adv_pad = 3, 1
    cols = []
    for t, c in tokens(text):
        if t != "g": continue
        rows = glyph_rows(rom, c) if c not in glyphs else [struct.unpack(">H", glyphs[c][2 * i:2 * i + 2])[0] for i in range(15)]
        wid = 0 if c == 0 else max(max(6, 12 - (r & -r).bit_length() + 1) if False else 0 for r in rows)
        cols.append((c, rows))
    adv = 8
    W, H = (len(cols) * adv + 4) * S, 20 * S
    px = [0] * (W * H)
    for n, (c, rows) in enumerate(cols):
        for y, r in enumerate(rows):
            for x in range(12):
                if (r >> (15 - x)) & 1:
                    for dy in range(S):
                        for dx in range(S):
                            px[((2 + y) * S + dy) * W + (2 + n * adv + x) * S + dx] = 255
    png(path, W, H, px)


def main():
    rom = open(sys.argv[1], "rb").read()
    lang = json.load(open(sys.argv[2]))
    en = sd.decode_all(rom)
    strs, names, blob, dropped = [], [], bytearray(), []
    def check(key, ent):
        src = en.get(key)
        if src is None: return "no such entry in the ROM"
        if hashlib.sha1(src.encode("utf-8")).hexdigest()[:8] != ent["h"]: return "English source differs from the one translated"
        if ctl_names(src) != ctl_names(ent["t"]): return "control codes differ: %s vs %s" % (ctl_names(src), ctl_names(ent["t"]))
        return None
    for key, ent in lang.get("strings", {}).items():
        why = check(key, ent)
        if why: dropped.append((key, why)); continue
        words = []
        try: toks = tokens(ent["t"])
        except ValueError as e: dropped.append((key, str(e))); continue
        for t, v in toks:
            if t == "g": words.append(v)
            elif t == "c": words.append(~HANDLER[v] & 0xFFFF)
            else: dropped.append((key, "name-only code in a string")); break
        else:
            strs.append((int(key, 16), len(blob), len(words))); blob += b"".join(struct.pack(">H", w) for w in words) + b"\xff\xff"
    for key, ent in lang.get("names", {}).items():
        why = check(key, ent)
        if why: dropped.append((key, why)); continue
        tab, idx = key.split(":")
        try: data = bytes(v for t, v in tokens(ent["t"]))
        except ValueError as e: dropped.append((key, str(e))); continue
        names.append((TABLES[tab], int(idx), len(blob), len(data))); blob += data
    ui = [(UI_KEYS[k], v) for k, v in lang.get("ui", {}).items()]
    glyphs = make_glyphs(rom)
    out = b"LKLG" + struct.pack(">HHHHH", 1, len(strs), len(names), len(ui), len(glyphs))
    out += b"".join(struct.pack(">HIH", *e) for e in strs) + b"".join(struct.pack(">BBIB", *e) for e in names)
    out += b"".join(struct.pack(">HH", *e) for e in ui) + b"".join(bytes([c]) + d for c, d in sorted(glyphs.items())) + bytes(blob)
    open(sys.argv[3], "wb").write(out)
    print("langbuild: %d strings, %d names, %d ui values, %d glyphs -> %s (%d bytes); dropped %d" % (len(strs), len(names), len(ui), len(glyphs), sys.argv[3], len(out), len(dropped)))
    for k, w in dropped: print("  dropped", k, "-", w)
    if "--preview" in sys.argv:
        preview(rom, glyphs, sys.argv[sys.argv.index("--preview") + 1], "Größe über Äpfel, Öl, Übung: Fuß schön Mädchen")


if __name__ == "__main__":
    main()

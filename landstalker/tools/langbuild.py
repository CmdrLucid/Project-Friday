#!/usr/bin/env python3
"""langbuild.py ROM lang/xx.json out.bin [--preview font.png]   or   langbuild.py ROM lang/ outdir/ (every *.json -> outdir/<code>.bin + outdir/index.txt): builds the runtime language files from translations (docs/TEXT_LAYER.md).
 * decodes the ROM's English strings (stringdump.py) and keeps only translations whose 'h' (first 8 hex digits of sha1 of the English source text) matches
 * checks the control codes ({Speaker}, {Item}, {Number} ...) of a translation against the English source (layout codes NewLine / SoftNewLine / pauses may differ)
 * converts text to the game's WORD STREAM (glyph code = word, control character = ~handler word, $FFFF end) and name tables to byte entries
 * adds the extended font glyphs (ä ö ü ß Ä Ö Ü = codes $6C..$72, 30 bytes each, derived from the ROM's own font) and the 'ui' layout values
The output is derived from the ROM (font): local only, never commit it.
Binary format (all numbers big endian):  'LKLG' u16 version(2) u16 n_str u16 n_name u16 n_ui u16 n_glyph u16 n_text
  n_str  x { u16 id, u32 blob offset, u16 word count (without the $FFFF) }       n_name x { u8 table, u8 index, u32 blob offset, u8 byte count }
  n_ui   x { u16 key, u16 value }                                                  n_glyph x { u8 code, 30 bytes main font, 8 bytes menu font }   n_text x { u8 key length, u8 value length, key, value }  (our own UI text: English key -> translation, umlauts as bytes $80..$86)   then the blob (strings as u16 words incl. $FFFF, names as bytes)"""
import hashlib, json, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stringdump as sd

HANDLER = [0x15, 0xE, 0x01, 0xB, 0xC, 0x05, 0x07, 0x06, 0x04, 0x03, 0x02, 0x18, 0x0F, 0x0D, 0x08, 0x09, 0x0A, 0x17, 0x19]   # ControlChars table: code $56 + k -> handler index
CTL = {v: k for k, v in sd.CONTROL.items()}
NAMECTL = {v.strip("{}"): k for k, v in sd.NAME_CODES.items()}
EXTRA = {"ä": 0x6C, "ö": 0x6D, "ü": 0x6E, "ß": 0x71, "Ä": 0x72, "Ö": 0x73, "Ü": 0x74}   # codes whose tile slots are BLANK in the menu font (slots $6F / $70 hold other art)
MENUFONT = 0xDC76   # 1bpp 8x8 glyphs, 8 bytes each; the menu lists draw names with these tiles (patch_lang.py patches the tiles in RAM before the DMA)
LAYOUT = {"NewLine", "SoftNewLine", "Pause1s", "Pause1sOrInput", "Pause1_5sOrInput", "Pause2sOrInput", "BreakSpace", "BreakPoint", "Hyphen"}
UI_BYTES = {"ä": 0x80, "ö": 0x81, "ü": 0x82, "ß": 0x83, "Ä": 0x84, "Ö": 0x85, "Ü": 0x86}   # our own UI text (patch_options.py lk_chr maps these bytes to the extra glyph codes)
TABLES = {name: i for i, (name, _, _) in enumerate(sd.NAME_TABLES)}
TABLES["area"] = 5   # LK_RMNAMES v1: dungeon names for the room map (name entries table 5, index = MAP_AREAS position)
MAP_AREAS = [("SWAMP_SHRINE", "Swamp Shrine"), ("MERCATOR_DUNGEON", "Mercator Dungeon"), ("KN_LABYRINTH", "King Nole's Labyrinth"), ("KN_CAVE", "King Nole's Cave"),
             ("KN_PALACE", "King Nole's Palace"), ("LAKE_SHRINE", "Lake Shrine"), ("WATERFALL_SHRINE", "Waterfall Shrine"), ("THIEVES_HIDEOUT", "Thieves' Hideout"),
             ("DESTEL_WELL", "Destel Well"), ("MIR_TOWER", "Mir's Tower"), ("VERLA_MINES", "Verla Mines"), ("MASSAN_CAVE", "Massan Cave"), ("CRYPT", "Crypt"),
             ("GREENMAZE", "Greenmaze"), ("HELGAS_HUT", "Helga's Hut"), ("TIBOR", "Tibor"), ("RYUMA_LIGHTHOUSE", "Ryuma Lighthouse")]   # English = the fallback in the game (patch_roommap.py)
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


def menu_glyph(rom, base, kind):
    """8x8 menu font glyph (8 bytes) for an extra character: kind 'l' = lower case with the dots in the free top row, 'u' = capital (one middle row dropped, dots + gap on top), 's' = sharp s"""
    if kind == "s": return bytes([0x78, 0xCC, 0xCC, 0xD8, 0xCC, 0xC6, 0xC6, 0xDC])
    r = list(rom[MENUFONT + 8 * sd.MAIN.index(base):MENUFONT + 8 * sd.MAIN.index(base) + 8])
    if kind == "l": r[0] |= 0x44; return bytes(r)
    body = r[1:3] + r[4:8]; return bytes([0x44, 0x00] + body)


# LK_LGFR v1 (user 2026-11-13: French like German / English (JP)): the accented letters of French, per language file (codes are per language: the German file keeps ä..Ü on these codes).
# Free codes: $56..$5F and $6C..$6E, $71..$76 (blank menu font slots, outside the ROM's main font).  Lower case: the mark in the free rows 1..2 above the x-height (rows 4..10);
# capitals: a middle row dropped like Ä, the mark in row 0; cedilla in rows 11..12.  Our own UI text (patch_options.py lk_chr: bytes $80..$86 -> codes $6C..$6E, $71..$74) gets é è à ê ç ô â.
EXTRA_DE, UI_BYTES_DE = EXTRA, UI_BYTES
EXTRA_FR = {"é": 0x6C, "è": 0x6D, "à": 0x6E, "ê": 0x71, "ç": 0x72, "ô": 0x73, "â": 0x74, "î": 0x75, "û": 0x76,
            "ù": 0x56, "ë": 0x57, "ï": 0x58, "ü": 0x59, "É": 0x5A, "À": 0x5B, "Ç": 0x5C, "Ê": 0x5D, "È": 0x5E, "Ô": 0x5F}
UI_BYTES_FR = {"é": 0x80, "è": 0x81, "à": 0x82, "ê": 0x83, "ç": 0x84, "ô": 0x85, "â": 0x86}
FR_MARK = {"acute": [0x1000, 0x2000], "grave": [0x2000, 0x1000], "circ": [0x3000, 0x4800], "diaer": [0, 0x4800]}            # rows 1, 2 (12-bit rows, bit 0x8000 = column 0)
FR_MARK_I = {"circ": [0x4000, 0xA000], "diaer": [0, 0xA000]}                                                                # the narrow i (stem in column 1)
FR_MARK_CAP = {"acute": 0x1800, "grave": 0x6000, "circ": 0x3000}                                                          # one row (row 0) above a capital
FR_MENU = {"acute": [0x08, 0x10], "grave": [0x20, 0x10], "circ": [0x10, 0x28], "diaer": [0x44, 0x00]}                     # menu font rows 0, 1
FR_SET = {"é": ("e", "acute"), "è": ("e", "grave"), "ê": ("e", "circ"), "ë": ("e", "diaer"), "à": ("a", "grave"), "â": ("a", "circ"),
          "ù": ("u", "grave"), "û": ("u", "circ"), "ü": ("u", "diaer"), "ô": ("o", "circ"), "î": ("i", "circ"), "ï": ("i", "diaer"), "ç": ("c", "ced"),
          "É": ("E", "acute"), "È": ("E", "grave"), "Ê": ("E", "circ"), "À": ("A", "grave"), "Ô": ("O", "circ"), "Ç": ("C", "ced")}


def make_glyphs_fr(rom):
    g = {}
    for ch, (base, mk) in FR_SET.items():
        r = glyph_rows(rom, sd.MAIN.index(base)); mi = sd.MAIN.index(base); m = list(rom[MENUFONT + 8 * mi:MENUFONT + 8 * mi + 8])
        if mk == "ced":                                  # cedilla under c / C (main rows 11..12; menu: the letter one row up, the hook in row 7)
            r[11] |= 0x2000; r[12] |= 0x6000; m = m[1:] + [0x10]
        elif base.isupper():                             # capital: drop a middle row, the mark in row 0 (main) / row 0 + gap (menu), like Ä
            d = next((i for i in range(1, 10) if r[i] == r[i - 1]), 5)          # drop a row that repeats the one above (keeps E's middle bar)
            r = [FR_MARK_CAP.get(mk, 0x4800)] + r[:d] + r[d + 1:11] + [0] * 4
            dm = next((i for i in range(2, 7) if m[i] == m[i - 1]), 3)
            m = [{"acute": 0x18, "grave": 0x30, "circ": 0x38}.get(mk, 0x44), 0x00] + (m[1:dm] + m[dm + 1:8])[-6:]
        else:
            if base == "i": r[1] = r[2] = 0; m[0] = m[1] = 0; marks = FR_MARK_I[mk]; mm = {"circ": [0x40, 0xA0], "diaer": [0x00, 0xA0]}[mk]
            else: marks = FR_MARK[mk]; mm = FR_MENU[mk]
            r[1] |= marks[0]; r[2] |= marks[1]; m[0] |= mm[0]; m[1] |= mm[1]
        g[EXTRA_FR[ch]] = pack(r) + bytes(m)
    return g


def make_glyphs(rom):
    """derived glyphs: small letters get the diaeresis in the free rows above; capitals lose one middle row to make room for it in row 0; a drawn sharp s"""
    dots = 0x4800                                   # columns 1 and 4
    g = {}
    for ch, base in (("ä", "a"), ("ö", "o"), ("ü", "u")):
        r = glyph_rows(rom, sd.MAIN.index(base)); r[2] |= dots; g[EXTRA[ch]] = pack(r) + menu_glyph(rom, base, "l")
    for ch, base in (("Ä", "A"), ("Ö", "O"), ("Ü", "U")):
        r = glyph_rows(rom, sd.MAIN.index(base)); body = r[:5] + r[6:11]      # 11 rows -> 10 rows (a middle row is dropped)
        g[EXTRA[ch]] = pack([dots] + body + [0] * 4) + menu_glyph(rom, base, "u")
    ss = [0x7000, 0x8800, 0x8800, 0x9000, 0xB000, 0x8800, 0x8400, 0x8400, 0x8400, 0xBC00, 0xB800, 0, 0, 0, 0]
    g[EXTRA["ß"]] = pack(ss) + menu_glyph(rom, "s", "s")
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


NAMES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lang", "names.json")


def load_names():
    """lang/names.json: key -> {en, de, jp, auto} (the Names option; LK_LGNAMES v1)"""
    try: d = json.load(open(NAMES_FILE, encoding="utf-8"))
    except (OSError, ValueError): return {}
    return {k: v for k, v in d.items() if not k.startswith("_")}


def name_form(names, key, form, base, variant):
    """{=key} / {=key:gen}: the name in the language 'base' (de / en) or the Japanese original (variant 'jp'); German genitive: + s, or an apostrophe after s / x / z"""
    e = names.get(key)
    if e is None: raise ValueError("unknown name placeholder {=%s}" % key)
    n = e["jp"] if variant == "jp" else e.get(base, e["en"])
    if form == "gen":
        if base == "de": return n + "'" if n[-1] in "sxzß" else n + "s"
        return n + "'s"
    return n


def resolve(text, names, base, variant):
    import re
    return re.sub(r"\{=([a-z0-9_]+)(?::([a-z]+))?\}", lambda m: name_form(names, m.group(1), m.group(2), base, variant), text)


def jp_names_lang(en, names):
    """the original English text with the Japanese character names (en.jpn.bin): every English string / name table entry that contains a localized name word"""
    import re
    rep = [(e["en"], e["jp"]) for e in names.values() if e.get("auto", True) and e["en"] != e["jp"]]
    if not rep: return None
    pat = re.compile(r"\b(" + "|".join(re.escape(a) for a, b in rep) + r")\b"); m = dict(rep)
    lang = {"meta": {"code": "en", "name": "English"}, "strings": {}, "names": {}}
    for k, v in en.items():
        if k.startswith("item:") or k.startswith("menu:"): continue
        t = pat.sub(lambda x: m[x.group(1)], v)
        if t != v: lang["names" if ":" in k else "strings"][k] = {"h": hashlib.sha1(v.encode("utf-8")).hexdigest()[:8], "t": t}
    return lang


# LK_LGKO v1 (user 2026-11-13: Korean, based on the Japanese original): Hangul syllables from lang/ko_glyphs.dat (Galmuri 11, OFL; tools/kofont.py), codes assigned per
# language file: the characters of the NAMES first on byte codes (the name tables are bytes), the rest on $101.. (16-bit glyph words, language file version 3 like ja.bin);
# low bytes the printer treats specially ($00 space, $40 / $47 speech blips, $7B / $7C marks) and the name codes $69..$6B are never used.
KO_LO = [c for c in range(0x56, 0x100) if c not in (0x69, 0x6A, 0x6B, 0x7B, 0x7C)]
KO_HI = [c for c in range(0x101, 0x889) if (c & 0xFF) not in (0x00, 0x40, 0x47, 0x7B, 0x7C)]


def ko_glyph_rows(ch):
    d = getattr(ko_glyph_rows, "d", None)
    if d is None: d = ko_glyph_rows.d = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lang", "ko_glyphs.dat"), "rb").read()
    i = ord(ch) - 0xAC00; return [struct.unpack(">H", d[6 + 22 * i + 2 * k:8 + 22 * i + 2 * k])[0] for k in range(11)] + [0] * 4


def ko_codes(lang):
    import re
    hang = lambda t: [c for c in re.sub(r"\{[^}]*\}", "", t) if 0xAC00 <= ord(c) <= 0xD7A3]
    first, rest = [], []
    for blk in ("names", "item_dialog"):
        for e in lang.get(blk, {}).values():
            for c in hang(e["t"]):
                if c not in first: first.append(c)
    for t in lang.get("map_areas", {}).values():
        for c in hang(t):
            if c not in first: first.append(c)
    freq = {}
    for e in list(lang.get("strings", {}).values()) + list(lang.get("items_jp", {}).get("strings", {}).values()):
        for c in hang(e["t"]): freq[c] = freq.get(c, 0) + 1
    rest = sorted((c for c in freq if c not in first), key=lambda c: -freq[c])
    lo, hi, code = list(KO_LO), list(KO_HI), {}
    for c in first + rest: code[c] = (lo or hi).pop(0)
    return code


def build_one(rom, en, lang_path, out_path, variant="local"):
    lang = json.load(open(lang_path, encoding="utf-8")) if isinstance(lang_path, str) else lang_path
    nm_tab = load_names(); base = lang.get("meta", {}).get("names", lang.get("meta", {}).get("code", "en")[:2])
    global EXTRA, UI_BYTES; fr = base == "fr"; EXTRA, UI_BYTES = (EXTRA_FR, UI_BYTES_FR) if fr else (EXTRA_DE, UI_BYTES_DE)   # LK_LGFR v1
    lang = json.loads(json.dumps(lang))   # a copy: the placeholders are resolved per variant
    ko = base == "ko"
    if ko:   # LK_LGKO v1: resolve the placeholders first, then give every Hangul syllable a code
        for blk in ("strings", "names", "item_dialog"):
            for ent in lang.get(blk, {}).values():
                if "{=" in ent.get("t", ""): ent["t"] = resolve(ent["t"], nm_tab, base, variant)
        EXTRA, UI_BYTES = ko_codes(lang), {}
    for blk in ("strings", "names"):
        for d in (lang.get(blk, {}), lang.get("items_jp", {}).get(blk, {})):   # LK_JPITEMS v1: block 'items_jp' = lines / names for Options > Items = Japanese
            for ent in d.values():
                if "{=" in ent.get("t", ""): ent["t"] = resolve(ent["t"], nm_tab, base, variant)
    strs, names, blob, dropped = [], [], bytearray(), []
    def check(key, ent):
        src = en.get(key)
        if src is None: return "no such entry in the ROM"
        if hashlib.sha1(src.encode("utf-8")).hexdigest()[:8] != ent["h"]: return "English source differs from the one translated"
        if ctl_names(src) != ctl_names(ent["t"]): return "control codes differ: %s vs %s" % (ctl_names(src), ctl_names(ent["t"]))
        return None
    sl = [(k, e, int(k, 16)) for k, e in lang.get("strings", {}).items()] + [(k, e, int(k, 16) | 0x8000) for k, e in lang.get("items_jp", {}).get("strings", {}).items()]   # Items = Japanese: id | $8000
    for key, ent, sid in sl:
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
            strs.append((sid, len(blob), len(words))); blob += b"".join(struct.pack(">H", w) for w in words) + b"\xff\xff"
    nl = [(k, e, 0) for k, e in lang.get("names", {}).items()] + [(k, e, 0x80) for k, e in lang.get("items_jp", {}).get("names", {}).items()]   # Items = Japanese: item name index | $80
    nl += [(k, e, 0x40) for k, e in lang.get("item_dialog", {}).items()]   # LK_LGKO v1: item names used only by {Item} in the dialogue (patch_lang.py LK_JPITEMS v3: index | $40)
    for key, ent, ibit in nl:
        why = check(key, ent)
        if why: dropped.append((key, why)); continue
        tab, idx = key.split(":")
        try: data = b"".join(struct.pack(">H", v) for t, v in tokens(ent["t"])) if ko else bytes(v for t, v in tokens(ent["t"]))   # LK_LGKO v1: 16-bit name codes (file version 4)
        except ValueError as e: dropped.append((key, str(e))); continue
        names.append((TABLES[tab], int(idx) | ibit, len(blob), len(data))); blob += data
    for i, (key, _) in enumerate(MAP_AREAS):   # LK_RMNAMES v1: block 'map_areas' {KEY: name} (no English source to hash: our own text)
        t = lang.get("map_areas", {}).get(key)
        if not t: continue
        try: toks = tokens(t); data = b"".join(struct.pack(">H", v) for _, v in toks) if ko else bytes(v for _, v in toks)
        except (ValueError, struct.error) as e: dropped.append(("map_areas:" + key, str(e))); continue
        names.append((TABLES["area"], i, len(blob), len(data))); blob += data
    ui = [(UI_KEYS[k], v) for k, v in lang.get("ui_values", lang.get("ui", {})).items()]
    texts = []
    for k, v in lang.get("ui_text", {}).items():
        if "{=" in v: v = resolve(v, nm_tab, base, variant)
        try: vb = bytes(UI_BYTES.get(c) or ord(c) for c in v); kb = k.encode("ascii")
        except (ValueError, UnicodeEncodeError): dropped.append(("ui_text:" + k, "unsupported character")); continue
        if any(c > 0x86 or (c > 0x7E and c < 0x80) for c in vb) or len(kb) > 255 or len(vb) > 255: dropped.append(("ui_text:" + k, "unsupported character")); continue
        texts.append(bytes([len(kb), len(vb)]) + kb + vb)
    glyphs = {} if ko else (make_glyphs_fr(rom) if fr else make_glyphs(rom))
    ver = 2
    if ko: glyphs = {c: pack(ko_glyph_rows(ch)) + bytes(8) for ch, c in EXTRA.items()}; ver = 4   # LK_LGKO v1: 16-bit glyph codes + 16-bit name codes (language file version 4)
    out = b"LKLG" + struct.pack(">HHHHHH", ver, len(strs), len(names), len(ui), len(glyphs), len(texts))
    if ver == 4: out += b"\0\0\0\0"   # LK_LGKOMENU v1: u32 offset of the menu trailer (filled below)
    out += b"".join(struct.pack(">HIH", *e) for e in strs) + b"".join(struct.pack(">BBIB", *e) for e in names)
    out += b"".join(struct.pack(">HH", *e) for e in ui) + b"".join((struct.pack(">H", c) if ver >= 3 else bytes([c])) + d for c, d in sorted(glyphs.items())) + b"".join(texts) + bytes(blob)
    if ver == 4:   # LK_LGKOMENU v1: Start menu item names in Hangul: 'KOMN' + u16 glyph count + 8 bytes each (index 0 = blank) + u8 item count + per item u8 n + n * u16 glyph index
        d7 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lang", "ko_glyphs7.dat"), "rb").read()
        mg, mi, items = [bytes(8)], {}, []
        for i in range(64):
            ent = lang.get("item_dialog", {}).get("item:%02d" % i); t = ent["t"] if ent and not check("item:%02d" % i, ent) else ""
            if any(not (0xAC00 <= ord(c) <= 0xD7A3 or c == " ") for c in t) or len(t) > 9: t = ""   # only pure Hangul names fit the 9 menu tiles
            if len(mg) + len(set(c for c in t if c != " " and c not in mi)) > 256: t = ""   # 256 virtual tiles (patch_lang.py LK_LGKOMENU v1)
            ix = []
            for c in t:
                if c == " ": ix.append(0); continue
                if c not in mi:
                    k = ord(c) - 0xAC00; mi[c] = len(mg); mg.append(bytes([0]) + d7[6 + 7 * k:13 + 7 * k])   # rows 1..7 of the tile (row 0 free like the menu letters)
                ix.append(mi[c])
            items.append(ix)
        tr = b"KOMN" + struct.pack(">H", len(mg)) + b"".join(mg) + bytes([64]) + b"".join(bytes([len(ix)]) + b"".join(struct.pack(">H", v) for v in ix) for ix in items)
        out = out[:16] + struct.pack(">I", len(out)) + out[20:] + tr
    open(out_path, "wb").write(out)
    print("langbuild: %d strings, %d names, %d ui values, %d glyphs, %d ui texts -> %s (%d bytes); dropped %d" % (len(strs), len(names), len(ui), len(glyphs), len(texts), out_path, len(out), len(dropped)))
    for k, w in dropped: print("  dropped", k, "-", w)
    if "--preview" in sys.argv:
        preview(rom, glyphs, sys.argv[sys.argv.index("--preview") + 1], "Größe über Äpfel, Öl, Übung: Fuß schön Mädchen")
    return lang.get("meta", {})


def main():
    rom = open(sys.argv[1], "rb").read()
    en = sd.decode_all(rom)
    if os.path.isdir(sys.argv[2]):                  # directory mode: every lang/*.json -> <out>/<code>.bin + <out>/index.txt ("code<TAB>name", English is built in)
        outdir = sys.argv[3]; os.makedirs(outdir, exist_ok=True); idx = []; jl = jp_names_lang(en, load_names())
        for f in sorted(os.listdir(sys.argv[2])):
            if not f.endswith(".json") or f in ("friday_hints.json", "names.json", "en_items.json", "ja_map.json"): continue   # ja_map.json: tools/jplang.py   # en_items.json = the Japanese items for the original English (en.items.bin, below)   # friday_hints.json = the Friday Hints texts (tools/patch_friday.py), names.json = the Names option table: not languages
            code = f[:-5]
            meta = build_one(rom, en, os.path.join(sys.argv[2], f), os.path.join(outdir, code + ".bin"))
            lj = json.load(open(os.path.join(sys.argv[2], f), encoding="utf-8"))
            for blk in ("strings", "names"):   # LK_LGNAMES v1: entries not translated yet = the original English with the Japanese names
                for k, ent in ((jl or {}).get(blk) or {}).items(): lj.setdefault(blk, {}).setdefault(k, ent)
            build_one(rom, en, lj, os.path.join(outdir, code + ".jpn.bin"), "jp")   # the same language with the Japanese character names
            idx.append("%s\t%s" % (code, meta.get("name", code)))
        ei = os.path.join(sys.argv[2], "en_items.json")   # LK_JPITEMS v1: Options > Items = Japanese with the original English
        ej = json.load(open(ei, encoding="utf-8")) if os.path.exists(ei) else None
        if ej: build_one(rom, en, ej, os.path.join(outdir, "en.items.bin"))
        if jl and ej: jl["items_jp"] = ej.get("items_jp", {})
        if jl: build_one(rom, en, jl, os.path.join(outdir, "en.jpn.bin"), "jp")   # the original English with the Japanese names
        open(os.path.join(outdir, "index.txt"), "w", encoding="utf-8").write("\n".join(idx) + ("\n" if idx else ""))
        print("langbuild: index.txt with %d languages" % len(idx))
    else:
        build_one(rom, en, sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()

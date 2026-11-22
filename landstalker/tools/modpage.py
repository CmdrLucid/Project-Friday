#!/usr/bin/env python3
"""modpage.py ROM LANG_SRC [MODS_DIR]: writes the MOD WORKSHOP page into the user's mods folder (MOD LAYER, 2026-11-22; user: 'die HTML-Seite im
Mod-Folder zum Aufrufen', and NO local server on the player's computer).

    <mods>/Mod Workshop.html      the editor (tools/modpage.html, opened with a double click, works from the disk) WITH its data inside (v2
                                  2026-11-22 night: a separate workshop/data.js was invisible to the Deck's sandboxed Flatpak browsers, they
                                  may read only the opened file): per language id, current translation, the user's mod texts and the last
                                  build's refused list, plus the original English decoded from the user's OWN ROM (stays on this computer, never shipped)
The page keeps unsaved edits in the browser and saves 'Project-Friday-mod-<code>.json' as a download; the next start moves it into
<mods>/lang/ and rebuilds that language (tools/modlayer.py sync).  Rewritten only when an input changed (stamp in line 2 of the page)."""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import modlayer   # noqa: E402

SKIP = ("friday_hints.json", "names.json", "en_items.json", "ja_map.json")
BLOCK_ORDER = ("names", "map_areas", "item_dialog", "strings", "ui_text")   # + "friday" (Friday hints)


def inputs(src, mods, rom):
    fs = [rom, os.path.join(HERE, "modpage.html")] + [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.endswith(".json")]
    ml = os.path.join(mods, "lang")
    if os.path.isdir(ml): fs += [os.path.join(ml, f) for f in sorted(os.listdir(ml))]
    return "|".join("%s:%d" % (os.path.basename(f), int(os.path.getmtime(f))) for f in fs if os.path.isfile(f))


def build(rom, src, mods):
    import re
    import stringdump as sd
    en_all = sd.decode_all(open(rom, "rb").read())
    import fridaylang
    en, langs, used, fen = {}, [], set(), {}
    for f in sorted(os.listdir(src)):
        if not f.endswith(".json") or f in SKIP: continue
        code = f[:-5]
        lang = json.load(open(os.path.join(src, f), encoding="utf-8"))
        rows = []
        for blk in BLOCK_ORDER:
            cur = lang.get(blk) or {}
            if blk in ("names", "item_dialog", "strings"):
                keys = list(cur.keys())
                if blk == "strings": keys = sorted(set(keys) | {k for k in en_all if re.fullmatch(r"[0-9A-F]{4}", k)})
                for k in keys:
                    e = cur.get(k); rows.append([blk, k, e["t"] if e else ""]); used.add(k)
            else:
                for k, t in cur.items(): rows.append([blk, k, t])
        if code in ("de",) + tuple(fridaylang.NAME):   # MOD LAYER v1: the Friday hints (gentle level, the one the game shows); English reference = our own English hint
            for h in fridaylang.hints():
                t = h.get(code); rows.append(["friday", h.get("id", ""), t[0] if isinstance(t, list) and t else ""]); fen[h.get("id", "")] = (h.get("en") or [""])[0]
        rp = os.path.join(mods, "lang", code + ".report.json")
        try: rep = json.load(open(rp, encoding="utf-8")).get("refused", []) if os.path.isfile(rp) else []
        except (OSError, ValueError): rep = []
        langs.append({"code": code, "name": lang.get("meta", {}).get("name", code), "rows": rows, "mod": modlayer.load_lang_mod(code), "refused": rep})
    for k in used:
        if k in en_all: en[k] = en_all[k]
    return {"generated": time.strftime("%Y-%m-%d %H:%M"), "mods": os.path.abspath(mods), "en": en, "fen": fen, "languages": langs,
            "layout": ["NewLine", "SoftNewLine", "Pause1s", "Pause1sOrInput", "Pause1_5sOrInput", "Pause2sOrInput", "BreakSpace", "BreakPoint", "Hyphen"]}


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    rom, src = sys.argv[1], sys.argv[2]
    mods = sys.argv[3] if len(sys.argv) > 3 else modlayer.mods_dir()
    os.makedirs(os.path.join(mods, "lang"), exist_ok=True)
    stamp = "<!-- PF_STAMP " + inputs(src, mods, rom) + " -->"
    page = os.path.join(mods, modlayer.PAGE_NAME)
    try:
        with open(page, encoding="utf-8") as f:
            if f.readline() and f.readline().strip() == stamp: return 0
    except OSError: pass
    data = build(rom, src, mods)
    html = open(os.path.join(HERE, "modpage.html"), encoding="utf-8").read()
    js = "<script>window.PF_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";</script>"
    assert "<!--PF_DATA-->" in html and html.startswith("<!doctype html>\n")
    html = html.replace("<!doctype html>\n", "<!doctype html>\n" + stamp + "\n", 1).replace("<!--PF_DATA-->", js, 1)
    tmp = page + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(html)
    os.replace(tmp, page)
    print("modpage: %s (%d languages, %d KB)" % (page, len(data["languages"]), os.path.getsize(page) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())

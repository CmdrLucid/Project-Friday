#!/usr/bin/env python3
"""modlayer.py: the MOD LAYER (2026-11-22, user: natives should correct texts without editing our JSON; 'auf einer Modding-Ebene').

Mods live in the user's own data folder and are never touched by an update or a rebuild:
    Linux / Deck:  ~/.local/share/project-friday/mods/      (XDG_DATA_HOME respected)
    Windows:       %LOCALAPPDATA%\\Project-Friday\\mods\\
    override:      LANDSTALKER_MODS=<folder>
Layer 1 = language: mods/lang/<code>.json holds ONLY the changed texts, in the blocks of lang/<code>.json, as plain strings:
    {"meta": {"code": "ru", "format": 1}, "strings": {"02E4": "..."}, "names": {"menu:02": "..."},
     "item_dialog": {"item:00": "..."}, "map_areas": {"SWAMP_SHRINE": "..."}, "ui_text": {"Widescreen": "..."}}
tools/langbuild.py mixes them in when it builds a language (apply(); a refused text keeps the current translation, mods/lang/<code>.report.json);
tools/modpage.py writes the editor page 'Mod Workshop.html' into the mods folder (no server: a file opened in the browser); firstrun.py
rebuilds a language at start when its mod file is newer than the built language file.  No game data in a mod file: only the modder's own text."""
import hashlib, json, os

LANG_BLOCKS = ("strings", "names", "item_dialog")     # entries {"h": hash of the English source, "t": text}
LANG_PLAIN = ("map_areas", "ui_text")                 # plain strings (our own keys, no English source)


def data_dir():
    """the launcher's data folder (same rule as firstrun.py DATA)"""
    if os.environ.get("LANDSTALKER_DATA"): return os.environ["LANDSTALKER_DATA"]
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local"), "Project-Friday")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), "project-friday")


def mods_dir():
    return os.environ.get("LANDSTALKER_MODS") or os.path.join(data_dir(), "mods")


def lang_mod_path(code):
    return os.path.join(mods_dir(), "lang", code + ".json")


def load_lang_mod(code):
    """the language mod of code ({} when there is none or it cannot be read)"""
    p = lang_mod_path(code)
    if not os.path.isfile(p): return {}
    try:
        m = json.load(open(p, encoding="utf-8"))
        return m if isinstance(m, dict) else {}
    except (OSError, ValueError) as e:
        print("modlayer: %s not read (%s)" % (p, e))
        return {}


def save_lang_mod(code, mod):
    p = lang_mod_path(code)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    mod = {k: v for k, v in mod.items() if k == "meta" or v}   # empty blocks out
    mod.setdefault("meta", {}).update({"code": code, "format": 1})
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(mod, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)
    return p


def count(mod):
    return sum(len(mod.get(b) or {}) for b in LANG_BLOCKS + LANG_PLAIN)


def apply(lang, mod, en=None, check=None):
    """lang (a dict of lang/<code>.json) with the mod's texts in place; en = the ROM's English (stringdump.decode_all) for entries that
    are not translated yet (their source hash); check(block, key, text) -> None or the reason a text is refused (the entry then keeps its
    current translation instead of falling back to English).  Returns (texts replaced, [(block, key, reason)] refused)."""
    n, bad = 0, []
    for blk in LANG_BLOCKS:
        for k, t in (mod.get(blk) or {}).items():
            if not isinstance(t, str): continue
            why = check(blk, k, t) if check else None
            if why: bad.append((blk, k, why)); continue
            ent = lang.setdefault(blk, {}).get(k)
            if ent is None:
                if en is None or en.get(k) is None: continue
                ent = lang[blk][k] = {"h": hashlib.sha1(en[k].encode("utf-8")).hexdigest()[:8]}
            ent["t"] = t; n += 1
    for blk in LANG_PLAIN:
        for k, t in (mod.get(blk) or {}).items():
            if isinstance(t, str): lang.setdefault(blk, {})[k] = t; n += 1
    return n, bad


def save_report(code, refused):
    """mods/lang/<code>.report.json: the texts the last build refused (shown in the workshop page)"""
    p = os.path.join(mods_dir(), "lang", code + ".report.json")
    if not refused:
        if os.path.isfile(p): os.remove(p)
        return
    json.dump({"refused": [{"block": b, "key": k, "why": w} for b, k, w in refused]}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

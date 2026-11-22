#!/usr/bin/env python3
"""modlayer.py: the MOD LAYER (2026-11-22, user: natives should correct texts without editing our JSON; 'auf einer Modding-Ebene').

Where mods live (v3 2026-11-22 night, user: NOTHING outside the Project-Friday folder, nothing placed or fetched elsewhere unasked):
    Windows ZIP:        <unzipped folder>\\Mods\\
    Windows installer:  <install folder>\\Mods\\  (%LOCALAPPDATA%\\Programs\\Project-Friday; the uninstaller leaves it: RMDir of a non-empty folder)
    AppImage:           'Project-Friday Mods' next to the AppImage file (the folder the player put it in)
    Deck dev build:     landstalker/Mods/ in the repository (git-ignored)
    firstrun.py sets LANDSTALKER_MODS for the packages (mods_for_app()); without it: <this tools folder>/../Mods.
    inside:             Mod Workshop.html (the editor, ONE file with its data: sandboxed browsers such as the Deck's Flatpak Chrome /
                        Firefox may read only the file that was opened) and lang/
Layer 1 = language: lang/<code>.json holds ONLY the changed texts, in the blocks of lang/<code>.json, as plain strings:
    {"meta": {"code": "ru", "format": 1}, "strings": {"02E4": "..."}, "names": {"menu:02": "..."},
     "item_dialog": {"item:00": "..."}, "map_areas": {"SWAMP_SHRINE": "..."}, "ui_text": {"Widescreen": "..."}}
The page saves straight into that folder where the browser allows it (Chrome / Edge: folder chosen once) or offers a download that the
player moves into lang/ himself (Firefox).  tools/langbuild.py mixes the mods in when it builds a language (apply(); a refused text keeps
the current translation, lang/<code>.report.json); sync() = rebuild the changed languages + rewrite the page (firstrun.py at every start).
No game data in a mod file: only the modder's own text.

    python3 tools/modlayer.py sync ROM LANG_SRC OUT_LANG     rebuild languages whose mod changed + rewrite the page (what a start does)
    python3 tools/modlayer.py where                          print the mods folder"""
import hashlib, json, os, subprocess, sys

LANG_BLOCKS = ("strings", "names", "item_dialog")     # entries {"h": hash of the English source, "t": text}
LANG_PLAIN = ("map_areas", "ui_text", "friday", "charnames")   # plain strings (our own keys, no English source); friday = Friday hints {hint id: gentle text} (lang/friday_hints.json); charnames = MOD LAYER 2 character names {names.json key: name} (Names = Localized only)


def data_dir():
    """the launcher's data folder (same rule as firstrun.py DATA)"""
    if os.environ.get("LANDSTALKER_DATA"): return os.environ["LANDSTALKER_DATA"]
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local"), "Project-Friday")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), "project-friday")


MODS_NAME = "Mods"                    # inside the Project-Friday folder (ZIP / installer / dev repository)
APPIMAGE_MODS = "Project-Friday Mods"  # next to the AppImage file
PAGE_NAME = "Mod Workshop.html"


def mods_for_app(app_dir):
    """the mods folder of a package whose files lie in app_dir (firstrun.py HERE): next to the AppImage file for an AppImage (its own
    folder is a read-only mount), else <app_dir>/Mods"""
    if os.environ.get("APPIMAGE"): return os.path.join(os.path.dirname(os.path.abspath(os.environ["APPIMAGE"])), APPIMAGE_MODS)
    return os.path.join(app_dir, MODS_NAME)


def mods_dir():
    return os.environ.get("LANDSTALKER_MODS") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), MODS_NAME)


def sync(rom, src, outdir):
    """what a start does: rebuild every language whose mod file is newer than its built file, or whose mod file was removed since it was
    built with one (<code>.modded from langbuild) (langbuild --only, ~3 s each), then rewrite the workshop page (tools/modpage.py, only when an input changed)"""
    here = os.path.dirname(os.path.abspath(__file__))
    ml = os.path.join(mods_dir(), "lang")
    todo = []
    if os.path.isdir(ml):
        for f in sorted(os.listdir(ml)):
            code = f[:-5] if f.endswith(".json") and not f.endswith(".report.json") else ""
            out = os.path.join(outdir, code + ".bin")
            if code and os.path.isfile(os.path.join(src, f)) and (not os.path.isfile(out) or os.path.getmtime(os.path.join(ml, f)) > os.path.getmtime(out)): todo.append(code)
    if os.path.isdir(outdir):   # a language built with a mod whose file is gone now (the player deleted it): back to the plain translation (langbuild <code>.modded)
        for f in sorted(os.listdir(outdir)):
            if f.endswith(".modded") and not os.path.isfile(os.path.join(ml, f[:-7] + ".json")) and f[:-7] not in todo: todo.append(f[:-7])
    for code in todo:
        r = subprocess.run([sys.executable, os.path.join(here, "langbuild.py"), rom, src, outdir, "--only", code], capture_output=True, text=True, timeout=300)
        print("modlayer: rebuilt %s (exit %d)" % (code, r.returncode)); sys.stdout.write(r.stdout[-2000:])
    r = subprocess.run([sys.executable, os.path.join(here, "modpage.py"), rom, src, mods_dir()], capture_output=True, text=True, timeout=120)
    sys.stdout.write(r.stdout[-2000:] + r.stderr[-2000:])


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
            if not isinstance(t, str): continue
            why = check(blk, k, t) if check and blk == "charnames" else None   # MOD LAYER 2: names checked (key known, no codes, length)
            if why: bad.append((blk, k, why)); continue
            lang.setdefault(blk, {})[k] = t; n += 1
    return n, bad


def save_report(code, refused):
    """mods/lang/<code>.report.json: the texts the last build refused (shown in the workshop page)"""
    p = os.path.join(mods_dir(), "lang", code + ".report.json")
    if not refused:
        if os.path.isfile(p): os.remove(p)
        return
    json.dump({"refused": [{"block": b, "key": k, "why": w} for b, k, w in refused]}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    a = sys.argv[1:]
    if a[:1] == ["where"]: print(mods_dir()); return 0
    if a[:1] == ["sync"] and len(a) == 4: sync(*a[1:]); return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())

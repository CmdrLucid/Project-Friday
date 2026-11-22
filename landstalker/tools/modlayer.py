#!/usr/bin/env python3
"""modlayer.py: the MOD LAYER (2026-11-22, user: natives should correct texts without editing our JSON; 'auf einer Modding-Ebene').

Mods live in a VISIBLE folder of the user (v2 2026-11-22 night: the hidden data folder was not user friendly) and are never touched by an
update or a rebuild:
    Linux / Deck:  ~/Documents/Project-Friday Mods/          (the XDG documents folder, xdg-user-dir DOCUMENTS)
    Windows:       Documents\\Project-Friday Mods\\              (the known folder, also when it is moved to OneDrive)
    override:      LANDSTALKER_MODS=<folder>
    inside:        Mod Workshop.html (the editor, ONE file with its data: sandboxed browsers such as the Deck's Flatpak Chrome / Firefox
                   may read only the file that was opened) and lang/
Layer 1 = language: lang/<code>.json holds ONLY the changed texts, in the blocks of lang/<code>.json, as plain strings:
    {"meta": {"code": "ru", "format": 1}, "strings": {"02E4": "..."}, "names": {"menu:02": "..."},
     "item_dialog": {"item:00": "..."}, "map_areas": {"SWAMP_SHRINE": "..."}, "ui_text": {"Widescreen": "..."}}
The page saves a download 'Project-Friday-mod-<code>.json'; pickup() moves such files from the Downloads folder into lang/ at the next
start (no folder to find for the player).  tools/langbuild.py mixes the mods in when it builds a language (apply(); a refused text keeps
the current translation, lang/<code>.report.json); sync() = migrate + pickup + rebuild the changed languages + rewrite the page
(firstrun.py at every start; CLI below).  No game data in a mod file: only the modder's own text.

    python3 tools/modlayer.py sync ROM LANG_SRC OUT_LANG     pickup + rebuild changed languages + page (what a start does)
    python3 tools/modlayer.py pickup                         only move downloaded mod files into lang/
    python3 tools/modlayer.py where                          print the mods folder"""
import glob, hashlib, json, os, shutil, subprocess, sys

LANG_BLOCKS = ("strings", "names", "item_dialog")     # entries {"h": hash of the English source, "t": text}
LANG_PLAIN = ("map_areas", "ui_text", "friday")       # plain strings (our own keys, no English source); friday = Friday hints {hint id: gentle text} (lang/friday_hints.json)


def data_dir():
    """the launcher's data folder (same rule as firstrun.py DATA)"""
    if os.environ.get("LANDSTALKER_DATA"): return os.environ["LANDSTALKER_DATA"]
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local"), "Project-Friday")
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"), "project-friday")


def user_dir(kind):
    """the user's visible Documents ('DOCUMENTS') or Downloads ('DOWNLOAD') folder"""
    home = os.path.expanduser("~")
    if os.name == "nt":
        try:   # SHGetKnownFolderPath: FOLDERID_Documents / FOLDERID_Downloads (a moved / OneDrive folder too)
            import ctypes, uuid
            from ctypes import wintypes
            g = uuid.UUID({"DOCUMENTS": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", "DOWNLOAD": "{374DE290-123F-4565-9164-39C4925E467B}"}[kind])
            class GUID(ctypes.Structure): _fields_ = [("b", ctypes.c_byte * 16)]
            gid = GUID(); ctypes.memmove(ctypes.byref(gid), g.bytes_le, 16); out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(gid), 0, None, ctypes.byref(out)) == 0:
                p = out.value; ctypes.windll.ole32.CoTaskMemFree(out)
                if p: return p
        except Exception:
            pass
        return os.path.join(os.environ.get("USERPROFILE") or home, {"DOCUMENTS": "Documents", "DOWNLOAD": "Downloads"}[kind])
    try:
        p = subprocess.run(["xdg-user-dir", kind], capture_output=True, text=True, timeout=5).stdout.strip()
        if p and os.path.abspath(p) != os.path.abspath(home): return p
    except Exception:
        pass
    return os.path.join(home, {"DOCUMENTS": "Documents", "DOWNLOAD": "Downloads"}[kind])


MODS_NAME = "Project-Friday Mods"
PAGE_NAME = "Mod Workshop.html"
DL_PREFIX = "Project-Friday-mod-"


def mods_dir():
    return os.environ.get("LANDSTALKER_MODS") or os.path.join(user_dir("DOCUMENTS"), MODS_NAME)


def migrate():
    """v1 kept the mods in the hidden data folder (<data>/mods): move the user's mod files to the visible folder once and remove the
    old generated page (Mod Workshop.html + workshop/data.js) and empty folders"""
    old = os.path.join(data_dir(), "mods")
    if os.environ.get("LANDSTALKER_MODS") or not os.path.isdir(old) or os.path.abspath(old) == os.path.abspath(mods_dir()): return
    new = os.path.join(mods_dir(), "lang"); os.makedirs(new, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(old, "lang", "*.json"))):
        if f.endswith(".report.json"): os.remove(f); continue
        dst = os.path.join(new, os.path.basename(f))
        if not os.path.exists(dst): shutil.move(f, dst); print("modlayer: moved %s -> %s" % (f, dst))
    for f in (os.path.join(old, "Mod Workshop.html"), os.path.join(old, "workshop", "data.js")):
        if os.path.isfile(f): os.remove(f)
    for d in (os.path.join(old, "workshop"), os.path.join(old, "lang"), old):
        try: os.rmdir(d)
        except OSError: pass


def pickup():
    """move the page's downloads (Downloads/Project-Friday-mod-<code>.json, also 'Project-Friday-mod-ru (1).json' and the like) into
    lang/<code>.json; the newest per language wins, older copies are removed.  Only files that are mod files (meta.code + format) are
    touched.  Returns the language codes that changed."""
    dl = user_dir("DOWNLOAD"); best = {}
    for f in glob.glob(os.path.join(dl, DL_PREFIX + "*.json")):
        try:
            m = json.load(open(f, encoding="utf-8")); code = m["meta"]["code"]
            if not (isinstance(m, dict) and m["meta"].get("format") == 1 and isinstance(code, str) and code.isalnum() and len(code) <= 8): continue
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
        best.setdefault(code, []).append((os.path.getmtime(f), f))
    done = []
    for code, fs in sorted(best.items()):
        fs.sort(); dst = lang_mod_path(code); os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(fs[-1][1], dst); os.utime(dst)   # mtime = now: newer than the built language file -> rebuilt
        for _, f in fs[:-1]: os.remove(f)
        print("modlayer: %s -> %s" % (fs[-1][1], dst)); done.append(code)
    return done


def sync(rom, src, outdir):
    """what a start does: migrate, pickup, rebuild every language whose mod file is newer than its built file (langbuild --only, ~3 s
    each), then rewrite the workshop page (tools/modpage.py, only when an input changed)"""
    here = os.path.dirname(os.path.abspath(__file__))
    migrate(); pickup()
    ml = os.path.join(mods_dir(), "lang")
    if os.path.isdir(ml):
        for f in sorted(os.listdir(ml)):
            code = f[:-5] if f.endswith(".json") and not f.endswith(".report.json") else ""
            out = os.path.join(outdir, code + ".bin")
            if code and os.path.isfile(os.path.join(src, f)) and (not os.path.isfile(out) or os.path.getmtime(os.path.join(ml, f)) > os.path.getmtime(out)):
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
            if isinstance(t, str): lang.setdefault(blk, {})[k] = t; n += 1
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
    if a[:1] == ["pickup"]: migrate(); pickup(); return 0
    if a[:1] == ["sync"] and len(a) == 4: sync(*a[1:]); return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Builds the Project-Friday release AppImage (x86_64).  It contains NOTHING from the game or generated from it:
launcher, patch tools, pristine genrecomp / Genesis Plus GX sources, a C compiler (zig), SDL2 headers, the capstone
wheel and the licence texts.  The game is built on the user's machine from the user's own ROM (firstrun.py).

  python3 packaging/make_appimage.py [--out DIR] [--keep-appdir]

Needs network on the build machine (zig, appimagetool, capstone wheel are downloaded once into ~/.cache/project-friday-build).
"""
import argparse, glob, hashlib, json, os, shutil, stat, subprocess, sys, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIG_VERSION = "0.16.0"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "project-friday-build")
APPIMAGETOOL = "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"


def fetch(url, dest):
    if os.path.isfile(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print("download", url, flush=True)
    urllib.request.urlretrieve(url, dest + ".part")
    os.replace(dest + ".part", dest)
    return dest


def get_zig():
    idx = json.load(urllib.request.urlopen("https://ziglang.org/download/index.json"))
    t = idx[ZIG_VERSION]["x86_64-linux"]
    f = fetch(t["tarball"], os.path.join(CACHE, os.path.basename(t["tarball"])))
    h = hashlib.sha256(open(f, "rb").read()).hexdigest()
    if h != t["shasum"]:
        os.remove(f)
        sys.exit("zig checksum mismatch")
    d = os.path.join(CACHE, "zig-" + ZIG_VERSION)
    if not os.path.isdir(d):
        with tarfile.open(f) as tf:
            tf.extractall(CACHE, filter="data")
        os.rename(os.path.join(CACHE, "zig-x86_64-linux-" + ZIG_VERSION), d)
    return d


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--keep-appdir", action="store_true", help="keep the intermediate Project-Friday.AppDir folder")
    a = ap.parse_args()

    if not (os.environ.get("CI") and os.path.isfile(os.path.join(ROOT, "vendor", "genrecomp", "CMakeLists.txt"))):
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_vendor.py")])   # CI: vendor was fetched at the pinned revision before
    zig = get_zig()
    app = os.path.join(a.out, "Project-Friday.AppDir")
    if os.path.isdir(app):
        shutil.rmtree(app)
    share = os.path.join(app, "usr", "share", "project-friday")
    os.makedirs(share)

    # launcher + build inputs (no ROM, nothing generated)
    for f in ("firstrun.py", "build.sh", "recomp.json"):
        copy(os.path.join(ROOT, f), os.path.join(share, f))
    copy(os.path.join(ROOT, "src", "main.c"), os.path.join(share, "src", "main.c"))
    copy(os.path.join(ROOT, "docs", "symbols.json"), os.path.join(share, "docs", "symbols.json"))
    copy(os.path.join(ROOT, "docs", "ENTITIES.md"), os.path.join(share, "docs", "ENTITIES.md"))   # read by tools/patch_shadow.py (entity names -> figure table); missing = the first start fails (found by the AppImage first-run test 2026-10-25)
    copy(os.path.join(ROOT, "docs", "ROOMS.md"), os.path.join(share, "docs", "ROOMS.md"))   # read by tools/roommap.py (room names -> map areas)
    for f in sorted(os.listdir(os.path.join(ROOT, "lang"))):   # translations (our own text, tools/langbuild.py builds them on the player's machine)
        if f.endswith(".json"):
            copy(os.path.join(ROOT, "lang", f), os.path.join(share, "lang", f))
    for f in sorted(os.listdir(os.path.join(ROOT, "tools"))):
        p = os.path.join(ROOT, "tools", f)
        if os.path.isfile(p) and f.endswith((".py", ".c", ".h", ".json", ".sh")):
            copy(p, os.path.join(share, "tools", f))
    shutil.copytree(os.path.join(ROOT, "vendor", "genrecomp"), os.path.join(share, "vendor", "genrecomp"))
    shutil.copytree(zig, os.path.join(share, "vendor", "zig"), symlinks=True)
    # SDL2 headers (the library itself is the user's system SDL2)
    hdr = "/usr/include/SDL2"
    if not os.path.isdir(hdr):
        sys.exit("SDL2 headers not found at /usr/include/SDL2 (install the SDL2 development package on the build machine)")
    shutil.copytree(hdr, os.path.join(share, "vendor", "sdl2", "include", "SDL2"))
    # Debian / Ubuntu: SDL_config.h only forwards to the multiarch file <SDL2/_real_SDL_config.h> (/usr/include/<triplet>/SDL2/)
    cfg = os.path.join(share, "vendor", "sdl2", "include", "SDL2", "SDL_config.h")
    if "_real_SDL_config.h" in open(cfg).read():
        real = glob.glob("/usr/include/*/SDL2/_real_SDL_config.h")
        if not real:
            sys.exit("SDL_config.h forwards to _real_SDL_config.h but that file was not found on the build machine")
        shutil.copy2(real[0], os.path.join(share, "vendor", "sdl2", "include", "SDL2", "_real_SDL_config.h"))
    # capstone wheel (python module used by the generator)
    wh = os.path.join(share, "vendor", "wheels")
    os.makedirs(wh)
    subprocess.check_call([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps", "-d", wh, "capstone==5.0.6"])

    # licences + notices
    lic = os.path.join(app, "usr", "share", "licenses", "project-friday")
    os.makedirs(lic)
    gr = os.path.join(ROOT, "vendor", "genrecomp")
    copy(os.path.join(gr, "LICENSE"), os.path.join(lic, "genrecomp-LICENSE-MIT.txt"))
    copy(os.path.join(gr, "ext", "Genesis-Plus-GX", "LICENSE.txt"), os.path.join(lic, "Genesis-Plus-GX-LICENSE.txt"))
    copy(os.path.join(gr, "ext", "Genesis-Plus-GX", "core", "m68k", "m68k.h"), os.path.join(lic, "Musashi-header-with-licence.h.txt"))
    copy(os.path.join(zig, "LICENSE"), os.path.join(lic, "zig-LICENSE-MIT.txt"))
    # capstone licence: from the wheel itself; SDL2 (zlib) licence: the header comment of SDL.h (works on every build machine)
    import re, zipfile
    whl = glob.glob(os.path.join(wh, "capstone-*.whl"))
    if not whl:
        sys.exit("capstone wheel missing")
    with zipfile.ZipFile(whl[0]) as z:
        names = [n for n in z.namelist() if n.upper().endswith("LICENSE.TXT")]
        if not names:
            sys.exit("capstone licence not found in the wheel")
        open(os.path.join(lic, "capstone-LICENSE-BSD.txt"), "wb").write(z.read(names[0]))
    m = re.match(r"\s*/\*(.*?)\*/", open(os.path.join(hdr, "SDL.h")).read(), re.S)
    if not m or "Permission is granted" not in m.group(1):
        sys.exit("SDL2 licence text not found in SDL.h")
    open(os.path.join(lic, "SDL2-LICENSE-zlib.txt"), "w").write(m.group(1).strip() + "\n")
    copy(os.path.join(ROOT, "..", "README.md"), os.path.join(lic, "Project-Friday-README.md"))
    copy(os.path.join(ROOT, "..", "LICENSE"), os.path.join(lic, "Project-Friday-LICENSE-MIT.txt"))
    open(os.path.join(lic, "NOTICE.txt"), "w").write(
        "Project-Friday release package\n\n"
        "This package contains NO ROM, NO game data and NO code generated from the game. On the first start the\n"
        "launcher builds the game on YOUR computer from YOUR OWN Landstalker ROM. The result is derived from that ROM:\n"
        "do not give it (or the ROM) to anyone else.\n\n"
        "Non-commercial use only: Genesis Plus GX and Musashi are free for non-commercial use only.\n"
        "Complete source of everything in this package: usr/share/project-friday (launcher, patches, tools,\n"
        "vendor/genrecomp = genrecomp + Genesis Plus GX unmodified; our changes are the tools/patch_*.py files,\n"
        "applied on your machine) and https://github.com/cmdrlucid/Project-Friday\n"
        "Zig (MIT) is the bundled C compiler, SDL2 headers (zlib) are used to compile against your system's SDL2.\n")

    for need in ("genrecomp-LICENSE-MIT.txt", "Genesis-Plus-GX-LICENSE.txt", "Musashi-header-with-licence.h.txt", "zig-LICENSE-MIT.txt",
                 "capstone-LICENSE-BSD.txt", "SDL2-LICENSE-zlib.txt", "Project-Friday-LICENSE-MIT.txt", "NOTICE.txt"):
        if not os.path.isfile(os.path.join(lic, need)):
            sys.exit("licence file missing in the package: " + need)

    # AppRun, desktop file, icon
    run = os.path.join(app, "AppRun")
    open(run, "w").write("""#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
cd "$HOME" || true
exec python3 "$HERE/usr/share/project-friday/firstrun.py" "$@"
""")
    os.chmod(run, 0o755)
    open(os.path.join(app, "project-friday.desktop"), "w").write(
        "[Desktop Entry]\nType=Application\nName=Project-Friday (Landstalker)\n"
        "Comment=Landstalker recompiled for PC / Steam Deck - bring your own ROM\nExec=AppRun\nIcon=project-friday\n"
        "Categories=Game;\nTerminal=false\n")
    import struct, zlib
    w = h = 256
    raw = (b"\x00" + b"\x20\x40\x90\xff" * w) * h

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(os.path.join(app, "project-friday.png"), "wb").write(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    tool = fetch(APPIMAGETOOL, os.path.join(CACHE, "appimagetool-x86_64.AppImage"))
    os.chmod(tool, os.stat(tool).st_mode | stat.S_IEXEC)
    out = os.path.join(a.out, "Project-Friday-x86_64.AppImage")
    env = dict(os.environ, ARCH="x86_64")
    subprocess.check_call([tool, "--appimage-extract-and-run", "--no-appstream", app, out], env=env)
    if not a.keep_appdir:
        shutil.rmtree(app)   # only the .AppImage is the result
    print("built", out, "%.0f MB" % (os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()

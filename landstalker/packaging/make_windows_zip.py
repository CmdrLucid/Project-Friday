#!/usr/bin/env python3
"""Builds the Windows release package Project-Friday-windows-x64.zip (cross-built on Linux, e.g. in GitHub Actions).
Like the AppImage it contains NOTHING from the game or generated from it: launcher exe, bundled Python (embeddable), patch tools,
pristine genrecomp / Genesis Plus GX sources, a C compiler (zig for Windows), the SDL2 MinGW development files + SDL2.dll, the capstone wheel
and the licence texts. The game is built on the user's PC from the user's own ROM (firstrun.py), the result is tied to that ROM.

  python3 packaging/make_windows_zip.py [--out DIR]

Needs network on the build machine (everything is downloaded once into ~/.cache/project-friday-build)."""
import argparse, glob, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from make_appimage import fetch, get_zig, copy, CACHE, ZIG_VERSION   # noqa: E402

PY_VERSION = "3.13.5"
PY_EMBED = "https://www.python.org/ftp/python/%s/python-%s-embed-amd64.zip" % (PY_VERSION, PY_VERSION)
SDL_VERSION = "2.32.10"
SDL_URL = "https://github.com/libsdl-org/SDL/releases/download/release-%s/SDL2-devel-%s-mingw.tar.gz" % (SDL_VERSION, SDL_VERSION)
CAPSTONE = "capstone==5.0.6"


def get_zig_windows():
    idx = json.load(urllib.request.urlopen("https://ziglang.org/download/index.json"))
    t = idx[ZIG_VERSION]["x86_64-windows"]
    f = fetch(t["tarball"], os.path.join(CACHE, os.path.basename(t["tarball"])))
    if hashlib.sha256(open(f, "rb").read()).hexdigest() != t["shasum"]:
        os.remove(f)
        sys.exit("zig (windows) checksum mismatch")
    d = os.path.join(CACHE, "zig-windows-" + ZIG_VERSION)
    if not os.path.isdir(d):
        with zipfile.ZipFile(f) as z:
            z.extractall(CACHE)
        os.rename(os.path.join(CACHE, "zig-x86_64-windows-" + ZIG_VERSION), d)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if not (os.environ.get("CI") and os.path.isfile(os.path.join(ROOT, "vendor", "genrecomp", "CMakeLists.txt"))):
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_vendor.py")])
    zig_linux = get_zig()
    zig_win = get_zig_windows()
    pyzip = fetch(PY_EMBED, os.path.join(CACHE, os.path.basename(PY_EMBED)))
    sdl_tar = fetch(SDL_URL, os.path.join(CACHE, os.path.basename(SDL_URL)))

    pkg = os.path.join(a.out, "Project-Friday")
    if os.path.isdir(pkg):
        shutil.rmtree(pkg)
    os.makedirs(pkg)

    # launcher + build inputs (no ROM, nothing generated)
    for f in ("firstrun.py", "build.sh", "recomp.json"):
        copy(os.path.join(ROOT, f), os.path.join(pkg, f))
    copy(os.path.join(ROOT, "src", "main.c"), os.path.join(pkg, "src", "main.c"))
    copy(os.path.join(ROOT, "docs", "symbols.json"), os.path.join(pkg, "docs", "symbols.json"))
    copy(os.path.join(ROOT, "docs", "ENTITIES.md"), os.path.join(pkg, "docs", "ENTITIES.md"))   # read by tools/patch_shadow.py (entity names -> figure table); missing = the first start fails (found by the AppImage first-run test 2026-10-25)
    copy(os.path.join(ROOT, "docs", "ROOMS.md"), os.path.join(pkg, "docs", "ROOMS.md"))   # read by tools/roommap.py (room names -> map areas)
    for f in sorted(os.listdir(os.path.join(ROOT, "lang"))):   # translations (our own text, tools/langbuild.py builds them on the player's machine)
        if f.endswith(".json"):
            copy(os.path.join(ROOT, "lang", f), os.path.join(pkg, "lang", f))
    for f in sorted(os.listdir(os.path.join(ROOT, "tools"))):
        p = os.path.join(ROOT, "tools", f)
        if os.path.isfile(p) and f.endswith((".py", ".c", ".h", ".json", ".sh")):
            copy(p, os.path.join(pkg, "tools", f))
    shutil.copytree(os.path.join(ROOT, "vendor", "genrecomp"), os.path.join(pkg, "vendor", "genrecomp"))
    shutil.copytree(zig_win, os.path.join(pkg, "vendor", "zig"))

    # SDL2 MinGW development files: headers, import / main libraries, SDL2.dll, licence
    with tarfile.open(sdl_tar) as t:
        t.extractall(os.path.join(CACHE, "sdl2-mingw-" + SDL_VERSION), filter="data")
    sdl_root = os.path.join(CACHE, "sdl2-mingw-" + SDL_VERSION, "SDL2-" + SDL_VERSION)
    mg = os.path.join(sdl_root, "x86_64-w64-mingw32")
    vs = os.path.join(pkg, "vendor", "sdl2")
    shutil.copytree(os.path.join(mg, "include"), os.path.join(vs, "include"))
    os.makedirs(os.path.join(vs, "lib"))
    os.makedirs(os.path.join(vs, "bin"))
    for f in ("libSDL2main.a", "libSDL2.dll.a"):
        shutil.copy2(os.path.join(mg, "lib", f), os.path.join(vs, "lib", f))
    shutil.copy2(os.path.join(mg, "bin", "SDL2.dll"), os.path.join(vs, "bin", "SDL2.dll"))

    # bundled Python (embeddable) + capstone: without python3xx._pth the script folder is on sys.path (the tools import their neighbours)
    py = os.path.join(pkg, "python")
    with zipfile.ZipFile(pyzip) as z:
        z.extractall(py)
    for f in glob.glob(os.path.join(py, "python*._pth")):
        os.remove(f)
    wheels = os.path.join(CACHE, "wheels-win")
    os.makedirs(wheels, exist_ok=True)
    if not glob.glob(os.path.join(wheels, "capstone-*.whl")):
        subprocess.check_call([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps", "--platform", "win_amd64", "--python-version", "3.13",
                               "--only-binary=:all:", "-d", wheels, CAPSTONE])
    whl = glob.glob(os.path.join(wheels, "capstone-*.whl"))[0]
    sp = os.path.join(py, "Lib", "site-packages")
    os.makedirs(sp, exist_ok=True)
    with zipfile.ZipFile(whl) as z:
        z.extractall(sp)

    # licences + notices
    lic = os.path.join(pkg, "licenses")
    os.makedirs(lic)
    gr = os.path.join(ROOT, "vendor", "genrecomp")
    copy(os.path.join(gr, "LICENSE"), os.path.join(lic, "genrecomp-LICENSE-MIT.txt"))
    copy(os.path.join(gr, "ext", "Genesis-Plus-GX", "LICENSE.txt"), os.path.join(lic, "Genesis-Plus-GX-LICENSE.txt"))
    copy(os.path.join(gr, "ext", "Genesis-Plus-GX", "core", "m68k", "m68k.h"), os.path.join(lic, "Musashi-header-with-licence.h.txt"))
    copy(os.path.join(zig_win, "LICENSE"), os.path.join(lic, "zig-LICENSE-MIT.txt"))
    copy(os.path.join(sdl_root, "LICENSE.txt"), os.path.join(lic, "SDL2-LICENSE-zlib.txt"))
    for n in glob.glob(os.path.join(sp, "capstone-*.dist-info", "LICENSE*")):
        copy(n, os.path.join(lic, "capstone-LICENSE-BSD.txt"))
    pylic = os.path.join(py, "LICENSE.txt")
    if os.path.isfile(pylic):
        copy(pylic, os.path.join(lic, "Python-LICENSE-PSF.txt"))
    copy(os.path.join(ROOT, "..", "README.md"), os.path.join(lic, "Project-Friday-README.md"))
    copy(os.path.join(ROOT, "..", "LICENSE"), os.path.join(lic, "Project-Friday-LICENSE-MIT.txt"))
    notice = (
        "Project-Friday release package (Windows, 64 bit)\n\n"
        "This package contains NO ROM, NO game data and NO code generated from the game. On the first start the launcher\n"
        "builds the game on YOUR computer from YOUR OWN Landstalker ROM (a few minutes, once). The result is derived from that ROM:\n"
        "do not give it (or the ROM) to anyone else.\n\n"
        "Non-commercial use only: Genesis Plus GX and Musashi are free for non-commercial use only.\n"
        "Complete source of everything in this package: this folder (launcher, patches, tools, vendor\\genrecomp = genrecomp + Genesis Plus GX\n"
        "unmodified; our changes are the tools\\patch_*.py files, applied on your machine) and https://github.com/cmdrlucid/Project-Friday\n"
        "Bundled: Python (embeddable, PSF licence), zig (MIT, C compiler), SDL2 (zlib), capstone (BSD).\n\n"
        "Start: double-click Project-Friday.exe. Built game, settings and the remembered ROM path live in %LOCALAPPDATA%\\Project-Friday\n"
        "(delete that folder to start fresh).\n")
    open(os.path.join(lic, "NOTICE.txt"), "w", newline="\r\n").write(notice)
    open(os.path.join(pkg, "README.txt"), "w", newline="\r\n").write(notice)
    for need in ("genrecomp-LICENSE-MIT.txt", "Genesis-Plus-GX-LICENSE.txt", "Musashi-header-with-licence.h.txt", "zig-LICENSE-MIT.txt",
                 "SDL2-LICENSE-zlib.txt", "capstone-LICENSE-BSD.txt", "Project-Friday-LICENSE-MIT.txt", "NOTICE.txt"):
        if not os.path.isfile(os.path.join(lic, need)):
            sys.exit("licence file missing in the package: " + need)

    # launcher exe (cross-compiled with the Linux zig)
    zig = os.path.join(zig_linux, "zig")
    subprocess.check_call([zig, "cc", "-target", "x86_64-windows-gnu", "-municode", "-O2", "-o", os.path.join(pkg, "Project-Friday.exe"),
                           os.path.join(HERE, "launcher_win.c")], env=dict(os.environ, ZIG_GLOBAL_CACHE_DIR=os.path.join(CACHE, "zigcache")))

    pdb = os.path.join(pkg, "Project-Friday.pdb")      # debug symbols of the launcher: not needed
    if os.path.isfile(pdb):
        os.remove(pdb)

    # zip (folder Project-Friday/ inside)
    out = os.path.join(a.out, "Project-Friday-windows-x64.zip")
    if os.path.isfile(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for r, _, fs in os.walk(pkg):
            for f in fs:
                full = os.path.join(r, f)
                z.write(full, os.path.join("Project-Friday", os.path.relpath(full, pkg)))
    shutil.rmtree(pkg)
    print("built", out, "%.0f MB" % (os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()

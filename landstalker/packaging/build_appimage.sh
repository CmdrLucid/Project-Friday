#!/usr/bin/env bash
# Builds Landstalker-<arch>.AppImage on YOUR machine from YOUR ROM.
# Usage: packaging/build_appimage.sh path/to/your.rom
#
# The AppImage holds code generated from the ROM, so build it locally and do
# not upload or share it. The ROM itself is NOT bundled: the app finds it at
# run time (see AppRun).
set -euo pipefail
cd "$(dirname "$0")/.."
ARCH="${ARCH:-x86_64}"
ROM="${1:?usage: packaging/build_appimage.sh path/to/your.rom}"

./build.sh "$ROM"

rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/lib
cp build/landstalker AppDir/usr/bin/
cp packaging/landstalker.desktop AppDir/

# Bundle SDL2 so it runs even where it is missing
SDL="$(ldd build/landstalker | awk '/libSDL2/ {print $3}')"
[ -n "$SDL" ] && cp -L "$SDL" AppDir/usr/lib/

# Simple placeholder icon (no external tools)
python3 - <<'PY'
import struct, zlib
w = h = 256
row = b"\x00" + b"\x20\x40\x90\xff" * w
raw = row * h
def chunk(t, d):
    c = struct.pack(">I", len(d)) + t + d
    return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) \
      + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
open("AppDir/landstalker.png", "wb").write(png)
PY

cat > AppDir/AppRun <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export LD_LIBRARY_PATH="$HERE/usr/lib:${LD_LIBRARY_PATH:-}"

# ROM lookup: argument > $LANDSTALKER_ROM > next to the AppImage > ~/ROMs
ROM="${1:-${LANDSTALKER_ROM:-}}"
if [ -z "$ROM" ]; then
  for dir in "$(dirname "${APPIMAGE:-$0}")" "$HOME/ROMs" "$HOME/Games" "$HOME/Downloads"; do
    for f in "$dir"/[Ll]andstalker*.md "$dir"/[Ll]andstalker*.bin "$dir"/[Ll]andstalker*.gen; do
      [ -f "$f" ] && ROM="$f" && break 2
    done
  done
fi
if [ -z "$ROM" ]; then
  if command -v zenity >/dev/null 2>&1; then
    ROM="$(zenity --file-selection --title='Select your Landstalker ROM')" || exit 1
  elif command -v kdialog >/dev/null 2>&1; then
    ROM="$(kdialog --getopenfilename "$HOME")" || exit 1
  else
    echo "Put your Landstalker ROM next to the AppImage or set LANDSTALKER_ROM." >&2
    exit 1
  fi
fi
[ "${1:-}" = "$ROM" ] && shift
exec "$HERE/usr/bin/landstalker" "$ROM" "$@"
RUN
chmod +x AppDir/AppRun

if [ ! -x appimagetool ]; then
  curl -fsSL -o appimagetool \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  chmod +x appimagetool
fi
ARCH="$ARCH" ./appimagetool --appimage-extract-and-run AppDir "Landstalker-${ARCH}.AppImage"
echo "Built Landstalker-${ARCH}.AppImage"

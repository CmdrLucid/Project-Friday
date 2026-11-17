#!/bin/bash
# gpucmp.sh REC OUTDIR [FRAMES] [BIN] : replay a user recording (~/Project-Friday-Test/aufnahmen/rec_<t>) WINDOWED but hidden (the GPU paths need SDL's GL context) with its options,
# Lighting On, and keep the console in OUTDIR/out.log ('gpult:' / 'gl5:' lines).  Extra env via EXTRA="LANDSTALKER_GL5_TIME=4 LANDSTALKER_GPULT_TIME=1 ...".
# (The CPU-vs-GPU compare modes LANDSTALKER_GPULT=2 / LANDSTALKER_GL5CMP were removed with the CPU light, 2026-11-12.)
# Example: EXTRA="LANDSTALKER_GL5_TIME=4" tools/gpucmp.sh ~/Project-Friday-Test/aufnahmen/rec_20261106_1322 /tmp/g5 ; grep '^gl5:' /tmp/g5/out.log | tail
# Local test aid only (ROM + recordings stay on the Deck).
R=$1; O=$2; F=$3; B=${4:-build/landstalker}; ROM=/home/deck/Documents/NonSteamGames/landstalker/landstalker.md
cd "$(dirname "$0")/.." || exit 1
T=$(basename "$R" | sed 's/^rec_//')
[ -z "$F" ] && F=$(tail -1 "$R.chk" | cut -d' ' -f1)
QS=$(grep -h QSPLAY "$R.cfg" 2>/dev/null | cut -d= -f2)
rm -rf "$O"; mkdir -p "$O/home"; cp ~/Project-Friday-Test/aufnahmen/opts_$T/.landstalker_* "$O/home/" 2>/dev/null; echo 1 > "$O/home/.landstalker_lighting"
cp ~/Project-Friday-Test/aufnahmen/save_$T.srm "$O/s.srm" || exit 1
echo "gpucmp: $R frames $F -> $O ($EXTRA)"
env -i $EXTRA PATH=$PATH HOME=$O/home XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DISPLAY=$DISPLAY WAYLAND_DISPLAY=$WAYLAND_DISPLAY $(grep -h -o 'LANDSTALKER_[A-Z_]*=[^ ]*' "$R.cfg" | grep -v QSPLAY) ${QS:+LANDSTALKER_QSPLAY=$QS} \
  GENRECOMP_INPUTSCRIPT=$R.txt GENRECOMP_CHECKLOG=$O/check.chk LANDSTALKER_SAVE=$O/s.srm LANDSTALKER_HIDDEN=1 LANDSTALKER_NOFOCUSPAUSE=1 SDL_AUDIODRIVER=dummy \
  "$B" --frames $((F + 5)) $ROM > "$O/out.log" 2>&1
echo "gpucmp: done; sync: $(diff <(awk -v L=$F '$1 <= L {print $1,$2,$3,$4}' "$R.chk") <(awk '{print $1,$2,$3,$4}' "$O/check.chk") >/dev/null && echo exact || echo DIFFERS)"

#!/bin/bash
# lightshots.sh REC OUTDIR FRAMES [BIN] : replay a user recording (~/aufnahmen/rec_<t>) headless with its options and save, Lighting On,
# screenshots (scale 2) of the given frames into OUTDIR; extra env via EXTRA="LANDSTALKER_SUN=2 LANDSTALKER_LIGHTING_DBG=5 ...".
# Checkpoints of the run go to OUTDIR/check.chk (compare columns 1-4 with REC.chk: the replay must stay in sync).
# Example: EXTRA="LANDSTALKER_LIGHTING=0" tools/lightshots.sh ~/aufnahmen/rec_20261103_2114 /tmp/off 1300,1900
#          then tools/contactsheet.py --ratio /tmp/off/shot_001900_w358.png /tmp/on/shot_001900_w358.png /tmp/r.png
# Local test aid only (ROM + recordings stay on the Deck).
R=$1; O=$2; F=$3; B=${4:-build/landstalker}; ROM=/home/deck/Documents/NonSteamGames/landstalker/landstalker.md
cd "$(dirname "$0")/.." || exit 1
T=$(basename "$R" | sed 's/^rec_//')
last=$(echo "$F" | tr , '\n' | sort -n | tail -1)
QS=$(grep -h QSPLAY "$R.cfg" 2>/dev/null | cut -d= -f2)
rm -rf "$O"; mkdir -p "$O/home"; cp ~/aufnahmen/opts_$T/.landstalker_* "$O/home/" 2>/dev/null; echo 1 > "$O/home/.landstalker_lighting"
cp ~/aufnahmen/save_$T.srm "$O/s.srm" || exit 1
echo "lightshots: $R frames $F -> $O"
env -i $EXTRA PATH=$PATH HOME=$O/home $(grep -h -o 'LANDSTALKER_[A-Z_]*=[^ ]*' "$R.cfg" | grep -v QSPLAY) ${QS:+LANDSTALKER_QSPLAY=$QS} GENRECOMP_INPUTSCRIPT=$R.txt GENRECOMP_CHECKLOG=$O/check.chk \
  LANDSTALKER_SAVE=$O/s.srm LANDSTALKER_SHOT=$F LANDSTALKER_SHOT_SCALE=2 LANDSTALKER_SHOT_DIR=$O "$B" --headless --frames $((last + 5)) $ROM > "$O/out.log" 2>&1
echo "lightshots: done, $(ls "$O"/shot_* 2>/dev/null | wc -l) shots; sync: $(diff <(awk -v L=$last '$1 <= L {print $1,$2,$3,$4}' "$R.chk") <(awk '{print $1,$2,$3,$4}' "$O/check.chk") >/dev/null && echo exact || echo DIFFERS)"

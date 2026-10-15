#!/bin/bash
# dogscan.sh ROM   -- finds the frame where the church is left (room change in the :5 dumps /tmp/refS), dumps every frame of a window behind it for ref and rec,
# and prints the room timeline and the fastest movers (the dog). Needs build/ from build.sh, $HOME/massan.txt and the /tmp/refS /tmp/recS dumps (--ram-dump :5).
ROM=${1:?usage: dogscan.sh ROM}
cd "$(dirname "$0")/.." || exit 1
F=$(python3 - <<'PY'
import os
def room(p):
    b = open(p, 'rb').read(65536); return (b[0x1204 ^ 1] << 8) | b[0x1205 ^ 1]
d = '/tmp/refS'
r0 = None; out = None
for f in sorted(x for x in os.listdir(d) if x.startswith('ram_')):
    k = int(f[4:10])
    if k < 400: continue
    r = room(os.path.join(d, f))
    if r0 is None: r0 = r
    if r != r0: out = k; break
print(out if out is not None else 0)
PY
)
echo "Raumwechsel (Kirche verlassen) in der Referenz bei Frame: $F"
[ "$F" -gt 0 ] || { echo "kein Raumwechsel gefunden, /tmp/refS vorhanden?"; exit 1; }
LO=$((F > 20 ? F - 20 : 0)); HI=$((F + 400))
rm -rf /tmp/refD /tmp/recD; mkdir -p /tmp/refD /tmp/recD
echo "Fenster $LO-$HI, jeder Frame ..."
GENRECOMP_DUMPRANGE=$LO:$HI GENRECOMP_INPUTSCRIPT=$HOME/massan.txt build/genrecomp_build/genrecomp_ref --headless --frames $((HI + 1)) --ram-dump /tmp/refD:1 "$ROM" > /dev/null 2>&1
GENRECOMP_DUMPRANGE=$LO:$HI GENRECOMP_INPUTSCRIPT=$HOME/massan.txt build/landstalker --headless --frames $((HI + 1)) --ram-dump /tmp/recD:1 "$ROM" > $HOME/recD.log 2>&1
echo "Dumps: $(ls /tmp/refD | wc -l) ref, $(ls /tmp/recD | wc -l) rec"
echo "=== Raum + Spielerposition ==="; python3 tools/timeline.py /tmp/refD /tmp/recD $LO $HI 40 | head -30
echo "=== Schnellste Figuren (Hund?) ==="; python3 tools/movers.py /tmp/refD /tmp/recD $LO $HI
echo "=== Wege der zwei schnellsten Figuren (Referenz | Rekompilat) ==="
for A in $(python3 tools/movers.py /tmp/refD /tmp/recD $LO $HI | awk '$2 ~ /^\$FF/ && ($2 ~ /00$/ || $2 ~ /80$/) {sub(/\$/,"",$2); print $2}' | head -2); do
  echo "--- Figur bei \$$A ---"; python3 tools/entitytrack.py /tmp/refD /tmp/recD $A $LO $HI 40 | cut -c1-120
done

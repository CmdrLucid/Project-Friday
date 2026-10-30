#!/bin/bash
# Landstalker mit Eingabe-Aufnahme (fuer die Funktions-Messung, siehe docs/replays/README.md). Installiert als ~/Landstalker_Aufnahme.sh
# (Vorlage im Repo: landstalker/tools/Landstalker_Aufnahme.sh; v2 2026-10-31).
#   ~/Landstalker_Aufnahme.sh          normal: spielt mit einer Kopie deines echten Spielstands; am Ende wird sie zurueckgeschrieben
#                                      (Speichern / Schnellspeichern waehrend der Aufnahme bleibt erhalten; Sicherung des alten Stands: landstalker.srm.vor_<zeit>)
#   ~/Landstalker_Aufnahme.sh neu      neues Spiel: leerer Spielstand (Intro, Anfang)
# Optional ein Name dahinter, z.B.:  ~/Landstalker_Aufnahme.sh normal laden   (wird Teil des Dateinamens)
# Ergebnis in ~/aufnahmen:  rec_<zeit>_<name>.txt (Tasten), .chk (Pruefzeilen), .cfg (Breitbild / Hoehe / Schnellspeichern-Zeitpunkte), .qs (Schnellspeichern / -laden),
#   save_<zeit>_<name>.srm (Spielstand vom ANFANG der Aufnahme, bleibt unveraendert), save_<zeit>_<name>_ende.srm (Stand am Ende), opts_<zeit>_<name>/ (Optionen beim Start)
# v2: (1) das Spiel schreibt in eine Arbeitskopie, nicht mehr in save_<zeit>.srm (sonst startet die Wiedergabe mit dem Stand vom ENDE, HANDOFF 0a189);
#     (2) Schnellspeichern / -laden wird mit Bildnummer aufgezeichnet (LANDSTALKER_QSLOG) und als LANDSTALKER_QSPLAY in die .cfg geschrieben;
#     (3) die Optionsdateien ~/.landstalker_* beim Start werden nach opts_<zeit>/ kopiert (die Wiedergabe braucht dieselben Optionen);
#     (4) LANDSTALKER_SNDCLOCK=0: Schnellvorlauf veraendert das Spiel nicht mehr (Musik dabei stumm).
ROM=/home/deck/Documents/NonSteamGames/landstalker/landstalker.md
SAVE=/home/deck/Documents/NonSteamGames/landstalker/landstalker.srm
DIR=$HOME/aufnahmen
MODE=${1:-normal}
LABEL=${2:-}
STAMP=$(date +%Y%m%d_%H%M)
[ -n "$LABEL" ] && STAMP=${STAMP}_$LABEL
[ "$MODE" = "neu" ] && STAMP=${STAMP}_neu
WORK="$DIR/save_${STAMP}_ende.srm"

mkdir -p "$DIR" || exit 1
cd /home/deck/ProjectL/landstalker || exit 1

rm -f "$WORK"
if [ "$MODE" = "neu" ]; then
    echo "[Aufnahme] Neues Spiel: leerer Spielstand (dein echter bleibt unberuehrt)"
    rm -f "$DIR/save_$STAMP.srm"
else
    [ -f "$SAVE" ] || { echo "[Aufnahme] FEHLER: kein Spielstand unter $SAVE"; exit 1; }
    cp "$SAVE" "$DIR/save_$STAMP.srm" && cp "$SAVE" "$WORK" || exit 1
    echo "[Aufnahme] Spielstand kopiert: $DIR/save_$STAMP.srm (Anfang, bleibt so)  Arbeitskopie: $WORK"
fi
mkdir -p "$DIR/opts_$STAMP" && for f in "$HOME"/.landstalker_*; do [ -f "$f" ] && cp "$f" "$DIR/opts_$STAMP/"; done
echo "[Aufnahme] Optionen gesichert: $DIR/opts_$STAMP ($(ls "$DIR/opts_$STAMP" | wc -l) Dateien)"
echo "[Aufnahme] Tasten werden aufgezeichnet nach: $DIR/rec_$STAMP.txt"
echo "[Aufnahme] Spiel starten ... normal spielen, am Ende das Spiel schliessen. (Schnellvorlauf geht, die Musik ist dabei stumm.)"

export LANDSTALKER_SAVE="$WORK"
export GENRECOMP_INPUTLOG="$DIR/rec_$STAMP.txt"
export GENRECOMP_CHECKLOG="$DIR/rec_$STAMP.chk"
export LANDSTALKER_QSLOG="$DIR/rec_$STAMP.qs"
export LANDSTALKER_LOCKDISPLAY=1
# Schnellvorlauf: normal laeuft der Sound-Teil dabei nur jedes N-te Bild (Musik in 1x); das veraendert die Spieldurchlaeufe beim Raumwechsel / Laden (das Spiel
# wartet auf den Soundtreiber) und ist nicht wiederholbar (HANDOFF 0a189). In Aufnahmen laeuft der Sound-Teil deshalb jedes Bild mit: Schnellvorlauf ist dann
# exakt wiederholbar, die Musik ist nur waehrend des Vorspulens stumm.
export LANDSTALKER_SNDCLOCK=0
# Breitbild / volle Hoehe beeinflussen das Spielverhalten minimal (Figuren im Rand werden frueher aktiv): fuer die Aufnahme werden die aktuellen Werte
# festgehalten (L2 / R2 aendern sie waehrend der Aufnahme nicht) und in rec_<zeit>.cfg gespeichert, damit die Wiedergabe dieselben benutzt.
if [ -f "$HOME/.landstalker_display" ]; then
    read -r _sc _fi _wi _ta _rest < "$HOME/.landstalker_display"
    export LANDSTALKER_WIDE=${_wi:-0}
    export LANDSTALKER_TALL=${_ta:-0}
fi
echo "LANDSTALKER_WIDE=${LANDSTALKER_WIDE:-0} LANDSTALKER_TALL=${LANDSTALKER_TALL:-0}" > "$DIR/rec_$STAMP.cfg"
_w=$((320 + 2 * ${LANDSTALKER_WIDE:-0}))
echo "[Aufnahme] Breitbild/Hoehe fuer diese Aufnahme festgehalten: $(cat "$DIR/rec_$STAMP.cfg")  = Bildbreite $_w px, volle Hoehe ${LANDSTALKER_TALL:-0}  (L2 / R2 wirken jetzt nicht)"
echo "[Aufnahme] Andere Breite gewuenscht? Spiel beenden, im normalen Spiel mit L2 umschalten (352 / 384 / 416 px), dann die Aufnahme neu starten."
export LANDSTALKER_INTERP_LOG="$HOME/interp.txt"
build/landstalker "$ROM"

# Schnellspeichern / -laden: Zeitpunkte in die .cfg (die Wiedergabe loest sie an derselben Stelle aus)
if [ -s "$DIR/rec_$STAMP.qs" ]; then
    _qs=$(paste -sd, "$DIR/rec_$STAMP.qs")
    echo "LANDSTALKER_QSPLAY=$_qs" >> "$DIR/rec_$STAMP.cfg"
    echo "[Aufnahme] Schnellspeichern / -laden aufgezeichnet: $_qs"
fi

# Fortschritt der Aufnahme (Speichern / Schnellspeichern) in den echten Spielstand zurueckschreiben, vorher Sicherung
if [ "$MODE" != "neu" ] && [ -f "$WORK" ]; then
    if cmp -s "$WORK" "$SAVE"; then
        echo "[Aufnahme] Spielstand unveraendert."
    else
        cp "$SAVE" "$SAVE.vor_$STAMP" && cp "$WORK" "$SAVE" \
            && echo "[Aufnahme] Spielstand uebernommen (Speichern / Schnellspeichern bleibt erhalten). Alter Stand gesichert: $SAVE.vor_$STAMP" \
            || echo "[Aufnahme] FEHLER beim Zurueckschreiben, dein echter Spielstand ist unveraendert."
    fi
fi

echo
echo "[Aufnahme] Fertig. Dateien:"
ls -la "$DIR"/rec_$STAMP.* "$DIR"/save_$STAMP*.srm 2>&1
SIZE=$(stat -c %s "$DIR/rec_$STAMP.txt" 2>/dev/null || echo 0)
if [ "$SIZE" -lt 100 ]; then
    echo "[Aufnahme] ACHTUNG: die Tasten-Datei ist fast leer ($SIZE Bytes), die Aufnahme taugt nichts."
else
    echo "[Aufnahme] Aufnahme sieht gut aus ($SIZE Bytes). Sag Claude den Namen: rec_$STAMP.txt"
fi

#!/bin/bash
# verify_build.sh -- does the build contain all fixes? Run in the landstalker/ folder after build.sh.
# (No timestamp test: unzip -o refreshes the timestamps of the sources. The markers prove which patches went into .deps/genrecomp; the checksum is compared with the value announced in the chat.)
cd "$(dirname "$0")/.." || exit 1
G=.deps/genrecomp
ok=0; bad=0
chk() { # description, file, marker
  if [ -f "$2" ] && grep -q "$3" "$2"; then echo "  [ok]  $1"; ok=$((ok+1)); else echo "  [FEHLT] $1"; bad=$((bad+1)); fi
}
echo "== Korrekturen im gebauten Code =="
chk "Zeitmodell (Block-Zyklen)"                     $G/src/bus.c                         "LANDSTALKER_TIMING"
chk "DMA-Stall auf Blanking-Rate"                   $G/src/bus.c                         "DMA done in write"
chk "Dump am Frameende / Pad am Frame-Wrap"         $G/src/bus.c                         "LANDSTALKER_WRAPINPUT"
chk "Referenz laedt Spielstand"                     $G/tools/ref_runner/main.c           "LANDSTALKER_REFSRAM"
chk "Frame-Statistik (FRAMESTAT)"                  $G/src/platform_sdl.c                "LANDSTALKER_FRAMESTAT"
chk "Anzeige: Skalierung/CRT-Filter (L1/R1)"       $G/src/platform_sdl.c                "LANDSTALKER_DISPLAY"
chk "Breitbild-Experiment (LANDSTALKER_WIDE)"        $G/ext/Genesis-Plus-GX/core/vdp_render.c "LANDSTALKER_WIDE"
chk "Screenshot-Dump (LANDSTALKER_SHOT)"          $G/src/platform_sdl.c                "LANDSTALKER_SHOT"
chk "Ton-Mitschnitt (LANDSTALKER_WAV)"             $G/src/platform_sdl.c                "LANDSTALKER_WAV"
chk "Audio-Puffer (LANDSTALKER_AUDIO_PREFILL)"       $G/src/platform_sdl.c                "LANDSTALKER_AUDIO_PREFILL"
chk "Breitbild per Taste umschaltbar (L2/F3)"       $G/src/platform_sdl.c                "platform_display_cycle_wide"
chk "Volle Hoehe per Taste (R2/F4)"               $G/ext/Genesis-Plus-GX/core/vdp_render.c "lk_tall_track"
chk "Volle Hoehe: Band vorgezeichnet (kein Tearing)" $G/ext/Genesis-Plus-GX/core/vdp_render.c "lk_tall_prerender"
chk "Breitbild: Scroll je Ebene getrennt (kein Uebertrag)" $G/ext/Genesis-Plus-GX/core/vdp_render.c "each 16-bit half"
chk "Koordinaten-Anzeige (R4/F5)"                  $G/src/platform_sdl.c                "platform_display_toggle_coords"
chk "Vollbild ohne Rahmen (L4/F11)"                  $G/src/platform_sdl.c                "platform_display_toggle_fullscreen"
chk "Testhilfe: zu Koordinaten laufen (LANDSTALKER_GOTO)" $G/src/platform_sdl.c                "LANDSTALKER_GOTO"
chk "Optionen-Reiter im Startmenue"                  $G/src/func_table.c                  "lk_menu_install"
chk "Alle Controller gleichzeitig (Dock/Xbox)"       $G/src/input.c                       "LANDSTALKER_MULTIPAD"
chk "Optionen: Rahmen blinkt"                         $G/src/func_table.c                  "lk_opt_blink"
chk "Voll-Hoehe: Nachladen nach Raumwechsel"      $G/src/func_table.c                  "reload at fade-in"
chk "Namen in den Diagnosezeilen (symbols.json)"      $G/src/func_table.c                  "lk_symfmt"
chk "Trap-Daten nie als Code (Schwertschlag)"          $G/tools/recompiler/analyze.py       "inline data words are never code"
chk "Testhilfe: in Raum springen (LANDSTALKER_WARP)" $G/src/func_table.c "LANDSTALKER_WARP"
chk "Inline-Daten nie als Code (Dialog-Freeze)"      $G/tools/recompiler/analyze.py       "LANDSTALKER_CALLDATA_PLAUSIBLE"
chk "Breitbild: NPCs im Rand (Sprite-Culling)"        "$(grep -l "margin entities" src/recomp/*.c 2>/dev/null | head -1)"    "margin entities"
chk "Pruefzeilen fuer Aufnahmen (CHECKLOG)"         $G/src/input.c                       "LANDSTALKER_CHECKLOG"
chk "Aufnahme: Breitbild/Hoehe sperrbar (LOCKDISPLAY)" $G/src/platform_sdl.c                "LANDSTALKER_LOCKDISPLAY"
chk "Namen im generierten C (Name_XXXXXX)"         "$(grep -l "UpdateSprites_0178C8" src/recomp/*.c 2>/dev/null | head -1)"  "UpdateSprites_0178C8"
chk "Gameplay: Schatten unter Nigel"                 $G/ext/Genesis-Plus-GX/core/vdp_render.c "LK_SHADOW"
chk "Gameplay: Quick Items (Anzeige)"               $G/ext/Genesis-Plus-GX/core/vdp_render.c "LK_QUICK v1"
chk "Gameplay: Quick Items (Tasten, Logik)"         $G/src/func_table.c "lk_quick_install"
chk "Titelbild: Project Friday (Anzeige)"            $G/ext/Genesis-Plus-GX/core/vdp_render.c "LK_BRAND v1"
chk "Modell-Overlay (LANDSTALKER_MODEL)"             $G/ext/Genesis-Plus-GX/core/vdp_render.c "LK_MODEL v2"
chk "Eigener Renderer (LANDSTALKER_OWN)"              $G/ext/Genesis-Plus-GX/core/vdp_render.c "LK_OWN v1"
chk "Vorspulen (R2 / Tab)"                           $G/src/platform_sdl.c "LK_FFWD v1"
chk "Schnellspeichern / -laden"                     $G/src/func_table.c "LK_QUICKSAVE v1"
chk "Schwierigkeit (Schaden / Gegner-HP)"           $G/src/func_table.c "LK_DIFF v2"
chk "Tastenbelegung (Pad + Tastatur)"                 $G/src/input.c "LK_KEYS v1"
chk "VDP-Arrays 64 Byte ausgerichtet (clang)"   $G/ext/Genesis-Plus-GX/core/vdp_ctrl.c "LK_ALIGN v1"
chk "Ton: Musik / Effekte getrennte Lautstaerke"   $G/ext/Genesis-Plus-GX/core/sound/sound.c "LK_SNDSEP2"
chk "Sprach-Blips abschaltbar"                     "$(grep -l "speech blips option" src/recomp/*.c 2>/dev/null | head -1)" "speech blips option"
chk "Absolute short Adressen vorzeichenerweitert"   $G/tools/recompiler/generate.py      "_abs_val"
chk "Befehlskorrekturen (ASL, CMPM, MOVEM, ...)"    $G/tools/recompiler/generate.py      "LANDSTALKER_INSNFIX"
chk "ASL-Makro"                                     $G/include/genrecomp/m68k.h          "M68K_ASL8"
chk "DIVS-Absturzschutz"                            $G/include/genrecomp/m68k.h          "LANDSTALKER_DIVS"
chk "FM-Puffer-Begrenzung"                          $G/ext/Genesis-Plus-GX/core/sound/sound.c "LANDSTALKER_FMCLAMP"
if [ -f build/landstalker ]; then echo "  [ok]  build/landstalker vorhanden ($(date -r build/landstalker '+%d.%m. %H:%M'))"; ok=$((ok+1))
else echo "  [FEHLT] build/landstalker existiert nicht"; bad=$((bad+1)); fi
echo
echo "Pruefsumme der Quellen (build.sh + tools/patch_*.py): $(cat build.sh tools/patch_*.py | sha1sum | cut -c1-10)"
echo "Ergebnis: $ok ok, $bad fehlend"
[ "$bad" -eq 0 ] && echo "=> Stand ist aktuell" || echo "=> NICHT aktuell: ./build.sh ausfuehren (bei fehlenden Markern: vorher ZIP neu laden mit unzip -o)"

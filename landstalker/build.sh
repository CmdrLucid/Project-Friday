#!/bin/bash
# Build the recompiled Landstalker from a ROM you own.
# Usage: ./build.sh path/to/your.rom   (.bin / .md; de-interleave .smd first)
set -euo pipefail
cd "$(dirname "$0")"

ROM="${1:?usage: ./build.sh path/to/your.rom}"
[ -f "$ROM" ] || { echo "ROM not found: $ROM" >&2; exit 1; }

mkdir -p .deps
if [ ! -d .deps/genrecomp ]; then
    git clone --recursive https://github.com/sp00nznet/genrecomp .deps/genrecomp
fi
# The GPGX core is a submodule: make sure it is really checked out (an interrupted/non-recursive clone leaves it empty)
git -C .deps/genrecomp submodule update --init --recursive
[ -f .deps/genrecomp/ext/Genesis-Plus-GX/core/vdp_render.c ] || { echo "ERROR: GPGX submodule missing in .deps/genrecomp (rm -rf .deps and rebuild)" >&2; exit 1; }
# Always patch a pristine genrecomp: every patch skips itself when its marker is already present, so an
# UPDATED patch would silently never be applied to the copy left in .deps by an earlier build.
git -C .deps/genrecomp checkout -q -- . 
git -C .deps/genrecomp submodule foreach --recursive --quiet 'git checkout -q -- .' || true

# Landstalker has more functions than genrecomp's default 4096-slot table
sed -i 's/#define FUNC_TABLE_SIZE  4096/#define FUNC_TABLE_SIZE  16384/' .deps/genrecomp/src/func_table.c

# genrecomp's window texture swaps red/blue; the chip renders XRGB
sed -i 's/SDL_PIXELFORMAT_RGBX8888/SDL_PIXELFORMAT_ARGB8888/' .deps/genrecomp/src/platform_sdl.c

# GENRECOMP_ASCII="300,1000" prints those frames as a letter grid (both the
# reference runner and the recompiled build go through platform_present_frame)
python3 - <<'PY'
p = ".deps/genrecomp/src/platform_sdl.c"
s = open(p).read()
if "LANDSTALKER_ASCII" not in s:
    m = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert m in s, "platform_sdl.c layout changed"
    block = open("tools/ascii_patch.c").read()
    s = s.replace(m, m + block, 1)
    open(p, "w").write(s)
PY

python3 -c "import capstone" 2>/dev/null || pip install capstone

# Game controller input + GENRECOMP_AUDIO_DEBUG probe
python3 tools/patch_runtime.py .deps/genrecomp
# VDP arrays aligned to 64 bytes: clang (zig cc) assumes 16 and crashed in vectorised code (tools/patch_align.py)
python3 tools/patch_align.py .deps/genrecomp
# Record (GENRECOMP_INPUTLOG) / replay (GENRECOMP_INPUTSCRIPT) controller input
python3 tools/patch_inputlog.py .deps/genrecomp
# checkpoint lines every 120 frames (GENRECOMP_CHECKLOG=file) to find where a replay leaves the live recording, see tools/patch_checklog.py
python3 tools/patch_checklog.py .deps/genrecomp

# Draw each scanline as it passes and fire HInt (raster effects, text boxes)
python3 tools/patch_perline.py .deps/genrecomp
# Latch screen height/width from the VDP registers each frame (was stuck at 192 lines)
python3 tools/patch_viewport.py .deps/genrecomp
python3 tools/patch_linelog.py .deps/genrecomp
python3 tools/patch_watchdog.py .deps/genrecomp
python3 tools/patch_watchfold.py .deps/genrecomp
python3 tools/patch_guard.py .deps/genrecomp

# Fix: follow jmp stubs the game writes into RAM (JmpInstr1 = $FF1850)
python3 tools/patch_ramstub.py .deps/genrecomp

# Fix: RTS that returns to an outer caller (dropped return address) unwinds C frames
python3 tools/patch_unwind.py .deps/genrecomp
python3 tools/patch_calltrace.py .deps/genrecomp
python3 tools/patch_interp.py .deps/genrecomp
python3 tools/patch_fmclamp.py .deps/genrecomp
python3 tools/patch_irqdelay.py .deps/genrecomp
python3 tools/patch_sram.py .deps/genrecomp

# Fix: call targets the analyzer never decoded were silently dropped (e.g. $002458)
python3 tools/patch_gencross.py .deps/genrecomp/tools/recompiler

# Fix: trap handlers that read inline data words (sound / text IDs)
python3 tools/patch_trap.py .deps/genrecomp/tools/recompiler
python3 tools/patch_calldata.py .deps/genrecomp/tools/recompiler

# Fix: memory-destination RMW ops with (An)+ / -(An) never updated An
python3 tools/patch_generate.py .deps/genrecomp/tools/recompiler/generate.py

# Fix: absolute short addresses ($XXXX.w) are sign-extended on the 68000 (found by tools/insnfuzz)
python3 tools/patch_absw.py .deps/genrecomp/tools/recompiler/generate.py

# Fixes found by tools/insnfuzz: cmpm/bcd temporaries, ASL overflow flag, ROX carry, capstone roxr.b, movem addressing modes
python3 tools/patch_insnfix.py .deps/genrecomp

# 68000 instruction timing (per-block bus_add_cycles from the Musashi opcode table, data-dependent mul/div, DRAM refresh);
# must run after the other bus.c / generate.py patches. LANDSTALKER_OLDTIMING=1 at run time = old model.
python3 tools/patch_timing.py .deps/genrecomp
# --ram-dump of the recompiled build at the END of each frame (like genrecomp_ref), so ref-vs-rec dumps are comparable
python3 tools/patch_dumpwrap.py .deps/genrecomp
# genrecomp_ref loads the same battery save (read-only) so replays from a save compare equal
python3 tools/patch_refsram.py .deps/genrecomp
# frame pacing diagnostics: LANDSTALKER_FRAMESTAT=1 (per-second wall-clock frame statistics), LANDSTALKER_NOSYNC=1 (vsync only, A/B)
python3 tools/patch_framestat.py .deps/genrecomp
# display pipeline: scaling modes (pad L1 / F1), CRT filter (pad R1 / F2), on-screen hint, settings in ~/.landstalker_display
python3 tools/patch_display.py .deps/genrecomp
# widescreen experiment: LANDSTALKER_WIDE=16|32|48 renders 352|384|416 px wide pictures (default 0 = unchanged), see tools/patch_wide.py
python3 tools/patch_wide.py .deps/genrecomp
# screenshot dump: LANDSTALKER_SHOT=frame,frame,.. [LANDSTALKER_SHOT_DIR, LANDSTALKER_SHOT_SCALE] writes PNGs of the final picture (tools/patch_shot.py)
python3 tools/patch_shot.py .deps/genrecomp
# full-height picture: map in the bottom band (pad R2 / F4, LANDSTALKER_TALL=0|1), see tools/patch_tall.py (needs patch_wide + patch_shot)
python3 tools/patch_tall.py .deps/genrecomp
# recordings: LANDSTALKER_LOCKDISPLAY=1 freezes widescreen width / full height (needs patch_wide + patch_tall), see tools/patch_lockdisplay.py
python3 tools/patch_lockdisplay.py .deps/genrecomp
# coordinate debug overlay (pad R4 / F5, LANDSTALKER_COORDS=1, LANDSTALKER_COORDS_LOG=N), see tools/patch_coords.py
python3 tools/patch_coords.py .deps/genrecomp
# borderless windowed fullscreen (pad L4 / F11 / Alt+Enter, saved in ~/.landstalker_fullscreen), see tools/patch_fullscreen.py
python3 tools/patch_fullscreen.py .deps/genrecomp
# test aid: LANDSTALKER_GOTO="603:37.02,36.02" walks Nigel to coordinates (headless tests), see tools/patch_goto.py
python3 tools/patch_goto.py .deps/genrecomp
# Options tab in the Start menu (third choice next to Use / Equip, built from the game's own text/tile routines), see tools/patch_options.py
python3 tools/patch_options.py .deps/genrecomp
# Gameplay option 'Shadow': ground shadow under Nigel / airborne entities, picture only (tools/patch_shadow.py; needs patch_options.py first)
python3 tools/patch_shadow.py .deps/genrecomp
# Gameplay option 'Quick Items': pad Y / B use assigned items, cells in the HUD bar (tools/patch_quick.py; needs patch_options.py and patch_shadow.py first)
python3 tools/patch_quick.py .deps/genrecomp
# Project-Friday branding on the title screen (tools/patch_overlay.py; needs patch_quick.py first)
python3 tools/patch_overlay.py .deps/genrecomp
# Fast forward on R2 / Tab (hold) + Gameplay option; frees L1 / R1 / L2 / R2 from display functions (tools/patch_ffwd.py; needs the display / options patches first)
python3 tools/patch_ffwd.py .deps/genrecomp
# Quick save / quick load anywhere (hidden fifth slot, the game's own save routines; tools/patch_quicksave.py; needs patch_ffwd.py first)
python3 tools/patch_quicksave.py .deps/genrecomp
# Quick Equip: hold R2 (binding 'Quick Equip') + direction changes sword / armour / boots / ring (tools/patch_equip.py; needs patch_quick.py and patch_quicksave.py first)
python3 tools/patch_equip.py .deps/genrecomp
# Difficulty options: damage taken / enemy HP (tools/patch_difficulty.py; needs patch_options.py and patch_quicksave.py first)
python3 tools/patch_difficulty.py .deps/genrecomp
# Optional fix 'Ride Objects': Nigel is carried by an object standing on a moving platform (tools/patch_carry.py; needs patch_difficulty.py first)
python3 tools/patch_carry.py .deps/genrecomp
# Optional 'Gaia Effect' (Live): the falling rocks of the Gaia statue / sword no longer freeze the game (tools/patch_gaia.py; needs patch_carry.py first)
python3 tools/patch_gaia.py .deps/genrecomp
# Optional 'Item Info': description of the item under the cursor in the Start menu (tools/patch_iteminfo.py; needs patch_options.py and patch_carry.py first)
python3 tools/patch_iteminfo.py .deps/genrecomp
# Optional 'Buy Quantity': choose how many consumables to buy at once in shops (tools/patch_buyqty.py; needs patch_iteminfo.py first)
python3 tools/patch_buyqty.py .deps/genrecomp
# Optional 'Map Behind Text': the map shows through the transparent pixels of the dialogue window instead of black (tools/patch_tbox.py; needs patch_wide.py)
python3 tools/patch_tbox.py .deps/genrecomp
# Key bindings for pad + keyboard (tools/patch_keys.py; replaces the fixed button / key lines of input.c, needs all input patches before it)
python3 tools/patch_keys.py .deps/genrecomp
# Controller polling on its own thread (Steam Deck HIDAPI stall every 3.4 s = micro stutter, tools/patch_padthread.py)
python3 tools/patch_padthread.py .deps/genrecomp
# Model view (block grid, entity boxes; R3 / F7 / LANDSTALKER_MODEL=1, tools/patch_model.py; needs patch_overlay.py and patch_keys.py first)
python3 tools/patch_model.py .deps/genrecomp
# Own text box tiles: mirror of the game's text buffer built by an own glyph printer (tools/patch_owntext.py; needs patch_buyqty.py first)
python3 tools/patch_owntext.py .deps/genrecomp
# Own renderer: RAM snapshot right after the VBlank handler = what the VDP shows next (tools/patch_ownvb.py; needs patch_owntext.py first)
python3 tools/patch_ownvb.py .deps/genrecomp
# Own renderer stage 2 groundwork: origin (ROM block + tile index) of tile graphics by content hash (tools/patch_gfxorg.py; needs patch_ownvb.py first)
python3 tools/patch_gfxorg.py .deps/genrecomp
# Own renderer, compare mode (LANDSTALKER_OWN=1 / 2, tools/patch_own.py; needs patch_shadow.py first)
python3 tools/patch_own.py .deps/genrecomp
# Stage 3 groundwork: ROM room decoder (C port of romroom.py) + per frame model, read only, check with LANDSTALKER_SMODEL_CHECK=1 (tools/patch_roommodel.py; needs patch_own.py first)
python3 tools/patch_roommodel.py .deps/genrecomp
# HD graphics, display side: HD picture from the compositor's n x n blocks, optional and Off by default (tools/patch_hd.py; needs patch_shot.py and patch_own.py first)
python3 tools/patch_hd.py .deps/genrecomp
# 3D room: Options > Video > 3D Room, the room as a 3D scene, camera on the right stick (tools/patch_room3d.py + tools/room3d_game.c; needs patch_hd.py first)
python3 tools/patch_room3d.py .deps/genrecomp
# test aid: LANDSTALKER_WARP="610:12.08,20.04" puts Nigel into a room at a spot (headless tests), see tools/patch_warp.py
python3 tools/patch_warp.py .deps/genrecomp
# audio capture: LANDSTALKER_WAV=file.wav (recompiled build and genrecomp_ref), compare with tools/wavcmp.py (tools/patch_wav.py)
python3 tools/patch_wav.py .deps/genrecomp
# audio buffer: ~3 frames of prefill + overflow valve against crackle (tools/patch_audiobuf.py, LANDSTALKER_AUDIO_PREFILL / _MAXQ)
python3 tools/patch_audiobuf.py .deps/genrecomp
# focus pause: no focus / minimized = game and audio paused (issue #9, tools/patch_focuspause.py, LANDSTALKER_NOFOCUSPAUSE=1 = off)
python3 tools/patch_focuspause.py .deps/genrecomp
# region: force NTSC / 60 Hz for every ROM (a Europe ROM was detected as PAL = 20 % too fast; tools/patch_region.py, LANDSTALKER_PAL=1 = auto-detect)
python3 tools/patch_region.py .deps/genrecomp
# sound diagnostics + separate music / effect volumes (tools/patch_sndsep.py, LANDSTALKER_SNDLOG / LANDSTALKER_ZRAMDUMP)
python3 tools/patch_sndsep.py .deps/genrecomp
# diagnostics: LANDSTALKER_VDPLOG=1 lists which game function writes which tile columns of the scroll planes (widescreen work)
python3 tools/patch_vdplog.py .deps/genrecomp
# names (from docs/symbols.json) in the console diagnostics: call stack, interp:, no function, RTS to, CALLTRACE (tools/patch_symnames.py; LANDSTALKER_NONAMES=1 = off)
python3 tools/patch_symnames.py .deps/genrecomp

# Expand seeds that land in a bra.w jump table into the whole table
python3 tools/expand_seeds.py "$ROM" recomp.json

# Seed every script entry point (cutscene + character script tables) so the interpreter fallback is not needed for scripts
python3 tools/script_tables.py "$ROM" recomp.json

# Human-readable names for ROM addresses (local file docs/symbols_auto.json, not committed); failure is not fatal
python3 tools/symbolize.py "$ROM" || echo "symbolize: skipped"

# 1. 68000 -> C (output stays local; it is derived from your ROM)
python3 tools/seed_missing.py "$ROM" recomp.json .deps/genrecomp/tools/recompiler/generate.py src/recomp

# 1b. widescreen: entities in the margins get sprite entries (no pop-in), patches the GENERATED sub_004144, see tools/patch_sprcull.py
python3 tools/patch_sprcull.py src/recomp

# 1b2. speech blips on/off option: skips the talk-sound trap in $023104 (tools/patch_talk.py; must run before rename_generated)
python3 tools/patch_talk.py src/recomp

# 1c. readable names in the generated C: sub_XXXXXX -> Name_XXXXXX from docs/symbols.json (address stays in the name; must run AFTER patch_sprcull; LANDSTALKER_NONAMES_C=1 = off), see tools/rename_generated.py
python3 tools/rename_generated.py src/recomp

# 2. Compile
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"

# generated functions cut off in the middle of an instruction (bogus function starts): informational
python3 tools/check_splits.py "$ROM" src/recomp 2>&1 | head -12 || true

echo
echo "Built: build/landstalker"
echo "Run:   build/landstalker \"$ROM\""
echo "Smoke: build/landstalker --headless --frames 600 \"$ROM\""

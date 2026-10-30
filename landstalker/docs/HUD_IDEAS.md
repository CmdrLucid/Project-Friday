# Modern HUD (option 'no HUD bar' + floating panels) — DESIGN AGREED, NOT BUILT

**Written 2026-10-30, Deck session (Opus 5.5 lead + Sonnet 5.5 agents). Based on `dev` commit `9d97acb` (experiment `LK_NOHUD v0` = ef46932).**
Nothing here is in the game yet except the env-only experiment `LANDSTALKER_NOHUD=1`. Re-check against the code of the day before acting.

## Why it works (verified headless, HANDOFF 0a186)
- Via the VDP the game maintains plane rows only from line 24 (lines 0..23 = window plane HUD, FORMATS 'Map screen layout') -> garbage there.
- The OWN RENDERER draws the whole room from ROM data (`lk_o_pa / lk_o_pb`, camera v0 + line), so lines 0..23 simply continue the map; figures are not culled at the top (`CheckEntityOnScreen $004144` accepts sprite Y -64..416). Screenshots `~/Mockups/nohud/`: no garbage, NPCs / enemies in the band, band scrolls and fades with the map.

## Design the user chose (mock-ups `~/Mockups/hud_A_entwurf1..5.png`, script `~/.landstalker_remake/hud/mk5.py`, NOT in git)
User decisions in order: variant A (corners) -> 'Herzen gestuft' (the game's own big / medium / small heart tiers, not a number) -> 'mit Boxen' (readability) -> 'Gold oben im Eck, darunter die Quick Items' -> 'Gold und Quick Items zu nah' -> 'Buttons bei den Quick Items, oder Keys wenn Keyboard-Input (aus den Keybindings)' -> 'Buttons grau und weiss, ruhiger' (entwurf 5 = the current state). The user said 'ja besser' to entwurf 4/5.
- Two floating panels, both the same height, in the style of the original bar: fill = HUD purple `$442288` (68,34,136) at ~80 % opacity, outer border white `$EEEEEE`, inner line grey `$666666`, small rounded corners.
- LEFT panel (top-left): row 1 = the original tiered hearts exactly as the bar draws them (big heart, medium hearts, 2 x 5 small hearts incl. the white outline + 1 px black shadow on the right / bottom -> crop must include it); row 2 = original sword icon + sword charge gauge 50 px x 5 rows in the ORIGINAL colours (rows `$AA0000 / $EE66AA / $EEEEEE / $EE66AA / $AA0000`, empty = `$000000`, 1 px per charge unit, `g_SwordCharge_0 $FF120A` byte 0..50). No '64/78' number (could go small next to the gauge if the user asks). The panel grows with the hearts (78 max health ~ 95 px wide).
- RIGHT panel (top-right): row 1 = gold in the game's own font ('1932G', right-aligned in the corner); thin grey separator line + a few px gap; row 2 = the two Quick Item cells (16x16 icon + quantity, as `lk_quick_hud` draws them), each with an input symbol LEFT of the icon: on pad a round grey button with a white letter (Y / B, no Xbox colours), on keyboard a light key cap with the letter from the key bindings (`lk_keys_step`, LESSONS 46) — switch by the last input device used.
- The EkeEke bag + count of the old bar is dropped (Quick Items replace it; note: in today's bar with Quick Items ON the bag and the EkeEke cell both show the same count).

## Data (all named in symbols.json)
`Player_CurrentHealth $FF543E`, `Player_MaxHealth $FF547E` (words, 1/256 hearts, HUD shows (v + $100) >> 8), `g_Gold $FF120E` (capped 9999), `g_SwordCharge_0 $FF120A`, equipped `$FF114E..$FF1151`, Quick Item slots from `~/.landstalker_quick` (+ icons `~/.landstalker_quick_icons`). `lk_o_hudbuild` (patch_own.py) already rebuilds the HUD tilemap from these (port of hud.asm) -> the heart tier tiles can be taken from there instead of cropping screenshots.

## Open for the real option (ask the user before building; one step at a time)
1. Options > Video row (e.g. 'HUD: Original / Modern'), saved option file, env override; Off = bit exact (timebench IDENTICAL).
2. Frames the own path does not draw (Start menu, game over, effects, intro rooms 139..143 have no HUD) must not flash the old bar (decide: keep the old bar there, or hide it).
3. Quick Items HUD (`lk_quick_hud`) moves into the right panel; Quick Equip / Item Info overlays checked.
4. Black void above the room edge (no bar any more): leave black, or fill (backdrop / neighbour room like Seamless Doors).
5. Nigel at the very top edge, 3D room mode (`lk_r3d_on`), HD tile packs, widescreen widths, CRT / De-Dither: test.
6. Map Behind Text and the sprite mask `lk_o_smk` keep working (text box unchanged).

## Notes for step 1 (2026-10-30 later, Deck, Opus 5.5; dev after Native Pace default On)
- Plan agreed with the user: 'Nativ-Tempo standardmaessig an, dann HUD' = start building. Proposed step 1: option row (Video, 'HUD: Original / Modern', file `~/.landstalker_hud`, env `LANDSTALKER_NOHUD` keeps working as override) + NOHUD band + LEFT panel (hearts, sword + gauge) + RIGHT panel with the gold only; the Quick Item cells move into the right panel in step 2.
- Proposed defaults for open points 2 / 4 (confirm with the user): frames the own path does not draw keep the OLD bar (no change = safe); the void above a room edge stays black.
- The original bar ALREADY contains the sword icon AND the charge gauge (bar tiles, rows 11..15, ~50 px): crop it, no own gauge drawing needed (the mock-up drew its own because it started from a Quick Items screenshot).
- Bar geometry (headless shot, `rec_20261030_0310` with save_0319, frame 1500, WIDE 19, no Quick Items): white border line 5, grey 6, interior 7..20, white 21, grey 22. At WIDE > 0 the bar is WIDER than 320 px (left cap + sword pommel lie left of plane x 0, i.e. in the margin): take the panel crops by TILE COLUMN of the window tilemap (`lk_o_hw[r][col]`, built by `lk_o_hudbuild` from hud.asm data) instead of by pixel x; crops from screenshots with Quick Items ON are shifted (lk_quick_hud removes columns).
- Hook point: the own renderer's per-pixel loop in `patch_own.py` (`col` = final RGB per pixel, after the window pixel choice); window pixels come from `lk_o_win(line, x, hint)` -> palette index -> `lk_o_pix` / `lk_o_fxpix` (so the panel content fades with the picture). Panels span lines ~3..39, i.e. below line 23: read the bar line (line - offset) via `lk_o_win` for the crop rows.
- Pillow on the Deck: `~/.landstalker_trailer/venv/bin/python` (system python3 has no PIL).
- USER 2026-10-30 (later): open point 2 = HIDE the old bar in frames the own path does not draw (Start menu fades, black room-load frames, effects the game draws), or better bring those frames into the own code; open point 4 = the void above a room stays black.
- USER 2026-10-30 (later): prefers NO boxes ('ohne gefaellt mir besser') but it was partly hard to read; quick buttons closer to the item -> Wind Waker HD style (user screenshot): the item lies ON a round button disc, the input letter as a small badge at the disc's edge; gold moves to the BOTTOM RIGHT; sword a bit further below the hearts. Mock-up `~/Mockups/hud_A_entwurf7.png` (script `~/.landstalker_remake/hud/mk7.py`, not in git): no boxes, 1 px dark outline (alpha ~190) around hearts / sword + gauge / gold, light translucent discs (fill (190,190,205) alpha 110, white rim, dark outer ring), discs top right, gold bottom right. Waiting for the user's verdict.

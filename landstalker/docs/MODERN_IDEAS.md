# Ideas: a modern Landstalker (THEORY ONLY, nothing built)

**Written 2026-10-30 late, Deck session (Opus 5.5), after the sprint work. Based on `dev` commit `7eabb4e`.**
User question: 'was koennten wir noch umsetzen, um Landstalker zu einem modernen Spielerlebnis zu machen?'. Proposed list (below) ->
**user picked (2026-10-30): (A) smooth sub-pixel scrolling (so a slower sprint, 1.5 x, no longer wobbles: 2 x is still too fast for him)
and (B) a map + 'where to go next' via talks with Friday, both OPTIONAL.**  Rules as always: every feature is an option, Off = the original
bit exact (`tools/timebench.py --compare` IDENTICAL), picture-only features change nothing in the game logic.

## (A) Smooth scrolling / 1.5 x sprint without wobble  (FIRST, fresh session)
What we measured (SPRINT_IDEAS, entries of 2026-10-30 late): in the 2:1 view the picture moves by the full step horizontally and by HALF the
step vertically (`VScrollIncrease $002452`: one line every second unit, `g_VScrollPhase $FF1180`). Odd steps (3 = 1.5 x) give 1 / 2 px vertical
alternation of the ROOM while Nigel stays at the same screen spot (the game's sprite table and our renderer agree exactly), so the ground wobbles;
4 / 2 alternation is uneven on both axes. The game logic must stay integer (positions, collision).
Idea: the OWN RENDERER draws the room planes at the IDEAL (fractional) camera position instead of the rounded VScroll:
 * keep the game state as it is; in the renderer compute the exact camera `cam_y_exact = (camera units) / 2` (half pixels) and draw plane A / B
   with that half pixel offset; the figures keep their own (integer) positions relative to the exact camera (Nigel then stays still and the ground
   moves 1.5 px every frame);
 * a half pixel needs output resolution: draw the map layers at 2x vertically (the HD path already has a scale: `lk_hd_n`, `LANDSTALKER_HD_SCALE`,
   `lk_hd_put`; on the Deck the 224 lines are shown on 800, so half a source line is visible) or shift the final upscaled picture by half a line
   per layer in `display_core.c`;
 * first prototype: only the vertical half step while Sprint (step 3) runs; check with a recording that the room scrolls evenly (1.5 px per frame)
   and that figures (NPCs too) do not wobble against the ground; then the sprint step back to 3 behind the option.
Open: text box / HUD lines must not move; the seam / room-change code (`lk_seam_step`) uses the integer camera; 3D room / HD packs.
**2026-10-30 night: PROTOTYPE BUILT, but without the HD path** (it is off for the user: no tile pack): a quarter line blend of the world pixels on the 1x picture instead of a real half line shift (works with every filter). Details HANDOFF 0a203, `tools/patch_subpix.py`. User check: 'passt alles' -> options row Quality of Life > Smooth Scrolling, default On (HANDOFF 0a204). (A) DONE.

## (B) Map + 'where to go next' (Friday)  (after A)
 * Map: an overview of visited rooms / regions (room ids and connections: `docs/ROOMS.md`, landstalker-lib import, INDEX section 6); visited set
   from the game's own `SetRoomVisited` flags (LoadRoomPath, FORMATS line about it); shown as an own screen (button or Start menu tab like Options).
 * Where to go next IN THE GAME (user): Friday tells it in a short dialogue when asked (a binding 'Ask Friday' or a Start menu entry): a table
   'story flag state -> hint text' written by us (`docs/FLAGS.md` has the flags), shown with the game's text box engine (`docs/TEXT_LAYER.md`,
   own UI text in `lang/*.json`), German + English. Never copy game dialogue; our own short hints.
 * Both optional (Quality of Life rows), default to be decided by the user.

## Backlog (proposed, not chosen yet)
1. Jump helper: landing marker / platform top outlines (height map data; the model view `patch_model.py` already draws cells).
2. Controls that match the 2:1 view: stick direction = screen direction (the game only moves along the world axes; d-pad up depends on facing).
3. Rewind a few seconds (quick save technique, ring buffer of states).
4. Text speed / instant text, skip cutscenes.
5. Collection overview (chests, Life Stocks per region).
6. Boss Rush (`BOSS_RUSH_IDEAS.md`).
Rejected earlier: room-name popup, rumble (for now).

## (A2) Sharp smooth scrolling (user 2026-10-31: 'brauchen wir die Unschärfe?' -> '1. später umsetzen'; rests on dev after 191e2f1)
The blend (LK_SUBPIX v3, weight 5/16) is soft while sprinting. Sharp variant: the Deck shows ~3.5 screen lines per game line, so a half game line is ~1.8 real lines: draw the WORLD layer shifted by the fraction at the output scale (nearest, no mixing) and Nigel / figures / HUD / text box unshifted on top. Needs: the compositor to hand world and overlay (with a mask) separately to the display path, the shift applied before / inside the display filters (CRT, de-dither run on the output picture), 1x windows fall back to the blend. Direction / amount: the v3 rule (scroll steps) gives which frames are half a line behind.
**2026-10-31 evening: BUILT (`LK_SSHARP v1`, tools/patch_subpix.py, HANDOFF 0a207).** Simpler than separate layers: the existing per-pixel world mask (`lk_ss_w` + 'nobody drew over it') goes to the CPU filters, which take a world pixel's sampling (rows, beam / scanline weight) from the output row y +- k (k = round(1/4 line * output rows / 224), 1 px on the Deck) when both rows are world there. Headless 1.43 / 1.57 lines per frame, sharp. User 2026-10-31: 'passt. scharf ersetzt sie ganz' (no Soft / Sharp choice; the blend is only the fallback where the shift cannot run). (A2) DONE.

## (B) status 2026-10-31
Friday hints DONE (Select, `tools/patch_friday.py`, `lang/friday_hints.json`, `docs/FRIDAY_HINTS.md`); the user reviews the texts. The map part is still open.


## (C) Modern effects (user 2026-11-05 night: 'was koennen wir mit Effekten noch tun, um das Spiel moderner aussehen zu lassen'; rests on dev cb5acc3, Lighting v8)
Picture only, every effect switchable, Off = original. Proposed list (user's picks marked CHOSEN):
1. Cloud shadows drifting over outdoor maps (cheap) - 'ggf.' (maybe, after the others).
2. CHOSEN: ambient particles per area: leaves on routes, fireflies in shaded forest spots, embers over lava / torches, water drips in caves (dust in light shafts exists).
3. CHOSEN: water: reflections of Nigel / enemies in rivers and ponds, glints, rings when wading.
4. CHOSEN: heat haze over lava and big fires.
5. Hit feedback (sparks, white flash, light shake) - not chosen.
6. CHOSEN: enemies dissolve into particles when defeated.
7. Dust puffs (sprint / landing), splashes - not chosen.
8. Item / magic effects (pickup sparkle, chest light, EkeEke aura, church save glow) - not chosen.
9. Nigel's silhouette behind walls - not chosen.
Order agreed: 2 -> 6 -> 4 -> 3 -> (1). Each one first as a preview video for the user.
- 2026-11-05 night, after the first preview (dev 5874320): leaves REMOVED (user); fireflies kept in the code but OFF until a future DAY / NIGHT CYCLE (user: 'heben wir uns auf fuer den Tag-Nacht-Zyklus, die passen gut in die Nacht'; `LANDSTALKER_AMBIENT_FORCE=2` shows them); drops only on walkable floor. New idea noted: day / night cycle (tint, fireflies at night, lit windows?) - not planned yet.
2026-11-05 night (dev 0b91956): Particles (id 49) and Enemy Dissolve (id 50, tools/patch_dissolve.py) BUILT; shafts lengthened; next: heat haze.
2026-11-06 (dev de1396e): Heat Haze (id 51, tools/patch_haze.py), Water Reflections (id 52, tools/patch_water.py; texture kept, original blue, reflection from the feet; glints / wading rings dropped) and Cloud Shadows (id 53, tools/patch_clouds.py) BUILT. List (C) done except item 5/7/8/9 (not chosen). Open idea: day / night cycle (fireflies ready).
2026-11-06 later (dev d80b624): DAY / NIGHT CYCLE built (Lighting, option id 54; time-lapse L5 + R5). Ideas on top: lit windows at night, indoor brightness by time of day, day length in the menu.

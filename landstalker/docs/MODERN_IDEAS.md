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
**2026-10-31 evening: BUILT (`LK_SSHARP v1`, tools/patch_subpix.py, HANDOFF 0a207).** Simpler than separate layers: the existing per-pixel world mask (`lk_ss_w` + 'nobody drew over it') goes to the CPU filters, which take a world pixel's sampling (rows, beam / scanline weight) from the output row y +- k (k = round(1/4 line * output rows / 224), 1 px on the Deck) when both rows are world there. Headless 1.43 / 1.57 lines per frame, sharp. Waiting for the user's eyes.

## (B) status 2026-10-31
Friday hints DONE (Select, `tools/patch_friday.py`, `lang/friday_hints.json`, `docs/FRIDAY_HINTS.md`); the user reviews the texts. The map part is still open.


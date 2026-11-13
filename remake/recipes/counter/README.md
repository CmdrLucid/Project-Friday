# Shop counter (Mercator special shop 695 / 696 / 697 / 719 / 720) - remake model, since 2026-11-12

Recipe only. `counter.py OUT.obj x0 x1 y0 y1 [walls] [cloth x0 x1 y0 y1] [--light]`: plank top 13.6 .. 16 with rounded edges, core 0.8 in,
vertical boards (pitch 8, 0.5 proud) on every side not at a wall, a small CLOTH on the island's top (22 x 22 at the back end, measured; first
read as a glass display, user: 'da liegt nur quasi ein Deckchen'). Island: x 416..448 y 432..528 cloth 420..442 x 444..466; wall counter
x 432..528 y 368..384, wall 'n'. Clay preview (user 'ja'): ~/.landstalker_remake/assets/counter/counter_v2_clay.png (local).

NOT IN THE LIGHT (2026-11-12): the game's collision box (16 high) already sits on the drawing, and every detail of the model is below a pixel
(cloth 0.1, board relief 0.5, top overhang 0.3, edge radius 0.8): in the GPU light they gave dotted dark lines (cloth rim, bottom of the front,
the rounded top edge as stair steps), even the `--light` variant (flush core, no boards / cloth). The plain box of the light field has none ->
the counters keep it; the model waits for the remake.

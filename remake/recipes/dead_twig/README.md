# Dead swamp twigs (tileset 13: rooms 432 / 433 / 436 / 443 ...) - 2026-11-21, WIP, waits for the user's OK

`python3 dead_twig.py OUT.obj VARIANT [X Y Z]`: round branches (tubes, 12 sides = smooth in the light) along a skeleton read on the drawing
(`variants.json`: [dU, dV, r] picture pixels from the drawn foot, radius in world units), branches in the picture plane (light variant = as drawn;
a spread 3D crown is for the remake variant).
- `big`: the big twig of rooms 432 / 436 (same map; the only pixel-equal copies of this drawing in tileset 13), foot U 1193 V 452 -> world 456.5 447.5 0
  (its own 2 step collision column at cell (28,27); it stands on the floor 0 in front of it). Skeleton fitted point by point (each point <= 2 px from the
  hand reading, local ~/Project-Friday-Test/lktest/swamp/fit_twig.py): IoU 0.728 on its own pixels (thin object: the 1 px rim weighs a lot), 18 px out.
- Found so far: dozens of twigs / stubs per swamp room, nearly every one its own drawing -> open question to the user: build them automatically from the
  drawing (skeleton of the twig pixels -> tubes, foot by the view ray) instead of one by one.
Not placed in data/light_proxies.json yet. Sheet: ~/Project-Friday-Test/Mockups/sumpfbaum_432.png.

# Pine clusters as single pines - light shapes (since 2026-11-16)

Recipe only (no ROM data: the pine template is rebuilt from the ROM on every run). The automatic outdoor light shapes take a group of drawn
pines that touch each other as ONE object = one sprite lathe = one round shadow (room 636 #6: r 17 for four pines; HANDOFF 0a452 / -207;
user 2026-11-15 'generell bei solchen Gruppen einzelne Tannen').

- `pine_cluster.py ROM SURVEY.log [ROOMS] [--write] [--png DIR]`: SURVEY.log = `landstalker/tools/proxysurvey.py ROM [ROOMS] --run DIR`
  (LANDSTALKER_LIGHTING_DBG=5 lines). Finds the pines of every lathe that is wider (r >= 13) or taller (>= 56) than one pine by a template match
  of the forest pine sprite on the cell lattice, keeps only pines that stand on a BLOCKED, raised cell of the game's height map (user
  2026-11-16: use the room data; the collision alone cannot tell a pine from a crate, the picture alone has shifted copies), and writes one
  mesh op per group (`surface`; the op drops the automatic lathe(s) in its rectangle). Guards (left out, reported): dense forest (> 8 pines),
  two drawn pines on one cell (forest edge on a step: 461 / 506 / 559 / 564 / 571), a lathe that stands away from the pines (a bush:
  636 steps group, 638), a rectangle holding a hip.
- `params_light.json`: the WILD style C pine (`remake/recipes/pine_court/pine.py`, trim 0) fitted to the forest pine sprite: silhouette IoU
  0.87, trunk axis = drawn foot - 3 in x and y.
- Writes `landstalker/data/proxies/pine_cl_ROOM_K.obj`; 2026-11-16: 10 groups in rooms 183, 425 (2), 430, 433, 474 (2), 484, 514, 636.
  Re-run after a change of the automatic shapes (the lathe numbers / feet come from the survey).

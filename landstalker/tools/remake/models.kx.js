// Remake models (kiln recipes, tools/remake_assets.py builds them into ~/.landstalker_remake/models/*.r3m).
// Only recipes live in the repo; the generated models stay on the user's machine.
// Units: metres, Y up, +Z front (kiln); the game scales every model to the height of the art it replaces.
pal({
  bark: "#6e4535", barkL: "#8a5a40",
  leafD: "#1f6a3a", leaf: "#2f9a4a", leafL: "#52c46a",
  bushD: "#27703a", bushL: "#45b05a",
  rock: "#7d8390", rockD: "#5f6470",
})

model("pine",
  cyl(0.10, 0.55, { mat: "bark", sides: 5 }),
  cone(0.78, 0.95, { mat: "leafD", sides: 7, pos: [0, 0.32, 0], jitter: 0.03, seed: 1 }),
  cone(0.60, 0.90, { mat: "leaf", sides: 7, pos: [0, 0.82, 0], rot: [0, 20, 0], jitter: 0.03, seed: 2 }),
  cone(0.42, 0.85, { mat: "leafL", sides: 7, pos: [0, 1.32, 0], rot: [0, 40, 0], jitter: 0.03, seed: 3 }))

model("bush",
  sphere(0.42, { mat: "bushD", detail: 1, pos: [0, 0.36, 0], jitter: 0.04, seed: 4 }),
  sphere(0.30, { mat: "bushL", detail: 1, pos: [0.22, 0.46, 0.1], jitter: 0.04, seed: 5 }))

model("rock",
  rock(0.45, { mat: "rock", seed: 3 }))

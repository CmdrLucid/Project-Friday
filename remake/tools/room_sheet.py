#!/usr/bin/env python3
"""room_sheet.py ROOM_DIR ORIGINAL.png OUT.png   -- comparison sheet of a room blockout (recipes/room_c.py): the original picture (rom_picture.py,
same window) next to the game view of the remake, below the three turned views (q1..q3) at half size.  Needs pillow (~/hdvenv/bin/python)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
d, orig, outp = sys.argv[1:4]
try: f = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 22)
except Exception: f = ImageFont.load_default()
a = Image.open(orig).convert("RGB"); b = Image.open(os.path.join(d, "game.png")).convert("RGB").resize(a.size)
qs = [Image.open(os.path.join(d, "q%d.png" % q)).convert("RGB") for q in (1, 2, 3)]
qw = (2 * a.width) // 3; qs = [q.resize((qw, qw * q.height // q.width)) for q in qs]
out = Image.new("RGB", (2 * a.width, a.height + max(q.height for q in qs)), (28, 28, 32)); dr = ImageDraw.Draw(out)
out.paste(a, (0, 0)); out.paste(b, (a.width, 0))
for i, q in enumerate(qs): out.paste(q, (i * qw, a.height))
for x, y, t in ((10, 8, "Original"), (a.width + 10, 8, "Remake (Rohbau)"), (10, a.height + 8, "q1 (90 Grad)"), (qw + 10, a.height + 8, "q2 (180 Grad)"), (2 * qw + 10, a.height + 8, "q3 (270 Grad)")):
    dr.text((x, y), t, fill=(255, 220, 120), font=f)
out.save(outp); print("sheet", outp, out.size)

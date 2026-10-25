#!/usr/bin/env python3
"""sheet.py materials_c   puts the per-material renders of recipes/materials_c.py into one labelled sheet
(~/.landstalker_remake/assets/materials_c/sheet.png).  Needs pillow (run with ~/hdvenv/bin/python)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
d = os.path.join(os.path.expanduser("~"), ".landstalker_remake", "assets", sys.argv[1] if len(sys.argv) > 1 else "materials_c")
rows = [l.split("\t") for l in open(os.path.join(d, "names.txt")).read().splitlines()]
COLS = 5; W, H, LAB = 320, 300, 46
try: f1 = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 20); f2 = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", 14)
except Exception: f1 = f2 = ImageFont.load_default()
out = Image.new("RGB", (COLS * W, ((len(rows) + COLS - 1) // COLS) * (H + LAB)), (28, 28, 32)); dr = ImageDraw.Draw(out)
for i, (n, desc) in enumerate(rows):
    x, y = (i % COLS) * W, (i // COLS) * (H + LAB)
    out.paste(Image.open(os.path.join(d, n + ".png")).convert("RGB"), (x, y))
    dr.text((x + 8, y + H + 2), n, fill=(255, 220, 120), font=f1); dr.text((x + 8, y + H + 25), desc, fill=(210, 210, 210), font=f2)
out.save(os.path.join(d, "sheet.png")); print(os.path.join(d, "sheet.png"), out.size)

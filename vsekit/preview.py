"""Render selected frames of a .blend to PNG + a labelled contact sheet.
Usage: blender -b file.blend --python preview.py -- <out_dir> <percent> <cols> <frame> [frame ...]"""
import os
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir, pct, cols = argv[0], int(argv[1]), int(argv[2])
frames = [int(x) for x in argv[3:]]
os.makedirs(out_dir, exist_ok=True)
scn = bpy.context.scene
r = scn.render
r.image_settings.media_type = 'IMAGE'
r.image_settings.file_format = 'PNG'
r.resolution_percentage = pct
paths = []
for fr in frames:
    scn.frame_set(fr)
    r.filepath = os.path.join(out_dir, f"f{fr:04d}.png")
    bpy.ops.render.render(write_still=True)
    paths.append((fr, r.filepath))

from PIL import Image, ImageDraw, ImageFont
ims = [(fr, Image.open(p).convert("RGB")) for fr, p in paths]
w, h = ims[0][1].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w + (cols + 1) * 6, rows * h + (rows + 1) * 6), (30, 30, 30))
d = ImageDraw.Draw(sheet)
try:
    fnt = ImageFont.truetype("arialbd.ttf", max(14, w // 14))
except OSError:
    fnt = ImageFont.load_default()
for i, (fr, im) in enumerate(ims):
    x, y = 6 + (i % cols) * (w + 6), 6 + (i // cols) * (h + 6)
    sheet.paste(im, (x, y))
    d.text((x + 8, y + 6), f"{fr} ({(fr - 1) / r.fps:.2f}s)", font=fnt, fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0))
sheet.save(os.path.join(out_dir, "sheet.png"))
print("SHEET>>", os.path.join(out_dir, "sheet.png"))

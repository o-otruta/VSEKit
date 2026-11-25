"""Step 1 (outside Blender): voice-over, captions, graphics, music, SFX -> assets/ + manifest.json.
Run with the toolbox venv:  ..\..\.venv\Scripts\python.exe prepare.py"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import config as C
from vsekit import audio as A, gfx as G, media as M, tts as T

D = {k: os.path.join(C.ASSETS, k) for k in ("img", "captions", "counters", "audio", "tts")}
for p in D.values():
    os.makedirs(p, exist_ok=True)

shot = lambda rel: Image.open(os.path.join(C.SHOTS, rel)).convert("RGBA")
img_path = lambda n: os.path.join(D["img"], n)
manifest = {"vo": [], "captions": [], "counters": {}, "img": {}, "audio": {}}
fps = C.FPS

# ------------------------------------------------------------------ voice-over + captions
f_cap = G.font(C.FONT_BODY, 76)
vo_ends = []
for vid, start, text in C.VO:
    mp3 = os.path.join(D["tts"], vid + ".mp3")
    words = T.synth(text, mp3, C.VOICE, C.VOICE_RATE)
    wav = os.path.join(D["tts"], vid + ".wav")
    M.to_wav(mp3, wav)
    dur = M.duration(wav)
    manifest["vo"].append({"id": vid, "file": wav, "start": start, "frames": int(round(dur * fps)), "words": words})
    vo_ends.append(start + dur * fps)

for i, v in enumerate(manifest["vo"]):
    nxt = manifest["vo"][i + 1]["start"] if i + 1 < len(manifest["vo"]) else C.TOTAL
    end = v["start"] + v["frames"]
    status = "OK" if end <= nxt - 2 else "OVERLAP!"
    print(f"{v['id']}: {v['start']}..{end:.0f} (next {nxt}) {status}")

for v in manifest["vo"]:
    sec = next(k for k, (a, b) in C.SEC.items() if a <= v["start"] < b)
    y = C.CAPTION_Y.get(sec, C.CAPTION_Y["default"])
    chunks = G.chunk_words(v["words"])
    for ci, ch in enumerate(chunks):
        texts = [w["text"] for w in ch]
        c_end = (chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else ch[-1]["end"] + 0.35)
        for wi, wd in enumerate(ch):
            im = G.caption_image(texts, wi, f_cap, font_path=C.FONT_BODY)
            fn = os.path.join(D["captions"], f"{v['id']}_{ci:02d}_{wi}.png")
            im.save(fn)
            st = v["start"] + int(round(wd["start"] * fps))
            en = v["start"] + int(round((ch[wi + 1]["start"] if wi + 1 < len(ch) else c_end) * fps))
            manifest["captions"].append({"file": fn, "start": st, "end": max(en, st + 2),
                                         "first": wi == 0, "y": y, "vo": v["id"]})

# ------------------------------------------------------------------ images
def save(name, im):
    im.save(img_path(name)); manifest["img"][name] = img_path(name)
    return im

save("hook_bg.png", G.cover(shot(C.HOOK_BG), C.W, C.H))
save("before.png", G.cover(shot(C.BEFORE), C.W, C.H, fy=0.45))
save("after.png", G.cover(shot(C.AFTER), C.W, C.H))
for i, rel in enumerate(C.MONTAGE):
    save(f"montage_{i}.png", G.cover(shot(rel), C.W, C.H))
save("adapt_bg.png", G.cover(shot(C.LANDSCAPE), C.W, C.H))
save("card_landscape.png", G.card(shot(C.LANDSCAPE), 960, 540))
save("phone.png", G.phone(shot(C.PORTRAIT), 330))
save("divider.png", G.divider(C.H))
f_t = lambda s: G.font(C.FONT_TITLE, s)
f_b = lambda s: G.font(C.FONT_BODY, s)
save("badge_devlog.png", G.pill("DEVLOG #1", f_t(64), (20, 16, 40, 255), (255, 214, 10, 255), pad=(40, 20)))
# outro background: gradient + glows + voxel confetti
bg = G.gradient(C.W, C.H, (32, 14, 70, 255), (8, 8, 22, 255))
bg.alpha_composite(G.radial(C.W, C.H, (540, 760), 760, (255, 180, 40, 90)))
bg.alpha_composite(G.radial(C.W, C.H, (160, 1700), 600, (110, 60, 255, 110)))
bg.alpha_composite(G.voxel_scatter(C.W, C.H, 140, [(255, 214, 10), (130, 90, 255), (60, 200, 255)]))
save("outro_bg.png", bg)
logo = Image.new("RGBA", (1000, 260), (0, 0, 0, 0))
from PIL import ImageDraw
d = ImageDraw.Draw(logo)
fl = f_t(170)
tw = fl.getlength("PROJECT B")
d.text(((1000 - tw) / 2, 20), "PROJECT B", font=fl, fill=(255, 214, 10, 255), stroke_width=10, stroke_fill=(20, 12, 40, 255))
save("logo.png", G.glow(logo, 26, (255, 170, 30, 255), 1.1))
save("btn_follow.png", G.pill("FOLLOW THE DEVLOG", f_b(58), (255, 255, 255, 255), (235, 40, 80, 255), pad=(54, 30)))

# counters (image sequences; count-up with ease-out over 18 frames, then hold)
f_num, f_lab = f_t(118), f_b(56)
for start, value, label in C.COUNTERS:
    files = []
    for k in range(56):
        v = round(value * G.ease_out_cubic(min(1.0, k / 18)))
        fn = os.path.join(D["counters"], f"{label.lower()}_{k:03d}.png")
        G.lower_third(str(v), label, f_num, f_lab).save(fn)
        files.append(fn)
    manifest["counters"][label] = {"start": start, "files": files}

# ------------------------------------------------------------------ music + SFX
beat = 60 / C.BPM
prog = [(33, [57, 60, 64]), (29, [53, 57, 60]), (36, [55, 60, 64]), (31, [55, 59, 62])]  # Am F C G
sections = [(0, 8, "intro"), (8, 44, "main"), (44, 52, "heavy"), (52, 62, "main"), (62, 68, "break")]
music = A.make_track(C.BPM, sections, C.TOTAL / fps + 2.0, prog)
# outro pad tail + final hit
place_t = 66 * beat
A.place(music, A.pad_chord([A.midi(n) for n in [57, 60, 64, 69]], 3.5, 1200) * 1.4, place_t)
sfx = {
    "music": music,
    "riser": A.sfx_riser(3.4),
    "impact": A.sfx_impact(),
    "whoosh": A.sfx_whoosh(0.4),
    "whoosh_long": A.sfx_whoosh(0.7, 200, 3500),
    "glitch": A.sfx_glitch(0.45),
    "pop": A.sfx_pop(),
    "ding": A.sfx_ding(),
    "tick": A.sfx_tick(),
}
for name, x in sfx.items():
    fn = os.path.join(D["audio"], name + ".wav")
    A.write_wav(fn, x)
    manifest["audio"][name] = fn

json.dump(manifest, open(os.path.join(C.ASSETS, "manifest.json"), "w", encoding="utf-8"), indent=1)
print("captions:", len(manifest["captions"]), "images:", len(manifest["img"]))

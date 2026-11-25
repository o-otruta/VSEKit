"""Demo 2 – Whisper: automatic jump cuts + karaoke captions + punch-ins (16:9, YouTube style).
    prepare:  .venv/Scripts/python.exe d2_jumpcuts.py prepare
    build:    blender -b --factory-startup --python d2_jumpcuts.py -- build"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
SRC = os.path.join(os.path.dirname(HERE), "media", "src", "nasa_students.mp4")   # natural Q&A speech
WORK = os.path.join(HERE, "work", "d2"); os.makedirs(WORK, exist_ok=True)
MAN = os.path.join(WORK, "manifest.json")
FPS_NUM, FPS_BASE = 30, 1.001
FPS = FPS_NUM / FPS_BASE
WIN = (0.0, 90.0)          # source window to edit


def prepare():
    from common import G, FONT_B, FONT_T, YEL
    from vsekit import transcribe as T
    r = T.transcribe(SRC)
    keep = T.cut_list(r, min_gap=0.28, pad=0.06, start=WIN[0], end=WIN[1])
    segs, t = [], 0.0
    for a, b in keep:
        segs.append({"in": a, "out": b, "tl": t}); t += b - a
    removed = (WIN[1] - WIN[0]) - t
    # remap words to the new timeline
    words = []
    for w in T.words(r):
        for s in segs:
            if s["in"] <= w["start"] < s["out"]:
                words.append({"text": w["text"], "start": s["tl"] + w["start"] - s["in"],
                              "end": s["tl"] + min(w["end"], s["out"]) - s["in"]}); break
    caps = []
    f = G.font(FONT_B, 62)
    chunks = G.chunk_words(words, max_words=4, max_chars=26)
    for ci, ch in enumerate(chunks):
        texts = [w["text"] for w in ch]
        c_end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else ch[-1]["end"] + 0.4
        for wi, w in enumerate(ch):
            fn = os.path.join(WORK, f"cap_{ci:03d}_{wi}.png")
            G.caption_image(texts, wi, f, width=1500, font_path=FONT_B, stroke=7).save(fn)
            caps.append({"file": fn, "start": w["start"], "end": ch[wi + 1]["start"] if wi + 1 < len(ch) else c_end,
                         "first": wi == 0})
    G.pill("WHISPER  ·  AUTO JUMP CUTS  ·  CAPTIONS", G.font(FONT_T, 32), (20, 16, 40, 255), YEL, pad=(26, 12)).save(
        os.path.join(WORK, "tag.png"))
    stat = f"removed {removed:.1f}s of pauses ({100 * removed / (WIN[1] - WIN[0]):.0f}%) · {len(segs)} cuts"
    G.pill(stat, G.font(FONT_B, 30), (255, 255, 255, 255), (12, 12, 22, 200), pad=(24, 12)).save(
        os.path.join(WORK, "stat.png"))
    # SRT of the edited version
    T.to_srt({"segments": [{"words": words}]}, os.path.join(HERE, "out", "02_whisper_jumpcuts.srt"))
    json.dump({"segs": segs, "caps": caps, "duration": t, "removed": removed}, open(MAN, "w"), indent=1)
    print(stat, "->", round(t, 1), "s")


def build():
    import bpy
    from vsekit import vse as V
    m = json.load(open(MAN))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.data.scenes[0]; scn.name = "Edit"
    end = round(m["duration"] * FPS) + 1
    ed = V.setup(scn, 1920, 1080, FPS_NUM, end)
    scn.render.fps_base = FPS_BASE
    V.name_channels(ed, {1: "Video A", 2: "Video B", 3: "Overlays", 4: "Captions", 6: "Dialogue A", 7: "Dialogue B"})
    f = lambda s: round(s * FPS) + 1
    for i, s in enumerate(m["segs"]):
        ch = 1 + i % 2                      # checkerboard: A/B tracks make cuts easy to see/edit
        mv, _ = V.clip(ed, f"Cut {i + 1:02d}", SRC, ch, s["in"], s["out"], f(s["tl"]), FPS, sound_ch=6 + i % 2)
        if i % 2 == 1:                      # punch-in on every other cut hides the jump
            mv.transform.origin = (0.5, 0.6)
            mv.transform.scale_x = mv.transform.scale_y = 1.12
    tag = V.image(ed, "Tag", os.path.join(WORK, "tag.png"), 3, 1, end, 400, 70)
    V.fade(tag, 1, 10)
    caps = sorted(m["caps"], key=lambda c: c["start"])
    for i, c in enumerate(caps):
        st, en = f(c["start"]), f(c["end"])
        if i + 1 < len(caps):
            en = min(en, f(caps[i + 1]["start"]))
        if en > st:
            s = V.image(ed, "Cap", c["file"], 4, st, en, 960, 940)
            if c["first"]:
                V.anim_scale(s.transform, [(st, 0.85), (st + 4, 1.0)], 'BACK', 'EASE_OUT')
    stp = V.image(ed, "Stat", os.path.join(WORK, "stat.png"), 3 + 2, end - 150, end, 1500, 1010) if end > 160 else None
    if stp:
        V.fade(stp, end - 150, end - 140)
    r = scn.render
    r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = 'MPEG4', 'H264', 'HIGH'
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_mixrate = 'AAC', 192, 48000
    r.filepath = os.path.join(HERE, "out", "02_whisper_jumpcuts.mp4"); r.use_file_extension = False
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "02_whisper_jumpcuts.blend"))
    print("BUILD>>", len(ed.strips_all), "strips")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"prepare": prepare, "build": build}[args[0]]()

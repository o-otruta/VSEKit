"""Demo 6 – Auto trailer: PySceneDetect shots + librosa beats -> beat-synced montage (16:9).
    prepare:  .venv/Scripts/python.exe d6_auto_trailer.py prepare
    build:    blender -b --factory-startup --python d6_auto_trailer.py -- build"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
MEDIA = os.path.join(os.path.dirname(HERE), "media", "src")
VID = os.path.join(MEDIA, "nasa_iss.mp4")
MUS = os.path.join(MEDIA, "music_upbeat_forever.wav")
WORK = os.path.join(HERE, "work", "d6"); os.makedirs(WORK, exist_ok=True)
MAN = os.path.join(WORK, "manifest.json")
FPS_NUM, FPS_BASE = 30, 1.001
FPS = FPS_NUM / FPS_BASE
LENGTH = 24.0
CREDITS = "Music: \"Upbeat Forever\" Kevin MacLeod (incompetech.com) CC BY 4.0  ·  Footage: NASA"


def prepare():
    from common import G, FONT_B, FONT_T, YEL
    from vsekit import scenes as S, beats as B
    sc = S.detect(VID)
    bt = B.analyze(MUS)
    # music window: most energetic LENGTH seconds, snapped back to a downbeat
    w0 = B.loudest_section(bt, LENGTH)
    w0 = max([d for d in bt["downbeats"] if d <= w0 + 0.01] or [bt["downbeats"][0]])
    beats = [b - w0 for b in bt["beats"] if w0 <= b < w0 + LENGTH]
    downs = [d - w0 for d in bt["downbeats"] if w0 <= d < w0 + LENGTH]
    # cut on every 2nd beat for the first half, every beat in the last third (accelerating edit)
    cuts = []
    for i, b in enumerate(beats):
        if b < 2.2:            # title card over the first bar
            continue
        if b > LENGTH - 2.6:   # end card
            break
        if b < LENGTH * 0.62 and i % 2:
            continue
        cuts.append(b)
    cuts.append(LENGTH - 2.6)
    usable = [s for s in sc if s["end"] - s["start"] >= 1.2 and 4 < s["start"] < sc[-1]["end"] - 6]
    n = len(cuts) - 1
    step = len(usable) / n
    picks = [usable[int(i * step)] for i in range(n)]
    clips = []
    for i in range(n):
        d = cuts[i + 1] - cuts[i]
        s = picks[i]
        mid = (s["start"] + s["end"]) / 2
        a = max(s["start"], min(mid - d / 2, s["end"] - d))
        clips.append({"tl": cuts[i], "in": a, "out": a + d})
    first = cuts[0]
    G.pill("SCENEDETECT + LIBROSA  ·  AUTO TRAILER", G.font(FONT_T, 30), (20, 16, 40, 255), YEL, pad=(24, 12)).save(
        os.path.join(WORK, "tag.png"))
    json.dump({"clips": clips, "downbeats": downs, "music_in": w0, "first": first, "tempo": bt["tempo"],
               "shots_total": len(sc), "length": LENGTH}, open(MAN, "w"), indent=1)
    print(f"tempo {bt['tempo']:.1f} BPM, {len(sc)} shots detected, {len(clips)} clips, music from {w0:.2f}s")


def build():
    import bpy
    from vsekit import vse as V
    m = json.load(open(MAN))
    from vsekit.env import FONT_TITLE as FT, FONT_BODY as FB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.data.scenes[0]; scn.name = "Edit"
    f = lambda s: round(s * FPS) + 1
    end = f(m["length"])
    ed = V.setup(scn, 1920, 1080, FPS_NUM, end)
    scn.render.fps_base = FPS_BASE
    V.name_channels(ed, {1: "Shots A", 2: "Shots B", 3: "Cards", 4: "Titles", 5: "Punch", 6: "Flash", 8: "Music"})
    title_bg = V.color(ed, "Title BG", (0.03, 0.02, 0.08), 3, 1, f(m["first"]) + 6)
    V.fade(title_bg, f(m["first"]), f(m["first"]) + 6, 1, 0)
    t1 = V.text(ed, "Title", "HUMANITY'S LAB IN SPACE", 4, 1, f(m["first"]) + 4, 960, 500, FT, 110, (1, 0.84, 0.04, 1))
    t1.transform.origin = (0.5, 1 - 500 / 1080)
    V.anim_scale(t1.transform, [(1, 0.7), (14, 1.0)], 'BACK', 'EASE_OUT'); V.fade(t1, 1, 8)
    t2 = V.text(ed, "Subtitle", f"{m['shots_total']} shots detected · cut to {m['tempo']:.0f} BPM", 5, 8,
                f(m["first"]) + 4, 960, 620, FB, 46)
    V.fade(t2, 8, 16)
    for i, c in enumerate(m["clips"]):
        mv, _ = V.clip(ed, f"Shot {i + 1:02d}", VID, 1 + i % 2, c["in"], c["out"], f(c["tl"]), FPS)
        st, en = f(c["tl"]), f(c["out"] - c["in"] + c["tl"])
        V.anim_scale(mv.transform, [(st, 1.10), (st + 6, 1.0), (en, 1.04)], 'CUBIC', 'EASE_OUT')
    for d in m["downbeats"]:
        if m["first"] - 0.05 <= d < m["length"] - 2.6:
            fl = V.color(ed, "Flash", (1, 1, 1), 6, f(d), f(d) + 4)
            V.keys(fl, "blend_alpha", [(f(d), 0.55), (f(d) + 3, 0.0)], 'LINEAR')
    end_bg = V.color(ed, "End BG", (0.03, 0.02, 0.08), 3, f(m["length"] - 2.6), end + 1)
    V.fade(end_bg, f(m["length"] - 2.6), f(m["length"] - 2.6) + 6)
    e1 = V.text(ed, "End title", "AUTO-CUT IN 0 CLICKS", 4, f(m["length"] - 2.5), end + 1, 960, 470, FT, 96, (1, 0.84, 0.04, 1))
    V.fade(e1, f(m["length"] - 2.5), f(m["length"] - 2.2))
    e2 = V.text(ed, "Credits", CREDITS, 5, f(m["length"] - 2.4), end + 1, 960, 980, FB, 30, (1, 1, 1, 0.85))
    tag = V.image(ed, "Tag", os.path.join(WORK, "tag.png"), 7, f(m["first"]), f(m["length"] - 2.6), 380, 70)
    mu = V.sound(ed, "Music", MUS, 8, 1 - round(m["music_in"] * FPS))
    mu.frame_final_start, mu.frame_final_end = 1, end + 1
    V.volume_keys(mu, [(end - 20, 1.0), (end, 0.0)])
    r = scn.render
    r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = 'MPEG4', 'H264', 'HIGH'
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_mixrate = 'AAC', 192, 48000
    r.filepath = os.path.join(HERE, "out", "06_auto_trailer.mp4"); r.use_file_extension = False
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "06_auto_trailer.blend"))
    print("BUILD>>", len(ed.strips_all), "strips")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"prepare": prepare, "build": build}[args[0]]()

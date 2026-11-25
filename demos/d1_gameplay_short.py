"""Demo 1 – Unity Recorder footage (BalanceBot) -> vertical short cut to music beats.
    prepare:  .venv/Scripts/python.exe d1_gameplay_short.py prepare
    build:    blender -b --factory-startup --python d1_gameplay_short.py -- build"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
KIT = os.path.dirname(HERE)
VID = os.path.join(KIT, "media", "gameplay", "bot_knight_full.mp4")
MUS = os.path.join(KIT, "media", "src", "music_upbeat_forever.wav")
WORK = os.path.join(HERE, "work", "d1"); os.makedirs(WORK, exist_ok=True)
MAN = os.path.join(WORK, "manifest.json")
FPS = 60


def prepare():
    from common import G, FONT_T, FONT_B, YEL
    from vsekit import beats as B, media as M
    dur = M.duration(VID)
    bt = B.analyze(MUS)
    w0 = B.loudest_section(bt, dur)
    w0 = max([d for d in bt["downbeats"] if d <= w0 + 0.01] or [0.0])
    beats = [b - w0 for b in bt["beats"] if w0 <= b < w0 + dur + 2]
    punches = [b - w0 for b in B.strongest(bt, 8, min_gap=1.0, after=w0 + 0.8, before=w0 + dur - 1.5)]
    G.pill("UNITY RECORDER  ·  BOT GAMEPLAY  ·  BEAT SYNC", G.font(FONT_T, 34), (20, 16, 40, 255), YEL,
           pad=(26, 12)).save(os.path.join(WORK, "tag.png"))
    json.dump({"dur": dur, "music_in": w0, "beats": beats, "punches": punches}, open(MAN, "w"), indent=1)
    print(f"footage {dur:.1f}s, tempo {bt['tempo']:.0f} BPM, {len(punches)} punch-ins")


def build():
    import bpy
    from vsekit import vse as V, fx as X
    m = json.load(open(MAN))
    from vsekit.env import FONT_TITLE as FT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.data.scenes[0]; scn.name = "Edit"
    f = lambda s: round(s * FPS) + 1
    SLOW_A, SLOW_B = 4.0, 5.2                       # source seconds played at 0.5x
    total = m["dur"] + (SLOW_B - SLOW_A)            # slow-mo adds time
    end = f(total)
    ed = V.setup(scn, 1080, 1920, FPS, end)
    V.name_channels(ed, {1: "Gameplay", 2: "Punch", 3: "Titles", 4: "Flash", 5: "Grade", 7: "Music"})
    mv = V.movie(ed, "Gameplay (Unity Recorder)", VID, 1, 1)
    # speed ramp via retiming keys: 1x -> 0.5x -> 1x
    k1 = mv.retiming_keys.add(timeline_frame=f(SLOW_A))
    k2 = mv.retiming_keys.add(timeline_frame=f(SLOW_B))
    k2.timeline_frame = f(SLOW_B + (SLOW_B - SLOW_A))
    last = mv.retiming_keys[len(mv.retiming_keys) - 1]
    last.timeline_frame = end
    mv.frame_final_end = end
    shift = lambda t: t if t < SLOW_A else (SLOW_A + (t - SLOW_A) * 2 if t < SLOW_B else t + (SLOW_B - SLOW_A))
    for i, p in enumerate(m["punches"]):
        t = shift(p)
        adj = V.adjustment(ed, f"Punch {i + 1}", 2, f(t), f(t) + 14)
        V.anim_scale(adj.transform, [(f(t), 1.12), (f(t) + 14, 1.0)], 'EXPO', 'EASE_OUT')
        fl = V.color(ed, f"Flash {i + 1}", (1, 1, 1), 4, f(t), f(t) + 5)
        V.keys(fl, "blend_alpha", [(f(t), 0.35), (f(t) + 4, 0.0)], 'LINEAR')
    hook = V.text(ed, "Hook", "MY BOT PLAYS\nMY GAME", 3, 1, f(2.6), 540, 760, FT, 120, (1, 0.84, 0.04, 1),
                  outline=((0.05, 0.03, 0.1, 1), 0.12))
    hook.transform.origin = (0.5, 1 - 760 / 1920)
    V.anim_scale(hook.transform, [(1, 0.6), (13, 1.0)], 'BACK', 'EASE_OUT'); V.fade(hook, f(2.3), f(2.6), 1, 0)
    sm = V.text(ed, "Slow-mo label", "0.5x", 3, f(SLOW_A), f(SLOW_B + 1.2), 900, 1500, FT, 90, (1, 1, 1, 0.9))
    V.fade(sm, f(SLOW_A), f(SLOW_A) + 6)
    tag = V.image(ed, "Tag", os.path.join(WORK, "tag.png"), 6, f(2.6), end, 540, 1830)
    V.fade(tag, f(2.6), f(2.9))
    gr = V.adjustment(ed, "Grade", 5, 1, end)
    X.attach(gr, X.grade(grain=0.05, vignette=0.35))
    mu = V.sound(ed, "Music", MUS, 7, 1 - round(m["music_in"] * FPS))
    mu.frame_final_start, mu.frame_final_end = 1, end
    V.volume_keys(mu, [(1, 0.0), (8, 0.9), (end - 30, 0.9), (end - 1, 0.0)])
    r = scn.render
    r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = 'MPEG4', 'H264', 'HIGH'
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_mixrate = 'AAC', 192, 48000
    r.filepath = os.path.join(HERE, "out", "01_gameplay_short.mp4"); r.use_file_extension = False
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "01_gameplay_short.blend"))
    print("BUILD>>", len(ed.strips_all), "strips; retiming", [k.timeline_frame for k in mv.retiming_keys])


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"prepare": prepare, "build": build}[args[0]]()

"""Demo 8: 9:16 devlog short (11.7 s) — HTML motion graphics over gameplay, music-synced, on a VSE timeline.
    all:    .venv\\Scripts\\python.exe d8_sprint_short.py         (HTML frames + audio, then Blender build)
    build:  blender -b --factory-startup --python d8_sprint_short.py -- build
    render: blender -b out/08_sprint_short.blend -a   ->  media.finalize()

Direction (references/direction_and_quality.md)
  Thread: "the horde got denser" — Sprint 16 traded HP-sponge enemies for density; the video proves it with
  a swarm, a number, three new enemies, then the name.
  Accent map: music = "Upbeat Forever" (Kevin MacLeod, CC BY 4.0) from 103.26 s; bar downbeats every 2.92 s.
  | t (s) | accent        | visual event                                   | sound            |
  | 0.35  | downbeat      | "THE HORDE" slams in, footage punch-in + shake | impact           |
  | 1.81  | half-bar      | "GOT DENSER" lands, underline starts drawing   | whoosh (once)    |
  | 2.6   | -             | underline becomes the "BEFORE 0.50s" bar       | -                |
  | 4.74  | half-bar      | counter hits 0.16s, "3x FASTER" pops           | ticks -> pop     |
  | 6.20  | downbeat      | enemy cards land                               | pops             |
  | 7.66  | half-bar      | cursor clicks Siege Golemite, card expands     | click + ding     |
  | 9.12  | downbeat      | end title rises, footage punch-in              | impact (lighter) |
  Options weighed for the hook: letters drop / scale-slam / swarm pushes words / rolling counter -> scale-slam
  over a swarm of the new enemies (the swarm *is* the claim). Cards: grid / carousel / stack + cursor pick
  -> stack + cursor (shows a UI interaction and frees time to read one detail).
"""
import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, KIT)
FPS, W, H = 60, 1080, 1920
CUTS = [0.0, 2.6, 5.9, 9.12, 11.7]                 # scene windows (s) — one VSE strip each
SCENES = ["S1 hook", "S2 spawn delay", "S3 new enemies", "S4 end card"]
WORK = os.path.join(HERE, "work", "d8")
OUT = os.path.join(HERE, "out")
FOOTAGE = os.path.join(KIT, "media", "gameplay", "bot_knight_full.mp4")   # vsekit record_bot_gameplay.cs
MUSIC = os.path.join(KIT, "media", "src", "music_upbeat_forever.wav")      # demos/fetch_media.py
MUSIC_IN = 103.26
PROJECTB = os.environ.get("PROJECTB_ROOT", r"D:\UnityProjects\ProjectB")
ICONS = os.path.join(PROJECTB, "Assets", "_UI", "Icons", "Generated", "enemy_{}Data.png")
CREDIT = "Music: “Upbeat Forever” — Kevin MacLeod (incompetech.com)<br>Licensed under CC BY 4.0"


def f(t):
    return 1 + round(t * FPS)


def prepare():
    import subprocess
    import time
    import numpy as np
    from vsekit import html_motion, audio as A, media, env
    os.makedirs(WORK, exist_ok=True)
    uri = lambda p: pathlib.Path(p).as_uri()  # noqa: E731
    params = {"icons": {k: uri(ICONS.format(n)) for k, n in
                        (("splitter", "SplitterSlime"), ("wisp", "FrostWisp"), ("golemite", "SiegeGolemite"))},
              "credit": CREDIT}
    t0 = time.time()
    for i, name in enumerate(SCENES):
        a, b = round(CUTS[i] * FPS), round(CUTS[i + 1] * FPS)
        html_motion.render(os.path.join(HERE, "html", "sprint_short.html"), os.path.join(WORK, f"s{i + 1}"),
                           (b - a) / FPS, fps=FPS, width=W, height=H, params=params, start=a / FPS)
    print(f"HTML frames: {time.time() - t0:.1f}s")

    dur = CUTS[-1]
    media.run([env.FFMPEG, "-y", "-v", "error", "-ss", str(MUSIC_IN), "-t", str(dur), "-i", MUSIC, "-af",
               f"afade=t=in:d=0.03,afade=t=out:st={dur - 0.9}:d=0.9", "-ar", "48000", "-ac", "2",
               os.path.join(WORK, "music.wav")])

    buf = np.zeros((int(dur * A.SR) + A.SR, 2))
    A.place(buf, A.sfx_impact(1.4) * 0.55, 0.35)
    A.place(buf, A.sfx_whoosh(0.4, 400, 6000) * 0.35, 1.45)
    # counter ticks: one per value change of the 0.50 -> 0.16 count (same easing as the CSS, approximated)
    for k in range(1, 34):
        x = k / 34
        u = x  # invert the ease-in-out roughly with a smoothstep inverse
        for _ in range(20):
            u -= (3 * u * u - 2 * u ** 3 - x) / max(1e-3, 6 * u - 6 * u * u)
            u = min(max(u, 0.0), 1.0)
        A.place(buf, A.sfx_tick() * 0.5, 3.3 + 1.44 * u)
    A.place(buf, A.sfx_pop(400, 1300, 0.16) * 0.7, 4.74)
    for t in (6.18, 6.34, 6.50):
        A.place(buf, A.sfx_pop(300, 900, 0.1) * 0.55, t)
    A.place(buf, A.sfx_tick() * 1.6, 7.6)
    A.place(buf, A.sfx_ding(1318, 0.9) * 0.8, 7.68)
    A.place(buf, A.sfx_impact(1.2) * 0.4, 9.12)
    A.write_wav(os.path.join(WORK, "sfx.wav"), buf[:int(dur * A.SR)])
    subprocess.run([env.BLENDER, "-b", "--factory-startup", "--python", __file__, "--", "build"], check=True)


def build():
    import glob
    import bpy
    from vsekit import vse, fx
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.data.scenes[0]
    scn.name = "Edit"
    end = f(CUTS[-1]) - 1
    ed = vse.setup(scn, W, H, FPS, end)

    mv, _ = vse.clip(ed, "Gameplay", FOOTAGE, 1, 0.0, CUTS[-1], 1, FPS)
    tr = mv.transform
    tr.origin = (0.5, 0.5)
    for slam, peak in ((0.35, 1.08), (9.12, 1.05)):            # punch-in on the two big downbeats
        for ax in ("scale_x", "scale_y"):
            vse.key(tr, ax, f(slam) - 2, 1.0 if slam < 1 else 1.02, 'LINEAR')
            vse.key(tr, ax, f(slam), peak, 'EXPO', 'EASE_OUT')
            vse.key(tr, ax, f(slam) + 30, 1.02, 'BEZIER')
    vse.shake(tr, f(0.35), f(0.75), strength=18, speed=2.2)

    gr = vse.adjustment(ed, "Grade", 2, 1, end + 1)
    fx.attach(gr, fx.grade(grain=0.04, vignette=0.35, bloom=0.25))
    dark = vse.color(ed, "Darken for text", (0.03, 0.03, 0.06), 3, 1, end + 1)
    vse.keys(dark, "blend_alpha", [(1, 0.3), (f(2.55), 0.3), (f(2.8), 0.6), (f(9.0), 0.6), (f(9.3), 0.45)],
             'SINE', 'EASE_IN_OUT')

    for i, name in enumerate(SCENES):
        files = sorted(glob.glob(os.path.join(WORK, f"s{i + 1}", "f_*.png")))
        vse.image_seq(ed, name, files, 5 + i % 2, f(CUTS[i]), f(CUTS[i + 1]))

    vse.sound(ed, "Music (CC BY Kevin MacLeod)", os.path.join(WORK, "music.wav"), 8, 1, volume=0.8)
    vse.sound(ed, "SFX", os.path.join(WORK, "sfx.wav"), 9, 1, volume=1.0)
    scn.audio_volume = 0.7
    vse.name_channels(ed, {1: "Footage", 2: "Grade", 3: "Darken", 5: "HTML A", 6: "HTML B", 8: "Music", 9: "SFX"})

    r = scn.render
    r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = 'MPEG4', 'H264', 'HIGH'
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_mixrate = 'AAC', 192, 48000
    r.filepath = os.path.join(OUT, "08_sprint_short_raw.mp4")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "08_sprint_short.blend"))
    print("saved", os.path.join(OUT, "08_sprint_short.blend"))


if __name__ == "__main__":
    if "build" in sys.argv:
        build()
    else:
        prepare()

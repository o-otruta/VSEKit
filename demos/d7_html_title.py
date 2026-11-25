"""Demo 7: HTML/CSS/SVG kinetic title -> PNG sequence with alpha -> image strip on a VSE timeline.
    frames:  .venv\\Scripts\\python.exe d7_html_title.py            (renders frames, then calls Blender)
    build:   blender -b --factory-startup --python d7_html_title.py -- build"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, KIT)
FPS, DUR = 60, 3.5
FRAMES = os.path.join(HERE, "work", "html_title")
# any 16:9 footage works as the background; falls back to a colour strip
BG = os.path.join(HERE, "out", "06_auto_trailer.mp4")


def frames():
    import subprocess
    import time
    from vsekit import html_motion, env
    t = time.time()
    files = html_motion.render(os.path.join(HERE, "html", "kinetic_title.html"), FRAMES, DUR, fps=FPS)
    print(f"{len(files)} frames in {time.time() - t:.1f}s")
    subprocess.run([env.BLENDER, "-b", "--factory-startup", "--python", __file__, "--", "build"], check=True)


def build():
    import glob
    import bpy
    from vsekit import vse
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.data.scenes[0]
    end = round(DUR * FPS)
    vse.setup(scn, 1920, 1080, FPS, end)
    ed = scn.sequence_editor_create()
    if os.path.exists(BG):
        vse.clip(ed, "Footage", BG, 1, 4.0, 4.0 + DUR, 1, FPS)
    else:
        vse.color(ed, "BG", (0.16, 0.24, 0.36), 1, 1, end + 1)
    files = sorted(glob.glob(os.path.join(FRAMES, "f_*.png")))
    vse.image_seq(ed, "HTML title", files, 3, 1, end + 1)
    vse.name_channels(ed, {1: "Footage", 3: "HTML overlay"})
    out = os.path.join(HERE, "out")
    r = scn.render
    r.image_settings.media_type = 'VIDEO'; r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = 'MPEG4', 'H264', 'HIGH'
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_mixrate = 'AAC', 192, 48000
    r.filepath = os.path.join(out, "07_html_title.mp4")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "07_html_title.blend"))
    print("saved", os.path.join(out, "07_html_title.blend"))


if __name__ == "__main__":
    if "build" in sys.argv:
        build()
    else:
        frames()

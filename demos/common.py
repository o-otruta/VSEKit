"""Shared helpers for demo builds (run with VSEKit/.venv python)."""
import os
import subprocess
import sys

DEMOS = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(DEMOS)
sys.path.insert(0, KIT)
from vsekit.env import FFMPEG, MEDIA  # noqa: E402
from vsekit import gfx as G  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = os.path.join(DEMOS, "out")
WORK = os.path.join(DEMOS, "work")
os.makedirs(OUT, exist_ok=True)
os.makedirs(WORK, exist_ok=True)
from vsekit.env import FONT_TITLE as FONT_T, FONT_BODY as FONT_B  # noqa: E402
# Some demos use assets from the ProjectB game repo (screenshots, gameplay capture):
PROJECTB = os.environ.get("PROJECTB_ROOT", r"D:\UnityProjects\ProjectB")
YEL = (255, 214, 10, 255)


def ff(*args):
    r = subprocess.run([FFMPEG, "-y", "-v", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])


def bg(w=1920, h=1080):
    im = G.gradient(w, h, (24, 16, 52, 255), (8, 8, 20, 255))
    im.alpha_composite(G.radial(w, h, (w * 0.75, h * 0.2), w * 0.5, (255, 170, 40, 40)))
    return im


def text(im, xy, s, size, fill=(255, 255, 255, 255), font=FONT_B, anchor="la"):
    ImageDraw.Draw(im).text(xy, s, font=G.font(font, size), fill=fill, anchor=anchor)


def card(title, lines=(), tag=None, w=1920, h=1080, extra=None, extra_xy=(160, 560)):
    im = bg(w, h)
    if tag:
        im.alpha_composite(G.pill(tag, G.font(FONT_T, 34), (20, 16, 40, 255), YEL, pad=(26, 12)), (140, 110))
    text(im, (160, 220), title, 92, YEL, FONT_T)
    for i, ln in enumerate(lines):
        text(im, (164, 350 + i * 62), ln, 44)
    if extra is not None:
        im.alpha_composite(extra, extra_xy)
    return im


def still_with_audio(png, wav, out_mp4, pad=0.5, fps=30):
    ff("-loop", "1", "-framerate", str(fps), "-i", png, "-i", wav, "-af", f"apad=pad_dur={pad}",
       "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21", "-pix_fmt", "yuv420p", "-r", str(fps),
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", out_mp4)


def still(png, seconds, out_mp4, fps=30):
    ff("-loop", "1", "-framerate", str(fps), "-i", png, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-t", str(seconds), "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", out_mp4)


def concat(parts, out_mp4):
    lst = out_mp4 + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", out_mp4)
    os.remove(lst)


def waveform(wav, png, w=1600, h=260, color="0xFFD60A"):
    ff("-i", wav, "-filter_complex", f"aformat=channel_layouts=mono,showwavespic=s={w}x{h}:colors={color}",
       "-frames:v", "1", png)
    return Image.open(png).convert("RGBA")


def spectrogram(wav, png, w=1600, h=330):
    ff("-i", wav, "-lavfi", f"showspectrumpic=s={w}x{h}:legend=0:color=intensity:scale=log:fscale=lin", png)
    return Image.open(png).convert("RGBA")


def wer(ref, hyp):
    import re
    norm = lambda s: re.sub(r"[^a-z0-9' ]", " ", s.lower()).split()
    r, h = norm(ref), norm(hyp)
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(r)][len(h)] / max(1, len(r))

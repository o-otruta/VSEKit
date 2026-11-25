"""ffmpeg helpers."""
import json
import subprocess
from .env import FFMPEG, FFPROBE


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"{args[0]} failed:\n{r.stderr[-2000:]}")
    return r


def to_wav(src, dst, sr=48000):
    run([FFMPEG, "-y", "-v", "error", "-i", src, "-ar", str(sr), "-ac", "2", dst])


def probe(path):
    r = run([FFPROBE, "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
             "-of", "json", path])
    return json.loads(r.stdout)


def duration(path):
    return float(probe(path)["format"]["duration"])


def loudness(path):
    """Integrated loudness (LUFS) + true peak via ebur128."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-filter_complex", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    out = {}
    for line in tail.splitlines():
        line = line.strip()
        if line.startswith("I:"):
            out["lufs"] = float(line.split()[1])
        elif line.startswith("Peak:"):
            out["true_peak"] = float(line.split()[1])
    return out


def finalize(src, dst, lufs=-14.0, tp=-1.5):
    """Normalise loudness for social platforms (TikTok/Shorts ~ -14 LUFS); video stream copied untouched."""
    run([FFMPEG, "-y", "-v", "error", "-i", src, "-c:v", "copy",
         "-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", dst])


def contact_sheet(video, out_png, every_s=1.0, cols=6, width=270):
    import math
    rows = math.ceil(duration(video) / every_s / cols)
    run([FFMPEG, "-y", "-v", "error", "-i", video, "-vf",
         f"fps=1/{every_s},scale={width}:-1,tile={cols}x{rows}:padding=4:color=black", "-frames:v", "1", out_png])


def assemble_sequence(folder, out_mp4, fps=60, cq=19, delete_frames=False):
    """Image sequence (e.g. Unity Recorder JPEG/PNG f_0000.jpg ...) -> H.264 mp4 via NVENC."""
    import glob
    import os
    import re
    files = sorted(glob.glob(os.path.join(folder, "*.jpg")) + glob.glob(os.path.join(folder, "*.png")))
    if not files:
        raise FileNotFoundError(f"no frames in {folder}")
    name = os.path.basename(files[0])
    m = re.match(r"(.*?)(\d+)(\.\w+)$", name)
    pattern = os.path.join(folder, f"{m.group(1)}%0{len(m.group(2))}d{m.group(3)}")
    run([FFMPEG, "-y", "-v", "error", "-framerate", str(fps), "-start_number", str(int(m.group(2))),
         "-i", pattern, "-c:v", "h264_nvenc", "-preset", "p5", "-cq", str(cq), "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", out_mp4])
    if delete_frames:
        for f in files:
            os.remove(f)
    return out_mp4


def frame_at(video, t, out_png, width=None):
    vf = ["-vf", f"scale={width}:-1"] if width else []
    run([FFMPEG, "-y", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", *vf, out_png])


def boundary_strip(video, t, out_png, before=3, after=3, width=320, fps=None):
    """Consecutive frames around time t (a cut / transition / sync point) tiled left-to-right in one row.
    A contact sheet shows compositions; this shows what actually happens across a boundary.
    Returns the timestamps of the tiles."""
    fps = fps or _fps(video)
    n = before + after
    first = max(0, round(t * fps) - before)
    run([FFMPEG, "-y", "-v", "error", "-ss", f"{first / fps:.4f}", "-i", video, "-vf",
         f"select='lt(n,{n})',scale={width}:-1,tile={n}x1:padding=3:color=black", "-frames:v", "1", out_png])
    return [round((first + i) / fps, 3) for i in range(n)]


def _fps(video):
    v = next(s for s in probe(video)["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    return float(num) / float(den)


def verify_export(path, fps=None, duration=None, width=None, height=None, audio=True, tol_frames=1):
    """Check the *decoded final file*, not the project: codec, pix_fmt, size, fps, real frame count,
    duration, audio stream present and not silent. Returns {"facts": {...}, "checks": [(name, ok, detail)]}.
    Passing this proves the container is right — not that the edit looks or sounds good."""
    r = run([FFPROBE, "-v", "error", "-count_frames", "-show_entries",
             "format=duration:stream=codec_type,codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames,"
             "sample_rate,channels", "-of", "json", path])
    info = json.loads(r.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    num, den = v["r_frame_rate"].split("/")
    facts = {"codec": v["codec_name"], "pix_fmt": v.get("pix_fmt"), "width": v["width"], "height": v["height"],
             "fps": round(float(num) / float(den), 3), "frames": int(v.get("nb_read_frames", 0)),
             "duration": round(float(info["format"]["duration"]), 3),
             "audio": a["codec_name"] if a else None}
    if a:
        vd = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af", "volumedetect",
                             "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        mx = [l for l in vd.stderr.splitlines() if "max_volume" in l]
        facts["audio_max_db"] = float(mx[-1].split(":")[1].split()[0]) if mx else None
    checks = [("h264/hevc", facts["codec"] in ("h264", "hevc"), facts["codec"]),
              ("yuv420p", facts["pix_fmt"] == "yuv420p", facts["pix_fmt"])]
    if width and height:
        checks.append(("size", (facts["width"], facts["height"]) == (width, height),
                       f'{facts["width"]}x{facts["height"]}'))
    if fps:
        checks.append(("fps", abs(facts["fps"] - fps) < 0.01, facts["fps"]))
    if duration and fps:
        want = round(duration * fps)
        checks.append(("frame count", abs(facts["frames"] - want) <= tol_frames, f'{facts["frames"]} vs {want}'))
    if audio:
        checks.append(("audio stream", a is not None, facts["audio"]))
        if a:
            loud = facts.get("audio_max_db") is not None and facts["audio_max_db"] > -50
            checks.append(("audio not silent", loud, facts.get("audio_max_db")))
    return {"facts": facts, "checks": checks}

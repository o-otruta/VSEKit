"""yt-dlp wrapper: download reference videos / audio and read their metadata.

Respect copyright: downloaded videos are for analysis and reference. Reuse in your own videos
only what is licensed for it (CC-BY with attribution, public domain, your own uploads)."""
import json
import os
import subprocess
from .env import YTDLP, tool_env


def _run(args):
    r = subprocess.run([YTDLP, "--no-warnings", *args], capture_output=True, text=True, env=tool_env(),
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return r.stdout


def info(url):
    """Full metadata: title, channel, duration, license, chapters, view_count, tags, description ..."""
    return json.loads(_run(["-J", "--skip-download", url]))


def search(query, n=10):
    out = _run([f"ytsearch{n}:{query}", "--skip-download", "--flat-playlist", "-J"])
    return [{"id": e["id"], "title": e.get("title"), "duration": e.get("duration"), "channel": e.get("channel")}
            for e in json.loads(out).get("entries", [])]


def video(url, out_dir, name="%(id)s", max_height=1080, subs=True):
    os.makedirs(out_dir, exist_ok=True)
    args = ["-f", f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/b[height<={max_height}]",
            "--merge-output-format", "mp4", "-o", os.path.join(out_dir, name + ".%(ext)s"), "--write-thumbnail",
            "--convert-thumbnails", "jpg", "--write-info-json"]
    if subs:
        args += ["--write-subs", "--write-auto-subs", "--sub-langs", "en.*,ru.*,uk.*", "--sub-format", "vtt"]
    _run(args + [url])


def audio(url, out_dir, name="%(id)s", fmt="wav"):
    os.makedirs(out_dir, exist_ok=True)
    _run(["-x", "--audio-format", fmt, "-o", os.path.join(out_dir, name + ".%(ext)s"), url])

"""Tool discovery. Nothing machine-specific is hard-coded: every path is found via an environment
variable override, PATH, or the usual install locations. `python -m vsekit.env` prints what was found;
`python -m vsekit.env blender` prints a single path (used by shell scripts).

Overrides (set as user env vars if auto-detection picks the wrong thing):
    VSEKIT_ROOT, VSEKIT_BLENDER, VSEKIT_FFMPEG_DIR, VSEKIT_DENO
"""
import glob
import os
import shutil
import sys

_HOME = os.path.expanduser("~")
_LA = os.environ.get("LOCALAPPDATA", os.path.join(_HOME, "AppData", "Local"))
_APPDATA = os.environ.get("APPDATA", os.path.join(_HOME, "AppData", "Roaming"))

KIT_ROOT = os.environ.get("VSEKIT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(KIT_ROOT, "media")
FONTS = os.path.join(KIT_ROOT, "assets", "fonts")
FONT_TITLE = os.path.join(FONTS, "RussoOne-Regular.ttf")
FONT_BODY = os.path.join(FONTS, "Rubik-Bold.ttf")
SKILL_DIR = os.path.join(KIT_ROOT, "skill", "video-editing")


def _first(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _newest(pattern):
    hits = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return hits[0] if hits else None


def _steam_libraries():
    """Steam library roots from libraryfolders.vdf (Blender can live in any of them)."""
    import re
    roots = []
    for steam in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"):
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            roots.append(steam)
            txt = open(vdf, encoding="utf-8", errors="ignore").read()
            roots += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', txt)]
    return list(dict.fromkeys(roots))


def _find_blender():
    cands = [os.environ.get("VSEKIT_BLENDER"), shutil.which("blender")]
    cands += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
    cands += [os.path.join(lib, "steamapps", "common", "Blender", "blender.exe") for lib in _steam_libraries()]
    return _first(cands)


BLENDER = _find_blender()
BLENDER_DIR = os.path.dirname(BLENDER) if BLENDER else None
# Blender's bundled Python + version folder (e.g. ...\Blender\5.3\python\bin\python.exe)
BLENDER_PY = _newest(os.path.join(BLENDER_DIR, "*", "python", "bin", "python.exe")) if BLENDER_DIR else None
BLENDER_VERSION = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(BLENDER_PY)))) if BLENDER_PY else None
MODULES = (os.path.join(_APPDATA, "Blender Foundation", "Blender", BLENDER_VERSION, "scripts", "modules")
           if BLENDER_VERSION else None)   # Pillow/edge-tts for Blender's Python live here (survives updates)
BLENDER_MCP = (os.path.join(_APPDATA, "Blender Foundation", "Blender", BLENDER_VERSION, "extensions",
                            "lab_blender_org", "mcp") if BLENDER_VERSION else None)


def _find_ffmpeg_dir():
    d = os.environ.get("VSEKIT_FFMPEG_DIR")
    if d and os.path.exists(os.path.join(d, "ffmpeg.exe")):
        return d
    w = shutil.which("ffmpeg")
    if w:
        return os.path.dirname(w)
    hit = _newest(os.path.join(_LA, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    return os.path.dirname(hit) if hit else None


_FF = _find_ffmpeg_dir()
FFMPEG = os.path.join(_FF, "ffmpeg.exe") if _FF else "ffmpeg"
FFPROBE = os.path.join(_FF, "ffprobe.exe") if _FF else "ffprobe"
WINGET_LINKS = os.path.join(_LA, "Microsoft", "WinGet", "Links")
DENO = (os.environ.get("VSEKIT_DENO") or shutil.which("deno") or _first([os.path.join(WINGET_LINKS, "deno.exe")])
        or _newest(os.path.join(_LA, "Microsoft", "WinGet", "Packages", "DenoLand.Deno*", "deno.exe")))
UV = shutil.which("uv") or _newest(os.path.join(_LA, "Programs", "Python", "Python*", "Scripts", "uv.exe")) \
    or _first([os.path.join(_HOME, ".local", "bin", "uv.exe")])

VENV_PY = os.path.join(KIT_ROOT, ".venv", "Scripts", "python.exe")         # whisper, librosa, kokoro, ...
VENV_DF_PY = os.path.join(KIT_ROOT, ".venv-df", "Scripts", "python.exe")   # DeepFilterNet (old numpy/torch)
YTDLP = os.path.join(KIT_ROOT, ".venv", "Scripts", "yt-dlp.exe")
REALESRGAN = os.path.join(KIT_ROOT, "tools", "realesrgan", "realesrgan-ncnn-vulkan.exe")


def tool_env():
    """Environment with ffmpeg + deno on PATH (for subprocesses like yt-dlp)."""
    e = dict(os.environ)
    extra = [p for p in (_FF, os.path.dirname(DENO) if DENO else None, WINGET_LINKS) if p]
    e["PATH"] = os.pathsep.join(extra + [e.get("PATH", "")])
    return e


SUMMARY = {
    "kit_root": KIT_ROOT, "blender": BLENDER, "blender_py": BLENDER_PY, "blender_version": BLENDER_VERSION,
    "blender_modules": MODULES, "ffmpeg": FFMPEG, "ffprobe": FFPROBE, "deno": DENO, "uv": UV,
    "venv_py": VENV_PY, "venv_df_py": VENV_DF_PY, "ytdlp": YTDLP, "realesrgan": REALESRGAN, "fonts": FONTS,
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(SUMMARY.get(sys.argv[1]) or "")
    else:
        for k, v in SUMMARY.items():
            print(f"{k:16s} {v}")

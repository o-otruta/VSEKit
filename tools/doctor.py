"""VSEKit environment check. Run with any Python (preferably .venv):  python tools/doctor.py
Prints one line per component (OK / MISSING / WARN) and exits 1 if a required piece is missing.
Claude: run this first in a new environment; if anything required is missing, offer `setup.ps1`."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from vsekit import env as E  # noqa: E402

rows, missing = [], 0


def check(name, ok, detail="", required=True):
    global missing
    status = "OK" if ok else ("MISSING" if required else "WARN")
    if not ok and required:
        missing += 1
    rows.append((status, name, detail))


def run(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


# core binaries
check("Blender", bool(E.BLENDER), f"{E.BLENDER} (v{E.BLENDER_VERSION})")
code, out = run([E.FFMPEG, "-hide_banner", "-encoders"]) if E.FFMPEG else (1, "")
check("ffmpeg", code == 0, E.FFMPEG)
check("ffmpeg NVENC (h264_nvenc)", "h264_nvenc" in out, "falls back to libx264 if missing", required=False)
check("deno (yt-dlp JS runtime)", bool(E.DENO), str(E.DENO))
check("uv", bool(E.UV), str(E.UV), required=False)
check("Real-ESRGAN", os.path.exists(E.REALESRGAN), E.REALESRGAN, required=False)
check("Fonts", all(os.path.exists(p) for p in (E.FONT_TITLE, E.FONT_BODY)), E.FONTS)

# main venv
probe = r"""
import json, importlib
mods = ['faster_whisper','librosa','scenedetect','cv2','kokoro','soundfile','opentimelineio','yt_dlp','PIL','edge_tts','en_core_web_sm','playwright']
res = {}
for m in mods:
    try:
        mod = importlib.import_module(m); res[m] = getattr(mod, '__version__', 'ok')
    except Exception as e:
        res[m] = 'ERR ' + str(e)[:60]
try:
    import torch; res['torch'] = torch.__version__; res['cuda'] = torch.cuda.is_available()
except Exception as e:
    res['torch'] = 'ERR ' + str(e)[:60]; res['cuda'] = False
print('JSON>>' + json.dumps(res))
"""
if os.path.exists(E.VENV_PY):
    code, out = run([E.VENV_PY, "-c", probe], timeout=180)
    try:   # torch prints warnings to stderr; take only our marked line
        res = json.loads(next(l for l in out.splitlines() if l.startswith("JSON>>"))[6:])
    except Exception:  # noqa: BLE001
        res = {}
        check(".venv imports", False, out[-200:])
    for k, v in res.items():
        if k == "cuda":
            check("torch CUDA", bool(v), "GPU whisper/kokoro (CPU works, slower)", required=False)
        else:
            check(f".venv {k}", not str(v).startswith("ERR"), str(v), required=k not in ("kokoro", "torch", "playwright"))
else:
    check(".venv", False, "run setup.ps1")

# headless Chromium for html_motion
if os.path.exists(E.VENV_PY):
    code, out = run([E.VENV_PY, "-c", "from playwright.sync_api import sync_playwright as s; p=s().start(); "
                     "b=p.chromium.launch(); print(b.version); b.close(); p.stop()"], timeout=60)
    check("Chromium (html_motion)", code == 0, out.strip()[-80:] if code == 0 else "python -m playwright install chromium --only-shell",
          required=False)

# DeepFilterNet venv
if os.path.exists(E.VENV_DF_PY):
    code, out = run([E.VENV_DF_PY, "-c", "import df; print('ok')"], timeout=120)
    check(".venv-df DeepFilterNet", code == 0, out[-80:], required=False)
else:
    check(".venv-df DeepFilterNet", False, "run setup.ps1 (optional)", required=False)

# Blender side
if E.BLENDER_PY and E.MODULES:
    code, out = run([E.BLENDER_PY, "-c", f"import sys; sys.path.insert(0, r'{E.MODULES}'); import PIL, edge_tts; print('ok')"])
    check("Blender Python: Pillow + edge-tts", code == 0, E.MODULES, required=False)
check("Blender MCP extension", bool(E.BLENDER_MCP and os.path.isdir(E.BLENDER_MCP)), str(E.BLENDER_MCP), required=False)

# skill link
link = os.path.join(os.path.expanduser("~"), ".claude", "skills", "video-editing")
linked = os.path.isdir(link) and os.path.exists(os.path.join(link, "SKILL.md"))
same = linked and os.path.realpath(link) == os.path.realpath(E.SKILL_DIR)
check("Claude skill installed", linked, link)
check("Skill points to this repo", same, f"-> {os.path.realpath(link) if linked else '-'}", required=False)
check("VSEKIT_ROOT env var", os.environ.get("VSEKIT_ROOT") is not None, os.environ.get("VSEKIT_ROOT", "not set"),
      required=False)

w = max(len(r[1]) for r in rows)
for status, name, detail in rows:
    print(f"{status:8s} {name:{w}s}  {detail}")
print(f"\n{'All required components present.' if not missing else f'{missing} required component(s) missing -> run setup.ps1'}")
sys.exit(1 if missing else 0)

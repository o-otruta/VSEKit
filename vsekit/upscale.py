"""Image/frame upscaling with Real-ESRGAN (ncnn-vulkan build, runs on the GPU, no Python deps)."""
import os
import subprocess
from .env import REALESRGAN

MODELS = {
    "photo": ("realesrgan-x4plus", 4),          # real photos / game renders
    "anime": ("realesrgan-x4plus-anime", 4),    # flat art, UI, pixel-ish
    "video2": ("realesr-animevideov3", 2),      # fast, x2, flat content & video frames
}


def upscale(src, dst, kind="photo", tile=0):
    name, scale = MODELS[kind]
    args = [REALESRGAN, "-i", src, "-o", dst, "-n", name, "-s", str(scale), "-f", "png"]
    if tile:
        args += ["-t", str(tile)]
    r = subprocess.run(args, capture_output=True, text=True, cwd=os.path.dirname(REALESRGAN))
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(r.stderr[-1500:])
    return dst

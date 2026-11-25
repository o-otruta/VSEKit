"""Voice clean-up: DeepFilterNet (neural, isolated venv) and a classic ffmpeg voice chain."""
import os
import subprocess
from .env import FFMPEG, VENV_DF_PY
from .media import run

_DF_SCRIPT = r"""
import sys, torch
from df.enhance import enhance, init_df, load_audio, save_audio
model, state, _ = init_df()
audio, _ = load_audio(sys.argv[1], sr=state.sr())
out = enhance(model, state, audio, atten_lim_db=float(sys.argv[3]) if len(sys.argv) > 3 else None)
save_audio(sys.argv[2], out, state.sr())
"""


def deepfilter(src, dst, atten_lim_db=None):
    """Neural noise suppression (48 kHz). atten_lim_db limits how much noise is removed (e.g. 18 keeps some room tone)."""
    tmp = dst + ".in.wav"
    run([FFMPEG, "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "48000", tmp])
    args = [VENV_DF_PY, "-c", _DF_SCRIPT, tmp, dst] + ([str(atten_lim_db)] if atten_lim_db else [])
    r = subprocess.run(args, capture_output=True, text=True)
    os.remove(tmp)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-1500:])
    return dst


VOICE_CHAIN = ("highpass=f=80,lowpass=f=14000,"
               "afftdn=nr=12:nf=-35:tn=1,"                       # spectral denoise (classic)
               "equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.0:g=3,"  # less mud, more presence
               "acompressor=threshold=-20dB:ratio=3:attack=10:release=120:makeup=4,"
               "alimiter=limit=0.95")


def voice_chain(src, dst, chain=VOICE_CHAIN):
    """Classic podcast-style chain with ffmpeg filters (fast, no ML)."""
    run([FFMPEG, "-y", "-v", "error", "-i", src, "-af", chain, "-ar", "48000", dst])
    return dst


def silence_ranges(src, noise_db=-35, min_s=0.5):
    """ffmpeg silencedetect -> [(start, end)] (useful without a transcript)."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", src, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out, st = [], None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            st = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and st is not None:
            out.append((st, float(line.split("silence_end:")[1].split()[0]))); st = None
    return out

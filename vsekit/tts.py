"""Text-to-speech engines with a common interface.

    edge   - Microsoft neural voices via edge-tts (online: text is sent to Microsoft). Word timings built in.
    kokoro - Kokoro-82M, local neural TTS on GPU/CPU (VENV_PY). Timings via whisper alignment.
    sapi   - Windows built-in SAPI voices (offline, robotic). Timings via whisper alignment.

`synth(...)` returns a list of words [{'text','start','end'}] and writes audio to `out` (.mp3 for edge,
.wav otherwise). Use `align(...)` (whisper) to get word timings for engines that don't provide them.
"""
import asyncio
import json
import os
import subprocess

DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"


# ------------------------------------------------------------------ edge-tts
async def _edge(text, out_mp3, voice, rate, pitch):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(out_mp3, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7
                words.append({"text": ch["text"], "start": st, "end": st + ch["duration"] / 1e7})
    return words


def synth(text, out_mp3, voice=DEFAULT_VOICE, rate="+0%", pitch="+0Hz", cache=True):
    """edge-tts (kept as the default for backwards compatibility)."""
    meta = out_mp3 + ".json"
    key = {"engine": "edge", "text": text, "voice": voice, "rate": rate, "pitch": pitch}
    if cache and os.path.exists(out_mp3) and os.path.exists(meta):
        d = json.load(open(meta, encoding="utf-8"))
        if d.get("key") in (key, {k: v for k, v in key.items() if k != "engine"}):
            return d["words"]
    words = asyncio.run(_edge(text, out_mp3, voice, rate, pitch))
    json.dump({"key": key, "words": words}, open(meta, "w", encoding="utf-8"), indent=1)
    return words


# ------------------------------------------------------------------ Kokoro (local)
_kokoro = {}


def kokoro(text, out_wav, voice="am_michael", speed=1.0, lang="a"):
    """Local neural TTS. Voices: af_heart, af_bella, am_michael, am_fenrir, bm_george, bf_emma ...
    lang: 'a' US English, 'b' UK English (others need extra phonemizers)."""
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    if lang not in _kokoro:
        _kokoro[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    chunks = [r.audio.cpu().numpy() if hasattr(r.audio, "cpu") else np.asarray(r.audio)
              for r in _kokoro[lang](text, voice=voice, speed=speed)]
    audio = np.concatenate(chunks) if chunks else np.zeros(1)
    sf.write(out_wav, audio, 24000)
    return out_wav


# ------------------------------------------------------------------ Windows SAPI (offline)
def sapi(text, out_wav, voice="Microsoft David Desktop", rate=0):
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SelectVoice('{voice}'); $s.Rate = {int(rate)}; $s.SetOutputToWaveFile('{out_wav}'); "
          f"$s.Speak([Console]::In.ReadToEnd()); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)
    return out_wav


# ------------------------------------------------------------------ alignment
def align(audio_path, language="en"):
    """Word timings for any audio via whisper (needs VENV_PY)."""
    from . import transcribe as T
    return [{"text": w["text"], "start": w["start"], "end": w["end"]}
            for w in T.words(T.transcribe(audio_path, language=language))]

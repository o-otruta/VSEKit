"""A/B demos: TTS shootout, voice denoise, upscaling.  Usage: python comparisons.py [tts|denoise|upscale|all]"""
import json
import os
import sys
import time

import numpy as np
from common import *  # noqa
from vsekit import tts as TT, transcribe as T, denoise as DN, upscale as UP, audio as A

RESULTS = os.path.join(OUT, "results.json")
results = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}


def save_results():
    json.dump(results, open(RESULTS, "w"), indent=1)


# ================================================================== TTS shootout
SCRIPT = ("Hey! I'm building a voxel survivor game, completely solo. Today I'm testing four different voices, "
          "so tell me in the comments which one sounds the most human.")


def demo_tts():
    d = os.path.join(WORK, "tts"); os.makedirs(d, exist_ok=True)
    engines = [
        ("Windows SAPI · David", "offline · built into Windows", lambda o: TT.sapi(SCRIPT, o)),
        ("edge-tts · Andrew", "online · Microsoft neural (text is sent to MS)",
         lambda o: (TT.synth(SCRIPT, o[:-4] + ".mp3"), ff("-i", o[:-4] + ".mp3", "-ar", "48000", o))),
        ("Kokoro · am_michael", "local · 82M model on RTX 3080", lambda o: TT.kokoro(SCRIPT, o, "am_michael")),
        ("Kokoro · af_heart", "local · 82M model on RTX 3080", lambda o: TT.kokoro(SCRIPT, o, "af_heart")),
    ]
    TT.kokoro("warm up", os.path.join(d, "_warm.wav"))   # exclude model load from timing
    parts = []
    intro = card("TTS shootout", ["Same script, four engines.", "Synthesis time + Whisper word-error-rate",
                                  "(lower WER = clearer speech)."], tag="VSEKIT DEMO")
    intro.save(os.path.join(d, "intro.png")); still(os.path.join(d, "intro.png"), 3.5, os.path.join(d, "intro.mp4"))
    parts.append(os.path.join(d, "intro.mp4"))
    rows = []
    for i, (name, note, fn) in enumerate(engines):
        wav = os.path.join(d, f"e{i}.wav")
        t0 = time.time(); fn(wav); dt = time.time() - t0
        wav48 = os.path.join(d, f"e{i}_48k.wav"); ff("-i", wav, "-ar", "48000", "-ac", "2", wav48)
        from vsekit.media import duration
        dur = duration(wav48)
        hyp = T.text(T.transcribe(wav48, language="en", cache=False))
        e = wer(SCRIPT, hyp)
        rows.append({"engine": name, "synth_s": round(dt, 2), "audio_s": round(dur, 2), "wer": round(e, 3), "heard": hyp})
        wf = waveform(wav48, os.path.join(d, f"wf{i}.png"))
        c = card(name, [note, f"synthesis {dt:.1f}s for {dur:.1f}s of audio  ·  WER {e * 100:.0f}%"],
                 tag=f"VOICE {i + 1}/4", extra=wf, extra_xy=(160, 620))
        c.save(os.path.join(d, f"c{i}.png"))
        still_with_audio(os.path.join(d, f"c{i}.png"), wav48, os.path.join(d, f"s{i}.mp4"), pad=0.8)
        parts.append(os.path.join(d, f"s{i}.mp4"))
    concat(parts, os.path.join(OUT, "03_tts_shootout.mp4"))
    results["tts"] = rows; save_results()


# ================================================================== denoise
def demo_denoise():
    d = os.path.join(WORK, "denoise"); os.makedirs(d, exist_ok=True)
    clean = os.path.join(d, "clean.wav")
    ff("-ss", "12", "-t", "8", "-i", os.path.join(MEDIA, "src", "nasa_expert.mp4"), "-ac", "1", "-ar", "48000", clean)
    x, sr = A.read_wav(clean); x = x[:, 0]
    n = x.size; t = np.arange(n) / sr
    rng = np.random.default_rng(5)
    white = rng.standard_normal(n)
    pink = np.cumsum(white); pink = A.hp_fast(pink, 60); pink /= np.abs(pink).max()     # brown-ish fan rumble
    hum = sum(np.sin(2 * np.pi * 50 * k * t) / k for k in (1, 2, 3, 5))                  # mains hum
    clicks = np.zeros(n)
    for c in rng.integers(0, n - 2000, 40):                                                # keyboard clicks
        clicks[c:c + 600] += rng.standard_normal(600) * np.exp(-np.arange(600) / 80)
    noise = pink * 0.6 + hum * 0.25 + clicks * 0.5 + white * 0.15
    rms = lambda v: np.sqrt(np.mean(v ** 2))
    noise *= rms(x) / rms(noise) / (10 ** (3 / 20))                                        # SNR 3 dB
    noisy = os.path.join(d, "noisy.wav"); A.write_wav(noisy, np.clip(x + noise, -1, 1), sr)
    chain = DN.voice_chain(noisy, os.path.join(d, "chain.wav"))
    t0 = time.time(); dfn = DN.deepfilter(noisy, os.path.join(d, "deepfilter.wav")); t_df = time.time() - t0
    both = DN.voice_chain(dfn, os.path.join(d, "deepfilter_chain.wav"),
                          chain=DN.VOICE_CHAIN.replace("afftdn=nr=12:nf=-35:tn=1,", ""))
    variants = [("Clean original", "reference (NASA narration)", clean),
                ("Noisy · SNR 3 dB", "fan rumble + 50 Hz hum + keyboard clicks", noisy),
                ("ffmpeg voice chain", "highpass + afftdn + EQ + compressor (no ML)", chain),
                ("DeepFilterNet", f"neural, CPU · {t_df:.1f}s for 8s audio", dfn),
                ("DeepFilterNet + chain", "neural denoise, then EQ + compressor", both)]
    parts = []
    intro = card("Voice clean-up", ["Same 8 seconds, five versions.", "Watch the spectrogram: noise = fog,",
                                    "speech = bright strokes."], tag="VSEKIT DEMO")
    intro.save(os.path.join(d, "intro.png")); still(os.path.join(d, "intro.png"), 3.5, os.path.join(d, "intro.mp4"))
    parts.append(os.path.join(d, "intro.mp4"))
    for i, (name, note, wav) in enumerate(variants):
        sp = spectrogram(wav, os.path.join(d, f"sp{i}.png"))
        c = card(name, [note], tag=f"{i + 1}/5", extra=sp, extra_xy=(160, 520))
        c.save(os.path.join(d, f"c{i}.png"))
        w48 = os.path.join(d, f"v{i}_st.wav"); ff("-i", wav, "-ar", "48000", "-ac", "2", w48)
        still_with_audio(os.path.join(d, f"c{i}.png"), w48, os.path.join(d, f"s{i}.mp4"), pad=0.6)
        parts.append(os.path.join(d, f"s{i}.mp4"))
    concat(parts, os.path.join(OUT, "04_voice_denoise.mp4"))
    results["denoise"] = {"deepfilter_cpu_s_for_8s": round(t_df, 2)}; save_results()


# ================================================================== upscale
def demo_upscale():
    d = os.path.join(WORK, "upscale"); os.makedirs(d, exist_ok=True)
    src = os.path.join(PROJECTB, "Screenshots", "Sprint13", "after_abilities_9x16.png")
    base = Image.open(src).convert("RGB"); W2, H2 = base.width * 2, base.height * 2
    outs = {"Lanczos (Pillow)": base.resize((W2, H2), Image.LANCZOS)}
    times = {}
    for label, kind in (("Real-ESRGAN x4plus", "photo"), ("Real-ESRGAN anime", "anime"), ("Real-ESRGAN animevideo x2", "video2")):
        p = os.path.join(d, f"{kind}.png")
        t0 = time.time(); UP.upscale(src, p, kind); times[label] = round(time.time() - t0, 2)
        outs[label] = Image.open(p).convert("RGB").resize((W2, H2), Image.LANCZOS)
    for k, im in outs.items():
        im.save(os.path.join(d, k.split()[0].lower() + "_" + str(abs(hash(k)) % 1000) + ".png"))
    # 4 columns, each a 3x zoom window panning over the screenshot's text-heavy area
    fps, secs = 30, 9
    cw, ch, zoom = 470, 900, 3
    frames = os.path.join(d, "frames"); os.makedirs(frames, exist_ok=True)
    path = [(560, 330), (380, 760), (560, 1150)]          # in 2x image px
    labels = list(outs.keys())
    for f in range(fps * secs):
        u = f / (fps * secs - 1)
        seg = min(int(u * (len(path) - 1)), len(path) - 2); lu = u * (len(path) - 1) - seg
        lu = lu * lu * (3 - 2 * lu)
        cx = path[seg][0] + (path[seg + 1][0] - path[seg][0]) * lu
        cy = path[seg][1] + (path[seg + 1][1] - path[seg][1]) * lu
        frame = bg()
        for i, k in enumerate(labels):
            sw, sh = cw / zoom, ch / zoom
            box = (int(cx - sw / 2), int(cy - sh / 2), int(cx + sw / 2), int(cy + sh / 2))
            crop = outs[k].crop(box).resize((cw, ch), Image.NEAREST)
            x = 18 + i * (cw + 8)
            frame.paste(crop, (x, 150))
            text(frame, (x + cw / 2, 95), k, 30, YEL, FONT_B, "mm")
            if k in times:
                text(frame, (x + cw / 2, 1070), f"{times[k]}s on GPU", 24, (200, 200, 220, 255), FONT_B, "mb")
        text(frame, (960, 40), "Upscale 540x960 -> 1080x1920  ·  3x zoom on the result", 34, (255, 255, 255, 255), FONT_T, "mm")
        frame.convert("RGB").save(os.path.join(frames, f"{f:04d}.png"))
    ff("-framerate", str(fps), "-i", os.path.join(frames, "%04d.png"), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-shortest", "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p", "-c:a", "aac",
       os.path.join(OUT, "05_upscale_compare.mp4"))
    results["upscale"] = times; save_results()


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("tts", demo_tts), ("denoise", demo_denoise), ("upscale", demo_upscale)):
        if which in (name, "all"):
            t0 = time.time(); fn(); print(name, "done in", round(time.time() - t0, 1), "s")
    print(json.dumps(results, indent=1)[:3000])

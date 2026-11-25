"""Speech-to-text with word timings (faster-whisper, local GPU). Run with VENV_PY.

Nothing leaves the machine. First call downloads the model (~1.6 GB for large-v3-turbo)."""
import json
import os


def _cuda_dlls():
    """ctranslate2 on Windows needs cuBLAS/cuDNN DLLs; reuse the ones shipped inside torch."""
    import importlib.util
    spec = importlib.util.find_spec("torch")
    if spec and spec.origin:
        lib = os.path.join(os.path.dirname(spec.origin), "lib")
        if os.path.isdir(lib):
            os.add_dll_directory(lib)
            os.environ["PATH"] = lib + os.pathsep + os.environ.get("PATH", "")


def transcribe(path, model="large-v3-turbo", language=None, device="cuda", compute_type="float16",
               vad=True, initial_prompt=None, cache=True):
    """Returns {'language', 'duration', 'segments': [{start,end,text,words:[{text,start,end,prob}]}]}.
    Cached next to the media as <file>.whisper.json."""
    out = path + ".whisper.json"
    if cache and os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(path):
        return json.load(open(out, encoding="utf-8"))
    _cuda_dlls()
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device=device, compute_type=compute_type)
    # decode with our ffmpeg instead of PyAV (newer PyAV broke faster-whisper's decode_audio)
    import subprocess
    import numpy as np
    from .env import FFMPEG
    pcm = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.float32)
    segs, info = m.transcribe(audio, language=language, word_timestamps=True, vad_filter=vad,
                              initial_prompt=initial_prompt, beam_size=5)
    res = {"language": info.language, "duration": info.duration, "segments": []}
    for s in segs:
        res["segments"].append({
            "start": s.start, "end": s.end, "text": s.text.strip(),
            "words": [{"text": w.word.strip(), "start": w.start, "end": w.end, "prob": w.probability}
                      for w in (s.words or [])]})
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return res


def words(res):
    return [w for s in res["segments"] for w in s["words"]]


def text(res):
    return " ".join(s["text"] for s in res["segments"])


def _ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def to_srt(res, path, max_words=7, max_chars=42, offset=0.0):
    """Subtitle file with short, readable lines (good for YouTube/TikTok upload)."""
    cues, cur = [], []
    for w in words(res):
        cur.append(w)
        line = " ".join(x["text"] for x in cur)
        if len(cur) >= max_words or len(line) >= max_chars or w["text"][-1:] in ".?!":
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts(c[0]['start'] + offset)} --> {_ts(c[-1]['end'] + offset)}\n"
                    f"{' '.join(x['text'] for x in c)}\n\n")
    return len(cues)


FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm"}


def cut_list(res, min_gap=0.45, pad=0.08, drop_fillers=True, start=None, end=None):
    """Jump-cut plan: list of (in, out) source ranges to KEEP — speech with pauses > min_gap
    and filler words removed. `pad` keeps a little air around words."""
    ws = [w for w in words(res) if (start is None or w["start"] >= start) and (end is None or w["end"] <= end)]
    if drop_fillers:
        ws = [w for w in ws if w["text"].lower().strip(".,!?") not in FILLERS]
    keep = []
    for w in ws:
        a, b = max(0.0, w["start"] - pad), w["end"] + pad
        if keep and a - keep[-1][1] <= min_gap:
            keep[-1][1] = max(keep[-1][1], b)
        else:
            keep.append([a, b])
    return [tuple(k) for k in keep]


def chapters(res, every_s=60.0):
    """Naive chapter markers: first sentence starting after each `every_s` boundary."""
    out, nxt = [], 0.0
    for s in res["segments"]:
        if s["start"] >= nxt:
            out.append((s["start"], s["text"][:60]))
            nxt = s["start"] + every_s
    return out

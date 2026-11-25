"""Music analysis with librosa (run with VENV_PY): tempo, beats, downbeats, onsets, energy."""
import json
import os
import numpy as np


def analyze(path, cache=True):
    out = path + ".beats.json"
    if cache and os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(path):
        return json.load(open(out))
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beats = librosa.frames_to_time(beat_frames, sr=sr)
    env = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(env, sr=sr)
    # downbeats: the beat phase (0..3) whose beats carry the most onset energy
    strength = np.interp(beats, times, env)
    phase = int(np.argmax([strength[p::4].sum() for p in range(4)]))
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=sr, units="time", backtrack=False)
    rms = librosa.feature.rms(y=y)[0]
    res = {
        "tempo": float(np.atleast_1d(tempo)[0]),
        "duration": float(len(y) / sr),
        "beats": [float(b) for b in beats],
        "downbeats": [float(b) for b in beats[phase::4]],
        "onsets": [float(o) for o in onsets],
        "beat_strength": [float(s) for s in strength / (strength.max() + 1e-9)],
        "energy_t": [float(t) for t in librosa.times_like(rms, sr=sr)[::4]],
        "energy": [float(v) for v in (rms / (rms.max() + 1e-9))[::4]],
    }
    json.dump(res, open(out, "w"))
    return res


def strongest(res, n, min_gap=0.4, after=0.0, before=None):
    """Top-n beats by onset strength (for punch-ins / flashes), spaced at least min_gap apart."""
    cand = sorted(zip(res["beats"], res["beat_strength"]), key=lambda x: -x[1])
    out = []
    for t, s in cand:
        if t < after or (before is not None and t > before):
            continue
        if all(abs(t - o) >= min_gap for o in out):
            out.append(t)
        if len(out) >= n:
            break
    return sorted(out)


def loudest_section(res, length):
    """Start time of the most energetic `length`-second window (pick the drop / chorus)."""
    t = np.array(res["energy_t"]); e = np.array(res["energy"])
    dt = t[1] - t[0]
    k = max(1, int(length / dt))
    c = np.convolve(e, np.ones(k), "valid")
    return float(t[int(np.argmax(c))])

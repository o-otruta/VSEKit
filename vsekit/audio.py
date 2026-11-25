"""Procedural music and SFX with numpy. Everything is 48 kHz stereo float."""
import wave
import numpy as np

SR = 48000
_rng = np.random.default_rng(1234)


def write_wav(path, x, sr=SR):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    data = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data)


def read_wav(path):
    with wave.open(path, 'rb') as w:
        n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
        a = np.frombuffer(w.readframes(n), '<i2').astype(np.float64) / 32767
    a = a.reshape(-1, ch)
    if ch == 1:
        a = np.repeat(a, 2, 1)
    return a, sr


# ------------------------------------------------------------------ primitives
def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env_exp(n, decay_s, attack_s=0.002):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack_s, 1e-5)) * np.exp(-t / decay_s)


def onepole_lp(x, cutoff):
    """One-pole low-pass; cutoff may be scalar or per-sample array (Hz)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, np.float64), x.shape[:1])
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = np.zeros(x.shape[1:]) if x.ndim > 1 else 0.0
    for i in range(x.shape[0]):
        acc = a[i] * acc + (1 - a[i]) * x[i]
        y[i] = acc
    return y


def lp_fast(x, cutoff):
    """Static low-pass via FFT brick-ish rolloff (fast, for long signals)."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(x.shape[0], 1 / SR)
    g = 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X * (g[:, None] if x.ndim > 1 else g), n=x.shape[0], axis=0)


def hp_fast(x, cutoff):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(x.shape[0], 1 / SR)
    g = 1 / np.sqrt(1 + (cutoff / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * (g[:, None] if x.ndim > 1 else g), n=x.shape[0], axis=0)


def reverb(x, seconds=1.6, mix=0.25, damp=6000):
    """Cheap stereo convolution reverb with a decaying-noise impulse response."""
    n = int(SR * seconds)
    ir = _rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * (6.9 / seconds))[:, None]
    ir = lp_fast(ir, damp)
    ir /= np.sqrt((ir ** 2).sum(0))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    L = x.shape[0] + n
    nfft = 1 << (L - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, nfft, axis=0) * np.fft.rfft(ir, nfft, axis=0), nfft, axis=0)[:x.shape[0]]
    return x * (1 - mix) + wet * mix


def place(buf, clip, t0):
    """Mix `clip` into `buf` at time t0 (seconds)."""
    i = int(round(t0 * SR))
    if i >= buf.shape[0]:
        return
    if clip.ndim == 1:
        clip = np.stack([clip, clip], 1)
    j = min(buf.shape[0], i + clip.shape[0])
    if i < 0:
        clip = clip[-i:]; i = 0
    buf[i:j] += clip[:j - i]


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# ------------------------------------------------------------------ instruments
def kick(dur=0.45):
    t = t_axis(dur)
    f = 45 + 110 * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(t.size, 0.22)
    s += _rng.standard_normal(t.size) * env_exp(t.size, 0.004) * 0.25
    return np.tanh(s * 1.8) * 0.9


def snare(dur=0.3):
    t = t_axis(dur)
    noise = hp_fast(_rng.standard_normal(t.size), 1500) * env_exp(t.size, 0.11)
    tone = np.sin(2 * np.pi * 185 * t) * env_exp(t.size, 0.05)
    return (noise * 0.7 + tone * 0.5) * 0.8


def hat(dur=0.08, open_=False):
    t = t_axis(0.3 if open_ else dur)
    return hp_fast(_rng.standard_normal(t.size), 7000) * env_exp(t.size, 0.12 if open_ else 0.025) * 0.35


def saw(freq, t, voices=1, detune=0.0):
    out = np.zeros_like(t)
    for v in range(voices):
        d = 1 + detune * (v - (voices - 1) / 2) / max(voices - 1, 1)
        ph = (freq * d * t + _rng.random()) % 1.0
        out += 2 * ph - 1
    return out / voices


def bass_note(freq, dur, drive=1.0):
    t = t_axis(dur)
    s = saw(freq, t) * 0.6 + np.sin(2 * np.pi * freq * t) * 0.6
    s = onepole_lp(s, 300 + 1800 * np.exp(-t * 14)) * env_exp(t.size, dur * 0.9, 0.004)
    return np.tanh(s * 2.2 * drive) * 0.55


def pluck(freq, dur=0.35):
    t = t_axis(dur)
    s = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5 + saw(freq * 2, t) * 0.3
    return onepole_lp(s, 900 + 5000 * np.exp(-t * 22)) * env_exp(t.size, 0.12) * 0.32


def pad_chord(freqs, dur, cutoff=1400):
    t = t_axis(dur)
    s = sum(saw(f, t, voices=3, detune=0.012) for f in freqs) / len(freqs)
    att = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.5)
    s = lp_fast(s * att, cutoff)
    return np.stack([s, np.roll(s, 240)], 1) * 0.28


# ------------------------------------------------------------------ SFX
def sfx_whoosh(dur=0.45, f0=300, f1=5000, pan=True):
    n = int(SR * dur); tt = np.arange(n) / n
    env = np.sin(np.pi * tt) ** 1.5
    cut = f0 + (f1 - f0) * np.sin(np.pi * tt)
    y = onepole_lp(onepole_lp(_rng.standard_normal(n), cut), cut) * env
    y /= np.abs(y).max() + 1e-9
    if pan:
        return np.stack([y * np.cos(tt * np.pi / 2), y * np.sin(tt * np.pi / 2)], 1) * 0.6
    return np.stack([y, y], 1) * 0.6


def sfx_riser(dur=3.5):
    n = int(SR * dur); tt = np.arange(n) / n
    noise = onepole_lp(_rng.standard_normal(n), 200 + 9000 * tt ** 2)
    f = 120 + 900 * tt ** 2.2
    tone = saw(1, np.cumsum(f) / SR) * 0.3
    y = (noise * 0.8 + tone) * tt ** 2
    return reverb(y / (np.abs(y).max() + 1e-9) * 0.6, 1.2, 0.3)


def sfx_impact(dur=2.2):
    t = t_axis(dur)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-t * 8)) / SR) * env_exp(t.size, 0.7)
    crack = hp_fast(_rng.standard_normal(t.size), 800) * env_exp(t.size, 0.06)
    y = np.tanh((sub * 1.2 + crack * 0.6) * 1.5)
    return reverb(y * 0.85, 2.2, 0.3)


def sfx_glitch(dur=0.5):
    n = int(SR * dur); y = np.zeros(n)
    i = 0
    while i < n:
        seg = int(_rng.integers(SR // 120, SR // 25))
        f = _rng.choice([80, 220, 440, 880, 1760, 3520]) * _rng.uniform(0.9, 1.1)
        t = np.arange(min(seg, n - i)) / SR
        kind = _rng.integers(3)
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * f * t))
        elif kind == 1:
            s = _rng.standard_normal(t.size)
        else:
            s = np.zeros(t.size)
        y[i:i + t.size] = s * _rng.uniform(0.2, 0.7)
        i += seg
    y = np.round(y * 6) / 6  # bitcrush
    return np.stack([y, np.roll(y, 120)], 1) * 0.45


def sfx_pop(f0=500, f1=1400, dur=0.12):
    t = t_axis(dur)
    s = np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, t.size)) / SR) * env_exp(t.size, 0.04)
    return s * 0.6


def sfx_ding(freq=1568, dur=0.9):
    t = t_axis(dur)
    s = (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t)) * env_exp(t.size, 0.3)
    return reverb(s * 0.4, 1.0, 0.25)


def sfx_tick():
    t = t_axis(0.03)
    return np.sin(2 * np.pi * 2400 * t) * env_exp(t.size, 0.006) * 0.35


# ------------------------------------------------------------------ track
def make_track(bpm, sections, total_s, progression):
    """sections: list of (start_beat, end_beat, style) with style in
    {'intro','main','heavy','break','outro'}; progression: list of (root_midi, chord_midis) per bar."""
    beat = 60 / bpm
    buf = np.zeros((int(SR * total_s), 2))
    drums = np.zeros_like(buf); bass = np.zeros_like(buf); keys = np.zeros_like(buf); pads = np.zeros_like(buf)
    K, S, H, HO = kick(), snare(), hat(), hat(open_=True)
    for b0, b1, style in sections:
        for b in range(b0, b1):
            t = b * beat
            bar = b // 4
            root, chord = progression[bar % len(progression)]
            if b % 4 == 0 and style != 'outro':
                place(pads, pad_chord([midi(n) for n in chord], beat * 4, 900 if style == 'intro' else 1500), t)
            if style in ('main', 'heavy'):
                place(drums, K, t)
                if b % 2 == 1:
                    place(drums, S * (1.15 if style == 'heavy' else 1), t)
                for e in range(2):
                    place(drums, (HO if (e == 1 and b % 4 == 3) else H) * (0.7 + 0.3 * e), t + e * beat / 2)
                for e in range(2):
                    place(bass, bass_note(midi(root), beat / 2 * 0.95, 1.8 if style == 'heavy' else 1.0), t + e * beat / 2)
                if style == 'main':
                    arp = chord + [chord[0] + 12]
                    for e in range(2):
                        place(keys, pluck(midi(arp[(b * 2 + e) % len(arp)] + 12)), t + e * beat / 2)
            elif style == 'break':
                if b % 2 == 0:
                    place(drums, K * 0.8, t)
                place(drums, H * 0.6, t + beat / 2)
    # sidechain-ish ducking of bass/pads on every main-section kick
    duck = np.ones(buf.shape[0])
    for b0, b1, style in sections:
        if style in ('main', 'heavy'):
            for b in range(b0, b1):
                i = int(b * beat * SR); n = int(0.18 * SR)
                if i < duck.size:
                    seg = 1 - 0.55 * np.exp(-np.arange(min(n, duck.size - i)) / SR / 0.07)
                    duck[i:i + seg.size] = np.minimum(duck[i:i + seg.size], seg)
    bass *= duck[:, None]; pads *= duck[:, None]
    mix = drums * 0.9 + bass * 0.8 + reverb(keys, 1.4, 0.35) * 0.7 + reverb(pads, 2.0, 0.3)
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    return mix / (np.abs(mix).max() + 1e-9) * 0.89

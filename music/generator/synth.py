"""Small numpy synth: drums, 808, basses, pads, plucks, bells, and the effects/master chain."""
import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
import librosa
import pyloudnorm as pyln

SR = 44100
rng = np.random.default_rng(7)

NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
QUAL = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10]}
SCALES = {'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10]}


def parse_chord(ch):
    root = ch[:2] if len(ch) > 1 and ch[1] == '#' else ch[:1]
    return NOTE[root], QUAL[ch[len(root):]]


def chord_pcs(ch):
    r, q = parse_chord(ch)
    return [(r + i) % 12 for i in q]


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def sos(kind, f, order=2):
    return signal.butter(order, f, kind, fs=SR, output='sos')


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x, axis=-1)


def env(n, a=0.005, r=0.05, decay=0.0, sustain=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4))
    if decay:
        e = e * (sustain + (1 - sustain) * np.exp(-t * decay))
    rl = min(int(r * SR), n)
    if rl > 0:
        e[-rl:] *= np.linspace(1, 0, rl)
    return e


def saw(freq, n, phase0=0.0):
    dt = np.broadcast_to(np.asarray(freq, float) / SR, (n,))
    p = (phase0 + np.cumsum(dt)) % 1.0
    y = 2 * p - 1
    m = p < dt
    x = p[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = p > 1 - dt
    x = (p[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def sine(freq, n, phase0=0.0):
    dt = np.broadcast_to(np.asarray(freq, float) / SR, (n,))
    return np.sin(2 * np.pi * (phase0 + np.cumsum(dt)))


def put(buf, x, start):
    """Add mono (n,) or stereo (2,n) x into stereo buf at sample start."""
    if start >= buf.shape[1]:
        return
    if x.ndim == 1:
        x = np.vstack([x, x])
    end = min(buf.shape[1], start + x.shape[1])
    buf[:, start:end] += x[:, :end - start]


def pan(x, p):
    """p in [-1, 1], constant power."""
    a = (p + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)])


# ---------------- drums ----------------

def kick(dur=0.45, f_hi=170.0, f_lo=48.0, punch=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-t * 32)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    click = filt(rng.standard_normal(n), 'high', 1500) * np.exp(-t * 500) * 0.25
    return np.tanh(punch * (y + click)) / np.tanh(punch) * env(n, 0.001, 0.02)


def snare(dur=0.3, tone_hz=190.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * tone_hz * t) * np.exp(-t * 25) * 0.5
    nz = filt(rng.standard_normal(n), 'bandpass', [1200, 8000]) * np.exp(-t * 16)
    return np.tanh(1.5 * (tone + nz * 0.8))


def clap(dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.009, 0.019, 0.028)):
        tt = t - off
        e += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) * (180 if k < 3 else 14)), 0)
    return filt(rng.standard_normal(n), 'bandpass', [900, 4500]) * e * 0.9


def hat(open_=False):
    dur = 0.45 if open_ else 0.07
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = filt(rng.standard_normal(n), 'high', 7500, 4)
    return nz * np.exp(-t * (7 if open_ else 55)) * env(n, 0.0005, 0.01)


def crash():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    nz = filt(rng.standard_normal((2, n)), 'high', 5000, 2)
    return nz * np.exp(-t * 1.8) * 0.5


# ---------------- tonal ----------------

def b808(freq, dur, drive=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.6 * np.exp(-t * 28))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 0.9)
    y = np.tanh(drive * y) / np.tanh(drive)
    return y * env(n, 0.002, 0.04)


def synth_bass(freq, dur, cutoff=900, pluck=True):
    n = int(dur * SR)
    y = 0.7 * saw(freq, n, rng.random()) + 0.5 * np.sin(2 * np.pi * freq * np.arange(n) / SR)
    y = filt(y, 'low', cutoff, 2)
    return y * env(n, 0.003, 0.03, decay=5 if pluck else 0, sustain=0.55)


def supersaw_note(freq, dur, voices=7, detune=14, cutoff=3000, a=0.25, r=0.6):
    n = int(dur * SR)
    out = np.zeros((2, n))
    cents = np.linspace(-detune, detune, voices)
    for i, c in enumerate(cents):
        v = saw(freq * 2 ** (c / 1200), n, rng.random())
        side = -1 if i % 2 else 1
        w = 0.5 + 0.5 * side * (abs(c) / detune)
        out[0] += v * w
        out[1] += v * (1 - w)
    out /= voices / 2
    out = filt(out, 'low', cutoff, 2)
    return out * env(n, a, r)


def epiano(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    idx = 1.8 * np.exp(-t * 6)
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * t))
    y += 0.15 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 8)
    y *= np.exp(-t * 1.6) * (1 + 0.15 * np.sin(2 * np.pi * 5 * t))
    return y * env(n, 0.002, 0.08)


def bell(freq, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    idx = 2.2 * np.exp(-t * 4)
    y = np.sin(2 * np.pi * freq * t + idx * np.sin(2 * np.pi * freq * 3.5 * t))
    y += 0.3 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t * 5)
    return y * np.exp(-t * 2.6) * env(n, 0.001, 0.1)


def pluck(freq, dur=1.2, decay=0.996, bright=6000):
    n = int(dur * SR)
    N = max(2, int(round(SR / freq)))
    x = np.zeros(n)
    x[:N] = filt(rng.uniform(-1, 1, N), 'low', bright, 1)
    a = np.zeros(N + 2)
    a[0] = 1
    a[N] = a[N + 1] = -decay * 0.5
    y = signal.lfilter([1.0], a, x)
    return y / (np.max(np.abs(y)) + 1e-9) * env(n, 0.001, 0.05)


# ---------------- effects ----------------

_IR = {}


def reverb(x, dur=2.0, decay=3.2, lp=7000, predelay=0.02):
    key = (dur, decay, lp, predelay)
    if key not in _IR:
        n = int(dur * SR)
        t = np.arange(n) / SR
        r = np.random.default_rng(11)
        ir = r.standard_normal((2, n)) * np.exp(-t * decay)
        ir = filt(ir, 'low', lp, 1)
        pd = int(predelay * SR)
        ir = np.concatenate([np.zeros((2, pd)), ir], axis=1)
        ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
        _IR[key] = ir
    ir = _IR[key]
    if x.ndim == 1:
        x = np.vstack([x, x])
    out = np.vstack([signal.oaconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])
    return out * 0.5


def pingpong(x, delay_s, fb=0.45, repeats=6, lp=4000):
    if x.ndim == 2:
        x = x.mean(axis=0)
    x = filt(x, 'low', lp, 1)
    out = np.zeros((2, len(x)))
    d = int(delay_s * SR)
    for k in range(1, repeats + 1):
        if k * d >= len(x):
            break
        ch = (k + 1) % 2
        out[ch, k * d:] += x[:len(x) - k * d] * fb ** k
    return out


def chorus(x, depth=0.003, rate=0.8, base=0.012, mix=0.5):
    if x.ndim == 1:
        x = np.vstack([x, x])
    n = x.shape[1]
    t = np.arange(n) / SR
    out = np.empty_like(x)
    for c in range(2):
        d = (base + depth * np.sin(2 * np.pi * rate * t + c * np.pi / 2)) * SR
        out[c] = (1 - mix) * x[c] + mix * np.interp(np.arange(n) - d, np.arange(n), x[c], left=0)
    return out


def sidechain(n, kick_samples, depth=0.6, release=0.16):
    g = np.ones(n)
    rel = int(release * 4 * SR)
    curve = 1 - depth * np.exp(-np.arange(rel) / (release * SR))
    for s in kick_samples:
        e = min(n, s + rel)
        g[s:e] = np.minimum(g[s:e], curve[:e - s])
    return g


def lowpass_curve(x, fc_frames, n_fft=2048, hop=512, order=2):
    """Time-varying lowpass via STFT mask. fc_frames: cutoff (Hz) per STFT frame."""
    out = []
    freqs = librosa.fft_frequencies(sr=SR, n_fft=n_fft)
    for c in range(x.shape[0]):
        S = librosa.stft(x[c], n_fft=n_fft, hop_length=hop)
        fc = np.interp(np.arange(S.shape[1]), np.arange(len(fc_frames)), fc_frames)
        mask = 1 / np.sqrt(1 + (freqs[:, None] / fc[None, :]) ** (2 * order))
        out.append(librosa.istft(S * mask, hop_length=hop, length=x.shape[1]))
    return np.vstack(out)


def mono_below(x, f=150):
    mid = (x[0] + x[1]) / 2
    side = filt((x[0] - x[1]) / 2, 'high', f, 2)
    return np.vstack([mid + side, mid - side])


def true_peak_env(x, os=4):
    up = signal.resample_poly(x, os, 1, axis=1)
    pk = np.abs(up).max(axis=0)
    pk = pk[:x.shape[1] * os].reshape(-1, os).max(axis=1)
    return np.maximum(pk, np.abs(x).max(axis=0))


def limiter(x, ceiling_db=-1.3, look_ms=5.0):
    ceil = 10 ** (ceiling_db / 20)
    L = int(look_ms / 1000 * SR)
    peak = maximum_filter1d(true_peak_env(x), size=2 * L + 1)
    fast = np.minimum(1.0, ceil / (peak + 1e-12))
    fast = uniform_filter1d(minimum_filter1d(fast, size=2 * L + 1), size=L)
    rel = np.exp(-1 / (0.08 * SR))
    slow = signal.lfilter([1 - rel], [1, -rel], fast - 1) + 1
    y = x * np.minimum(fast, slow)
    over = true_peak_env(y).max() / ceil
    if over > 1:
        y /= over
    return y


def master(mix, target_lufs=-10.0, ceiling_db=-1.3):
    mix = filt(mix, 'high', 28, 2)
    mix = mono_below(mix, 140)
    meter = pyln.Meter(SR)
    gain_db = target_lufs - meter.integrated_loudness(mix.T)
    for _ in range(4):
        y = limiter(mix * 10 ** (gain_db / 20), ceiling_db)
        err = target_lufs - meter.integrated_loudness(y.T)
        if abs(err) < 0.15:
            break
        gain_db += err
    return y


def rms_db(x, mask=None):
    x = np.asarray(x)
    if x.ndim == 2:
        x = x.mean(axis=0)
    if mask is not None:
        x = x[mask]
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def tuned_hz(tonic_pc, target_hz):
    """Tonic or fifth of the key, in the octave closest to target_hz."""
    best = None
    for pc in (tonic_pc, (tonic_pc + 7) % 12):
        for octv in range(0, 9):
            f = float(hz(12 * octv + pc))
            if best is None or abs(np.log2(f / target_hz)) < abs(np.log2(best / target_hz)):
                best = f
    return best

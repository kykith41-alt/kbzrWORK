"""Russian TTS (Piper via sherpa-onnx) -> WORLD vocoder -> time-fit + hard autotune / whisper."""
import re
import numpy as np
import librosa
import pyworld as pw
import sherpa_onnx as so
from scipy import signal

from synth import SR, filt

FP = 5.0  # WORLD frame period, ms


class Voice:
    def __init__(self, models_dir, name):
        d = f"{models_dir}/vits-piper-ru_RU-{name}-medium"
        cfg = so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(
            vits=so.OfflineTtsVitsModelConfig(model=f"{d}/ru_RU-{name}-medium.onnx", tokens=f"{d}/tokens.txt",
                                              data_dir=f"{d}/espeak-ng-data"),
            num_threads=4))
        self.tts = so.OfflineTts(cfg)

    def say(self, text, speed=1.0):
        a = self.tts.generate(text, sid=0, speed=speed)
        y = np.array(a.samples, dtype=np.float64)
        y, _ = librosa.effects.trim(y, top_db=38)
        return y, a.sample_rate


def clean(text):
    t = re.sub(r'[«»"“”]', '', text)
    t = t.replace('—', ',').replace('…', '.').replace('?..', '?')
    t = re.sub(r'\s*,\s*,', ',', t)
    return re.sub(r'\s+', ' ', t).strip(' ,')


def _stretch_frames(arr, n_new):
    n = arr.shape[0]
    pos = np.linspace(0, n - 1, n_new)
    if arr.ndim == 1:
        return arr[np.round(pos).astype(int)]
    lo = np.floor(pos).astype(int)
    hi = np.minimum(lo + 1, n - 1)
    w = (pos - lo)[:, None]
    return arr[lo] * (1 - w) + arr[hi] * w


def tune(f0, frame_times, allowed_fn, center, spread=1.5, glide_ms=12, note_ms=200):
    """Hard-tune: map the speech contour around `center` (midi) and hold one allowed note per syllable
    (voiced run), splitting long runs into ~note_ms pieces."""
    v = f0 > 0
    if v.sum() < 3:
        return f0
    m_all = np.zeros_like(f0)
    m_all[v] = 69 + 12 * np.log2(f0[v] / 440.0)
    med = np.median(m_all[v])
    m_all[v] = center + spread * (m_all[v] - med)
    out = np.zeros_like(f0)
    edges = np.flatnonzero(np.diff(np.concatenate([[0], v.astype(int), [0]])))
    a = np.exp(-FP / glide_ms)
    prev = None
    for s, e in zip(edges[::2], edges[1::2]):
        if e - s < 2:
            continue
        pieces = max(1, int(round((e - s) * FP / note_ms)))
        cuts = np.linspace(s, e, pieces + 1).astype(int)
        steps = np.empty(e - s)
        for ps, pe in zip(cuts[:-1], cuts[1:]):
            target = np.median(m_all[ps:pe])
            allowed = allowed_fn(frame_times[(ps + pe) // 2])
            steps[ps - s:pe - s] = allowed[np.argmin(np.abs(allowed - target))]
        start = steps[0] if prev is None else prev
        sm = signal.lfilter([1 - a], [1, -a], steps - start) + start
        prev = steps[-1]
        out[s:e] = 440.0 * 2 ** ((sm - 69) / 12)
    return out


def render_line(voice, text, target_dur, mode, allowed_fn=None, center=57, spread=1.5, max_speed=1.6, min_speed=0.72):
    """Return mono vocal at SR whose length is <= target_dur (seconds)."""
    text = clean(text)
    y, sr = voice.say(text, 1.0)
    natural = len(y) / sr
    speed = float(np.clip(natural / target_dur, min_speed, max_speed))
    if abs(speed - 1) > 0.04:
        y, sr = voice.say(text, speed)
    x = np.ascontiguousarray(y)
    f0, t = pw.dio(x, sr, f0_floor=60, f0_ceil=500, frame_period=FP)
    f0 = pw.stonemask(x, f0, t, sr)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    n_target = int(target_dur * 1000 / FP)
    if len(f0) > n_target:
        f0, sp, ap = _stretch_frames(f0, n_target), _stretch_frames(sp, n_target), _stretch_frames(ap, n_target)
    times = np.arange(len(f0)) * FP / 1000
    if mode == 'sing':
        f0 = tune(f0, times, allowed_fn, center, spread)
    elif mode == 'whisper':
        f0 = np.zeros_like(f0)
    elif mode == 'spoken':
        v = f0 > 0
        if v.any():  # gently lower to sit under the music
            f0[v] *= 2 ** (-2 / 12)
    out = pw.synthesize(np.ascontiguousarray(f0), np.ascontiguousarray(sp), np.ascontiguousarray(ap), sr, FP)
    out = librosa.resample(out, orig_sr=sr, target_sr=SR)
    out = filt(out, 'high', 110 if mode != 'whisper' else 300, 2)
    out = out / (np.sqrt(np.mean(out ** 2)) + 1e-9) * 0.1
    return out

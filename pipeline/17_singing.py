"""Step 17: find singing / shouting / 'nieeeuw' moments in wind-heavy GoPro audio.
Voice = harmonic (pitched) sound: normalised autocorrelation peak at 80-700 Hz on a 250-3000 Hz band-passed
signal, 40 ms frames. Wind and ski hiss are noisy (low pitch strength). Output: singing.json + printout."""
import json, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import median_filter, uniform_filter1d
from common import SRC, FFMPEG, save_json, load_json
SR, FR = 16000, 640
def pitch_track(f):
    x = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-i", str(SRC / f), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                     capture_output=True).stdout, np.float32)
    x = sosfiltfilt(butter(4, [250, 3000], "bandpass", fs=SR, output="sos"), x)
    n = len(x) // FR; fr = x[: n * FR].reshape(n, FR) * np.hanning(FR)
    spec = np.fft.rfft(fr, 2 * FR, axis=1); ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :FR]
    ac = ac / (ac[:, :1] + 1e-9)
    lo, hi = SR // 700, SR // 80
    k = lo + np.argmax(ac[:, lo:hi], 1); ps = ac[np.arange(n), k]
    db = 10 * np.log10((fr ** 2).mean(1) + 1e-12)
    return ps, db, SR / k
out = {}
for f in sys.argv[1:]:
    ps, db, f0 = pitch_track(f)
    t = np.arange(len(ps)) * FR / SR
    rel = db - median_filter(db, 151)
    voiced = (uniform_filter1d(ps, 5) > 0.55) & (rel > 0)
    voiced = median_filter(voiced.astype(np.uint8), 5).astype(bool)
    m = np.concatenate([[0], voiced, [0]]).astype(int); d = np.diff(m)
    runs = [(a, b) for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]) if (b - a) * FR / SR >= 0.35]
    ev = [{"start": round(t[a], 2), "end": round(t[b - 1] + FR / SR, 2), "pitch_strength": round(float(ps[a:b].mean()), 2),
           "f0": int(np.median(f0[a:b])), "loud": round(float(rel[a:b].mean()), 1),
           "glide": int(f0[a:b][-3:].mean() - f0[a:b][:3].mean())} for a, b in runs]
    out[f] = ev
    print(f, len(ev), "voiced runs")
    for e in ev: print(f"   {int(e['start']//60)}:{e['start']%60:05.2f}-{e['end']:.1f}s  dur {e['end']-e['start']:.1f}  ps {e['pitch_strength']}  f0 {e['f0']}  +{e['loud']}dB  glide {e['glide']}")
save_json("singing.json", out)

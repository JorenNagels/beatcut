"""Step 12: music analysis - tempo, beat grid, downbeats (bars), loudness per bar, sections, leading/trailing silence.
Steady-tempo songs: tempo from onset autocorrelation, phase from onset energy on the grid, then each beat is
snapped to the nearest onset peak (+-60 ms) to follow small drift. Output: music.json (+ sheets/music_*.png).
Tracks come from event.yaml  music.tracks: {role: path}  (roles are names the plan uses, e.g. calm / upbeat)."""
import subprocess, sys
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import uniform_filter1d
from common import ROOT, FFMPEG, save_json, cfg, event_path

SR, HOP = 22050, 256
TRACKS = cfg("music.tracks") or {}


def load(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(event_path(path)), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def analyze(x):
    n = (len(x) - 2048) // HOP
    fr = np.lib.stride_tricks.as_strided(x, (n, 2048), (x.strides[0] * HOP, x.strides[0])) * np.hanning(2048)
    S = np.log1p(100 * np.abs(np.fft.rfft(fr, axis=1)))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(1); flux = np.concatenate([[0], flux])
    onset = flux - uniform_filter1d(flux, 32); onset = np.maximum(onset, 0)
    fps = SR / HOP
    rms = np.sqrt((fr ** 2).mean(1)); db = 20 * np.log10(rms + 1e-6)
    # silence at start/end
    loud = db > db.max() - 45
    t0, t1 = np.argmax(loud) / fps, (n - np.argmax(loud[::-1])) / fps
    # tempo: autocorrelation of onset over 70-180 BPM, prefer 90-150
    ac = np.correlate(onset, onset, "full")[len(onset) - 1:]
    lags = np.arange(int(fps * 60 / 180), int(fps * 60 / 70))
    w = np.exp(-0.5 * (np.log2((60 * fps / lags) / 120)) ** 2 / 0.6 ** 2)
    lag = lags[np.argmax(ac[lags] * w)]
    # refine to fractional lag with long-range comb
    cands = np.linspace(lag - 1, lag + 1, 81)
    best = max(cands, key=lambda L: sum(np.interp(np.arange(1, 64) * L, np.arange(len(ac)), ac)))
    period = best / fps; bpm = 60 / period
    # phase
    phases = np.linspace(0, period, 64, endpoint=False)
    def grid_score(ph):
        g = np.arange(t0 + ph, t1, period)
        return np.interp(g * fps, np.arange(n), uniform_filter1d(onset, 3)).sum()
    ph = max(phases, key=grid_score)
    beats = np.arange(t0 + ph, t1, period)
    sm = uniform_filter1d(onset, 3)
    snapped = []
    for b in beats:                                     # follow drift: snap to local onset max within +-60 ms
        i0, i1 = int((b - .06) * fps), int((b + .06) * fps) + 1
        seg = sm[max(0, i0):i1]
        snapped.append((max(0, i0) + int(np.argmax(seg))) / fps if len(seg) and seg.max() > np.median(sm) * 2 else b)
    beats = np.array(snapped)
    # downbeat: which of 4 offsets has the strongest low-frequency onset (kick)
    low = np.maximum(0, np.diff(S[:, :20], axis=0)).sum(1); low = np.concatenate([[0], low])
    lowb = np.interp(beats * fps, np.arange(n), uniform_filter1d(low, 3))
    off = int(np.argmax([lowb[k::4].mean() for k in range(4)]))
    bars = beats[off::4]
    # loudness per bar + sections (novelty on bar loudness/brightness)
    def bar_feat(a, b):
        i, j = int(a * fps), max(int(a * fps) + 1, int(b * fps))
        return [float(np.mean(db[i:j])), float(np.mean(S[i:j, 200:].mean(1)))]
    bf = np.array([bar_feat(a, b) for a, b in zip(bars[:-1], bars[1:])])
    z = (bf - bf.mean(0)) / (bf.std(0) + 1e-6)
    nov = np.r_[0, np.abs(np.diff(uniform_filter1d(z, 2, axis=0), axis=0)).sum(1)]
    pk, _ = find_peaks(nov, distance=4, prominence=np.percentile(nov, 75))
    bounds = [0] + [int(p) for p in pk] + [len(bf)]
    sections = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b <= a: continue
        e = float(np.mean(z[a:b, 0]))
        sections.append({"bar_start": a, "bar_end": b, "start": float(bars[a]), "end": float(bars[min(b, len(bars) - 1)]),
                         "energy": round(e, 2), "level": "high" if e > 0.4 else "low" if e < -0.6 else "mid"})
    return {"bpm": round(bpm, 2), "beat_period": round(period, 4), "audio_start": round(t0, 3), "audio_end": round(t1, 3),
            "beats": np.round(beats, 3).tolist(), "downbeat_offset": off, "bars": np.round(bars, 3).tolist(),
            "bar_loudness_db": np.round(bf[:, 0], 1).tolist(), "sections": sections, "duration": round(len(x) / SR, 2),
            "_db": db, "_fps": fps}


def plot(name, r):
    from PIL import Image, ImageDraw
    db, fps = r.pop("_db"), r.pop("_fps")
    W, H = 1800, 220
    im = Image.new("RGB", (W, H), (250, 250, 250)); d = ImageDraw.Draw(im)
    dur = len(db) / fps; X = lambda t: int(t / dur * (W - 1))
    env = uniform_filter1d(db, int(fps / 4))
    for i in range(0, len(env), 4):
        y = int(np.interp(env[i], [env.max() - 50, env.max()], [H - 30, 20]))
        d.line([(X(i / fps), H - 30), (X(i / fps), y)], fill=(170, 190, 220))
    for s in r["sections"]:
        col = {"high": (220, 60, 40), "mid": (230, 160, 30), "low": (60, 140, 90)}[s["level"]]
        d.line([(X(s["start"]), 0), (X(s["start"]), H - 30)], fill=col, width=2)
        d.text((X(s["start"]) + 3, 3), f"{s['level']} {s['start']:.0f}s", fill=col)
    for t in range(0, int(dur), 10):
        d.text((X(t), H - 25), f"{t}", fill=(80, 80, 80))
    d.text((W - 300, H - 14), f"{name}: {r['bpm']} BPM", fill=(0, 0, 0))
    im.save(ROOT / "sheets" / f"music_{name}.png")


def main():
    if not TRACKS: raise SystemExit("event.yaml has no music.tracks")
    (ROOT / "sheets").mkdir(exist_ok=True)
    out = {}
    for name, path in TRACKS.items():
        r = analyze(load(path)); plot(name, r)
        r["file"] = path; out[name] = r
        print(f"{name}: {r['bpm']} BPM, {len(r['beats'])} beats, {len(r['bars'])} bars, audio {r['audio_start']}-{r['audio_end']}s of {r['duration']}s")
        for s in r["sections"]:
            print(f"   bars {s['bar_start']:3d}-{s['bar_end']:3d}  {s['start']:6.1f}-{s['end']:6.1f}s  {s['level']:4s} ({s['energy']:+.2f})")
    save_json("music.json", out)


if __name__ == "__main__":
    main()

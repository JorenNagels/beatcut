"""Step 5: turn per-frame signals into per-second features and detected events.

No GPMF telemetry exists in this footage, so IMU events are detected from video + audio:
  jump   : snow-hiss (3-8 kHz) drops >=0.3 s while the camera image steadies, then a landing jolt
           (vertical image shift spike) and/or loud thump
  crash  : chaotic motion/spin burst followed by >=2 s near-stillness
  spin   : integrated optical-flow rotation over <=2 s
  speed  : sustained high image-flow speed while riding (top-speed sections proxy)
  voice  : loud, voice-band, tonal audio peaks (shouting, laughing, cheering) - not wind
  bad    : black / pocket, lens covered / white-out, extreme shake, blur
Output: features/<id>.json (per-second arrays) and events.json
"""
import numpy as np
from scipy.ndimage import uniform_filter1d, median_filter
from common import ROOT, CACHE, load_json, save_json

FEAT = ROOT / "features"; FEAT.mkdir(exist_ok=True)


def per_sec(x, fps, fn=np.mean):
    n = len(x) // fps
    return fn(np.asarray(x[: n * fps]).reshape(n, fps), axis=1) if n else np.zeros(0)


def runs(mask):
    """[(start, end_exclusive)] of True runs."""
    m = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def analyze(name, fid, hints):
    d = np.load(CACHE / "signals" / f"{fid}.npz")
    fps = int(d["fps"])
    n = len(d["motion"]) // fps
    if n < 2:
        return None, []
    dx, dy, rot = d["dx"], d["dy"], d["rot"]
    spd = np.hypot(dx, dy)
    # shake = high-frequency part of shift (minus 1 s moving average)
    hf = np.hypot(dx - uniform_filter1d(dx, fps), dy - uniform_filter1d(dy, fps))
    F = {
        "motion": per_sec(d["motion"], fps), "speed": per_sec(spd, fps, np.median), "shake": per_sec(hf, fps),
        "rot": per_sec(rot, fps), "bright": per_sec(d["bright"], fps), "std": per_sec(d["std"], fps),
        "sharp": per_sec(d["sharp"], fps), "sat": per_sec(d["sat"], fps), "snow": per_sec(d["snow"], fps),
        "sky": per_sec(d["sky"], fps), "dark": per_sec(d["dark"], fps),
    }
    fc = d["faces"][:n] if len(d["faces"]) else np.zeros((n, 2))
    fc = np.vstack([fc, np.zeros((max(0, n - len(fc)), 2))])
    F["faces"], F["face_area"] = fc[:, 0], fc[:, 1]
    # audio at 10 Hz -> 1 Hz
    A = {k: d[k] for k in ("a_db", "a_voice", "a_flat", "a_low", "a_hf")}
    has_audio = len(A["a_db"]) > 10
    if has_audio:
        na = min(n, len(A["a_db"]) // 10)
        for k in A:
            F[k] = np.pad(per_sec(A[k], 10, np.max if k == "a_db" else np.mean)[:na], (0, n - na), constant_values=np.nan)
    for k in F:
        F[k] = np.asarray(F[k], np.float32)[:n]

    # ---- bad-frame flags ----
    black = (F["dark"] > 0.8) | (F["bright"] < 18)
    covered = (F["std"] < 9) | ((F["sharp"] < 8) & (F["std"] < 25))           # lens in snow / pocket / white-out
    shake_thr = max(np.nanpercentile(F["shake"], 97), 6.0)
    extreme_shake = F["shake"] > shake_thr
    F["bad"] = (black | covered | extreme_shake).astype(np.float32)

    ev = []
    def add(kind, s, e, score, why):
        ev.append({"file": name, "kind": kind, "start": float(s), "end": float(e), "score": float(score), "why": why})

    # ---- voice peaks (not wind) ----
    if has_audio:
        db = A["a_db"]; v = A["a_voice"]; fl = A["a_flat"]; lo = A["a_low"]
        base = np.nanmedian(db)
        loud = (db > base + 9) & (v > 0.45) & (fl < 0.35) & (lo < 0.5)
        loud = median_filter(loud.astype(np.uint8), 3).astype(bool)
        for s, e in runs(loud):
            if e - s >= 4:                                                    # >= 0.4 s
                pk = float(db[s:e].max() - base)
                add("voice", s / 10, e / 10, min(1, pk / 25) * min(1, (e - s) / 15) ** 0.5,
                    f"voices/laughter {pk:.0f} dB above clip level ({(e - s) / 10:.1f}s)")

    # ---- jumps: hiss gap + steady image, then landing jolt ----
    if has_audio:
        hiss = uniform_filter1d(A["a_hf"] * 10 ** (A["a_db"] / 20), 3)
        riding = hiss > np.nanpercentile(hiss, 40)
        sh10 = np.pad(np.abs(np.diff(dy)), (1, 0))
        m10 = min(len(hiss), len(sh10))
        gap = (~riding[:m10])
        for s, e in runs(gap):
            L = (e - s) / 10
            if not (0.4 <= L <= 2.5) or s < 15 or e + 5 > m10: continue
            before = riding[max(0, s - 15):s].mean()
            land_jolt = sh10[e:e + 5].max() / (np.median(sh10[max(0, s - 30):s]) + 1e-3)
            thump = A["a_db"][e:e + 5].max() - np.nanmedian(A["a_db"][max(0, s - 30):s])
            steady = sh10[s:e].mean() < np.median(sh10[max(0, s - 30):s]) * 1.2
            if before > 0.8 and land_jolt > 4 and thump > 5 and steady:
                sc = min(1, 0.4 + L / 2 + min(land_jolt, 10) / 25)
                add("jump", max(0, s / 10 - 2), e / 10 + 1.5, sc, f"jump ~{L:.1f}s airtime (hiss gap + landing jolt)")

    # ---- crashes: chaotic burst then stillness ----
    chaos = (F["shake"] > np.nanpercentile(F["shake"], 92)) & (np.abs(F["rot"]) > np.nanpercentile(np.abs(F["rot"]), 85))
    still = F["motion"] < np.nanpercentile(F["motion"], 15)
    for s, e in runs(chaos):
        if e + 2 <= n and still[e:e + 3].mean() >= 0.66 and not F["bad"][s:e].all():
            add("crash", max(0, s - 2), min(n, e + 3), 0.8, "possible crash: chaotic spin/shake then stillness")

    # ---- spins / fast turns ----
    rot2 = uniform_filter1d(F["rot"], 2) * 2
    thr = max(np.nanpercentile(np.abs(rot2), 98), 0.02)
    for s, e in runs(np.abs(rot2) > thr):
        add("spin", max(0, s - 1), min(n, e + 2), min(1, float(np.abs(rot2[s:e]).max() / thr / 2)), "fast turn / spin (image rotation)")

    # ---- top speed sections ----
    sp = uniform_filter1d(F["speed"], 5)
    good = F["bad"] < 0.5
    if good.sum() > 10:
        thr = np.nanpercentile(sp[good], 92)
        for s, e in runs((sp > thr) & good):
            if e - s >= 3:
                add("speed", s, min(n, s + 8), 0.5 + 0.5 * min(1, (e - s) / 10), f"fast riding section ({e - s}s of high image speed)")

    for h in hints.get(name, []):
        add("hint", h["start"], h["end"], 1.0, f"named clip in source: '{h['label']}'")

    save_json(f"features/{fid}.json", {k: np.round(np.nan_to_num(v), 4).tolist() for k, v in F.items()})
    return F, ev


def main():
    idx = load_json("signals_index.json")
    hints = load_json("dedup.json").get("hints", {})
    allev, summary = [], {}
    for name, fid in idx.items():
        F, ev = analyze(name, fid, hints)
        allev += ev
        if F is not None:
            summary[name] = {"seconds": len(F["motion"]), "bad_s": int(F["bad"].sum()),
                             "events": {k: sum(1 for e in ev if e["kind"] == k) for k in ("jump", "crash", "spin", "speed", "voice", "hint")}}
    save_json("events.json", allev)
    save_json("features/summary.json", summary)
    tot = {k: sum(s["events"][k] for s in summary.values()) for k in ("jump", "crash", "spin", "speed", "voice", "hint")}
    print("events:", tot, " bad seconds:", sum(s["bad_s"] for s in summary.values()), "of", sum(s["seconds"] for s in summary.values()))


if __name__ == "__main__":
    main()

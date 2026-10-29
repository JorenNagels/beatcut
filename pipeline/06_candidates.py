"""Step 6: score and pick ~60 candidate clips (2-8 s) + 15 best photos.

Inputs: tags.json (visual pass), events.json + features/*.json (signals), inventory.json, dedup.json
Two kinds:  ACTION (action, crash, auto-detected jump/speed/spin) - fast cuts
            CALM   (scenic, faces, lifestyle)                       - slow breathers
Rules: only kept (non-duplicate) files; no two candidates overlap or sit within 12 s in the same file;
max 3 per file (4 for 9-min GoPro chapters); spread over days and categories.
Output: candidates.json / candidates.csv, photos_best.json
"""
import csv, re
from datetime import datetime, timedelta
import numpy as np
from common import ROOT, load_json, save_json

TARGET, ACTION_SHARE = 60, 0.5
ACTION_CATS, CALM_CATS = {"action", "crash", "jump", "speed", "spin"}, {"scenic", "faces", "lifestyle"}


def day_of(r, est):
    st = r.get("shot_time")
    if st:
        d = datetime.fromisoformat(st)
        if d.hour < 5: d -= timedelta(days=1)           # after-midnight party belongs to the evening before
        return d.date().isoformat(), "dated"
    return est.get(r["file"], "unknown"), "estimated"


def nz(x):
    x = np.asarray(x, float)
    lo, hi = np.percentile(x, 5), np.percentile(x, 95)
    return np.clip((x - lo) / (hi - lo + 1e-9), 0, 1)


def window_scores(F, cat):
    """Per-second desirability for a category (0..1)."""
    n = len(F["motion"])
    bad = np.asarray(F["bad"], float)
    sharp, shake, mot, spd = nz(F["sharp"]), nz(F["shake"]), nz(F["motion"]), nz(F["speed"])
    voice = nz(np.asarray(F.get("a_voice", np.zeros(n))) * (np.asarray(F.get("a_db", np.zeros(n))) - np.median(F.get("a_db", [0]))).clip(0))
    face = np.clip(np.asarray(F["face_area"]) * 25, 0, 1)
    if cat in ("action", "jump", "speed", "spin"):
        s = 0.45 * mot + 0.35 * spd + 0.2 * sharp - 0.15 * shake
    elif cat == "crash":
        s = 0.4 * nz(np.abs(F["rot"])) + 0.3 * mot + 0.3 * voice
    elif cat == "scenic":
        s = 0.45 * (1 - shake) + 0.35 * sharp + 0.2 * nz(F["sky"])
    elif cat == "faces":
        s = 0.4 * face + 0.3 * voice + 0.3 * (1 - shake)
    else:  # lifestyle
        s = 0.4 * voice + 0.3 * face + 0.3 * (1 - shake)
    return s - 0.8 * bad


def best_window(s, a, b, L):
    a, b = int(a), int(min(b, len(s)))
    if b - a <= L:
        return a, b, float(np.mean(s[a:b])) if b > a else 0.0
    cs = np.concatenate([[0], np.cumsum(s[a:b])])
    m = (cs[L:] - cs[:-L]) / L
    k = int(np.argmax(m))
    return a + k, a + k + L, float(m[k])


def main():
    inv = {r["file"]: r for r in load_json("inventory.json")}
    dd = load_json("dedup.json"); tags = load_json("tags.json"); idx = load_json("signals_index.json")
    events = load_json("events.json")
    est = tags["day_estimates"]
    feats = {f: load_json(f"features/{fid}.json") for f, fid in idx.items()}
    usable = dd["usable"]

    def in_usable(f, s, e):
        return any(s >= a - 0.5 and e <= b + 0.5 for a, b in usable.get(f, []))

    pool = []
    # ---- 1) tagged segments ----
    for t in tags["tags"]:
        f = t["file"]
        if f not in feats or f in dd["excluded"] or t["cat"] == "boring":
            continue
        F = feats[f]; cat = t["cat"]
        L = {"action": 5, "crash": 7, "scenic": 7, "faces": 5, "lifestyle": 6}[cat]
        s = window_scores(F, cat)
        a, b, q = best_window(s, t["start"], t["end"], L)
        if b - a < 2: continue
        evs = [e for e in events if e["file"] == f and e["start"] < b and e["end"] > a and e["kind"] != "hint"]
        # only voice/laughter evidence is trusted; jump/crash detectors were not confirmed visually on this footage
        bonus = min(0.15, sum(0.05 + 0.05 * e["score"] for e in evs if e["kind"] == "voice"))
        why = [t["note"]] + sorted({e["why"] for e in evs if e["kind"] == "voice"}, key=lambda w: -float(re.search(r"(\d+) dB", w).group(1)))[:1]
        pool.append({"file": f, "start": float(a), "end": float(b), "cat": cat, "people": t["people"],
                     "score": round(0.65 * t["rating"] / 5 + 0.2 * max(0, min(1, q + 0.3)) + bonus, 3),
                     "source": "visual tag + signals", "reason": "; ".join(why)})
    # ---- 2) strong auto-detected events outside tags (jumps, top speed) ----
    for e in events:
        f = e["file"]
        if e["kind"] not in ("jump", "speed") or f not in feats: continue
        if any(t["file"] == f and t["start"] - 3 < e["end"] and t["end"] + 3 > e["start"] for t in tags["tags"]): continue
        F = feats[f]; a, b = int(e["start"]), int(min(e["end"], e["start"] + 6))
        if b - a < 2 or np.mean(F["bad"][a:b]) > 0.2 or np.mean(F["sharp"][a:b]) < 30: continue
        pool.append({"file": f, "start": float(a), "end": float(b), "cat": e["kind"], "people": [],
                     "score": round(0.25 + 0.3 * e["score"], 3), "source": "auto (audio/video motion)", "reason": e["why"]})

    pool = [p for p in pool if in_usable(p["file"], p["start"], p["end"])]
    for p in pool:
        p["verified"] = p["source"].startswith("visual")
    unverified = [p for p in pool if not p["verified"]]
    pool = [p for p in pool if p["verified"]]          # auto jumps showed no visible jump on the check sheet
    for p in pool:
        r = inv[p["file"]]
        p["day"], p["day_source"] = day_of(r, est)
        p["kind"] = "ACTION" if p["cat"] in ACTION_CATS else "CALM"
        p["vertical"] = r["height"] > r["width"]
        p["fps"] = r["fps"]; p["slowmo_ok"] = r["fps"] >= 50
        p["src_res"] = f'{r["width"]}x{r["height"]}'

    # ---- selection with spread ----
    pool.sort(key=lambda p: -p["score"])
    chosen, per_file = [], {}
    days = sorted({p["day"] for p in pool})
    def ok(p):
        cap = 4 if inv[p["file"]]["duration"] > 500 else 3
        if per_file.get(p["file"], 0) >= cap: return False
        return all(not (c["file"] == p["file"] and p["start"] < c["end"] + 12 and p["end"] > c["start"] - 12) for c in chosen)
    def take(p):
        chosen.append(p); per_file[p["file"]] = per_file.get(p["file"], 0) + 1
    # guarantee: >=3 per day per kind where possible, and >=7 each of scenic/faces/lifestyle
    for d in days:
        for kind in ("ACTION", "CALM"):
            for p in [p for p in pool if p["day"] == d and p["kind"] == kind][:6]:
                if sum(1 for c in chosen if c["day"] == d and c["kind"] == kind) >= 3: break
                if p not in chosen and ok(p): take(p)
    for cat, mn in (("faces", 10), ("scenic", 8), ("lifestyle", 8), ("crash", 7)):
        for p in [p for p in pool if p["cat"] == cat]:
            if sum(1 for c in chosen if c["cat"] == cat) >= mn: break
            if p not in chosen and ok(p): take(p)
    n_action = int(TARGET * ACTION_SHARE)
    for kind, n in (("ACTION", n_action), ("CALM", TARGET - n_action)):
        for p in [p for p in pool if p["kind"] == kind]:
            if sum(1 for c in chosen if c["kind"] == kind) >= n: break
            if p not in chosen and ok(p): take(p)
    for p in pool:                                             # top up if one kind ran dry
        if len(chosen) >= TARGET: break
        if p not in chosen and ok(p): take(p)

    chosen.sort(key=lambda p: (p["day"], p["file"], p["start"]))
    for i, p in enumerate(chosen, 1):
        p["id"] = f"c{i:03d}"; p["duration"] = round(p["end"] - p["start"], 1)
    save_json("candidates.json", chosen)
    keys = ["id", "day", "day_source", "kind", "cat", "score", "file", "start", "end", "duration", "reason", "people",
            "source", "vertical", "fps", "slowmo_ok", "src_res"]
    with open(ROOT / "candidates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, keys, extrasaction="ignore"); w.writeheader()
        for p in chosen: w.writerow({**p, "people": ", ".join(p["people"])})
    save_json("candidate_pool.json", {"verified": pool, "unverified_auto_events": unverified})

    # ---- photos: sharpness check + visual rating ----
    import cv2
    from common import SRC
    best = []
    for f, v in tags["photos"].items():
        if f in dd["excluded"]: continue
        g = cv2.imread(str(SRC / f), cv2.IMREAD_GRAYSCALE)
        g = cv2.resize(g, (1024, int(1024 * g.shape[0] / g.shape[1])))
        sh = float(cv2.Laplacian(g, cv2.CV_32F).var())
        r = inv[f]; d, src = day_of(r, est)
        best.append({"file": f, "rating": v["rating"], "cat": v["cat"], "note": v["note"], "sharpness": round(sh, 1),
                     "day": d if src == "dated" else "unknown", "score": round(v["rating"] / 5 * 0.8 + min(sh, 600) / 600 * 0.2, 3)})
    best.sort(key=lambda b: -b["score"])
    save_json("photos_best.json", best[:15])

    from collections import Counter
    print("pool", len(pool), "chosen", len(chosen))
    print("kind", Counter(p["kind"] for p in chosen), "\ncat", Counter(p["cat"] for p in chosen))
    print("day", sorted(Counter(p["day"] for p in chosen).items()))
    print("photos:", [b["file"] for b in best[:15]])


if __name__ == "__main__":
    main()

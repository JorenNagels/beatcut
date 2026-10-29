"""Step 19b: laughter, cheering, singing and shouting with an AudioSet sound-event model (PANNs Cnn14, local).
   19b_sounds [file ...]

Every kept video with sound -> per-frame class probabilities (100 per second) for groups of AudioSet classes,
smoothed over 0.5 s; runs above the group threshold become events. Unlike the voice-band detector in 05_events
it tells laughing from talking and is not fooled by wind. edl_lib counts laughter/cheering as voices (camera sound,
crash reactions, best_talk), and 15_fun_search ranks windows with laughter first.
Output: sounds.json [{file, kind: laugh|cheer|sing|shout, start, end, score, why}], cache/sounds/<id>.npz.
The model (~330 MB) downloads on first use to ~/panns_data."""
import subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter1d
from common import SRC, CACHE, FFMPEG, save_json, need, device, file_id, kept_videos

SR = 32000
OUT = CACHE / "sounds"; OUT.mkdir(exist_ok=True)
GROUPS = {   # kind: (AudioSet classes, threshold)
    "laugh": (["Laughter", "Baby laughter", "Giggle", "Snicker", "Belly laugh", "Chuckle, chortle"], 0.25),
    "cheer": (["Cheering", "Applause", "Crowd", "Whoop"], 0.3),
    "sing": (["Singing", "Choir", "Yodeling", "Chant", "Humming"], 0.3),
    "shout": (["Shout", "Yell", "Screaming", "Children shouting", "Battle cry"], 0.25),
}
DATA = Path.home() / "panns_data"
FILES = {"class_labels_indices.csv": "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv",
         "Cnn14_DecisionLevelMax.pth": "https://zenodo.org/record/3987831/files/Cnn14_DecisionLevelMax_mAP%3D0.385.pth?download=1"}


def fetch():
    """panns_inference downloads with wget (missing on Windows): get the files first"""
    DATA.mkdir(exist_ok=True)
    for name, url in FILES.items():
        if not (DATA / name).exists():
            print(f"downloading {name} ..."); tmp = DATA / (name + ".part")
            urllib.request.urlretrieve(url, tmp); tmp.replace(DATA / name)


def load(f):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(SRC / f), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def runs(mask):
    m = np.concatenate([[0], mask.astype(int), [0]]); d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def main():
    files, inv = kept_videos()
    files = [f for f in (sys.argv[1:] or files) if inv[f].get("has_audio")]
    todo = [f for f in files if not (OUT / f"{file_id(f)}.npz").exists()]
    if todo:
        fetch()
        panns = need("panns_inference", "Sound-event detection")
        from panns_inference import labels
        dev = device()
        sed = panns.SoundEventDetection(checkpoint_path=str(DATA / "Cnn14_DecisionLevelMax.pth"),
                                        device="cuda" if dev == "cuda" else "cpu")
        cols = {k: [labels.index(c) for c in cs if c in labels] for k, (cs, _) in GROUPS.items()}
        for k, f in enumerate(todo, 1):
            x = load(f); probs = []
            for i in range(0, max(1, len(x)), 60 * SR):                 # 60 s chunks keep GPU memory small
                ch = x[i:i + 60 * SR]
                if len(ch) < SR: ch = np.pad(ch, (0, SR - len(ch)))
                fw = sed.inference(ch[None, :])[0]                         # (frames, 527) at 100 fps
                probs.append(fw[: int(np.ceil(len(x[i:i + 60 * SR]) / SR * 100))])
            P = np.concatenate(probs) if probs else np.zeros((0, 527))
            np.savez_compressed(OUT / f"{file_id(f)}.npz", **{g: P[:, c].max(1).astype(np.float16) for g, c in cols.items()})
            print(f"[{k}/{len(todo)}] {f}", flush=True)
    ev = []
    for f in files:
        d = np.load(OUT / f"{file_id(f)}.npz")
        for g, (_, thr) in GROUPS.items():
            p = uniform_filter1d(d[g].astype(np.float32), 50) if len(d[g]) else d[g]
            for a, b in runs(p > thr):
                if b - a < 40: continue                                    # >= 0.4 s
                sc = float(p[a:b].max())
                ev.append({"file": f, "kind": g, "start": round(a / 100, 2), "end": round(b / 100, 2), "score": round(sc, 2),
                           "why": f"{g} (sound model {sc:.2f}, {(b - a) / 100:.1f}s)"})
    save_json("sounds.json", ev)
    print({g: sum(1 for e in ev if e["kind"] == g) for g in GROUPS}, f"events in {len(files)} files -> sounds.json")


if __name__ == "__main__":
    main()

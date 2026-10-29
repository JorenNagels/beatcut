"""Step 3: per-second signal analysis of every KEPT video range (duplicates are skipped).

One ffmpeg decode per file at 10 fps / 320x180:
  - motion energy (mean abs frame diff), camera shift via phase correlation -> speed + shake (jitter)
  - rotation rate (spins / fast turns) from log-polar-free approx: optical-flow curl on a coarse grid
  - brightness, sharpness (Laplacian var), saturation, sky/snow fractions, flat (lens-in-snow / pocket)
  - faces (OpenCV Haar, frontal + profile) on 1 frame per second
  - sample JPEG every 2 s -> cache/frames/<id>/<t>.jpg (for contact sheets + review)
Audio (16 kHz mono): per 0.1 s loudness, voice-band ratio, spectral flatness, low-frequency (wind) ratio.

Telemetry note: these files are re-exports without GPMF; motion from video replaces the IMU.
Output: cache/signals/<id>.npz + signals_index.json
"""
import subprocess, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np, cv2
from common import SRC, ROOT, CACHE, FFMPEG, load_json, save_json, file_id

FPS, W, H = 10, 320, 180
SIG = CACHE / "signals"; SIG.mkdir(exist_ok=True)
FR = CACHE / "frames"; FR.mkdir(exist_ok=True)
SR = 16000


def audio_feats(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = SR // 10
    n = len(x) // hop
    if n == 0:
        return {k: np.zeros(0) for k in ("a_db", "a_voice", "a_flat", "a_low", "a_hf")}
    fr = x[: n * hop].reshape(n, hop) * np.hanning(hop)
    spec = np.abs(np.fft.rfft(fr, axis=1)) ** 2 + 1e-12
    f = np.fft.rfftfreq(hop, 1 / SR)
    tot = spec.sum(1)
    band = lambda lo, hi: spec[:, (f >= lo) & (f < hi)].sum(1) / tot
    return {
        "a_db": 10 * np.log10(tot / hop + 1e-12),
        "a_voice": band(250, 3000),                  # shouting / laughing / talking
        "a_low": band(0, 200),                       # wind rumble
        "a_hf": band(3000, 8000),                    # snow hiss / edges scraping
        "a_flat": np.exp(np.log(spec[:, 5:200]).mean(1)) / spec[:, 5:200].mean(1),   # 1=noise, low=tonal
    }


def analyze(name):
    fid = file_id(name)
    out = SIG / f"{fid}.npz"
    if out.exists():
        return name, fid, "cached"
    fdir = FR / fid; fdir.mkdir(exist_ok=True)
    face_f = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    face_p = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    proc = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(SRC / name), "-an", "-vf",
                             f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
                             "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    fsz = W * H * 3
    win = cv2.createHanningWindow((160, 90), cv2.CV_32F)
    prev_g = None; prev_small = None
    rec = {k: [] for k in ("motion", "dx", "dy", "resp", "rot", "bright", "sharp", "sat", "std", "snow", "sky", "dark")}
    faces = []                         # per second: (n_faces, max_face_area_frac)
    i = 0
    while True:
        buf = proc.stdout.read(fsz)
        if len(buf) < fsz: break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(g, (160, 90), interpolation=cv2.INTER_AREA).astype(np.float32)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        if prev_small is not None:
            (dx, dy), resp = cv2.phaseCorrelate(prev_small, small, win)
            mot = float(np.abs(small - prev_small).mean())
            # rotation: flow on coarse grid, curl about center
            fl = cv2.calcOpticalFlowFarneback(prev_g, cv2.resize(g, (80, 45)), None, 0.5, 2, 9, 2, 5, 1.1, 0)
            yy, xx = np.mgrid[0:45, 0:80]; rx, ry = xx - 40, yy - 22.5
            r2 = rx ** 2 + ry ** 2 + 1
            rot = float(((rx * fl[..., 1] - ry * fl[..., 0]) / r2).mean())
        else:
            dx = dy = resp = mot = rot = 0.0
        prev_small = small; prev_g = cv2.resize(g, (80, 45))
        rec["motion"].append(mot); rec["dx"].append(dx); rec["dy"].append(dy); rec["resp"].append(resp); rec["rot"].append(rot)
        rec["bright"].append(float(g.mean())); rec["std"].append(float(g.std()))
        rec["sharp"].append(float(cv2.Laplacian(g, cv2.CV_32F).var()))
        rec["sat"].append(float(hsv[..., 1].mean()))
        rec["snow"].append(float(((hsv[..., 2] > 170) & (hsv[..., 1] < 40)).mean()))
        rec["sky"].append(float(((hsv[..., 0] > 95) & (hsv[..., 0] < 130) & (hsv[..., 1] > 50) & (hsv[..., 2] > 90))[: H // 2].mean()))
        rec["dark"].append(float((g < 25).mean()))
        if i % FPS == 0:
            fs = list(face_f.detectMultiScale(g, 1.1, 6, minSize=(18, 18)))
            fs += list(face_p.detectMultiScale(g, 1.1, 6, minSize=(18, 18)))
            faces.append((len(fs), max((w * h for (_, _, w, h) in fs), default=0) / (W * H)))
        if i % (2 * FPS) == 0:
            cv2.imwrite(str(fdir / f"{i // FPS:05d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        i += 1
    proc.wait()
    a = audio_feats(SRC / name)
    np.savez_compressed(out, fps=FPS, faces=np.array(faces, np.float32).reshape(-1, 2),
                        **{k: np.array(v, np.float32) for k, v in rec.items()}, **a)
    return name, fid, f"{i} frames"


def main():
    inv = {r["file"]: r for r in load_json("inventory.json")}
    dd = load_json("dedup.json")
    files = [f for f in dd["usable"] if inv[f]["kind"] == "video" and dd["usable"][f]]
    files.sort(key=lambda f: -inv[f]["duration"])           # longest first for better packing
    idx = {}
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex:
        for name, fid, msg in ex.map(analyze, files):
            idx[name] = fid
            print(f"{name}: {msg}", flush=True)
    save_json("signals_index.json", idx)


if __name__ == "__main__":
    main()

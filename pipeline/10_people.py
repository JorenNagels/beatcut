"""Step 10: find the distinct people. Face detection (YuNet) + face identity embeddings (SFace) on all kept
photos (full res) and kept videos (1 fps, native 720p), then cluster embeddings into persons.
Strangers (seen in only one source) are dropped. One best crop per person -> people/<pid>.jpg + people.json.
Models (repo models/, downloaded by install.py): models/face_detection_yunet_2023mar.onnx, models/face_recognition_sface_2021dec.onnx (OpenCV zoo)."""
import subprocess, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np, cv2
from PIL import Image, ImageOps
from scipy.cluster.hierarchy import linkage, fcluster
from common import ROOT, SRC, CACHE, FFMPEG, MODELS, load_json, save_json, file_id

MD = MODELS
FC = CACHE / "faces"; FC.mkdir(exist_ok=True)
OUT = ROOT / "people"; OUT.mkdir(exist_ok=True)
MIN_W = 56                      # min face width in px for identity use


def models():
    det = cv2.FaceDetectorYN.create(str(MD / "face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.85, 0.3, 5000)
    rec = cv2.FaceRecognizerSF.create(str(MD / "face_recognition_sface_2021dec.onnx"), "")
    return det, rec


def faces_in(img, det, rec):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, fs = det.detect(img)
    out = []
    for f in (fs if fs is not None else []):
        x, y, fw, fh = f[:4]; score = float(f[-1])
        if fw < MIN_W: continue
        le, re_, nose = f[4:6], f[6:8], f[8:10]
        eye_d = np.hypot(*(re_ - le))
        frontal = 1 - min(1, abs(nose[0] - (le[0] + re_[0]) / 2) / (eye_d + 1e-6))     # 1 = looking at camera
        crop = rec.alignCrop(img, f)
        emb = rec.feature(crop).ravel(); emb /= np.linalg.norm(emb) + 1e-9
        sharp = cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_32F).var()
        out.append({"box": [float(x), float(y), float(fw), float(fh)], "score": score, "frontal": float(frontal),
                    "sharp": float(sharp), "emb": emb.astype(np.float32)})
    return out


def scan(item):
    kind, name = item
    cache = FC / f"{file_id(name)}.npz"
    if cache.exists():
        d = np.load(cache, allow_pickle=True); return list(d["recs"])
    det, rec = models()
    recs = []
    if kind == "photo":
        im = ImageOps.exif_transpose(Image.open(SRC / name)).convert("RGB")
        img = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        s = 1600 / max(img.shape[:2])
        if s < 1: img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        for f in faces_in(img, det, rec): recs.append({**f, "src": name, "t": -1, "scale": min(s, 1)})
    else:
        pr = subprocess.run([FFMPEG, "-v", "error", "-i", str(SRC / name), "-map", "0:v:0", "-vf", "fps=1",
                             "-f", "image2pipe", "-vcodec", "bmp", "-"], capture_output=True).stdout
        i = t = 0
        while i < len(pr):
            size = int.from_bytes(pr[i + 2:i + 6], "little")
            img = cv2.imdecode(np.frombuffer(pr[i:i + size], np.uint8), cv2.IMREAD_COLOR)
            i += size
            if img is not None:
                for f in faces_in(img, det, rec): recs.append({**f, "src": name, "t": t, "scale": 1.0})
            t += 1
    np.savez(cache, recs=np.array(recs, dtype=object))
    return recs


def crop_face(r, centroid, det, rec, size=360, margin=0.45):
    """Re-detect in the actual source frame and keep the face that matches this person; None if not found."""
    if r["t"] < 0:
        im = ImageOps.exif_transpose(Image.open(SRC / r["src"])).convert("RGB")
        img = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    else:
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{r['t']}", "-i", str(SRC / r["src"]), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "bmp", "-"], capture_output=True).stdout
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None: return None
    s = min(1, 1600 / max(img.shape[:2]))
    work = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img
    found = [f for f in faces_in(work, det, rec)]
    if not found: return None
    f = max(found, key=lambda f: float(f["emb"] @ centroid))
    if float(f["emb"] @ centroid) < 0.3: return None
    x, y, w, h = [v / s for v in f["box"]]
    cx, cy, half = x + w / 2, y + h / 2, max(w, h) * (0.5 + margin)
    H, W = img.shape[:2]
    x0, y0, x1, y1 = int(max(0, cx - half)), int(max(0, cy - half)), int(min(W, cx + half)), int(min(H, cy + half))
    c = img[y0:y1, x0:x1]
    return cv2.resize(c, (size, int(size * c.shape[0] / max(1, c.shape[1]))), interpolation=cv2.INTER_CUBIC)


def main():
    inv = {r["file"]: r for r in load_json("inventory.json")}
    dd = load_json("dedup.json")
    items = [(inv[f]["kind"], f) for f in dd["usable"] if dd["usable"][f]]
    items.sort(key=lambda it: -inv[it[1]].get("duration", 0))
    allr = []
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as ex:
        for recs in ex.map(scan, items):
            allr += recs
    print("faces detected:", len(allr))
    good = [r for r in allr if r["score"] > 0.9 and r["frontal"] > 0.45 and r["box"][2] >= 64]
    E = np.stack([r["emb"] for r in good])
    Z = linkage(E, "average", metric="cosine")
    lab = fcluster(Z, t=float(sys.argv[2]) if len(sys.argv) > 2 else 0.62, criterion="distance")
    unit = lambda v: v / (np.linalg.norm(v) + 1e-9)
    clusters = []
    for c in np.unique(lab):
        mem = [good[i] for i in np.where(lab == c)[0]]
        cen = unit(np.mean([m["emb"] for m in mem], 0))
        mem = [m for m in mem if float(m["emb"] @ cen) >= 0.38]           # drop outliers (wrongly merged faces)
        if not mem: continue
        clusters.append({"members": mem, "centroid": unit(np.mean([m["emb"] for m in mem], 0))})
    # merge clusters of the same person (centroid similarity), most members first
    clusters.sort(key=lambda c: -len(c["members"]))
    merged = []
    for c in clusters:
        tgt = next((m for m in merged if float(m["centroid"] @ c["centroid"]) > 0.5), None)
        if tgt:
            tgt["members"] += c["members"]; tgt["centroid"] = unit(np.mean([m["emb"] for m in tgt["members"]], 0))
        else:
            merged.append(c)
    q = lambda m: m["box"][2] * m["box"][3] * m["score"] * (0.4 + m["frontal"]) * min(1, m["sharp"] / 200) * (2.5 if m["t"] < 0 else 1)
    people = []
    for c in merged:
        mem = c["members"]; srcs = {m["src"] for m in mem}
        in_photo = any(m["t"] < 0 and m["box"][2] >= 80 for m in mem)
        if not (len(srcs) >= 2 or in_photo): continue                    # video one-offs = strangers / noise
        mem.sort(key=q, reverse=True)
        people.append({"members": mem, "n": len(mem), "sources": sorted(srcs), "centroid": c["centroid"]})
    people.sort(key=lambda p: (-len(p["sources"]), -p["n"]))
    det, rec = models()
    meta = []
    for p in people:
        pid = f"p{len(meta) + 1:02d}"
        best = None
        for m in p["members"][:6]:                                       # first member whose re-detected crop works
            best = crop_face(m, p["centroid"], det, rec)
            if best is not None: break
        if best is None: continue
        cv2.imwrite(str(OUT / f"{pid}.jpg"), best, [cv2.IMWRITE_JPEG_QUALITY, 88])
        nex, seen = 0, {m["src"]}
        for m2 in p["members"][1:]:
            if nex >= 3: break
            if m2["src"] in seen: continue
            cr = crop_face(m2, p["centroid"], det, rec, 140, 0.4)
            if cr is None: continue
            cv2.imwrite(str(OUT / f"{pid}_{nex}.jpg"), cr, [cv2.IMWRITE_JPEG_QUALITY, 82]); nex += 1; seen.add(m2["src"])
        meta.append({"id": pid, "n_faces": p["n"], "n_sources": len(p["sources"]), "sources": p["sources"],
                     "best": {"src": m["src"], "t": m["t"]}, "extras": nex, "centroid": p["centroid"].round(5).tolist()})
    save_json("people.json", meta)
    print(len(meta), "people:", [(m["id"], m["n_faces"], m["n_sources"]) for m in meta])


if __name__ == "__main__":
    main()

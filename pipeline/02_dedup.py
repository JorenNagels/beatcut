"""Step 2: find duplicates BEFORE heavy analysis.

  a) exact copies: fast hash (size + first/last MB) -> confirmed with full SHA-256
  b) near-duplicates / overlapping trims: per-video dHash sequence at 4 fps (32x18 gray),
     matched across files with an offset vote -> offset + overlap range
  c) photos: perceptual hash (pHash + dHash)

Outputs: duplicates.csv, dedup.json (keepers + usable ranges per source file), cache/hash/*.npy
"""
import csv, hashlib, re, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageOps
import imagehash
from common import SRC, ROOT, CACHE, FFMPEG, load_json, save_json, file_id, base

HFPS = 4                      # hash samples per second
HW, HH = 32, 18
HDIR = CACHE / "hash"; HDIR.mkdir(exist_ok=True)
MB = 1 << 20


# ---------- exact ----------
def fast_hash(p):
    s = p.stat().st_size
    h = hashlib.sha1(str(s).encode())
    with open(p, "rb") as f:
        h.update(f.read(MB))
        if s > MB:
            f.seek(max(0, s - MB)); h.update(f.read(MB))
    return h.hexdigest()


def full_hash(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 * MB), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- perceptual (video) ----------
def video_hashes(name):
    out = HDIR / f"{file_id(name)}.npz"
    if out.exists():
        d = np.load(out); return d["h"], d["v"]
    cmd = [FFMPEG, "-v", "error", "-i", str(SRC / name), "-an", "-vf",
           f"fps={HFPS},scale={HW}:{HH}:flags=area,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, HH, HW).astype(np.float32)
    # dHash 8x8 on a 9x8 area-downscale -> 64 bits; plus frame std (to ignore flat frames)
    small = np.stack([np.asarray(Image.fromarray(f).resize((9, 8), Image.BILINEAR), np.float32) for f in fr]) if len(fr) else np.zeros((0, 8, 9))
    bits = (small[:, :, 1:] > small[:, :, :-1]).reshape(len(fr), 64)
    h = np.packbits(bits, axis=1).view(">u8").ravel().astype(np.uint64)
    v = fr.reshape(len(fr), -1).std(1) if len(fr) else np.zeros(0)
    np.savez(out, h=h, v=v)
    return h, v


_POP = np.array([bin(i).count("1") for i in range(256)], np.uint8)


def hamming(a, b):
    """a: (n,), b: (m,) uint64 -> (n,m) hamming distances."""
    x = (a[:, None] ^ b[None, :])
    return _POP[x.view(np.uint8).reshape(x.shape + (8,))].sum(-1)


def match_pair(ha, va, hb, vb):
    """Return (offset_seconds, n_matches, a_range, b_range) for b aligned against a, or None."""
    ia = np.where(va > 12)[0]; ib = np.where(vb > 12)[0]       # skip flat (snow/black) frames
    if len(ia) < 8 or len(ib) < 8:
        return None
    d = hamming(ha[ia], hb[ib])
    ai, bi = np.nonzero(d <= 8)
    if len(ai) < 8:
        return None
    offs = ia[ai] - ib[bi]                                      # a_index = b_index + off
    vals, cnts = np.unique(offs, return_counts=True)
    # tolerate +-1 sample jitter
    sm = np.convolve(cnts, [1, 1, 1], "same") if len(cnts) > 2 else cnts
    k = int(np.argmax(sm)); off = int(vals[k])
    sel = np.abs(offs - off) <= 1
    n = len(np.unique(ib[bi[sel]]))
    if n < max(8, 0.25 * min(len(ia), len(ib))):
        return None
    bb = ib[bi[sel]]
    return off / HFPS, n, (bb.min() + off) / HFPS, ((bb.max() + off) / HFPS), bb.min() / HFPS, bb.max() / HFPS


# ---------- keeper preference ----------
def quality_key(r):
    n = base(r["file"])
    copy_mark = bool(re.search(r"\(\d+\)|copy", n, re.I))
    gopro = bool(re.match(r"^G[XH]\d{6}", n, re.I)) or bool(r.get("firmware"))
    camera_name = gopro or bool(re.match(r"^IMG_\d+", n, re.I))
    return (r.get("has_gpmf", False), r.get("width", 0) * r.get("height", 0), r.get("fps", 0) >= 50,
            gopro, camera_name, not copy_mark, r.get("bitrate", 0), r.get("duration", 0), r["size"])


def reason(keep, other):
    bits = []
    if keep.get("has_gpmf") and not other.get("has_gpmf"): bits.append("has telemetry")
    if keep.get("width", 0) * keep.get("height", 0) > other.get("width", 0) * other.get("height", 0): bits.append("higher resolution")
    if keep.get("firmware") and not other.get("firmware"): bits.append("GoPro file (camera name + firmware tag)")
    elif re.match(r"^(G[XH]\d{6}|IMG_\d+)", base(keep["file"])) and not re.match(r"^(G[XH]\d{6}|IMG_\d+)", base(other["file"])): bits.append("original camera file name")
    if re.search(r"\(\d+\)|copy", base(other["file"]), re.I) and not re.search(r"\(\d+\)|copy", base(keep["file"]), re.I): bits.append("other is a '(1)'/'Copy' file")
    if keep.get("duration", 0) > other.get("duration", 0) + 1: bits.append("longer (other is a trimmed part)")
    if keep.get("bitrate", 0) > other.get("bitrate", 0) * 1.05: bits.append("higher bitrate")
    return "; ".join(bits) or "equivalent; kept first by name"


class UF:
    def __init__(s): s.p = {}
    def f(s, x):
        s.p.setdefault(x, x)
        while s.p[x] != x: s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def u(s, a, b): s.p[s.f(a)] = s.f(b)


def main():
    inv = load_json("inventory.json")
    by = {r["file"]: r for r in inv}
    rows, uf = [], UF()
    excluded = {}                    # file -> dict(reason, kept, type)
    covered = {}                     # file -> list of (start,end) covered by a keeper (partial overlaps)

    # --- a) exact ---
    fh = {}
    for r in inv:
        fh.setdefault(fast_hash(SRC / r["file"]), []).append(r["file"])
    exact_groups = []
    for files in fh.values():
        if len(files) > 1:
            full = {}
            for f in files: full.setdefault(full_hash(SRC / f), []).append(f)
            exact_groups += [g for g in full.values() if len(g) > 1]
    for g in exact_groups:
        g = sorted(g, key=lambda f: quality_key(by[f]), reverse=True)
        for o in g[1:]:
            excluded[o] = {"type": "exact copy", "kept": g[0], "why": "identical bytes (SHA-256); " + reason(by[g[0]], by[o])}
            uf.u(o, g[0])

    # --- c) photos ---
    photos = [r for r in inv if r["kind"] == "photo"]
    ph = {}
    for r in photos:
        im = ImageOps.exif_transpose(Image.open(SRC / r["file"])).convert("RGB")
        ph[r["file"]] = (imagehash.phash(im), imagehash.dhash(im), im.size)
    pf = [r["file"] for r in photos if r["file"] not in excluded]
    for i, a in enumerate(pf):
        for b in pf[i + 1:]:
            if b in excluded or a in excluded: continue
            dp, dd = ph[a][0] - ph[b][0], ph[a][1] - ph[b][1]
            if dp <= 10 and dd <= 12:
                k, o = sorted([a, b], key=lambda f: quality_key(by[f]), reverse=True)
                excluded[o] = {"type": "near-duplicate photo", "kept": k,
                               "why": f"pHash dist {dp}, dHash dist {dd}; " + reason(by[k], by[o])}
                uf.u(o, k)

    # --- b) videos: perceptual ---
    vids = [r["file"] for r in inv if r["kind"] == "video" and r["file"] not in excluded]
    with ThreadPoolExecutor(6) as ex:
        H = dict(zip(vids, ex.map(video_hashes, vids)))
    order = sorted(vids, key=lambda f: quality_key(by[f]), reverse=True)    # best first
    pairs = []
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            m = match_pair(*H[a], *H[b])
            if m: pairs.append((a, b, m))
    # resolve: process from lower quality upwards; a file is excluded when (mostly) inside a better kept file
    hints = {}                       # name hints from excluded trims, e.g. "anna-backwards-fall"
    inv_fps = {r["file"]: r.get("fps", 30) for r in inv}
    for a, b, (off, n, a0, a1, b0, b1) in pairs:
        cov_b = min((b1 - b0 + 1 / HFPS) / max(by[b]["duration"], 0.1), 1)
        cov_a = min((a1 - a0 + 1 / HFPS) / max(by[a]["duration"], 0.1), 1)
        if cov_a >= 0.85 and cov_b < 0.85:          # a is the trimmed part of b -> keep b (the longer original)
            a, b, off, a0, a1, b0, b1, cov_b = b, a, -off, b0, b1, a0, a1, cov_a
        if b in excluded or a in excluded: continue
        ra, rb = by[a], by[b]
        dur_close = abs(ra["duration"] - rb["duration"]) <= 1.0
        kind = "near-duplicate (re-encode)" if dur_close and abs(off) <= 1 else "overlapping clip (trim/part)"
        info = {"type": kind, "kept": a, "offset_in_kept_s": round(float(off), 2),
                "range_in_kept": [round(float(a0), 1), round(float(a1), 1)], "range_in_this": [round(float(b0), 1), round(float(b1), 1)],
                "matched_samples": int(n), "coverage": round(float(cov_b), 3),
                "why": f"{n} matching frames at offset {off:+.2f}s; " + reason(ra, rb)}
        if cov_b >= 0.85:
            excluded[b] = info; uf.u(b, a)
            if not re.match(r"^([0-9A-F]{8}-|G[XH]\d|IMG_)", base(b), re.I):
                label = "shared in the group chat" if base(b).startswith("VIDEO-") else re.sub(r"[-_]+", " ", base(b).rsplit(".", 1)[0])
                hints.setdefault(a, []).append({"start": info["range_in_kept"][0], "end": info["range_in_kept"][1],
                                                "label": label, "alt": b, "alt_offset": -info["offset_in_kept_s"],
                                                "alt_fps": inv_fps.get(b, 30)})
        else:
            covered.setdefault(b, []).append(info); uf.u(b, a)

    # --- write duplicates.csv ---
    groups = {}
    for f in list(excluded) + list(covered):
        groups.setdefault(uf.f(f), set()).update([f])
    out_rows, gid = [], 0
    dup_bytes = 0
    for root, members in groups.items():
        gid += 1
        allm = set(members) | {excluded.get(m, {}).get("kept") for m in members} | {c["kept"] for m in members for c in covered.get(m, [])}
        allm.discard(None)
        for m in sorted(allm, key=lambda f: quality_key(by[f]), reverse=True):
            r = by[m]
            if m in excluded:
                e = excluded[m]; status = "EXCLUDED"; dup_bytes += r["size"]
            elif m in covered:
                e = covered[m][0]; status = "PARTIAL (overlap excluded)"
                e = dict(e, why="part overlaps kept file: " + e["why"])
                dup_bytes += int(r["size"] * e["coverage"])
            else:
                e = {"type": "", "kept": m, "why": "best version in group"}; status = "KEPT"
            out_rows.append({"group": gid, "status": status, "file": m, "kind": r["kind"], "type": e["type"],
                             "kept_version": e["kept"], "reason": e["why"],
                             "offset_in_kept_s": e.get("offset_in_kept_s", ""), "range_in_this_s": e.get("range_in_this", ""),
                             "range_in_kept_s": e.get("range_in_kept", ""), "duration_s": r.get("duration", ""),
                             "resolution": f'{r.get("width")}x{r.get("height")}', "size_MB": round(r["size"] / MB, 1)})
    with open(ROOT / "duplicates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(out_rows[0].keys())); w.writeheader(); w.writerows(out_rows)

    # usable ranges per kept file (excluding parts already covered by a better file)
    usable = {}
    for r in inv:
        if r["file"] in excluded: continue
        rngs = [[0.0, r.get("duration", 0)]]
        for c in covered.get(r["file"], []):
            s, e = c["range_in_this"]; new = []
            for a0, a1 in rngs:
                if e <= a0 or s >= a1: new.append([a0, a1]); continue
                if s > a0: new.append([a0, s])
                if e < a1: new.append([e, a1])
            rngs = [x for x in new if x[1] - x[0] >= 2]
        usable[r["file"]] = rngs
    save_json("dedup.json", {"excluded": excluded, "partial": covered, "usable": usable, "hints": hints,
                             "exact_groups": exact_groups, "pairs": [(a, b, list(m)) for a, b, m in pairs],
                             "duplicate_bytes": dup_bytes})
    nv = sum(1 for f in excluded if by[f]["kind"] == "video"); npf = len(excluded) - nv
    print(f"exact copy groups: {len(exact_groups)}; excluded videos: {nv}, photos: {npf}; partial overlaps: {len(covered)}")
    print(f"duplicate bytes: {dup_bytes/ (1<<30):.2f} GB")
    kept_v = [f for f in usable if by[f]["kind"] == "video"]
    print(f"kept videos: {len(kept_v)}, usable minutes: {sum(e-s for f in kept_v for s,e in usable[f])/60:.1f}")


if __name__ == "__main__":
    main()

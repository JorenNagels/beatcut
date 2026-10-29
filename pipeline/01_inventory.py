"""Step 1: inventory every video and photo in the source folder -> inventory.csv / inventory.json."""
import csv, re
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ExifTags
from common import SRC, ROOT, EXCLUDE_NAMES, VIDEO_EXT, PHOTO_EXT, ffprobe, save_json

GOPRO_RE = re.compile(r"^G([XHL])(\d{2})(\d{4})", re.I)


def probe_video(p):
    info = ffprobe(p)
    fmt = info.get("format", {})
    tags = {k.lower(): v for k, v in fmt.get("tags", {}).items()}
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    gpmd = [s for s in info.get("streams", []) if s.get("codec_tag_string") == "gpmd"
            or "gopro met" in s.get("tags", {}).get("handler_name", "").lower()]
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0
    w, h = v.get("width", 0), v.get("height", 0)
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    rot = int(v.get("tags", {}).get("rotate", rot) or 0)
    m = GOPRO_RE.match(p.name)
    return {
        "file": p.relative_to(SRC).as_posix(), "kind": "video", "size": p.stat().st_size,
        "duration": round(float(fmt.get("duration", 0) or 0), 3),
        "width": w, "height": h, "rotation": rot, "fps": round(fps, 3),
        "vcodec": v.get("codec_name", ""), "bitrate": int(fmt.get("bit_rate", 0) or 0),
        "has_audio": a is not None, "has_gpmf": bool(gpmd),
        "creation_time": tags.get("creation_time", ""),
        "encoder": tags.get("encoder", "") or v.get("tags", {}).get("encoder", ""),
        "firmware": tags.get("firmware", ""),
        "make": tags.get("com.apple.quicktime.make", "") or ("GoPro" if gpmd else ""),
        "model": tags.get("com.apple.quicktime.model", ""),
        "gopro_chapter": int(m.group(2)) if m else "", "gopro_number": m.group(3) if m else "",
    }


def probe_photo(p):
    row = {"file": p.relative_to(SRC).as_posix(), "kind": "photo", "size": p.stat().st_size}
    try:
        im = Image.open(p)
        row["width"], row["height"] = im.size
        ex = {ExifTags.TAGS.get(k, k): v for k, v in im.getexif().items()}
        sub = im.getexif().get_ifd(0x8769)
        ex.update({ExifTags.TAGS.get(k, k): v for k, v in sub.items()})
        row["creation_time"] = str(ex.get("DateTimeOriginal") or ex.get("DateTime") or "")
        row["make"], row["model"] = str(ex.get("Make", "")).strip("\x00 "), str(ex.get("Model", "")).strip("\x00 ")
        row["orientation"] = ex.get("Orientation", 1)
    except Exception as e:
        row["error"] = str(e)
    return row


def main():
    files = [p for p in sorted(SRC.rglob("*")) if p.is_file() and p.name not in EXCLUDE_NAMES]
    vids = [p for p in files if p.suffix.lower() in VIDEO_EXT]
    phots = [p for p in files if p.suffix.lower() in PHOTO_EXT]
    other = [p for p in files if p not in vids and p not in phots]
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(probe_video, vids)) + list(ex.map(probe_photo, phots))
    for r in rows:
        r["path"] = str((SRC / r["file"]).relative_to(SRC.parent))
    save_json("inventory.json", rows)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "file", k))
    with open(ROOT / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    print(f"videos={len(vids)} photos={len(phots)} other={[p.name for p in other]}")
    print(f"total video duration = {sum(r['duration'] for r in rows if r['kind']=='video')/60:.1f} min")


if __name__ == "__main__":
    main()

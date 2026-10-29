"""Step 1b: recover real shooting times. Re-exports carry the export time in creation_time,
but iPhone exports keep com.apple.quicktime.creationdate inside moov/meta. Photos use EXIF.
Adds shot_time + date_source to inventory.json / inventory.csv."""
import csv, re
from datetime import datetime
from common import SRC, ROOT, load_json, save_json, base

ISO = re.compile(rb"(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)([+-]\d{4})")


def moov_date(p):
    d = p.read_bytes() if p.stat().st_size < 400 << 20 else None
    if d is None: return None
    i = d.find(b"moov")
    m = ISO.search(d, max(0, i - 4)) if i >= 0 else None
    return (m.group(1) + m.group(2)).decode() if m else None


def main():
    inv = load_json("inventory.json")
    for r in inv:
        r["shot_time"], r["date_source"] = "", "unknown (re-export without date)"
        if r["kind"] == "photo" and r.get("creation_time"):
            r["shot_time"] = datetime.strptime(r["creation_time"], "%Y:%m:%d %H:%M:%S").isoformat()
            r["date_source"] = "EXIF DateTimeOriginal"
        elif r["kind"] == "video":
            md = moov_date(SRC / r["file"])
            wa = re.match(r"VIDEO-(\d{4})-(\d\d)-(\d\d)-(\d\d)-(\d\d)-(\d\d)", base(r["file"]))
            if md is None and wa:                       # WhatsApp save: date/time is in the file name
                y, mo, d, h, mi, s = wa.groups()
                r["shot_time"] = f"{y}-{mo}-{d}T{h}:{mi}:{s}"; r["date_source"] = "file name (WhatsApp save time)"
            elif md:
                r["shot_time"] = datetime.strptime(md, "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None).isoformat()
                r["date_source"] = "QuickTime creationdate (local time)"
            elif r.get("model"):          # native iPhone .MOV: creation_time is UTC of capture
                r["shot_time"] = r["creation_time"][:19]; r["date_source"] = "camera creation_time (UTC)"
    save_json("inventory.json", inv)
    keys = sorted({k for r in inv for k in r}, key=lambda k: (k != "file", k))
    with open(ROOT / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(inv)
    for r in inv:
        if r["shot_time"] and r["kind"] == "video": print(r["file"], r["shot_time"], r["date_source"])


if __name__ == "__main__":
    main()

"""Step 4: contact sheets for the visual pass (a human/AI looks at these and writes tags.json).
One thumbnail every STEP seconds of every kept video, labelled "<short name> m:ss", 8 per row.
Also a sheet of all photos. Output: sheets/*.jpg + sheets/index.json"""
import re, sys
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, CACHE, SRC, DEFAULT_FONT, load_json, save_json, file_id, base
from PIL import ImageOps

STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 6
TW, TH, COLS, ROWS = 240, 135, 8, 7
OUT = ROOT / "sheets"; OUT.mkdir(exist_ok=True)
try:
    FONT = ImageFont.truetype(str(DEFAULT_FONT), 15)
except OSError:
    FONT = ImageFont.load_default()


def short(n):
    d = n.rsplit("/", 1)[0] + "/" if "/" in n else ""        # keep the folder: two cameras can share file names
    n = base(n).rsplit(".", 1)[0]
    return d + (n[:8] if re.match(r"^[0-9A-F]{8}-", n, re.I) else n)


def order_key(n):
    n = base(n)
    m = re.match(r"G[XH](\d\d)(\d{4})", n)
    if m: return (0, int(m.group(2)), int(m.group(1)))
    m = re.match(r"IMG_(\d+)", n)
    if m: return (1, int(m.group(1)), 0)
    return (2, 0, n)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, len(text) * 9 + 6, 18], fill=(0, 0, 0))
    d.text((3, 1), text, fill=(255, 230, 0), font=FONT)


def main():
    idx = load_json("signals_index.json")
    files = sorted(idx, key=order_key)
    only = load_json(sys.argv[2])["files"] if len(sys.argv) > 2 else None     # e.g. cache/new_files.json
    if only: files = [f for f in files if f in only]
    thumbs = []
    for f in files:
        fdir = CACHE / "frames" / idx[f]
        for p in sorted(fdir.glob("*.jpg")):
            t = int(p.stem)
            if t % STEP == 0:
                thumbs.append((f, t, p))
    per = COLS * ROWS
    sheets = []
    for s in range(0, len(thumbs), per):
        chunk = thumbs[s:s + per]
        sheet = Image.new("RGB", (COLS * TW, ROWS * TH), (30, 30, 30))
        for k, (f, t, p) in enumerate(chunk):
            im = Image.open(p).resize((TW, TH))
            label(im, f"{short(f)} {t // 60}:{t % 60:02d}")
            sheet.paste(im, ((k % COLS) * TW, (k // COLS) * TH))
        name = f"{'new' if only else 'sheet'}_{len(sheets) + 1:03d}.jpg"
        sheet.save(OUT / name, quality=82)
        sheets.append({"sheet": name, "items": [[f, t] for f, t, _ in chunk]})
    # photos
    inv = load_json("inventory.json"); dd = load_json("dedup.json")
    photos = [r["file"] for r in inv if r["kind"] == "photo" and r["file"] not in dd["excluded"]]
    sheet = Image.new("RGB", (6 * 320, ((len(photos) + 5) // 6) * 240), (30, 30, 30))
    for k, f in enumerate(photos):
        im = ImageOps.exif_transpose(Image.open(SRC / f)).convert("RGB"); im.thumbnail((320, 240))
        cell = Image.new("RGB", (320, 240), (30, 30, 30)); cell.paste(im, ((320 - im.width) // 2, (240 - im.height) // 2))
        label(cell, short(f)[:14]); sheet.paste(cell, ((k % 6) * 320, (k // 6) * 240))
    sheet.save(OUT / "photos.jpg", quality=85)
    save_json("sheets/index.json", sheets)
    print(f"{len(thumbs)} thumbs on {len(sheets)} sheets (+ photos.jpg)")


if __name__ == "__main__":
    main()

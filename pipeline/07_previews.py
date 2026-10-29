"""Step 7: small looping preview MP4s (+ poster JPG) for every candidate, photo thumbnails,
and a check sheet (4 frames per candidate) for verification.
Output: review/previews/<id>.mp4, review/previews/<id>.jpg, review/photos/*.jpg, sheets/candidates_check*.jpg"""
import subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageOps
from common import ROOT, SRC, FFMPEG, load_json

OUT = ROOT / "review" / "previews"; OUT.mkdir(parents=True, exist_ok=True)
PH = ROOT / "review" / "photos"; PH.mkdir(parents=True, exist_ok=True)


def preview(c):
    mp4, jpg = OUT / f"{c['id']}.mp4", OUT / f"{c['id']}.jpg"
    if mp4.exists() and "--force" not in sys.argv:
        return
    vf = "scale=-2:360" if c["vertical"] else "scale=480:-2"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{c['start']:.2f}", "-t", f"{c['end'] - c['start']:.2f}",
                    "-i", str(SRC / c["file"]), "-an", "-vf", f"{vf},fps=24", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
    mid = (c["end"] - c["start"]) / 2
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{mid:.2f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "4", str(jpg)], check=True)


def frames4(c):
    ims = []
    for k in range(4):
        t = c["start"] + (c["end"] - c["start"]) * (k + 0.5) / 4
        raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.2f}", "-i", str(SRC / c["file"]), "-frames:v", "1",
                              "-vf", "scale=240:135:force_original_aspect_ratio=decrease,pad=240:135:(ow-iw)/2:(oh-ih)/2",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        ims.append(Image.frombytes("RGB", (240, 135), raw) if len(raw) == 240 * 135 * 3 else Image.new("RGB", (240, 135)))
    return ims


def main():
    cands = load_json("candidates.json")
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(preview, cands))
        rows = list(ex.map(frames4, cands))
    for b in load_json("photos_best.json"):
        im = ImageOps.exif_transpose(Image.open(SRC / b["file"])).convert("RGB"); im.thumbnail((900, 900))
        out = PH / (b["file"].rsplit(".", 1)[0] + ".jpg"); out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, quality=82)
    per = 15
    for s in range(0, len(cands), per):
        sheet = Image.new("RGB", (4 * 240 + 330, per * 135), (25, 25, 25)); d = ImageDraw.Draw(sheet)
        for i, (c, ims) in enumerate(zip(cands[s:s + per], rows[s:s + per])):
            for k, im in enumerate(ims): sheet.paste(im, (k * 240, i * 135))
            d.text((970, i * 135 + 8), f"{c['id']} {c['cat'].upper()} {c['score']}\n{c['file'][:30]}\n{c['start']:.0f}-{c['end']:.0f}s\n{c['reason'][:46]}\n{c['reason'][46:92]}", fill=(255, 230, 0))
        sheet.save(ROOT / "sheets" / f"candidates_check{s // per + 1}.jpg", quality=80)
    print("previews:", len(cands))


if __name__ == "__main__":
    main()

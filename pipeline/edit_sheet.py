"""Contact sheet of the rendered edit: one frame per shot (60% into the shot) with section + source labels."""
import json, subprocess, sys
from PIL import Image, ImageDraw
from common import ROOT, FFMPEG, load_json, edl_file, out_name
mode = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "preview"
E = load_json(edl_file()); segs = E["segments"]
TW, TH, C = 240, 135, 8
rows = (len(segs) + C - 1) // C
sheet = Image.new("RGB", (C * TW, rows * (TH + 26)), (255, 255, 255)); d = ImageDraw.Draw(sheet)
for i, s in enumerate(segs):
    t = s["t0"] + s["dur"] * 0.6
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(ROOT / "render" / f"{out_name(mode)}.mp4"), "-frames:v", "1",
                          "-vf", f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    im = Image.frombytes("RGB", (TW, TH), raw)
    x, y = (i % C) * TW, (i // C) * (TH + 26)
    sheet.paste(im, (x, y + 26))
    lab = s.get("namecard") or ("TITLE" if s.get("title") else "")
    d.text((x + 2, y + 1), f"{i} {s['section'][:9]} {int(s['t0'] // 60)}:{s['t0'] % 60:04.1f} {lab}", fill=(180, 0, 0))
    d.text((x + 2, y + 13), f"{s['src'][:22]} {s.get('in') if s.get('in') is not None else ''}", fill=(60, 60, 60))
sheet.save(ROOT / "sheets" / f"edit_{out_name(mode)}.jpg", quality=82)
print(f"sheets/edit_{out_name(mode)}.jpg")

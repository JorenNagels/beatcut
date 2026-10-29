"""Contact sheet of a clip section with timestamps and a loudness/voice strip under each frame.
python scripts/inspect_clip.py <file> <start> <dur> <fps> <out.png>"""
import json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, SRC, FFMPEG, load_json
f, a, d, fps, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
TW, TH = 240, 135
raw = subprocess.run([FFMPEG, "-v", "error", "-ss", str(a), "-t", str(d), "-i", str(SRC / f), "-vf",
                      f"fps={fps},scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, TH, TW, 3)
au = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-ss", str(a), "-t", str(d), "-i", str(SRC / f), "-vn", "-ac", "1",
                                   "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
ev = [e for e in load_json("events.json") if e["file"] == f and e["kind"] == "voice"]
C = 8; rows = (len(fr) + C - 1) // C
sheet = Image.new("RGB", (C * TW, rows * (TH + 16)), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
for i, im in enumerate(fr):
    t = a + i / fps; x, y = (i % C) * TW, (i // C) * (TH + 16)
    sheet.paste(Image.fromarray(im), (x, y))
    seg = au[int((t - a) * 8000): int((t - a + 1 / fps) * 8000)]
    db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-6) if len(seg) else -90
    v = any(e["start"] - .3 <= t <= e["end"] + .3 for e in ev)
    dr.rectangle([x, y + TH, x + int(TW * min(1, max(0, (db + 50) / 45))), y + TH + 6], fill=(255, 80, 80) if v else (90, 160, 255))
    dr.text((x + 2, y + 1), f"{int(t // 60)}:{t % 60:05.2f}", fill=(255, 255, 0))
sheet.save(ROOT / "sheets" / out)
print(out, len(fr), "frames; voice events:", [(round(e['start'], 1), round(e['end'], 1)) for e in ev if a <= e['start'] <= a + d])

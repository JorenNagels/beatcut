"""Timeline view of one stretch of a clip: filmstrip + waveform + spoken words + detected sounds in one PNG.
   timeline <file> <start> <end> [--n 10]      e.g.  timeline GX014904.mp4 8 26

Use it to decide exact in/out points (where the laugh starts, where a sentence ends) instead of guessing from
contact sheets. Rows: frames (n evenly spaced, labelled), loudness envelope (red where 19b_sounds heard laughter,
orange cheering, purple singing, blue voice peaks from 05_events), the Whisper words at their times (19_transcribe)
and a second ruler. Output: sheets/timeline_<file>_<start>.png"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, SRC, FFMPEG, DEFAULT_FONT, load_json, file_id

args = [a for a in sys.argv[1:]]
N = int(args[args.index("--n") + 1]) if "--n" in args else 10
f, a, b = args[0], float(args[1]), float(args[2])
d = b - a
Wd = 1800; TW = Wd // N; TH = TW * 9 // 16
WAVE, WORDS, RULER = 110, 70, 22
im = Image.new("RGB", (Wd, TH + WAVE + WORDS + RULER + 8), (250, 250, 250)); dr = ImageDraw.Draw(im)
font = ImageFont.truetype(str(DEFAULT_FONT), 15); small = ImageFont.truetype(str(DEFAULT_FONT), 12)
X = lambda t: int((t - a) / d * (Wd - 1))
mm = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"

for k in range(N):                                                      # filmstrip
    t = a + (k + 0.5) * d / N
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(SRC / f), "-frames:v", "1", "-vf",
                          f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if len(raw) == TW * TH * 3: im.paste(Image.frombytes("RGB", (TW, TH), raw), (k * TW, 0))
    dr.text((k * TW + 4, 3), mm(t), font=small, fill=(255, 255, 0), stroke_width=2, stroke_fill=(0, 0, 0))

y0 = TH + 4                                                             # waveform, coloured by sound events
x = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-ss", str(a), "-t", str(d), "-i", str(SRC / f), "-vn", "-ac", "1",
                                  "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32)
col = {"laugh": (220, 40, 40), "cheer": (240, 140, 20), "sing": (140, 60, 200), "shout": (200, 40, 120), "voice": (60, 120, 230)}
ev = [e for e in load_json("sounds.json", []) if e["file"] == f] + \
     [e for e in load_json("events.json", []) if e["file"] == f and e["kind"] == "voice"]
for px in range(Wd):
    t = a + px / Wd * d; seg = x[int((t - a) * 8000): int((t - a + d / Wd) * 8000) + 1]
    db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-6) if len(seg) else -90
    h = int(WAVE * min(1, max(0, (db + 55) / 50)))
    kind = next((e["kind"] for e in sorted(ev, key=lambda e: e["kind"] == "voice") if e["start"] <= t <= e["end"]), None)
    dr.line([(px, y0 + WAVE - h), (px, y0 + WAVE)], fill=col.get(kind, (170, 175, 185)))
for k, (name, c) in enumerate(col.items()):
    dr.text((Wd - 330 + k * 66, y0 + 2), name, font=small, fill=c)

y1 = y0 + WAVE + 4                                                      # words, two staggered rows
T = load_json(f"transcripts/{file_id(f)}.json") or {"segments": []}
k = 0
for s in T["segments"]:
    for w in s["words"]:
        if a <= w["s"] <= b:
            dr.line([(X(w["s"]), y1), (X(w["s"]), y1 + 8)], fill=(0, 0, 0))
            dr.text((X(w["s"]) + 2, y1 + 6 + (k % 2) * 26), w["w"], font=font,
                    fill=(20, 20, 20) if w["p"] > 0.5 else (150, 150, 150)); k += 1
if not T["segments"]: dr.text((6, y1 + 10), "no transcript (19_transcribe)", font=font, fill=(150, 150, 150))

y2 = y1 + WORDS                                                         # ruler
for s in np.arange(np.ceil(a), b + 0.01, 1.0 if d <= 40 else 5.0):
    dr.line([(X(s), y2), (X(s), y2 + 6)], fill=(60, 60, 60)); dr.text((X(s) + 2, y2 + 4), mm(s), font=small, fill=(60, 60, 60))
out = ROOT / "sheets" / f"timeline_{f.replace('/', '_').rsplit('.', 1)[0]}_{int(a)}.png"
out.parent.mkdir(exist_ok=True); im.save(out)
print(out.relative_to(ROOT).as_posix())

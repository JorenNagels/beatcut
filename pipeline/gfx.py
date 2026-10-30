"""Look at the graphics without rendering the film: stills of the Remotion graphics over the shots under them, as one
contact sheet (preview size).   gfx [list | <item> | all] [--frames 6] [--edl <name>]

  gfx list       the graphics of this EDL: number, time, component, text
  gfx 3          graphic 3 at --frames moments from its start to its end (pop-in, middle, exit)
  gfx  / gfx all every graphic once, at 40 % of its length
Writes render/gfx/check_<name>.jpg and prints its path. The background is the source frame (fill crop, letterbox),
not the graded film. Needs Remotion (python install.py --remotion)."""
import shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, SRC, FFMPEG, DEFAULT_FONT, load_json, cfg, event_path, edl_file, out_name, frame_size
import graphics_lib

args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in ("--edl", "--frames")]
what = args[0] if args else "all"
N = int(sys.argv[sys.argv.index("--frames") + 1]) if "--frames" in sys.argv else 6
E = load_json(edl_file()); FPS = E["fps"]
W, H = frame_size(E.get("format", "16:9"), "preview")
font = ROOT / "render" / "fonts" / "title.ttf"
if not font.exists():
    font.parent.mkdir(parents=True, exist_ok=True); shutil.copy(event_path(cfg("style.font", DEFAULT_FONT)), font)
if not graphics_lib.available(): raise SystemExit("Remotion is not installed: python install.py --remotion")
its = graphics_lib.items(E, W, H, FPS)
total = round(E["duration"] * FPS)
label = lambda p: str(p.get("text") or p.get("big") or p.get("title") or "")[:40]

if what == "list":
    for k, (f, c, p) in enumerate(its):
        print(f"{k:3d}  {f / FPS:7.2f}s  {p['frames'] / FPS:5.2f}s  {c:12s} {label(p)}")
    raise SystemExit
if what == "all":
    picks = [(k, f + round(p["frames"] * 0.4)) for k, (f, c, p) in enumerate(its)]
else:
    k = int(what); f, c, p = its[k]
    picks = [(k, f + min(p["frames"] - 1, round(p["frames"] * x))) for x in [0.04, 0.12, 0.25, 0.5, 0.8, 0.96][:N]] if N <= 6 else \
            [(k, f + round(p["frames"] * (i + 0.5) / N)) for i in range(N)]
if not picks: raise SystemExit("no graphics in this EDL")

tmp = ROOT / "render" / "gfx" / f"stills_{out_name('check')}"
shutil.rmtree(tmp, ignore_errors=True)
graphics_lib.stills(its, font, W, H, FPS, total, [fr for _, fr in picks], tmp)


def background(fr):
    """the source frame under timeline frame fr, cropped to fill the frame"""
    t = fr / FPS
    s = next((s for s in E["segments"] if s["t0"] <= t < s["t0"] + s["frames"] / FPS), E["segments"][-1])
    off = t - s["t0"]
    parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["frames"] / FPS, "slowmo": s.get("slowmo", 1.0)}]
    for p in parts:
        if off < p["dur"] or p is parts[-1]: break
        off -= p["dur"]
    vf = (f"transpose={s['transpose']}," if s.get("transpose") else "") + \
         f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    src, at = SRC / p["src"], p["in"] + off * p.get("slowmo", 1.0)
    cmd = [FFMPEG, "-v", "error", "-ss", f"{max(0, at):.3f}"] + (["-loop", "1"] if s["type"] == "photo" else []) + \
          ["-i", str(src), "-frames:v", "1", "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"]
    r = subprocess.run(cmd, capture_output=True)
    img = Image.open(__import__("io").BytesIO(r.stdout)).convert("RGB") if r.stdout else Image.new("RGB", (W, H), "gray")
    if s.get("letterbox") and W > H:
        d = ImageDraw.Draw(img); lb = round(H * 0.1278)
        d.rectangle([0, 0, W, lb], fill="black"); d.rectangle([0, H - lb, W, H], fill="black")
    return img


cols = min(3, len(picks)); rows = -(-len(picks) // cols)
sheet = Image.new("RGB", (cols * W, rows * (H + 28)), "white")
lf = ImageFont.truetype(str(font), 20)
for i, (k, fr) in enumerate(picks):
    img = background(fr)
    ov = tmp / f"{fr}.png"
    if ov.exists(): img.paste(Image.open(ov).convert("RGBA"), (0, 0), Image.open(ov).convert("RGBA"))
    x, y = (i % cols) * W, (i // cols) * (H + 28)
    sheet.paste(img, (x, y + 28))
    f, c, p = its[k]
    ImageDraw.Draw(sheet).text((x + 6, y + 3), f"#{k} {c} {label(p)}  t={fr / FPS:.2f}s (+{(fr - f) / FPS:.2f})", fill="black", font=lf)
out = ROOT / "render" / "gfx" / f"check_{out_name('all' if what == 'all' else what)}.jpg"
sheet.save(out, quality=88)
print(out)

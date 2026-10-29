"""Search the footage by description (needs 20_clip).   search "powder spray" [--n 24] [--file GX014904.mp4]

Ranks every 2-second frame by similarity to the text, merges hits less than 6 s apart in the same file, prints
"file  m:ss-m:ss  score" and writes sheets/search_<words>.jpg (one frame per hit, labelled) to look at.
Several phrasings help: search "falling in the snow" "lying in the snow laughing"."""
import re, sys
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, CACHE, load_json
import clip_lib

args = sys.argv[1:]
N = int(args[args.index("--n") + 1]) if "--n" in args else 24
ONLY = args[args.index("--file") + 1] if "--file" in args else None
queries = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--n", "--file"))]
if not queries: raise SystemExit(__doc__)
q = clip_lib.embed_text(queries).mean(0); q /= np.linalg.norm(q)
idx = load_json("signals_index.json")
hits = []
for f, (t, e) in clip_lib.index().items():
    if ONLY and f != ONLY: continue
    s = e @ q
    for i in np.argsort(-s)[:20]: hits.append((float(s[i]), f, float(t[i])))
hits.sort(reverse=True)
wins = []
for sc, f, t in hits:
    w = next((w for w in wins if w["file"] == f and w["start"] - 6 <= t <= w["end"] + 6), None)
    if w: w["start"], w["end"] = min(w["start"], t), max(w["end"], t + 2); continue
    if len(wins) < N: wins.append({"file": f, "start": t, "end": t + 2, "score": sc, "t": t})
mm = lambda t: f"{int(t // 60)}:{int(t % 60):02d}"
for w in wins: print(f"{w['score']:.3f}  {w['file']}  {mm(w['start'])}-{mm(w['end'])}")
TW, TH, C = 320, 180, 6
sheet = Image.new("RGB", (C * TW, ((len(wins) + C - 1) // C) * (TH + 18)), (250, 250, 250)); d = ImageDraw.Draw(sheet)
for i, w in enumerate(wins):
    x, y = (i % C) * TW, (i // C) * (TH + 18)
    p = CACHE / "frames" / idx[w["file"]] / f"{int(w['t']):05d}.jpg"
    if p.exists(): sheet.paste(Image.open(p).resize((TW, TH)), (x, y + 18))
    d.text((x + 3, y + 3), f"{i + 1}. {w['file'][:30]} {mm(w['start'])} ({w['score']:.2f})", fill=(30, 30, 30))
slug = re.sub(r"[^a-z0-9]+", "_", queries[0].lower()).strip("_")[:40]
(ROOT / "sheets").mkdir(exist_ok=True)
sheet.save(ROOT / "sheets" / f"search_{slug}.jpg", quality=85)
print(f"sheets/search_{slug}.jpg")

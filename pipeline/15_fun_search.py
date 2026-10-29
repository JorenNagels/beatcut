"""Step 15: find untagged 'fun' moments (talking, laughing, shouting) from voice events across all kept videos.
Merges nearby voice peaks into windows, ranks them, skips windows already covered by visual tags, and writes a
check sheet (3 frames per window) for the visual pass. Output: fun_windows.json, sheets/fun_*.jpg"""
import json, subprocess
from collections import defaultdict
from PIL import Image, ImageDraw
from common import ROOT, SRC, FFMPEG, load_json, save_json

ev = [e for e in load_json("events.json") if e["kind"] == "voice"]
tags = load_json("tags.json")["tags"]; dd = load_json("dedup.json"); inv = {r["file"]: r for r in load_json("inventory.json")}
by = defaultdict(list)
for e in ev: by[e["file"]].append(e)
wins = []
for f, es in by.items():
    if f in dd["excluded"]: continue
    es.sort(key=lambda e: e["start"]); cur = None
    for e in es:
        if cur and e["start"] - cur["end"] < 2.5:
            cur["end"] = e["end"]; cur["score"] += e["score"]; cur["n"] += 1
        else:
            if cur: wins.append(cur)
            cur = {"file": f, "start": e["start"], "end": e["end"], "score": e["score"], "n": 1}
    if cur: wins.append(cur)
def covered(w):
    return any(t["file"] == w["file"] and t["start"] - 1 <= w["start"] and w["end"] <= t["end"] + 1 for t in tags)
wins = [w for w in wins if not covered(w) and w["score"] >= 0.6]
wins.sort(key=lambda w: -w["score"])
wins = wins[:60]
for i, w in enumerate(wins): w["id"] = f"f{i:02d}"
save_json("fun_windows.json", wins)
TW, TH = 200, 113
for s in range(0, len(wins), 20):
    chunk = wins[s:s + 20]
    sheet = Image.new("RGB", (4 * TW + 260, len(chunk) * TH), (25, 25, 25)); d = ImageDraw.Draw(sheet)
    for i, w in enumerate(chunk):
        for k, t in enumerate([w["start"] - 1.5, w["start"], (w["start"] + w["end"]) / 2, w["end"] + 1]):
            raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", str(SRC / w["file"]), "-frames:v", "1",
                                  "-vf", f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(raw) == TW * TH * 3: sheet.paste(Image.frombytes("RGB", (TW, TH), raw), (k * TW, i * TH))
        d.text((4 * TW + 6, i * TH + 6), f"{w['id']}  score {w['score']:.1f} ({w['n']} peaks)\n{w['file'][:34]}\n{w['start']:.1f}-{w['end']:.1f}s", fill=(255, 230, 0))
    sheet.save(ROOT / "sheets" / f"fun_{s // 20 + 1}.jpg", quality=80)
print(len(wins), "fun windows")

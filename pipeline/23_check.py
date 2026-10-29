"""Step 23: self-check of a render before the user sees it.   23_check preview|final [--edl <name>]

Decodes the render once (small) and checks every shot and cut against the EDL:
  picture  black frames, single-frame flashes, frozen frames (source ran out -> last frame held), shots under 0.35 s,
           a cut that looks like no cut (same scene on both sides)
  sound    the music dropping out (silence), clipping, a loudness jump of > 10 dB across a cut, integrated loudness
           (aim: about -14 LUFS for YouTube/Instagram/TikTok)
Writes check_<name>.json (issues with film time, shot number, source and a suggested fix) and sheets/check_<name>.jpg
(frames -3..+3 around every flagged cut). Fix the plan, re-render, check again (max 3 rounds; then tell the user
what is left)."""
import re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, FFMPEG, load_json, save_json, edl_file, out_name

MODE = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "preview"
E = load_json(edl_file()); FPS = E["fps"]; segs = E["segments"]
inv = {r["file"]: r for r in load_json("inventory.json")}
VIDEO = ROOT / "render" / f"{out_name(MODE)}.mp4"
TW = 96
probe = subprocess.run([FFMPEG, "-v", "error", "-i", str(VIDEO), "-frames:v", "1", "-vf", f"scale={TW}:-2", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True).stdout
TH = len(probe) // TW
raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(VIDEO), "-vf", f"scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, TH, TW).astype(np.float32)
lum = fr.mean((1, 2))
diff = np.r_[99, np.abs(np.diff(fr, axis=0)).mean((1, 2))]
issues = []
mm = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"


def src_of(s):
    return f"{s['src']} @{s['in']:.1f}s" if s["type"] == "video" else s["src"]


def add(kind, i, t, detail, fix):
    issues.append({"kind": kind, "shot": i, "time": mm(t), "t": round(t, 2), "source": src_of(segs[i]), "detail": detail, "fix": fix})


fin, fout = E.get("fades", [1.0, 3.0])
for i, s in enumerate(segs):
    a, n = round(s["t0"] * FPS), s["frames"]
    lo, hi = max(a, round(fin * FPS) + 1 if a == 0 else a), min(a + n, len(lum) - round(fout * FPS))
    if n < 0.35 * FPS: add("short", i, s["t0"], f"{n / FPS:.2f}s shot", "merge with a neighbour or give it a beat more")
    if s.get("credits") or s.get("dim") or hi <= lo: continue
    dark = lum[lo:hi] < 14
    if dark.sum() >= 3:
        add("black", i, s["t0"] + (lo - a + int(np.argmax(dark))) / FPS, f"{int(dark.sum())} dark frames",
            "move the in-point or take() the dark part (pocket / lens covered / night)")
    if s["section"] != "title":
        for k in range(lo + 1, hi - 1):
            if lum[k] - lum[k - 1] > 60 and lum[k] - lum[k + 1] > 60:
                add("flash", i, k / FPS, f"one-frame flash (+{lum[k] - lum[k - 1]:.0f})", "shift the shot a few frames"); break
    if s["type"] == "video" and s["section"] != "title":
        still = diff[lo + 1:hi] < 0.12
        runs = np.diff(np.r_[0, still.astype(int), 0]); st, en = np.where(runs == 1)[0], np.where(runs == -1)[0]
        long = [(x, y) for x, y in zip(st, en) if y - x >= 8]
        if long:
            x, y = long[0]
            parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": s.get("slowmo", 1.0)}]
            over = [p for p in parts if p["in"] + p["dur"] * p.get("slowmo", 1) > inv[p["src"]]["duration"] - 0.05]
            add("frozen", i, (lo + 1 + x) / FPS, f"{(y - x) / FPS:.1f}s without movement" + (" (source ends)" if over else ""),
                "start earlier / make the shot shorter: the source runs out" if over else "a static moment: use another part")
for i in range(1, len(segs)):                                 # cuts that do not look like cuts
    c = round(segs[i]["t0"] * FPS)
    if c < 2 or c + 2 >= len(fr) or segs[i]["section"] == "title" or segs[i - 1]["section"] == "title": continue
    x, y = fr[c - 2].ravel(), fr[c + 1].ravel()
    if np.corrcoef(x, y)[0, 1] > 0.97 and abs(x.mean() - y.mean()) < 6:
        add("no-cut", i, segs[i]["t0"], "both sides look the same", "pick a different shot or join the two shots")

# ---- sound ----
SR = 16000
au = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-i", str(VIDEO), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                  capture_output=True).stdout, np.float32)
win = SR // 4
db = 20 * np.log10(np.sqrt((au[: len(au) // win * win].reshape(-1, win) ** 2).mean(1)) + 1e-9)
quiet = db < -48
q0, q1 = 2, len(db) - int(4 * max(1, fout))                  # ignore the very start and the fade at the end
m = np.diff(np.r_[0, quiet[q0:q1].astype(int), 0])
for x, y in zip(np.where(m == 1)[0], np.where(m == -1)[0]):
    if y - x >= 2:                                            # >= 0.5 s
        t = (q0 + x) / 4; i = max(n for n, s in enumerate(segs) if s["t0"] <= t)
        add("silence", i, t, f"{(y - x) / 4:.1f}s of silence", "the music stops: extend or overlap the music cues")
clip = int((np.abs(au) > 0.999).sum())
if clip > 50:                                                 # a few overshooting AAC samples are inaudible
    issues.append({"kind": "clipping", "shot": None, "time": "", "t": 0, "source": "", "detail": f"{clip} clipped samples",
                        "fix": "lower cam_audio on the loudest bite"})
for i in range(1, len(segs)):
    k = int(segs[i]["t0"] * 4)
    if 2 <= k < len(db) - 2:
        jump = np.maximum(db[k:k + 2], -60).mean() - np.maximum(db[k - 2:k], -60).mean()
        if jump > 10 and not quiet[k - 2:k].any():          # out of a silence: already reported as silence
            add("loud-cut", i, segs[i]["t0"], f"+{jump:.0f} dB at the cut", "lower cam_audio on this shot or duck more")
ebur = subprocess.run([FFMPEG, "-v", "info", "-i", str(VIDEO), "-vn", "-af", "ebur128", "-f", "null", "-"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur)[-1]) if "LUFS" in ebur else None

order = {"black": 0, "frozen": 1, "silence": 2, "flash": 3, "loud-cut": 4, "no-cut": 5, "short": 6, "clipping": 7}
issues.sort(key=lambda x: (order[x["kind"]], x["t"]))
save_json(f"check_{out_name(MODE)}.json", {"video": VIDEO.name, "lufs": lufs, "issues": issues})
print(f"{VIDEO.name}: {len(segs)} shots, {len(issues)} issues, loudness {lufs} LUFS (target about -14)")
for x in issues:
    print(f"  {x['kind']:9s} {x['time']:>7s}  shot {x['shot']}  {x['source'][:40]:40s} {x['detail']}  -> {x['fix']}")

flag = sorted({x["shot"] for x in issues if x["shot"] is not None})[:30]
if flag:
    S = 7; sheet = Image.new("RGB", (S * TW * 2, len(flag) * (TH * 2 + 16)), (250, 250, 250)); d = ImageDraw.Draw(sheet)
    for r, i in enumerate(flag):
        c = round(segs[i]["t0"] * FPS); y = r * (TH * 2 + 16)
        d.text((4, y + 2), f"shot {i} at {mm(segs[i]['t0'])}: " + ", ".join(x["kind"] for x in issues if x["shot"] == i), fill=(180, 0, 0))
        for k in range(-3, 4):
            if 0 <= c + k < len(fr):
                sheet.paste(Image.fromarray(fr[c + k].astype(np.uint8)).resize((TW * 2, TH * 2)), ((k + 3) * TW * 2, y + 16))
    sheet.save(ROOT / "sheets" / f"check_{out_name(MODE)}.jpg", quality=85)
    print(f"sheets/check_{out_name(MODE)}.jpg")

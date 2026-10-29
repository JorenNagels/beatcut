"""Step 18: shot list of the finished film (shotlist.csv) from edl.json - every shot with film time, section,
source file, in/out seconds in the source, speed, sound and why it is there."""
import csv
from common import ROOT, load_json
E = load_json("edl.json")
rows = []
for i, s in enumerate(E["segments"], 1):
    parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": s.get("slowmo", 1.0)}]
    src = " + ".join(f"{p['src']} @{p['in']:.1f}s" + (" (slow-mo 50%)" if p.get("slowmo", 1) < 1 else "") for p in parts) \
        if s["type"] == "video" else s["src"]
    t = s["t0"]
    rows.append({"#": i, "film_time": f"{int(t // 60)}:{t % 60:04.1f}", "length_s": round(s["dur"], 2), "section": s["section"],
                 "source": src, "what": s.get("why", ""), "category": s.get("cat", ""),
                 "camera_sound": "on" if s.get("cam_audio") else "off", "sound_note": s.get("cam_note", ""),
                 "look": ", ".join(k for k in ("letterbox", "bite", "transpose", "title", "credits") if s.get(k))})
with open(ROOT / "shotlist.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "shots -> shotlist.csv")

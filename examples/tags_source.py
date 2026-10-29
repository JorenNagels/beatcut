"""Visual tags, written by hand while looking at the contact sheets (sheets/*.jpg, 1 frame / 6 s).
Copy to the event folder as tags_source.py, fill in, run:  python tags_source.py  -> tags.json next to it.
cat: scenic | faces | action | lifestyle | crash | boring    rating: 1..5 (5 = could open the film)"""
import json
from pathlib import Path

# people described by clothing until names are known (used in notes / people lists)
P = {"white": "white parka, white helmet", "navy": "navy jacket", "blue": "blue jacket, blue goggles"}

# (file, start_s, end_s, cat, rating, note, people)
T = [
    ("GX014875.mp4", 0, 32, "scenic", 4, "high alpine panorama with sunstar, bluebird", []),
    ("GX014888.mp4", 0, 29, "lifestyle", 5, "chairlift ride: selfie with blue goggles, friend on lift", ["blue"]),
    ("GX014890.mp4", 0, 26, "crash", 5, "friend wiped out in whiteout, lying in the snow, others laughing", ["white"]),
    ("GX014894.mp4", 22, 46, "action", 4, "skiing between snow-laden fir trees, friend ahead", []),
    ("IMG_5532.mp4", 0, 36, "lifestyle", 5, "dinner in wooden restaurant, everyone laughing", []),
]

# shooting day for files whose dates were lost (re-exports): from weather/light, GoPro file order, dated phone clips
DAY = {}
for f in ["GX0148%02d.mp4" % n for n in range(74, 89)]: DAY[f] = "2026-03-13"

# photos: (rating, cat, note) - for the best-15 pick on the review page
PHOTOS = {
    "IMG_4029.jpg": (5, "faces", "whole group posing in the sun, clouds behind"),
}

if __name__ == "__main__":
    out = {"people": P, "tags": [dict(zip(("file", "start", "end", "cat", "rating", "note", "people"), t)) for t in T],
           "day_estimates": DAY, "photos": {k: {"rating": v[0], "cat": v[1], "note": v[2]} for k, v in PHOTOS.items()}}
    Path(__file__).resolve().with_name("tags.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(len(T), "video tags,", len(PHOTOS), "photo ratings")

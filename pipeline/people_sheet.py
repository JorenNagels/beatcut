"""Contact sheet of people/*.jpg for checking face clusters (sheets/people_check.jpg)."""
from PIL import Image, ImageDraw
from common import ROOT, load_json

P = load_json("people.json"); W = 4 * 180
sh = Image.new("RGB", (W * 3, ((len(P) + 2) // 3) * 200), (255, 255, 255)); d = ImageDraw.Draw(sh)
for k, p in enumerate(P):
    x0, y0 = (k % 3) * W, (k // 3) * 200
    ims = [ROOT / "people" / f"{p['id']}.jpg"] + [ROOT / "people" / f"{p['id']}_{j}.jpg" for j in range(p["extras"])]
    for j, f in enumerate(ims):
        im = Image.open(f); im.thumbnail((175, 175)); sh.paste(im, (x0 + j * 180, y0 + 20))
    d.text((x0 + 4, y0 + 3), f"{p['id']} n={p['n_faces']}", fill=(200, 0, 0))
(ROOT / "sheets").mkdir(exist_ok=True)
sh.save(ROOT / "sheets" / "people_check.jpg", quality=85)

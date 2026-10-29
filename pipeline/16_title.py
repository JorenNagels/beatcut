"""Step 16: kinetic title animation as transparent PNG frames, timed to the music beat (title = 8 beats).
Texts come from edl.json title_anim (big / sub / tag; set in event.yaml title.*), font from render/fonts/title.ttf.
  beat 0  white flash + BIG word slams in (scale 1.7 -> 1.0, RGB split, shake)
  beat 2  SUB line wipes in left -> right
  beat 4  TAG pops (white box, black text, overshoot)
  beat 6  BIG word flips to outline for a beat, small shake on every beat
  beat 7.5 glitch slices, then everything is gone on the next bar (hard cut)
python 16_title.py <width> <height> <frames> <bpm> [--edl <name>]  -> render/title_<w>/0000.png ...
Sizes follow U = the height of a 16:9 frame of this width, so the title also fits 9:16 / 1:1."""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
from common import ROOT, load_json, edl_file, out_name

W, H, N, BPM = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
FPS, BEAT = 30, 60 / BPM
OUT = ROOT / "render" / f"title_{out_name(str(W))}"; OUT.mkdir(parents=True, exist_ok=True)
FONT = str(ROOT / "render" / "fonts" / "title.ttf")
TA = load_json(edl_file())["title_anim"]
U = min(H, W * 9 / 16)


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_name(weight)          # variable fonts (Oswald, Bahnschrift); static fonts keep their weight
    except Exception: pass
    return f


def text_layer(txt, size, tracking, weight="Bold", outline=False):
    f = font(size, weight)
    ws = [f.getbbox(c)[2] - f.getbbox(c)[0] if c != " " else size * 0.3 for c in txt]
    tw = int(sum(ws) + tracking * (len(txt) - 1)) + 8
    th = int(size * 1.25)
    im = Image.new("L", (tw, th), 0); d = ImageDraw.Draw(im); x = 4
    for c, w in zip(txt, ws):
        if outline: d.text((x - f.getbbox(c)[0], 0), c, font=f, fill=0, stroke_width=max(2, size // 40), stroke_fill=255)
        else: d.text((x - f.getbbox(c)[0], 0), c, font=f, fill=255)
        x += w + tracking
    return im.crop(im.getbbox())


BIG_SIZE = int(U * 0.30 * min(1.0, 5 / max(5, len(TA["big"]))))      # long words shrink to stay on screen
BIG = text_layer(TA["big"].upper(), BIG_SIZE, int(BIG_SIZE * 0.15))
BIG_O = text_layer(TA["big"].upper(), BIG_SIZE, int(BIG_SIZE * 0.15), outline=True)
SUB = text_layer(TA.get("sub", "").upper() or " ", int(U * 0.055), int(U * 0.028), weight="SemiBold")
TAG = text_layer(TA.get("tag", "") or " ", int(U * 0.06), int(U * 0.01))
ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3


def paste_alpha(canvas, mask, cx, cy, scale=1.0, color=(255, 255, 255), alpha=1.0):
    if scale != 1.0:
        mask = mask.resize((max(1, int(mask.width * scale)), max(1, int(mask.height * scale))), Image.BICUBIC)
    a = mask.point(lambda v: int(v * alpha))
    layer = Image.new("RGBA", mask.size, color + (0,)); layer.putalpha(a)
    canvas.alpha_composite(layer, (int(cx - mask.width / 2), int(cy - mask.height / 2)))


for i in range(N):
    t = i / FPS; b = t / BEAT
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 70)))                       # slight darken behind text
    shake = (np.random.default_rng(int(b)).integers(-6, 7, 2) * U / 1080) if (b % 1) < 0.12 else (0, 0)
    cx, cy = W / 2 + shake[0], H * 0.44 + shake[1]
    # BIG word slam
    k = ease(t / 0.16)
    sc = 1.7 - 0.7 * k
    split = int((1 - k) * U * 0.03 + (U * 0.006 if (b % 1) < 0.1 else 0))
    mask = BIG_O if 6 <= b < 7 else BIG
    if split:
        paste_alpha(im, mask, cx - split, cy, sc, (255, 40, 60), 0.75)
        paste_alpha(im, mask, cx + split, cy, sc, (40, 220, 255), 0.75)
    paste_alpha(im, mask, cx, cy, sc, (255, 255, 255), min(1, t / 0.05))
    # SUB line wipe (beat 2)
    if b >= 2 and TA.get("sub"):
        p = ease((b - 2) * BEAT / 0.14)
        m = SUB.copy(); w = int(m.width * p)
        if w > 0:
            m = m.crop((0, 0, w, m.height)); pad = Image.new("L", SUB.size, 0); pad.paste(m, (0, 0))
            paste_alpha(im, pad, W / 2 + shake[0], H * 0.44 + BIG.height * 0.80 + shake[1])
    # TAG (beat 4)
    if b >= 4 and TA.get("tag"):
        p = (b - 4) * BEAT / 0.18
        sc2 = 1.0 + 0.35 * math.exp(-6 * p) * math.cos(10 * p) if p < 1 else 1.0
        bw, bh = int(TAG.width + U * 0.05), int(TAG.height + U * 0.03)
        box = Image.new("RGBA", (bw, bh), (255, 255, 255, 255))
        yl = Image.new("RGBA", TAG.size, (15, 15, 15, 0)); yl.putalpha(TAG)
        box.alpha_composite(yl, ((bw - TAG.width) // 2, (bh - TAG.height) // 2))
        box = box.resize((max(1, int(bw * sc2)), max(1, int(bh * sc2))), Image.BICUBIC)
        x = int(W / 2 + BIG.width / 2 - box.width + shake[0]); y = int(H * 0.44 - BIG.height * 0.5 - box.height * 1.15 + shake[1])
        im.alpha_composite(box, (x, y))
    # white flash on the drop
    if t < 0.1:
        im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(235 * (1 - t / 0.1)))))
    # glitch out: horizontal slices offset in the last half beat
    if b >= 7.5:
        arr = np.array(im); rng = np.random.default_rng(i)
        for _ in range(9):
            y0 = rng.integers(0, H - 20); hgt = rng.integers(8, int(H * 0.06))
            arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], rng.integers(-int(W * 0.08), int(W * 0.08)), axis=1)
        im = Image.fromarray(arr)
        if b >= 7.85: im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.save(OUT / f"{i:04d}.png", compress_level=1)
print(N, "title frames ->", OUT)

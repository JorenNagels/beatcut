"""Remotion graphics for 14_render: kinetic title, styled captions, end card and lower thirds, rendered as one
transparent track the length of the film (remotion/ "Overlay", ProRes 4444). 14_render lays the matching stretch
of it over every shot it touches while rendering the shots.

event.yaml  style.graphics: python (default: the built-in title/credits/libass captions, no Node needed) | remotion
            style.title_style: slam | minimal | handwritten | glitch | vhs   (all but slam need remotion)
            captions.emoji: true | false | {word: emoji}   (styled captions: an emoji after a matching group)
            style.accent: "#FFE600"   (highlighted caption word, lower-third bar)
Shot options:  lower_third="Vincent" or {"text": "Vincent", "sub": "backwards fall"};  with style.name_cards: true
every shot that has a `name` (face shots) gets one.
The track is cached by its content (render/gfx/overlay_<hash>.mov): it is only re-rendered when a graphic changes."""
import hashlib, json, re, shutil, subprocess
from common import REPO, ROOT, cfg
import subs_lib

REMOTION = REPO / "remotion"
STYLES = ("slam", "minimal", "handwritten", "glitch", "vhs")
EMOJI = {"haha": "😂", "hahaha": "😂", "hihi": "😂", "lol": "😂", "omg": "😱", "god": "😱", "wow": "😮", "nice": "🔥",
         "fire": "🔥", "yes": "🙌", "go": "🚀", "cheers": "🍻", "proost": "🍻", "santé": "🍻", "love": "❤️", "sorry": "😬",
         "nee": "😬", "no": "😬", "help": "🆘", "snow": "❄️", "sneeuw": "❄️", "koud": "🥶", "cold": "🥶", "happy": "🎉",
         "birthday": "🎂", "verjaardag": "🎂", "party": "🎉", "feest": "🎉", "pizza": "🍕", "beer": "🍺", "bier": "🍺"}


def available():
    return bool(shutil.which("node")) and (REMOTION / "node_modules" / "@remotion" / "renderer").exists()


def engine():
    want = cfg("style.graphics", "python")
    style = cfg("style.title_style", "slam")
    if want == "remotion" and not available():
        print("style.graphics is remotion, but Remotion is not installed (python install.py --remotion): using the built-in graphics")
        want = "python"
    if want != "remotion" and style != "slam":
        print(f"title_style {style} needs style.graphics: remotion; using slam")
    return "remotion" if want == "remotion" else "python"


def emoji_for(words):
    on = cfg("captions.emoji", True)
    if on is False: return None
    table = {**EMOJI, **(on if isinstance(on, dict) else {})}
    for w in words:
        e = table.get(re.sub(r"[^\w']", "", w.lower()))
        if e: return e
    return None


def items(E, W, H, FPS):
    """[(first_frame, composition, props)] for this EDL"""
    size = {"width": W, "height": H, "fps": FPS}
    fr = lambda t: round(t * FPS)
    accent = cfg("style.accent", "#FFE600")
    out = []
    ta = E["title_anim"]
    tsegs = [s for s in E["segments"] if s["section"] == "title"]
    if tsegs:
        style = cfg("style.title_style", "slam")
        out.append((fr(tsegs[0]["t0"]), "Title", {**size, "frames": sum(s["frames"] for s in tsegs), "big": ta["big"], "sub": ta["sub"], "tag": ta["tag"],
                                        "bpm": ta["bpm"], "style": style if style in STYLES else "slam"}))
    for s in E["segments"]:
        if s.get("credits"):
            out.append((fr(s["t0"]), "EndCard", {**size, "frames": fr(E["duration"]) - fr(s["t0"]), "title": E["title"],
                                             "lines": E.get("credits", [])}))
        lt = s.get("lower_third") or (s.get("name") if cfg("style.name_cards", False) else None)
        if lt:
            lt = lt if isinstance(lt, dict) else {"text": lt}
            out.append((fr(s["t0"]), "LowerThird", {**size, "frames": min(s["frames"], 3 * FPS), "text": lt["text"],
                                                "sub": lt.get("sub", ""), "accent": accent}))
    if E.get("subtitles") == "styled-captions":
        groups = subs_lib.caption_groups([w for w in subs_lib.timeline_words(E) if w["s"] < E["duration"]])
        for g in groups: g["emoji"] = emoji_for(g["words"])
        fs, bottom = subs_lib.caption_layout(W, H)
        spans = []                                       # stretches of speech, each one overlay
        for g in groups:
            if spans and g["steps"][0]["a"] - spans[-1][-1]["steps"][-1]["b"] < 1.5: spans[-1].append(g)
            else: spans.append([g])
        for sp in spans:
            a = fr(max(0.0, sp[0]["steps"][0]["a"] - 0.1)); b = fr(min(E["duration"], sp[-1]["steps"][-1]["b"] + 0.3))
            out.append((a, "Captions", {**size, "frames": max(1, b - a), "start": a / FPS, "groups": sp,
                                        "highlight": accent, "bottom": bottom, "size": fs}))
    return out


def render(its, font, W, H, FPS, frames):
    """the overlay track for these items (cached); returns its path, or None when there is nothing to draw"""
    if not its: return None
    gfx = ROOT / "render" / "gfx"; pub = gfx / "public"; pub.mkdir(parents=True, exist_ok=True)
    shutil.copy(font, pub / "title.ttf")
    props = {"width": W, "height": H, "fps": FPS, "frames": frames,
             "items": [{"from": f, "composition": c, "props": p} for f, c, p in its]}
    fhash = hashlib.md5((pub / "title.ttf").read_bytes()).hexdigest()
    code = hashlib.md5(b"".join(f.read_bytes() for f in sorted((REMOTION / "src").glob("*.ts*")))).hexdigest()
    key = hashlib.md5(json.dumps([props, fhash, code], sort_keys=True).encode()).hexdigest()[:12]
    out = gfx / f"overlay_{key}.mov"
    if out.exists(): print(f"remotion: {len(its)} graphics (cached)"); return out
    spec = gfx / "jobs.json"
    spec.write_text(json.dumps({"publicDir": str(pub), "concurrency": 6,
                                "jobs": [{"composition": "Overlay", "props": props, "out": str(out)}]}, ensure_ascii=False), encoding="utf-8")
    print(f"remotion: {len(its)} graphics ({', '.join(sorted({c for _, c, _ in its}))}), {frames} frames")
    r = subprocess.run([shutil.which("node"), str(REMOTION / "render.mjs"), str(spec)], cwd=REMOTION)
    if r.returncode: raise RuntimeError("remotion render failed (see above)")
    return out

"""Remotion graphics for 14_render: title, styled captions, end card, lower thirds, text on shots and the film's own
graphics, rendered as one transparent track the length of the film (remotion/ "Overlay", ProRes 4444).
14_render lays the matching stretch of it over every shot it touches while rendering the shots.

event.yaml  style.graphics: auto (default: remotion when installed, else the built-in python graphics) | remotion | python
            style.title_style: slam | minimal | handwritten | glitch | vhs | <a component in the event's graphics/>
            captions.emoji: true | false | {word: emoji}   (styled captions: an emoji after a matching group)
            style.accent: "#FFE600"   (highlighted words, rings, lower-third bar; every graphic gets it)
The film's own graphics: <event>/graphics/*.tsx, React components (`export const Name`) that import helpers from
'beatcut' (remotion/src/lib.ts). One named like a built-in (Title, Captions, EndCard, LowerThird) replaces it. Other
files in graphics/ (images, fonts) are served as static files (staticFile('logo.png')).
Placing graphics (plan.py): shot option gfx={"use": "Pop", "text": "SEND IT", "at": 0.4, "dur": 1.5, ...props} (or a
list; at/dur in seconds from the shot's start, dur default: to the shot's end), or graphic("Pop", t, dur, ...) for
any timeline time. Built-ins to place: Pop (words popping in on the beat), Callout (ring + label), LowerThird.
Every graphic gets width/height/fps/frames, beats/bars (seconds from its first frame) and accent.
Shot options:  lower_third="Vincent" or {"text": "Vincent", "sub": "backwards fall"};  with style.name_cards: true
every shot that has a `name` (face shots) gets one.
The track is cached by its content (render/gfx/overlay_<hash>.mov): it is only re-rendered when a graphic changes."""
import hashlib, json, re, shutil, subprocess
from common import REPO, ROOT, EVENT_DIR, cfg
import subs_lib

REMOTION = REPO / "remotion"
OWN = EVENT_DIR / "graphics"
STYLES = ("slam", "minimal", "handwritten", "glitch", "vhs")
BUILTIN = ("Title", "Captions", "EndCard", "LowerThird", "Pop", "Callout")
EMOJI = {"haha": "😂", "hahaha": "😂", "hihi": "😂", "lol": "😂", "omg": "😱", "god": "😱", "wow": "😮", "nice": "🔥",
         "fire": "🔥", "yes": "🙌", "go": "🚀", "cheers": "🍻", "proost": "🍻", "santé": "🍻", "love": "❤️", "sorry": "😬",
         "nee": "😬", "no": "😬", "help": "🆘", "snow": "❄️", "sneeuw": "❄️", "koud": "🥶", "cold": "🥶", "happy": "🎉",
         "birthday": "🎂", "verjaardag": "🎂", "party": "🎉", "feest": "🎉", "pizza": "🍕", "beer": "🍺", "bier": "🍺"}
CODE = (".tsx", ".ts", ".jsx", ".js")


def available():
    return bool(shutil.which("node")) and (REMOTION / "node_modules" / "@remotion" / "renderer").exists()


def own():
    """the film's own components: {name: file}"""
    out = {}
    for f in sorted(OWN.glob("*")) if OWN.is_dir() else []:
        if f.suffix in CODE:
            for m in re.finditer(r"export\s+(?:const|function)\s+([A-Z]\w*)", f.read_text(encoding="utf-8")): out[m[1]] = f
    return out


def placed(E):
    """graphics the plan put on shots or the timeline: [(t0, dur, spec)]"""
    out = [(g["t"], g["dur"], g) for g in E.get("graphics", [])]
    for s in E["segments"]:
        gs = s.get("gfx") or []
        for g in [gs] if isinstance(gs, dict) else gs:
            at = g.get("at", 0.0)
            out.append((s["t0"] + at, g.get("dur", s["frames"] / E["fps"] - at), g))
    return out


def engine(E):
    """remotion | python. Stops (instead of quietly drawing something else) when the event asks for graphics only
    Remotion can draw and it is missing."""
    want = cfg("style.graphics", "auto")
    style = cfg("style.title_style", "slam")
    needs = [why for why, on in [(f"title_style {style}", style != "slam"), (f"the event's graphics/ folder", bool(own())),
                                 ("graphics placed in the plan (gfx= / graphic())", bool(placed(E)))] if on]
    if want == "python":
        if needs: raise SystemExit(f"style.graphics is python, but the event uses {', '.join(needs)}: set style.graphics: remotion")
        return "python"
    if available(): return "remotion"
    if want == "remotion" or needs:
        raise SystemExit(f"Remotion is needed ({', '.join(needs) or 'style.graphics: remotion'}) but not installed: "
                         "run `python install.py --remotion` (needs Node.js 18+), or set style.graphics: python")
    print("graphics: built-in (python). Install Remotion (python install.py --remotion) for title styles, text on shots "
          "and the film's own graphics.")
    return "python"


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
    fr = lambda t: round(t * FPS)
    accent = cfg("style.accent", "#FFE600")
    names = set(BUILTIN) | set(own())

    def music(f, n):                                 # beat / bar times around this graphic, seconds from its first frame
        t0 = f / FPS
        return {k: [round(b - t0, 3) for b in E.get(k, []) if t0 - 2 <= b <= t0 + n / FPS + 1] for k in ("beats", "bars")}

    def add(f, comp, n, props):
        if comp not in names:
            raise SystemExit(f"no graphic called {comp}: built-ins {', '.join(BUILTIN)}; own ({OWN}): {', '.join(sorted(own())) or 'none'}")
        out.append((f, comp, {"width": W, "height": H, "fps": FPS, "frames": max(1, n), "accent": accent, **music(f, n), **props}))

    out = []
    ta = E["title_anim"]
    tsegs = [s for s in E["segments"] if s["section"] == "title"]
    if tsegs:
        style = cfg("style.title_style", "slam")
        add(fr(tsegs[0]["t0"]), style if style in own() else "Title", sum(s["frames"] for s in tsegs),
            {"big": ta["big"], "sub": ta["sub"], "tag": ta["tag"], "bpm": ta["bpm"], "style": style if style in STYLES else "slam"})
    for s in E["segments"]:
        if s.get("credits"):
            add(fr(s["t0"]), "EndCard", fr(E["duration"]) - fr(s["t0"]), {"title": E["title"], "lines": E.get("credits", [])})
        lt = s.get("lower_third") or (s.get("name") if cfg("style.name_cards", False) else None)
        if lt:
            lt = lt if isinstance(lt, dict) else {"text": lt}
            add(fr(s["t0"]), "LowerThird", min(s["frames"], 3 * FPS), {"text": lt["text"], "sub": lt.get("sub", "")})
    for t, dur, g in placed(E):
        add(fr(t), g["use"], fr(t + dur) - fr(t), {k: v for k, v in g.items() if k not in ("use", "at", "dur", "t")})
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
            add(a, "Captions", b - a, {"start": a / FPS, "groups": sp, "highlight": accent, "bottom": bottom, "size": fs})
    return out


def _prepare(font):
    """public folder (font + the film's assets), the generated list of the film's components, and a hash of all code"""
    gfx = ROOT / "render" / "gfx"; pub = gfx / "public"; pub.mkdir(parents=True, exist_ok=True)
    shutil.copy(font, pub / "title.ttf")
    files = sorted(OWN.glob("*")) if OWN.is_dir() else []
    for f in files:
        if f.is_file() and f.suffix not in CODE: shutil.copy(f, pub / f.name)
    entry = None
    if own():
        mods = sorted(set(own().values()))
        entry = gfx / "event_graphics.ts"
        entry.write_text("// generated by graphics_lib.py: the event's own graphics\n"
                         + "".join(f"import * as m{i} from '{f.as_posix()}';\n" for i, f in enumerate(mods))
                         + "const pick = (m: Record<string, any>) => Object.fromEntries(Object.entries(m).filter(([k, v]) => /^[A-Z]/.test(k) && typeof v === 'function'));\n"
                         + f"export const EVENT = {{{', '.join(f'...pick(m{i})' for i in range(len(mods)))}}};\n", encoding="utf-8")
    code = hashlib.md5()
    for f in sorted((REMOTION / "src").glob("*.ts*")) + [REMOTION / "webpack.mjs", pub / "title.ttf"] + [f for f in files if f.is_file()]:
        code.update(f.read_bytes())
    return gfx, pub, entry, code.hexdigest()


def _run(gfx, pub, entry, jobs):
    spec = gfx / "jobs.json"
    spec.write_text(json.dumps({"publicDir": str(pub), "concurrency": 6, "eventEntry": str(entry) if entry else None, "jobs": jobs},
                               ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([shutil.which("node"), str(REMOTION / "render.mjs"), str(spec)], cwd=REMOTION)
    if r.returncode: raise RuntimeError("remotion render failed (see above)")


def render(its, font, W, H, FPS, frames):
    """the overlay track for these items (cached); returns its path, or None when there is nothing to draw"""
    if not its: return None
    gfx, pub, entry, code = _prepare(font)
    props = {"width": W, "height": H, "fps": FPS, "frames": frames,
             "items": [{"from": f, "composition": c, "props": p} for f, c, p in its]}
    key = hashlib.md5(json.dumps([props, code], sort_keys=True).encode()).hexdigest()[:12]
    out = gfx / f"overlay_{key}.mov"
    if out.exists(): print(f"remotion: {len(its)} graphics (cached)"); return out
    print(f"remotion: {len(its)} graphics ({', '.join(sorted({c for _, c, _ in its}))}), {frames} frames")
    _run(gfx, pub, entry, [{"composition": "Overlay", "props": props, "out": str(out)}])
    return out


def stills(its, font, W, H, FPS, frames, at, out_dir):
    """transparent PNGs of the graphics at these timeline frames: out_dir/<frame>.png"""
    gfx, pub, entry, _ = _prepare(font)
    props = {"width": W, "height": H, "fps": FPS, "frames": frames,
             "items": [{"from": f, "composition": c, "props": p} for f, c, p in its]}
    _run(gfx, pub, entry, [{"composition": "Overlay", "props": props, "stills": sorted(set(at)), "out": str(out_dir)}])

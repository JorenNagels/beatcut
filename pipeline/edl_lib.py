"""Toolkit for an event's plan.py: build the edit decision list (edl.json) on the music grid.

A plan does  `from edl_lib import *`, sets the event-specific lists on S (Settings), reserves its pinned shots with
pin()/pin_best(), lays the timeline out with place()/chapter()/pick(), and ends with finish(...).
Rules enforced here: a moment (file + seconds) is never used twice; pinned shots are reserved before fillers;
fillers come from tags.json ranked by tag rating + signal quality (+ bonus for the reviewed candidates);
slow motion only from >= 50 fps sources; camera sound only where the voice detector hears people.
Optional inputs when they exist: tags_auto.json (20_clip --autotag) when there is no hand-made tags.json,
sounds.json (19b_sounds: laughter/cheering count as voices), scenes.json (21_scenes: windows never cross a cut).
See examples/ski-trip-plan.py for a complete film, templates/plan_short.py for a 9:16 short."""
import glob, importlib, math
from collections import Counter, defaultdict
import numpy as np
import common
from common import ROOT, CACHE, load_json, save_json, cfg, base

cand_mod = importlib.import_module("06_candidates")

FPS = 30
inv = {r["file"]: r for r in load_json("inventory.json")}
tags = load_json("tags.json") or load_json("tags_auto.json")
if tags is None: raise SystemExit("no tags.json (visual pass) or tags_auto.json (20_clip --autotag) yet")
idx = load_json("signals_index.json")
M = load_json("music.json")
CANDS = load_json("candidates.json", [])
PEOPLE = load_json("people.json", [])
NAMES = {k: v["face_ids"] for k, v in (load_json("people_names.json") or {"people": {}})["people"].items()}
EVENTS = load_json("events.json", [])
HINTS = (load_json("dedup.json") or {}).get("hints", {})
SOUNDS = load_json("sounds.json", [])               # 19b_sounds: laughter, cheering, singing, shouting
SCENES = load_json("scenes.json", {})               # 21_scenes: shot changes inside a file (seconds)
feats = {}


class Settings:
    """event-specific lists the plan fills in"""
    evening = set()            # indoor/evening clips: kept for the outro, never used as fillers; voices always on
    ending = staticmethod(lambda f, a: False)   # (file, second) -> True if saved for the ending
    force_vertical = set()     # files to treat as vertical although the metadata says landscape
    outdoor_photos = set()     # for best_face(): photos taken outdoors
    indoor_videos = set()      # for best_face(): landscape videos filmed indoors
    requested_sound = set()    # files the user wants to hear (camera sound kept even without detected voices)
    cam_override = []          # (file, in_from, in_to, level): manual sound choices from review
    allow_vertical = False     # shorts (9:16): vertical phone clips may be fillers too


S = Settings()


def F(f):
    if f not in feats: feats[f] = load_json(f"features/{idx[f]}.json")
    return feats[f]


def day(f):
    return cand_mod.day_of(inv[f], tags["day_estimates"])[0]


# ---------------- moment bookkeeping ----------------
used = defaultdict(list)                           # file -> [(a, b)]


def free(f, a, b, margin=0.5):
    return all(b + margin <= x or a - margin >= y for x, y in used[f])


def take(f, a, b):
    """reserve a source range (also to keep a moment for later, or to block a boring part)"""
    used[f].append((a, b))


# ---------------- shots ----------------
def shot(kind, src, a=None, dur=None, **kw):
    return {"type": kind, "src": src, "in": a, **kw}


def pin(f, a, L, **kw):
    """a fixed shot: file f from second a, L seconds long"""
    take(f, a, a + L)
    return shot("video", f, float(a), **kw)


def face_records():
    recs = []
    for p in glob.glob(str(CACHE / "faces" / "*.npz")):
        recs += list(np.load(p, allow_pickle=True)["recs"])
    return recs


FACES = None
USED_PHOTOS = set()


def best_face(name, avoid_srcs, prefer_outdoor):
    """Best smiling close-up of a person: big, frontal, sharp face; photos allowed."""
    global FACES
    if FACES is None: FACES = face_records()
    pids = NAMES[name]
    cents = [np.array(p["centroid"]) / np.linalg.norm(p["centroid"]) for p in PEOPLE if p["id"] in pids]
    best, bq = None, -1
    for r in FACES:
        sim = max(float(r["emb"] @ c) for c in cents)
        if sim < 0.42 or r["src"] in avoid_srcs: continue
        if r["t"] >= 0 and not free(r["src"], r["t"] - 2, r["t"] + 3): continue
        w = r["box"][2] / r["scale"]
        outdoor = base(r["src"]).startswith("GX") or r["src"] in S.outdoor_photos or \
            (r["t"] >= 0 and inv[r["src"]]["width"] > inv[r["src"]]["height"] and r["src"] not in S.indoor_videos)
        q = sim * r["score"] * (0.3 + r["frontal"]) * min(1, r["sharp"] / 150) * min(1, w / 160)
        if prefer_outdoor is not None and outdoor != prefer_outdoor: q *= 0.4
        if q > bq: best, bq = r, q
    return best


def face_shot(name, dur, prefer_outdoor):
    """name-card shot: the person's best close-up (video, or a photo)"""
    r = best_face(name, USED_PHOTOS, prefer_outdoor)
    if r is None: return None
    box = [v / r["scale"] for v in r["box"]]
    if r["t"] < 0:
        USED_PHOTOS.add(r["src"])
        return shot("photo", r["src"], focus=box, name=name)
    a = max(0.0, r["t"] - dur * 0.45); b = a + dur
    take(r["src"], a, b)
    return shot("video", r["src"], a, focus=box, name=name, cat="faces", why=f"{name}: best close-up")


# ---------------- filler pool ----------------
def window_for(t, L, s_fn_cat):
    """best free window of length L (s) inside tag t; returns (start, quality)."""
    f = t["file"]; Fe = F(f)
    s = cand_mod.window_scores(Fe, s_fn_cat)
    n = len(s); Li = max(1, math.ceil(L))
    best = None
    for a in range(int(t["start"]), int(min(t["end"], n)) - Li + 1):
        if not free(f, a, a + L) or crosses_cut(f, a, a + L): continue
        q = float(np.mean(s[a:a + Li]))
        if best is None or q > best[1]: best = (a, q)
    return best


def crosses_cut(f, a, b):
    """a shot change (scenes.json) inside [a, b] (0.3 s slack at the edges)"""
    return any(a + 0.3 < c < b - 0.3 for c in SCENES.get(f, ()))


CAND_WIN = defaultdict(list)
for c in CANDS: CAND_WIN[c["file"]].append((c["start"], c["end"]))

VOICE = defaultdict(list)
for e in EVENTS:
    if e["kind"] == "voice": VOICE[e["file"]].append(e)
for e in SOUNDS:                                   # model-detected laughter etc. weigh like strong voice peaks
    if e["kind"] in ("laugh", "cheer", "sing", "shout"): VOICE[e["file"]].append(e)


def voice_in(f, a, b):
    """voice/laughter evidence inside [a,b]: sum of event scores weighted by overlap"""
    return sum(e["score"] * max(0, min(b, e["end"]) - max(a, e["start"])) / max(0.1, e["end"] - e["start"]) for e in VOICE[f])


def vertical(f):
    return (inv[f]["height"] > inv[f]["width"] or f in S.force_vertical) and not S.allow_vertical


def pick(L, cats, days=None, prev=(), exclude_files=()):
    """best free filler of length L from the tagged categories (optionally limited to some days)"""
    best = None
    for t in tags["tags"]:
        f = t["file"]
        if f not in idx or t["cat"] not in cats or f in exclude_files: continue
        if f in S.evening or vertical(f) or S.ending(f, t["end"] - 1): continue
        if days and day(f) not in days: continue
        if f in prev: continue
        if t["end"] - t["start"] < min(L, 2): continue
        w = window_for(t, L, t["cat"])
        if not w: continue
        a, q = w
        in_cand = any(a < y and a + L > x for x, y in CAND_WIN[f])
        n_used = len(used[f])
        v = voice_in(f, a, a + L) if t["cat"] in ("faces", "lifestyle", "crash") else 0
        score = 0.6 * t["rating"] / 5 + 0.3 * max(0, q + 0.3) + (0.15 if in_cand else 0) - 0.12 * n_used + min(0.15, v)
        if best is None or score > best[0]:
            best = (score, f, a, t, v)
    if not best: return None
    _, f, a, t, v = best
    take(f, a, a + L)
    return shot("video", f, float(a), cat=t["cat"], why=t["note"] + ("; people talking/laughing" if v else ""),
                letterbox=t["cat"] == "scenic", cam_audio=1.0 if t["cat"] == "crash" else 0.85 if v else 0)


def pin_best(f, a0, a1, L, cat, **kw):
    """best free window of length L inside [a0,a1] for a category (e.g. crash: chaos + laughter after)"""
    w = window_for({"file": f, "start": a0, "end": a1}, L, cat)
    if not w: raise RuntimeError(f"no free window in {f} {a0}-{a1}")
    a = float(w[0])
    if cat == "crash":                     # make sure the reaction (laughter) is inside: shift towards voices
        vs = [e for e in VOICE[f] if a0 <= e["start"] <= a1 + 4]
        if vs and not voice_in(f, a, a + L):
            a = min(max(a0, vs[0]["end"] - L + 0.5), a1 - L) if a1 - L > a0 else a0
    take(f, a, a + L)
    return shot("video", f, a, cat=cat, **kw)


def best_talk(L, exclude=()):
    """window with the most talking/laughing (daytime, landscape): bridges a song change"""
    best = None
    for t in tags["tags"]:
        f = t["file"]
        if t["cat"] not in ("faces", "lifestyle") or f in S.evening or vertical(f) or f in exclude or f not in idx: continue
        for a in np.arange(t["start"], max(t["start"], t["end"] - L) + 0.01, 0.5):
            if not free(f, a, a + L): continue
            v = voice_in(f, a, a + L) + 0.02 * t["rating"]
            if best is None or v > best[0]: best = (v, f, float(a), t)
    v, f, a, t = best
    take(f, a, a + L)
    return shot("video", f, a, cat="talk", cam_audio=1.0, why=f"talk transition: {t['note']}")


# ---------------- timeline ----------------
segs = []
graphics = []                                      # graphic(): graphics placed on the timeline


def graphic(use, t, dur, **props):
    """a graphic (graphics_lib: built-in Pop / Callout / LowerThird or one in the event's graphics/) from timeline
    second t for dur seconds; props go to the component. On a single shot use the shot option gfx= instead."""
    graphics.append({"use": use, "t": round(t, 3), "dur": round(dur, 3), **props})


def place(t0, t1, s, section):
    """put shot s on the timeline from t0 to t1 (seconds, snapped to frames)"""
    if s is None:
        raise RuntimeError(f"no shot for {section} at {t0:.1f}")
    f0, f1 = round(t0 * FPS), round(t1 * FPS)
    s.update({"t0": f0 / FPS, "frames": f1 - f0, "section": section})
    s["dur"] = s["frames"] / FPS
    segs.append(s)


def prev_files(k=2):
    return tuple(s["src"] for s in segs[-k:])


def chapter(bars, to_t, b0, b1, days, special, label):
    """1-bar cuts from bar b0 to b1 of a song; special = {bar_index: (shot, n_bars)} for pinned shots.
    bars: the song's bar times; to_t: song time -> timeline time. Every 4th bar may be faces/lifestyle."""
    i = b0
    while i < b1:
        if i in special:
            s, nb = special[i]
            place(to_t(bars[i]), to_t(bars[min(i + nb, b1)]), s, label); i += nb; continue
        L = bars[i + 1] - bars[i]
        cats = {"action"} if (i - b0) % 4 != 3 else {"action", "faces", "lifestyle"}
        s = pick(L, cats, days=days, prev=prev_files()) or pick(L, cats | {"scenic"}, days=days, prev=prev_files()) \
            or pick(L, cats, prev=prev_files())
        place(to_t(bars[i]), to_t(bars[i + 1]), s, label); i += 1


def nearest_beat(beats, t):
    return beats.index(min(beats, key=lambda b: abs(b - t)))


# ---------------- finishing passes ----------------
def ramp(s, slow_tl=2.4):
    """speed ramp on a crash: normal speed into the fall, the impact in real slow motion from a >= 50 fps copy
    (dedup hints: alt_t = main_t + alt_offset), then the reaction at normal speed again"""
    alt = next((h for h in HINTS.get(s["src"], []) if h.get("alt_fps", 30) >= 50
                and h["start"] <= s["in"] and s["in"] + s["dur"] - 1.2 <= h["end"]), None)
    if not alt: return
    Fe = F(s["src"]); a, b = int(s["in"] + 1), int(s["in"] + s["dur"] - 2.5)
    chaos = np.abs(np.array(Fe["rot"][a:b + 1])) * 10 + np.array(Fe["shake"][a:b + 1])
    imp = a + float(np.argmax(chaos)) + 0.3                      # main-file time of the impact
    pre = max(0.6, imp - 0.6 - s["in"])                          # timeline seconds before the slow part
    post = s["dur"] - pre - slow_tl
    s["parts"] = [{"src": s["src"], "in": s["in"], "dur": pre, "slowmo": 1.0},
                  {"src": alt["alt"], "in": round(s["in"] + pre + alt["alt_offset"], 3), "dur": slow_tl, "slowmo": 0.5, "alt_of": s["src"]},
                  {"src": s["src"], "in": s["in"] + pre + slow_tl * 0.5, "dur": post, "slowmo": 1.0}]
    s["why"] += f"; slow motion on the impact (60 fps source {alt['alt'][:28]})"


def legs_ramp(s, p1=1.9, p2=2.8):
    """fixed speed ramp (p1 s normal, p2 s at 50 % from the >= 50 fps copy, rest normal) for shots flagged legs_ramp"""
    alt = next(h for h in HINTS.get(s["src"], []) if h.get("alt_fps", 30) >= 50)
    a = s["in"]
    s["parts"] = [{"src": s["src"], "in": a, "dur": p1, "slowmo": 1.0},
                  {"src": alt["alt"], "in": round(a + p1 + alt["alt_offset"], 3), "dur": p2, "slowmo": 0.5},
                  {"src": s["src"], "in": a + p1 + p2 * 0.5, "dur": s["dur"] - p1 - p2, "slowmo": 1.0}]


def finish(duration, music_cues, title_t0, title_t1, title_bpm, fmt=None, subtitles=None, fades=(1.0, 3.0)):
    """slow-motion ramps, sound decisions, checks; writes edl.json (edl_<name>.json for plan_<name>.py).
    music_cues: [{"track": role, "from": song_s, "to": song_s, "at": timeline_s, "fade_in", "fade_out", "fade_curve"}]
    title_t0 == title_t1: no kinetic title. fmt: "16:9" | "9:16" | "1:1" | "4:5" (default film.format);
    subtitles: "none" | "speech" | "styled-captions" (default event.yaml subtitles); fades: picture fade in/out (s)"""
    for s in segs:
        if s.get("cat") == "crash" and s["type"] == "video" and s["dur"] >= 4.5 and not s.get("parts"): ramp(s)
        if s.get("legs_ramp"): legs_ramp(s)

    # camera sound only where people actually talk / laugh / react (voice detector), never plain ski/wind noise
    for s in segs:
        if s["type"] != "video" or not s.get("cam_audio"): continue
        v = voice_in(s["src"], s["in"], s["in"] + s["dur"])
        if s["src"] in S.evening: s["cam_note"] = "evening/indoor: always talking"; continue   # detector misses talk in noisy rooms
        if s.get("bite") or s["src"] in S.requested_sound: s["cam_note"] = "requested / sound bite"; continue
        if v < 0.05: s["cam_audio"] = 0; s["cam_note"] = "no voices -> muted"
        else: s["cam_note"] = f"voices {v:.2f}"
    for s in segs:
        for f, a, b, lvl in S.cam_override:
            if s["type"] == "video" and s["src"] == f and a <= s["in"] <= b:
                s["cam_audio"] = lvl; s["cam_note"] = "manual"

    beats, bars = set(), set()                   # the music's beats and bars on the timeline (graphics animate on them)
    cues = sorted(music_cues, key=lambda c: c["at"])      # where songs overlap, the newer one counts
    for c, end in zip(cues, [c["at"] for c in cues[1:]] + [duration]):
        for key, out in (("beats", beats), ("bars", bars)):
            out.update(round(c["at"] + b - c["from"], 3) for b in M[c["track"]][key]
                       if c["from"] <= b < c["to"] and 0 <= c["at"] + b - c["from"] < end)
    title = cfg("title", {}) or {}
    edl = {"fps": FPS, "duration": round(duration, 3),
           "format": fmt or cfg("film.format", "16:9"), "subtitles": subtitles or cfg("subtitles", "none") or "none", "fades": list(fades),
           "title_anim": {"t0": title_t0, "t1": title_t1, "bpm": title_bpm,
                          "big": title.get("big", ""), "sub": title.get("sub", ""), "tag": str(title.get("tag", ""))},
           "music": {"tracks": {k: M[k]["file"] for k in M}, "cues": music_cues},
           "title": title.get("full", ""), "credits": cfg("credits", []) or [],
           "names": sorted(NAMES), "beats": sorted(beats), "bars": sorted(bars), "graphics": graphics, "segments": segs}
    save_json(common.edl_file(), edl)

    print(f"duration {duration:.1f}s ({int(duration // 60)}:{duration % 60:04.1f}), {len(segs)} shots")
    print("by section", dict(Counter(s["section"] for s in segs)))
    seen = defaultdict(list)
    for s in segs:
        if s["type"] == "video":
            L = s["dur"] * s.get("slowmo", 1)
            for a, b in seen[s["src"]]:
                assert s["in"] + L <= a or s["in"] >= b, f"overlap {s['src']} {s['in']}"
            seen[s["src"]].append((s["in"], s["in"] + L))
    ph = [s["src"] for s in segs if s["type"] == "photo"]
    assert len(ph) == len(set(ph)), "photo used twice"
    print("no moment used twice: OK")
    return edl

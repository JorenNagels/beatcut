"""Starter film plan: one song, driven by event.yaml. Copy to the event folder as plan.py, run step 13_edl,
then reshape it by hand (examples/ski-trip-plan.py is a complete two-song film with talk transitions and sound bites).

  intro    scenic/lifestyle, 2-bar cuts          music.tracks.main  (bars 0 .. INTRO)
  title    kinetic title over 4 shots, 2 bars
  chapters one per day, 1-bar cuts, must-haves placed evenly inside their day
  outro    lifestyle/faces, 2-bar cuts, then credits; the song fades out at the target length

event.yaml used here: music.tracks.main, film.length_s (target seconds), must_have (list), title.*, credits.
  must_have: [{file: GX014904.mp4, at: 14.0, bars: 3, why: "one-leg skiing", sound: true}, ...]
"""
from edl_lib import *

TRACK = "main" if "main" in M else next(iter(M))
SONG = M[TRACK]
BARS, BEATS = SONG["bars"], SONG["beats"]
BAR = BARS[1] - BARS[0]
TARGET = float(cfg("film.length_s", 180))

# the film ends on a bar line near the target length (or where the song ends)
LAST = min(len(BARS) - 1, max(16, round(TARGET / BAR)))
END = BARS[LAST] - BARS[0] + 4.0                     # + 4 s of credits while the music fades
t = lambda s: s - BARS[0]                            # song time -> timeline (bar 0 = 0 s)

INTRO, TITLE = 8, 2                                  # bars
OUTRO = 8
CH0, CH1 = INTRO + TITLE, LAST - OUTRO

# must-haves from event.yaml, reserved first so fillers can't take them
musts = []
for m in cfg("must_have", []) or []:
    s = pin(m["file"], float(m["at"]), m.get("bars", 2) * BAR, cat=m.get("cat", "action"),
            cam_audio=1.0 if m.get("sound") else 0, why=m.get("why", "must-have"))
    if m.get("sound"): S.requested_sound.add(m["file"])
    musts.append((day(m["file"]), m.get("bars", 2), s))

# 1) intro: 2-bar cuts, scenery first (set S.evening for indoor/evening clips so they stay out of the fillers)
for b in range(0, INTRO, 2):
    s = pick(BARS[b + 2] - BARS[b], {"scenic"}, prev=prev_files()) or \
        pick(BARS[b + 2] - BARS[b], {"scenic", "lifestyle", "faces", "action"}, prev=prev_files())
    place(t(BARS[b]), t(BARS[b + 2]), s, "intro")

# 2) kinetic title: 4 background shots of 2 beats each
b0 = nearest_beat(BEATS, BARS[INTRO])
tc = [BARS[INTRO]] + [BEATS[b0 + 2 * k] for k in (1, 2, 3)] + [BARS[INTRO + TITLE]]
for k in range(4):
    s = pick(tc[k + 1] - tc[k], {"scenic", "action"}, prev=prev_files())
    place(t(tc[k]), t(tc[k + 1]), s, "title")

# 3) one chapter per day, bars shared by footage amount; must-haves spread evenly inside their day
# (only days with some action: travel/arrival days without action footage get no chapter of their own)
ACT = [x for x in tags["tags"] if x["file"] in idx and x["cat"] in ("action", "crash")]
cnt = Counter(day(x["file"]) for x in ACT)
days = sorted(d for d, n in cnt.items() if n >= 3 and d != "unknown") or [None]
weight = {d: sum(1 for x in ACT if d is None or day(x["file"]) == d) for d in days}
total, b = sum(weight.values()), CH0
for i, d in enumerate(days):
    nb = CH1 - b if i == len(days) - 1 else max(4, round((CH1 - CH0) * weight[d] / total))
    e = min(CH1, b + nb)
    mine = [(n, s) for dd, n, s in musts if dd == d or d is None]
    special, step = {}, max(1, (e - b) // (len(mine) + 1))
    for k, (n, s) in enumerate(mine):
        at = b + step * (k + 1) - 1
        while any(at <= x < at + n or x <= at < x + special[x][1] for x in special): at += 1
        if at + n <= e: special[at] = (s, n)
    chapter(BARS, t, b, e, {d} if d else None, special, f"day {i + 1}")
    b = e

# 4) outro: 2-bar lifestyle/faces cuts, then credits
for b in range(CH1, LAST, 2):
    e = min(LAST, b + 2)
    s = pick(BARS[e] - BARS[b], {"lifestyle", "faces"}, prev=prev_files()) or \
        pick(BARS[e] - BARS[b], {"scenic", "lifestyle", "faces"}, prev=prev_files())
    place(t(BARS[b]), t(BARS[e]), s, "outro")
s = pick(END - t(BARS[LAST]), {"scenic"}, prev=prev_files()) or pick(END - t(BARS[LAST]), {"scenic", "lifestyle"})
s.update(dim=0.5, credits=True, letterbox=False)
place(t(BARS[LAST]), END, s, "credits")

cues = [{"track": TRACK, "from": BARS[0], "to": min(SONG["audio_end"], BARS[LAST] + 4.0), "at": 0.0,
         "fade_in": 0.5, "fade_out": 4.0}]
finish(END, cues, t(BARS[INTRO]), t(BARS[INTRO + TITLE]), SONG["bpm"])

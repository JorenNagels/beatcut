"""Starter plan for a 9:16 short (TikTok / Reels / YouTube Shorts). Copy it to the event folder as
plan_<name>.py (plan_short1.py, plan_falls.py ...; several shorts per event are fine), then:
    13_edl plan_short1.py          -> edl_short1.json
    14_render preview --edl short1 -> render/short1_preview.mp4  (540x960; final: 1080x1920)

  hook  bars 0-2   the best fall or jump WITH its sound: a must_have with `hook: true`, else the top crash/action tag
  body             1-bar cuts, every 4th bar two 2-beat cuts; one sound bite (punch-in, music ducked) in the middle
  end   2 bars     the most laughing/talking window, then a quick fade
The song starts at its first high-energy section, so the hook lands on the drop. Vertical phone clips are allowed
as fillers (they fill the frame); landscape shots get a crop that follows faces and motion (shot option
reframe="fit" shows the whole frame on a blurred fill instead). Styled word-by-word captions need 19_transcribe."""
from edl_lib import *

LENGTH = 30                                   # seconds: 15 / 30 / 60
TRACK = next((r for r in ("short", "main", "upbeat") if r in M), next(iter(M)))
REUSE = False                                 # False: skip moments already used in the film and the other shorts
SUBS = "styled-captions"                      # styled-captions | speech | none
S.allow_vertical = True

SONG = M[TRACK]
BARS, BEATS = SONG["bars"], SONG["beats"]
hi = [s for s in SONG["sections"] if s["level"] == "high"]
BAR = BARS[1] - BARS[0]
NB = max(6, round(LENGTH / BAR))              # length in bars
B0 = min(hi[0]["bar_start"] if hi else 0, len(BARS) - NB - 1)
t = lambda s: s - BARS[B0]                    # song time -> timeline

if not REUSE:                                 # block everything the film and other shorts already show
    for p in sorted(ROOT.glob("edl*.json")):
        if p.name == common.edl_file(): continue
        for s in load_json(p.name)["segments"]:
            if s["type"] != "video": continue
            for q in s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": s.get("slowmo", 1.0)}]:
                take(q["src"], q["in"], q["in"] + q["dur"] * q.get("slowmo", 1.0))

# 1) hook: a must_have marked hook, else the best crash/action with people reacting
m = next((m for m in cfg("must_have", []) or [] if m.get("hook")), None)
if m:
    hook = pin(m["file"], float(m["at"]), 2 * BAR, cat=m.get("cat", "crash"), cam_audio=1.0, why="hook: " + m.get("why", ""))
else:
    hook = None
    ranked = sorted((x for x in tags["tags"] if x["cat"] in ("crash", "action") and x["file"] in idx
                     and x["end"] - x["start"] >= 2 * BAR),
                    key=lambda x: -(x["rating"] + (1 if x["cat"] == "crash" else 0) + min(1, voice_in(x["file"], x["start"], x["end"]))))
    for x in ranked:
        try: hook = pin_best(x["file"], x["start"], x["end"], 2 * BAR, x["cat"], cam_audio=1.0, why="hook: " + x["note"]); break
        except RuntimeError: continue
S.requested_sound.add(hook["src"])
place(0, t(BARS[B0 + 2]), hook, "hook")

# 2) body: 1-bar cuts, 2-beat cuts every 4th bar, a sound bite in the middle
END_B = B0 + NB - 2
MID = B0 + NB // 2 - 1
b = B0 + 2
while b < END_B:
    if b == MID and b + 2 <= END_B:
        s = best_talk(2 * BAR, exclude=prev_files())
        s.update(bite=True, why="sound bite: " + s["why"])
        place(t(BARS[b]), t(BARS[b + 2]), s, "bite"); b += 2; continue
    if (b - B0) % 4 == 3:
        k = nearest_beat(BEATS, BARS[b])
        for c0, c1 in ((BARS[b], BEATS[k + 2]), (BEATS[k + 2], BARS[b + 1])):
            s = pick(c1 - c0, {"action", "crash"}, prev=prev_files()) or pick(c1 - c0, {"action", "scenic", "lifestyle"}, prev=prev_files())
            s["cam_audio"] = 0; place(t(c0), t(c1), s, "body")
    else:
        L = BARS[b + 1] - BARS[b]
        s = pick(L, {"action", "crash"}, prev=prev_files()) or pick(L, {"action", "scenic", "lifestyle", "faces"}, prev=prev_files())
        s["cam_audio"] = 0; place(t(BARS[b]), t(BARS[b + 1]), s, "body")   # body = music only (short cuts)
    b += 1

# 3) end on a laugh
s = best_talk(BARS[B0 + NB] - BARS[END_B], exclude=prev_files())
place(t(BARS[END_B]), t(BARS[B0 + NB]), s, "end")

END = t(BARS[B0 + NB])
cues = [{"track": TRACK, "from": BARS[B0], "to": min(SONG["audio_end"], BARS[B0 + NB] + 0.5), "at": 0.0, "fade_out": 0.8}]
finish(END, cues, 0.0, 0.0, SONG["bpm"], fmt="9:16", subtitles=SUBS, fades=(0.0, 0.4))

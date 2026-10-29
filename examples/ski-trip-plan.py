"""Example: the complete plan of a 4:50 ski-trip film (two songs). Copy pieces into your own plan.py.

Structure (LATTJO-style, cinematic + funny):
  calm (Tycho - Awake)      bars 0-10    cold open: travel, arrival, first views (cut every 2 bars)
  talk A                                 voices bridge the song change; 1901 creeps in under it
  upbeat (Phoenix - 1901)   bars 0-32    fast montage intro (2-bar, then 1-bar, then 2-beat cuts)
                            bars 32-34   kinetic title over 4 background shots
                            bars 34-55   action chapter 1 (13-14 Mar)
                            bars 55-72   breakdown: the funny bit (sound bites, falls + laughter), music low
                            bars 72-108  action chapter 2 (15-16 Mar)
                            bars 108-113 last runs back to the village
  talk B                                 voices; Awake returns
  calm (Tycho - Awake)      bars 78-96+  outro: cheers, dinner, charades, presents, birthday, shadows, credits
"""
from edl_lib import *

S.evening = {"IMG_5532.mp4", "IMG_6810.mp4", "IMG_6812.mp4", "IMG_6813.mp4", "IMG_8133.mp4", "IMG_5798.mp4",
             "IMG_3768.mp4", "7D5FD233-FAF9-4799-9639-73C46AB2C096 Copy.mp4"}
S.ending = lambda f, a: f == "GX024910.mp4" or (f == "GX014910.mp4" and a >= 450)   # last-day village shots
S.force_vertical = {"IMG_6770.MOV"}
S.outdoor_photos = {"IMG_4029.jpg", "IMG_6800.jpg", "IMG_6886.jpg", "IMG_6883.jpg", "IMG_5552.jpg", "IMG_5627.jpg",
                    "IMG_8152.jpg", "IMG_8131.jpg", "IMG_5489.jpg", "IMG_5508.jpg", "IMG_8141.jpg"}
S.indoor_videos = {"IMG_5532.mp4"}
# clips the user asked for because of their sound (laughing, posing, funny noises)
S.requested_sound = {"VIDEO-2026-03-13-19-21-45.mp4", "VIDEO-2026-03-14-16-48-22.mp4", "VIDEO-2026-03-14-16-55-04.mp4",
                     "GX014900.mp4", "GX014880.mp4", "GX014904.mp4"}
S.cam_override = [("FA3DCEC9-3E36-46B1-A679-B4C31999DFD9.mp4", 125, 131, 0.0),   # 2:09 fall: music instead
                  ("GX024903.mp4", 290, 300, 1.0)]                               # guy talking to camera: hear him

# ---------------- timeline grid ----------------
TB, PB = M["calm"]["bars"], M["upbeat"]["bars"]
P_BEATS = M["upbeat"]["beats"]
TALK_A, TALK_B = 5.0, 5.5                          # talking clips bridging the songs
CALM_OUT = TB[10]                                  # Awake fades out here under talk A
T_UP = CALM_OUT + TALK_A                           # then 1901 bar 0 hits
t_p = lambda s: T_UP + (s - PB[0])                 # 1901 song time -> timeline
T_TAIL = t_p(PB[113]) + TALK_B                     # talk B after 1901, then the Awake tail
TAIL_FROM = TB[78]
t_tail = lambda s: T_TAIL + (s - TAIL_FROM)
END = t_tail(M["calm"]["audio_end"])
BAR = PB[1] - PB[0]

# 1) cold open on Awake bars 0..10 (2-bar cuts)
co = [0.0] + [TB[i] for i in (2, 4, 6, 8, 10)]
L0 = co[1] - co[0]
cold = [lambda L: shot("video", "IMG_6770.MOV", 0.0, slowmo=0.5, why="arriving by car (60 fps -> slow motion)"),
        lambda L: shot("video", "IMG_6770.MOV", round(L0 * 0.5 + 0.3, 2), slowmo=0.5, why="arriving by car, mountains"),
        lambda L: pin("GX014874.mp4", 62.0, L, cat="scenic", letterbox=True, why="first morning: sunlit forest valley"),
        lambda L: pin("GX014875.mp4", 14.0, L, cat="scenic", letterbox=True, why="high alpine panorama, sunstar"),
        lambda L: pin("GX014888.mp4", 17.0, L, cat="lifestyle", why="chairlift ride")]
for i, mk in enumerate(cold):
    L = co[i + 1] - co[i]
    s = mk(L)
    if s["src"] == "IMG_6770.MOV": take(s["src"], s["in"], s["in"] + L * 0.5)
    place(co[i], co[i + 1], s, "cold open")

# pinned shots used later: reserve them now so fillers cannot take them
pins = {
    # kinetic title: background cuts every 2 beats under the animated text
    "title": pin("IMG_5595.mp4", 24.0, 2.0, cat="scenic", why="title bg: sea of clouds"),
    "title2": pin("GX014903.mp4", 366.0, 2.0, cat="action", why="title bg: powder spray"),
    "title3": pin("96C1E7D0-5678-4DB1-A4CD-D536DF04C7E6.mp4", 3.0, 2.0, cat="scenic", why="title bg: bluebird piste"),
    "title4": pin("GX014875.mp4", 2.0, 2.0, cat="scenic", why="title bg: alpine panorama"),
    "talk_b": pin("GX014910.mp4", 482.5, TALK_B + 0.2, cat="talk", cam_audio=1.0, why="talk transition: regrouping in the village, chatting"),
    "legs": pin("GX014883.mp4", 6.0, 3 * BAR, cat="action", legs_ramp=True, why="camera skis under my legs (slow-mo)"),
    # user-requested clips (review round 4)
    "jump1": pin("VIDEO-2026-03-13-19-21-45.mp4", 13.0, 2 * BAR, cat="action", transpose=1, why="jump (phone held sideways)"),
    "jump2": pin("VIDEO-2026-03-13-19-21-45.mp4", 20.0, 4 * BAR, cat="action", transpose=1, cam_audio=1.0, why="jump, skis at the camera, laughing"),
    "f76d": pin("76d2044c-1ecc-4ef5-8632-1cff0fe656d4.mp4", 6.0, 2 * BAR, cat="action", why="forest run down to the lift"),
    "f4880": pin("GX014880.mp4", 49.5, 3 * BAR, cat="action", cam_audio=1.0, why="group messing about"),
    "c4900": pin("GX014900.mp4", 210.5, 4 * BAR, cat="crash", cam_audio=1.0, why="wipe-out in a cloud of spray, then posing"),
    "oneleg": pin("GX014904.mp4", 14.0, 3 * BAR, cat="action", cam_audio=1.0, why="skiing on one leg"),
    "fog_fall": shot("video", "VIDEO-2026-03-14-16-48-22.mp4", 7.6, cat="crash", cam_audio=1.0, why="fall in the fog + laughter (jump-cut)",
                     parts=[{"src": "VIDEO-2026-03-14-16-48-22.mp4", "in": 7.6, "dur": 3.4, "slowmo": 1.0},
                            {"src": "VIDEO-2026-03-14-16-48-22.mp4", "in": 15.0, "dur": 3.27, "slowmo": 1.0}]),
    "fall2nd": pin("VIDEO-2026-03-14-16-55-04.mp4", 63.3, 5 * BAR, cat="crash", cam_audio=1.0, why="falls a second time, everyone laughing"),
    "blur_in": pin("IMG_3764.mp4", 0.0, 2 * BAR, cat="lifestyle", why="blurry fog opener"),
    # sound bites: singing / 'nieeeuw' - music dips low, punch-in zoom
    "bite1": pin("GX014908.mp4", 74.9, 1 * BAR, cat="bite", cam_audio=1.0, bite=True, why="singing"),
    "bite2": pin("GX014908.mp4", 95.2, 2 * BAR, cat="bite", cam_audio=1.0, bite=True, why="nieeeuw"),
    "bite3": pin("GX014908.mp4", 128.8, 1 * BAR, cat="bite", cam_audio=1.0, bite=True, why="singing"),
    "bite4": pin("GX014909.mp4", 144.3, 2 * BAR, cat="bite", cam_audio=1.0, bite=True, why="funny sounds"),
    "bite5": pin("GX014909.mp4", 151.7, 1 * BAR, cat="bite", cam_audio=1.0, bite=True, why="funny sounds"),
    "fall_ph1": pin_best("VIDEO-2026-03-14-13-03-23.mp4", 2, 36, 3 * BAR + 0.2, "crash", cam_audio=1.0, why="white parka wipes out in deep powder"),
    "fall_ph2": pin_best("VIDEO-2026-03-14-16-55-04.mp4", 0, 70, 3 * BAR + 0.2, "crash", cam_audio=1.0, why="stuck in deep powder, friends laughing"),
    "fall_ph3": pin_best("VIDEO-2026-03-14-16-55-04.mp4", 70, 140, 2 * BAR + 0.2, "crash", cam_audio=1.0, why="kicking a ski up, still stuck"),
    # falls run 3 bars (~5 s) so the reactions/laughter after the fall are in, camera sound up
    "crash1": pin("GX014890.mp4", 11.0, 3 * BAR + 0.3, cat="crash", cam_audio=1.0, why="wipe-out in the whiteout + laughter"),
    "crash_v": pin("GX014910.mp4", 74.0, 4 * BAR, cat="crash", cam_audio=1.0, why="friend's backward fall"),
    "crash_a7": pin("A7F8E300-7FDB-44B3-AC01-37C69DFE4015.mp4", 49.0, 3 * BAR, cat="crash", cam_audio=1.0, why="crash: skis in the air"),
    "crash_skis": pin("GX014910.mp4", 120.0, 3 * BAR, cat="crash", cam_audio=1.0, why="skis up: another fall"),
    "powder_fall": pin_best("GX014903.mp4", 302, 330, 3 * BAR, "crash", cam_audio=1.0, why="floundering in deep powder"),
    "fall_fa1": pin_best("FA3DCEC9-3E36-46B1-A679-B4C31999DFD9.mp4", 128, 148, 3 * BAR, "crash", cam_audio=1.0, why="friend down in the snow, laughter"),
    "fall_fa2": pin_best("FA3DCEC9-3E36-46B1-A679-B4C31999DFD9.mp4", 64, 80, 3 * BAR, "crash", cam_audio=1.0, why="someone down, group around"),
    "fall_53": pin_best("5308BAB3-F73D-4595-BF90-76648498F6D8.mp4", 22, 38, 3 * BAR, "crash", cam_audio=1.0, why="friend down in the snow under blue sky"),
    "powder1": pin("GX014903.mp4", 290.0, 2 * BAR, cat="action", why="off-piste powder under the chairlift"),
    "powder2": pin("GX014903.mp4", 402.0, 2 * BAR, cat="action", why="steep powder descent"),
    "village": pin("GX014910.mp4", 495.0, PB[111] - PB[108], cat="lifestyle", why="skiing back into the village"),
    "end_run": pin("GX024910.mp4", 3.0, PB[113] - PB[111], cat="lifestyle", why="last metres: chalets"),
    "cheers": pin("7D5FD233-FAF9-4799-9639-73C46AB2C096 Copy.mp4", 0.3, TB[78] - TB[76], cat="lifestyle", cam_audio=1.0, why="cheers"),
    "dinner": pin("IMG_5532.mp4", 12.0, TB[80] - TB[78], cat="lifestyle", cam_audio=1.0, why="dinner, everyone laughing"),
    "charades": pin("IMG_6813.mp4", 64.0, TB[92] - TB[90], cat="lifestyle", cam_audio=1.0, why="charades"),
    "birthday": pin("IMG_8133.mp4", 20.0, TB[94] - TB[92], cat="lifestyle", cam_audio=1.0, why="birthday presents"),
}
pins.update({
    "credits": pin("IMG_5595.mp4", 36.0, END - t_tail(TB[96]), cat="scenic", dim=0.5, credits=True, why="credits over the sea of clouds"),
    "shadows": pin("5308BAB3-F73D-4595-BF90-76648498F6D8.mp4", 136.0, TB[96] - TB[94], cat="lifestyle", why="two long shadows"),
    "talk_a": best_talk(TALK_A),
    "dinner2": pin("IMG_5532.mp4", 38.5, TB[2] - TB[0], cat="lifestyle", cam_audio=1.0, why="dinner selfie, everyone cracking up"),
    "charades1": pin("IMG_6810.mp4", 24.0, TB[2] - TB[0], cat="lifestyle", cam_audio=1.0, why="charades"),
    "charades2": pin("IMG_6812.mp4", 34.0, TB[2] - TB[0], cat="lifestyle", cam_audio=1.0, why="charades round 2"),
    "presents": pin("IMG_5798.mp4", 70.0, TB[2] - TB[0], cat="lifestyle", cam_audio=1.0, why="presents"),
})
take("5308BAB3-F73D-4595-BF90-76648498F6D8.mp4", 130.0, 150.0)     # keep the whole shadows moment for the ending
take("VIDEO-2026-03-14-16-48-22.mp4", 7.6, 18.3)
take("GX014910.mp4", 94.0, 110.0)                                   # review: the 0:58 trees shot was boring

# User feedback (first cut): no still photos and no name cards (face_shot() stays available).

# talk A: Awake fades out, people talking/laughing, then 1901 kicks in
place(CALM_OUT, T_UP, pins["talk_a"], "talk")

# 2) 1901 montage intro: bars 0-8 two-bar cuts (establishing), 8-28 one-bar, 28-32 two-beat
cuts = [PB[i] for i in range(0, 9, 2)] + [PB[i] for i in range(9, 29)]
beat_ix = [nearest_beat(P_BEATS, PB[28])]
while P_BEATS[beat_ix[-1]] < PB[32] - 0.1: beat_ix.append(beat_ix[-1] + 2)
cuts += [P_BEATS[i] for i in beat_ix[1:]]
cuts[-1] = PB[32]
days_cycle = ["2026-03-13", "2026-03-14", "2026-03-15", "2026-03-16"]
for k in range(len(cuts) - 1):
    a, b = cuts[k], cuts[k + 1]; L = b - a
    cats = {"scenic", "lifestyle"} if k < 4 else {"action", "faces"} if k % 3 else {"action", "lifestyle", "faces"}
    s = pick(L, cats, days={days_cycle[k % 4]}, prev=prev_files()) or pick(L, cats, prev=prev_files())
    place(t_p(a), t_p(b), s, "montage")

# 3) kinetic title over 4 quick background shots (2 beats each)
b32 = nearest_beat(P_BEATS, PB[32])
tcuts = [PB[32]] + [P_BEATS[b32 + 2 * k] for k in (1, 2, 3)] + [PB[34]]
for k, key in enumerate(("title", "title2", "title3", "title4")):
    place(t_p(tcuts[k]), t_p(tcuts[k + 1]), pins[key], "title")

# 4) action chapter 1 (13-14 Mar)
chapter(PB, t_p, 34, 55, {"2026-03-13", "2026-03-14"},
        {34: (pins["jump1"], 2), 36: (pins["legs"], 3), 40: (pins["fall_ph1"], 3), 44: (pins["crash1"], 3),
         47: (pins["f4880"], 3), 51: (pins["fog_fall"], 4)}, "chapter 1")

# 5) breakdown (music low): blurry fog opener, singing bites, the deep-powder double fall, more bites
bar = 55
for p, nb in [("blur_in", 2), ("bite1", 1), ("bite2", 2), ("bite3", 1), ("fall_ph2", 3), ("fall2nd", 5), ("bite4", 2), ("bite5", 1)]:
    place(t_p(PB[bar]), t_p(PB[min(bar + nb, 72)]), pins[p], "breakdown"); bar += nb

# 6) action chapter 2 (15-16 Mar)
chapter(PB, t_p, 72, 108, {"2026-03-15", "2026-03-16"},
        {74: (pins["powder1"], 2), 76: (pins["oneleg"], 3), 80: (pins["crash_a7"], 3), 83: (pins["f76d"], 2),
         86: (pins["powder2"], 2), 88: (pins["c4900"], 4), 92: (pins["jump2"], 4), 96: (pins["crash_v"], 4),
         102: (pins["crash_skis"], 3), 105: (pins["fall_fa1"], 3)}, "chapter 2")

# 7) back to the village, then talk B (1901 ends, voices, then Awake)
place(t_p(PB[108]), t_p(PB[111]), pins["village"], "village")
place(t_p(PB[111]), t_p(PB[113]), pins["end_run"], "village")
place(t_p(PB[113]), T_TAIL, pins["talk_b"], "talk")

# 8) outro on Awake bars 78.. : cheers, dinner, charades, presents, birthday, shadows, credits
tb = lambda i: t_tail(TB[i])
place(tb(78), tb(80), pins["cheers"], "outro")
place(tb(80), tb(82), pins["dinner"], "outro")
for k, key in enumerate(("dinner2", "charades1", "presents", "charades2")):
    place(tb(82 + 2 * k), tb(84 + 2 * k), pins[key], "outro")
place(tb(90), tb(92), pins["charades"], "outro")
place(tb(92), tb(94), pins["birthday"], "outro")
place(tb(94), tb(96), pins["shadows"], "outro")
place(tb(96), END, pins["credits"], "credits")

# music: Awake drops away under talk A, 1901 creeps in under it (1.6 s) and is fully up on bar 0,
# the Awake tail starts under talk B and carries the outro to the end - the music never stops
CREEP = 1.6
cues = [{"track": "calm", "from": 0.0, "to": T_UP + 0.05, "at": 0.0, "fade_out": 3.0},
        {"track": "upbeat", "from": PB[0] - CREEP, "to": M["upbeat"]["audio_end"], "at": T_UP - CREEP,
         "fade_in": CREEP, "fade_curve": "sq"},
        {"track": "calm", "from": TAIL_FROM - TALK_B, "to": M["calm"]["audio_end"], "at": T_TAIL - TALK_B,
         "fade_in": 1.0, "fade_out": 4.0}]

finish(END, cues, t_p(PB[32]), t_p(PB[34]), M["upbeat"]["bpm"])

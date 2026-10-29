# Writing plan.py

`plan.py` lives in the event folder and describes one film. It runs through `beatcut 13_edl` with
`from edl_lib import *`. Start from `templates/plan.py` (one song, config-driven) or `examples/ski-trip-plan.py`
(two songs, talk transitions, chapters, funny breakdown, outro).

## What edl_lib gives you
| name | what |
|---|---|
| `M` | music.json: `M[role]["bars"]`, `["beats"]`, `["bpm"]`, `["audio_end"]`, `["sections"]` |
| `tags`, `inv`, `idx`, `day(f)` | visual tags, inventory, analysed files, shooting day of a file |
| `S` | event lists: `evening`, `ending(f, a)`, `force_vertical`, `requested_sound`, `cam_override`, … |
| `pin(f, a, L, **kw)` | fixed shot: file f from second a, L s long (reserves the moment) |
| `pin_best(f, a0, a1, L, cat)` | best free window inside [a0, a1]; for `crash` it shifts so the laughter is in |
| `pick(L, cats, days=, prev=)` | best free filler of length L from tagged categories (None if nothing fits) |
| `best_talk(L)` | the window with the most talking/laughing, used to bridge song changes |
| `take(f, a, b)` | reserve/block a range (rejected boring bits, moments saved for later) |
| `place(t0, t1, shot, section)` | put a shot on the timeline (snapped to frames) |
| `chapter(bars, to_t, b0, b1, days, special, label)` | 1-bar action cuts with pinned specials `{bar: (shot, n_bars)}` |
| `nearest_beat(beats, t)`, `prev_files()` | helpers |
| `finish(end, cues, title_t0, title_t1, bpm)` | speed ramps, sound decisions, checks, writes edl.json |

Shot options (keyword args on `pin`/`shot`): `cat`, `why` (shows in shotlist.csv), `cam_audio` (0-1),
`letterbox`, `slowmo` (0.5 = half speed, ≥ 50 fps sources only), `transpose` (1 = phone held sideways),
`bite` (sound bite: punch-in zoom, music −14 dB), `legs_ramp` (fixed slow-mo ramp), `dim`, `credits`,
`parts` (jump-cut: list of `{src, in, dur, slowmo}`).

## Timeline math
Put cuts on the song's bars and beats. With one song starting at bar 0: `t = lambda s: s - BARS[0]`.
With several songs, define a song-time → timeline function per song (see the ski example: `t_p`, `t_tail`).

## Music cues
`finish()` takes the music as cues: `{"track": role, "from": song_s, "to": song_s, "at": timeline_s,
"fade_in": s, "fade_out": s, "fade_curve": "sq"}`. Overlap cues under a talking clip, fading one out and
creeping the next in (`fade_curve: sq`, ~1.6 s). Make sure the last cue runs to the end of the film.

## Structures that work
- **Cinematic + funny (3-5 min, 16:9)**: calm song: cold open (travel, arrival, first views, 2-bar cuts) →
  talk → upbeat song: montage (2-bar → 1-bar → 2-beat cuts) → kinetic title (2 bars) → action chapter →
  breakdown with sound bites and falls (music low) → action chapter → back home → talk → calm song: outro
  (evenings, dinner, games) → credits.
- **Short (30-60 s, 9:16)**: hook in the first 2 s (the best fall or jump, with sound), then 1-beat/2-beat
  cuts on one upbeat song, 1 sound bite, end on a laugh or freeze. No title card, or a 1-beat one. Needs the 9:16
  renderer (ROADMAP).
- **Emotional (wedding/birthday)**: slow song, 4-bar cuts, speeches as sound-on segments with the music ducked,
  build to the high point (first dance / cake), warm or natural grade, no glitch title.

## Checks the plan does for you
No moment used twice (asserts), no photo twice, camera sound auto-muted when no voices are found (unless the
file is in `S.requested_sound`/`S.evening` or the shot is a bite), speed ramps on crashes that have a ≥ 50 fps copy.

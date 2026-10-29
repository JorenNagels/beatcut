# Workflow

`hf = python <repo>/hf.py <event-folder>`. Steps are cached: re-running is cheap and only new files get processed.

## Phase 1: what is there (no checkpoint, just report)
```
hf 01_inventory          # inventory.csv/.json: every video/photo, duration, resolution, fps, bitrate, shot time
hf 01b_dates             # real shooting dates (QuickTime creationdate / EXIF / WhatsApp names)
hf 02_dedup              # duplicates.csv, dedup.json: exact + perceptual + trimmed copies; hints for 60 fps copies
hf 03_analyze 6          # per-frame signals for kept files (6 workers): motion, shake, faces, sharpness, audio
hf 05_events             # per-second features + events.json (voice/laughter peaks, motion events)
hf 04_sheets 6           # contact sheets (1 frame / 6 s) for the visual pass -> sheets/
```
Report: hours of footage, cameras, duplicates found + GB, what telemetry/fps/resolution there is.

## Phase 2: the visual pass (you look, you tag)
Open the contact sheets (sheets/*.jpg) and write the visual tags: `tags_source.py` in the event folder (copy the
shape from the ski example: `(file, start_s, end_s, cat, rating 1-5, note, people)` + `DAY` estimates for undated
files + `PHOTOS` ratings). Run it, and it writes `tags.json` next to itself.
Categories: `scenic`, `faces`, `action`, `lifestyle`, `crash` (falls/fails with reactions), `boring`.
Rate honestly: 5 = would open the film, 3 = good filler, 1 = only if desperate.

```
hf 06_candidates         # candidates.json/.csv (~60 clips, action + calm) + photos_best.json
hf 07_previews           # small looping previews for the review page
hf 08_review             # review.html (light theme): keep/drop/star per candidate, exports selections.json
```
**Checkpoint 1**: open review.html for the user. Also ask for their funny moments ("who fell where, who sang").
Those are usually the best clips, and the detectors miss half of them.

## Phase 3: people (optional; ask in the interview)
```
hf 10_people 6           # face detection + clustering -> people.json, people/*.jpg
hf people_sheet          # sheets/people_check.jpg to check clusters; merge with people.same_as in event.yaml
hf 11_people_page        # names.html: one crop per unknown person -> user exports names.json into the event folder
```
Then write `people_names.json` (`{"people": {"Name": {"face_ids": ["p01", ...]}}}`).

## Phase 4: music
Put the songs somewhere (event folder `music/` is fine), list them in `event.yaml` → `music.tracks` with roles
(`calm`, `upbeat`, `main` …), then `hf 12_music`. It writes music.json (BPM, beats, bars, sections) and
sheets/music_*.png (loudness + sections).
**Checkpoint 2**: tell the user BPM, length and where the drops/breakdowns are, and how the film maps onto it.
If the song is shorter than the film, plan a second song or a loop, because the music must never stop early.

## Phase 5: find more fun
```
hf 15_fun_search         # untagged talking/laughing windows -> fun_windows.json + sheets/fun_*.jpg
hf 17_singing GX014908.mp4 GX014909.mp4    # pitched voice (singing, silly noises) in wind-heavy audio
hf inspect_clip <file> <start> <dur> <fps> <out.jpg>   # frames + loudness/voice strip of a section
```

## Phase 6: plan → preview → feedback rounds
```
hf 13_edl                # runs <event>/plan.py -> edl.json (asserts no moment is used twice)
hf 14_render preview --force   # render/preview.mp4, 960x540, ~1-2 min
hf 18_shotlist           # shotlist.csv: film time, section, source + in-point, slow-mo, sound and why
hf edit_sheet preview    # sheets/edit_preview.jpg, one frame per shot (self-check)
```
**Checkpoint 3**: the user watches the preview and gives timestamped feedback. Loop until they're happy.

## Phase 7: final
```
hf 14_render final --force     # render/final.mp4, 1920x1080, sharpened + grain, ~10-20 min
hf 18_shotlist
```
Update the event's README/project.md with the section table and how it was made.

## Without `--force`
14_render reuses already-rendered shots in render/seg_<mode>/ by index, so after changing the plan always pass
`--force` (otherwise shots shift and stale segments get reused).

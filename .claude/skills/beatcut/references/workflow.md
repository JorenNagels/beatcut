# Workflow

`beatcut = python <repo>/beatcut.py <event-folder>` (shorthand below). Steps are cached: re-running is cheap and only new files get processed.

## Phase 1: what is there (no checkpoint, just report)
```
beatcut 01_inventory          # inventory.csv/.json: every video/photo, duration, resolution, fps, bitrate, shot time
beatcut 01b_dates             # real shooting dates (QuickTime creationdate / EXIF / WhatsApp names)
beatcut 02_dedup              # duplicates.csv, dedup.json: exact + perceptual + trimmed copies; hints for 60 fps copies
beatcut 03_analyze 6          # per-frame signals for kept files (6 workers): motion, shake, faces, sharpness, audio
beatcut 05_events             # per-second features + events.json (voice/laughter peaks, motion events)
beatcut 04_sheets 6           # contact sheets (1 frame / 6 s) for the visual pass -> sheets/
```
Report: hours of footage, cameras, duplicates found + GB, what telemetry/fps/resolution there is.

## Phase 1b: listen and look with AI (when the AI extras are installed; all cached)
```
beatcut 19_transcribe         # Whisper: transcripts/*.json (word timestamps) + transcripts.md (all speech, one file)
beatcut 19b_sounds            # laughter / cheering / singing / shouting -> sounds.json (counts as voices in the plan)
beatcut 20_clip --autotag     # image embeddings for search + tags_auto.json (first-draft visual tags)
beatcut 21_scenes 4           # shot changes inside clips -> scenes.json (fillers never cross one)
```
Missing extras? The step says so; offer `python install.py --extras` (ask first: several GB). Without them
everything still works from the voice-band detector and hand tags.
Read `transcripts.md` (grep it): quotes, names, "kijk", "oh no", laughter in the text are where the fun is.
Whisper on wind-heavy GoPro audio produces some junk lines ("Ja.", repeated words); trust lines with conf >= 0.6.

## Phase 2: the visual pass (you look, you tag)
Open the contact sheets (sheets/*.jpg) and write the visual tags. With `tags_auto.json` (20_clip) start from it:
check its categories on the sheets, fix ratings, add what a picture can't tell (falls, who is who), then write `tags_source.py` in the event folder (copy the
shape from the ski example: `(file, start_s, end_s, cat, rating 1-5, note, people)` + `DAY` estimates for undated
files + `PHOTOS` ratings). Run it, and it writes `tags.json` next to itself.
Categories: `scenic`, `faces`, `action`, `lifestyle`, `crash` (falls/fails with reactions), `boring`.
Rate honestly: 5 = would open the film, 3 = good filler, 1 = only if desperate.

```
beatcut 06_candidates         # candidates.json/.csv (~60 clips, action + calm) + photos_best.json
beatcut 07_previews           # small looping previews for the review page
beatcut 08_review             # review.html (light theme): keep/drop/star per candidate, exports selections.json
```
**Checkpoint 1**: open review.html for the user. Also ask for their funny moments ("who fell where, who sang").
Those are usually the best clips, and the detectors miss half of them.

## Phase 3: people (optional; ask in the interview)
```
beatcut 10_people 6           # face detection + clustering -> people.json, people/*.jpg
beatcut people_sheet          # sheets/people_check.jpg to check clusters; merge with people.same_as in event.yaml
beatcut 11_people_page        # names.html: one crop per unknown person -> user exports names.json into the event folder
```
Then write `people_names.json` (`{"people": {"Name": {"face_ids": ["p01", ...]}}}`).

## Phase 4: music
Put the songs somewhere (event folder `music/` is fine), list them in `event.yaml` → `music.tracks` with roles
(`calm`, `upbeat`, `main` …), then `beatcut 12_music`. It writes music.json (BPM, beats, bars, sections) and
sheets/music_*.png (loudness + sections).
**Checkpoint 2**: tell the user BPM, length and where the drops/breakdowns are, and how the film maps onto it.
If the song is shorter than the film, plan a second song or a loop, because the music must never stop early.

## Phase 5: find more fun
```
beatcut search "falling in the snow" "lying in the snow laughing"   # text search over all frames -> sheets/search_*.jpg
beatcut timeline GX014904.mp4 8 26   # filmstrip + waveform (laughs in red) + spoken words: exact in/out points
beatcut 15_fun_search         # untagged talking/laughing windows -> fun_windows.json + sheets/fun_*.jpg
beatcut 17_singing GX014908.mp4 GX014909.mp4    # pitched voice (singing, silly noises) in wind-heavy audio
beatcut inspect_clip <file> <start> <dur> <fps> <out.jpg>   # frames + loudness/voice strip of a section
```

## Phase 6: plan → preview → feedback rounds
```
beatcut 13_edl                # runs <event>/plan.py -> edl.json (asserts no moment is used twice)
beatcut 14_render preview --force   # render/preview.mp4, 960x540, ~1-2 min
beatcut 18_shotlist           # shotlist.csv: film time, section, source + in-point, slow-mo, sound and why
beatcut edit_sheet preview    # sheets/edit_preview.jpg, one frame per shot (self-check)
beatcut 23_check preview      # black / frozen / flash frames, music gaps, loud cuts, loudness -> check_preview.json
```
**Self-check loop** (before every checkpoint): fix what 23_check reports in plan.py, re-render, check again.
Max 3 rounds; then tell the user what is left and why (e.g. "frozen 0.4 s at 1:12: the clip ends there").
**Checkpoint 3**: the user watches the preview and gives timestamped feedback. Loop until they're happy.
**Hand-tuning in an editor**: `beatcut 22_export` writes render/edit.otio (DaVinci Resolve: File > Import >
Timeline), edit.xml (Premiere) and edit.fcpxml (Final Cut) with the same cuts on the original files.

## Phase 7: final
```
beatcut 14_render final --force     # render/final.mp4, 1920x1080, sharpened + grain, ~10-20 min
beatcut 23_check final
beatcut 18_shotlist
```

## Shorts (9:16 TikTok / Reels / Shorts)
One event can have the film plus any number of shorts. Each short is a plan file `plan_<name>.py` in the event
folder (start from `templates/plan_short.py`), with its own EDL and renders:
```
beatcut 13_edl plan_short1.py                  # -> edl_short1.json
beatcut 14_render preview --force --edl short1 # -> render/short1_preview.mp4 (540x960); final: 1080x1920
beatcut 23_check preview --edl short1
beatcut 18_shotlist --edl short1
```
By default a short skips moments already used in the film or other shorts (`REUSE = False`). Landscape shots get
a crop that follows faces and motion; set `reframe="fit"` (whole frame on a blurred fill), `"center"` or a fixed
0-1 position on a shot when the crop misses the action. Check the edit sheet: a crop that cuts off the person who
falls is the most common problem.

## Graphics (Remotion)
With `style.graphics: remotion` in event.yaml, 14_render draws the title (`style.title_style`), the styled captions
(with emoji), the end card and lower thirds with Remotion instead of the built-in title/drawtext/libass. The graphics
are rendered once per change into render/gfx/ (a 5-min film: ~2 min at preview size) and laid over the shots, so
always pass `--force` after switching engines or changing the plan. Tweak the look: `cd remotion && npm run studio`.
Lower thirds: `lower_third="Vincent"` or `{"text": "Vincent", "sub": "backwards fall"}` on a shot in the plan.

## Subtitles
`subtitles:` in event.yaml (or `finish(..., subtitles=)`): `speech` (sentence subtitles, bottom) or
`styled-captions` (TikTok style, 1-3 big words, current word yellow). Only audible speech gets subtitles (shots with
camera sound on); `subs=False` on a shot hides them, `subs=True` forces them. Every render also writes a `.srt`
next to the video for platforms that take a subtitle file. Needs 19_transcribe; check the words in the edit
(Whisper mishears names: fix those lines in transcripts/<id>.json and re-render).
Update the event's README/project.md with the section table and how it was made.

## Without `--force`
14_render reuses already-rendered shots in render/seg_<mode>/ by index, so after changing the plan always pass
`--force` (otherwise shots shift and stale segments get reused).

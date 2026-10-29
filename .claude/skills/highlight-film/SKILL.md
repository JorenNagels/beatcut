---
name: highlight-film
description: Make a highlight film (or short vertical clips) from a folder of trip/event footage - GoPro, phone, WhatsApp copies, photos - without the user watching everything. Interviews the user, analyses and de-duplicates the footage, finds the best and funniest moments, cuts to the beat of their music and renders with ffmpeg; then iterates on their feedback. Use when the user wants a trip video, holiday film, vacation/ski/wedding/birthday/festival edit, highlight reel, recap, montage or TikTok/Reels from their own footage, or wants to continue/redo an earlier film made with this pipeline.
---

# Highlight film

The `highlight-film` repo holds a generic Python + ffmpeg pipeline. Its path is in `repo-path.txt` next to this
file (written by `install.py`); if that file is missing, ask the user where they cloned the repo and to run
`python install.py` there (`python3` on macOS). Each film is
an **event folder** elsewhere on disk holding `event.yaml` (the interview answers), the hand-made decisions
(`tags.json`, `plan.py`, `people_names.json`) and `project.md` (session memory). Footage is read-only; generated
files go to the event's work folder. Run every step as:

```
python <repo>/hf.py <event-folder> <step> [args]      # python3 on macOS; e.g. python hf.py D:\trips\ibiza-2027 02_dedup
```

## How to work
1. **Continuing?** If the event folder already has `project.md`, read it and `event.yaml` first, summarise where
   things stand in two lines, and carry on from there. Don't redo the interview.
2. **Interview** (new event): follow [references/interview.md](references/interview.md). Ask with AskUserQuestion
   in 2-3 short rounds; never ask what the footage or saved preferences already answer. Write `event.yaml` from
   `templates/event.yaml` and start `project.md` from `templates/project.md`.
3. **Run the phases** in [references/workflow.md](references/workflow.md). Stop at each checkpoint (review page,
   music, preview cut) and show the user something concrete, such as a page, a sheet or a timestamped list.
4. **Write the plan**: copy `templates/plan.py` for a simple one-song film, or adapt `examples/ski-trip-plan.py`
   for a structured film (cold open, talk transitions, chapters, funny breakdown, outro). Read
   [references/plan-guide.md](references/plan-guide.md) first.
5. **Feedback rounds**: the user gives timestamps ("2:09 should have sound", "add GX014904 from 0:10").
   Look up the shot in `shotlist.csv`, change `plan.py` (pins, `S.cam_override`, `take()` to block a moment),
   re-run `13_edl` → `14_render preview` → `18_shotlist`, and check the cut points before answering (see self-check).
6. **Persist**: after every round, append decisions and feedback to `project.md` (what changed and why). The
   next session starts from it.

## Defaults the user has already chosen (don't ask again; override only if they say so)
Read [references/preferences.md](references/preferences.md). Short version: no Ken Burns photo zooms, no name
cards, the music never stops (it ducks under voices and songs change under a talking clip), camera sound only on
talking/laughing/reactions, a kinetic modern title, no "filmed on" or date lines in the credits, funny moments
are the heart of the film, light-themed helper pages.

## Self-check before showing a render
- `edit_sheet.py preview` → look at `sheets/edit_preview.jpg` (one frame per shot) for black frames, wrong
  rotation, lens-in-snow and the same scene twice in a row.
- `inspect_clip.py` on anything the user mentioned, to make sure the moment is actually in the shot.
- Check the plan output: total length, "no moment used twice: OK", and that the music lasts to the end.
- Say plainly what you could not do (e.g. "no telemetry in these files", "that clip is only 720p").

## Hard rules
- Never write to, move or delete anything in the source folder.
- Ask before installing anything big (models over ~200 MB, CUDA wheels, Node packages).
- Music files are the user's; never commit them or renders to git (the repo's .gitignore covers event folders).
- Lessons from earlier films are in [references/lessons.md](references/lessons.md). Read it once per event.
- Planned features (subtitles, 9:16 shorts, Whisper, CLIP search, Resolve export, Remotion titles) are in
  `ROADMAP.md`. If the user asks for one that isn't built yet, say so and offer to build it.

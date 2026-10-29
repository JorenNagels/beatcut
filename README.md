# highlight-film

Turn a folder of trip or event footage (GoPro, phones, WhatsApp copies, photos) into a beat-synced highlight film
without watching everything yourself. A [Claude Code](https://claude.com/claude-code) skill, `/highlight-film`,
asks you a few questions, analyses the footage, finds the best and funniest moments, cuts them to the beat of your
music and renders the film. You give feedback on previews until it's right.

- **Local and free**: Python, ffmpeg and OpenCV on your own computer. Your footage is never uploaded anywhere by
  the pipeline (Claude does see contact-sheet images and file names while it edits).
- **Your footage is never changed**: everything generated goes into a separate work folder.
- **Duplicates handled**: the same clip from the group chat, the shared album and the SD card is used once,
  in its best copy.
- **Edits like a person**: cuts on bars and beats, song changes under people talking, camera sound only when someone
  laughs or talks, real slow motion on 60 fps footage, a kinetic title, a shot list explaining every choice.

## Install (once)
You need [Python 3.10+](https://www.python.org/downloads/), git and [Claude Code](https://claude.com/claude-code).

**Windows**
```powershell
git clone https://github.com/JorenNagels/highlight-film
cd highlight-film
python install.py
```
**macOS**
```bash
git clone https://github.com/JorenNagels/highlight-film
cd highlight-film
python3 install.py
```
The installer sets up a Python environment, downloads two small face models (~40 MB), checks for ffmpeg
(offers to install it with winget or [Homebrew](https://brew.sh)) and links the skill into `~/.claude/skills`, so
`/highlight-film` works in every Claude Code session. Run it again after moving the repo or pulling updates.

**Even easier:** open Claude Code in the cloned folder and say *"install this"*.

## Make a film
1. Make a folder for the event and put all footage in `media` inside it (any layout, subfolders are fine):
   ```
   ibiza-2027/
     media/
       gopro-sam/    GX010001.MP4 …        two cameras with the same file names are fine
       phone-alex/   IMG_1234.MOV …
       whatsapp/     VIDEO-2027-07-03-14-22-10.mp4 …
     music/          the songs (optional: Claude can suggest some)
   ```
2. Open Claude Code in `ibiza-2027` and type **`/highlight-film`**.
3. Answer a few questions: what it is, length and format, the feel, music, title, must-have clips.
4. Check the review page, pick the music, watch the previews, give feedback with timestamps ("0:58 is boring",
   "add GX010023 from 0:10, the fall"), then render the final film.

Come back another day? Open Claude Code in the same folder and run `/highlight-film` again; it continues from
`project.md`.

### Footage tips
- **Use originals where you can**: GoPro straight from the SD card (keep the `.LRV`/`.THM` files), phone videos by
  cable/AirDrop/iCloud "Download originals". Shared-album and WhatsApp copies are compressed (often 720p) and
  lose GoPro data, though WhatsApp copies are still useful (sometimes 60 fps, good for slow motion).
- Don't clean up first: duplicates are found automatically. Adding clips later is fine; only new files get analysed.
- The footage can also stay where it is (external drive): set `source:` in `event.yaml` to its path.
- iPhone `.HEIC` photos and HEVC videos work.

### Music
Use songs you have the rights to for where you'll post the film. Music files are never committed or uploaded.

## What's in an event folder
```
ibiza-2027/
  event.yaml        your answers: paths, music, title, style, sound, people
  tags_source.py    visual tags (Claude writes them from contact sheets) -> tags.json
  plan.py           the film: sections, pinned shots, music cues
  project.md        session log: decisions and feedback rounds
  media/            your footage (never modified)
  work/             everything generated: analysis cache, sheets, review page, render/preview.mp4, render/final.mp4
```

## Run steps by hand
```
python hf.py <event-folder> list
python hf.py <event-folder> 13_edl
python hf.py <event-folder> 14_render preview --force
```

| step | what |
|---|---|
| `01_inventory`, `01b_dates` | every video/photo with duration, resolution, fps, real shooting time |
| `02_dedup` | exact, re-encoded and trimmed duplicates (keeps the best copy, maps 60 fps copies for slow motion) |
| `03_analyze`, `05_events` | per-second motion/shake/faces/sharpness/audio; voice & laughter peaks |
| `04_sheets` | contact sheets for the visual pass |
| `06_candidates`, `07_previews`, `08_review` | ~60 candidate clips + best photos on a review page |
| `10_people`, `people_sheet`, `11_people_page` | face clustering + a page to name people |
| `12_music` | tempo, beat grid, bars, sections of each song |
| `15_fun_search`, `17_singing` | talking/laughing windows; singing and silly sounds in windy audio |
| `13_edl` | runs the event's `plan.py` → `edl.json` (never uses a moment twice) |
| `14_render` | `preview` (960×540, ~1.5 min) or `final` (1080p, grain) |
| `16_title` | kinetic title frames (called by the renderer) |
| `18_shotlist`, `edit_sheet`, `inspect_clip` | shot list CSV, one-frame-per-shot sheet, close look at a clip |

## Repo layout
```
install.py                  one-time setup (Windows, macOS, Linux)
AGENTS.md                   instructions for coding agents (CLAUDE.md imports it)
hf.py                       step runner (sets the event, uses .venv)
pipeline/                   the steps + common.py (config) + edl_lib.py (plan toolkit)
templates/                  event.yaml, plan.py (one-song starter), project.md
examples/                   ski-trip-plan.py (complete two-song film), tags_source.py
fonts/                      Oswald (SIL Open Font License), the default title font
.claude/skills/highlight-film/   SKILL.md + references (interview, workflow, plan guide, default taste, lessons)
ROADMAP.md                  next: Whisper, CLIP search, Resolve export, TikTok shorts + subtitles, Remotion titles
```

## Status
Used for one finished 5-minute film so far (Windows 11). macOS is supported by design (pathlib, Homebrew ffmpeg,
bundled font) but not yet tested on a Mac. Issues and pull requests welcome.

Inspired by [browser-use/video-use](https://github.com/browser-use/video-use) (text-first footage for the LLM,
ask → confirm → cut → self-check → persist) and [CutClaw](https://github.com/GVCLab/CutClaw) (music-structure-aware
editing). MIT licensed.

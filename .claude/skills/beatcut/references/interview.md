# Setup interview

Goal: fill `event.yaml` (see `templates/event.yaml`) with as few questions as possible. Look first, then ask.

## Where is the footage?
If the user hasn't said: ask for the folder. Recommended layout is an event folder with `media/` inside
(subfolders per camera/person are fine; files are identified by their path inside `media/`, so two GoPros with
the same file names don't clash). Footage can also stay where it is (`source:` absolute path in event.yaml).
If the event folder doesn't exist yet, create it with `event.yaml`, `project.md`, `music/`. Never move the footage.

## Look before asking
- List the footage folder (count, cameras from file names: `GX…`/`GH…` GoPro, `IMG_…` iPhone, `VIDEO-…` WhatsApp,
  UUID names = iCloud/AirDrop exports). Check one file with ffprobe for resolution/fps.
- Dates from file names / metadata → a first guess at the days.
- A style-reference video in the folder? Put it in `exclude` and ask whether it is the reference.
- Music files in the folder or the event folder? Then the music is probably chosen.

## Round 1 (AskUserQuestion, up to 4 questions)
1. **What is it?** ski trip / summer holiday / city trip / wedding / birthday / festival / other
   → decides which moments to hunt for (jumps & falls, speeches & first dance, scenery & food, crowd & stage).
2. **Length & format**: Instagram/TikTok short (30-60 s, 9:16), group film (3-5 min, 16:9), long cut (8+ min),
   or several (one film + a few shorts).
3. **Feel** (multi-select): funny/chaotic, cinematic/calm, high-energy, emotional. Offer a reference video.
4. **Music**: "I have songs" (where?), "suggest some after you've seen the footage", or "one song for the whole film".

## Round 2 (only what is still open)
- **Footage quality**: if the files are 720p/compressed copies (iCloud Shared Album, WhatsApp), ask once if the
  originals (SD card, phone) still exist. Continue with what's there if not.
- **Must-haves / must-nots**: clips they already know they want, as `file + timestamp + why`, and things
  that must stay out (people who don't want to be in it, private moments).
- **Title & credits**: film name; title style (kinetic slam, minimal, none); credits lines (default: title + music).
- **People**: recognise faces so everyone gets screen time? (default yes). Names on screen? (default no).
- **Sound**: camera audio only on talking/laughing (default), more ambient sound, or music only.
- **Subtitles** (shorts or speech-heavy films): none / speech (sentence subtitles) / styled-captions (TikTok-style
  words). Default: styled-captions on shorts, none on the film. Needs the AI extras (Whisper).
- **Shorts**: when they want shorts too, how many and how long (15 / 30 / 60 s), and whether a short may reuse
  moments from the film (default: no, different moments).

## Defaults when the user says "you decide"
| field | default |
|---|---|
| length | 3-5 min group film, 16:9 |
| feel | cinematic + funny |
| structure | cold open (calm song) → talk → fast montage → kinetic title → chapters by day → funny breakdown → outro (evenings) → credits |
| grade | cool-muted for snow/winter, warm for summer, punchy for shorts, natural for weddings |
| letterbox | scenic shots only (cinematic films) |
| slow motion | only real ≥ 50 fps footage, as speed ramps on impacts/jumps |
| camera sound | voices/laughter only, music never stops |

## After the interview
Write `event.yaml`, repeat the plan back in 3-4 lines ("4-min film, 16:9, cinematic + funny, Awake → 1901 →
Awake, title IBIZA / SUMMER / 2027, …"), then start phase 1.

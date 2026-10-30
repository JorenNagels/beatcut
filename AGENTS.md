# beatcut

Instructions for coding agents (Claude Code, Codex, Cursor, ...). Python + ffmpeg pipeline and a Claude Code skill that turn trip/event footage into a beat-synced highlight film.
Read README.md for the layout; the skill is in `.claude/skills/beatcut/`.

## If the user asks to install / set up
Run `python install.py` (`python3` on macOS/Linux). It creates `.venv`, installs requirements, downloads the face
models, checks ffmpeg (offers winget/Homebrew; ask the user before installing), offers the optional AI extras
(several GB: ask the user; `--extras` / `--no-extras` answer it without a prompt) and links the skill into
`~/.claude/skills`. Afterwards tell them: put footage in `<event folder>/media`, open Claude Code in the event
folder, type `/beatcut`.

## Working on the pipeline
- Steps are `pipeline/NN_name.py`, run via `python beatcut.py <event-folder> <step>`; they need `BEATCUT_EVENT` (beatcut.py sets it).
- Per-event data never goes in the repo: event.yaml, plan.py, tags, people and project.md live in the event folder,
  either outside the repo or in `events/<name>/` (git-ignored). Never run `git clean -x` here: it deletes those.
  Test changes on a real event, e.g. `python beatcut.py events/<name> 13_edl`.
- Source footage is read-only. Generated files go to the event's `work` folder.
- Files are identified by their path inside the source folder (`cam2/GX010001.MP4`); use `common.base()` for
  camera-name patterns.
- Keep it cross-platform (Windows + macOS): `pathlib`, no hard-coded Windows paths, the bundled font in `fonts/`.
- After changing a step, re-run it on a real event and compare outputs (edl.json, `18_shotlist`, a preview
  render) before and after.
- Code style: compact, numbered steps with a docstring explaining what the step does and writes.
- AI packages (torch, faster-whisper, open_clip, panns, beat_this) are optional: import them through
  `common.need()` inside the step, so the rest of the pipeline runs without them. Helper modules end in `_lib.py`
  (beatcut.py does not list them as steps).
- An event can hold several EDLs (film + shorts): read and write them through `common.edl_file()` / `out_name()`.
- `remotion/` is an optional Node sub-project (graphics); pin all `@remotion/*` packages to the same exact version.
  Each event can have its own components in `<event>/graphics/*.tsx` (bundled via `remotion/webpack.mjs`; they
  import helpers from `'beatcut'` = `remotion/src/lib.ts`, so keep that API stable). Check a graphics change with
  `python beatcut.py events/<name> gfx <n>` (contact sheet) and a preview render.

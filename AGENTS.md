# highlight-film

Instructions for coding agents (Claude Code, Codex, Cursor, ...). Python + ffmpeg pipeline and a Claude Code skill that turn trip/event footage into a beat-synced highlight film.
Read README.md for the layout; the skill is in `.claude/skills/highlight-film/`.

## If the user asks to install / set up
Run `python install.py` (`python3` on macOS/Linux). It creates `.venv`, installs requirements, downloads the face
models, checks ffmpeg (offers winget/Homebrew; ask the user before installing) and links the skill into
`~/.claude/skills`. Afterwards tell them: put footage in `<event folder>/media`, open Claude Code in the event
folder, type `/highlight-film`.

## Working on the pipeline
- Steps are `pipeline/NN_name.py`, run via `python hf.py <event-folder> <step>`; they need `HF_EVENT` (hf.py sets it).
- Per-event data never goes in the repo: event.yaml, plan.py, tags, people and project.md live in the event folder.
- Source footage is read-only. Generated files go to the event's `work` folder.
- Files are identified by their path inside the source folder (`cam2/GX010001.MP4`); use `common.base()` for
  camera-name patterns.
- Keep it cross-platform (Windows + macOS): `pathlib`, no hard-coded Windows paths, the bundled font in `fonts/`.
- After changing a step, re-run it on a real event and compare outputs (edl.json, `18_shotlist`, a preview
  render) before and after.
- Code style: compact, numbered steps with a docstring explaining what the step does and writes.

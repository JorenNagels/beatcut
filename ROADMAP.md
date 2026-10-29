# Roadmap

Stages 1-4 are done.
- **Stage 1-2**: a reusable pipeline, the `/beatcut` skill with the setup interview, per-event config, and the
  first film (a ski trip) reproduced exactly from the new setup.
- **Stage 3: better moment finding + hand-tuning** (AI parts need `python install.py --extras`)
  | step | what |
  |---|---|
  | `19_transcribe` | Whisper (faster-whisper, large-v3 on NVIDIA, small elsewhere): word timestamps + transcripts.md |
  | `19b_sounds` | laughter / cheering / singing / shouting from an AudioSet model (PANNs Cnn14); counts as voices in the plan |
  | `20_clip`, `search` | SigLIP embeddings of the 2-second frames; text search; `--autotag` first-draft visual tags |
  | `21_scenes` | PySceneDetect shot changes inside clips; filler windows never cross one |
  | `12_music --tracker beat_this` | neural beats/downbeats (falls back to the grid tracker if the model can't load) |
  | `timeline` | filmstrip + waveform (coloured by sound events) + spoken words for one stretch of a clip |
  | `22_export` | .otio (Resolve 18.5+), .xml (Premiere / FCP7), .fcpxml (Final Cut) on the original files |
  | `23_check` | self-check of a render: black / frozen / flash frames, no-cut cuts, music gaps, loud cuts, LUFS |
- **Stage 4: shorts + subtitles**
  - Formats 9:16, 1:1, 4:5 next to 16:9 (`film.format` or `finish(fmt=)`); landscape shots get a crop that follows
    faces, then saliency + camera-compensated motion (shot option `reframe`: follow / center / fit / 0-1).
  - Several EDLs per event: `plan_<name>.py` -> `edl_<name>.json` -> `render/<name>_preview.mp4` (`--edl <name>`).
  - `templates/plan_short.py`: hook (best fall with sound) on the song's first loud section, 1-bar / 2-beat cuts,
    a sound bite, ends on a laugh; skips moments used in the film and other shorts unless `REUSE = True`.
  - Subtitles from the Whisper words, only where camera sound is on: `speech` (sentences, + .srt) and
    `styled-captions` (1-3 big words, current word highlighted, pop-in, above the TikTok buttons), via libass.

Known limits
- Auto-tags agree with hand tags ~40% of the time on the ski trip (snowy slopes read as "action"); they are a
  first draft, not a replacement for the visual pass. Falls/crashes still come from eyes, sound and the user.
- 19b_sounds hears laughter reliably indoors (charades, dinner) but hardly at all under wind: on the ski trip every
  laugh after a fall scored below 0.1. Outdoors, the voice-band detector (05_events) and 17_singing still matter.
- beat_this downloads its model from cloud.cp.jku.at; on 2026-10-29 that server's TLS certificate had expired, so
  12_music fell back to the grid tracker (it says so and keeps working).
- The subject-following crop misses fast skiers entering from the edge; check the edit sheet and set `reframe`.
- Captions have no emoji (libass draws no colour emoji); Remotion (stage 5) would add them.
- Whisper hallucinates short lines ("Ja.") on wind noise; low-confidence lines are kept in transcripts.md with
  their confidence so they can be ignored.

## Stage 5: Remotion for titles and captions (optional)
**What Remotion is:** a free (for individuals) framework where you build video graphics as React/TypeScript
components and render them to video frames. The output is the same kind of transparent title overlay as now,
but with web design tools: any Google font, smooth spring animations, shapes, masks, emoji, gradients.
- `remotion/` sub-project: `KineticTitle`, `Captions` (word-by-word captions with emoji and richer motion than
  the libass version), `LowerThird`, `EndCard`
  compositions that read their text/timing from edl.json, rendered as transparent PNG sequences (or ProRes 4444)
  and overlaid by 14_render exactly like the current Python title frames.
- The Python title (16_title.py) stays as the fallback, so Node is never required.
- Title styles to choose in the interview: slam (current), minimal, handwritten, glitch, retro VHS.
- Needs Node (already installed: v26) and ~300 MB of npm packages; ask before installing.

## Ideas parked
- Music suggestions: analyse the footage mood + length, propose songs with BPM/energy that fit (user picks).
- Auto-sync multiple cameras recording the same moment (audio cross-correlation) for multi-angle crashes.
- GoPro telemetry (HiLight tags, speed, jumps from the accelerometer) once SD-card originals are available:
  `gopro-telemetry` (npm) or a Python GPMF parser.

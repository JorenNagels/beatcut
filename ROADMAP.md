# Roadmap

Stages 1-5 are done.
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
- The built-in (libass) captions have no emoji; the Remotion captions (stage 5) do.
- Whisper hallucinates short lines ("Ja.") on wind noise; low-confidence lines are kept in transcripts.md with
  their confidence so they can be ignored.

- **Stage 6: graphics designed per film** (2026-10-30)
  - `<event>/graphics/*.tsx`: the film's own Remotion components, bundled with the built-ins (`remotion/webpack.mjs`,
    helpers from `'beatcut'` = `remotion/src/lib.ts`); a component named like a built-in replaces it, or
    `style.title_style: <Component>`.
  - Placed from the plan: shot option `gfx={...}` or `graphic(use, t, dur, ...)`; every graphic gets the music's
    beats and bars (edl.json now stores them on the timeline) so it can animate on the beat.
  - New built-ins: `Pop` (TikTok-style words popping in on the beat), `Callout` (ring + label).
  - `gfx` step: contact sheet of graphics over their shots; 14_render re-renders only shots whose command changed.
  - `style.graphics: auto` (default): Remotion when installed; an event that needs Remotion and lacks it stops
    with a message instead of silently getting the built-in title.
  - The skill designs the look per film (references/graphics.md) instead of choosing from five presets.
- **Stage 5: Remotion graphics** (optional: `python install.py --remotion`, needs Node.js 18+)
  - `remotion/`: `Title` in five styles (slam, minimal, handwritten, glitch, vhs), `Captions` (word-by-word with
    emoji and spring motion), `EndCard`, `LowerThird`; one `Overlay` composition places them all on the timeline.
  - `pipeline/graphics_lib.py` turns the EDL into that overlay (cached by content), and 14_render lays the right
    stretch of it over each shot it touches. Per shot, because ffmpeg restarts its filters on the joined film when
    the shots' colour tags change, which loses a long overlay's place.
  - The Python title (16_title.py) stays the fallback when Remotion is not installed, so Node is never required.

## Ideas parked
- Music suggestions: analyse the footage mood + length, propose songs with BPM/energy that fit (user picks).
- Auto-sync multiple cameras recording the same moment (audio cross-correlation) for multi-angle crashes.
- GoPro telemetry (HiLight tags, speed, jumps from the accelerometer) once SD-card originals are available:
  `gopro-telemetry` (npm) or a Python GPMF parser.

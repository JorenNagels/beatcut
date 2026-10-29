# Roadmap

Stages 1-2 are done: a reusable pipeline, the `/highlight-film` skill with the setup interview, per-event config,
and the first film (a ski trip) reproduced exactly from the new setup (same edit, bit-identical sound, identical frames).

## Stage 3: better moment finding + hand-tuning
| what | how | why |
|---|---|---|
| **Whisper transcripts** | `faster-whisper` (local; fast on an NVIDIA GPU, fine on CPU / Apple Silicon), word timestamps → `transcripts/<file>.json` + one packed `transcripts.md` | search for what people said, find laughs/quotes/speech boundaries for clean cuts, and the base for subtitles |
| **Laughter / sound events** | Whisper's non-speech tokens + a small audio-event model (e.g. PANNs/YAMNet) | replaces the hand-tuned voice detector; finds laughter, cheering, singing |
| **CLIP / SigLIP search** | `open_clip` embeddings of 1 frame/s → `search.py "powder spray"` | auto-tags scenic/action/faces/food, so most of `tags_source.py` gets generated instead of written by hand |
| **Shot boundaries** | PySceneDetect | cleaner in/out points inside long phone clips |
| **Beat tracking** | `beat_this` (or madmom) as an option next to 12_music | more reliable on songs with tempo changes |
| **Timeline view** | filmstrip + waveform + transcript words for a time range in one PNG (idea from browser-use/video-use) | faster, more precise looking at decision points than contact sheets |
| **Resolve export** | `opentimelineio` → `.otio`/`.fcpxml` from edl.json (same shots, source in/out points, music cues) | open the cut in DaVinci Resolve (free) and nudge clips by hand instead of describing timestamps |
| **Self-check loop** | after each render: frames ±3 around every cut + audio levels → auto-fix list (up to 3 rounds) | catches black frames, flashes, bad cuts before the user sees them |

## Stage 4: shorts (TikTok / Reels) + subtitles
- **9:16 rendering**: `film.format: "9:16"` → 1080×1920. Landscape shots are reframed with a subject-following
  crop (faces/motion from 03_analyze, smoothed), vertical phone clips fill the frame natively, letterbox off.
- **Shorts plan template** (`templates/plan_short.py`): hook in the first 1-2 s (best fall/jump with sound),
  1-beat/2-beat cuts, one sound bite, ends on a laugh; 15/30/60 s variants; several shorts from one event
  without reusing the film's exact moments (or reusing on purpose).
- **Subtitles** from the Whisper words:
  - `speech`: clean sentence subtitles (SRT + burned in) for talking parts of the long film;
  - `styled-captions`: TikTok style, 1-3 words at a time, big bold font, the current word highlighted,
    pop-in on each word, emoji optional, safe zone above the TikTok UI. Rendered as ASS subtitles through
    ffmpeg (libass) for the first version.
- Language: auto-detect (Dutch/English mixed is fine for Whisper large-v3).

## Stage 5: Remotion for titles and captions (optional)
**What Remotion is:** a free (for individuals) framework where you build video graphics as React/TypeScript
components and render them to video frames. The output is the same kind of transparent title overlay as now,
but with web design tools: any Google font, smooth spring animations, shapes, masks, emoji, gradients.
- `remotion/` sub-project: `KineticTitle`, `Captions` (word-by-word TikTok captions), `LowerThird`, `EndCard`
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

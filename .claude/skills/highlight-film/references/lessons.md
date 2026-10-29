# Lessons from earlier films

## Footage
- **iCloud Shared Album copies are 720p/30 fps ~3 Mbps re-exports**, even of GoPro files, with no GPMF telemetry
  (no HiLight tags, GPS, accelerometer, gyro). Ask for SD-card/phone originals up front. If originals turn up
  later, drop them in the source folder and re-run: dedup ranks originals first and they replace the copies.
- **WhatsApp copies** (`VIDEO-YYYY-MM-DD-HH-MM-SS.mp4`) are often trims of a longer clip, sometimes at 60 fps.
  Dedup finds the offset; `dedup.json → hints` maps them, which is how speed ramps get real slow motion.
- GoPro splits long recordings into chapters (`GX01xxxx`, `GX02xxxx`, … same xxxx); a chapter can be missing.
- Re-exported files lose their dates. Estimate days from weather/light + GoPro file order + dated phone clips,
  and write them to `DAY` in tags_source.py.
- Phone clips held sideways: the plan sets `transpose=1` on the shot. Vertical phone clips render on a blurred fill.
- Some files say landscape in metadata but display vertical (rotation flag): add them to `S.force_vertical`.

## Detection
- Audio jump detection (snow-hiss gap + landing) was unreliable, so jumps were picked by eye. Ask the user.
- The voice detector misses talk in noisy rooms (dinner, games), so evening clips are in `S.evening`
  (sound always on).
- Singing in wind-heavy GoPro audio: pitch strength works (`17_singing.py`), loudness doesn't.
- The detectors find maybe half of the funny moments. The user's memory finds the rest. Always ask.

## Edit
- Falls need 3+ bars (~5 s at 144 BPM) so the laughter afterwards is in.
- Use `take(file, a, b)` to block boring stretches the user rejected, and to save moments for the ending.
- Two songs: fade the first out over a talking clip, creep the second in 1.6 s early (squared fade), and
  bring the first song's tail back under another talking clip for the outro.
- The kinetic title takes exactly 8 beats (2 bars) with 4 background shots of 2 beats each.

## Rendering
- ffmpeg from winget (`Gyan.FFmpeg`) on Windows or Homebrew on macOS; common.py finds both even when not on PATH.
- 14_render: shots render in parallel (6 threads), are joined losslessly, then one final pass adds title,
  credits, fades and grain. A preview takes ~1.5 min, the final ~15 min (CPU x264 `slow`).
- Pass `--force` after any plan change (segments are cached by index).
- Fonts: the bundled Oswald (variable, fonts/) is the default; any .ttf works via `style.font`.

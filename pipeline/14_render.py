"""Step 14: render edl.json.   14_render preview|final [--force] [--edl <name>]

Video, per shot (exact frame count, 30 fps): framing (fill / blurred fill for vertical on landscape / face-centred
crop; on 9:16, 1:1 and 4:5 a landscape shot gets a crop that follows faces and motion: shot option reframe =
"follow" (default) | "center" | "fit" (whole frame on a blurred fill) | 0.0-1.0 (fixed horizontal position)),
slow motion (>= 50 fps sources; speed ramps = shot split into parts), muted cool grade, 2.39:1 letterbox on scenic
shots. Shots are joined losslessly; the final pass overlays the kinetic title (16_title.py frames) and credits,
fades in/out, burns in subtitles (edl "subtitles": speech | styled-captions, from 19_transcribe; see subs_lib.py)
and (final) adds grain.
Graphics: style.graphics python (default: 16_title frames, drawtext credits, libass captions) or remotion (graphics_lib:
one transparent track with title / captions / end card / lower thirds, laid over the shots it touches).
Audio (numpy): the music is a list of cues from edl.json (song part -> timeline position, fades), so the plan decides
where songs change (best under a talking clip, so the music never stops); music dips 6 dB under clips with voices
(soft 0.25 s ramps), 14 dB under sound bites; clip sound loudness-matched; peak limiter.
Look from event.yaml: style.grade (preset name or raw ffmpeg filter), style.grain, style.font (default: bundled Oswald).
Format from the EDL (film.format / finish(fmt=)): 16:9 -> 960x540 preview, 1920x1080 final; 9:16 -> 540x960, 1080x1920.
Output: render/preview.mp4 / render/final.mp4 (+ .srt when there is speech); --edl short1 -> render/short1_preview.mp4."""
import json, shutil, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from common import ROOT, SRC, FFMPEG, PIPELINE, DEFAULT_FONT, MODELS, EDL_NAME, load_json, cfg, event_path, \
    edl_file, out_name, frame_size, file_id
import subs_lib, graphics_lib

MODE = sys.argv[1] if len(sys.argv) > 1 else "preview"
FORCE = "--force" in sys.argv
E = load_json(edl_file()); FPS = E["fps"]
W, H = frame_size(E.get("format", "16:9"), MODE)
U = min(H, W * 9 / 16)                       # text/title scale: the height of a 16:9 frame this wide
CRF, PRESET = (26, "veryfast") if MODE == "preview" else (17, "slow")
NAME = out_name(MODE)
R = ROOT / "render"; SEG = R / f"seg_{NAME}"; TMP = R / "tmp"
TITLE_DIR = R / f"title_{out_name(str(W))}"
for d in (R, SEG, TMP, R / "txt", R / "fonts"): d.mkdir(parents=True, exist_ok=True)
FONT = R / "fonts" / "title.ttf"
if FORCE or not FONT.exists(): shutil.copy(event_path(cfg("style.font", DEFAULT_FONT)), FONT)
inv = {r["file"]: r for r in load_json("inventory.json")}
SR = 48000

GRADES = {
    # muted, slightly cool film look: lower saturation, blue shadows, lifted blacks (the ski film)
    "cool-muted": ("eq=contrast=1.05:saturation=0.82,"
                   "colorbalance=rs=-0.03:gs=-0.01:bs=0.04:rm=-0.02:bm=0.02:rh=0.01:bh=-0.01,"
                   "curves=all='0/0.035 1/0.965'"),
    # golden summer: warmer mids/highlights, a touch more saturation
    "warm": ("eq=contrast=1.04:saturation=1.05,"
             "colorbalance=rs=0.02:bs=-0.02:rm=0.03:bm=-0.03:rh=0.03:bh=-0.04,"
             "curves=all='0/0.02 1/0.98'"),
    # social / TikTok: contrasty and saturated
    "punchy": "eq=contrast=1.12:saturation=1.18,curves=all='0/0 0.5/0.48 1/1'",
    "natural": "null",
}
GRADE = GRADES.get(cfg("style.grade", "cool-muted"), cfg("style.grade", "cool-muted"))   # preset or raw filter
GRAIN = cfg("style.grain", True)
GFX = graphics_lib.engine()                  # python: 16_title + drawtext credits + libass; remotion: overlays
SHARP = ",unsharp=5:5:0.5" if MODE == "final" else ""
LB = round(H * 0.1278) if W > H else 0                 # 2.39:1 letterbox only on landscape films
LETTERBOX = f",drawbox=x=0:y=0:w=iw:h={LB}:color=black:t=fill,drawbox=x=0:y=ih-{LB}:w=iw:h={LB}:color=black:t=fill"
_dims = {}


def disp_dims(f):
    """displayed (rotation-applied) size of a video, from one decoded frame"""
    if f not in _dims:
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(SRC / f), "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "bmp", "-"], capture_output=True).stdout
        _dims[f] = (int.from_bytes(raw[18:22], "little"), abs(int.from_bytes(raw[22:26], "little", signed=True)))
    return _dims[f]


def face_rect(sw, sh, box, face_frac):
    x, y, w, h = box
    ch = min(sh, max(sh * 0.45, h / face_frac)); cw = min(sw, ch * W / H); ch = cw * H / W
    cx, cy = x + w / 2, y + h * 0.6
    x0 = min(max(0, cx - cw / 2), sw - cw); y0 = min(max(0, cy - ch / 2), sh - ch)
    return int(x0), int(y0), int(cw) // 2 * 2, int(ch) // 2 * 2


def photo_base(s, out):
    im = ImageOps.exif_transpose(Image.open(SRC / s["src"])).convert("RGB")
    sw, sh = im.size
    if s.get("focus"):
        x0, y0, cw, ch = face_rect(sw, sh, s["focus"], 0.42)
        im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((2 * W, 2 * H), Image.LANCZOS)
    elif not 0.845 < (sw / sh) / (W / H) < 1.6:                     # far from the frame shape: blurred fill
        bg = ImageOps.fit(im, (2 * W, 2 * H)).filter(ImageFilter.GaussianBlur(40))
        bg = Image.eval(bg, lambda v: int(v * 0.8))
        fg = im.copy(); fg.thumbnail((2 * W, 2 * H), Image.LANCZOS)
        bg.paste(fg, ((2 * W - fg.width) // 2, (2 * H - fg.height) // 2)); im = bg
    else:
        im = ImageOps.fit(im, (2 * W, 2 * H), Image.LANCZOS)
    if s.get("dim"): im = Image.eval(im, lambda v: int(v * s["dim"]))
    im.save(out, quality=95)


_tls = threading.local()                      # one face detector per render thread (OpenCV DNN is not thread-safe)


def follow_track(src, a, span, sp):
    """horizontal subject position (0-1 of the source width) over the shot: faces (YuNet) first, else where
    the motion is (pulled towards the centre), smoothed and speed-limited. [(timeline_s, x)] every 0.6 s"""
    key = TMP / f"follow_{file_id(src)}_{a:.2f}_{span:.2f}.json"
    if key.exists() and not FORCE: return json.loads(key.read_text())
    import cv2
    from scipy.ndimage import median_filter
    fw, fh = 320, 180
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0, a):.3f}", "-t", f"{span:.3f}", "-i", str(SRC / src),
                          "-vf", f"fps=5,scale={fw}:{fh}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, fh, fw, 3)
    if not hasattr(_tls, "yunet"):
        _tls.yunet = cv2.FaceDetectorYN.create(str(MODELS / "face_detection_yunet_2023mar.onnx"), "", (fw, fh), 0.7)
    def norm(c):
        c = np.clip(c - np.median(c), 0, None); return c / (c.sum() + 1e-9)
    xs, prev = [], None
    for im in fr:
        g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (9, 9), 0).astype(np.float32)
        _, faces = _tls.yunet.detect(im)
        if faces is not None and len(faces):
            wts = faces[:, 2] * faces[:, 3]
            xs.append(float(np.sum((faces[:, 0] + faces[:, 2] / 2) * wts) / wts.sum() / fw)); prev = g; continue
        # saliency (spectral residual): what stands out, e.g. a dark skier on white snow
        sm = cv2.resize(g, (64, 36)); F = np.fft.fft2(sm); L = np.log(np.abs(F) + 1e-6)
        sal = np.abs(np.fft.ifft2(np.exp(L - cv2.blur(L, (3, 3)) + 1j * np.angle(F)))) ** 2
        col = norm(cv2.resize(cv2.GaussianBlur(sal, (5, 5), 2), (fw, 36)).sum(0))
        if prev is not None:                                       # motion after cancelling the camera pan
            (dx, dy), _ = cv2.phaseCorrelate(prev, g)
            moved = np.abs(g - cv2.warpAffine(prev, np.float32([[1, 0, dx], [0, 1, dy]]), (fw, fh), borderMode=cv2.BORDER_REPLICATE))
            col = col + norm(np.pad(moved[:, 8:-8].sum(0), 8))  # border columns are warp edges
        w = col ** 2
        xs.append(0.5 + 0.8 * (float((w * np.arange(fw)).sum() / w.sum()) / fw - 0.5) if w.sum() > 0 else 0.5)
        prev = g
    x = np.array(xs, float)
    if len(x) == 0 or np.all(np.isnan(x)): x = np.full(max(1, len(x)), 0.5)
    x = np.where(np.isnan(x), np.nanmedian(x), x)
    x = uniform_filter1d(median_filter(x, 5, mode="nearest"), 5, mode="nearest")
    for i in range(1, len(x)):                                     # max 0.12 of the width per second: calm pans
        x[i] = x[i - 1] + np.clip(x[i] - x[i - 1], -0.024, 0.024)
    keys = [(round(i / 5 / sp, 3), round(float(x[i]), 3)) for i in range(0, len(x), 3)]
    keys.append((round(span / sp + 1, 3), round(float(x[-1]), 3)))
    key.write_text(json.dumps(keys)); return keys


def lerp_expr(keys):
    """piecewise-linear ffmpeg expression in t through (t, value) keys"""
    e = f"{keys[-1][1]}"
    for (t0, v0), (t1, v1) in reversed(list(zip(keys[:-1], keys[1:]))):
        e = f"if(lt(t\\,{t1})\\,{v0}+({v1 - v0:.4f})*(t-{t0})/{max(t1 - t0, 1e-3):.3f}\\,{e})"
    return e


def encode_args(n):
    return ["-frames:v", str(n), "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
            "-pix_fmt", "yuv420p", "-g", str(FPS), "-video_track_timescale", "15360"]


OV, OV_RANGES = None, []                     # remotion graphics track and the frame ranges it draws on


def with_graphics(vf, f0, n):
    """extra inputs + filter graph that lay this stretch (timeline frames f0..f0+n) of the graphics track over
    the shot. Done per shot, not on the joined film: ffmpeg restarts its filters when the shots' colour tags change,
    which loses an overlay's place. ProRes frames are all keyframes, so the seek is frame-exact."""
    if not OV or not any(a < f0 + n and f0 < b for a, b in OV_RANGES): return [], vf
    return (["-ss", f"{max(0, f0 / FPS - 0.0001):.4f}", "-i", str(OV)],
            f"[0:v]{vf}[base];[1:v]setpts=PTS-STARTPTS[g];[base][g]overlay=eof_action=pass,format=yuv420p")


def video_cmd(s, src, a, n, sp, out, f0):
    D = n / FPS
    sw, sh = disp_dims(src)
    pre = f"setpts=PTS/{sp}," if sp != 1 else ""
    if s.get("transpose"):                                          # phone held sideways
        pre += f"transpose={s['transpose']},"; sw, sh = sh, sw
    src_ar, out_ar, rf = sw / sh, W / H, s.get("reframe", "follow")
    if (sh > sw if W > H else src_ar < out_ar * 0.7):               # vertical on a landscape film: blurred fill
        geo = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,"
               f"eq=brightness=-0.08[bg];[b]scale=-2:{H}{SHARP}[fg];[bg][fg]overlay=(W-w)/2:0")
    elif W <= H and src_ar > out_ar * 1.15 and rf == "fit":         # whole landscape frame on a blurred fill
        geo = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,"
               f"eq=brightness=-0.08[bg];[b]scale={W}:-2{SHARP}[fg];[bg][fg]overlay=0:(H-h)/2")
    elif W <= H and src_ar > out_ar * 1.15 and not s.get("focus"):  # landscape on 9:16 / 1:1 / 4:5: moving crop
        if isinstance(rf, (int, float)): cx = f"{rf}"
        elif rf == "center" or s.get("transpose"): cx = "0.5"
        else: cx = lerp_expr(follow_track(src, a, D * sp, sp))
        geo = (f"crop=w=trunc(ih*{out_ar:.5f}/2)*2:h=ih:x=clip(({cx})*iw-ow/2\\,0\\,iw-ow):y=0,"
               f"scale={W}:{H}:flags=lanczos{SHARP}")
    elif s.get("focus"):
        x0, y0, cw, ch = face_rect(sw, sh, s["focus"], 0.22)
        geo = f"crop={cw}:{ch}:{x0}:{y0},scale={W}:{H}:flags=lanczos{SHARP}"
    else:
        geo = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}{SHARP}"
    if s.get("bite"):                                               # comic punch-in for sound bites
        geo += f",crop=iw/1.3:ih/1.3,scale={W}:{H}:flags=lanczos"
    dim = f",colorchannelmixer=rr={s['dim']}:gg={s['dim']}:bb={s['dim']}" if s.get("dim") else ""
    lb = LETTERBOX if s.get("letterbox") else ""
    vf = f"{pre}fps={FPS},{geo},setsar=1,{GRADE}{dim}{lb},tpad=stop_mode=clone:stop_duration=2,format=yuv420p"
    extra = []
    if s.get("title_frame0") is not None:            # burn the kinetic title into this shot (frames from 16_title.py)
        extra = ["-start_number", str(s["title_frame0"]), "-framerate", str(FPS), "-i", str(TITLE_DIR / "%04d.png")]
        vf = f"[0:v]{vf}[base];[1:v]format=rgba,setpts=PTS-STARTPTS[t];[base][t]overlay=eof_action=pass,format=yuv420p"
    else:
        extra, vf = with_graphics(vf, f0, n)
    return [FFMPEG, "-v", "error", "-y", "-ss", f"{max(0, a):.3f}", "-t", f"{D * sp + 0.4:.3f}", "-i", str(SRC / src)] + extra + \
           ["-filter_complex", vf] + encode_args(n) + [str(out)]


def render_seg(i_s):
    """returns list of rendered files for this shot (several for speed ramps)"""
    i, s = i_s
    n = s["frames"]; f0 = round(s["t0"] * FPS)
    if s["type"] == "photo":
        out = SEG / f"{i:03d}.mp4"
        if out.exists() and not FORCE: return [out]
        base = TMP / f"{NAME}_{i:03d}.jpg"; photo_base(s, base); D = n / FPS
        lb = LETTERBOX if s.get("letterbox") else ""
        vf = (f"scale=w='trunc({W}*(1.0+0.07*t/{D:.3f})/2)*2':h=-2:eval=frame:flags=bicubic,"
              f"crop={W}:{H},setsar=1,{GRADE}{lb},format=yuv420p")
        extra, g = with_graphics(vf, f0, n)
        cmd = [FFMPEG, "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{D + 0.5:.3f}", "-i", str(base)] +             extra + (["-filter_complex", g] if extra else ["-vf", vf]) + encode_args(n) + [str(out)]
        jobs = [(cmd, out)]
    else:
        parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": s.get("slowmo", 1.0)}]
        frames = [round(p["dur"] * FPS) for p in parts]; frames[-1] = n - sum(frames[:-1])
        jobs = []
        for k, (p, nf) in enumerate(zip(parts, frames)):
            out = SEG / (f"{i:03d}.mp4" if len(parts) == 1 else f"{i:03d}_{k}.mp4")
            jobs.append((video_cmd(s, p["src"], p["in"], nf, p.get("slowmo", 1.0), out, f0 + sum(frames[:k])), out))
    for cmd, out in jobs:
        if out.exists() and not FORCE: continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: raise RuntimeError(f"seg {i} {s['src']}: {r.stderr[-800:]}")
    return [o for _, o in jobs]


# ---------------- audio ----------------
def load_audio(path, start=None, dur=None):
    cmd = [FFMPEG, "-v", "error"]
    if start is not None: cmd += ["-ss", f"{max(0, start):.3f}"]
    if dur is not None: cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", str(path), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)
    return x.reshape(-1, 2).copy()


def place_audio(buf, x, t0, fade_in=0.0, fade_out=0.0, gain=1.0):
    i0 = int(round(t0 * SR)); x = x[: max(0, len(buf) - i0)] * gain
    if len(x) == 0: return
    if fade_in > 0:
        k = min(len(x), int(fade_in * SR)); x[:k] *= np.linspace(0, 1, k)[:, None]
    if fade_out > 0:
        k = min(len(x), int(fade_out * SR)); x[-k:] *= np.linspace(1, 0, k)[:, None]
    buf[i0:i0 + len(x)] += x


def ramp_env(n, intervals, ramp=0.25):
    """gain envelope: 1 outside, (1-depth) inside each (a, b, depth) interval, linear ramps"""
    t = np.arange(n) / SR; duck = np.zeros(n, np.float32)
    for a, b, depth in intervals:
        lo, hi = int(max(0, (a - ramp) * SR)), int(min(n, (b + ramp) * SR))
        tt = t[lo:hi]
        duck[lo:hi] = np.maximum(duck[lo:hi], depth * np.clip(np.minimum((tt - (a - ramp)) / ramp, ((b + ramp) - tt) / ramp), 0, 1))
    return 1 - duck


def audio(segs, out):
    m = E["music"]; D = E["duration"]; n = int(D * SR) + SR
    mus = np.zeros((n, 2), np.float32)
    songs = {role: load_audio(event_path(f)) for role, f in m["tracks"].items()}
    # music cues: song seconds [from, to) placed at timeline second `at`; a negative `from` starts with silence;
    # fade_curve "sq" = slow creep-in (a song sneaking in under talking)
    for c in m["cues"]:
        song = songs[c["track"]]
        x = song[int(c["from"] * SR): int(c["to"] * SR)].copy() if c["from"] >= 0 else \
            np.vstack([np.zeros((int(-c["from"] * SR), 2), np.float32), song[: int(c["to"] * SR)]])
        fi = c.get("fade_in", 0.0)
        if c.get("fade_curve") == "sq" and fi > 0:
            k = int(fi * SR); x[:k] *= np.linspace(0.0, 1.0, k)[:, None] ** 2; fi = 0.0
        place_audio(mus, x, c["at"], fade_in=fi, fade_out=c.get("fade_out", 0.0))
    # clip sound: loudness-matched to -21 dBFS RMS (max +12 dB / -12 dB), only shots flagged by the voice check
    cam = np.zeros_like(mus); ducks = []
    for s in segs:
        if s["type"] != "video" or not s.get("cam_audio") or not inv[s["src"]].get("has_audio"): continue
        parts = s.get("parts") or [{"src": s["src"], "in": s["in"], "dur": s["dur"], "slowmo": 1.0}]
        t = s["t0"]
        for p in parts:
            if p.get("slowmo", 1) == 1:                       # slow-motion parts stay music-only
                x = load_audio(SRC / p["src"], p["in"], p["dur"])
                if len(x):
                    rms = np.sqrt(np.mean(x ** 2)) + 1e-6
                    g = np.clip(10 ** (-21 / 20) / rms, 0.25, 4.0) * s["cam_audio"]
                    place_audio(cam, x, t, 0.06, 0.12, g)
                    ducks.append((t, t + p["dur"], 0.8 if s.get("bite") else 0.5))
            t += p["dur"]
    mus *= 0.8 * ramp_env(n, ducks)[:, None]               # music never stops: -6 dB under voices, -14 dB under bites
    mix = mus + cam
    # peak limiter: 5 ms look-around peak envelope, 150 ms release
    pk = maximum_filter1d(np.abs(mix).max(1), int(0.005 * SR))
    env = np.maximum(pk, 1e-6); g = np.minimum(1, 0.94 / env)
    g = -maximum_filter1d(-g, int(0.01 * SR)); g = uniform_filter1d(g, int(0.15 * SR) | 1)
    g = np.minimum(g, np.minimum(1, 0.98 / env)) * 0.84          # -1.5 dB headroom so AAC peaks stay below 0 dBFS
    mix = (mix * g[:, None])[: int(D * SR)]
    p = subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s16le",
                        str(out)], input=mix.astype(np.float32).tobytes(), capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode()[-800:])


# ---------------- overlays ----------------
def txt(name, text):
    p = R / "txt" / f"{name}.txt"; p.write_text(text, encoding="utf-8"); return f"render/txt/{name}.txt"


def spaced(s):
    return " ".join(s.upper()).replace("   ", "     ")


def fade(a, b, fi=0.35, fo=0.35):
    return f"alpha='if(lt(t,{a + fi:.2f}),max(0,(t-{a:.2f})/{fi}),if(gt(t,{b - fo:.2f}),max(0,({b:.2f}-t)/{fo}),1))'"


def credits(segs):
    f = "fontfile=render/fonts/title.ttf"; sh = "shadowcolor=black@0.55:shadowx=2:shadowy=2"
    out = []
    for s in segs:
        if not s.get("credits"): continue
        a = s["t0"]
        # first line = film title (big, letter-spaced), then the small lines from event.yaml credits
        lines = [(spaced(E["title"]), .046, .42)] + [(t, .026, .54 + .05 * k) for k, t in enumerate(E.get("credits", []))]
        for k, (t, fs, y) in enumerate(lines):
            out.append(f"drawtext={f}:textfile={txt(f'{NAME}_cred{k}', t)}:fontsize={int(U * fs)}:fontcolor=white:"
                       f"x=(w-text_w)/2:y=h*{y}:{sh}:enable='gte(t,{a + .6 + .25 * k:.2f})':{fade(a + .6 + .25 * k, E['duration'] + 9, .6, .1)}")
    return out


def main():
    segs = E["segments"]
    ta = E["title_anim"]
    nt = sum(s["frames"] for s in segs if s["section"] == "title")
    if nt and GFX == "python" and (FORCE or not (TITLE_DIR / f"{nt - 1:04d}.png").exists()):
        subprocess.run([sys.executable, str(PIPELINE / "16_title.py"), str(W), str(H), str(nt), str(ta["bpm"])]
                       + (["--edl", EDL_NAME] if EDL_NAME else []), check=True)
    f0 = 0
    for s in segs:
        if s["section"] == "title" and GFX == "python": s["title_frame0"] = f0; f0 += s["frames"]
    global OV, OV_RANGES
    if GFX == "remotion":
        its = graphics_lib.items(E, W, H, FPS)
        OV = graphics_lib.render(its, FONT, W, H, FPS, sum(s["frames"] for s in segs))
        OV_RANGES = [(f, f + p["frames"]) for f, _, p in its]
    with ThreadPoolExecutor(6) as ex:
        files = [f for fs in ex.map(render_seg, enumerate(segs)) for f in fs]
    lst = TMP / f"concat_{NAME}.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files), encoding="utf-8")
    joined = TMP / f"joined_{NAME}.mp4"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)], check=True)
    wav = TMP / f"audio_{NAME}.wav"; audio(segs, wav)
    D = E["duration"]; fin, fout = E.get("fades", [1.0, 3.0])
    subs = []
    if E.get("subtitles", "none") != "none":
        ass = TMP / f"subs_{NAME}.ass"
        n = subs_lib.build(E, E["subtitles"], W, H, FONT, ass, R / f"{NAME}.srt")
        print(f"subtitles ({E['subtitles']}): {n} words" + ("" if n else " - none found; run 19_transcribe first?"))
        if n and not (GFX == "remotion" and E["subtitles"] == "styled-captions"):    # remotion draws those
            subs = [f"ass={ass.relative_to(ROOT).as_posix()}:fontsdir=render/fonts"]
    pre = (credits(segs) if GFX == "python" else []) + subs
    post = ([f"fade=t=in:st=0:d={fi}" for fi in [fin] if fi] + [f"fade=t=out:st={D - fo:.2f}:d={fo}" for fo in [fout] if fo]
            + (["noise=c0s=7:c0f=t+u:c1s=3:c2s=3"] if MODE == "final" and GRAIN else []))
    fc = f"[0:v]{','.join(pre + post) or 'null'},format=yuv420p[v]"
    script = TMP / f"video_fc_{NAME}.txt"; script.write_text(fc, encoding="utf-8")
    out = R / f"{NAME}.mp4"
    cmd = [FFMPEG, "-v", "error", "-y", "-i", str(joined.relative_to(ROOT)), "-i", str(wav.relative_to(ROOT)),
           "-/filter_complex", str(script.relative_to(ROOT)), "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", PRESET,
           "-crf", str(CRF), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", f"{D:.3f}",
           str(out.relative_to(ROOT))]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr[-1500:])
    print("written", out)


if __name__ == "__main__":
    main()

"""Subtitles for a rendered EDL from the Whisper words (19_transcribe), used by 14_render.

Only speech you can hear gets subtitles: shots with camera sound on (cam_audio > 0), normal-speed parts; a shot can
force them with subs=True or switch them off with subs=False. Source word times are mapped onto the timeline.
  speech           clean sentence subtitles, max 2 lines of ~42 characters, bottom centre (+ .srt file)
  styled-captions  TikTok style: 1-3 words at a time, big bold uppercase, the current word highlighted, pop-in on
                   every new group, placed above the TikTok/Reels buttons on 9:16
Written as ASS (libass via the ffmpeg `ass` filter, same font as the title). Emoji are not drawn (libass has no
colour emoji)."""
import re
from PIL import ImageFont
from common import load_json, file_id

HIGHLIGHT = "&H0000E6FF&"            # ASS colours are &HAABBGGRR: this is yellow


def timeline_words(E):
    """[{w, s, e}] in timeline seconds for every audible word of the film"""
    out = []
    for seg in E["segments"]:
        if seg["type"] != "video" or seg.get("subs") is False: continue
        if not seg.get("cam_audio") and not seg.get("subs"): continue
        t = seg["t0"]
        for p in seg.get("parts") or [{"src": seg["src"], "in": seg["in"], "dur": seg["dur"], "slowmo": seg.get("slowmo", 1.0)}]:
            T = load_json(f"transcripts/{file_id(p['src'])}.json") if p.get("slowmo", 1) == 1 else None
            for s in (T or {}).get("segments", []):
                for w in s["words"]:
                    mid = (w["s"] + w["e"]) / 2
                    if p["in"] <= mid < p["in"] + p["dur"]:
                        a = t + max(0.0, w["s"] - p["in"]); b = t + min(p["dur"], w["e"] - p["in"])
                        out.append({"w": w["w"], "s": round(a, 3), "e": round(max(b, a + 0.08), 3), "seg_end": t + p["dur"]})
            t += p["dur"]                                       # part durations are timeline seconds
    return sorted(out, key=lambda w: w["s"])


def cues(words, max_chars=42, max_lines=2, gap=0.6):
    """sentence-like cues [(start, end, text)] for speech subtitles / srt"""
    out, cur = [], []
    def flush():
        if not cur: return
        text = " ".join(w["w"] for w in cur)
        if len(text) > max_chars:                                  # break into two balanced lines
            cut = min(range(1, len(cur)), key=lambda k: abs(len(" ".join(w["w"] for w in cur[:k])) - len(text) / 2))
            text = " ".join(w["w"] for w in cur[:cut]) + "\n" + " ".join(w["w"] for w in cur[cut:])
        out.append([cur[0]["s"], cur[-1]["e"], text]); cur.clear()
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > gap or w["s"] >= cur[-1]["seg_end"] or
                    len(" ".join(x["w"] for x in cur + [w])) > max_chars * max_lines or re.search(r"[.!?]$", cur[-1]["w"])):
            flush()
        cur.append(w)
    flush()
    for k, c in enumerate(out):                                     # stay up >= 1 s when there is room, max 6 s
        nxt = out[k + 1][0] if k + 1 < len(out) else c[1] + 1.0
        c[1] = min(max(c[1], min(c[0] + 1.0, nxt - 0.05)), c[0] + 6.0)
    return out


def groups(words, n=3, max_chars=14, gap=0.35):
    """1-3 word groups for styled captions"""
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= n or w["s"] - cur[-1]["e"] > gap or w["s"] >= cur[-1]["seg_end"] or
                    len(" ".join(x["w"] for x in cur + [w])) > max_chars or re.search(r"[.,!?]$", cur[-1]["w"])):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out


def ts(t):
    t = max(0.0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def clean(w, upper):
    w = w.replace("{", "").replace("}", "").replace("\\", "")
    if upper: w = re.sub(r"[.,;:]+$", "", w).upper()
    return w


def header(W, H, font, size, outline, margin_v, bold):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,{bold},0,0,0,100,100,0,0,1,{outline},{outline * 0.6:.1f},2,{int(W * 0.06)},{int(W * 0.06)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build(E, mode, W, H, font_path, ass_path, srt_path):
    """write the .ass (burned in by 14_render) and an .srt next to the film; returns the number of words"""
    words = [w for w in timeline_words(E) if w["s"] < E["duration"]]
    font = ImageFont.truetype(str(font_path), 20).getname()[0]
    U = min(W, H)                                                # text scales with the short side of the frame
    lines = []
    if mode == "styled-captions":
        margin = int(H * (0.30 if H > W else 0.12))              # 9:16: above the like/comment buttons and caption
        hdr = header(W, H, font, int(U * (0.1 if H > W else 0.085)), round(U * 0.008, 1), margin, -1)
        gs = groups(words)
        for k, g in enumerate(gs):
            nxt = gs[k + 1][0]["s"] if k + 1 < len(gs) else g[-1]["e"] + 0.5
            steps = []                                          # (start, end, highlighted word)
            for i, w in enumerate(g):
                a = g[0]["s"] if i == 0 else w["s"]
                b = g[i + 1]["s"] if i + 1 < len(g) else min(max(w["e"] + 0.35, w["s"] + 0.3), nxt)
                if steps and a - steps[-1][0] < 0.12:           # words Whisper squeezed together: no flicker
                    steps[-1][1] = b; continue
                steps.append([a, b, i])
            for a, b, i in steps:
                if b <= a: continue
                pop = r"{\fscx72\fscy72\t(0,90,\fscx100\fscy100)}" if i == 0 else ""
                txt = " ".join((r"{\c" + HIGHLIGHT + r"}" + clean(x["w"], True) + r"{\c&H00FFFFFF&}") if j == i
                               else clean(x["w"], True) for j, x in enumerate(g))
                lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{pop}{txt}")
    else:
        hdr = header(W, H, font, int(U * 0.042), round(U * 0.0025, 1), int(H * (0.18 if H > W else 0.06)), 0)
        for a, b, text in cues(words):
            lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{clean(text, False).replace(chr(10), r'\N')}")
    ass_path.write_text(hdr + "\n".join(lines) + "\n", encoding="utf-8")
    srt = []
    for k, (a, b, text) in enumerate(cues(words), 1):
        st = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"
        srt.append(f"{k}\n{st(a)} --> {st(b)}\n{text}\n")
    srt_path.write_text("\n".join(srt), encoding="utf-8")
    return len(words)

"""Step 19: speech transcripts with word timestamps (faster-whisper, local).   19_transcribe [model] [file ...]

Every kept video with sound (or only the files given) -> transcripts/<id>.json:
  {"file", "language", "segments": [{"start", "end", "text", "words": [{"w", "s", "e", "p"}]}]}
plus transcripts.md: all speech of the event in one text file ("file  m:ss  text"), to search for quotes, laughs and
sentence boundaries. These words also drive the subtitles in 14_render.
Model: large-v3 on an NVIDIA GPU, small elsewhere (override: argument or event.yaml transcribe.model).
Language: auto-detected per file (event.yaml transcribe.language to force one, e.g. nl). Voice activity detection
skips wind and silence, so long GoPro runs are quick. Cached: only new files are transcribed."""
import subprocess, sys, time
import numpy as np
from common import SRC, ROOT, FFMPEG, cfg, save_json, load_json, need, device, file_id, kept_videos

TR = ROOT / "transcripts"; TR.mkdir(exist_ok=True)


def model():
    fw = need("faster_whisper", "Transcription")
    dev = device()
    if dev == "cuda":
        import torch                                    # loads the cuDNN/cuBLAS DLLs that CTranslate2 needs
    name = next((a for a in sys.argv[1:] if not a.startswith("-") and "." not in a), None) or \
        cfg("transcribe.model") or ("large-v3" if dev == "cuda" else "small")
    print(f"whisper {name} on {dev} (first run downloads the model)")
    return fw.WhisperModel(name, device="cuda" if dev == "cuda" else "cpu",
                           compute_type="float16" if dev == "cuda" else "int8")


def audio(f):
    """16 kHz mono float32, decoded by ffmpeg like every other step"""
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(SRC / f), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    files, inv = kept_videos()
    only = [a for a in sys.argv[1:] if "." in a]
    files = [f for f in (only or files) if inv[f].get("has_audio")]
    todo = [f for f in files if not (TR / f"{file_id(f)}.json").exists()]
    print(f"{len(files)} files with sound, {len(todo)} to transcribe")
    if todo:
        m = model(); lang = cfg("transcribe.language")
        for k, f in enumerate(todo, 1):
            t0 = time.time()
            segs, info = m.transcribe(audio(f), language=lang, word_timestamps=True, vad_filter=True,
                                      vad_parameters={"min_silence_duration_ms": 400}, beam_size=5,
                                      condition_on_previous_text=False)   # less hallucination on noisy clips
            out = []
            for s in segs:
                words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)}
                         for w in (s.words or []) if w.word.strip()]
                # drop typical hallucinations on wind/silence: very low confidence, or no real words
                if not words or (s.no_speech_prob > 0.6 and s.avg_logprob < -0.8): continue
                out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(), "words": words,
                            "conf": round(sum(w["p"] for w in words) / len(words), 2)})
            save_json(f"transcripts/{file_id(f)}.json", {"file": f, "language": info.language, "segments": out})
            print(f"[{k}/{len(todo)}] {f}: {info.language}, {len(out)} lines ({time.time() - t0:.0f}s)", flush=True)
    # one packed text file for the whole event
    lines = ["# What people say (19_transcribe)", "file | time | conf | text", ""]
    for f in sorted(files, key=lambda f: inv[f].get("shot_time") or f):
        T = load_json(f"transcripts/{file_id(f)}.json")
        if not T or not T["segments"]: continue
        lines.append(f"## {f}  ({T['language']})")
        lines += [f"{mmss(s['start'])}-{mmss(s['end'])}  {s['conf']:.2f}  {s['text']}" for s in T["segments"]]
        lines.append("")
    (ROOT / "transcripts.md").write_text("\n".join(lines), encoding="utf-8")
    print("transcripts.md written")


if __name__ == "__main__":
    main()

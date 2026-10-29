"""Step 21: shot changes inside each kept video (PySceneDetect, adaptive content detector).   21_scenes [workers]

Phone clips and edited/exported videos often hold several shots: a quick pan to something else, a pause/resume,
a WhatsApp compilation. edl_lib never lets a filler window cross one of these cuts, so shots start and end clean.
Fast camera moves (GoPro on a run) are mostly not cuts; the adaptive detector compares each frame with its
neighbours' average, which keeps those out. Output: scenes.json {file: [cut seconds]} (cached per file)."""
import sys
from concurrent.futures import ProcessPoolExecutor
from common import SRC, load_json, save_json, kept_videos, need


def cuts(f):
    sd = need("scenedetect", "Shot detection")
    video = sd.open_video(str(SRC / f))
    sm = sd.SceneManager(); sm.auto_downscale = True
    sm.add_detector(sd.AdaptiveDetector(adaptive_threshold=3.5, min_scene_len=15))
    sm.detect_scenes(video)
    return f, [round(a.get_seconds(), 2) for a, _ in sm.get_scene_list()[1:]]


def main():
    files, _ = kept_videos()
    out = load_json("scenes.json", {})
    todo = [f for f in files if f not in out]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as ex:
        for k, (f, c) in enumerate(ex.map(cuts, todo), 1):
            out[f] = c
            print(f"[{k}/{len(todo)}] {f}: {len(c)} cuts", flush=True)
            if k % 10 == 0: save_json("scenes.json", out)
    save_json("scenes.json", out)
    print(f"{sum(len(v) for v in out.values())} cuts in {sum(1 for v in out.values() if v)} of {len(out)} files -> scenes.json")


if __name__ == "__main__":
    main()

"""Step 20: image embeddings of every kept video (one per 2 s, the frames 03_analyze saved) for text search and
automatic visual tags.   20_clip [--autotag]

  embeddings  cache/clip/<model>/<id>.npz  (t, emb); search them with  search.py "powder spray"
  --autotag   tags_auto.json in the tags.json shape: runs of frames whose best category (scenic / action / faces /
              lifestyle / boring) is clear, rated 1-5 by how clearly they match and how sharp/steady they are.
              edl_lib uses it when there is no hand-made tags.json; it is also a quick first draft for the visual
              pass (falls/crashes still need eyes or the user's memory: a picture can't tell a fall from a sit-down).
Prompts per category can be changed in event.yaml clip.prompts: {scenic: [...], ...}."""
import sys
import numpy as np
from common import CACHE, cfg, load_json, save_json, file_id, kept_videos
import clip_lib

PROMPTS = {
    "scenic": ["a wide landscape view of mountains", "a scenic panorama of nature", "a sunset over the sea",
               "a beautiful view from a high place", "clouds over a valley", "an old town street with beautiful buildings"],
    "action": ["a person skiing fast down a slope", "someone jumping in the air", "point of view footage of a sport",
               "a person surfing a wave", "people riding bikes", "a person snowboarding", "people swimming and diving"],
    "faces": ["a close-up selfie of smiling friends", "a group of friends posing for a photo", "a person laughing at the camera",
              "a portrait of a person"],
    "lifestyle": ["friends having dinner at a table", "people drinking at a bar", "people playing a game indoors", "a party at night",
                  "people walking through a town", "people travelling in a car", "people sitting on a chairlift", "people on a terrace"],
    "boring": ["a blurry image", "a very dark image", "the inside of a pocket", "a close-up of the ground",
               "an empty white screen", "a floor or a wall"],
}


def embed():
    files, inv = kept_videos()
    for k, f in enumerate(files, 1):
        out = clip_lib.CLIP / f"{file_id(f)}.npz"
        if out.exists(): continue
        frames = sorted((CACHE / "frames" / load_json("signals_index.json")[f]).glob("*.jpg"))
        if not frames: continue
        e = clip_lib.embed_images(frames)
        np.savez_compressed(out, t=np.array([int(p.stem) for p in frames], np.float32), emb=e.astype(np.float16))
        print(f"[{k}/{len(files)}] {f}: {len(frames)} frames", flush=True)


def autotag():
    prompts = {**PROMPTS, **(cfg("clip.prompts") or {})}
    cats = list(prompts)
    T = {c: clip_lib.embed_text(p) for c, p in prompts.items()}
    idx = load_json("signals_index.json"); out = []
    for f, (t, e) in clip_lib.index().items():
        S = np.stack([(e @ T[c].T).max(1) for c in cats], 1)              # frame x category: best prompt
        Z = (S - S.mean(0)) / (S.std(0) + 1e-6)                            # per-category z over this file
        Z = (Z + (S - S.mean()) / (S.std() + 1e-6)) / 2                    # mixed with the absolute similarity
        best = Z.argmax(1); margin = np.sort(Z, 1)[:, -1] - np.sort(Z, 1)[:, -2]
        F = load_json(f"features/{idx[f]}.json") or {}
        i = 0
        while i < len(best):
            j = i
            while j + 1 < len(best) and best[j + 1] == best[i]: j += 1
            c = cats[best[i]]; a, b = float(t[i]), float(t[j]) + 2
            if b - a >= 4 and c != "boring" or b - a >= 2 and c == "boring":
                sec = slice(int(a), int(b))
                sharp = float(np.mean(F.get("sharp", [100])[sec] or [100])); bad = float(np.mean(F.get("bad", [0])[sec] or [0]))
                q = float(np.mean(margin[i:j + 1])) + 0.3 * float(np.mean(Z[i:j + 1, best[i]])) + 0.3 * min(1, sharp / 150) - bad
                out.append({"file": f, "start": a, "end": b, "cat": c, "q": q, "note": f"auto: {c} ({q:.2f})", "people": []})
            i = j + 1
    qs = np.array([x["q"] for x in out if x["cat"] != "boring"])
    for x in out:
        x["rating"] = 1 if x["cat"] == "boring" else int(1 + np.searchsorted(np.quantile(qs, [0.2, 0.45, 0.7, 0.9]), x.pop("q")))
        x.pop("q", None)
    est = (load_json("tags.json") or {}).get("day_estimates", {})
    save_json("tags_auto.json", {"tags": out, "day_estimates": est, "photos": {}, "source": "20_clip --autotag"})
    from collections import Counter
    print("tags_auto.json:", dict(Counter(x["cat"] for x in out)), "| ratings", dict(sorted(Counter(x["rating"] for x in out).items())))


if __name__ == "__main__":
    embed()
    if "--autotag" in sys.argv: autotag()

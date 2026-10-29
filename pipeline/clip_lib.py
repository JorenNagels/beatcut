"""Image/text embeddings (open_clip SigLIP) for 20_clip and search.py. Model from event.yaml clip.model
(default ViT-B-16-SigLIP / webli, ~800 MB on first use). Frames are the 2-second samples 03_analyze saved."""
import numpy as np
from common import cfg, need, device, CACHE

MODEL = cfg("clip.model", "ViT-B-16-SigLIP:webli")
CLIP = CACHE / "clip" / MODEL.replace(":", "_").replace("/", "_"); CLIP.mkdir(parents=True, exist_ok=True)
_m = None


def load():
    global _m
    if _m is None:
        oc = need("open_clip", "Image search")
        import torch
        name, pre = MODEL.split(":")
        model, _, prep = oc.create_model_and_transforms(name, pretrained=pre, device=device())
        _m = (model.eval(), prep, oc.get_tokenizer(name), torch)
    return _m


def embed_images(paths, batch=64):
    from PIL import Image
    model, prep, _, torch = load()
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            x = torch.stack([prep(Image.open(p).convert("RGB")) for p in paths[i:i + batch]]).to(device())
            e = model.encode_image(x).float(); out.append((e / e.norm(dim=-1, keepdim=True)).cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, 768), np.float32)


def embed_text(texts):
    model, _, tok, torch = load()
    with torch.no_grad():
        e = model.encode_text(tok(texts).to(device())).float()
    return (e / e.norm(dim=-1, keepdim=True)).cpu().numpy()


def index():
    """{file: (times, embeddings)} for every embedded video"""
    from common import load_json, file_id
    out = {}
    for f in load_json("signals_index.json"):
        p = CLIP / f"{file_id(f)}.npz"
        if p.exists():
            d = np.load(p); out[f] = (d["t"], d["emb"].astype(np.float32))
    return out

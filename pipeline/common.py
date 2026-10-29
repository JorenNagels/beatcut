"""Shared paths and helpers for the beatcut pipeline.

Every step works on one *event* (a trip, wedding, weekend ...). The event folder holds event.yaml plus the
hand-made decisions (tags.json, plan.py, project.md, people_names.json). event.yaml points to:
  source: the footage folder (read-only: never written to)
  work:   where everything generated goes (cache, features, sheets, renders)
The event folder comes from the BEATCUT_EVENT environment variable (set by beatcut.py)."""
import json, os, subprocess, shutil, sys
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[1]
PIPELINE = REPO / "pipeline"
MODELS = REPO / "models"
DEFAULT_FONT = REPO / "fonts" / "Oswald.ttf"         # bundled (SIL OFL), same look on every computer

try:                                                  # iPhone originals: .HEIC photos
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

if not os.environ.get("BEATCUT_EVENT"):
    raise SystemExit("BEATCUT_EVENT is not set - run steps through beatcut.py:  python beatcut.py <event-folder> <step> [args]")
EVENT_DIR = Path(os.environ["BEATCUT_EVENT"]).resolve()
EVENT = yaml.safe_load((EVENT_DIR / "event.yaml").read_text(encoding="utf-8")) or {}


def event_path(p):
    """a path from event.yaml: absolute, or relative to the event folder"""
    p = Path(p)
    return p if p.is_absolute() else (EVENT_DIR / p).resolve()


SRC = event_path(EVENT.get("source", "media-source"))      # originals: never written to
ROOT = event_path(EVENT.get("work", "work"))                # generated files
ROOT.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

# files in the source folder that are not footage (e.g. a style-reference film)
EXCLUDE_NAMES = set(EVENT.get("exclude", []))

VIDEO_EXT = {".mp4", ".mov"}
PHOTO_EXT = {".jpg", ".jpeg", ".heic", ".png"}

# hand-made decision files live in the event folder; everything else in the work folder
EVENT_FILES = {"tags.json", "people_names.json", "names.json"}


def cfg(dotted, default=None):
    """event.yaml lookup: cfg('style.grade', 'cool')"""
    v = EVENT
    for k in dotted.split("."):
        if not isinstance(v, dict) or k not in v: return default
        v = v[k]
    return v


def _find(tool):
    """ffmpeg/ffprobe: PATH first, then the usual install places (winget on Windows, Homebrew on macOS)"""
    p = shutil.which(tool)
    if p:
        return p
    if os.name == "nt":
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
        for c in winget.glob(f"Gyan.FFmpeg*/*/bin/{tool}.exe"):
            return str(c)
    for d in ("/opt/homebrew/bin", "/usr/local/bin"):
        if Path(d, tool).exists():
            return str(Path(d, tool))
    raise SystemExit(f"{tool} not found - install ffmpeg (Windows: winget install Gyan.FFmpeg, macOS: brew install ffmpeg)")


FFMPEG = _find("ffmpeg")
FFPROBE = _find("ffprobe")


def ffprobe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format",
                          "-show_streams", str(path)], capture_output=True, text=True, encoding="utf-8")
    return json.loads(out.stdout or "{}")


def _loc(name):
    return EVENT_DIR / name if name in EVENT_FILES else ROOT / name


def load_json(name, default=None):
    p = _loc(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(name, obj):
    _loc(name).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


def base(f):
    """file name without folders: source files are identified by their path inside the source folder
    ("cam2/GX010001.MP4"), but camera naming patterns (GX…, IMG_…, VIDEO-…) live in the base name"""
    return f.rsplit("/", 1)[-1]


def file_id(name):
    """Stable short id for a source file name (used for cache file names)."""
    import hashlib
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


# ---------------- several films per event (one long film + shorts) ----------------
# plan.py -> edl.json -> render/preview.mp4;  plan_<name>.py -> edl_<name>.json -> render/<name>_preview.mp4.
# Steps that read an EDL take  --edl <name>  (13_edl sets it from the plan file name).
EDL_NAME = sys.argv[sys.argv.index("--edl") + 1] if "--edl" in sys.argv[:-1] else ""


def edl_file():
    return f"edl_{EDL_NAME}.json" if EDL_NAME else "edl.json"


def out_name(stem):
    """render/shotlist/sheet names per EDL: 'preview' -> 'short1_preview'"""
    return f"{EDL_NAME}_{stem}" if EDL_NAME else stem


FORMATS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:5": (4, 5)}


def frame_size(fmt, mode):
    """output size for a format: the long side is 1920 (final) or 960 (preview)"""
    a, b = FORMATS.get(fmt, (16, 9))
    L = 1920 if mode == "final" else 960
    w, h = (L, L * b // a) if a >= b else (L * a // b, L)
    return w // 2 * 2, h // 2 * 2


def need(module, what):
    """import an optional AI package or explain how to get it"""
    import importlib
    try:
        return importlib.import_module(module)
    except ImportError:
        raise SystemExit(f"{what} needs the AI extras ({module} is not installed). Run:  python install.py --extras")


def device():
    """'cuda' on an NVIDIA GPU, 'mps' on Apple Silicon, else 'cpu' (torch is optional)"""
    try:
        import torch
        if torch.cuda.is_available(): return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available(): return "mps"
    except ImportError:
        pass
    return "cpu"


def kept_videos():
    """the analysed video files (duplicates skipped), longest first"""
    inv = {r["file"]: r for r in load_json("inventory.json")}
    return sorted(load_json("signals_index.json"), key=lambda f: -inv[f]["duration"]), inv

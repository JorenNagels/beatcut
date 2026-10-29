"""Shared paths and helpers for the highlight-film pipeline.

Every step works on one *event* (a trip, wedding, weekend ...). The event folder holds event.yaml plus the
hand-made decisions (tags.json, plan.py, project.md, people_names.json). event.yaml points to:
  source: the footage folder (read-only: never written to)
  work:   where everything generated goes (cache, features, sheets, renders)
The event folder comes from the HF_EVENT environment variable (set by hf.py)."""
import json, os, subprocess, shutil
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

if not os.environ.get("HF_EVENT"):
    raise SystemExit("HF_EVENT is not set - run steps through hf.py:  python hf.py <event-folder> <step> [args]")
EVENT_DIR = Path(os.environ["HF_EVENT"]).resolve()
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

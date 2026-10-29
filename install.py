"""One-time setup for beatcut. Works on Windows and macOS (and Linux).

    python install.py          (Windows)
    python3 install.py         (macOS / Linux)
    --yes        answer yes to every question (ffmpeg and the AI extras)
    --extras     install the AI extras without asking;  --no-extras  skip them

What it does:
  1. creates .venv and installs the Python packages (requirements.txt)
  2. downloads the two face models (~40 MB) into models/
  3. checks for ffmpeg and offers to install it (winget on Windows, Homebrew on macOS)
  4. offers the optional AI extras (~3-5 GB, requirements-ai.txt): Whisper transcripts and subtitles, laughter
     detection, image search / auto-tags, a neural beat tracker. PyTorch comes in the right build for the machine
     (CUDA on an NVIDIA GPU, the standard build on macOS and CPU-only PCs). Models download on first use.
  5. links the Claude Code skill into ~/.claude/skills/beatcut, so /beatcut works in any folder
Safe to run again, e.g. after moving the repo or pulling updates."""
import os, shutil, subprocess, sys, urllib.request, venv
from pathlib import Path

REPO = Path(__file__).resolve().parent
VENV = REPO / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SKILL = REPO / ".claude" / "skills" / "beatcut"
LINK = Path.home() / ".claude" / "skills" / "beatcut"
MODELS = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
YES = "--yes" in sys.argv
EXTRAS = True if "--extras" in sys.argv or YES else False if "--no-extras" in sys.argv else None


def step(msg):
    print(f"\n== {msg}")


def ask(q):
    if YES: return True
    try: return input(f"{q} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError: return False


def python_env():
    step("Python packages")
    if sys.version_info < (3, 10):
        sys.exit(f"Python 3.10 or newer is needed (this is {sys.version.split()[0]}).")
    if not PY.exists():
        print("creating .venv ...")
        venv.create(VENV, with_pip=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(REPO / "requirements.txt")], check=True)
    print("ok")


def models():
    step("Face models")
    (REPO / "models").mkdir(exist_ok=True)
    for name, url in MODELS.items():
        dst = REPO / "models" / name
        if dst.exists(): print(f"{name}: already there"); continue
        print(f"downloading {name} ...")
        tmp = dst.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp); tmp.replace(dst)
    print("ok")


def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p: return p
    if os.name == "nt":
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
        return next((str(c) for c in winget.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe")), None)
    return next((f"{d}/ffmpeg" for d in ("/opt/homebrew/bin", "/usr/local/bin") if Path(d, "ffmpeg").exists()), None)


def ffmpeg():
    step("ffmpeg")
    p = find_ffmpeg()
    if p: print(f"found: {p}"); return
    if os.name == "nt" and shutil.which("winget"):
        cmd = ["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"]
    elif sys.platform == "darwin" and shutil.which("brew"):
        cmd = ["brew", "install", "ffmpeg"]
    else:
        print("ffmpeg is missing. Install it (Windows: winget install Gyan.FFmpeg, macOS: https://brew.sh then "
              "brew install ffmpeg, Linux: your package manager) and run this again."); return
    if ask(f"ffmpeg is missing. Install it now with `{' '.join(cmd[:4])}`?"):
        subprocess.run(cmd)
        print("installed" if find_ffmpeg() else "still not found - open a new terminal and run install.py again")
    else:
        print("skipped - the pipeline needs ffmpeg before the first step")


def nvidia():
    """CUDA version the NVIDIA driver supports (e.g. 12.6), or None"""
    if not shutil.which("nvidia-smi"): return None
    out = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
    import re
    m = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", out)
    return (int(m[1]), int(m[2])) if m else None


def have_extras():
    return subprocess.run([str(PY), "-c", "import faster_whisper, open_clip, torch"], capture_output=True).returncode == 0


def extras():
    step("AI extras (optional)")
    if have_extras() and EXTRAS is None:
        print("already installed"); return
    cuda = nvidia()
    where = f"NVIDIA GPU, CUDA {cuda[0]}.{cuda[1]}" if cuda else "Apple Silicon" if sys.platform == "darwin" else "CPU only (slower)"
    print("Speech transcripts + subtitles (Whisper), laughter/cheering detection, image search and automatic visual\n"
          f"tags, neural beat tracking. Download: ~{'4.5' if cuda else '2.5'} GB now, models ~2 GB on first use. Runs on: {where}.\n"
          "Everything else works without them.")
    if EXTRAS is False or (EXTRAS is None and not ask("Install the AI extras?")):
        print("skipped - run `python install.py --extras` any time to add them"); return
    torch = ["torch", "torchvision", "torchaudio"]
    if cuda and cuda >= (12, 6): idx = ["--index-url", "https://download.pytorch.org/whl/cu126"]
    elif cuda and cuda >= (11, 8): idx = ["--index-url", "https://download.pytorch.org/whl/cu118"]
    elif sys.platform != "darwin": idx = ["--index-url", "https://download.pytorch.org/whl/cpu"]   # no 2 GB CUDA libs
    else: idx = []
    pip = [str(PY), "-m", "pip", "install", "--disable-pip-version-check"]
    print("installing PyTorch ...")
    subprocess.run(pip + torch + idx, check=True)
    print("installing the rest ...")
    subprocess.run(pip + ["-r", str(REPO / "requirements-ai.txt")], check=True)
    print("ok" if have_extras() else "something is missing - see the messages above")


def remove_old_link():
    """the project used to be called highlight-film: drop that skill link if it points into this repo or nowhere"""
    old = LINK.parent / "highlight-film"
    if not os.path.lexists(old): return
    try: target = Path(os.readlink(old).removeprefix("\\\\?\\"))
    except OSError: return                            # a real folder: not ours to touch
    if not target.exists() or REPO.resolve() in target.resolve().parents:
        os.rmdir(old) if os.name == "nt" else os.unlink(old)
        print(f"removed the old /highlight-film link ({old})")


def link_skill():
    step("Claude Code skill")
    LINK.parent.mkdir(parents=True, exist_ok=True)
    remove_old_link()
    if LINK.exists() or os.path.lexists(LINK):
        try:
            target = Path(os.readlink(LINK).removeprefix("\\\\?\\"))   # symlink (macOS) or junction (Windows)
        except OSError:
            print(f"{LINK} is a normal folder, not a link - leaving it alone. Remove it and run again to link this repo.")
            return
        if target.resolve() == SKILL.resolve():
            print(f"already linked: {LINK}")
        else:
            os.rmdir(LINK) if os.name == "nt" else os.unlink(LINK)   # removes only the link, never its target
            print(f"was linked to {target}, relinking")
    if not os.path.lexists(LINK):
        if os.name == "nt":                           # junction: works without admin rights
            subprocess.run(["cmd", "/c", "mklink", "/J", str(LINK), str(SKILL)], check=True, capture_output=True)
        else:
            os.symlink(SKILL, LINK, target_is_directory=True)
        print(f"linked: {LINK} -> {SKILL}")
    (SKILL / "repo-path.txt").write_text(str(REPO), encoding="utf-8")   # the skill reads this to find beatcut.py


def main():
    print(f"beatcut setup in {REPO}")
    python_env(); models(); ffmpeg(); extras(); link_skill()
    print("\nDone. Make a film: put your footage in <event folder>/media, open Claude Code in the event folder "
          "and type /beatcut")


if __name__ == "__main__":
    main()

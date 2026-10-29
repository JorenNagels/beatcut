"""Run a pipeline step for an event.

  python hf.py <event-folder> <step> [args...]       e.g.  python hf.py ~/trips/ibiza-2027 14_render preview
  python hf.py <event-folder> list                   show the steps

<step> is a script name in pipeline/ without .py (a unique prefix is enough: '13' -> 13_edl).
The event folder must contain event.yaml. Uses the repo's .venv Python when it exists."""
import os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
PIPE = REPO / "pipeline"
VENV_PY = REPO / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    event = Path(sys.argv[1]).resolve()
    if not (event / "event.yaml").exists():
        sys.exit(f"no event.yaml in {event}")
    step = sys.argv[2]
    steps = sorted(p.stem for p in PIPE.glob("*.py") if p.stem not in ("common", "edl_lib"))
    if step == "list":
        print("\n".join(steps)); return
    match = [s for s in steps if s == step] or [s for s in steps if s.startswith(step)]
    if len(match) != 1:
        sys.exit(f"step '{step}' matches {match or 'nothing'}; steps: {', '.join(steps)}")
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    env = dict(os.environ, HF_EVENT=str(event), PYTHONIOENCODING="utf-8")
    r = subprocess.run([py, str(PIPE / f"{match[0]}.py")] + sys.argv[3:], cwd=PIPE, env=env)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()

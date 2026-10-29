"""Step 13: run the event's plan.py (in the event folder) -> edl.json.
The plan describes the film (sections, pinned shots, music cues) with the helpers in edl_lib.py.
Start a new plan from templates/plan.py; examples/ski-trip-plan.py is a complete film."""
import runpy
from common import EVENT_DIR

plan = EVENT_DIR / "plan.py"
if not plan.exists():
    raise SystemExit(f"no plan.py in {EVENT_DIR} - copy templates/plan.py there and fill it in")
runpy.run_path(str(plan), run_name="__main__")

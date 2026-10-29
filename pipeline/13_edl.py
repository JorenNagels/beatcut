"""Step 13: run an event plan (in the event folder) -> edl.json.   13_edl [plan_<name>.py]
The plan describes the film (sections, pinned shots, music cues) with the helpers in edl_lib.py.
plan.py writes edl.json; plan_<name>.py (e.g. a short: plan_short1.py) writes edl_<name>.json, and the other
steps take --edl <name> for it. Start from templates/plan.py (film) or templates/plan_short.py (9:16 short);
examples/ski-trip-plan.py is a complete film."""
import runpy, sys
import common
from common import EVENT_DIR

plan = EVENT_DIR / (next((a for a in sys.argv[1:] if a.endswith(".py")), "plan.py"))
if not plan.exists():
    raise SystemExit(f"no {plan.name} in {EVENT_DIR} - copy templates/plan.py there and fill it in")
common.EDL_NAME = "" if plan.stem == "plan" else plan.stem.removeprefix("plan_")
print(f"{plan.name} -> {common.edl_file()}")
runpy.run_path(str(plan), run_name="__main__")

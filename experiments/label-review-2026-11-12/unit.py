"""Print corpus v2 units: `python unit.py <unit_id> [...]` shows the text; `python unit.py --children <unit_id>` lists units under it."""
import json, sys
from pathlib import Path
UNITS = Path(__file__).resolve().parents[2] / "data/normalized/experiment-scope-v2-ve5261858b8f3/units.jsonl"
units = {}
for line in UNITS.open(encoding="utf-8"):
    u = json.loads(line); units[u["unit_id"]] = u
args = sys.argv[1:]
if args and args[0] == "--children":
    for uid in args[1:]:
        for k in units:
            if k.startswith(uid + "/") or k == uid:
                print(k, "|", units[k]["text"][:160].replace("\n", " "))
else:
    for uid in args:
        u = units.get(uid)
        print("=" * 8, uid, "(MISSING)" if u is None else "")
        if u: print(u["text"])

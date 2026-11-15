"""Print corpus v3 units: `python unit.py <unit_id> [...]` shows the text; `python unit.py --children <unit_id>` lists units under it;
`python unit.py --grep <text> [document_id]` lists units whose text contains the text."""
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
UNITS = Path(__file__).resolve().parents[2] / "data/normalized/experiment-scope-v3-v48feefc6d53b/units.jsonl"
units = {}
for line in UNITS.open(encoding="utf-8"):
    u = json.loads(line)
    units[u["unit_id"]] = u
args = sys.argv[1:]
if args and args[0] == "--children":
    for uid in args[1:]:
        for k in units:
            if k.startswith(uid + "/") or k == uid:
                print(k, "|", units[k]["text"][:160].replace("\n", " "))
elif args and args[0] == "--grep":
    needle, doc = args[1], (args[2] if len(args) > 2 else None)
    for k, u in units.items():
        if needle in u["text"] and (doc is None or u["document_id"] == doc):
            print(k, "|", u["text"][:160].replace("\n", " "))
else:
    for uid in args:
        u = units.get(uid)
        print("=" * 8, uid, "(MISSING)" if u is None else "")
        if u:
            print(u["text"])

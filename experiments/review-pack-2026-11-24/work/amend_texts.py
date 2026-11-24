"""Rebuild the normalized full text of every amending snapshot (offline) and dump it to work/amend-texts/<doc>.txt,
so each edge instruction can be read in context. Same steps as `amendments.build`."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from legal_ai.ingestion.vbpl_api import document_text, unwrap
from legal_ai.normalization.text import normalize
from legal_ai.schemas.contract import text_hash

out = Path("experiments/review-pack-2026-11-24/work/amend-texts")
out.mkdir(parents=True, exist_ok=True)
config = json.loads(Path("configs/amendments-v1.json").read_text(encoding="utf-8"))
for s in config["sources"]:
    raw = (Path("data/raw/vbpl") / s["vbpl_id"] / s["snapshot_sha256"] / "document.json").read_bytes()
    text = normalize(document_text(unwrap(raw))["text"])["text"]
    (out / f"{s['document_id']}.txt").write_text(text, encoding="utf-8")
    print(s["document_id"], len(text), text_hash(text))

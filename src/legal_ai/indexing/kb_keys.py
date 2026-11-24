"""Deterministic retrieval keys from the knowledge base (`kb-keys-v1`, plan 22/11/2026 section 4.2 step 1).

A DK3/DK4 unit record with claims gets a list of key phrases appended to its `index_text` only: what BM25 and the
dense encoder read. The keys are never shown to the generator (`generator_text` keeps the record's text without
them) and are never evidence; an answer still rests on the verbatim source text and its offsets.

Per claim, in this order (the record keeps each distinct phrase once, in order of first appearance):

1. Actor names: every canonical actor of the alias table (`configs/experiments/actor-aliases.json`, the table of
   `norm-query-v1`) whose canonical name or alias occurs as whole words in the claim's actor slot after accent
   folding (`retrieval.norm_query.actor_keys`), followed by all aliases of that entry as the table writes them. The
   actor slot may be extracted or inherited from the parent lead-in (`claims-inherit-v1`).
2. The modality in plain words, from the fixed table `MODALITY_KEYS` (none for `unknown`).
3. `SANCTION_KEY` when the claim's outcome slot names a sanction (`phạt`, `xử phạt` as a whole word).
4. The values inherited from the parent lead-in by `claims-inherit-v1` (`claim["inheritance"]["slots"]`) for the
   actor and outcome slots, verbatim.

DK4 reads its keys from the validated claim set, so the keys of claims the validator rejected are absent. The alias
table is an input of the run: changing it, or this table, is a new variant.

`kb-keys-v2` (plan 22/11/2026 section 4.2 step 2) adds, after the `kb-keys-v1` phrases, the model-written questions of
a keys run (`evaluation.keys_run`, `cli kb-keys-gen`): 2-3 everyday questions per unit, generated from the unit's text
and its DK3 claims. They follow the same rules (index text only, never evidence, never shown to the generator). A
record gets a unit's questions when one of the record's claims is among the claims the questions were written from,
so DK4 drops the questions of a unit whose claims were all rejected. The keys run must come from the same bundle and
the same DK3 claims as the condition's knowledge base; units outside the keys run's scope get no model keys.
"""

import json
from pathlib import Path
import re

from legal_ai.common.io import digest, read_jsonl
from legal_ai.retrieval.norm_query import actor_keys, fold

KEYS_VERSION = "kb-keys-v1"
MODEL_KEYS_VERSION = "kb-keys-v2"
# The norm types in plain words a person uses when telling a case: who must, who may not, who may.
MODALITY_KEYS = {
    "obligation": "nghĩa vụ phải",
    "prohibition": "bị cấm không được",
    "entitlement": "được quyền",
    "permission": "được quyền",
}
SANCTION_KEY = "bị xử phạt"
SANCTION = re.compile(r"(?<!\w)(?:xử phạt|phạt)(?!\w)", re.IGNORECASE)
INHERITED_SLOTS = ("actor", "outcome")


class KbKeys:
    """The key builder of one run: the alias table read once, with its path and SHA-256 for the manifest, and for
    `kb-keys-v2` the model keys of one keys run ({unit_id: {"claim_ids", "keys"}}, from `load_model_keys`)."""

    def __init__(self, aliases_path, model_keys=None):
        self.aliases_path = Path(aliases_path)
        table = json.loads(self.aliases_path.read_text(encoding="utf-8"))["actors"]
        self.table = {name: list(aliases) for name, aliases in table.items()}
        self.folded = {name: sorted({fold(name), *(fold(a) for a in aliases)}, key=len, reverse=True) for name, aliases in table.items()}
        self.model_keys = model_keys

    def claim_keys(self, claim):
        """The key phrases of one claim, in the fixed order of the module docstring (duplicates kept)."""
        slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
        keys = []
        actor = slots.get("actor")
        if isinstance(actor, str) and actor.strip():
            found = actor_keys(actor, self.folded)
            for name in self.table:  # Table order, so the keys never depend on set iteration.
                if name in found:
                    keys += [name, *self.table[name]]
        if claim.get("modality") in MODALITY_KEYS:
            keys.append(MODALITY_KEYS[claim["modality"]])
        outcome = slots.get("outcome")
        if isinstance(outcome, str) and SANCTION.search(outcome):
            keys.append(SANCTION_KEY)
        inherited = (claim.get("inheritance") or {}).get("slots") or {}
        for name in INHERITED_SLOTS:
            value = slots.get(name)
            if name in inherited and isinstance(value, str) and value.strip():
                keys.append(value.strip())
        return keys

    def unit_model_keys(self, unit_id, claim_ids):
        """The model questions of `unit_id` when one of `claim_ids` is among the claims they were written from."""
        entry = (self.model_keys or {}).get(unit_id)
        return list(entry["keys"]) if entry is not None and entry["claim_ids"] & set(claim_ids) else []

    def record_keys(self, claims):
        """The distinct key phrases of a record's claims, in order of first appearance: the `kb-keys-v1` phrases of
        every claim, then (`kb-keys-v2`) the model questions of the record's units."""
        keys = [key for claim in claims for key in self.claim_keys(claim)]
        if self.model_keys is not None:
            for unit_id in dict.fromkeys(claim.get("unit_id") for claim in claims):
                keys += self.unit_model_keys(unit_id, [c["claim_id"] for c in claims if c.get("unit_id") == unit_id])
        return list(dict.fromkeys(keys))


def load_model_keys(folder, units_sha256, dk3_sha256):
    """({unit_id: {"claim_ids", "keys"}}, manifest record) of a finished keys run, checked against the condition's
    bundle and DK3 claims, so that claim IDs name the same claims."""
    folder = Path(folder)
    manifest_bytes = (folder / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("bundle") or {}).get("units_sha256") != units_sha256:
        raise ValueError("the keys run was generated for another corpus bundle")
    if (manifest.get("kb_run") or {}).get("dk3_sha256") != dk3_sha256:
        raise ValueError("the keys run was generated from other DK3 claims than the condition's knowledge base")
    table = {}
    for row in read_jsonl(folder / "keys.jsonl"):
        if row["unit_id"] in table or not row["keys"]:
            raise ValueError(f"keys.jsonl repeats a unit or has one without keys: {row['unit_id']}")
        table[row["unit_id"]] = {"claim_ids": set(row["claim_ids"]), "keys": list(row["keys"])}
    record = {"path": folder.as_posix(), "manifest_sha256": digest(manifest_bytes), "keys_sha256": digest((folder / "keys.jsonl").read_bytes()),
              "model": manifest.get("model"), "effort": manifest.get("effort"), "prompt": manifest.get("prompt"), "units_with_keys": len(table)}
    return table, record


def check_config(spec):
    """`index_keys` of a condition: {"version": "kb-keys-v1", "aliases": <alias table path>} or
    {"version": "kb-keys-v2", "aliases": <alias table path>, "model_keys": <keys run directory>}."""
    shapes = {KEYS_VERSION: {"version", "aliases"}, MODEL_KEYS_VERSION: {"version", "aliases", "model_keys"}}
    if (not isinstance(spec, dict) or spec.get("version") not in shapes or set(spec) != shapes[spec["version"]]
            or not all(isinstance(spec[name], str) for name in shapes[spec["version"]])):
        raise ValueError(f'index_keys must be {{"version": "{KEYS_VERSION}", "aliases": <alias table path>}} or '
                         f'{{"version": "{MODEL_KEYS_VERSION}", "aliases": <alias table path>, "model_keys": <keys run directory>}}')
    return spec

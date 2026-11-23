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
"""

import json
from pathlib import Path
import re

from legal_ai.retrieval.norm_query import actor_keys, fold

KEYS_VERSION = "kb-keys-v1"
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
    """The key builder of one run: the alias table read once, with its path and SHA-256 for the manifest."""

    def __init__(self, aliases_path):
        self.aliases_path = Path(aliases_path)
        table = json.loads(self.aliases_path.read_text(encoding="utf-8"))["actors"]
        self.table = {name: list(aliases) for name, aliases in table.items()}
        self.folded = {name: sorted({fold(name), *(fold(a) for a in aliases)}, key=len, reverse=True) for name, aliases in table.items()}

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

    def record_keys(self, claims):
        """The distinct key phrases of a record's claims, in order of first appearance."""
        return list(dict.fromkeys(key for claim in claims for key in self.claim_keys(claim)))


def check_config(spec):
    """`index_keys` of a condition: {"version": "kb-keys-v1", "aliases": <alias table path>}."""
    if not isinstance(spec, dict) or set(spec) != {"version", "aliases"} or spec["version"] != KEYS_VERSION or not isinstance(spec["aliases"], str):
        raise ValueError(f'index_keys must be {{"version": "{KEYS_VERSION}", "aliases": <alias table path>}}')
    return spec

"""CPU lexical baseline for review; not the completed DK1/DK2 experiment."""

from collections import Counter
import math
import re
import unicodedata

from legal_ai.schemas.contract import validate_unit
from legal_ai.validation.evidence import align_quote


def tokens(text):
    return re.findall(r"[^\W_]+|%", unicodedata.normalize("NFC", text).lower(), re.UNICODE)


def search(units, question, top_k=5):
    if type(top_k) is not int or not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")
    for unit in units:
        validate_unit(unit)
    by_id = {unit["unit_id"]: unit for unit in units}
    if len(by_id) != len(units):
        raise ValueError("duplicate unit ID")
    parents = {unit["parent_id"] for unit in units}
    leaves = [unit for unit in units if unit["unit_id"] not in parents]
    documents = []
    for unit in leaves:
        chain, seen, current = [], set(), unit
        while current:
            if current["unit_id"] in seen:
                raise ValueError("parent cycle")
            seen.add(current["unit_id"])
            chain.append(current)
            if current["parent_id"] and current["parent_id"] not in by_id:
                raise ValueError("missing parent")
            current = by_id.get(current["parent_id"])
        documents.append((unit, chain, Counter(tokens("\n".join(u["text"] for u in reversed(chain))))))
    if not documents:
        return []
    average_length = sum(sum(counts.values()) for _, _, counts in documents) / len(documents)
    query = set(tokens(question))
    results = []
    for unit, chain, counts in documents:
        score = 0.0
        for token in query:
            frequency = counts[token]
            document_frequency = sum(token in doc_counts for _, _, doc_counts in documents)
            if frequency:
                idf = math.log(1 + (len(documents) - document_frequency + 0.5) / (document_frequency + 0.5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * sum(counts.values()) / average_length))
        if score > 0:
            results.append({"unit_id": unit["unit_id"], "score": score, "evidence": align_quote(unit, unit["text"]), "parent_evidence": [align_quote(parent, parent["text"]) for parent in reversed(chain[1:])]})
    return sorted(results, key=lambda row: (-row["score"], row["unit_id"]))[:top_k]

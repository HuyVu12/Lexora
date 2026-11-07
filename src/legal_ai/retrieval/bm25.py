"""CPU lexical retrieval: the BM25 ranker shared by DK1/DK2 runs and the review search over leaf units."""

from collections import Counter
import math
import re
import unicodedata

from legal_ai.schemas.contract import validate_unit
from legal_ai.validation.evidence import align_quote


def tokens(text):
    return re.findall(r"[^\W_]+|%", unicodedata.normalize("NFC", text).lower(), re.UNICODE)


class BM25:
    """Okapi BM25 over pre-tokenized documents: idf = ln(1 + (N - df + 0.5) / (df + 0.5)).

    `rank` returns (index, score) for documents with a positive score, best first, ties broken by index
    so a fixed document order gives a reproducible ranking. Query tokens count once each.
    """

    def __init__(self, documents, k1=1.2, b=0.75):
        if not (isinstance(k1, (int, float)) and k1 >= 0 and isinstance(b, (int, float)) and 0 <= b <= 1):
            raise ValueError("need k1 >= 0 and 0 <= b <= 1")
        self.k1, self.b = k1, b
        self.counts = [Counter(document) for document in documents]
        self.lengths = [sum(counts.values()) for counts in self.counts]
        self.average = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        frequency = Counter(token for counts in self.counts for token in counts)
        total = len(self.counts)
        self.idf = {token: math.log(1 + (total - df + 0.5) / (df + 0.5)) for token, df in frequency.items()}

    def rank(self, query):
        scored = []
        terms = [token for token in dict.fromkeys(query) if token in self.idf]
        for index, counts in enumerate(self.counts):
            score = 0.0
            for token in terms:
                tf = counts[token]
                if tf:
                    norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average)
                    score += self.idf[token] * tf * (self.k1 + 1) / (tf + norm)
            if score > 0:
                scored.append((index, score))
        return sorted(scored, key=lambda row: (-row[1], row[0]))


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
        documents.append((unit, chain, tokens("\n".join(u["text"] for u in reversed(chain)))))
    if not documents:
        return []
    # k1=1.5, b=0.75: the parameters this review search has always used.
    index = BM25([document for _, _, document in documents], k1=1.5, b=0.75)
    results = []
    for position, score in index.rank(tokens(question)):
        unit, chain, _ = documents[position]
        results.append({"unit_id": unit["unit_id"], "score": score, "evidence": align_quote(unit, unit["text"]), "parent_evidence": [align_quote(parent, parent["text"]) for parent in reversed(chain[1:])]})
    return sorted(results, key=lambda row: (-row["score"], row["unit_id"]))[:top_k]

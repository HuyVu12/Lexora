"""Versioned evidence graph, exported as JSON and SQLite for local review."""

from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from legal_ai.common.io import canonical, digest, read_jsonl, write_json
from legal_ai.extraction.candidates import rule_candidates
from legal_ai.kb.references import detect_references
from legal_ai.validation.bundle import validate_bundle
from legal_ai.validation.evidence import align_quote, check_evidence, validate_record

GRAPH_VERSION = "evidence-graph-v2"


def make_graph(documents, units, evidence, claims, *, aliases=None, include_candidates=False, extraction_mode="unit-cues"):
    decisions = validate_bundle(documents, units, evidence, claims)
    if any(row["decision"] == "rejected" for row in decisions):
        raise ValueError("rejected claim cannot enter review graph")
    claims = list(claims)
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    extraction_report = []
    if include_candidates:
        if extraction_mode == "norm-rules-v1":
            from legal_ai.extraction.norms import extract_norms
            candidates, anchors, extraction_report = extract_norms(units)
        elif extraction_mode == "unit-cues":
            candidates, anchors = rule_candidates(units)
        else:
            raise ValueError("unsupported extraction mode")
        existing = {claim["claim_id"] for claim in claims}
        claims.extend(claim for claim in candidates if claim["claim_id"] not in existing)
        for anchor in anchors:
            evidence_by_id[anchor["evidence_id"]] = anchor
    nodes, edges, references = {}, {}, []
    unit_by_id = {unit["unit_id"]: unit for unit in units}
    unit_nodes = {unit["unit_version_id"]: "unit:" + unit["unit_version_id"] for unit in units}
    document_nodes = {doc["document_id"]: "document:" + doc["document_id"] + ":" + doc["document_version_id"] for doc in documents}

    def node(key, kind, label, payload):
        record = {"id": key, "kind": kind, "label": label, "payload": payload}
        if key in nodes and nodes[key] != record:
            raise ValueError("node identity collision")
        nodes[key] = record
        return key

    def edge(kind, source, target, proof):
        proof = sorted(set(proof))
        if not proof:
            raise ValueError("edge must carry evidence")
        key = digest(canonical([GRAPH_VERSION, kind, source, target, proof]))
        edges[key] = {"id": key, "kind": kind, "source": source, "target": target, "evidence_ids": proof}

    for document in documents:
        node(document_nodes[document["document_id"]], "Document", document["title"], document)
    for unit in units:
        node(unit_nodes[unit["unit_version_id"]], "LegalUnit", unit["text"].splitlines()[0], unit)
        anchor = align_quote(unit, unit["text"])
        evidence_by_id[anchor["evidence_id"]] = anchor
        parent = unit_nodes[unit_by_id[unit["parent_id"]]["unit_version_id"]] if unit["parent_id"] else document_nodes[unit["document_id"]]
        edge("PART_OF", unit_nodes[unit["unit_version_id"]], parent, [anchor["evidence_id"]])
        for reference in detect_references(unit, units, aliases):
            anchor = reference["evidence"]
            evidence_by_id[anchor["evidence_id"]] = anchor
            references.append(reference)
            ref_node = node("reference:" + reference["reference_id"], "ReferenceMention", reference["raw"], {key: value for key, value in reference.items() if key != "evidence"})
            edge("MENTIONS_REFERENCE", unit_nodes[unit["unit_version_id"]], ref_node, [anchor["evidence_id"]])
            if reference["status"] == "resolved":
                for target_version in reference["target_unit_version_ids"]:
                    edge("REFERENCES", unit_nodes[unit["unit_version_id"]], unit_nodes[target_version], [anchor["evidence_id"]])
    for claim in claims:
        decision = validate_record(claim, list(evidence_by_id.values()), units)
        if decision["decision"] == "rejected":
            raise ValueError("candidate evidence invalid")
        semantic = claim["extraction_run_id"].startswith("norm-rules-v1:")
        claim_node = node("claim:" + digest(canonical([claim["extraction_run_id"], claim["claim_id"]])), "NormClaim", (claim["slots"]["action"]["text"] if semantic and claim["slots"].get("action", {}).get("state") == "present" else "Quy phạm giới hạn định lượng" if semantic else "Ứng viên quy phạm"), {**claim, "validation": decision, "semantic_extraction": semantic})
        for version in claim["source_unit_version_ids"]:
            proof = [eid for eid in claim["evidence_ids"] if evidence_by_id[eid]["unit_version_id"] == version]
            edge("EXTRACTED_FROM", claim_node, unit_nodes[version], proof)
        for name, slot in claim["slots"].items():
            if slot["state"] != "present":
                continue
            kinds = {"actor": "Entity", "beneficiary": "Entity", "recipient": "Entity", "counterparty": "Entity", "action": "Action", "object": "LegalConcept", "conditions": "Condition", "exceptions": "Exception", "quantities": "Quantity", "deadlines": "Deadline", "scope": "Scope", "outcome": "Outcome", "references": "ReferenceText"}
            edge_kinds = {"actor": "HAS_ACTOR", "beneficiary": "HAS_BENEFICIARY", "recipient": "HAS_RECIPIENT", "counterparty": "HAS_COUNTERPARTY", "action": "HAS_ACTION", "object": "HAS_OBJECT", "conditions": "HAS_CONDITION", "exceptions": "HAS_EXCEPTION", "quantities": "HAS_QUANTITY", "deadlines": "HAS_DEADLINE", "scope": "HAS_SCOPE", "outcome": "HAS_OUTCOME", "references": "HAS_REFERENCE_TEXT"}
            slot_node = node(claim_node + "/slot/" + name, kinds[name] if semantic else "ClaimSlot", slot["text"] if semantic else name, {**slot, "slot_name": name, "claim_id": claim["claim_id"], "document_id": evidence_by_id[slot["evidence_ids"][0]]["document_id"], "identity_scope": "claim-local mention; not globally resolved", "validation_decision": decision["decision"]})
            edge(edge_kinds[name] if semantic else "HAS_SLOT", claim_node, slot_node, slot["evidence_ids"])
            for eid in slot["evidence_ids"]:
                edge("SUPPORTED_BY", slot_node, "evidence:" + eid, [eid])
        if semantic and claim.get("modality_evidence_ids"):
            modality_node = node(claim_node + "/modality", "Modality", claim["modality"], {"text": claim["modality"], "evidence_ids": claim["modality_evidence_ids"], "claim_id": claim["claim_id"], "document_id": evidence_by_id[claim["modality_evidence_ids"][0]]["document_id"], "validation_decision": decision["decision"]})
            edge("HAS_MODALITY", claim_node, modality_node, claim["modality_evidence_ids"])
            for eid in claim["modality_evidence_ids"]:
                edge("SUPPORTED_BY", modality_node, "evidence:" + eid, [eid])
    for anchor in evidence_by_id.values():
        if check_evidence(anchor, units):
            raise ValueError("invalid graph evidence")
        eid = node("evidence:" + anchor["evidence_id"], "Evidence", anchor["quote"], anchor)
        edge("ANCHORED_IN", eid, unit_nodes[anchor["unit_version_id"]], [anchor["evidence_id"]])
    for row in edges.values():
        if row["source"] not in nodes or row["target"] not in nodes or not set(row["evidence_ids"]) <= evidence_by_id.keys():
            raise ValueError("dangling graph edge/evidence")
    content = {"graph_version": GRAPH_VERSION, "nodes": sorted(nodes.values(), key=lambda row: row["id"]), "edges": sorted(edges.values(), key=lambda row: row["id"]), "references": sorted(references, key=lambda row: row["reference_id"]), "extraction_report": sorted(extraction_report, key=lambda row: row["unit_id"])}
    return {**content, "graph_hash": digest(canonical(content)), "summary": {"nodes": dict(sorted(Counter(row["kind"] for row in nodes.values()).items())), "edges": dict(sorted(Counter(row["kind"] for row in edges.values()).items())), "reference_status": dict(sorted(Counter(row["status"] for row in references).items())), "claim_decisions": dict(sorted(Counter(nodes[key]["payload"]["validation"]["decision"] for key in nodes if nodes[key]["kind"] == "NormClaim").items())), "synthetic": any(document["synthetic"] for document in documents), "legal_status": "unknown"}}


def build_graph(bundle, output, aliases=None, include_candidates=False, extraction_mode="unit-cues"):
    bundle, output = Path(bundle), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("graph output must be new or empty")
    records = [read_jsonl(bundle / f"{name}.jsonl") for name in ("documents", "units", "evidence", "claims")]
    graph = make_graph(*records, aliases=aliases, include_candidates=include_candidates, extraction_mode=extraction_mode)
    write_json(output / "graph.json", graph)
    with closing(sqlite3.connect(output / "graph.sqlite")) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, payload TEXT NOT NULL)")
        connection.execute("CREATE TABLE edges (id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL REFERENCES nodes(id), target TEXT NOT NULL REFERENCES nodes(id), evidence_ids TEXT NOT NULL)")
        connection.execute("CREATE INDEX edges_source ON edges(source)")
        connection.execute("CREATE INDEX edges_target ON edges(target)")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?)", [(row["id"], row["kind"], row["label"], canonical(row["payload"])) for row in graph["nodes"]])
        connection.executemany("INSERT INTO edges VALUES (?, ?, ?, ?, ?)", [(row["id"], row["kind"], row["source"], row["target"], canonical(row["evidence_ids"])) for row in graph["edges"]])
        connection.execute("INSERT INTO metadata VALUES (?, ?)", ("graph_hash", graph["graph_hash"]))
    from legal_ai.kb.viewer import render_viewer
    render_viewer(graph, output / "index.html")
    artifacts = ["graph.json", "graph.sqlite", "index.html"]
    if (output / "structure.html").exists():
        artifacts.append("structure.html")
    manifest = {"graph_version": GRAPH_VERSION, "graph_hash": graph["graph_hash"], "bundle_hashes": {name: digest((bundle / name).read_bytes()) for name in ("documents.jsonl", "units.jsonl", "evidence.jsonl", "claims.jsonl")}, "aliases": aliases or {}, "include_candidates": include_candidates, "extraction_mode": extraction_mode, "summary": graph["summary"], "status": "prepared_for_review", "artifacts": {name: digest((output / name).read_bytes()) for name in artifacts}}
    write_json(output / "manifest.json", manifest)
    return manifest

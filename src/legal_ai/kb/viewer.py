"""Self-contained graph inspector, generated from a validated local graph."""

from pathlib import Path
import json

from legal_ai.glossary import embed_terms


def render_viewer(graph, output):
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    semantic = any(node["kind"] == "NormClaim" and node["payload"].get("semantic_extraction") for node in graph["nodes"])
    template = Path(__file__).with_name("entity-viewer.html" if semantic else "viewer.html").read_text(encoding="utf-8")
    Path(output).write_text(embed_terms(template.replace("__GRAPH_JSON__", payload)), encoding="utf-8")
    if semantic:
        structure = Path(__file__).with_name("viewer.html").read_text(encoding="utf-8")
        Path(output).with_name("structure.html").write_text(embed_terms(structure.replace("__GRAPH_JSON__", payload)), encoding="utf-8")

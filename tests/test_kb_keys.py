"""Deterministic retrieval keys of the knowledge base (`kb-keys-v1`): in the index text only, never in what the
generator reads; DK4 keys come from the validated claims only; off by default. The thin claim view (`claims_view:
thin`) prints only what is not verbatim in the source text. Synthetic statute, not real law."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_kb_records_graph import LAW, claim
from test_retrieval_run import bundle
from legal_ai.common.io import canonical, digest, read_jsonl, write_json, write_jsonl
from legal_ai.evaluation.preflight import check
from legal_ai.evaluation.retrieval_run import run
from legal_ai.indexing.kb_keys import MODALITY_KEYS, SANCTION_KEY, KbKeys, check_config
from legal_ai.indexing.packing import Packer
from legal_ai.indexing.records import kb_unit_records, structural_records, thin_lines, token_spans

# Digest of the DK3 records of the fixture (full and compact views) built by the code before kb-keys-v1 (commit cba25dc).
OLD_RECORDS_SHA256 = "5435eb7206fc439e6d00aef013cbdcc7615213f850a5215380413ba160c32b85"


class KbKeysTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.documents, self.units, self.texts = bundle(self.root / "bundle", {"syn": LAW})
        self.aliases = self.root / "aliases.json"
        write_json(self.aliases, {"status": "draft", "actors": {"bên vi phạm": ["người gây thiệt hại", "bên có lỗi"], "Bên A": ["bên thứ nhất"]}})
        self.keys = KbKeys(self.aliases)
        inherited = claim(self.units, "syn/chapter-i/article-3/clause-1", "Bên vi phạm phải bồi thường một khoản tiền tương ứng", "kb:3",
                          actor="Bên vi phạm", action="bồi thường một khoản tiền tương ứng", outcome="Phạt tiền")
        inherited["inheritance"] = {"version": "claims-inherit-v1", "slots": {"actor": {"rule": "leadin-subject"}, "outcome": {"rule": "leadin-sanction"}}}
        self.claims = [claim(self.units, "syn/chapter-i/article-1/clause-1", "Không quá 60 ngày", "kb:1", quantities="60 ngày") | {"modality": "unknown"},
                       claim(self.units, "syn/chapter-i/article-2/clause-1", "Bên A phải thông báo kết quả thử nghiệm cho bên B", "kb:2",
                             actor="Bên A", action="thông báo kết quả thử nghiệm"),
                       inherited]
        kb = self.root / "kb"
        write_json(kb / "manifest.json", {"units_sha256": digest((self.root / "bundle" / "units.jsonl").read_bytes())})
        write_jsonl(kb / "dk3.jsonl", self.claims)
        write_jsonl(kb / "dk4.jsonl", [self.claims[0], self.claims[2]])  # The validator rejected kb:2.
        self.kb = kb
        self.questions = self.root / "q.json"
        write_json(self.questions, {"questions": [
            {"question_id": "q1", "question": "Người gây thiệt hại chịu gì?", "split": "dev", "expected_status": "answer",
             "relevant_unit_ids": ["syn/chapter-i/article-3/clause-1"]}]})
        self.shared = self.root / "shared.json"
        write_json(self.shared, {"top_k": 1, "token_budgets": [40, 400],
                                 "retrieval": {"method": "bm25", "tokenizer": "lexora-syllable-v1", "k1": 1.2, "b": 0.75, "recall_k": [1]}})

    def condition(self, name, condition, **extra):
        path = self.root / f"{name}.json"
        write_json(path, {"condition": condition, "representation": {"DK3": "llm_kb_raw", "DK4": "llm_kb_validated", "DK2": "structural_units"}[condition],
                          "max_tokens": 384, "record": "unit_with_claims", "kb_run": self.kb.as_posix()} | extra)
        return path

    def spec(self):
        return {"version": "kb-keys-v1", "aliases": self.aliases.as_posix()}

    def test_claim_keys_follow_the_fixed_order_and_tables(self):
        self.assertEqual(self.keys.claim_keys(self.claims[0]), [], "unknown modality and no actor: no key")
        self.assertEqual(self.keys.claim_keys(self.claims[1]), ["Bên A", "bên thứ nhất", MODALITY_KEYS["obligation"]])
        self.assertEqual(self.keys.claim_keys(self.claims[2]), ["bên vi phạm", "người gây thiệt hại", "bên có lỗi", "nghĩa vụ phải", SANCTION_KEY,
                                                                "Bên vi phạm", "Phạt tiền"],
                         "alias entry, modality, sanction, then the inherited actor and outcome verbatim")
        twice = self.keys.record_keys([self.claims[1], self.claims[1] | {"claim_id": "kb:2b"}])
        self.assertEqual(twice, ["Bên A", "bên thứ nhất", "nghĩa vụ phải"], "each phrase once per record")
        self.assertEqual(MODALITY_KEYS["entitlement"], MODALITY_KEYS["permission"])

    def test_keys_reach_the_index_text_only(self):
        for view in ("full", "compact"):
            plain = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view=view)
            keyed = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view=view, index_keys=self.keys)
            self.assertEqual(len(plain), len(keyed))
            for a, b in zip(plain, keyed):
                self.assertEqual((a["text"], a["token_count"], a["record_id"], a["claim_ids"]), (b["text"], b["token_count"], b["record_id"], b["claim_ids"]))
                self.assertEqual(a.get("generator_text") or a["index_text"], b.get("generator_text") or b["index_text"], "the generator reads the same text")
                if b.get("index_keys"):
                    self.assertEqual(b["index_text"], a["index_text"] + "\n" + " · ".join(b["index_keys"]))
                    self.assertNotIn("bên thứ nhất", b["generator_text"])
                else:
                    self.assertEqual(a, b, f"a record without keys is unchanged ({view})")
            for mode in ("P0", "P3"):
                ranked = list(reversed(keyed))
                one = Packer(mode, plain, self.units, self.documents).pack(list(reversed(plain)), 10 ** 6)
                two = Packer(mode, keyed, self.units, self.documents).pack(ranked, 10 ** 6)
                self.assertEqual([b["text"] for b in one["blocks"]], [b["text"] for b in two["blocks"]], f"packed text unchanged ({view}, {mode})")
                self.assertEqual(one["tokens"], two["tokens"])
        no_claims = next(r for r in keyed if r["unit_ids"] == ["syn/chapter-i/article-4"])
        self.assertNotIn("index_keys", no_claims)

    def test_default_off_reproduces_the_old_records(self):
        out = []
        for view in ("full", "compact"):
            records = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view=view)
            self.assertEqual(records, kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view=view, index_keys=None))
            self.assertFalse(any("index_keys" in r for r in records))
            out.append(records)
        self.assertEqual(digest(canonical(out)), OLD_RECORDS_SHA256)
        run(self.root / "bundle", self.questions, self.condition("dk3", "DK3"), self.shared, self.root / "r-plain")
        written = read_jsonl(self.root / "r-plain" / "records.jsonl")
        self.assertFalse(any("index_keys" in r or "generator_text" in r for r in written), "the full view without keys has no new field")

    def test_dk4_keys_exclude_rejected_claims_and_change_the_ranking(self):
        three = self.root / "r3"
        four = self.root / "r4"
        plain = run(self.root / "bundle", self.questions, self.condition("dk3", "DK3"), self.shared, self.root / "r3-plain")
        keyed = run(self.root / "bundle", self.questions, self.condition("dk3k", "DK3", index_keys=self.spec()), self.shared, three)
        run(self.root / "bundle", self.questions, self.condition("dk4k", "DK4", index_keys=self.spec()), self.shared, four)
        self.assertEqual(plain["mean_recall"]["1"], 0.0, "the question names the bearer only by an alias")
        self.assertEqual(keyed["mean_recall"]["1"], 1.0, "the alias key finds it")
        dk3 = {r["unit_ids"][0]: r for r in read_jsonl(three / "records.jsonl")}
        dk4 = {r["unit_ids"][0]: r for r in read_jsonl(four / "records.jsonl")}
        self.assertIn("bên thứ nhất", dk3["syn/chapter-i/article-2/clause-1"]["index_text"])
        self.assertNotIn("index_keys", dk4["syn/chapter-i/article-2/clause-1"], "kb:2 was rejected, so DK4 has none of its keys")
        self.assertNotIn("bên thứ nhất", dk4["syn/chapter-i/article-2/clause-1"]["index_text"])
        self.assertEqual(dk4["syn/chapter-i/article-3/clause-1"]["index_keys"], dk3["syn/chapter-i/article-3/clause-1"]["index_keys"])
        manifest = json.loads((three / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["index_keys"]["aliases_sha256"], digest(self.aliases.read_bytes()))
        self.assertEqual(manifest["index_keys"]["records_with_keys"], 2)
        report = check([three, four])
        shape = next(c for c in report["checks"] if c["check"] == "DK3 and DK4 use the same record shape and graph")
        self.assertEqual(shape["status"], "pass")
        report = check([self.root / "r3-plain", four])
        shape = next(c for c in report["checks"] if c["check"] == "DK3 and DK4 use the same record shape and graph")
        self.assertEqual(shape["status"], "fail", "DK3 without keys and DK4 with keys are not one ladder")

    def test_thin_view_prints_only_what_is_not_verbatim(self):
        lead = claim(self.units, "syn/chapter-i/article-1/clause-2", "Không quá 6 ngày đối với công việc khác", "kb:4",
                     actor="hai bên", quantities="6 ngày", conditions="đối với công việc khác")
        lead["inheritance"] = {"version": "claims-inherit-v1", "slots": {"actor": {"rule": "leadin-subject"}}}
        twin = dict(lead, claim_id="kb:5")
        claims = self.claims + [lead, twin]
        dk2 = {r["unit_ids"][0]: r for r in structural_records(self.documents, self.units, self.texts)}
        compact = {r["unit_ids"][0]: r for r in kb_unit_records("DK3", self.documents, self.units, self.texts, claims, view="compact")}
        thin = {r["unit_ids"][0]: r for r in kb_unit_records("DK3", self.documents, self.units, self.texts, claims, view="thin")}
        for unit_id, row in thin.items():
            base = dk2[unit_id]["index_text"].rstrip("\n")
            self.assertEqual(row["index_text"], compact[unit_id]["index_text"], "search still reads the full claims")
            self.assertTrue(row["generator_text"].startswith(base))
            self.assertLessEqual(row["token_count"], compact[unit_id]["token_count"])
            suffix = row["generator_text"][len(base):]
            for c in (c for c in claims if c["unit_id"] == unit_id):
                for name, value in c["slots"].items():
                    if value and not (name == "actor" and "inheritance" in c):
                        self.assertNotIn(value, suffix, f"slot {name} is verbatim source text")
                self.assertNotIn(c["modality_cue"], suffix)
        self.assertEqual(thin["syn/chapter-i/article-1/clause-1"]["generator_text"], dk2["syn/chapter-i/article-1/clause-1"]["index_text"].rstrip("\n"),
                         "an unknown modality adds nothing: no claim line at all")
        self.assertEqual(thin["syn/chapter-i/article-1/clause-1"]["token_count"], dk2["syn/chapter-i/article-1/clause-1"]["token_count"])
        self.assertTrue(thin["syn/chapter-i/article-2/clause-1"]["generator_text"].endswith("cho bên B.\n[Quy phạm 1] nghĩa vụ"),
                        "an extracted actor is verbatim: only the modality label is printed")
        self.assertNotIn("Chủ thể", thin["syn/chapter-i/article-3/clause-1"]["generator_text"].split("[Quy phạm 1]")[1],
                         "an inherited actor already in the unit text is not repeated")
        point = thin["syn/chapter-i/article-1/clause-2"]["generator_text"]
        self.assertTrue(point.endswith("\n[Quy phạm 1] nghĩa vụ · Chủ thể (từ câu dẫn): hai bên"), point)
        self.assertNotIn("[Quy phạm 2]", point, "an identical line is printed once")
        self.assertEqual(thin_lines([], "x"), [])
        packed = Packer("P3", list(thin.values()), self.units, self.documents).pack([thin["syn/chapter-i/article-1/clause-2"]], 10 ** 6)
        block = next(b for b in packed["blocks"] if b["record"]["unit_ids"] == ["syn/chapter-i/article-1/clause-2"])
        self.assertTrue(block["text"].endswith("[Quy phạm 1] nghĩa vụ · Chủ thể (từ câu dẫn): hai bên"))
        self.assertEqual(block["token_count"], len(token_spans(block["text"])), "the budget counts the thin line")

    def test_thin_view_with_keys_reads_thin_and_searches_keys(self):
        keyed = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view="thin", index_keys=self.keys)
        thin = kb_unit_records("DK3", self.documents, self.units, self.texts, self.claims, view="thin")
        for a, b in zip(thin, keyed):
            self.assertEqual(a["generator_text"], b["generator_text"])
            self.assertEqual(a["token_count"], b["token_count"])
        row = next(r for r in keyed if r["unit_ids"] == ["syn/chapter-i/article-3/clause-1"])
        self.assertIn("người gây thiệt hại", row["index_text"])
        self.assertNotIn("người gây thiệt hại", row["generator_text"])
        result = run(self.root / "bundle", self.questions, self.condition("dk3t", "DK3", claims_view="thin", index_keys=self.spec()), self.shared,
                     self.root / "r-thin")
        self.assertEqual(result["mean_recall"]["1"], 1.0)

    def test_bad_configs_are_rejected(self):
        for bad in ("kb-keys-v1", {"version": "kb-keys-v2", "aliases": "x"}, {"version": "kb-keys-v1"}):
            with self.assertRaisesRegex(ValueError, "index_keys"):
                check_config(bad)
        with self.assertRaisesRegex(ValueError, "unit_with_claims"):
            run(self.root / "bundle", self.questions, self.condition("c", "DK3", record="claims", index_keys=self.spec()), self.shared, self.root / "c")
        with self.assertRaisesRegex(ValueError, "DK3/DK4 only"):
            run(self.root / "bundle", self.questions, self.condition("d2", "DK2", index_keys=self.spec()), self.shared, self.root / "d2")


if __name__ == "__main__":
    unittest.main()

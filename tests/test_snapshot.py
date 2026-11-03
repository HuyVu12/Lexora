"""Snapshot failures and immutable storage, with all network calls mocked."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legal_ai.common.io import digest
from legal_ai.ingestion.snapshot import snapshot, OfficialRedirects


class SnapshotTests(unittest.TestCase):
    def response(self, data):
        response = MagicMock()
        response.__enter__.return_value = response
        response.url = "https://vbpl.vn/law"
        response.headers.get.return_value = "text/html"
        response.headers.get_content_charset.return_value = "utf-8"
        response.read.return_value = data
        return response

    def test_disallowed_host_and_unsafe_id_never_open_network(self):
        with patch("legal_ai.ingestion.snapshot.build_opener") as opener:
            for url, document_id in (("https://example.com/law", "safe"), ("https://vbpl.vn/law", "../outside")):
                with self.assertRaises(ValueError):
                    snapshot(url, "unused", document_id, "marker")
            opener.assert_not_called()

    def test_redirect_rejects_unapproved_host_before_following(self):
        with self.assertRaises(ValueError):
            OfficialRedirects().redirect_request(None, None, 302, "Found", {}, "https://example.com/law")

    def test_homepage_not_saved_as_snapshot(self):
        response = self.response("<html>marker Điều Navigation only</html>".encode("utf-8"))
        response.url = "https://vbpl.vn/"
        with tempfile.TemporaryDirectory() as temp, patch("legal_ai.ingestion.snapshot.build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(ValueError):
                snapshot("https://vbpl.vn/law", temp, "safe", "marker")
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_valid_snapshot_hash_and_metadata_are_immutable(self):
        body = '<p class="prov-article">Điều 1. marker</p>'
        stream = f"f:T{len(body.encode('utf-8')):x}," + body
        data = ('<html>marker Điều<script>self.__next_f.push(' + json.dumps([1, stream], ensure_ascii=False) + ')</script></html>').encode("utf-8")
        response = self.response(data)
        with tempfile.TemporaryDirectory() as temp, patch("legal_ai.ingestion.snapshot.build_opener") as opener:
            opener.return_value.open.return_value = response
            first = snapshot(response.url, temp, "safe", "marker")
            second = snapshot(response.url, temp, "safe", "marker")
            self.assertEqual(first, second)
            self.assertEqual(Path(first["local_path"]).read_bytes(), data)
            self.assertEqual(first["source_sha256"], digest(data))
            Path(first["local_path"]).write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                snapshot(response.url, temp, "safe", "marker")

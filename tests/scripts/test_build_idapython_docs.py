"""Unit tests for scripts/build_idapython_docs.py — HTML index parser."""

from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.build_idapython_docs import (
    MANIFEST_SCHEMA_VERSION,
    Manifest,
    ManifestEntry,
    discover_modules_from_index,
    fetch_with_retry,
    load_manifest,
    sha256_text,
    write_atomic,
    write_manifest,
)


class TestDiscoverModules(unittest.TestCase):
    def test_parses_module_links_from_index_html(self):
        # Hex-Rays index page has <a href="ida_typeinf/"> links for each module
        html = """
        <html><body>
        <a href="ida_typeinf/">ida_typeinf</a>
        <a href="ida_name/">ida_name</a>
        <a href="idautils/">idautils</a>
        <a href="idaapi/">idaapi</a>
        <a href="https://example.com/external/">skip me</a>
        <a href="#fragment">skip me too</a>
        </body></html>
        """
        result = discover_modules_from_index(html)
        self.assertEqual(
            sorted(result),
            ["ida_name", "ida_typeinf", "idaapi", "idautils"],
        )

    def test_empty_html_returns_empty_list(self):
        self.assertEqual(discover_modules_from_index(""), [])

    def test_malformed_html_no_modules_returns_empty(self):
        # If no <a href="<module>/"> matches, parser returns empty
        html = "<html><body><p>no modules here</p></body></html>"
        self.assertEqual(discover_modules_from_index(html), [])


class TestFetchWithRetry(unittest.TestCase):
    def test_successful_fetch_returns_body(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"ida_typeinf module docs"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = fetch_with_retry("https://example.com/test")
        self.assertEqual(result, "ida_typeinf module docs")

    def test_retries_on_timeout_then_succeeds(self):
        # First 2 calls raise timeout, 3rd succeeds
        mock_response = MagicMock()
        mock_response.read.return_value = b"success"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch(
            "urllib.request.urlopen",
            side_effect=[TimeoutError("net"), TimeoutError("net"), mock_response],
        ):
            with patch("time.sleep"):  # Don't actually sleep in tests
                result = fetch_with_retry("https://example.com/test", max_retries=3)
        self.assertEqual(result, "success")

    def test_persistent_timeout_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("net")):
            with patch("time.sleep"):
                result = fetch_with_retry("https://example.com/test", max_retries=2)
        self.assertIsNone(result)

    def test_http_404_returns_none_no_retry(self):
        # 4xx is not retried — module path is genuinely wrong
        error = urllib.error.HTTPError("https://example.com/x", 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            result = fetch_with_retry("https://example.com/x", max_retries=3)
        self.assertIsNone(result)


class TestHelpers(unittest.TestCase):
    def test_write_atomic_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "subdir" / "out.txt"
            write_atomic(target, "hello world")
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_text(encoding="utf-8"), "hello world")

    def test_write_atomic_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            target.write_text("old")
            write_atomic(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "new")

    def test_write_atomic_no_tmp_files_left_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            write_atomic(target, "content")
            leftovers = list(Path(tmp).glob("*.tmp*"))
            self.assertEqual(leftovers, [], msg=f"leftover tmp files: {leftovers}")

    def test_write_atomic_writes_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.bin"
            payload = b"\x00\x01\x02 binary"
            write_atomic(target, payload)
            self.assertEqual(target.read_bytes(), payload)

    def test_sha256_text_deterministic(self):
        h1 = sha256_text("hello")
        h2 = sha256_text("hello")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)  # SHA-256 hex = 64 chars

    def test_sha256_text_matches_known_value(self):
        # sha256("hello") -> 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
        self.assertEqual(
            sha256_text("hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    def test_sha256_text_distinguishes_different_inputs(self):
        self.assertNotEqual(sha256_text("hello"), sha256_text("world"))


def _sample_entry(name: str = "ida_typeinf") -> ManifestEntry:
    return ManifestEntry(
        name=name,
        file=f"{name}.rst.txt",
        source_url=f"https://python.docs.hex-rays.com/_sources/{name}/index.rst.txt",
        sha256="a" * 64,
        byte_size=12345,
        fetched_at="2026-07-07T00:00:00Z",
    )


class TestManifestRoundTrip(unittest.TestCase):
    def test_write_then_load_returns_equal_manifest(self):
        manifest = Manifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            upstream_base="https://python.docs.hex-rays.com",
            fetched_at="2026-07-07T00:00:00Z",
            module_count=2,
            total_bytes=24690,
            modules=(_sample_entry("ida_typeinf"), _sample_entry("ida_name")),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            write_manifest(manifest, path=path)
            loaded = load_manifest(path=path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded, manifest)

    def test_write_atomic_no_tmp_leftovers(self):
        manifest = Manifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            upstream_base="https://python.docs.hex-rays.com",
            fetched_at="2026-07-07T00:00:00Z",
            module_count=1,
            total_bytes=100,
            modules=(_sample_entry(),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            write_manifest(manifest, path=path)
            leftovers = list(Path(tmp).glob("*.tmp*"))
            self.assertEqual(leftovers, [])

    def test_load_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = load_manifest(path=Path(tmp) / "MANIFEST.json")
            self.assertIsNone(result)

    def test_load_corrupt_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            path.write_text("not valid json {{{", encoding="utf-8")
            self.assertIsNone(load_manifest(path=path))

    def test_schema_version_preserved_across_writes(self):
        # If existing MANIFEST exists with schema_version=N, write_manifest
        # does NOT bump to current MANIFEST_SCHEMA_VERSION blindly —
        # we just preserve what's passed in.
        manifest = Manifest(
            schema_version=99,  # arbitrary
            upstream_base="https://x",
            fetched_at="2026-07-07T00:00:00Z",
            module_count=0,
            total_bytes=0,
            modules=(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            write_manifest(manifest, path=path)
            loaded = load_manifest(path=path)
            self.assertEqual(loaded.schema_version, 99)

    def test_json_is_human_readable(self):
        # Pretty-printed with sort_keys for stable diffs
        manifest = Manifest(
            schema_version=1,
            upstream_base="https://x",
            fetched_at="t",
            module_count=1,
            total_bytes=10,
            modules=(_sample_entry(),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MANIFEST.json"
            write_manifest(manifest, path=path)
            raw = path.read_text(encoding="utf-8")
            # Pretty-printed = multiple lines
            self.assertGreater(raw.count("\n"), 5)
            # JSON parseable
            data = json.loads(raw)
            self.assertEqual(data["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

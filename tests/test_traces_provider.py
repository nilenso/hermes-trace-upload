from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import traces_provider as provider  # noqa: E402


class TracesProviderTests(unittest.TestCase):
    def test_upsert_shares_unshared_trace(self):
        calls = []
        with patch.object(provider, "_run", side_effect=lambda _config, args: calls.append(args) or {"ok": True}):
            result = provider.TracesComCliProvider(dict(provider.DEFAULT_CONFIG)).upsert(
                provider.TraceRecord("session-1", "/tmp/project", 1, "")
            )
        self.assertEqual("shared", result["action"])
        self.assertEqual([["share", "--trace-id", "session-1", "--visibility", "private", "--json"]], calls)

    def test_upsert_refreshes_existing_shared_trace(self):
        calls = []
        with patch.object(provider, "_run", side_effect=lambda _config, args: calls.append(args) or {"ok": True}):
            result = provider.TracesComCliProvider(dict(provider.DEFAULT_CONFIG)).upsert(
                provider.TraceRecord("session-1", "/tmp/project", 1, "https://traces.com/s/abc")
            )
        self.assertEqual("refreshed", result["action"])
        self.assertEqual([["refresh", "--trace-id", "session-1", "--json"]], calls)

    def test_explicit_id_is_not_limited_to_current_directory(self):
        trace = provider.TraceRecord("remote-session", "/other/workspace", 2, "")

        class FakeProvider:
            def list(self):
                return [trace]
            def upsert(self, item):
                self.item = item
                return {"action": "shared", "trace_id": item.id}

        fake = FakeProvider()
        with patch.object(provider, "provider_from_config", return_value=fake):
            result = provider.upload_current_trace("/tmp/current", "remote-session")
        self.assertIs(trace, fake.item)
        self.assertEqual("remote-session", result["trace_id"])

    def test_desktop_path_falls_back_to_pnpm_global_cli(self):
        with patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}, clear=False):
            resolved = provider._executable(dict(provider.DEFAULT_CONFIG))
        self.assertEqual(str(Path.home() / ".local/share/pnpm/traces"), resolved)

    def test_save_config_rejects_unknown_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(provider, "config_path", return_value=Path(temp) / "plugin.json"):
                with self.assertRaisesRegex(provider.TraceProviderError, "Unsupported provider"):
                    provider.save_config({"provider": "other"})


if __name__ == "__main__":
    unittest.main()

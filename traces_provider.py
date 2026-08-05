"""Provider boundary and Traces.com CLI implementation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from hermes_constants import get_hermes_home

DEFAULT_CONFIG = {
    "provider": "traces.com-cli",
    "cli_path": "traces",
    "namespace": "",
    "visibility": "private",
}


class TraceProviderError(RuntimeError):
    """Recoverable provider error suitable for chat or UI display."""


def config_path() -> Path:
    return get_hermes_home() / "traces" / "plugin.json"


def load_config() -> dict[str, str]:
    config = dict(DEFAULT_CONFIG)
    try:
        stored = json.loads(config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceProviderError(f"Could not read Traces plugin config: {exc}") from exc
    if not isinstance(stored, dict):
        raise TraceProviderError("Traces plugin config must be a JSON object.")
    for key in config:
        if isinstance(stored.get(key), str):
            config[key] = stored[key]
    return config


def save_config(updates: dict[str, Any]) -> dict[str, str]:
    config = load_config()
    config.update({key: updates.get(key, config[key]) for key in DEFAULT_CONFIG})
    if config["provider"] != "traces.com-cli":
        raise TraceProviderError("Unsupported provider. Only traces.com CLI is currently available.")
    if not isinstance(config["cli_path"], str) or not config["cli_path"].strip() or "\x00" in config["cli_path"]:
        raise TraceProviderError("CLI path must be a non-empty executable name or absolute path.")
    if not isinstance(config["namespace"], str) or any(c.isspace() for c in config["namespace"]) or "\x00" in config["namespace"]:
        raise TraceProviderError("Namespace must not contain whitespace.")
    if config["visibility"] not in {"private", "direct", "public"}:
        raise TraceProviderError("Visibility must be private, direct, or public.")
    config["cli_path"] = config["cli_path"].strip()
    config["namespace"] = config["namespace"].strip().lstrip("@")
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = handle.name
    os.replace(temporary, target)
    return config


def _executable(config: dict[str, str]) -> str:
    candidate = config["cli_path"]
    if os.path.isabs(candidate):
        if Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    else:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise TraceProviderError(
        f"Traces CLI '{candidate}' was not found. Add its bin directory to desktop.backend_path or set an absolute executable path in Traces settings."
    )


def _run(config: dict[str, str], args: Iterable[str], timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [_executable(config), *args], stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TraceProviderError(f"Traces CLI timed out after {timeout}s.") from exc
    stdout, stderr = (result.stdout or "").strip(), (result.stderr or "").strip()
    if result.returncode:
        raise TraceProviderError(f"Traces CLI failed: {stderr or stdout or f'exit code {result.returncode}'}")
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        raise TraceProviderError(f"Traces CLI returned invalid JSON: {stdout[:500]}") from exc
    if not isinstance(payload, dict) or payload.get("ok") is False:
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        raise TraceProviderError(message or "Traces CLI reported an error.")
    return payload


@dataclass(frozen=True)
class TraceRecord:
    id: str
    directory: str
    timestamp: float
    shared_url: str = ""


class TracesComCliProvider:
    id = "traces.com-cli"

    def __init__(self, config: dict[str, str]):
        self.config = config

    def status(self) -> dict[str, str]:
        return {"provider": self.id, "resolved_cli": _executable(self.config), "cli_path": self.config["cli_path"]}

    def list(self) -> list[TraceRecord]:
        rows = _run(self.config, ["list", "--all", "--json"]).get("data", {}).get("traces", [])
        if not isinstance(rows, list):
            raise TraceProviderError("Traces CLI returned an invalid trace list.")
        return sorted([
            TraceRecord(str(row["id"]), str(row.get("directory") or ""), float(row.get("timestamp") or 0), str(row.get("sharedUrl") or ""))
            for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)
        ], key=lambda trace: trace.timestamp, reverse=True)

    def upsert(self, trace: TraceRecord) -> dict[str, Any]:
        # `refresh` targets the existing shared trace ID, so re-running the command
        # syncs that same remote trace instead of making a duplicate.
        if trace.shared_url:
            payload, action = _run(self.config, ["refresh", "--trace-id", trace.id, "--json"]), "refreshed"
        else:
            args = ["share"]
            if self.config["namespace"]:
                args.append(f"@{self.config['namespace']}")
            args += ["--trace-id", trace.id, "--visibility", self.config["visibility"], "--json"]
            payload, action = _run(self.config, args), "shared"
        return {"action": action, "trace_id": trace.id, "payload": payload}


def provider_from_config(config: dict[str, str] | None = None) -> TracesComCliProvider:
    config = config or load_config()
    if config["provider"] != "traces.com-cli":
        raise TraceProviderError(f"Unsupported traces provider: {config['provider']}")
    return TracesComCliProvider(config)


def upload_current_trace(cwd: str, trace_id: str | None = None) -> dict[str, Any]:
    traces = provider_from_config().list()
    if trace_id:
        trace = next((item for item in traces if item.id == trace_id), None)
    else:
        target = str(Path(cwd).expanduser().resolve())
        trace = next((item for item in traces if str(Path(item.directory).expanduser().resolve()) == target), None)
    if trace is None:
        scope = f"trace '{trace_id}'" if trace_id else f"a trace for {Path(cwd).resolve()}"
        raise TraceProviderError(f"Could not find {scope}. Pass an exact trace ID or open the target session.")
    return provider_from_config().upsert(trace)

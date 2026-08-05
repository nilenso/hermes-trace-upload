"""Hermes Traces upload plugin."""
from __future__ import annotations

import shlex
from pathlib import Path

from .traces_provider import TraceProviderError, load_config, provider_from_config, upload_current_trace

_HELP = """/trace-upload [trace-id]

Upload or refresh a trace through the configured host. Without an ID, the command
selects the newest trace in the active workspace. Desktop uses its active session
ID, so it works for remote and local trace storage alike.

`/trace-upload status` verifies the provider and CLI path.
`/trace-upload <trace-id>` uploads one exact trace."""


def _cwd(ctx) -> str:
    cli = getattr(getattr(ctx, "_manager", None), "_cli_ref", None)
    return str(getattr(cli, "cwd", None) or getattr(cli, "_cwd", None) or Path.cwd())


def _handle(ctx, raw_args: str) -> str:
    try:
        args = shlex.split(raw_args)
    except ValueError as exc:
        return f"Trace upload error: invalid arguments ({exc})."
    if args and args[0] in {"help", "--help"}:
        return _HELP
    if args == ["status"]:
        try:
            config = load_config()
            status = provider_from_config(config).status()
            return f"Traces upload ready\nProvider: traces.com CLI\nCLI: {status['resolved_cli']}\nNamespace: {config['namespace'] or '(active CLI namespace)'}\nVisibility: {config['visibility']}"
        except TraceProviderError as exc:
            return f"Trace upload is not ready: {exc}"
    if len(args) > 1 or (args and args[0].startswith("-")):
        return _HELP
    try:
        outcome = upload_current_trace(_cwd(ctx), args[0] if args else None)
    except TraceProviderError as exc:
        return f"Trace upload failed: {exc}"
    return f"Trace {outcome['action']}: {outcome['trace_id']}"


def register(ctx) -> None:
    ctx.register_command("trace-upload", lambda raw: _handle(ctx, raw), description="Upload or refresh the current trace.", args_hint="[trace-id|status]")

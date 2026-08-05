"""Desktop backend for the Traces plugin, mounted at /api/plugins/traces/."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Dashboard APIs are imported as standalone modules. Load the provider module
# from the plugin root explicitly rather than relying on package import order.
_root = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hermes_traces_provider", _root / "traces_provider.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("Could not load Traces provider module")
_provider = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _provider
_spec.loader.exec_module(_provider)

router = APIRouter()


class ConfigBody(BaseModel):
    provider: str = "traces.com-cli"
    cli_path: str = "traces"
    namespace: str = ""
    visibility: str = "private"


class UploadBody(BaseModel):
    cwd: str
    trace_id: Optional[str] = None


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/config")
def get_config():
    try:
        config = _provider.load_config()
        status = _provider.provider_from_config(config).status()
        return {"config": config, "status": status}
    except _provider.TraceProviderError as exc:
        return {"config": _provider.load_config(), "status_error": str(exc)}


@router.put("/config")
def put_config(body: ConfigBody):
    try:
        config = _provider.save_config(body.model_dump())
        status = _provider.provider_from_config(config).status()
        return {"config": config, "status": status}
    except _provider.TraceProviderError as exc:
        raise _error(exc)


@router.post("/upload")
def upload(body: UploadBody):
    try:
        return _provider.upload_current_trace(body.cwd, body.trace_id)
    except _provider.TraceProviderError as exc:
        raise _error(exc)

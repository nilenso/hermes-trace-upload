#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
HERMES_HOME=${HERMES_HOME:-"$HOME/.hermes"}
mkdir -p "$HERMES_HOME/plugins" "$HERMES_HOME/desktop-plugins"
ln -sfn "$ROOT" "$HERMES_HOME/plugins/traces"
ln -sfn "$ROOT/desktop-plugin" "$HERMES_HOME/desktop-plugins/traces"

# Capture the caller's fully resolved executable once. The desktop backend may
# start with a different (minimal) PATH, so storing an absolute path is more
# portable than assuming pnpm, npm, nvm, Volta, Homebrew, or a system package
# manager uses a particular bin directory. Never overwrite a user's settings.
CONFIG="$HERMES_HOME/traces/plugin.json"
if [ ! -f "$CONFIG" ]; then
  TRACE_CLI=$(command -v traces || true)
  if [ -n "$TRACE_CLI" ]; then
    mkdir -p "$(dirname "$CONFIG")"
    python - "$CONFIG" "$TRACE_CLI" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(json.dumps({
    "provider": "traces.com-cli",
    "cli_path": sys.argv[2],
    "namespace": "",
    "visibility": "private",
}, indent=2) + "\n", encoding="utf-8")
PY
    echo "Configured Traces CLI: $TRACE_CLI"
  else
    echo "Warning: 'traces' is not on this shell's PATH. Configure an absolute executable path in Traces settings."
  fi
fi

hermes plugins enable traces
echo "Installed Traces plugin. Restart the gateway to mount the settings API, then reload desktop plugins."

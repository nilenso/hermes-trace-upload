#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
HERMES_HOME=${HERMES_HOME:-"$HOME/.hermes"}
mkdir -p "$HERMES_HOME/plugins" "$HERMES_HOME/desktop-plugins"
ln -sfn "$ROOT" "$HERMES_HOME/plugins/traces"
ln -sfn "$ROOT/desktop-plugin" "$HERMES_HOME/desktop-plugins/traces"

hermes plugins enable traces
echo "Installed Traces plugin. Configure desktop.backend_path if the Desktop backend cannot resolve 'traces', then restart Hermes Desktop."

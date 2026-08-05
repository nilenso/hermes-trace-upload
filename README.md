# Hermes Traces Upload

A standalone Hermes plugin that discovers the current Hermes trace and syncs it
with a configurable trace-host provider.

## Current provider

| Provider | Configuration | Upload behavior |
| --- | --- | --- |
| **traces.com CLI** | CLI executable on the gateway's `PATH` (or an absolute executable path), optional namespace and visibility | First upload calls `traces share --trace-id …`; later uploads call `traces refresh --trace-id …` for the same stable trace ID. |

The provider boundary lives in `traces_provider.py`. New hosts only need to
implement trace listing and upsert behavior; the slash command and desktop UI
remain provider-agnostic.

## Install

```bash
git clone https://github.com/nilenso/hermes-trace-upload.git
cd hermes-trace-upload
./install.sh
# restart the Hermes gateway, then Cmd/Ctrl+K → Reload desktop plugins
```

`install.sh` links this repository into both `$HERMES_HOME/plugins/traces` and
`$HERMES_HOME/desktop-plugins/traces`, then enables the Python plugin. When
`traces` is available in the shell that runs the installer, it also records the
**absolute resolved executable path** in the plugin config. This prevents a
minimal desktop or service `PATH` from breaking npm, pnpm, nvm, Volta,
Homebrew, or system-package installations. Existing plugin settings are never
overwritten. The backend routes require a gateway restart because plugin routes
are mounted at startup.

## Configure and use

1. Open **Traces** from the desktop sidebar.
2. Choose **traces.com CLI** (the only provider today), set the executable
   (normally `traces`), then optionally set a namespace and visibility.
3. Click **Upload active trace**. The desktop passes its active Hermes session
   ID, so it locates that exact trace whether the data originated locally or was
   synced from a remote source.

In chat, use:

```text
/trace-upload <trace-id>
/trace-upload status
```

The CLI/gateway slash-command API does not currently expose a per-command
session ID to third-party plugins. Therefore `/trace-upload <trace-id>` is the
precise portable form; `/trace-upload status` diagnoses the configured CLI.

## Configuration

Non-secret settings are stored in `$HERMES_HOME/traces/plugin.json`:

```json
{
  "provider": "traces.com-cli",
  "cli_path": "traces",
  "namespace": "",
  "visibility": "private"
}
```

Authentication stays owned by the Traces CLI (`traces login`) rather than being
stored by this plugin.

#!/bin/bash
# Export FDA_PLUGIN_ROOT so all bash commands in the session can locate bundled scripts.
# CLAUDE_PLUGIN_ROOT is substituted by Claude Code in the hooks.json command field,
# so this script's path resolves correctly. We then derive the plugin root from our
# own location and write it to CLAUDE_ENV_FILE.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo "export FDA_PLUGIN_ROOT=\"$PLUGIN_ROOT\"" >> "$CLAUDE_ENV_FILE"
fi

exit 0

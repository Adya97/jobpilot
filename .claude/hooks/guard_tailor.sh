#!/bin/bash
# PostToolUse hook: run the anti-invention guard whenever a tailor.yaml is written.
# Exit 2 sends the guard's findings back to Claude so it fixes the file.
f=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
case "$f" in
  */tailor.yaml) python3 "$CLAUDE_PROJECT_DIR/scripts/guard.py" "$f" >/dev/null || exit 2 ;;
esac
exit 0

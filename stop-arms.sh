#!/usr/bin/env bash
# Usage:
#   stop-arms.sh              → stop EVERYTHING (watcher + arms), fail pending tasks, close tmux
#   stop-arms.sh PROJ CH      → stop only that channel's arm and fail its pending tasks
#   stop-arms.sh --pending    → kill running arms + fail pending tasks (watcher and tmux stay up)

BASE="$(cd "$(dirname "$0")" && pwd)"
SESSION="$(cd "$BASE" && python3 -c 'from config import CONFIG; print(CONFIG["tmux_session"])' 2>/dev/null || echo arms)"
# Arm processes are recognised by the first words of their prompt (current and legacy wording).
ARM_PATTERN='ARM (for project|del progetto)'

if [ "$(uname -s)" = Darwin ]; then
    stop_watcher()  { launchctl bootout "gui/$(id -u)/com.brain-arm.watcher" 2>/dev/null; }
    START_HINT="launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.brain-arm.watcher.plist"
else
    stop_watcher()  { systemctl --user stop brain-arm-watcher.service 2>/dev/null; }
    START_HINT="systemctl --user start brain-arm-watcher"
fi

# fail_pending [PROJ CH] — fail pending tasks (all, or one channel's), under the shared lock
fail_pending() {
    python3 - "$BASE" "$@" <<'EOF'
import sys
from datetime import datetime
sys.path.insert(0, sys.argv[1])
from store import DATA_DIR, update_json
proj, ch = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else (None, None)
now = datetime.now().isoformat(timespec="seconds")
changed = 0
with update_json(DATA_DIR / "tasks.json", []) as tasks:
    for t in tasks:
        if t["status"] == "pending" and (proj is None or (
                t.get("project", "default") == proj and t.get("channel", "default") == ch)):
            t["status"] = "failed"
            t["result"] = "cancelled manually with stop-arms.sh"
            t["updated_at"] = now
            changed += 1
print(f"  {changed} pending task(s) marked as failed" + (f" for {proj}:{ch}." if proj else "."))
EOF
}

if [ "$1" = "--pending" ]; then
    echo "Killing running arms..."
    pkill -f "$ARM_PATTERN" 2>/dev/null && echo "  arm processes killed." || echo "  no arm found."
    echo "Failing pending tasks..."
    fail_pending
    echo "Done. (watcher and tmux are still running)"

elif [ $# -eq 0 ]; then
    echo "=== FULL STOP ==="
    echo "1. Stopping the watcher..."
    stop_watcher && echo "  watcher stopped." || true
    pkill -f watcher.py 2>/dev/null || true

    echo "2. Killing every running arm..."
    pkill -f "$ARM_PATTERN" 2>/dev/null && echo "  arm processes killed." || echo "  no arm found."

    echo "3. Failing all pending tasks..."
    fail_pending

    echo "4. Closing tmux session '$SESSION'..."
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "  tmux closed." || echo "  tmux session not found."

    echo "=== Everything stopped. Restart the watcher with: $START_HINT ==="

else
    PROJ="$1"
    CH="$2"
    if [ -z "$CH" ]; then
        echo "Usage: stop-arms.sh PROJECT CHANNEL"
        exit 1
    fi
    WNAME="${PROJ}:${CH}"
    echo "Stopping arm $WNAME..."
    pkill -f "\"${PROJ}\", chat \"${CH}\"" 2>/dev/null || true
    WID=$(tmux list-windows -t "$SESSION" -F '#{window_id} #{window_name}' 2>/dev/null | awk -v n="$WNAME" '$2==n{print $1}')
    if [ -n "$WID" ]; then
        for w in $WID; do tmux kill-window -t "$w"; done
        echo "  tmux window $WNAME closed."
    else
        echo "  window $WNAME not found."
    fi
    echo "Failing pending tasks of $WNAME..."
    fail_pending "$PROJ" "$CH"
    echo "Done."
fi

#!/usr/bin/env bash
# Utilizzo:
#   stop-arms.sh              → ferma TUTTO (arm + watcher) e pulisce pending
#   stop-arms.sh PROJ CH      → ferma solo l'arm di quel canale
#   stop-arms.sh --pending    → killa arm attivi + marca pending come failed (NO watcher, NO tmux)

SESSION="arms"
BASE="$(cd "$(dirname "$0")" && pwd)"

# fail_pending [PROJ CH] — marca failed i task pending (tutti, o solo di un canale), con lock
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
            t["result"] = "annullato manualmente con stop-arms.sh"
            t["updated_at"] = now
            changed += 1
print(f"  {changed} task pending marcati come failed" + (f" per {proj}:{ch}." if proj else "."))
EOF
}
fail_pending_all() { fail_pending; }
fail_pending_channel() { fail_pending "$1" "$2"; }

if [ "$1" = "--pending" ]; then
    echo "Killo arm in corso..."
    pkill -f "ARM del progetto" 2>/dev/null && echo "  processi arm killati." || echo "  nessun arm trovato."
    echo "Marco task pending come failed..."
    fail_pending_all
    echo "Fatto. (watcher e tmux restano attivi)"

elif [ $# -eq 0 ]; then
    echo "=== STOP TOTALE ==="
    echo "1. Fermo il watcher..."
    systemctl --user stop brain-arm-watcher.service 2>/dev/null && echo "  watcher fermato." || true
    pkill -f watcher.py 2>/dev/null || true

    echo "2. Killo tutti gli arm in corso..."
    pkill -f "ARM del progetto" 2>/dev/null && echo "  processi arm killati." || echo "  nessun arm trovato."

    echo "3. Marco tutti i task pending come failed..."
    fail_pending_all

    echo "4. Chiudo sessione tmux '$SESSION'..."
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "  tmux chiuso." || echo "  tmux non trovato."

    echo "=== Tutto fermato. ==="

else
    PROJ="$1"
    CH="$2"
    if [ -z "$CH" ]; then
        echo "Uso: stop-arms.sh PROGETTO CANALE"
        exit 1
    fi
    WNAME="${PROJ}:${CH}"
    echo "Fermando arm $WNAME..."
    pkill -f "ARM del progetto \"${PROJ}\", chat \"${CH}\"" 2>/dev/null || true
    WID=$(tmux list-windows -t "$SESSION" -F '#{window_id} #{window_name}' 2>/dev/null | awk -v n="$WNAME" '$2==n{print $1}')
    if [ -n "$WID" ]; then
        for w in $WID; do tmux kill-window -t "$w"; done
        echo "  finestra tmux $WNAME chiusa."
    else
        echo "  finestra $WNAME non trovata."
    fi
    echo "Marcando task pending di $WNAME come failed..."
    fail_pending_channel "$PROJ" "$CH"
    echo "Fatto."
fi

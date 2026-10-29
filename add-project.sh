#!/usr/bin/env bash
# Map a project (or a single channel) to its repository folder.
#   ./add-project.sh webshop ~/code/webshop                 → every channel of "webshop" works in that folder
#   ./add-project.sh data-platform:ingestion ~/code/ingest  → only that channel uses a different folder
#   ./add-project.sh --list                                 → show the current map
set -euo pipefail
PROJECTS="$HOME/.brain-arm-projects.json"
[ -f "$PROJECTS" ] || echo '{}' > "$PROJECTS"

if [ "${1:-}" = "--list" ] || [ $# -eq 0 ]; then
  echo "Projects map ($PROJECTS):"
  python3 -c 'import json,sys; [print(f"  {k:30} → {v}") for k, v in json.load(open(sys.argv[1])).items()] or None' "$PROJECTS"
  [ $# -eq 0 ] && echo && echo "Usage: ./add-project.sh <project>[:<channel>] <folder>"
  exit 0
fi

[ $# -eq 2 ] || { echo "Usage: ./add-project.sh <project>[:<channel>] <folder>"; exit 1; }
KEY="$1"
FOLDER="$(cd "${2/#\~/$HOME}" 2>/dev/null && pwd)" || { echo "STOP: folder '$2' does not exist."; exit 1; }
[[ "$KEY" =~ ^[a-z0-9][a-z0-9._-]*(:[a-z0-9][a-z0-9._-]*)?$ ]] \
  || { echo "STOP: use lowercase names with letters, digits, '-', '.', '_' (e.g. webshop or webshop:checkout)."; exit 1; }
[[ "$KEY" == default* ]] && { echo "STOP: 'default' is reserved."; exit 1; }

python3 - "$PROJECTS" "$KEY" "$FOLDER" <<'EOF'
import json, sys
path, key, folder = sys.argv[1:4]
data = json.load(open(path))
old = data.get(key)
data[key] = folder
json.dump(data, open(path, "w"), indent=2)
print(f"[ok] {key} → {folder}" + (f"   (was {old})" if old and old != folder else ""))
EOF

echo
echo "If you haven't yet, trust this folder in Claude Code once (otherwise the arm stops on that prompt):"
echo "    cd \"$FOLDER\" && claude      → accept the trust question, then type /exit"
echo "In the brain chat use:  project=\"${KEY%%:*}\"$( [[ "$KEY" == *:* ]] && echo "  channel=\"${KEY#*:}\"" )"

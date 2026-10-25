#!/usr/bin/env bash
# brain-arm installer (WSL2 / Linux). Safe to re-run: it never overwrites your projects map or local config.
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
say() { printf '\n== %s\n' "$*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

say "Checking prerequisites"
for cmd in python3 tmux claude systemctl git; do
  command -v "$cmd" >/dev/null 2>&1 || fail "'$cmd' not found. Install it and re-run."
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || fail "Python >= 3.10 required"
python3 -m venv --help >/dev/null 2>&1 || fail "python3-venv missing: sudo apt install python3-venv"
systemctl --user show-environment >/dev/null 2>&1 \
  || fail "systemd user session not available. In /etc/wsl.conf set [boot] systemd=true, then run 'wsl --shutdown' from Windows."
echo "Claude Code $(claude --version 2>/dev/null | head -1)"

say "Python environment"
[ -d "$BASE/.venv" ] || python3 -m venv "$BASE/.venv"
"$BASE/.venv/bin/pip" install --quiet --upgrade pip
"$BASE/.venv/bin/pip" install --quiet -r "$BASE/requirements.txt"
mkdir -p "$BASE/data" "$BASE/logs"
echo "ok: $BASE/.venv"

say "Projects map"
PROJECTS="$HOME/.brain-arm-projects.json"
if [ -f "$PROJECTS" ]; then
  echo "kept existing $PROJECTS"
else
  cp "$BASE/examples/brain-arm-projects.example.json" "$PROJECTS"
  echo "created $PROJECTS from the example: edit it with your real project folders"
fi

say "Watcher service (systemd --user)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
sed "s|@BASE@|$BASE|g" "$BASE/systemd/brain-arm-watcher.service.template" > "$UNIT_DIR/brain-arm-watcher.service"
systemctl --user daemon-reload
systemctl --user enable --now brain-arm-watcher.service
echo "watcher: $(systemctl --user is-active brain-arm-watcher.service)"

say "Claude Desktop (Windows)"
cat <<EOF
Add this entry under "mcpServers" in %APPDATA%\\Claude\\claude_desktop_config.json,
then quit Claude Desktop from the tray icon and reopen it:

    "brain-arm": {
      "command": "wsl",
      "args": ["$BASE/.venv/bin/python", "$BASE/server.py"]
    }

(If brain-arm is not in your default WSL distro, use: "args": ["-d", "<distro>", ...])
EOF

say "Done. Next steps"
cat <<EOF
1. Edit $PROJECTS (project key -> folder; "project:channel" keys override a single channel).
2. Open each project folder once with 'claude' and accept the folder-trust prompt.
3. Paste docs/brain-instructions.md into your Claude Desktop project instructions.
4. Watch the queue:  watch -n3 python3 $BASE/status.py      Live arms:  tmux attach -t arms
EOF

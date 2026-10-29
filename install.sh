#!/usr/bin/env bash
# brain-arm installer for Windows (inside WSL2), macOS and Linux.
#   ./install.sh --check   only checks your machine and tells you what is missing (changes nothing)
#   ./install.sh           installs (safe to re-run: never overwrites your projects map or local config)
set -uo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
CHECK_ONLY=0; [ "${1:-}" = "--check" ] && CHECK_ONLY=1
OK="  [ok]"; NO="  [missing]"
say()  { printf '\n== %s\n' "$*"; }
die()  { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- platform
case "$(uname -s)" in
  Darwin) PLATFORM=macos ;;
  Linux)  if grep -qi microsoft /proc/version 2>/dev/null; then PLATFORM=wsl; else PLATFORM=linux; fi ;;
  *)      die "unsupported system $(uname -s). Use macOS, or Windows with WSL2." ;;
esac
say "System: $PLATFORM   (brain-arm folder: $BASE)"

# ---------------------------------------------------------------- prerequisites
say "Checking prerequisites"
missing=0
need() {  # need <command> <how to install>
  if command -v "$1" >/dev/null 2>&1; then echo "$OK $1"; else echo "$NO $1  →  install with: $2"; missing=1; fi
}
if [ "$PLATFORM" = macos ]; then
  command -v brew >/dev/null 2>&1 && echo "$OK brew" || echo "  [tip] Homebrew not found: see https://brew.sh (makes the installs below one command)"
  PKG="brew install"
  need python3 "$PKG python"
  need tmux    "$PKG tmux"
  need git     "xcode-select --install"
  need watch   "$PKG watch"
else
  PKG="sudo apt install -y"
  need python3 "$PKG python3 python3-venv"
  need tmux    "$PKG tmux"
  need git     "$PKG git"
  need watch   "$PKG procps"
fi
need claude "curl -fsSL https://claude.ai/install.sh | bash   (then open a new terminal and run 'claude' once to sign in)"

if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then echo "$OK python3 >= 3.10"
  else echo "$NO python3 >= 3.10 (you have $(python3 -V 2>&1))"; missing=1; fi
  if python3 -m venv --help >/dev/null 2>&1; then echo "$OK python3 venv"
  else echo "$NO python3 venv  →  install with: $PKG python3-venv"; missing=1; fi
fi
if command -v claude >/dev/null 2>&1; then echo "       Claude Code $(claude --version 2>/dev/null | head -1)"; fi

if [ "$PLATFORM" != macos ]; then
  if systemctl --user show-environment >/dev/null 2>&1; then echo "$OK systemd (user services)"
  else
    missing=1
    if [ "$PLATFORM" = wsl ]; then
      echo "$NO systemd  →  run:  printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf"
      echo "                    then in Windows PowerShell:  wsl --shutdown   and reopen Ubuntu"
    else
      echo "$NO systemd user session (needed to start the watcher automatically)"
    fi
  fi
fi

if [ "$PLATFORM" = linux ]; then
  echo
  echo "  NOTE: Claude Desktop (the brain) is officially available for macOS and Windows only."
  echo "        On Linux the watcher and the arms work, but you need another MCP client as the brain."
fi

[ "$missing" -eq 0 ] || die "install the [missing] items above, then run ./install.sh again."
if [ "$CHECK_ONLY" -eq 1 ]; then say "Check passed: run ./install.sh to install."; exit 0; fi

# ---------------------------------------------------------------- python env
say "Python environment"
[ -d "$BASE/.venv" ] || python3 -m venv "$BASE/.venv" || die "could not create $BASE/.venv"
"$BASE/.venv/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
"$BASE/.venv/bin/pip" install --quiet -r "$BASE/requirements.txt" || die "pip install failed (network/proxy?)"
mkdir -p "$BASE/data" "$BASE/logs"
echo "$OK $BASE/.venv"
chmod +x "$BASE"/*.sh 2>/dev/null

# ---------------------------------------------------------------- projects map
say "Projects map"
PROJECTS="$HOME/.brain-arm-projects.json"
if [ -f "$PROJECTS" ]; then echo "$OK kept your existing $PROJECTS"
else echo '{}' > "$PROJECTS"; echo "$OK created an empty $PROJECTS (add projects with ./add-project.sh)"; fi

# ---------------------------------------------------------------- watcher service
say "Watcher service (starts automatically)"
if [ "$PLATFORM" = macos ]; then
  PLIST="$HOME/Library/LaunchAgents/com.brain-arm.watcher.plist"
  mkdir -p "$(dirname "$PLIST")"
  PATH_VALUE="$(dirname "$(command -v claude)"):$(dirname "$(command -v tmux)"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  sed -e "s|@BASE@|$BASE|g" -e "s|@PATH@|$PATH_VALUE|g" -e "s|@HOME@|$HOME|g" \
      "$BASE/launchd/com.brain-arm.watcher.plist.template" > "$PLIST"
  launchctl bootout "gui/$(id -u)/com.brain-arm.watcher" >/dev/null 2>&1
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || die "launchctl could not load $PLIST"
  sleep 2
  launchctl print "gui/$(id -u)/com.brain-arm.watcher" 2>/dev/null | grep -q "state = running" \
    && echo "$OK watcher running (launchd)" || echo "  [warn] watcher not running yet: see $BASE/logs/watcher.stderr.log"
else
  UNIT_DIR="$HOME/.config/systemd/user"
  mkdir -p "$UNIT_DIR"
  sed "s|@BASE@|$BASE|g" "$BASE/systemd/brain-arm-watcher.service.template" > "$UNIT_DIR/brain-arm-watcher.service"
  systemctl --user daemon-reload
  systemctl --user enable --now brain-arm-watcher.service >/dev/null 2>&1
  [ "$(systemctl --user is-active brain-arm-watcher.service)" = active ] \
    && echo "$OK watcher running (systemd)" || echo "  [warn] watcher not running: systemctl --user status brain-arm-watcher"
fi

# ---------------------------------------------------------------- Claude Desktop
say "Claude Desktop connection"
case "$PLATFORM" in
  wsl)
    APPDATA_WIN="$(cd /mnt/c 2>/dev/null && cmd.exe /c 'echo %APPDATA%' 2>/dev/null | tr -d '\r')"
    DESKTOP_CFG="$( [ -n "$APPDATA_WIN" ] && wslpath -u "$APPDATA_WIN" 2>/dev/null)/Claude/claude_desktop_config.json"
    ENTRY="{\"command\": \"wsl\", \"args\": [\"$BASE/.venv/bin/python\", \"$BASE/server.py\"]}"
    WHERE="%APPDATA%\\Claude\\claude_desktop_config.json" ;;
  macos)
    DESKTOP_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    ENTRY="{\"command\": \"$BASE/.venv/bin/python\", \"args\": [\"$BASE/server.py\"]}"
    WHERE="~/Library/Application Support/Claude/claude_desktop_config.json" ;;
  linux)
    DESKTOP_CFG=""
    ENTRY="{\"command\": \"$BASE/.venv/bin/python\", \"args\": [\"$BASE/server.py\"]}"
    WHERE="your MCP client's configuration" ;;
esac
echo "Entry to add under \"mcpServers\" in $WHERE:"
echo
echo "    \"brain-arm\": $ENTRY"
echo
if [ -n "$DESKTOP_CFG" ] && [ -t 0 ]; then
  read -r -p "Add it to Claude Desktop for you now (a backup is made)? [y/N] " answer
  if [ "${answer:-N}" = y ] || [ "${answer:-N}" = Y ]; then
    "$BASE/.venv/bin/python" - "$DESKTOP_CFG" "$ENTRY" <<'EOF' || echo "  [warn] could not edit it: add the entry by hand."
import json, pathlib, shutil, sys
path, entry = pathlib.Path(sys.argv[1]), json.loads(sys.argv[2])
text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
data = json.loads(text) if text.strip() else {}
if path.exists():
    shutil.copy2(path, str(path) + ".bak-brain-arm")
data.setdefault("mcpServers", {})["brain-arm"] = entry
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  [ok] brain-arm added to {path}" + (" (backup: .bak-brain-arm)" if text else ""))
EOF
  fi
fi

# ---------------------------------------------------------------- next steps
say "Installed. Next steps (details in INSTALL.md)"
cat <<EOF
1. Quit Claude Desktop completely (tray / menu bar icon → Quit) and open it again.
2. Add your projects:      ./add-project.sh <project> <folder>
3. Trust each folder once: cd <folder> && claude    → accept the trust prompt, then type /exit
4. Paste docs/brain-instructions.md into your Claude Desktop project instructions.
5. Watch it work:          watch -n3 python3 $BASE/status.py      and      tmux attach -t arms
EOF

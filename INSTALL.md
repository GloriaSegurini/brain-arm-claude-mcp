# Installing brain-arm

About 20 minutes. Every step has the exact command to copy and **what you should see** — if you see
something else, stop and check [Common problems](#common-problems).

## Which guide?

| Your computer | Guide |
|---|---|
| Windows 10/11 | [A. Windows](#a-windows-with-wsl2) — brain-arm runs inside WSL2 (a Linux system built into Windows) |
| Mac | [B. macOS](#b-macos) |
| Linux | Not supported as a whole: Claude Desktop (the brain) is officially available only for Windows and macOS. The watcher and arms do run on Linux (`./install.sh` works) if you have another MCP client to act as the brain. |

**Before you start, you need:** a Claude account with access to **Claude Desktop** and **Claude Code**,
an internet connection, and (Windows) administrator rights to install WSL.

> **How to paste in a terminal:** Windows/Ubuntu terminal → right-click or `Ctrl+Shift+V`; Mac Terminal → `Cmd+V`.
> Paste one command at a time and press Enter.

---

## A. Windows (with WSL2)

### A1. Install WSL2 with Ubuntu
Open **PowerShell as administrator** (Start → type *PowerShell* → right-click → *Run as administrator*):
```powershell
wsl --install -d Ubuntu-24.04
```
Restart the PC when asked. Then open **Ubuntu** from the Start menu and choose a Linux username and password
(the password is not shown while you type — that's normal).

✅ You should see a prompt like `yourname@PC:~$`.
*Already have WSL?* In PowerShell, `wsl -l -v` must show your Ubuntu with `VERSION 2`.

> From here on, **every command goes in the Ubuntu terminal** unless it says PowerShell.

### A2. Turn on systemd (lets brain-arm start automatically)
```bash
printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf
```
Then in **PowerShell** (normal, not admin): `wsl --shutdown`, and reopen Ubuntu.

✅ `systemctl --user is-system-running` prints `running` (or `degraded` — also fine).

### A3. Install the tools
```bash
sudo apt update && sudo apt install -y python3 python3-venv tmux git procps
```
✅ It ends without red `E:` errors.

### A4. Install Claude Code (inside Ubuntu) and sign in
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Close and reopen Ubuntu, then:
```bash
claude --version
claude
```
Follow the sign-in link it shows, then type `/exit`.
✅ `claude --version` prints a version number.

### A5. Install Claude Desktop (on Windows)
Download it from the official Claude download page, install it and sign in.

### A6. Download brain-arm
```bash
git clone https://github.com/GloriaSegurini/brain-arm-claude-mcp.git ~/brain-arm
cd ~/brain-arm
```
✅ `ls` shows `install.sh`, `server.py`, `watcher.py`…

### A7. Check, then install
```bash
./install.sh --check
```
✅ Every line says `[ok]`. If something says `[missing]`, run the command printed next to it, then repeat.
```bash
./install.sh
```
When it asks **"Add it to Claude Desktop for you now?"** type `y`.
✅ It ends with `Installed. Next steps` and shows `[ok] watcher running (systemd)`.

### A8. Restart Claude Desktop
Right-click the Claude icon in the system tray (bottom right, near the clock) → **Quit**. Open Claude Desktop again.
✅ In a chat, the connectors / tools menu lists **brain-arm**.

Continue with [Both: connect your projects](#both-connect-your-projects).

---

## B. macOS

### B1. Install Homebrew (skip if `brew --version` already works)
Open **Terminal** (Applications → Utilities → Terminal):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
At the end it prints **"Next steps"** with two or three commands — copy and run them. Then close and reopen Terminal.
✅ `brew --version` prints a version.

### B2. Install the tools
```bash
brew install python tmux git watch
```
✅ `python3 --version` shows 3.10 or newer.

### B3. Install Claude Code and sign in
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Close and reopen Terminal, then:
```bash
claude --version
claude
```
Follow the sign-in link, then type `/exit`.

### B4. Install Claude Desktop
Download it from the official Claude download page, drag it to Applications, open it and sign in.

### B5. Download brain-arm
```bash
git clone https://github.com/GloriaSegurini/brain-arm-claude-mcp.git ~/brain-arm
cd ~/brain-arm
```

### B6. Check, then install
```bash
./install.sh --check
./install.sh
```
Answer `y` to **"Add it to Claude Desktop for you now?"**.
✅ It shows `[ok] watcher running (launchd)`. macOS may show a notification *"Background Items Added"*: that's
the brain-arm watcher — allow it.

### B7. Restart Claude Desktop
Claude menu → **Quit Claude** (or `Cmd+Q`), then open it again.
✅ The connectors / tools menu in a chat lists **brain-arm**.

---

## Both: connect your projects

### 1. Map each project to its folder
```bash
cd ~/brain-arm
./add-project.sh webshop ~/code/webshop
```
The first word is the **project name** you'll use in the brain chat; the second is the **repository folder**.
A single chat can use a different folder: `./add-project.sh webshop:docs ~/code/webshop-docs`.
✅ `[ok] webshop → /home/you/code/webshop`. See the map any time with `./add-project.sh --list`.

### 2. Trust each folder once in Claude Code
```bash
cd ~/code/webshop && claude
```
Accept the question *"Do you trust the files in this folder?"*, then type `/exit`.
Without this, the arm would stop on that question (the watcher gives up after 10 minutes).

### 3. Tell the brain who it is
In Claude Desktop create a **Project** (or use an existing one) and paste the contents of
[`docs/brain-instructions.md`](docs/brain-instructions.md) into its **instructions**, replacing
`<project>` (e.g. `webshop`) and `<channel>` (a short name for this chat, e.g. `checkout-redesign`).
One chat = one channel.

### 4. Optional: allow arms to use DEV/TEST environments
```bash
python3 automode_devtest.py            # shows what it would add
python3 automode_devtest.py --apply    # adds it, with a backup of your settings
```

---

## Verify everything

| Check | Command | You should see |
|---|---|---|
| Watcher running | Windows/Linux: `systemctl --user is-active brain-arm-watcher` · Mac: `launchctl print gui/$(id -u)/com.brain-arm.watcher \| grep state` | `active` · `state = running` |
| Status table | `watch -n3 python3 ~/brain-arm/status.py` | the table (Ctrl+C to exit) |
| Live arms | `tmux attach -t arms` | a `status` window; arm windows appear when tasks arrive (`Ctrl+b d` to leave) |
| End-to-end test | see below | `done … get_result: ok` |

**End-to-end test** (uses a throw-away folder):
```bash
mkdir -p ~/brain-arm-sandbox && cd ~/brain-arm-sandbox && claude     # accept trust, then /exit
cd ~/brain-arm && ./add-project.sh brain-arm:selftest ~/brain-arm-sandbox
.venv/bin/python tests/e2e_brain_wait.py brain-arm selftest
```
✅ Within a minute: `wait_for_task #1: done …` and `get_result: ok`. Add `--slow` to also test the
"wait … call again" path (~80 s).

Then the real thing: in your brain chat ask for something small, e.g. *"Delegate a read-only task: list the
files in the project root."* — it should create the task, wait on its own and report the result.

---

## Common problems

| What you see | What to do |
|---|---|
| `./install.sh: Permission denied` | `chmod +x install.sh add-project.sh stop-arms.sh` and retry. |
| `[missing] systemd` (Windows) | Redo [A2](#a2-turn-on-systemd-lets-brain-arm-start-automatically), including `wsl --shutdown`. |
| `claude: command not found` after installing it | Close and reopen the terminal. |
| Claude Desktop says the brain-arm configuration is not valid | Re-run `./install.sh` and answer `y`, or copy the entry it prints. On Windows it must use `"command": "wsl"`. Then quit Desktop from the tray and reopen it. |
| brain-arm missing in Claude Desktop | Quit Desktop completely (tray/menu bar → Quit), not just the window. |
| Windows: `Wsl/Service/E_UNEXPECTED` or the connector stops working | In PowerShell: `wsl --shutdown`, open Ubuntu, restart Claude Desktop. |
| A task stays `PEND` with ○ | Project not mapped (`./add-project.sh --list`), folder not trusted (step 2), or watcher stopped (see Verify). |
| The arm keeps asking for approvals | Update Claude Code (`claude update`, or reinstall with the A4/B3 command): auto mode needs a recent version. |
| `pip install failed` | Network or proxy: retry; behind a corporate proxy set `HTTPS_PROXY` first. |

## Updating

```bash
cd ~/brain-arm && git pull && ./install.sh
```

## Uninstalling

```bash
cd ~/brain-arm && ./stop-arms.sh
# Windows/Linux:
systemctl --user disable --now brain-arm-watcher && rm ~/.config/systemd/user/brain-arm-watcher.service
# Mac:
launchctl bootout gui/$(id -u)/com.brain-arm.watcher; rm ~/Library/LaunchAgents/com.brain-arm.watcher.plist
# Both:
rm -rf ~/brain-arm ~/.brain-arm-projects.json
```
Then remove the `brain-arm` entry from the Claude Desktop configuration.

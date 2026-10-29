# Install brain-arm — step-by-step guide

This guide assumes **no experience with terminals or programming tools**. Follow the steps in order and
don't skip any. It takes about **20–30 minutes**.

## What you are going to install

| Piece | What it is | Why you need it |
|---|---|---|
| **Claude Desktop** | The Claude app you chat with | It is the **brain**: you plan the work with it |
| **Claude Code** | Claude working inside your project folders | It is the **arm**: it does the work |
| **brain-arm** | This tool | It connects the two and runs the arms for you |
| A few small tools | Python, tmux, git, watch | brain-arm needs them to run |

## How to read this guide

Every step looks like this:

- 👉 **Do:** what to do
- 📋 **Copy:** a command to copy and paste, then press **Enter**
- ✅ **You should see:** how to know it worked
- ❌ **If not:** what to do instead

**Three things worth knowing before you start**

1. A **terminal** is a window where you type commands instead of clicking.
2. **Pasting** in a terminal: on Windows (Ubuntu window) **right-click** or `Ctrl+Shift+V`; on Mac `Cmd+V`.
   Paste **one command at a time**, then press **Enter** and wait until it finishes
   (the blinking cursor comes back after a line ending in `$` or `%`).
3. When a terminal asks for your **password**, nothing appears while you type — no dots, no stars.
   That's normal: type it and press Enter.

## Which part is for you?

- I have a **Windows** PC → [Part A — Windows](#part-a--windows)
- I have a **Mac** → [Part B — Mac](#part-b--mac)

Then everyone continues with [Part C — Connect your first project](#part-c--connect-your-first-project).

> **Using VS Code?** Its built-in terminal works too: menu **Terminal → New Terminal**. On Windows, open the
> folder through WSL (see A9) so the terminal is the Ubuntu one; on Mac it is the normal Mac terminal.

---

## Part A — Windows

On Windows, brain-arm runs inside **WSL**, a small Linux system that Windows can install for you. You'll install
it once; after that you'll use an app called **Ubuntu** as your terminal.

### A1. Check your Windows version
- 👉 **Do:** press `Win+R`, type `winver`, press Enter.
- ✅ **You should see:** Windows 11, or Windows 10 version 2004 or later.
- ❌ **If not:** update Windows first (Settings → Windows Update).

### A2. Open PowerShell as administrator
- 👉 **Do:** click **Start**, type `PowerShell`, then **right-click** "Windows PowerShell" →
  **Run as administrator** → click **Yes**.
- ✅ **You should see:** a blue or black window whose title starts with "Administrator".

### A3. Install WSL with Ubuntu
- 📋 **Copy** (into the administrator PowerShell):
  ```powershell
  wsl --install -d Ubuntu-24.04
  ```
- ✅ **You should see:** download and installation messages, then a request to **restart** the computer.
- 👉 **Do:** restart the computer.
- ❌ **If not:** if it says WSL is already installed, type `wsl -l -v` — if you see `Ubuntu-24.04` with
  `VERSION 2`, go to A4. If it mentions *virtualization*, ask your IT department to enable it.

### A4. Start Ubuntu for the first time
- 👉 **Do:** click **Start**, type `Ubuntu`, open **Ubuntu 24.04**. The first start takes a few minutes.
- 👉 **Do:** when asked, choose a **username** (lowercase, no spaces, e.g. `maria`) and a **password**.
  **Write the password down**: you'll need it during installation.
- ✅ **You should see:** a line like `maria@PC-NAME:~$` with a blinking cursor.

> **From now on, unless a step says "PowerShell", every command goes in this Ubuntu window.**

### A5. Turn on automatic start (systemd)
- 📋 **Copy:**
  ```bash
  printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf
  ```
- 👉 **Do:** type your Ubuntu password when asked (invisible) and press Enter.
- 👉 **Do:** close the Ubuntu window. Open **PowerShell** (normal, not administrator) and copy:
  ```powershell
  wsl --shutdown
  ```
- 👉 **Do:** open **Ubuntu** again from the Start menu.
- 📋 **Copy:**
  ```bash
  systemctl --user is-system-running
  ```
- ✅ **You should see:** `running` or `degraded` (both are fine).
- ❌ **If not:** repeat A5 from the beginning; make sure you ran `wsl --shutdown`.

### A6. Install the small tools
- 📋 **Copy:**
  ```bash
  sudo apt update && sudo apt install -y python3 python3-venv tmux git procps
  ```
- 👉 **Do:** type your password if asked. It takes a minute or two.
- ✅ **You should see:** it ends without red lines starting with `E:`.

### A7. Install Claude Code and sign in
- 📋 **Copy:**
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- 👉 **Do:** close the Ubuntu window and open it again.
- 📋 **Copy:**
  ```bash
  claude --version
  ```
- ✅ **You should see:** a version number, e.g. `2.1.302 (Claude Code)`.
- 📋 **Copy:**
  ```bash
  claude
  ```
- 👉 **Do:** follow what it asks: pick a theme, then it shows a **sign-in link** — `Ctrl+click` it (or copy it into
  your browser), sign in with your Claude account and approve. Back in Ubuntu, when you see a box to type in,
  type `/exit` and press Enter.
- ❌ **If not:** `claude: command not found` → close and reopen Ubuntu and try again.

### A8. Install Claude Desktop (the Windows app)
- 👉 **Do:** download Claude Desktop for Windows from **https://claude.ai/download**, install it and sign in.
- ✅ **You should see:** the Claude app open, with a chat box.

### A9. Download brain-arm
- 📋 **Copy** (in Ubuntu):
  ```bash
  git clone https://github.com/GloriaSegurini/brain-arm-claude-mcp.git ~/brain-arm
  cd ~/brain-arm
  ```
- ✅ **You should see:** the line now ends with `~/brain-arm$`.
- *(VS Code users: type `code .` here to open the folder in VS Code connected to Ubuntu.)*

### A10. Check your computer, then install brain-arm
- 📋 **Copy:**
  ```bash
  ./install.sh --check
  ```
- ✅ **You should see:** every line with `[ok]` and at the end `Check passed`.
- ❌ **If not:** for each line with `[missing]`, copy the command written after `install with:`, run it,
  then run `./install.sh --check` again.
- 📋 **Copy:**
  ```bash
  ./install.sh
  ```
- 👉 **Do:** when it asks **"Add it to Claude Desktop for you now (a backup is made)? [y/N]"** type `y` and press Enter.
- ✅ **You should see:** `[ok] watcher running (systemd)`, `[ok] brain-arm added to …` and `Installed. Next steps`.

### A11. Restart Claude Desktop
- 👉 **Do:** at the bottom right of the screen, near the clock, click the **^** arrow, **right-click** the Claude
  icon → **Quit**. (Closing the window with X is not enough.) Then open Claude Desktop again.
- ✅ **You should see:** in a chat, open the tools / connectors menu (the icon near the message box):
  **brain-arm** is listed and switched on.
- ❌ **If not:** see [Common problems](#common-problems).

➡️ Continue with [Part C](#part-c--connect-your-first-project).

---

## Part B — Mac

On a Mac everything runs directly on macOS; you'll use the **Terminal** app.

### B1. Open Terminal
- 👉 **Do:** press `Cmd+Space`, type `Terminal`, press Enter.
- ✅ **You should see:** a window with a line ending in `%` and a blinking cursor.
- *(VS Code: menu **Terminal → New Terminal** gives you the same thing.)*

### B2. Install Apple's developer tools
- 📋 **Copy:**
  ```bash
  xcode-select --install
  ```
- 👉 **Do:** a window appears → click **Install** → **Agree**, and wait until it finishes (a few minutes).
- ❌ **If not:** if it says *"already installed"*, that's fine — go on.

### B3. Install Homebrew (a tool that installs other tools)
- 👉 **Do:** first check if you already have it:
  ```bash
  brew --version
  ```
  If you see a version number, skip to B4.
- 📋 **Copy:**
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- 👉 **Do:** type your **Mac password** when asked (invisible), press **Enter** when asked to continue.
- 👉 **Do:** at the end it prints **"Next steps"** with two or three commands: **copy and run each of them**.
  Then close Terminal and open it again.
- ✅ **You should see:** `brew --version` now prints a version number.

### B4. Install the small tools
- 📋 **Copy:**
  ```bash
  brew install python tmux git watch
  ```
- ✅ **You should see:** it ends without `Error:`. `python3 --version` shows 3.10 or newer.

### B5. Install Claude Code and sign in
- 📋 **Copy:**
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- 👉 **Do:** close Terminal and open it again.
- 📋 **Copy:**
  ```bash
  claude --version
  claude
  ```
- 👉 **Do:** follow what it asks: pick a theme, `Cmd+click` the sign-in link, sign in and approve. Back in
  Terminal, type `/exit` and press Enter.
- ✅ **You should see:** a version number from `claude --version`.

### B6. Install Claude Desktop (the Mac app)
- 👉 **Do:** download Claude Desktop for Mac from **https://claude.ai/download**, open the downloaded file,
  drag **Claude** into **Applications**, open it and sign in.

### B7. Download brain-arm
- 📋 **Copy:**
  ```bash
  git clone https://github.com/GloriaSegurini/brain-arm-claude-mcp.git ~/brain-arm
  cd ~/brain-arm
  ```
- ✅ **You should see:** the line now contains `brain-arm`.

### B8. Check your Mac, then install brain-arm
- 📋 **Copy:**
  ```bash
  ./install.sh --check
  ```
- ✅ **You should see:** every line `[ok]` and `Check passed`.
- ❌ **If not:** run the command shown after `install with:` for each `[missing]` line, then check again.
- 📋 **Copy:**
  ```bash
  ./install.sh
  ```
- 👉 **Do:** answer `y` to **"Add it to Claude Desktop for you now?"**.
- ✅ **You should see:** `[ok] watcher running (launchd)` and `Installed. Next steps`.
  macOS may show a notification **"Background Items Added"**: that's brain-arm's watcher — allow it.

### B9. Restart Claude Desktop
- 👉 **Do:** with Claude Desktop in front, press `Cmd+Q` (closing the window is not enough), then open it again.
- ✅ **You should see:** in a chat, the tools / connectors menu lists **brain-arm**, switched on.

➡️ Continue with Part C.

---

## Part C — Connect your first project

Do this part in the **Ubuntu window** (Windows) or **Terminal** (Mac).

### C1. Find your project folder
A **project folder** is the folder that contains the code the arm will work on.
- **Windows:** the folder should be **inside Ubuntu**, e.g. `~/code/webshop` (`~` means your home folder).
  If your code is still in Windows (e.g. `C:\code\webshop`), the easiest way is to download it again inside
  Ubuntu with `git clone …`. (Windows folders are reachable as `/mnt/c/...`, but slower.)
- **Mac:** e.g. `~/code/webshop`. Tip: type the start of a command, then **drag the folder from Finder into
  Terminal** to paste its full path.

### C2. Tell brain-arm about it
- 📋 **Copy** (replace the name and the folder with yours):
  ```bash
  cd ~/brain-arm
  ./add-project.sh webshop ~/code/webshop
  ```
  `webshop` is the **project name** you'll use with the brain: lowercase, no spaces.
- ✅ **You should see:** `[ok] webshop → /home/…/code/webshop`.
- ❌ **If not:** `folder … does not exist` → check the path (C1).

### C3. Let Claude Code trust the folder (once per folder)
- 📋 **Copy** (your folder):
  ```bash
  cd ~/code/webshop && claude
  ```
- 👉 **Do:** to the question **"Do you trust the files in this folder?"** choose **Yes**, then type `/exit`.
- *(Why: otherwise every arm would stop on that question.)*

### C4. Tell the brain who it is
- 👉 **Do:** in Claude Desktop create a **Project** (left sidebar → Projects → New project), e.g. "Webshop".
- 👉 **Do:** open [`docs/brain-instructions.md`](docs/brain-instructions.md) (on GitHub, or in the terminal with
  `cat ~/brain-arm/docs/brain-instructions.md`), copy the block between the two lines, and paste it into the
  project's **instructions**.
- 👉 **Do:** in the pasted text replace `<project>` with your project name (e.g. `webshop`) and `<channel>` with a
  short name for this chat (e.g. `checkout-redesign`). **One chat = one channel.**

### C5. Test that everything is connected
- 📋 **Copy** (uses an empty test folder, nothing of yours is touched):
  ```bash
  mkdir -p ~/brain-arm-sandbox && cd ~/brain-arm-sandbox && claude
  ```
  Choose **Yes** to trust the folder, then type `/exit`.
  ```bash
  cd ~/brain-arm && ./add-project.sh brain-arm:selftest ~/brain-arm-sandbox
  .venv/bin/python tests/e2e_brain_wait.py brain-arm selftest
  ```
- ✅ **You should see,** within a minute: `wait_for_task #1: done …` and `get_result: ok`.
- ❌ **If not:** see [Common problems](#common-problems).

### C6. Try it for real
- 👉 **Do:** in a chat of your Claude Desktop project, write:
  *"Delegate a read-only task: list the files in the project folder."*
- ✅ **You should see:** the brain creates the task, waits **by itself** (you don't have to tell it anything) and
  then reports the list of files.

### C7. Watch it work (optional, fun)
- 📋 **Copy:**
  ```bash
  watch -n3 python3 ~/brain-arm/status.py
  ```
  The table of tasks updates every 3 seconds (`Ctrl+C` to close it).
- 📋 **Copy:**
  ```bash
  tmux attach -t arms
  ```
  You see the arms working live. To leave without stopping anything press `Ctrl+b`, then `d`.
  (In VS Code's terminal `Ctrl+b` may be captured by VS Code: close the terminal tab instead.)

🎉 **Done.** From now on just chat with your brain: brain-arm starts and stops the arms by itself.

---

## Every day

| I want to… | Command (in Ubuntu / Terminal) |
|---|---|
| add another project | `cd ~/brain-arm && ./add-project.sh <name> <folder>` (then C3 for that folder) |
| see my projects | `cd ~/brain-arm && ./add-project.sh --list` |
| see the tasks | `watch -n3 python3 ~/brain-arm/status.py` |
| see the arms working | `tmux attach -t arms` |
| stop everything now | `cd ~/brain-arm && ./stop-arms.sh` |

## Common problems

| What you see | What to do |
|---|---|
| `Permission denied` when running `./install.sh` | `cd ~/brain-arm && chmod +x *.sh` and try again. |
| `[missing] systemd` (Windows) | Redo **A5**, including `wsl --shutdown` in PowerShell. |
| `claude: command not found` | Close and reopen the terminal. |
| brain-arm not listed in Claude Desktop | Quit Claude Desktop **completely** (A11 / B9) and reopen it. If still missing, run `./install.sh` again and answer `y`. |
| Claude Desktop says the brain-arm configuration is not valid | Run `./install.sh` again and answer `y` (it rewrites the entry correctly; on Windows it must use `"command": "wsl"`), then restart Claude Desktop. |
| Windows: `Wsl/Service/E_UNEXPECTED`, or brain-arm stops responding | In PowerShell: `wsl --shutdown`, open Ubuntu, restart Claude Desktop. |
| A task stays in `PEND` | The project isn't mapped (`./add-project.sh --list`), the folder isn't trusted (C3), or the watcher is off (run `./install.sh` again). |
| The arm keeps asking for permission | Update Claude Code: `claude update`. |
| `pip install failed` | Internet or company proxy problem: try again, or ask IT for the proxy settings. |

## Updating brain-arm
```bash
cd ~/brain-arm && git pull && ./install.sh
```

## Uninstalling
```bash
cd ~/brain-arm && ./stop-arms.sh
# Windows (Ubuntu):
systemctl --user disable --now brain-arm-watcher && rm ~/.config/systemd/user/brain-arm-watcher.service
# Mac:
launchctl bootout gui/$(id -u)/com.brain-arm.watcher; rm ~/Library/LaunchAgents/com.brain-arm.watcher.plist
# Both:
rm -rf ~/brain-arm ~/.brain-arm-projects.json
```
Then remove the `brain-arm` entry from Claude Desktop's configuration (Settings → Developer → Edit config) and
restart Claude Desktop.

## Using Linux?
The watcher and the arms work on Linux (`./install.sh` supports it, like on Windows/Ubuntu), but Claude Desktop —
the brain — is officially available only for Windows and Mac, so on Linux you need another MCP client as the brain.

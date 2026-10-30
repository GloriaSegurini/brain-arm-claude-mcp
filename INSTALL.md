# Install brain-arm — step-by-step guide

This guide assumes **no experience with terminals or programming tools**. Follow the steps in order and
don't skip any. It takes about **20–30 minutes**.

## What you are going to install

| Piece                    | What it is                                 | Why you need it                                      |
| ------------------------ | ------------------------------------------ | ---------------------------------------------------- |
| **Claude Desktop** | The Claude app you chat with               | It is the **brain**: you plan the work with it |
| **Claude Code**    | Claude working inside your project folders | It is the **arm**: it does the work            |
| **brain-arm**      | This tool                                  | It connects the two and runs the arms for you        |
| A few small tools        | Python, tmux, git, watch                   | brain-arm needs them to run                          |

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

Then everyone continues with [Part C — Finish the setup by chatting](#part-c--finish-the-setup-by-chatting).

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

➡️ Continue with [Part C](#part-c--finish-the-setup-by-chatting).

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

## Part C — Finish the setup by chatting

From here on, **Claude does the rest**. You don't need the terminal anymore.

### C1. Ask Claude to set up brain-arm

- 👉 **Do:** in Claude Desktop open a **new chat** and write:
  *"Set up brain-arm."*
- ✅ **You should see:** Claude checks your installation (tool `setup_check`) and tells you what is ready and
  what is still missing.
- ❌ **If Claude doesn't know what brain-arm is:** brain-arm is not connected. Go back to **A11 / B9**.

### C2. Answer Claude's questions

Claude asks you **two things**:

1. **Which folder contains your code.** Write the full path, for example:
   - Windows: `C:\code\webshop`, or a folder inside Ubuntu such as `~/code/webshop` (faster);
   - Mac: `~/code/webshop`. Tip: drag the folder from Finder into the chat box to paste its path.
2. **A short name for the project**, e.g. `webshop` (lowercase, no spaces).

Claude then connects the project (tool `add_project`).

### C3. Say yes (or no) to trusting the folder

Claude Code works only in folders you **trust**. Trusting a folder lets the arms **read, write and run commands
in it** without asking you each time.

- 👉 Claude names the exact folder and asks you a **yes/no question**. It is not allowed to trust a folder
  without your explicit "yes" (tool `trust_folder`).
- ✅ **Yes:** Claude marks the folder as trusted. It also keeps a backup of Claude Code's settings
  (`~/.claude.json.bak-brain-arm`).
- **No:** nothing changes. You can trust it yourself later: `cd <folder> && claude`, answer **Yes**, type `/exit`.

### C4. First test

- 👉 Claude offers a first **read-only** task, e.g. listing the files in the project folder. Say yes.
- ✅ **You should see:** Claude sends the task, **waits by itself** (you don't have to tell it anything) and reports
  the list of files. 🎉 **Done.**

### Every new chat

Each chat works on one **project** and one **channel** (the chat's name, e.g. `checkout-redesign`). Claude
proposes them at the start of the chat; just confirm. **One chat = one channel.**

### Watch it work (optional, fun)

In the Ubuntu window (Windows) or Terminal (Mac):

- 📋 `watch -n3 python3 ~/brain-arm/status.py` — the table of tasks, updated every 3 seconds (`Ctrl+C` to close).
- 📋 `tmux attach -t arms` — the arms working live. To leave without stopping anything press `Ctrl+b`, then `d`.
  (In VS Code's terminal `Ctrl+b` may be captured by VS Code: close the terminal tab instead.)

<details>
<summary>Prefer the terminal? The same steps by hand</summary>

```bash
cd ~/brain-arm && ./add-project.sh webshop ~/code/webshop   # C2: connect the project
cd ~/code/webshop && claude                                  # C3: answer Yes to the trust question, then /exit
```

If your Claude Desktop ignores the instructions sent by brain-arm (Claude doesn't propose project and channel,
or doesn't wait for the arms by itself), paste the block from [`docs/brain-instructions.md`](docs/brain-instructions.md)
into the instructions of a Claude Desktop **Project** (left sidebar → Projects → New project).

End-to-end check without Claude Desktop (uses an empty test folder):

```bash
mkdir -p ~/brain-arm-sandbox && cd ~/brain-arm-sandbox && claude   # trust it, then /exit
cd ~/brain-arm && ./add-project.sh brain-arm:selftest ~/brain-arm-sandbox
.venv/bin/python tests/e2e_brain_wait.py brain-arm selftest           # expect "get_result: ok"
```

</details>

---

## Every day

| I want to…          | Command (in Ubuntu / Terminal)                                                   |
| -------------------- | -------------------------------------------------------------------------------- |
| add another project  | `cd ~/brain-arm && ./add-project.sh <name> <folder>` (or ask Claude: *"connect the project in &lt;folder&gt;"*) |
| see my projects      | `cd ~/brain-arm && ./add-project.sh --list`                                    |
| see the tasks        | `watch -n3 python3 ~/brain-arm/status.py`                                      |
| see the arms working | `tmux attach -t arms`                                                          |
| stop everything now  | `cd ~/brain-arm && ./stop-arms.sh`                                             |

## Common problems

| What you see                                                         | What to do                                                                                                                                               |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Permission denied` when running `./install.sh`                  | `cd ~/brain-arm && chmod +x *.sh` and try again.                                                                                                       |
| `[missing] systemd` (Windows)                                      | Redo **A5**, including `wsl --shutdown` in PowerShell.                                                                                           |
| `claude: command not found`                                        | Close and reopen the terminal.                                                                                                                           |
| brain-arm not listed in Claude Desktop                               | Quit Claude Desktop **completely** (A11 / B9) and reopen it. If still missing, run `./install.sh` again and answer `y`.                        |
| Claude Desktop says the brain-arm configuration is not valid         | Run `./install.sh` again and answer `y` (it rewrites the entry correctly; on Windows it must use `"command": "wsl"`), then restart Claude Desktop. |
| Windows: `Wsl/Service/E_UNEXPECTED`, or brain-arm stops responding | In PowerShell: `wsl --shutdown`, open Ubuntu, restart Claude Desktop.                                                                                  |
| A task stays in `PEND`                                             | Ask Claude: *"check the brain-arm setup"*. It runs `setup_check` and tells you what is missing (project not connected, folder not trusted, watcher off).               |
| The arm keeps asking for permission                                  | Update Claude Code: `claude update`.                                                                                                                   |
| `pip install failed`                                               | Internet or proxy problem: check your connection and try again.                                                                                          |

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

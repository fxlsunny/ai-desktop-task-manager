# 🖥️ AI Desktop Task Manager

> A minimalist, low-footprint, cross-platform desktop task manager. Comes with a multi-model AI assistant, a Markdown editor, screenshot annotation, alarm reminders and more — all built on the Python standard library + Tkinter. **Zero hard dependencies, millisecond startup, ~20 MB RAM.**
>
> Runs natively on **Windows / macOS / Linux**. UI is fully bilingual — **🇨🇳 简体中文 / 🇺🇸 English** — switchable in *Settings* with no restart. Chinese is the default.

🌐 **Language**: [简体中文](./README.md) | [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey) ![Language](https://img.shields.io/badge/i18n-zh__CN%20%2F%20en__US-orange) ![License](https://img.shields.io/badge/License-MIT-green) ![Dependencies](https://img.shields.io/badge/Core%20Deps-Zero-success)

---

## 📸 Screenshots

### English UI

![Desktop Task Manager - English UI](./img/ai_task_manager_02.jpg)

### Chinese UI

![Desktop Task Manager - Chinese UI](./img/ai_task_manager_01.jpg)

> A translucent always-on-top overlay (drag / fold / **drag-resize** / opacity) + task manager + AI chat + a maximised editor + screenshot annotator, all glued together.

---

## ✨ Features

### 🖥️ Desktop Overlay
- Always-on-top, drag the title bar to anywhere on screen
- **Drag-resize**: a `◢` grip at the bottom-right resizes both width and height. Minimum `280×180`, dimensions are persisted to `config.json` on release.
- **Adjustable opacity** (20% ~ 100%) so it never gets in your way
- **One-click fold** down to a 26-px title strip
- **Off-screen clamp**: never disappears when you unplug a secondary monitor
- Optional system-tray icon (uses `pystray`, gracefully degrades if missing)
- **Cross-platform autostart**: Windows registry / macOS LaunchAgent / Linux `~/.config/autostart/*.desktop`, toggle in one click

### 🌐 Internationalization (i18n)
- Bundled **🇨🇳 Simplified Chinese** + **🇺🇸 English** UI translations
- Defaults to Chinese (`config.language = "zh_CN"`); switch via *Settings → Interface Language / 界面语言* and pick `English`
- After switching, the manager window, overlay, AI chat, tray menu rebuild instantly with the new strings — **no restart needed**

### 📝 Task Management
- Each task carries: **title / body / priority / due date / alarm / category tags**
- Status: open / done (filter to show only open)
- Colour-coded priority dot (🔴 high / 🟡 medium / 🟢 low)
- Search, filter, sort built in
- **Maximised editor**: double-click a task body to open a full-window editor (1200×720) with side-by-side preview
  - Search/replace, font zoom (Ctrl+Wheel), shortcuts Ctrl+S/Z/F
  - **Pure-Tk Markdown preview** for `# / ## / **bold** / *italic* / \`code\` / > quote / - list / [link]`
  - **Local image preview**: `![alt](relative/path.jpg)` renders inline thumbnails

### 🤖 AI Assistant (Multi-Provider)
Bundled config templates for **7 mainstream AI providers**, switchable on the fly:

| Provider | Notes | Pricing |
|----------|-------|---------|
| 🐉 **Tencent Hunyuan** | `hunyuan-turbos-latest`, optimised for Chinese, ships with a DEMO key for zero-config trial | Free tier |
| 🟢 **Ollama (local)** | Runs entirely offline, default model `qwen2:7b` | Free (self-hosted) |
| ⚡ **Groq** | `llama3-8b-8192`, ultra-fast inference | Generous free tier |
| 🔵 **DeepSeek** | `deepseek-chat`, strong at code | Cheap |
| 🌙 **Moonshot** | `moonshot-v1-8k`, long context | Paid |
| 🤖 **OpenAI** | `gpt-4o-mini` and friends | Paid |
| 🔧 **Custom** | Any OpenAI-compatible endpoint | Depends |

**Highlights**:
- **SSE streaming** with cancel-mid-flight support
- **Persistent conversations** auto-saved to `data/chat_history/`
  - Left sidebar lists past chats — view / delete / reopen, ChatGPT-style
- **Customisable system prompt** in settings
- **Pass-through `extra_body`** (e.g. Hunyuan's `enable_enhancement`)

### 📷 Screenshot & Annotation
- Full-screen translucent mask → drag a region → enter the annotation editor
- **Tools**: rectangle, ellipse, arrow, brush, text, mosaic
- Colour palette + thickness slider, undo / redo / clear
- Shortcuts: Ctrl+Z/Y (undo/redo), Ctrl+S (save), Esc (cancel)
- **Multi-monitor + HiDPI** aware (DPI awareness enabled at startup)
- **Auto-insert into task**: saved screenshots are appended into the currently-edited task body
- **Global hotkey**: `Ctrl+Alt+A` (requires the `keyboard` package)

### ⏰ Alarm Reminders
- Polled every minute, aligned to the system clock
- Pop-up + optional cross-platform beep
- Supports an "N minutes early" offset

### 💾 Backup / Email Export
- One click bundles `tasks.json` + chat history into a zip
- Optional SMTP email delivery (default: QQ Mail 465 SSL)
- Built-in profiles for QQ / 163 / 126 / Gmail / Outlook / Sina / Yahoo
- Optional inclusion of `config.json` (sensitive fields auto-redacted)

---

## 🗂️ Project Layout

```
ai-desktop-task-manager/
├── src/                         # ─── all Python source code ───
│   ├── main.py                  # entry point
│   ├── i18n.py                  # zh_CN / en_US translation tables
│   ├── platform_utils.py        # cross-platform helpers (DPI / beep / autostart)
│   ├── config.py                # config load / save
│   ├── models.py                # Task model & Store
│   ├── overlay.py               # desktop overlay window
│   ├── manager.py               # task manager window
│   ├── ai_window.py             # AI chat window
│   ├── ai_chat.py               # AI backend abstraction (OpenAI / Ollama) + history
│   ├── markdown_editor.py       # maximised editor (MD preview + find/replace)
│   ├── screenshot.py            # screenshot & annotation
│   ├── alarm.py                 # alarms (cross-platform beep)
│   ├── backup.py                # backup & email export
│   └── autostart.py             # autostart shim (delegates to platform_utils)
│
├── scripts/                     # ─── all executable scripts ───
│   ├── run.py                   # ★ cross-platform Python launcher (with crash log)
│   ├── start.bat                # Windows launcher (silent pythonw + --console for diag)
│   ├── start.sh                 # Linux / macOS shell launcher
│   ├── start.command            # macOS Finder double-click launcher
│   ├── install_deps.bat         # Windows: install optional deps
│   ├── install_deps.sh          # Linux / macOS: install optional deps
│   └── _sync_img.py             # maintenance: sync README/img to GitHub (dev only)
│
├── start.bat                    # ★ root convenience entry (forwards to scripts/start.bat)
├── start.sh                     # ★ root convenience entry (forwards to scripts/start.sh)
│
├── config/
│   ├── config.example.json      # config template (committed)
│   └── config.json              # actual local config (.gitignored, auto-created)
├── data/                        # runtime data (.gitignored)
│   ├── tasks.json
│   ├── chat_history/
│   └── img/YYYYMMDD/            # screenshots archived by date
├── logs/                        # runtime logs (.gitignored, auto-written on crash)
│   └── runtime.log              # silent-crash stack traces (pythonw mode)
├── img/                         # README screenshots (committed)
│   ├── ai_task_manager_01.jpg   # Chinese UI preview
│   └── ai_task_manager_02.jpg   # English UI preview
│
├── requirements.txt             # optional deps
├── README.md                    # Chinese docs
├── README.en.md                 # English docs
├── LICENSE
└── .gitignore
```

> 📐 **Convention**: `src/` = all source; `scripts/` = all executable scripts; the root only holds standard metadata (README/LICENSE/requirements), data dirs (config/data/logs/img), and the double-click convenience launchers (`start.bat` / `start.sh`).

---

## 🚀 Quick Start

### 1. Requirements

| Platform | Python | Tkinter | Notes |
|----------|--------|---------|-------|
| Windows 10/11 | 3.8+ ([official installer](https://www.python.org/downloads/windows/)) | bundled | 64-bit recommended |
| macOS 11+ | 3.8+ (`brew install python@3.12`) | `brew install python-tk` | Native Apple Silicon |
| Ubuntu/Debian | 3.8+ (`sudo apt install python3`) | `sudo apt install python3-tk` | Needs X11 / Wayland |
| Fedora | 3.8+ (`sudo dnf install python3`) | `sudo dnf install python3-tkinter` | — |
| Arch / Manjaro | 3.8+ (`sudo pacman -S python`) | `sudo pacman -S tk` | — |

> The core runtime has **zero dependencies** beyond stdlib + Tkinter. Optional extras: `pillow` (screenshot & image preview), `pystray` (tray icon), `keyboard` (global hotkey — needs root on Linux, Accessibility permission on macOS).

### 2. Clone

```bash
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager
```

### 3. Launch — One-Liners per Platform

| Platform | Launch | Install optional deps |
|----------|--------|-----------------------|
| **Windows** | Double-click `start.bat` in repo root (foreground diag: `start.bat --console`) | Double-click `scripts\install_deps.bat` |
| **macOS**   | Double-click `scripts/start.command` (first time: `chmod +x scripts/start.command`) | `bash scripts/install_deps.sh` |
| **Linux**   | `./start.sh` (first time: `chmod +x start.sh scripts/*.sh`)<br>Foreground debug: `./start.sh --console` | `./scripts/install_deps.sh` |

Or the universal CLI (works everywhere):

```bash
# Recommended: cross-platform launcher
python scripts/run.py             # auto-detaches console (uses pythonw on Windows)
python scripts/run.py --console   # force keep the console (see logs)

# Or run src/main.py directly
python src/main.py
```

> On first launch `config/config.example.json` is copied to `config/config.json`. Fill in your API keys via the in-app settings panel.

### 4. Switch UI Language (Chinese / English)

Launch the app → `📋 Open Manager` → `⚙️ Settings` → find **Interface Language / 界面语言** dropdown → pick `English`, hit save. The manager rebuilds itself in the new language with **no restart**.

### 5. Run at Startup

Tick **Run at startup / 开机自启动** in `⚙️ Settings`. Per platform:

| Platform | Mechanism | File |
|----------|-----------|------|
| Windows | Registry key `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` | — |
| macOS  | LaunchAgent | `~/Library/LaunchAgents/com.fxlsunny.DesktopTaskManager.plist` |
| Linux  | freedesktop autostart | `~/.config/autostart/DesktopTaskManager.desktop` |

> Unticking auto-cleans up the corresponding file / registry entry, keeping the system tidy.

---

## 🐧🍎 Platform Deployment in Detail

### Windows
```powershell
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager
scripts\install_deps.bat   # optional
start.bat                  # or just double-click start.bat in the root
```

### macOS
```bash
brew install python@3.12 python-tk
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager
chmod +x start.sh scripts/start.sh scripts/start.command scripts/install_deps.sh
bash scripts/install_deps.sh   # optional
./start.sh                     # or double-click scripts/start.command in Finder
```
> On macOS Big Sur+ the first double-click of `scripts/start.command` may show "cannot be opened". Open *System Settings → Privacy & Security* and click "Open Anyway".

### Linux (Ubuntu / Debian example)
```bash
sudo apt update
sudo apt install -y python3 python3-tk python3-pip git
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager
chmod +x start.sh scripts/start.sh scripts/install_deps.sh
./scripts/install_deps.sh   # optional
./start.sh
```
> On Wayland (GNOME 42+) the screenshot tool relies on `xdg-desktop-portal`; X11 sessions are most reliable.
> Tray icon: install `gir1.2-appindicator3-0.1` on GNOME, KDE has SNI support out of the box.

### Through Docker / remote desktop
This is a pure desktop app and needs a graphical session. To run on a server, pair with one of:
- **VcXsrv / X410** (Windows X11 forwarding)
- **xrdp / VNC** (Linux remote desktop)
- **macOS Screen Sharing**

---

## ⚙️ AI Provider Configuration

### Option 1: edit `config/config.json` (not committed)

Open `config/config.json`, find `ai.providers.<provider>.api_key`, drop your key in:

```jsonc
{
  "ai": {
    "active_provider": "hunyuan",        // default: Tencent Hunyuan
    "providers": {
      "hunyuan": {
        "label": "Tencent Hunyuan",
        "api_key": "sk-your-hunyuan-key-here",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-turbos-latest"
      },
      "deepseek": {
        "label": "DeepSeek",
        "api_key": "sk-your-deepseek-key",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
      }
      // ... more providers
    }
  }
}
```

### Option 2: in-app UI (recommended)

Launch → `⚙️ Settings` → switch to `🤖 AI Configuration` → pick a provider → paste key → save.

### Option 3: local Ollama (fully free / offline)

1. Install [Ollama](https://ollama.com), then `ollama pull qwen2:7b`
2. Set `ai.prefer_ollama` to `true` in `config/config.json`
3. Launch — the assistant will route through your local Ollama

### 🔑 Where to get API keys

| Model | URL | Notes |
|-------|-----|-------|
| Tencent Hunyuan | https://cloud.tencent.com/product/hunyuan | New users get free token credit |
| Groq | https://console.groq.com/keys | Generous free quota, very fast |
| DeepSeek | https://platform.deepseek.com/api_keys | Cheap, high-quality, no GFW issues |
| Moonshot | https://platform.moonshot.cn/console/api-keys | New-user credit |
| OpenAI | https://platform.openai.com/api-keys | Needs an overseas card |

---

## ⌨️ Shortcuts

### Global
| Key | Action |
|-----|--------|
| `Ctrl+Alt+A` | Take screenshot (needs `pip install keyboard`) |

### Maximised Editor (double-click a task body)
| Key | Action |
|-----|--------|
| `Ctrl+S` | Save |
| `Ctrl+Z / Y` | Undo / redo |
| `Ctrl+F` | Find |
| `Ctrl++ / -` | Zoom font |
| `Ctrl+Wheel` | Zoom font |
| `Esc` | Close |

### Annotation
| Key | Action |
|-----|--------|
| `Ctrl+Z / Y` | Undo / redo |
| `Ctrl+S` | Save & insert |
| `Esc` | Cancel |

---

## 🛡️ Privacy & Security

- **All data stays 100% local**: tasks, chat history, screenshots all live under `data/` — nothing is uploaded.
- **API keys are only used to call the corresponding AI provider**; the program itself collects nothing.
- **`config/config.json` is in `.gitignore`** so it can never be accidentally pushed.
- To sync tasks across devices, use the *Backup → Email* feature for manual transfer.

---

## 🧪 Development / Debugging

```bash
# foreground launch (see print output)
python src/main.py

# probe a single module
python -c "import sys; sys.path.insert(0,'src'); import config; print(config.load())"
```

### Architecture in 30 seconds

- Main loop in `main.py::main()`, driven by Tk mainloop
- Task data flow: `models.Store` ← → `data/tasks.json` (atomic writes)
- AI backend abstraction: `OllamaBackend` / `OpenAICompatBackend` in `ai_chat.py` share a single `stream(messages)` interface
- Overlay and manager are decoupled via callbacks; `_on_cfg_saved` triggers a full refresh on any settings change

---

## ❓ FAQ

**Q1. Why is the overlay not transparent?**
A. Windows requires `WS_EX_LAYERED` GPU support — virtually every Win10/11 machine has it. In some remote-desktop scenarios it can be downgraded; the *opacity* slider still works regardless.

**Q2. Where do screenshots go?**
A. `data/img/YYYYMMDD/HHMMSS_xxx_DesktopManager.jpg`, archived by date. The path inserted into the task body is **relative**, so moving the data folder doesn't break anything.

**Q3. AI replies are slow?**
A. Three angles to check:
- Network — some overseas APIs (OpenAI / Groq) need a VPN.
- Provider — try Hunyuan / DeepSeek for China-direct connectivity.
- Local — switch to Ollama for zero-latency offline runs.

**Q4. Can I sync to my phone?**
A. There's no mobile client yet; use *Backup → Email zip* to send `tasks.json` over for read-only viewing.

**Q5. Can it be packaged into exe / .app / AppImage?**
A. Yes, with PyInstaller:
```bash
# Windows
pyinstaller --noconsole --onefile --add-data "config/config.example.json;config" --name "DesktopTaskManager" scripts/run.py

# macOS (.app bundle)
pyinstaller --noconsole --onefile --windowed --add-data "config/config.example.json:config" --name "DesktopTaskManager" scripts/run.py

# Linux (binary; wrap with appimagetool for AppImage)
pyinstaller --onefile --add-data "config/config.example.json:config" --name "DesktopTaskManager" scripts/run.py
```

**Q6. How do I switch to the Chinese UI?**
A. Launch → `📋 Open Manager` → `⚙️ Settings` → **Interface Language / 界面语言** → pick `简体中文` → click **💾 Save All Settings**. The manager rebuilds in the new language; the entire UI (task list / edit form / settings / backup / screenshot / AI / overlay / tray menu) follows immediately. The next time you open the AI window it'll also use the new language.

**Q7. macOS double-click on `start.command` says "developer can't be verified"?**
A. That's Gatekeeper. Open *System Settings → Privacy & Security*, scroll to the bottom and click "Open Anyway", or run:
```bash
xattr -d com.apple.quarantine scripts/start.command
```

**Q8. Tray icon invisible on Linux?**
A. GNOME doesn't show legacy tray icons by default; install an extension:
- **GNOME**: install [AppIndicator and KStatusNotifierItem Support](https://extensions.gnome.org/extension/615/appindicator-support/)
- **KDE / XFCE / Cinnamon**: works out of the box

**Q9. Double-clicking `start.bat` does nothing / flashes and exits on Windows?**
A. `start.bat` defaults to `pythonw.exe` (no console, no window) for daily use. If launching fails, work down this list:
1. **Switch to console mode** to surface errors live: in a terminal run `start.bat --console` (root or `scripts\start.bat --console` both work).
2. **Inspect the crash log**: `scripts/run.py` writes uncaught exceptions to `logs/runtime.log` automatically, with full stack traces.
3. **Off-screen overlay?** After unplugging a secondary monitor, `overlay_x` / `overlay_y` in `config/config.json` may point off-screen. The repo already auto-clamps to screen bounds, but if it still misbehaves you can manually reset to `20` / `100`.
4. **Tkinter missing**: rare — re-run the Python installer with `tcl/tk and IDLE` ticked.
5. **Python too old**: needs Python 3.8+. Run `python --version` to verify.

**Q10. Can I drag-resize the overlay?**
A. Yes — grab the small `◢` handle at the bottom-right of the overlay and drag. Both width and height adjust together; the new size is persisted to `config.json` on release. Minimum size is `280×180` to keep all title-bar buttons visible.

---

## 📋 Roadmap

- [x] Multi-model AI assistant + persistent conversations
- [x] Maximised editor + Markdown preview
- [x] Screenshot annotation + inline-into-task
- [x] Email backup
- [x] **Cross-platform support** (Windows / macOS / Linux)
- [x] **Bilingual UI** (Chinese / English)
- [x] **Drag-resizable overlay**
- [ ] More languages (JP / KR / FR / DE… PRs welcome)
- [ ] Cloud sync (WebDAV / S3)
- [ ] Mobile read-only web viewer
- [ ] Kanban board view
- [ ] Pomodoro integration

---

## 🤝 Contributing

Issues and PRs welcome. Code style:
- Prefer the standard library; avoid heavy dependencies
- Any new feature must **degrade gracefully**: if an optional dependency is missing it should display a hint, never crash
- Each UI file keeps a single responsibility (one window / component per file)

---

## 📜 License

[MIT License](./LICENSE) © 2026 fxlsunny

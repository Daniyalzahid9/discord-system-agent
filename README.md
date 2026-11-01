# 🎮 Sentient Desktop Controller — Universal Autonomous Windows Remote Presence

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2.svg)](https://github.com/Rapptz/discord.py)
[![OpenCV SIMD](https://img.shields.io/badge/opencv-50_FPS-00D26A.svg)](https://opencv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows_10%20%2F%2011-0078D6.svg)](https://www.microsoft.com/windows)

**Sentient Desktop Controller** turns your Windows PC into a self-hosted, touchless autonomous workstation accessible worldwide through Discord and ultra-low-latency 50 FPS mobile web streaming.

---

## 🌟 Key Highlights

### ⚡ 1. 50 FPS Hardware-Accelerated Touch Remote (`/stream`)
- **OpenCV SIMD Video Pipeline:** Instant zero-copy screen capture streaming at 50 FPS with TurboJPEG hardware compression.
- **Natural 2-Finger Pinch-to-Zoom:** Smoothly pinch to zoom from 1.0x to 4.5x directly on the mobile screen, with 2-finger panning and double-tap reset.
- **Predictive Mouse Cursor:** Zero-latency client-side cursor movement combined with real-time server-rendered hardware mouse pointer with drop-shadow and precision hotspot.
- **Floating Rounded Mousepad:** Sleek glassmorphic draggable widget with tactile Left/Right click pills and an integrated vertical scroll rail. Minimizable into a floating corner badge.
- **90° Landscape Mode:** Rotate the widescreen desktop 90° via CSS transform to span across your entire phone screen without toggling phone auto-rotate.
- **Virtual PC Key Drawer:** Instant access to `Esc`, `F5`, `F11`, `Del`, `Tab`, `Win`, `Ctrl+C/V/Z`, and Windows On-Screen Keyboard (`osk.exe`).

### 📱 2. Discord-Native Control Center (`/remote`)
- **Zero Browser Required:** Control your computer 100% inside the official Discord mobile app.
- **Interactive Action Buttons:** Direct buttons for Left Click, Right Click, Windows OSK, Alt+Tab, Enter, Screen Refresh, and PC Lock.
- **Native Typing Modal:** Tap `[💬 Type Text]` in Discord to open a native text dialog to write code or shell commands directly onto your PC.
- **100% Encrypted:** Operates over Discord's official TLS encryption across 4G/5G anywhere in the world.

### 🤖 3. Autonomous Multi-Task AI Desktop Pilot
- **Compound Multi-Step Execution:** Execute complex chained tasks with natural commands:
  - *"open chrome with profile Personal and then yt with michael jackson song and then open notepad"*
  - *"open calculator and then type 420*69 and press enter"*
  - *"search quantum computing on google and then lock pc"*
- **Universal AI Engine:** Autonomous multi-turn interactive agent sessions inside dedicated Discord Threads.

### 💻 4. Persistent Interactive Shell Sessions (`/shell start`)
- Spawns a dedicated Discord Thread running a live, persistent PowerShell or CMD instance via `pywinpty`.
- Type commands directly in the thread (e.g., `git commit`, `npm start`, `cd ..`) with live ANSI terminal output streaming back.

### 🎯 5. Windows Window Automation (`/focus`)
- Snaps into native Windows UI windows via `pywinauto`.
- `/focus <window_name>`: Brings any app or browser to the foreground.

### 👁️ 6. Hardware Sensors & Physical Presence
- **Webcam Snapshot (`/webcam`):** Capture photos from your laptop camera.
- **Microphone Listener (`/listen [duration]`):** Record ambient room audio and receive a playable `.wav` file.
- **Voice Synthesizer (`/say <text>`):** Speaks text out loud through laptop speakers using Windows SAPI5 TTS.
- **Screen Motion GIF (`/motion [duration]`):** Generates an animated GIF with hardware cursor tracking.

### 🔔 7. Windows Toast Notification Forwarder (`/notifications start`)
- Intercepts native Windows toast alerts (WhatsApp, Slack, Defender, battery, IDEs) and mirrors them to Discord in real time.

---

## 🔒 Security Architecture

1. **Zero-Trust Discord Whitelist:** Every interaction, button, modal, and slash command verifies your User ID against `ALLOWED_USER_IDS` in `.env`. Unauthorized users are blocked with an instant ephemeral rejection.
2. **5-Minute Inactivity Auto-Lock:** If the remote stream sits idle without user interaction for 5 minutes, the workstation automatically locks itself (`LockWorkStation`).
3. **No Open Ports to Public Internet:** When using Discord-native controls (`/remote`), zero web ports need to be exposed.
4. **Persistent Secret Tokens:** Stream sessions are secured with high-entropy URL-safe cryptographic tokens.

---

## 🚀 Quick Start Guide

### Step 1: Clone the Repository
```bash
git clone https://github.com/Daniyalzahid9/discord-system-agent.git
cd discord-system-agent
```

### Step 2: Set Up Virtual Environment & Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Edit `.env` with your values:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
ALLOWED_USER_IDS=your_discord_user_id
DEFAULT_WORKSPACE=C:\Users\yourusername
```

### Step 4: Run
- **Console Mode:** Double-click `run.bat`
- **Silent Background Service:** Double-click `run_hidden.vbs`
- **Auto-Start on Boot:** Double-click `install_autostart.bat`

---

## 📋 Full Command Cheat Sheet

| Slash Command | Text Prefix | Description |
|---|---|---|
| `/remote` | `!remote` | Discord Native Controller (Zero browser, 100% in app) |
| `/stream` | `!stream` | 50 FPS OpenCV Touch Remote with pinch-to-zoom, mousepad & Stop button |
| `/stream_stop` | - | Shuts down active web stream |
| `/shell start [type]` | `!shell` | Starts persistent interactive terminal thread |
| `/shell stop` | `exit` | Closes terminal session |
| `/screen` | `!screen` | Instant desktop screenshot with cursor overlay |
| `/status` | `!status` | Hardware metrics (CPU, RAM, Disk, Battery, Uptime) |
| `/focus <title>` | - | Brings target window to foreground |
| `/clip get` | `!clip get` | Reads laptop clipboard to mobile Discord |
| `/clip set <text>` | `!clip set <text>` | Sets laptop clipboard from mobile |
| `/webcam` | `!webcam` | Takes front camera photo |
| `/listen [seconds]` | `!listen 5` | Records ambient room audio via laptop mic |
| `/say <text>` | `!say <text>` | Speaks text through laptop speakers |
| `/motion [seconds]` | `!motion 3` | Captures animated GIF of screen motion |
| `/notifications start` | - | Live forwarding of Windows toast alerts |
| `/power <action>` | `!lock` | Power actions (`lock`, `sleep`, `restart`, `shutdown`) |
| `/cmd <command>` | `!cmd <command>` | One-shot PowerShell command execution |
| `/open <target>` | - | Opens file, directory, application, or URL |
| `/apps` & `/kill <id>` | - | Process inspector & terminator |
| `/download <path>` | `!download <path>` | Transfers PC file to mobile phone |

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

# Contributing to Sentient Desktop Controller

Thank you for your interest in contributing! We welcome bug fixes, documentation improvements, and new features.

---

## Development Setup

1. Fork and clone the repository.
2. Create a clean virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up a local test bot in the [Discord Developer Portal](https://discord.com/developers/applications).
4. Copy `.env.example` to `.env` and configure your credentials.
   > **Note:** Never commit `.env` or personal tokens! Verify `.gitignore` is intact.

---

## Code Quality & Architecture Standards

- **PEP 8 Compliance:** Follow standard Python formatting.
- **Asynchronous Safety:** Never block the `asyncio` event loop with long-running synchronous calls — wrap CPU-heavy tasks or blocking I/O with `asyncio.to_thread()`.
- **Desktop Session Attachment:** Win32 API calls interacting with user desktop session must invoke `_attach_to_default_desktop()`.
- **Non-Breaking Changes:** Preserve existing slash command schemas and prefix fallbacks.

---

## Submitting Pull Requests

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Test code execution and compile check:
   ```bash
   python -m py_compile bot.py web_remote_server.py system_controller.py
   ```
3. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat: add support for multi-monitor selection"
   ```
4. Push to your fork and submit a Pull Request.

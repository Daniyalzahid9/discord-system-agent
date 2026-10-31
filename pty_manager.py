import re
import time
import asyncio
import threading
from typing import Dict, Optional
import winpty
import discord

ANSI_ESCAPE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    """Removes terminal ANSI codes for clean Discord codeblock display."""
    clean = ANSI_ESCAPE.sub('', text)
    # Remove excessive carriage returns
    return clean.replace('\r\n', '\n').replace('\r', '\n')

class PTYSession:
    def __init__(self, thread_id: int, thread: discord.Thread, shell_cmd: str = "powershell.exe", cwd: str = None):
        self.thread_id = thread_id
        self.thread = thread
        self.shell_cmd = shell_cmd
        self.cwd = cwd
        self.pty: Optional[winpty.PTY] = None
        self.is_running = False
        self.reader_thread: Optional[threading.Thread] = None
        self.loop = asyncio.get_event_loop()
        self.buffer = ""
        self.lock = threading.Lock()

    def start(self):
        # Initialize winpty terminal (80 columns, 24 rows)
        self.pty = winpty.PTY(cols=90, rows=30)
        self.pty.spawn(self.shell_cmd, cwd=self.cwd)
        self.is_running = True
        
        # Start background reader thread
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()

        # Start async buffer flusher in the asyncio event loop
        asyncio.create_task(self._flush_loop())

    def _read_loop(self):
        """Continuously reads bytes from winpty."""
        while self.is_running and self.pty and self.pty.isalive():
            try:
                raw_chunk = self.pty.read(blocking=True)
                if raw_chunk:
                    cleaned = strip_ansi(raw_chunk)
                    with self.lock:
                        self.buffer += cleaned
            except Exception:
                break
        self.is_running = False

    async def _flush_loop(self):
        """Periodically flushes the buffered terminal output back into the Discord Thread."""
        while self.is_running:
            await asyncio.sleep(1.0)
            to_send = ""
            with self.lock:
                if self.buffer:
                    to_send = self.buffer
                    self.buffer = ""
            
            if to_send.strip():
                # Split chunks if longer than Discord 1900 char limit
                while to_send:
                    chunk = to_send[:1800]
                    to_send = to_send[1800:]
                    if chunk.strip():
                        try:
                            await self.thread.send(f"```ansi\n{chunk}\n```")
                        except Exception:
                            try:
                                await self.thread.send(f"```text\n{chunk}\n```")
                            except Exception:
                                pass

        # Session ended notice
        try:
            await self.thread.send("⚠️ **PTY Session Closed.**")
        except Exception:
            pass

    def write_input(self, text: str):
        """Sends user input into the terminal."""
        if self.is_running and self.pty and self.pty.isalive():
            # Ensure line ending
            if not text.endswith("\r\n") and not text.endswith("\n"):
                text += "\r\n"
            elif text.endswith("\n") and not text.endswith("\r\n"):
                text = text[:-1] + "\r\n"
            self.pty.write(text)

    def stop(self):
        self.is_running = False
        try:
            if self.pty and self.pty.isalive():
                del self.pty
                self.pty = None
        except Exception:
            pass


class PTYManager:
    def __init__(self):
        self.sessions: Dict[int, PTYSession] = {}

    def create_session(self, thread_id: int, thread: discord.Thread, shell_type: str = "powershell", cwd: str = None) -> PTYSession:
        shell_exe = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" if shell_type.lower() == "powershell" else r"C:\Windows\System32\cmd.exe"
        session = PTYSession(thread_id=thread_id, thread=thread, shell_cmd=shell_exe, cwd=cwd)
        session.start()
        self.sessions[thread_id] = session
        return session

    def get_session(self, thread_id: int) -> Optional[PTYSession]:
        session = self.sessions.get(thread_id)
        if session and session.is_running:
            return session
        if session and not session.is_running:
            self.sessions.pop(thread_id, None)
        return None

    def close_session(self, thread_id: int) -> bool:
        session = self.sessions.pop(thread_id, None)
        if session:
            session.stop()
            return True
        return False

# Global manager instance
pty_manager = PTYManager()

import os
import shutil
import sqlite3
import tempfile
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
import discord

DB_PATH = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db')

class ToastNotificationWatcher:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.target_channel_id: Optional[int] = None
        self.last_order_id: int = 0
        self.is_running = False
        self._init_last_order()

    def _init_last_order(self):
        """Finds current max order ID so we only send fresh notifications going forward."""
        if not os.path.isfile(DB_PATH):
            return
        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            shutil.copy2(DB_PATH, tmp)
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            res = cur.execute("SELECT MAX([Order]) FROM Notification").fetchone()
            if res and res[0] is not None:
                self.last_order_id = int(res[0])
            conn.close()
            try:
                os.remove(tmp)
            except Exception:
                pass
        except Exception:
            pass

    def parse_toast_xml(self, payload_raw: str) -> tuple[str, str]:
        """Extracts title and message body from toast XML payload."""
        if not payload_raw:
            return "Windows Notification", ""
        try:
            root = ET.fromstring(payload_raw)
            texts = [elem.text.strip() for elem in root.iter('text') if elem.text and elem.text.strip()]
            title = texts[0] if len(texts) > 0 else "Notification"
            body = "\n".join(texts[1:]) if len(texts) > 1 else ""
            return title, body
        except Exception:
            # Fallback regex/strip if malformed XML
            cleaned = payload_raw.replace("<toast>", "").replace("</toast>", "")
            return "Notification", cleaned[:300]

    async def start_listening(self, channel_id: int):
        self.target_channel_id = channel_id
        self.is_running = True
        
        while self.is_running:
            await asyncio.sleep(4.0)
            if not self.target_channel_id or not os.path.isfile(DB_PATH):
                continue

            try:
                # Read new notifications
                new_notifications = await asyncio.to_thread(self._fetch_new_notifications)
                if not new_notifications:
                    continue

                channel = self.bot.get_channel(self.target_channel_id)
                if not channel:
                    continue

                for order, app_id, payload in new_notifications:
                    title, body = self.parse_toast_xml(payload)
                    app_name = app_id.split("!")[-1] if app_id else "Windows System"
                    
                    embed = discord.Embed(
                        title=f"🔔 {app_name}",
                        description=f"**{title}**\n{body}" if body else f"**{title}**",
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"Toast ID: {order}")
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass

            except Exception:
                pass

    def _fetch_new_notifications(self) -> list:
        tmp = ""
        results = []
        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            shutil.copy2(DB_PATH, tmp)
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            query = """
                SELECT n.[Order], h.PrimaryId, n.Payload
                FROM Notification n
                LEFT JOIN NotificationHandler h ON n.HandlerId = h.RecordId
                WHERE n.[Order] > ?
                ORDER BY n.[Order] ASC
                LIMIT 10
            """
            rows = cur.execute(query, (self.last_order_id,)).fetchall()
            for r in rows:
                order = int(r[0])
                app_id = r[1] or "Windows"
                payload = r[2]
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8', errors='ignore')
                results.append((order, app_id, payload))
                if order > self.last_order_id:
                    self.last_order_id = order
            conn.close()
        except Exception:
            pass
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        return results

    def stop(self):
        self.is_running = False

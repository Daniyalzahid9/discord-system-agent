import os
import io
import asyncio
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

import config
import system_controller as sys_ctl
import email_service
from pty_manager import pty_manager
import hardware_sensor as hw
import ui_automation as ui
from notification_listener import ToastNotificationWatcher
from web_remote_server import web_remote_server

# Setup Discord Bot Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None)
toast_watcher = ToastNotificationWatcher(bot)

# ----------------- SECURITY CHECK -----------------
def is_owner(user_id: int) -> bool:
    return config.is_authorized(user_id)

async def check_auth_interaction(interaction: discord.Interaction) -> bool:
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            f"🚫 **Access Denied.** Your User ID (`{interaction.user.id}`) is not authorized in `.env`.",
            ephemeral=True
        )
        return False
    return True

# ----------------- DISCORD-NATIVE REMOTE CONTROLLER -----------------
class DiscordTypeModal(discord.ui.Modal, title="Type on Windows PC"):
    text_input = discord.ui.TextInput(
        label="Text or Code to Type",
        style=discord.TextStyle.paragraph,
        placeholder="Type text, commands, or paste code to send to PC...",
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("🚫 Access Denied", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        import pyautogui
        pyautogui.write(self.text_input.value, interval=0.01)
        file = await asyncio.to_thread(sys_ctl.capture_screen, quality=75)
        await interaction.followup.send(
            content=f"⌨️ **Typed on PC:** `{self.text_input.value[:80]}...`\n**Live Screen Result:**",
            file=file,
            ephemeral=True
        )

class StreamLinkView(discord.ui.View):
    def __init__(self, url: str, pin: str):
        super().__init__(timeout=600)
        self.url = url
        self.pin = pin
        # Direct Clickable Link Button for mobile browser
        self.add_item(discord.ui.Button(label="🚀 Open 50 FPS Stream", style=discord.ButtonStyle.link, url=url))

    @discord.ui.button(label="📋 Copy Link Only", style=discord.ButtonStyle.secondary, emoji="🔗")
    async def copy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Replies with ONLY the raw URL for clean 1-tap clipboard copying on phone
        await interaction.response.send_message(self.url, ephemeral=True)

    @discord.ui.button(label="🔑 Copy PIN Only", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def pin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Replies with ONLY the raw 6-digit PIN
        await interaction.response.send_message(self.pin, ephemeral=True)

class DiscordRemoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="📸 Refresh", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        await interaction.response.defer()
        file = await asyncio.to_thread(sys_ctl.capture_screen, quality=80)
        stats = sys_ctl.get_system_stats()
        await interaction.followup.send(
            content=f"📸 **Desktop Live View** (`{stats['uptime']}` | CPU `{stats['cpu_percent']}`)",
            file=file,
            view=DiscordRemoteView()
        )

    @discord.ui.button(label="⌨️ Type Text", style=discord.ButtonStyle.success, emoji="💬", row=0)
    async def type_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        await interaction.response.send_modal(DiscordTypeModal())

    @discord.ui.button(label="🖱️ Left Click", style=discord.ButtonStyle.secondary, emoji="👆", row=0)
    async def lclick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        sys_ctl._attach_to_default_desktop()
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        await interaction.response.send_message("🖱️ Left Click sent.", ephemeral=True)

    @discord.ui.button(label="🖱️ Right Click", style=discord.ButtonStyle.secondary, emoji="👉", row=0)
    async def rclick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        sys_ctl._attach_to_default_desktop()
        ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
        await interaction.response.send_message("🖱️ Right Click sent.", ephemeral=True)

    @discord.ui.button(label="⌨️ Windows OSK", style=discord.ButtonStyle.primary, emoji="🪟", row=1)
    async def osk_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        os.system("start osk.exe")
        await interaction.response.send_message("⌨️ Launched Windows On-Screen Keyboard on laptop.", ephemeral=True)

    @discord.ui.button(label="Alt+Tab", style=discord.ButtonStyle.secondary, emoji="🔁", row=1)
    async def alttab_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        import pyautogui
        pyautogui.hotkey("alt", "tab")
        await interaction.response.send_message("🔁 Pressed Alt+Tab.", ephemeral=True)

    @discord.ui.button(label="Enter ↵", style=discord.ButtonStyle.secondary, emoji="⏎", row=1)
    async def enter_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        import pyautogui
        pyautogui.press("enter")
        await interaction.response.send_message("⏎ Pressed Enter.", ephemeral=True)

    @discord.ui.button(label="🔒 Lock PC", style=discord.ButtonStyle.danger, emoji="🔐", row=1)
    async def lock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        ok, msg = sys_ctl.power_action("lock")
        await interaction.response.send_message(f"🔒 {msg}", ephemeral=True)

    @discord.ui.button(label="🌐 50fps Web Stream", style=discord.ButtonStyle.success, emoji="📱", row=2)
    async def stream_link_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction): return
        await interaction.response.defer(ephemeral=True)
        url, pin = await web_remote_server.start()
        await interaction.followup.send(
            content=f"🎮 **50 FPS Web Touch Stream:**\n👉 **`{url}`**\n🔑 **Access PIN:** `{pin}`\n*(Hardware-accelerated OpenCV 50 FPS • Draggable Mousepad • 2-Finger Pinch Zoom)*",
            view=StreamLinkView(url, pin),
            ephemeral=True
        )

# ----------------- INTERACTIVE BUTTON VIEW -----------------
class QuickControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📸 Screen", style=discord.ButtonStyle.primary, emoji="🖥️")
    async def screenshot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        await interaction.response.defer()
        file = await asyncio.to_thread(sys_ctl.capture_screen, quality=80)
        await interaction.followup.send(content="📸 **Current Desktop View:**", file=file, view=QuickControlView())

    @discord.ui.button(label="🎬 Motion", style=discord.ButtonStyle.primary, emoji="🎞️")
    async def motion_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        await interaction.response.defer()
        file = await asyncio.to_thread(hw.capture_screen_motion, 3, 5)
        await interaction.followup.send(content="🎬 **3-Second Screen Motion:**", file=file, view=QuickControlView())

    @discord.ui.button(label="⚡ Stats", style=discord.ButtonStyle.secondary, emoji="📊")
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        await interaction.response.defer()
        stats = sys_ctl.get_system_stats()
        embed = build_stats_embed(stats)
        await interaction.followup.send(embed=embed, view=QuickControlView())

    @discord.ui.button(label="📷 Webcam", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def webcam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        await interaction.response.defer()
        try:
            file = await asyncio.to_thread(hw.capture_webcam, 0)
            await interaction.followup.send(content="👁️ **Webcam Room View:**", file=file, view=QuickControlView())
        except Exception as e:
            await interaction.followup.send(f"❌ Webcam capture failed: {e}")

    @discord.ui.button(label="📱 Touch Remote", style=discord.ButtonStyle.success, emoji="🎮")
    async def stream_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        url, pin = await web_remote_server.start()
        await interaction.followup.send(
            content=f"🎮 **50 FPS Mobile Touch Remote Active!**\n👉 **`{url}`**\n🔑 **Access PIN:** `{pin}`\n*(Enter this PIN in your phone's browser to unlock)*",
            view=StreamLinkView(url, pin),
            ephemeral=True
        )

    @discord.ui.button(label="🔒 Lock", style=discord.ButtonStyle.danger, emoji="🔐")
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await check_auth_interaction(interaction):
            return
        ok, msg = sys_ctl.power_action("lock")
        await interaction.response.send_message(f"🔒 {msg}")

def build_stats_embed(stats: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🖥️ Windows System Telemetry",
        color=discord.Color.brand_green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="CPU Usage", value=f"`{stats['cpu_percent']}%`", inline=True)
    embed.add_field(name="RAM Usage", value=f"`{stats['ram_used_gb']} GB / {stats['ram_total_gb']} GB ({stats['ram_percent']}%)`", inline=True)
    embed.add_field(name="Disk (C:)", value=f"`{stats['disk_free_gb']} GB Free / {stats['disk_total_gb']} GB ({stats['disk_percent']}%)`", inline=True)
    embed.add_field(name="Battery", value=f"`{stats['battery']}`", inline=True)
    embed.add_field(name="Uptime", value=f"`{stats['uptime']}`", inline=True)
    embed.add_field(name="Processes", value=f"`{stats['active_processes']} running`", inline=True)
    embed.set_footer(text="Discord Sentient PC Remote")
    return embed

# ----------------- EVENTS -----------------
@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print(f"Authorized User IDs: {config.ALLOWED_USER_IDS}")
    print(f"Default Workspace: {config.DEFAULT_WORKSPACE}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands successfully.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")
    print(f"Agent 10/10 Sentient Remote Controller Ready.")
    print(f"==================================================")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Check authorization
    if not is_owner(message.author.id):
        if message.content.startswith(config.COMMAND_PREFIX):
            await message.reply(f"🚫 **Access Denied.** Your User ID is `{message.author.id}`. Add it to `.env`.")
        return

    # 1. Route message to active PTY interactive shell session if in a PTY Thread
    if isinstance(message.channel, discord.Thread):
        pty_session = pty_manager.get_session(message.channel.id)
        if pty_session:
            if message.content.strip().lower() in ["exit", "/exit", "quit"]:
                pty_manager.close_session(message.channel.id)
                await message.reply("🔌 PTY shell terminated.")
                return
            pty_session.write_input(message.content)
            return

    # 2. File Upload Handler: If attachments are sent, download them to PC
    if message.attachments:
        dest_dir = Path(config.DEFAULT_WORKSPACE) / "discord_downloads"
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        for att in message.attachments:
            target_path = dest_dir / att.filename
            await att.save(target_path)
            saved_files.append(str(target_path))
        
        await message.reply(f"📥 **Saved {len(saved_files)} file(s) to PC:**\n" + "\n".join(f"`{p}`" for p in saved_files))
        return

    await bot.process_commands(message)

# ----------------- SLASH COMMANDS (UPGRADED 10/10 SUITE) -----------------

# 0. DISCORD-NATIVE REMOTE & 30FPS TOUCH STREAM
@bot.tree.command(name="remote", description="Opens Discord Native Remote Control Center (Zero browser needed, 100% in Discord).")
async def slash_remote(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    file = await asyncio.to_thread(sys_ctl.capture_screen, quality=80)
    stats = sys_ctl.get_system_stats()
    content = (
        f"📱 **Discord Native Remote Controller**\n"
        f"`{stats['uptime']}` | CPU `{stats['cpu_percent']}%` | RAM `{stats['ram_used_gb']}/{stats['ram_total_gb']}GB`\n"
        f"*(Zero browser needed. Tap buttons below to click, type, alt+tab, launch OSK or refresh)*"
    )
    await interaction.followup.send(content=content, file=file, view=DiscordRemoteView())

# 1. PERSISTENT PTY SESSIONS
@bot.tree.command(name="shell", description="Starts or controls a persistent interactive PTY terminal thread.")
@app_commands.describe(
    action="start or stop",
    shell_type="powershell or cmd (default: powershell)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Start Interactive Shell Session", value="start"),
    app_commands.Choice(name="Stop Active Shell Session", value="stop")
], shell_type=[
    app_commands.Choice(name="PowerShell", value="powershell"),
    app_commands.Choice(name="Command Prompt (cmd)", value="cmd")
])
async def slash_shell(interaction: discord.Interaction, action: app_commands.Choice[str], shell_type: Optional[app_commands.Choice[str]] = None):
    if not await check_auth_interaction(interaction):
        return
    
    stype = shell_type.value if shell_type else "powershell"

    if action.value == "start":
        await interaction.response.defer()
        thread_name = f"💻 PTY Shell ({stype}) - {datetime.now().strftime('%H:%M:%S')}"
        thread = await interaction.channel.create_thread(
            name=thread_name,
            auto_archive_duration=60,
            type=discord.ChannelType.public_thread
        )
        session = pty_manager.create_session(thread_id=thread.id, thread=thread, shell_type=stype, cwd=config.DEFAULT_WORKSPACE)
        await interaction.followup.send(f"🚀 **Spawned Interactive PTY Session** in thread: {thread.jump_url}\nType any command directly in that thread to interact with the shell!")
        await thread.send(f"🟢 **Persistent {stype.upper()} PTY Connected.**\nWorking Directory: `{config.DEFAULT_WORKSPACE}`\nType `exit` or use `/shell stop` to close.")

    elif action.value == "stop":
        thread_id = interaction.channel.id
        closed = pty_manager.close_session(thread_id)
        if closed:
            await interaction.response.send_message("🔌 PTY Session closed.")
        else:
            await interaction.response.send_message("❌ This channel is not an active PTY session thread.", ephemeral=True)

# 2. COMPUTER VISION & NATIVE UI AUTOMATION
@bot.tree.command(name="focus", description="Brings an application window to the foreground.")
@app_commands.describe(window_title="Name or partial title of the window (e.g. Chrome, Code, Notepad)")
async def slash_focus(interaction: discord.Interaction, window_title: str):
    if not await check_auth_interaction(interaction):
        return
    ok, msg = await asyncio.to_thread(ui.focus_window_by_title, window_title)
    await interaction.response.send_message(f"{'🎯' if ok else '❌'} {msg}")

@bot.tree.command(name="window_controls", description="Lists interactive buttons and controls in the active window.")
async def slash_window_controls(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    controls = await asyncio.to_thread(ui.list_window_controls)
    if not controls:
        await interaction.followup.send("⚠️ No controls detected in active window.")
    else:
        text = "\n".join(controls)
        await interaction.followup.send(f"📋 **Detected Window Controls:**\n```text\n{text[:1800]}\n```")

# 3. REAL-TIME CLIPBOARD MIRRORING
@bot.tree.command(name="clip", description="Bi-directional clipboard sync between mobile Discord and your PC.")
@app_commands.describe(action="get or set", text="Text to copy to PC clipboard (for 'set')")
@app_commands.choices(action=[
    app_commands.Choice(name="Get text currently on laptop clipboard", value="get"),
    app_commands.Choice(name="Set text to laptop clipboard", value="set")
])
async def slash_clip(interaction: discord.Interaction, action: app_commands.Choice[str], text: Optional[str] = None):
    if not await check_auth_interaction(interaction):
        return
    
    if action.value == "get":
        clip_content = await asyncio.to_thread(ui.get_clipboard_text)
        if not clip_content:
            await interaction.response.send_message("📋 Clipboard is currently empty.")
        else:
            await interaction.response.send_message(f"📋 **Laptop Clipboard:**\n```text\n{clip_content[:1800]}\n```")
    elif action.value == "set":
        if not text:
            await interaction.response.send_message("❌ Please provide text to set to the clipboard.", ephemeral=True)
            return
        await asyncio.to_thread(ui.set_clipboard_text, text)
        await interaction.response.send_message(f"📋 **Copied to Laptop Clipboard:** `{text[:100]}...` (Ready to Ctrl+V on PC)")

# 4. HARDWARE PRESENCE: WEBCAM, MIC, TTS
@bot.tree.command(name="webcam", description="Takes a photo using your laptop's front camera.")
async def slash_webcam(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    try:
        file = await asyncio.to_thread(hw.capture_webcam, 0)
        await interaction.followup.send(content="👁️ **Webcam Photo:**", file=file, view=QuickControlView())
    except Exception as e:
        await interaction.followup.send(f"❌ Webcam capture failed: {str(e)}")

@bot.tree.command(name="listen", description="Records ambient room audio from your laptop microphone.")
@app_commands.describe(duration="Recording duration in seconds (1 to 30, default: 5)")
async def slash_listen(interaction: discord.Interaction, duration: int = 5):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    try:
        file = await asyncio.to_thread(hw.record_room_audio, duration)
        await interaction.followup.send(content=f"🎙️ **Ambient Room Audio ({duration}s):**", file=file)
    except Exception as e:
        await interaction.followup.send(f"❌ Audio recording failed: {str(e)}")

@bot.tree.command(name="say", description="Speaks text out loud through your laptop speakers.")
@app_commands.describe(text="The message to speak out loud")
async def slash_say(interaction: discord.Interaction, text: str):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    ok, msg = await asyncio.to_thread(hw.speak_text, text)
    await interaction.followup.send(f"{'🔊' if ok else '❌'} {msg}")

# 5. LIVE MOTION SCREEN CLIPS
@bot.tree.command(name="motion", description="Records a 3-5 second animated preview of your laptop screen.")
@app_commands.describe(duration="Length of clip in seconds (1 to 6, default: 3)")
async def slash_motion(interaction: discord.Interaction, duration: int = 3):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    try:
        file = await asyncio.to_thread(hw.capture_screen_motion, duration, 5)
        await interaction.followup.send(content=f"🎬 **Live Screen Motion ({duration}s):**", file=file, view=QuickControlView())
    except Exception as e:
        await interaction.followup.send(f"❌ Screen motion recording failed: {str(e)}")

# 6. WINDOWS TOAST NOTIFICATION FORWARDER
@bot.tree.command(name="notifications", description="Toggle live forwarding of Windows toast notifications.")
@app_commands.describe(action="start or stop forwarding notifications to this channel")
@app_commands.choices(action=[
    app_commands.Choice(name="Start forwarding toasts to this channel", value="start"),
    app_commands.Choice(name="Stop forwarding toasts", value="stop")
])
async def slash_notifications(interaction: discord.Interaction, action: app_commands.Choice[str]):
    if not await check_auth_interaction(interaction):
        return

    if action.value == "start":
        if not toast_watcher.is_running:
            asyncio.create_task(toast_watcher.start_listening(interaction.channel_id))
        else:
            toast_watcher.target_channel_id = interaction.channel_id
        await interaction.response.send_message(f"🔔 **Windows Toast Notification Forwarder Enabled!**\nAlerts from WhatsApp, Slack, Antigravity IDE, Defender, etc., will be posted here in real time.")
    elif action.value == "stop":
        toast_watcher.stop()
        await interaction.response.send_message("🔕 Windows notification forwarding disabled.")

# ZERO-INSTALL MOBILE TOUCH REMOTE (WEBSOCKET/CANVAS)
@bot.tree.command(name="stream", description="Starts the 50 FPS mobile web touch remote server with dynamic PIN protection.")
async def slash_stream(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    try:
        await interaction.response.defer()
    except Exception:
        pass

    url, pin = await web_remote_server.start()
    embed = discord.Embed(
        title="🎮 Sentient Mobile Touch Remote (50 FPS)",
        description=(
            f"**Tap the link below on your phone to control your laptop:**\n\n"
            f"👉 **[Launch Touch Remote]({url})**\n`{url}`\n\n"
            f"🔑 **Dynamic Security PIN:** `{pin}`\n"
            f"*(Enter this 6-digit PIN on the login screen to unlock live control)*\n\n"
            f"✨ **Controls & Touch Features:**\n"
            f"• **1-Finger Tap:** Instant Left Click on desktop\n"
            f"• **2-Finger Pinch:** Dynamic Zoom (works everywhere, even black borders!)\n"
            f"• **1-Finger Drag (when zoomed):** Pan desktop viewport\n"
            f"• **Double Tap:** Reset zoom to 1.0x\n"
            f"• **Floating Mousepad:** Draggable touchpad with scroll rail\n"
            f"• **AI Pilot:** Multi-task assistant ('open chrome and open gpt and say hi')\n"
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Hardware Accelerated • 50 FPS OpenCV • End-to-End Encrypted")
    view = StreamLinkView(url, pin)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
    except Exception:
        await interaction.channel.send(embed=embed, view=view)

@bot.tree.command(name="stream_stop", description="Shuts down the mobile web touch remote server.")
async def slash_stream_stop(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await web_remote_server.stop()
    await interaction.response.send_message("🛑 Mobile touch remote server stopped.")

# ----------------- STANDARD CORE COMMANDS -----------------
@bot.tree.command(name="screen", description="Captures a live screenshot of your laptop desktop.")
@app_commands.describe(scale="Scale factor (1.0 = original, 0.5 = 50%)", quality="JPEG quality (1-100)")
async def slash_screen(interaction: discord.Interaction, scale: float = 1.0, quality: int = 80):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    try:
        file = await asyncio.to_thread(sys_ctl.capture_screen, quality=quality, scale=scale)
        await interaction.followup.send(content="📸 **Desktop Screenshot:**", file=file, view=QuickControlView())
    except Exception as e:
        await interaction.followup.send(f"❌ Screenshot failed: {str(e)}")

@bot.tree.command(name="status", description="Displays CPU, RAM, Disk, Battery, and system health.")
async def slash_status(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    stats = sys_ctl.get_system_stats()
    embed = build_stats_embed(stats)
    await interaction.followup.send(embed=embed, view=QuickControlView())

@bot.tree.command(name="cmd", description="Executes a one-shot PowerShell command on your Windows computer.")
@app_commands.describe(command="The PowerShell command to run", cwd="Working directory (optional)")
async def slash_cmd(interaction: discord.Interaction, command: str, cwd: Optional[str] = None):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    code, out = await asyncio.to_thread(sys_ctl.execute_shell, command, cwd=cwd)
    
    if len(out) <= 1900:
        content = f"**Exit Code:** `{code}`\n```text\n{out or '(No output)'}\n```"
        await interaction.followup.send(content=content)
    else:
        buf = io.BytesIO(out.encode('utf-8'))
        file = discord.File(fp=buf, filename="output.txt")
        await interaction.followup.send(
            content=f"**Exit Code:** `{code}` (Output exceeded Discord limit, attached as file):",
            file=file
        )

@bot.tree.command(name="open", description="Opens a file, app, folder, or URL on your Windows PC.")
@app_commands.describe(target="Path to file/folder or app name/URL")
async def slash_open(interaction: discord.Interaction, target: str):
    if not await check_auth_interaction(interaction):
        return
    ok, msg = sys_ctl.open_path_or_app(target)
    await interaction.response.send_message(f"{'✅' if ok else '❌'} {msg}")

@bot.tree.command(name="apps", description="Lists top resource-consuming running applications.")
async def slash_apps(interaction: discord.Interaction):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    procs = sys_ctl.list_top_processes(limit=15)
    lines = ["`PID` | `CPU%` | `MEM%` | `NAME`", "---------------------------------"]
    for p in procs:
        lines.append(f"`{str(p['pid']).ljust(6)}` | `{str(p.get('cpu_percent') or 0).ljust(4)}%` | `{str(round(p.get('memory_percent') or 0, 1)).ljust(4)}%` | {p['name']}")
    embed = discord.Embed(title="Active Applications & Processes", description="\n".join(lines), color=discord.Color.dark_theme())
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="kill", description="Terminates a process by PID or name.")
@app_commands.describe(target="Process PID (e.g. 1234) or executable name (e.g. chrome)")
async def slash_kill(interaction: discord.Interaction, target: str):
    if not await check_auth_interaction(interaction):
        return
    ok, msg = sys_ctl.kill_process(target)
    await interaction.response.send_message(f"{'✅' if ok else '❌'} {msg}")

@bot.tree.command(name="download", description="Sends a file from your Windows PC to Discord.")
@app_commands.describe(file_path="Full path to the file on your computer")
async def slash_download(interaction: discord.Interaction, file_path: str):
    if not await check_auth_interaction(interaction):
        return
    path = Path(file_path)
    if not path.is_file():
        await interaction.response.send_message(f"❌ File not found: `{file_path}`", ephemeral=True)
        return
    
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > 24:
        await interaction.response.send_message(f"⚠️ File is `{round(file_size_mb, 1)} MB`. Discord free limit is 25 MB.")
        return
        
    await interaction.response.defer()
    file = discord.File(str(path), filename=path.name)
    await interaction.followup.send(content=f"📦 **File retrieved:** `{path.name}`", file=file)

@bot.tree.command(name="power", description="Control PC power state (lock, sleep, restart, shutdown).")
@app_commands.describe(action="lock, sleep, restart, shutdown, abort")
@app_commands.choices(action=[
    app_commands.Choice(name="Lock Workstation", value="lock"),
    app_commands.Choice(name="Sleep Mode", value="sleep"),
    app_commands.Choice(name="Restart PC", value="restart"),
    app_commands.Choice(name="Shutdown PC", value="shutdown"),
    app_commands.Choice(name="Abort Pending Shutdown", value="abort")
])
async def slash_power(interaction: discord.Interaction, action: app_commands.Choice[str]):
    if not await check_auth_interaction(interaction):
        return
    ok, msg = sys_ctl.power_action(action.value)
    await interaction.response.send_message(f"{'⚡' if ok else '❌'} {msg}")

@bot.tree.command(name="type", description="Simulates keyboard typing onto the active window.")
@app_commands.describe(text="The text to type")
async def slash_type(interaction: discord.Interaction, text: str):
    if not await check_auth_interaction(interaction):
        return
    ok, msg = sys_ctl.simulate_input("type", text)
    await interaction.response.send_message(f"{'⌨️' if ok else '❌'} {msg}")

@bot.tree.command(name="hotkey", description="Simulates keyboard hotkeys (e.g. 'ctrl c', 'alt tab').")
@app_commands.describe(keys="Space-separated keys (e.g. 'ctrl c', 'alt tab', 'win d')")
async def slash_hotkey(interaction: discord.Interaction, keys: str):
    if not await check_auth_interaction(interaction):
        return
    key_list = keys.strip().split()
    ok, msg = sys_ctl.simulate_input("hotkey", *key_list)
    await interaction.response.send_message(f"{'⌨️' if ok else '❌'} {msg}")

@bot.tree.command(name="email", description="Sends an email from your PC using configured SMTP.")
@app_commands.describe(to="Recipient email", subject="Email subject", body="Email message", attachment="Optional file path")
async def slash_email(interaction: discord.Interaction, to: str, subject: str, body: str, attachment: Optional[str] = None):
    if not await check_auth_interaction(interaction):
        return
    await interaction.response.defer()
    att_list = [attachment] if attachment and os.path.isfile(attachment) else None
    html = f"<div style='font-family:sans-serif;'>{body}</div>"
    ok, msg = await email_service.send_email_async(to_email=to, subject=subject, html_content=html, attachment_paths=att_list)
    await interaction.followup.send(f"{'📧' if ok else '❌'} {msg}")

# ----------------- PREFIX COMMANDS (TEXT FALLBACK) -----------------
@bot.command(name="screen")
async def cmd_screen(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    file = await asyncio.to_thread(sys_ctl.capture_screen, quality=80)
    await ctx.reply(content="📸 **Desktop View:**", file=file, view=QuickControlView())

@bot.command(name="motion")
async def cmd_motion(ctx: commands.Context, duration: int = 3):
    if not is_owner(ctx.author.id): return
    file = await asyncio.to_thread(hw.capture_screen_motion, duration, 5)
    await ctx.reply(content=f"🎬 **Screen Motion ({duration}s):**", file=file, view=QuickControlView())

@bot.command(name="webcam")
async def cmd_webcam(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    try:
        file = await asyncio.to_thread(hw.capture_webcam, 0)
        await ctx.reply(content="👁️ **Webcam Snapshot:**", file=file, view=QuickControlView())
    except Exception as e:
        await ctx.reply(f"❌ Webcam error: {e}")

@bot.command(name="listen")
async def cmd_listen(ctx: commands.Context, duration: int = 5):
    if not is_owner(ctx.author.id): return
    try:
        file = await asyncio.to_thread(hw.record_room_audio, duration)
        await ctx.reply(content=f"🎙️ **Ambient Audio ({duration}s):**", file=file)
    except Exception as e:
        await ctx.reply(f"❌ Audio error: {e}")

@bot.command(name="say")
async def cmd_say(ctx: commands.Context, *, text: str):
    if not is_owner(ctx.author.id): return
    ok, msg = await asyncio.to_thread(hw.speak_text, text)
    await ctx.reply(f"{'🔊' if ok else '❌'} {msg}")

@bot.command(name="clip")
async def cmd_clip(ctx: commands.Context, action: str = "get", *, text: str = ""):
    if not is_owner(ctx.author.id): return
    if action.lower() == "get":
        c = await asyncio.to_thread(ui.get_clipboard_text)
        await ctx.reply(f"📋 **Laptop Clipboard:**\n```text\n{c[:1800]}\n```" if c else "📋 Clipboard is empty.")
    elif action.lower() == "set":
        await asyncio.to_thread(ui.set_clipboard_text, text)
        await ctx.reply(f"📋 Copied to laptop clipboard: `{text[:80]}...`")

@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    stats = sys_ctl.get_system_stats()
    embed = build_stats_embed(stats)
    await ctx.reply(embed=embed, view=QuickControlView())

@bot.command(name="cmd")
async def cmd_cmd(ctx: commands.Context, *, command: str):
    if not is_owner(ctx.author.id): return
    code, out = await asyncio.to_thread(sys_ctl.execute_shell, command)
    if len(out) <= 1900:
        await ctx.reply(f"**Exit Code:** `{code}`\n```text\n{out or '(No output)'}\n```")
    else:
        buf = io.BytesIO(out.encode('utf-8'))
        file = discord.File(fp=buf, filename="output.txt")
        await ctx.reply(content=f"**Exit Code:** `{code}` (Output attached):", file=file)

@bot.command(name="lock")
async def cmd_lock(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    ok, msg = sys_ctl.power_action("lock")
    await ctx.reply(f"🔒 {msg}")

@bot.command(name="stream")
async def cmd_stream(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    url, pin = await web_remote_server.start()
    embed = discord.Embed(
        title="🎮 50 FPS Mobile Touch Remote Active",
        description=(
            f"👉 **[Open Remote Stream]({url})**\n`{url}`\n\n"
            f"🔑 **One-Time Access PIN:** `{pin}`\n"
            f"*(Enter this 6-digit PIN on the login screen to unlock)*"
        ),
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    await ctx.reply(embed=embed, view=StreamLinkView(url, pin))

@bot.command(name="remote")
async def cmd_remote(ctx: commands.Context):
    if not is_owner(ctx.author.id): return
    file = await asyncio.to_thread(sys_ctl.capture_screen, quality=80)
    stats = sys_ctl.get_system_stats()
    content = (
        f"📱 **Discord Native Remote Controller**\n"
        f"`{stats['uptime']}` | CPU `{stats['cpu_percent']}%` | RAM `{stats['ram_used_gb']}/{stats['ram_total_gb']}GB`\n"
        f"*(Zero browser needed. Tap buttons below to click, type, alt+tab, launch OSK or refresh)*"
    )
    await ctx.reply(content=content, file=file, view=DiscordRemoteView())

def run():
    token = config.DISCORD_BOT_TOKEN
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("=" * 65)
        print("❌ CONFIGURATION NEEDED:")
        print("  1. Open: C:\\Users\\daniy\\discord_system_agent\\.env")
        print("  2. Set DISCORD_BOT_TOKEN to your bot token from Discord Developer Portal")
        print("  3. Set ALLOWED_USER_IDS to your Discord User ID")
        print("=" * 65)
        return

    if token.startswith("http://") or token.startswith("https://"):
        print("=" * 65)
        print("❌ WRONG TOKEN VALUE IN .ENV:")
        print("  You pasted the OAuth2 Invite Link (https://discord.com/...)!")
        print("  You need the secret BOT TOKEN instead.")
        print()
        print("  HOW TO GET IT:")
        print("  1. Go to: https://discord.com/developers/applications")
        print("  2. Click your application (Client ID: 1566168086107656222)")
        print("  3. In the left menu, click 'Bot'")
        print("  4. Under the username, click 'Reset Token' (and confirm)")
        print("  5. Click 'Copy' to copy the real bot token")
        print("  6. Paste it into C:\\Users\\daniy\\discord_system_agent\\.env")
        print("=" * 65)
        return

    if not config.ALLOWED_USER_IDS:
        print("=" * 65)
        print("⚠️ WARNING: ALLOWED_USER_IDS is not set in .env!")
        print("  Nobody will be authorized to trigger commands.")
        print("  Please add your Discord User ID to ALLOWED_USER_IDS in .env.")
        print("=" * 65)

    bot.run(token)

if __name__ == "__main__":
    run()

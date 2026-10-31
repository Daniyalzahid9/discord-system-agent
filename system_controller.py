import io
import os
import time
import ctypes
import psutil
import subprocess
from datetime import datetime
from PIL import Image, ImageGrab
import pyautogui
import discord

# Disable pyautogui fail-safe delay for fast response
pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = True

def _attach_to_default_desktop():
    """Ensure the current thread is attached to the active user desktop on Windows."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

def capture_screen(quality: int = 80, scale: float = 1.0) -> discord.File:
    """Captures the current desktop and returns a compressed discord.File object."""
    _attach_to_default_desktop()
    
    # Grab screenshot using Pillow
    img = ImageGrab.grab(all_screens=True)
    
    # Draw visible hardware cursor onto the screenshot
    try:
        from PIL import ImageDraw
        pos = pyautogui.position()
        cx, cy = int(pos.x), int(pos.y)
        if 0 <= cx < img.width and 0 <= cy < img.height:
            draw = ImageDraw.Draw(img)
            shadow = [
                (cx + 1, cy + 1), (cx + 1, cy + 19), (cx + 5, cy + 15),
                (cx + 10, cy + 23), (cx + 13, cy + 22), (cx + 8, cy + 14),
                (cx + 14, cy + 14)
            ]
            draw.polygon(shadow, fill=(0, 0, 0))
            cursor = [
                (cx, cy), (cx, cy + 17), (cx + 4, cy + 13),
                (cx + 9, cy + 21), (cx + 12, cy + 20), (cx + 7, cy + 12),
                (cx + 13, cy + 12)
            ]
            draw.polygon(cursor, fill=(255, 255, 255), outline=(0, 0, 0))
            draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=(239, 68, 68))
    except Exception:
        pass

    # Resize if downscaling requested for faster mobile upload
    if scale != 1.0 and scale > 0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Compress into in-memory JPEG buffer
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return discord.File(fp=buf, filename=f"screen_{timestamp}.jpg")

def get_system_stats() -> dict:
    """Collects system health, resource usage, battery, and uptime."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    
    # Battery
    battery = psutil.sensors_battery()
    battery_info = "N/A"
    if battery:
        plugged = "[AC]" if battery.power_plugged else "[Battery]"
        battery_info = f"{battery.percent}% {plugged}"
        
    # Uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_duration = datetime.now() - boot_time
    hours, remainder = divmod(int(uptime_duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    return {
        "cpu_percent": cpu_percent,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_percent": mem.percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "battery": battery_info,
        "uptime": uptime_str,
        "active_processes": len(psutil.pids())
    }

def execute_shell(command: str, cwd: str = None, timeout: int = 120) -> tuple[int, str]:
    """Executes a PowerShell command synchronously and returns (exit_code, output)."""
    target_cwd = cwd if cwd and os.path.isdir(cwd) else None
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=target_cwd,
            text=True,
            timeout=timeout,
            errors="replace"
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return -1, f"Command timed out after {timeout} seconds."
    except Exception as e:
        return -1, f"Execution failed: {str(e)}"

def list_top_processes(limit: int = 15) -> list[dict]:
    """Returns top resource consuming processes."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # Sort by memory percent descending
    procs.sort(key=lambda x: x.get('memory_percent') or 0, reverse=True)
    return procs[:limit]

def kill_process(target: str) -> tuple[bool, str]:
    """Kills a process by PID or image name."""
    if target.isdigit():
        pid = int(target)
        try:
            p = psutil.Process(pid)
            name = p.name()
            p.kill()
            return True, f"Killed process {name} (PID: {pid})"
        except psutil.NoSuchProcess:
            return False, f"PID {pid} not found."
        except Exception as e:
            return False, f"Failed to kill PID {pid}: {str(e)}"
    else:
        # Kill by name
        killed = 0
        target_lower = target.lower()
        if not target_lower.endswith(".exe"):
            target_lower += ".exe"
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if p.info['name'] and p.info['name'].lower() == target_lower:
                    p.kill()
                    killed += 1
            except Exception:
                pass
        if killed > 0:
            return True, f"Terminated {killed} instance(s) of '{target}'"
        return False, f"No running process found matching '{target}'"

def launch_antigravity_ide(workspace: str = None) -> tuple[bool, str]:
    """Launches the full Antigravity desktop IDE GUI on Windows."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity IDE" / "Antigravity IDE.exe",
        Path("C:/Users/daniy/AppData/Local/Programs/antigravity/Antigravity.exe"),
        Path("C:/Users/daniy/AppData/Local/Programs/Antigravity IDE/Antigravity IDE.exe"),
    ]
    for exe in candidates:
        if exe.is_file():
            try:
                cmd = f'"{exe}"'
                if workspace and os.path.isdir(workspace):
                    cmd += f' "{workspace}"'
                subprocess.Popen(cmd, shell=True)
                return True, f"Launched Antigravity IDE ({exe.name})"
            except Exception as e:
                return False, f"Failed launching {exe}: {e}"
    # Fallback to start command
    try:
        os.system("start antigravity:")
        return True, "Triggered Antigravity application launcher."
    except Exception as e:
        return False, f"Antigravity IDE executable not found: {e}"

def open_path_or_app(target: str) -> tuple[bool, str]:
    """Opens a file, directory, application, or URL on Windows with intelligent resolution."""
    t_clean = target.strip()
    t_low = t_clean.lower()

    # Smart Target Aliases
    if t_low in ["gpt", "chatgpt", "open gpt", "chat gpt"]:
        os.startfile("https://chatgpt.com")
        return True, "Opened ChatGPT (https://chatgpt.com)"
    elif t_low in ["yt", "youtube"]:
        os.startfile("https://www.youtube.com")
        return True, "Opened YouTube (https://www.youtube.com)"
    elif t_low in ["antigravity", "antigravity ide", "agy"]:
        return launch_antigravity_ide()
    elif t_low == "chrome":
        os.system("start chrome.exe")
        return True, "Launched Google Chrome"
    elif t_low in ["notepad", "note"]:
        os.system("start notepad.exe")
        return True, "Launched Notepad"
    elif t_low in ["calc", "calculator"]:
        os.system("start calc.exe")
        return True, "Launched Windows Calculator"
    elif t_low in ["code", "vscode", "vs code"]:
        os.system("code .")
        return True, "Launched Visual Studio Code"

    try:
        os.startfile(t_clean)
        return True, f"Opened: {t_clean}"
    except Exception as e:
        # Fallback to shell start
        try:
            os.system(f'start "" "{t_clean}"')
            return True, f"Started: {t_clean}"
        except Exception:
            return False, f"Failed to open '{t_clean}': {str(e)}"

def simulate_input(action_type: str, *args) -> tuple[bool, str]:
    """Simulates keyboard or mouse events."""
    _attach_to_default_desktop()
    try:
        if action_type == "type":
            text = args[0]
            pyautogui.write(text, interval=0.02)
            return True, f"Typed text ({len(text)} chars)"
        elif action_type == "hotkey":
            pyautogui.hotkey(*args)
            return True, f"Pressed hotkey: {' + '.join(args)}"
        elif action_type == "click":
            x, y = int(args[0]), int(args[1])
            pyautogui.click(x, y)
            return True, f"Clicked at ({x}, {y})"
        elif action_type == "press":
            key = args[0]
            pyautogui.press(key)
            return True, f"Pressed key: {key}"
        return False, f"Unknown action: {action_type}"
    except Exception as e:
        return False, f"Input error: {str(e)}"

def power_action(action: str) -> tuple[bool, str]:
    """Executes Windows system power operations."""
    act = action.lower().strip()
    if act == "lock":
        ctypes.windll.user32.LockWorkStation()
        return True, "Workstation locked."
    elif act == "sleep":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return True, "Entering sleep mode."
    elif act == "restart":
        subprocess.run(["shutdown.exe", "/r", "/t", "5"])
        return True, "System will restart in 5 seconds."
    elif act == "shutdown":
        subprocess.run(["shutdown.exe", "/s", "/t", "10"])
        return True, "System will shut down in 10 seconds."
    elif act == "abort":
        subprocess.run(["shutdown.exe", "/a"])
        return True, "Aborted pending shutdown/restart."
    return False, f"Invalid power action: '{action}'. Options: lock, sleep, restart, shutdown, abort."

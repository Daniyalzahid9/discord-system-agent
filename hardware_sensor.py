import io
import time
import wave
import ctypes
from datetime import datetime
import cv2
import sounddevice as sd
import numpy as np
from PIL import Image, ImageGrab
import imageio
import pyttsx3
import discord

def _attach_to_default_desktop():
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

def capture_webcam(device_index: int = 0) -> discord.File:
    """Captures a snapshot from the laptop's front webcam."""
    cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device_index)
        if not cap.isOpened():
            raise RuntimeError(f"Webcam device {device_index} could not be opened or is in use.")

    # Warm up camera for a couple frames to adjust auto-exposure
    for _ in range(4):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Failed to capture image frame from webcam.")

    # Encode to JPEG
    success, encoded_img = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not success:
        raise RuntimeError("Failed to compress webcam image frame.")

    buf = io.BytesIO(encoded_img.tobytes())
    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return discord.File(fp=buf, filename=f"webcam_{timestamp}.jpg")

def record_room_audio(duration: int = 5, samplerate: int = 16000) -> discord.File:
    """Records ambient room audio from the microphone and returns a WAV audio file."""
    if duration > 30:
        duration = 30  # Cap duration to prevent massive files
    if duration < 1:
        duration = 1

    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(recording.tobytes())

    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return discord.File(fp=buf, filename=f"room_audio_{timestamp}.wav")

def speak_text(text: str, rate: int = 175) -> tuple[bool, str]:
    """Speaks text out loud through laptop speakers using Windows SAPI5 TTS."""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine
        return True, f"Spoke out loud: \"{text[:100]}\""
    except Exception as e:
        return False, f"TTS error: {str(e)}"

def capture_screen_motion(duration: int = 3, fps: int = 5) -> discord.File:
    """Captures a short animated GIF of screen motion (3-5 seconds)."""
    _attach_to_default_desktop()
    if duration > 6:
        duration = 6
    if duration < 1:
        duration = 1

    total_frames = int(duration * fps)
    interval = 1.0 / fps
    frames = []

    for _ in range(total_frames):
        start_t = time.time()
        img = ImageGrab.grab(all_screens=False)
        # Draw visible hardware cursor onto each frame of motion
        try:
            from PIL import ImageDraw
            import pyautogui
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
        # Downscale 50% for fast animated GIF delivery to mobile
        resized = img.resize((img.width // 2, img.height // 2), Image.Resampling.BILINEAR)
        frames.append(resized)
        elapsed = time.time() - start_t
        if interval > elapsed:
            time.sleep(interval - elapsed)

    buf = io.BytesIO()
    imageio.mimsave(buf, frames, format='GIF', duration=interval, loop=0)
    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return discord.File(fp=buf, filename=f"motion_{timestamp}.gif")

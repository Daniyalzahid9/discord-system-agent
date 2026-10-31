import os
import io
import time
import json
import re
import socket
import secrets
import asyncio
import ctypes
import urllib.parse
from pathlib import Path
from typing import Optional, Set, List, Tuple
from aiohttp import web
import cv2
import numpy as np
import mss
import pyautogui
import config
import system_controller as sys_ctl

# Win32 Mouse & Keyboard Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000

user32 = ctypes.windll.user32

def _attach_to_default_desktop():
    """Ensure current thread is attached to the active user desktop on Windows."""
    try:
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

def get_local_ip() -> str:
    """Discovers local LAN IPv4 address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

# ----------------- 50 FPS HIGH PERFORMANCE HTML5 CLIENT -----------------
HTML_CLIENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
<title>Sentient Remote Pro — 50 FPS</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-touch-callout: none; -webkit-user-select: none; user-select: none; }
  body, html {
    width: 100vw; height: 100dvh; overflow: hidden; background: #06080d;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #fff;
  }

  /* STAGE VIEWPORT */
  #stage {
    position: absolute; top: 0; left: 0; width: 100vw; height: 100dvh;
    display: flex; align-items: center; justify-content: center;
    background: #000; overflow: hidden; touch-action: none;
    transition: transform 0.25s cubic-bezier(0.2, 0.9, 0.4, 1.1);
  }

  #canvas-container {
    position: relative; display: flex; align-items: center; justify-content: center;
    transform-origin: center center; will-change: transform;
  }

  /* View Modes */
  #stage.mode-fit #screen-canvas {
    max-width: 100vw; max-height: 100dvh; width: 100%; height: auto; object-fit: contain;
  }
  #stage.mode-fill #screen-canvas {
    width: 100vw; height: 100dvh; object-fit: fill;
  }
  #stage.mode-rotated {
    transform: rotate(90deg);
    transform-origin: center center;
    width: 100dvh !important;
    height: 100dvw !important;
    position: fixed;
    top: calc((100dvh - 100dvw) / 2);
    left: calc((100dvw - 100dvh) / 2);
  }
  #stage.mode-rotated #screen-canvas {
    width: 100dvh; height: 100dvw; object-fit: contain;
  }

  #screen-canvas {
    display: block; box-shadow: 0 0 50px rgba(0, 0, 0, 0.95);
    cursor: default; touch-action: none; image-rendering: auto;
  }

  /* PREDICTIVE CLIENT-SIDE HARDWARE CURSOR */
  #client-cursor {
    position: absolute; width: 18px; height: 22px; pointer-events: none; z-index: 1000;
    transform: translate(-1px, -1px); display: none; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
  }

  /* TOP HUD */
  .hud-top {
    position: absolute; top: 8px; left: 8px; right: 8px; display: flex;
    justify-content: space-between; align-items: center;
    background: rgba(13, 17, 26, 0.88); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 16px; padding: 6px 10px;
    z-index: 100; transition: all 0.25s ease;
  }
  .hud-top.hidden { transform: translateY(-75px); opacity: 0; pointer-events: none; }
  .status-badge { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 800; color: #10b981; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 10px #10b981; }
  
  .hud-actions { display: flex; gap: 5px; flex-wrap: nowrap; overflow-x: auto; }
  .btn-hud {
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14);
    color: #e2e8f0; padding: 6px 9px; border-radius: 10px; font-size: 11px; font-weight: 700;
    cursor: pointer; transition: all 0.15s; white-space: nowrap; display: flex; align-items: center; gap: 4px;
  }
  .btn-hud:active { background: rgba(59, 130, 246, 0.4); transform: scale(0.95); }
  .btn-hud.active { background: #3b82f6; border-color: #60a5fa; color: #fff; }

  /* RESTORE HUD BUTTON (FOR FULLSCREEN) */
  #btn-hud-restore {
    position: absolute; top: 12px; right: 12px; width: 38px; height: 38px;
    background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 50%; display: none; align-items: center; justify-content: center;
    color: #fff; font-size: 16px; z-index: 150; cursor: pointer; backdrop-filter: blur(12px);
  }

  /* BOTTOM DOCK */
  .hud-bottom {
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); display: flex; gap: 5px;
    background: rgba(13, 17, 26, 0.88); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 28px; padding: 4px 8px;
    z-index: 100; transition: all 0.25s ease; max-width: 96vw; overflow-x: auto;
  }
  .hud-bottom.hidden { transform: translate(-50%, 75px); opacity: 0; pointer-events: none; }
  .dock-btn {
    background: transparent; border: none; color: #cbd5e1; padding: 7px 9px;
    font-size: 12px; font-weight: 600; border-radius: 20px; cursor: pointer;
    display: flex; align-items: center; gap: 4px; white-space: nowrap;
  }
  .dock-btn:active { background: rgba(255, 255, 255, 0.15); }
  .dock-btn.ai { color: #c084fc; font-weight: 700; }

  /* FLOATING COMPACT ROUNDED MOUSEPAD */
  #floating-mousepad {
    position: absolute; bottom: 65px; right: 12px; width: 185px; height: 190px;
    background: rgba(15, 23, 42, 0.92); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 22px;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.7), 0 0 15px rgba(59, 130, 246, 0.3);
    display: flex; flex-direction: column; overflow: hidden; z-index: 110; touch-action: none;
  }
  .pad-header {
    height: 28px; background: rgba(255, 255, 255, 0.07); display: flex; align-items: center;
    justify-content: space-between; padding: 0 10px; font-size: 10px; font-weight: 800;
    color: #94a3b8; cursor: move; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .pad-drag-title { display: flex; align-items: center; gap: 4px; pointer-events: none; }
  .pad-controls { display: flex; gap: 8px; }
  .pad-ctrl-btn { cursor: pointer; color: #94a3b8; font-size: 13px; font-weight: bold; }

  .pad-body { flex: 1; display: flex; position: relative; }
  .pad-surface {
    flex: 1; background: transparent; touch-action: none; display: flex; flex-direction: column;
    align-items: center; justify-content: center; color: rgba(255, 255, 255, 0.18);
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    background-image: radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
    background-size: 14px 14px;
  }
  .pad-scroll-strip {
    width: 26px; background: rgba(255, 255, 255, 0.03); border-left: 1px dashed rgba(255, 255, 255, 0.12);
    display: flex; flex-direction: column; align-items: center; justify-content: space-between;
    padding: 6px 0; font-size: 9px; color: #64748b; touch-action: none; font-weight: 800;
  }

  .pad-buttons { height: 44px; display: flex; border-top: 1px solid rgba(255, 255, 255, 0.12); }
  .pad-btn {
    flex: 1; border: none; color: #fff; font-size: 11px; font-weight: 700;
    cursor: pointer; transition: all 0.12s; display: flex; align-items: center;
    justify-content: center; gap: 4px; touch-action: manipulation;
  }
  .pad-btn-left { background: rgba(59, 130, 246, 0.25); border-right: 1px solid rgba(255, 255, 255, 0.1); }
  .pad-btn-left:active { background: #3b82f6; }
  .pad-btn-right { background: rgba(168, 85, 247, 0.25); }
  .pad-btn-right:active { background: #a855f7; }

  /* MINIMIZED MOUSEPAD BADGE */
  #mousepad-badge {
    position: absolute; bottom: 65px; right: 14px; width: 44px; height: 44px;
    background: rgba(15, 23, 42, 0.92); border: 2px solid #3b82f6; border-radius: 50%;
    display: none; align-items: center; justify-content: center; font-size: 20px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 12px rgba(59, 130, 246, 0.4);
    z-index: 110; cursor: pointer; backdrop-filter: blur(12px);
  }

  /* DRAWERS */
  .drawer {
    position: absolute; bottom: 65px; left: 10px; right: 10px;
    background: rgba(15, 23, 42, 0.96); backdrop-filter: blur(28px); -webkit-backdrop-filter: blur(28px);
    border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 20px; padding: 12px;
    z-index: 120; display: none; animation: slideUp 0.2s ease-out; box-shadow: 0 20px 40px rgba(0,0,0,0.7);
  }
  @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  .drawer-title { font-size: 11px; font-weight: 800; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; }
  .key-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
  .key-btn {
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #fff;
    padding: 9px 4px; border-radius: 8px; font-size: 11px; font-weight: 700; text-align: center; cursor: pointer;
  }
  .key-btn:active { background: #3b82f6; }
  .key-btn.special { background: rgba(168, 85, 247, 0.28); border-color: rgba(168, 85, 247, 0.5); }

  /* FULL PC KEYBOARD */
  .pc-keyboard-grid { display: flex; flex-direction: column; gap: 4px; }
  .pc-row { display: flex; gap: 3px; justify-content: center; }
  .pc-key {
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); color: #fff;
    padding: 8px 4px; border-radius: 6px; font-size: 10px; font-weight: 700; text-align: center; flex: 1;
    min-width: 24px; cursor: pointer;
  }
  .pc-key:active { background: #3b82f6; }

  /* MULTI-TASK AI DESKTOP PILOT BAR */
  .ai-bar { display: flex; gap: 6px; }
  .ai-input {
    flex: 1; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 10px; padding: 8px 10px; color: #fff; font-size: 13px; outline: none;
  }
  .ai-submit {
    background: linear-gradient(135deg, #a855f7, #6366f1); border: none; color: #fff;
    font-weight: 800; padding: 0 14px; border-radius: 10px; cursor: pointer;
  }

  /* NATIVE INPUT BRIDGE */
  #hidden-input { position: absolute; opacity: 0; pointer-events: none; top: -100px; }

  /* TOUCH RIPPLES */
  .touch-ripple {
    position: absolute; width: 30px; height: 30px; border-radius: 50%; pointer-events: none;
    transform: translate(-50%, -50%); animation: rippleAnim 0.3s ease-out forwards; z-index: 200;
  }
  .ripple-left { border: 2px solid #3b82f6; background: rgba(59, 130, 246, 0.35); }
  .ripple-right { border: 2px solid #ef4444; background: rgba(239, 68, 68, 0.35); }
  @keyframes rippleAnim { 0% { opacity: 1; transform: translate(-50%, -50%) scale(0.3); } 100% { opacity: 0; transform: translate(-50%, -50%) scale(1.6); } }

  /* SECURITY PIN CHECKPOINT OVERLAY */
  #auth-overlay {
    position: fixed; top: 0; left: 0; width: 100vw; height: 100dvh;
    background: radial-gradient(circle at center, #0b1329 0%, #030712 100%);
    display: flex; align-items: center; justify-content: center; z-index: 10000;
    transition: opacity 0.35s ease, transform 0.35s ease;
  }
  #auth-overlay.unlocked {
    opacity: 0; transform: scale(1.04); pointer-events: none;
  }
  .auth-card {
    background: rgba(15, 23, 42, 0.90); backdrop-filter: blur(28px); -webkit-backdrop-filter: blur(28px);
    border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 26px; padding: 32px 24px;
    max-width: 360px; width: 90%; text-align: center;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(59, 130, 246, 0.2);
  }
  .auth-badge {
    display: inline-block; font-size: 10px; font-weight: 800; letter-spacing: 1.5px;
    color: #38bdf8; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.28);
    padding: 4px 10px; border-radius: 20px; margin-bottom: 14px; text-transform: uppercase;
  }
  .auth-icon { font-size: 42px; margin-bottom: 8px; filter: drop-shadow(0 0 16px rgba(56, 189, 248, 0.5)); }
  .auth-title { font-size: 20px; font-weight: 800; color: #fff; margin-bottom: 6px; letter-spacing: -0.3px; }
  .auth-desc { font-size: 12px; color: #94a3b8; line-height: 1.5; margin-bottom: 22px; }
  .pin-box-wrapper { margin-bottom: 12px; }
  #pin-input {
    width: 100%; font-size: 32px; letter-spacing: 10px; text-align: center; font-weight: 800;
    color: #38bdf8; background: rgba(255, 255, 255, 0.05); border: 2px solid rgba(56, 189, 248, 0.35);
    border-radius: 16px; padding: 10px 0; outline: none; transition: all 0.2s;
  }
  #pin-input:focus { border-color: #38bdf8; box-shadow: 0 0 20px rgba(56, 189, 248, 0.35); }
  #auth-msg { min-height: 20px; font-size: 12px; font-weight: 700; margin-bottom: 12px; color: #ef4444; }
  #btn-unlock {
    width: 100%; background: linear-gradient(135deg, #2563eb, #7c3aed); border: none; color: #fff;
    font-size: 13px; font-weight: 800; letter-spacing: 0.5px; padding: 14px 0; border-radius: 14px;
    cursor: pointer; transition: all 0.2s; box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
  }
  #btn-unlock:active { transform: scale(0.97); }
  .auth-meta { font-size: 10px; color: #64748b; margin-top: 16px; font-weight: 600; }
</style>
</head>
<body>

<!-- SECURITY PIN CHECKPOINT OVERLAY -->
<div id="auth-overlay">
  <div class="auth-card">
    <div class="auth-badge">SECURITY CHECKPOINT</div>
    <div class="auth-icon">🛡️</div>
    <h1 class="auth-title">Sentient Remote Pro</h1>
    <p class="auth-desc">Enter the 6-digit dynamic PIN generated in Discord to authorize this device.</p>
    
    <div class="pin-box-wrapper">
      <input type="password" id="pin-input" inputmode="numeric" pattern="[0-9]*" maxlength="6" placeholder="• • • • • •" autofocus autocomplete="off">
    </div>
    
    <div id="auth-msg"></div>
    
    <button id="btn-unlock" onclick="submitPin()">UNLOCK LIVE CONTROL</button>
    <div class="auth-meta">🔒 Dynamic One-Time Token • 50 FPS OpenCV SIMD</div>
  </div>
</div>

<div id="stage" class="mode-fit">
  <div id="canvas-container">
    <canvas id="screen-canvas"></canvas>
    <!-- Predictive Hardware Cursor SVG -->
    <svg id="client-cursor" viewBox="0 0 17 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M0 0V17L4 13L9 21L12 20L7 12L13 12L0 0Z" fill="white" stroke="black" stroke-width="1.2"/>
      <circle cx="1" cy="1" r="1.5" fill="#ef4444"/>
    </svg>
  </div>
</div>

<input type="text" id="hidden-input" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">

<!-- TOP HUD BAR -->
<div class="hud-top" id="hud-top">
  <div class="status-badge">
    <div class="status-dot"></div>
    <span id="fps-label">50 FPS</span>
  </div>
  <div class="hud-actions">
    <button class="btn-hud" id="btn-view-mode" title="Switch Aspect View Mode">📐 Fit</button>
    <button class="btn-hud" id="btn-rotate" title="Force Landscape 90 deg">🔄 Rotate</button>
    <button class="btn-hud" id="btn-zoom-reset" title="Reset Zoom">🔍 1.0x</button>
    <button class="btn-hud" id="btn-mousepad-toggle" title="Toggle Mousepad">🖱️ Pad</button>
    <button class="btn-hud" id="btn-fullscreen" title="Immersive Fullscreen">⛶ Full</button>
  </div>
</div>

<button id="btn-hud-restore" title="Show Controls">☰</button>

<!-- FLOATING COMPACT ROUNDED MOUSEPAD -->
<div id="floating-mousepad">
  <div class="pad-header" id="pad-drag-handle">
    <div class="pad-drag-title">
      <span>⠿</span>
      <span>TOUCHPAD</span>
    </div>
    <div class="pad-controls">
      <span class="pad-ctrl-btn" onclick="minimizeMousepad(true)" title="Minimize">—</span>
      <span class="pad-ctrl-btn" onclick="toggleMousepad(false)" title="Close">✕</span>
    </div>
  </div>
  <div class="pad-body">
    <div class="pad-surface" id="pad-surface">
      <span>Glide Pointer</span>
    </div>
    <div class="pad-scroll-strip" id="pad-scroll">
      <span>▲</span>
      <span>S</span>
      <span>▼</span>
    </div>
  </div>
  <div class="pad-buttons">
    <button class="pad-btn pad-btn-left" onmousedown="sendMouseDown('left')" onmouseup="sendMouseUp('left')" ontouchstart="sendMouseDown('left')" ontouchend="sendMouseUp('left')">🖱️ LEFT</button>
    <button class="pad-btn pad-btn-right" onmousedown="sendMouseDown('right')" onmouseup="sendMouseUp('right')" ontouchstart="sendMouseDown('right')" ontouchend="sendMouseUp('right')">RIGHT 🖱️</button>
  </div>
</div>

<!-- MINIMIZED MOUSEPAD BADGE -->
<div id="mousepad-badge" onclick="minimizeMousepad(false)">🖱️</div>

<!-- BOTTOM DOCK -->
<div class="hud-bottom" id="hud-bottom">
  <button class="dock-btn" id="dock-keyboard">⌨️ Keyboard</button>
  <button class="dock-btn" id="dock-full-kb">💻 PC Keys</button>
  <button class="dock-btn" id="dock-quick-keys">⚡ Hotkeys</button>
  <button class="dock-btn ai" id="dock-ai">✨ AI Pilot</button>
  <button class="dock-btn" id="dock-osk" onclick="launchOSK()">🪟 OSK</button>
  <button class="dock-btn" id="dock-lock">🔒 Lock</button>
</div>

<!-- Quick Hotkeys Drawer -->
<div class="drawer" id="drawer-keys">
  <div class="drawer-title">⚡ Quick Windows Hotkeys</div>
  <div class="key-grid">
    <div class="key-btn" onclick="sendKey('win')">🪟 Windows</div>
    <div class="key-btn" onclick="sendHotkey(['alt', 'tab'])">Alt+Tab</div>
    <div class="key-btn" onclick="sendKey('esc')">Esc</div>
    <div class="key-btn" onclick="sendKey('enter')">Enter ↵</div>
    <div class="key-btn" onclick="sendHotkey(['ctrl', 'c'])">Ctrl+C</div>
    <div class="key-btn" onclick="sendHotkey(['ctrl', 'v'])">Ctrl+V</div>
    <div class="key-btn" onclick="sendHotkey(['ctrl', 'z'])">Ctrl+Z</div>
    <div class="key-btn special" onclick="launchOSK()">⌨️ Windows OSK</div>
  </div>
</div>

<!-- Full Virtual PC Keyboard Drawer -->
<div class="drawer" id="drawer-full-kb">
  <div class="drawer-title">💻 Virtual PC Keyboard</div>
  <div class="pc-keyboard-grid">
    <div class="pc-row">
      <div class="pc-key" onclick="sendKey('esc')">Esc</div>
      <div class="pc-key" onclick="sendKey('f5')">F5</div>
      <div class="pc-key" onclick="sendKey('f11')">F11</div>
      <div class="pc-key" onclick="sendKey('delete')">Del</div>
      <div class="pc-key" onclick="sendKey('home')">Home</div>
      <div class="pc-key" onclick="sendKey('end')">End</div>
    </div>
    <div class="pc-row">
      <div class="pc-key" onclick="sendKey('tab')">Tab</div>
      <div class="pc-key" onclick="sendHotkey(['ctrl', 'a'])">Select All</div>
      <div class="pc-key" onclick="sendHotkey(['ctrl', 'c'])">Copy</div>
      <div class="pc-key" onclick="sendHotkey(['ctrl', 'v'])">Paste</div>
      <div class="pc-key" onclick="sendKey('backspace')">⌫ Back</div>
    </div>
    <div class="pc-row">
      <div class="pc-key" onclick="sendKey('win')">🪟 Win</div>
      <div class="pc-key" onclick="sendKey('up')">▲</div>
      <div class="pc-key" onclick="sendKey('down')">▼</div>
      <div class="pc-key" onclick="sendKey('left')">◄</div>
      <div class="pc-key" onclick="sendKey('right')">►</div>
      <div class="pc-key" style="background:#3b82f6;" onclick="sendKey('enter')">Enter ↵</div>
    </div>
  </div>
</div>

<!-- AI Assist Drawer -->
<div class="drawer" id="drawer-ai">
  <div class="drawer-title">✨ Autonomous Desktop Multi-Task Pilot</div>
  <div class="ai-bar">
    <input type="text" class="ai-input" id="ai-prompt" placeholder="e.g. Open chrome and open gpt and say hi...">
    <button class="ai-submit" onclick="executeAIAction()">GO</button>
  </div>
</div>

<script>
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token') || '';
  const stage = document.getElementById('stage');
  const container = document.getElementById('canvas-container');
  const canvas = document.getElementById('screen-canvas');
  const ctx = canvas.getContext('2d', { alpha: false });
  const clientCursor = document.getElementById('client-cursor');
  const hiddenInput = document.getElementById('hidden-input');
  const hudTop = document.getElementById('hud-top');
  const hudBottom = document.getElementById('hud-bottom');
  const btnRestore = document.getElementById('btn-hud-restore');
  const btnZoomReset = document.getElementById('btn-zoom-reset');
  
  let nativeWidth = 1920, nativeHeight = 1080;
  let ws = null;
  let lastFrameTime = performance.now();
  let frameCount = 0;
  let verifiedPin = '';

  // SECURITY PIN SUBMISSION
  async function submitPin() {
    const pinInput = document.getElementById('pin-input');
    const msgEl = document.getElementById('auth-msg');
    const pin = pinInput.value.trim();

    if (!pin || pin.length < 4) {
      msgEl.textContent = 'Please enter the complete PIN.';
      pinInput.focus();
      return;
    }

    msgEl.style.color = '#38bdf8';
    msgEl.textContent = 'Verifying security PIN...';

    try {
      const res = await fetch('/verify_pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token, pin: pin })
      });
      const data = await res.json();
      if (res.ok && data.valid) {
        verifiedPin = pin;
        msgEl.style.color = '#10b981';
        msgEl.textContent = 'Authorized! Connecting 50 FPS stream...';
        const overlay = document.getElementById('auth-overlay');
        overlay.classList.add('unlocked');
        setTimeout(() => overlay.remove(), 400);
        connect(verifiedPin);
      } else {
        msgEl.style.color = '#ef4444';
        msgEl.textContent = data.error || 'Invalid PIN. Check Discord.';
        pinInput.value = '';
        pinInput.focus();
        if (navigator.vibrate) navigator.vibrate([40, 60, 40]);
      }
    } catch (err) {
      msgEl.style.color = '#ef4444';
      msgEl.textContent = 'Verification connection failed.';
    }
  }

  document.getElementById('pin-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitPin();
  });

  // VIEW MODE ENGINE
  let currentMode = 'fit';
  let isRotated = false;

  // PINCH-TO-ZOOM & PAN STATE
  let currentScale = 1.0;
  let panX = 0, panY = 0;
  let isPinching = false;
  let pinchStartDist = 0;
  let pinchStartScale = 1.0;
  let panStartX = 0, panStartY = 0;

  function updateTransform() {
    container.style.transform = `translate(${panX}px, ${panY}px) scale(${currentScale})`;
    btnZoomReset.textContent = `🔍 ${currentScale.toFixed(1)}x`;
    if (currentScale > 1.05) {
      btnZoomReset.classList.add('active');
    } else {
      btnZoomReset.classList.remove('active');
    }
  }

  btnZoomReset.addEventListener('click', () => {
    currentScale = 1.0;
    panX = 0;
    panY = 0;
    updateTransform();
  });

  document.getElementById('btn-view-mode').addEventListener('click', () => {
    if (currentMode === 'fit') {
      currentMode = 'fill';
      stage.classList.remove('mode-fit');
      stage.classList.add('mode-fill');
      document.getElementById('btn-view-mode').textContent = '📐 Fill';
    } else {
      currentMode = 'fit';
      stage.classList.remove('mode-fill');
      stage.classList.add('mode-fit');
      document.getElementById('btn-view-mode').textContent = '📐 Fit';
    }
  });

  document.getElementById('btn-rotate').addEventListener('click', () => {
    isRotated = !isRotated;
    if (isRotated) {
      stage.classList.add('mode-rotated');
      document.getElementById('btn-rotate').classList.add('active');
    } else {
      stage.classList.remove('mode-rotated');
      document.getElementById('btn-rotate').classList.remove('active');
    }
  });

  // IMMERSIVE FULLSCREEN
  let isImmersive = false;
  function toggleFullscreen() {
    isImmersive = !isImmersive;
    if (isImmersive) {
      try {
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else if (document.documentElement.webkitRequestFullscreen) {
          document.documentElement.webkitRequestFullscreen();
        }
      } catch (err) {}
      hudTop.classList.add('hidden');
      hudBottom.classList.add('hidden');
      btnRestore.style.display = 'flex';
      document.querySelectorAll('.drawer').forEach(d => d.style.display = 'none');
    } else {
      try {
        if (document.exitFullscreen) document.exitFullscreen().catch(() => {});
      } catch (err) {}
      hudTop.classList.remove('hidden');
      hudBottom.classList.remove('hidden');
      btnRestore.style.display = 'none';
    }
  }
  document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);
  btnRestore.addEventListener('click', toggleFullscreen);

  // WEBSOCKET 50 FPS ENGINE
  let isRenderingFrame = false;

  function connect(pin) {
    const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${location.host}/ws?token=${encodeURIComponent(token)}&pin=${encodeURIComponent(pin)}`;
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'blob';

    ws.onopen = () => console.log('50 FPS Stream Connected.');

    ws.onmessage = async (e) => {
      if (typeof e.data === 'string') {
        const msg = JSON.parse(e.data);
        if (msg.type === 'init') {
          nativeWidth = msg.width;
          nativeHeight = msg.height;
          canvas.width = nativeWidth;
          canvas.height = nativeHeight;
        }
      } else {
        if (isRenderingFrame) return;
        isRenderingFrame = true;

        const img = new Image();
        img.onload = () => {
          if (canvas.width !== nativeWidth || canvas.height !== nativeHeight) {
            canvas.width = nativeWidth;
            canvas.height = nativeHeight;
          }
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          URL.revokeObjectURL(img.src);
          isRenderingFrame = false;

          frameCount++;
          const now = performance.now();
          if (now - lastFrameTime >= 1000) {
            document.getElementById('fps-label').textContent = `${frameCount} FPS`;
            frameCount = 0;
            lastFrameTime = now;
          }
        };
        img.src = URL.createObjectURL(e.data);
      }
    };

    ws.onclose = () => {
      document.getElementById('fps-label').textContent = 'RECONNECTING...';
      setTimeout(() => { if (verifiedPin) connect(verifiedPin); }, 1500);
    };
  }

  function sendWS(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  function createRipple(x, y, isRight = false) {
    const r = document.createElement('div');
    r.className = `touch-ripple ${isRight ? 'ripple-right' : 'ripple-left'}`;
    r.style.left = `${x}px`;
    r.style.top = `${y}px`;
    document.body.appendChild(r);
    setTimeout(() => r.remove(), 280);
  }

  function getScreenCoords(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = nativeWidth / rect.width;
    const scaleY = nativeHeight / rect.height;
    const x = Math.max(0, Math.min(nativeWidth, (clientX - rect.left) * scaleX));
    const y = Math.max(0, Math.min(nativeHeight, (clientY - rect.top) * scaleY));
    return { x: Math.round(x), y: Math.round(y) };
  }

  // --- TWO-FINGER PINCH-TO-ZOOM & PAN ON STAGE (ANYWHERE INCLUDING BLACK BORDERS) ---
  let touchStartTime = 0;
  let touchStartX = 0, touchStartY = 0;
  let lastTouchX = 0, lastTouchY = 0;
  let touchCount = 0;
  let isDragging = false;
  let holdTimer = null;
  let lastTapTime = 0;

  stage.addEventListener('touchstart', (e) => {
    touchCount = e.touches.length;
    touchStartTime = performance.now();

    if (touchCount === 2) {
      // 2-Finger Pinch Zoom & Pan anywhere on screen (even on letterbox borders!)
      isPinching = true;
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      isDragging = false;
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      pinchStartDist = Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY);
      pinchStartScale = currentScale;
      panStartX = (t0.clientX + t1.clientX) / 2 - panX;
      panStartY = (t0.clientY + t1.clientY) / 2 - panY;
      return;
    }

    if (touchCount === 1) {
      const t = e.touches[0];
      touchStartX = t.clientX;
      touchStartY = t.clientY;
      lastTouchX = t.clientX;
      lastTouchY = t.clientY;

      const rect = canvas.getBoundingClientRect();
      const isInsideCanvas = (t.clientX >= rect.left && t.clientX <= rect.right &&
                             t.clientY >= rect.top && t.clientY <= rect.bottom);

      // Double tap anywhere on stage to reset zoom
      const now = performance.now();
      if (now - lastTapTime < 300) {
        currentScale = 1.0;
        panX = 0; panY = 0;
        updateTransform();
        lastTapTime = 0;
        return;
      }
      lastTapTime = now;

      if (isInsideCanvas && currentScale <= 1.05) {
        holdTimer = setTimeout(() => {
          isDragging = true;
          if (navigator.vibrate) navigator.vibrate(35);
          const coords = getScreenCoords(t.clientX, t.clientY);
          sendWS({ type: 'mouse_down', button: 'left', x: coords.x, y: coords.y });
          createRipple(t.clientX, t.clientY, false);
        }, 350);
      }
    }
  }, { passive: false });

  stage.addEventListener('touchmove', (e) => {
    e.preventDefault();

    if (isPinching && e.touches.length === 2) {
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      const dist = Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY);
      if (pinchStartDist > 0) {
        const ratio = dist / pinchStartDist;
        currentScale = Math.max(1.0, Math.min(5.0, pinchStartScale * ratio));
      }
      const midX = (t0.clientX + t1.clientX) / 2;
      const midY = (t0.clientY + t1.clientY) / 2;
      panX = midX - panStartX;
      panY = midY - panStartY;
      updateTransform();
      return;
    }

    if (e.touches.length === 1) {
      const t = e.touches[0];
      const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);
      if (dist > 8 && holdTimer) {
        clearTimeout(holdTimer);
        holdTimer = null;
      }
      if (isDragging) {
        const coords = getScreenCoords(t.clientX, t.clientY);
        sendWS({ type: 'mouse_move', x: coords.x, y: coords.y });
      } else if (currentScale > 1.05) {
        // Panning works ANYWHERE on screen, including the black borders!
        panX += (t.clientX - lastTouchX);
        panY += (t.clientY - lastTouchY);
        updateTransform();
      }
      lastTouchX = t.clientX;
      lastTouchY = t.clientY;
    }
  }, { passive: false });

  stage.addEventListener('touchend', (e) => {
    if (holdTimer) clearTimeout(holdTimer);
    if (isPinching) {
      if (e.touches.length < 2) isPinching = false;
      return;
    }

    if (isDragging) {
      isDragging = false;
      const t = e.changedTouches[0];
      const coords = getScreenCoords(t.clientX, t.clientY);
      sendWS({ type: 'mouse_up', button: 'left', x: coords.x, y: coords.y });
      return;
    }

    const duration = performance.now() - touchStartTime;
    const t = e.changedTouches[0];
    const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);

    if (dist < 12 && duration < 320 && touchCount === 1) {
      const rect = canvas.getBoundingClientRect();
      if (t.clientX >= rect.left && t.clientX <= rect.right &&
          t.clientY >= rect.top && t.clientY <= rect.bottom) {
        createRipple(t.clientX, t.clientY, false);
        const coords = getScreenCoords(t.clientX, t.clientY);
        sendWS({ type: 'mouse_click', button: 'left', x: coords.x, y: coords.y });
      }
    }
  }, { passive: false });

  // --- FLOATING COMPACT MOUSEPAD ---
  const pad = document.getElementById('floating-mousepad');
  const padBadge = document.getElementById('mousepad-badge');
  const padSurface = document.getElementById('pad-surface');
  const padScroll = document.getElementById('pad-scroll');
  const padHandle = document.getElementById('pad-drag-handle');

  let padTouchX = 0, padTouchY = 0;
  let padTouchStartTime = 0;

  padSurface.addEventListener('touchstart', (e) => {
    const t = e.touches[0];
    padTouchX = t.clientX;
    padTouchY = t.clientY;
    padTouchStartTime = performance.now();
  }, { passive: false });

  padSurface.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (e.touches.length === 1) {
      const t = e.touches[0];
      const dx = Math.round((t.clientX - padTouchX) * 1.5);
      const dy = Math.round((t.clientY - padTouchY) * 1.5);
      if (dx !== 0 || dy !== 0) {
        sendWS({ type: 'trackpad_move', dx, dy });
      }
      padTouchX = t.clientX;
      padTouchY = t.clientY;
    } else if (e.touches.length === 2) {
      const t = e.touches[0];
      const dy = Math.round((t.clientY - padTouchY) * 2.5);
      if (Math.abs(dy) > 1) {
        sendWS({ type: 'mouse_scroll', dy });
      }
      padTouchY = t.clientY;
    }
  }, { passive: false });

  padSurface.addEventListener('touchend', (e) => {
    const duration = performance.now() - padTouchStartTime;
    if (duration < 220 && e.changedTouches.length === 1) {
      sendWS({ type: 'mouse_click', button: 'left' });
      if (navigator.vibrate) navigator.vibrate(20);
    }
  });

  // Vertical Scroll Rail
  let scrollStartY = 0;
  padScroll.addEventListener('touchstart', (e) => {
    scrollStartY = e.touches[0].clientY;
  }, { passive: false });

  padScroll.addEventListener('touchmove', (e) => {
    e.preventDefault();
    const currentY = e.touches[0].clientY;
    const dy = Math.round((currentY - scrollStartY) * 3);
    if (Math.abs(dy) > 2) {
      sendWS({ type: 'mouse_scroll', dy });
      scrollStartY = currentY;
    }
  }, { passive: false });

  // Dragging Mousepad Anywhere
  let isDraggingPad = false;
  let padStartX = 0, padStartY = 0;

  padHandle.addEventListener('touchstart', (e) => {
    isDraggingPad = true;
    const t = e.touches[0];
    padStartX = t.clientX - pad.offsetLeft;
    padStartY = t.clientY - pad.offsetTop;
  }, { passive: false });

  window.addEventListener('touchmove', (e) => {
    if (!isDraggingPad) return;
    const t = e.touches[0];
    pad.style.right = 'auto';
    pad.style.bottom = 'auto';
    const newX = Math.max(0, Math.min(window.innerWidth - 185, t.clientX - padStartX));
    const newY = Math.max(0, Math.min(window.innerHeight - 190, t.clientY - padStartY));
    pad.style.left = `${newX}px`;
    pad.style.top = `${newY}px`;
  }, { passive: false });

  window.addEventListener('touchend', () => isDraggingPad = false);

  function sendMouseDown(btn) {
    if (navigator.vibrate) navigator.vibrate(25);
    sendWS({ type: 'mouse_down', button: btn });
  }
  function sendMouseUp(btn) {
    sendWS({ type: 'mouse_up', button: btn });
  }

  function toggleMousepad(show) {
    const isVisible = pad.style.display !== 'none';
    const targetState = show !== undefined ? show : !isVisible;
    pad.style.display = targetState ? 'flex' : 'none';
    padBadge.style.display = 'none';
  }

  function minimizeMousepad(min) {
    if (min) {
      pad.style.display = 'none';
      padBadge.style.display = 'flex';
    } else {
      padBadge.style.display = 'none';
      pad.style.display = 'flex';
    }
  }

  document.getElementById('btn-mousepad-toggle').addEventListener('click', () => toggleMousepad());

  // DRAWERS & KEYS
  function toggleDrawer(id) {
    const el = document.getElementById(id);
    const isShown = el.style.display === 'block';
    document.querySelectorAll('.drawer').forEach(d => d.style.display = 'none');
    el.style.display = isShown ? 'none' : 'block';
  }

  document.getElementById('dock-quick-keys').addEventListener('click', () => toggleDrawer('drawer-keys'));
  document.getElementById('dock-full-kb').addEventListener('click', () => toggleDrawer('drawer-full-kb'));
  document.getElementById('dock-ai').addEventListener('click', () => toggleDrawer('drawer-ai'));
  document.getElementById('dock-keyboard').addEventListener('click', () => hiddenInput.focus());

  document.getElementById('dock-lock').addEventListener('click', () => {
    if (confirm("Lock your Windows laptop?")) {
      sendWS({ type: 'power', action: 'lock' });
    }
  });

  hiddenInput.addEventListener('input', (e) => {
    if (e.data) {
      sendWS({ type: 'keyboard_type', text: e.data });
      hiddenInput.value = '';
    }
  });
  hiddenInput.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') sendWS({ type: 'keyboard_key', key: 'backspace' });
    else if (e.key === 'Enter') sendWS({ type: 'keyboard_key', key: 'enter' });
  });

  function sendKey(key) {
    sendWS({ type: 'keyboard_key', key });
  }
  function sendHotkey(keys) {
    sendWS({ type: 'keyboard_hotkey', keys });
  }
  function launchOSK() {
    sendWS({ type: 'launch_osk' });
    document.querySelectorAll('.drawer').forEach(d => d.style.display = 'none');
  }
  function executeAIAction() {
    const prompt = document.getElementById('ai-prompt').value.trim();
    if (!prompt) return;
    sendWS({ type: 'ai_action', prompt });
    document.getElementById('ai-prompt').value = '';
    document.querySelectorAll('.drawer').forEach(d => d.style.display = 'none');
  }
</script>
</body>
</html>
"""

# ----------------- SERVER CLASS (50 FPS HARDWARE ACCELERATED) -----------------
class WebRemoteServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 20129):
        self.host = host
        self.port = port
        self.active_token: Optional[str] = None
        self.active_pin: Optional[str] = None
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.active_websockets: Set[web.WebSocketResponse] = set()
        self.is_running = False
        self.capture_task: Optional[asyncio.Task] = None
        self.screen_width = 1920
        self.screen_height = 1080
        self.last_activity = time.time()

    def generate_session(self) -> Tuple[str, str]:
        """Generates dynamic per-session access token and random 6-digit PIN."""
        self.active_token = secrets.token_urlsafe(16)
        self.active_pin = f"{secrets.randbelow(900000) + 100000}"
        ip = get_local_ip()
        url = f"http://{ip}:{self.port}/?token={self.active_token}"
        return url, self.active_pin

    def get_access_info(self) -> Tuple[str, str]:
        if not self.active_token or not self.active_pin:
            return self.generate_session()
        ip = get_local_ip()
        return f"http://{ip}:{self.port}/?token={self.active_token}", self.active_pin

    async def handle_index(self, request: web.Request):
        req_token = request.query.get("token")
        if not req_token or req_token != self.active_token:
            return web.Response(text="⛔ Unauthorized: Invalid or expired access token.", status=403)
        return web.Response(text=HTML_CLIENT, content_type="text/html")

    async def handle_verify_pin(self, request: web.Request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"valid": False, "error": "Malformed request"}, status=400)
        token = data.get("token", "").strip()
        pin = data.get("pin", "").strip()
        if token == self.active_token and pin == self.active_pin and self.active_token:
            return web.json_response({"valid": True})
        return web.json_response({"valid": False, "error": "Invalid PIN. Check Discord."}, status=401)

    async def handle_ws(self, request: web.Request):
        req_token = request.query.get("token")
        req_pin = request.query.get("pin")
        if not req_token or req_token != self.active_token or not req_pin or req_pin != self.active_pin:
            return web.Response(text="Forbidden: Invalid token or PIN", status=403)

        ws = web.WebSocketResponse(max_msg_size=10*1024*1024)
        await ws.prepare(request)
        self.active_websockets.add(ws)
        self.last_activity = time.time()

        try:
            with mss.MSS() as sct:
                mon = sct.monitors[1]
                self.screen_width = mon["width"]
                self.screen_height = mon["height"]
        except Exception:
            pass

        await ws.send_str(json.dumps({
            "type": "init",
            "width": self.screen_width,
            "height": self.screen_height
        }))

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    self.last_activity = time.time()
                    await self._process_input_event(json.loads(msg.data))
        finally:
            self.active_websockets.discard(ws)
        return ws

    async def _process_input_event(self, data: dict):
        event_type = data.get("type")
        _attach_to_default_desktop()

        if event_type == "mouse_click":
            btn = data.get("button", "left")
            x = data.get("x")
            y = data.get("y")
            if x is not None and y is not None:
                user32.SetCursorPos(int(x), int(y))
            if btn == "left":
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif btn == "right":
                user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

        elif event_type == "mouse_down":
            btn = data.get("button", "left")
            x = data.get("x")
            y = data.get("y")
            if x is not None and y is not None:
                user32.SetCursorPos(int(x), int(y))
            flag = MOUSEEVENTF_LEFTDOWN if btn == "left" else MOUSEEVENTF_RIGHTDOWN
            user32.mouse_event(flag, 0, 0, 0, 0)

        elif event_type == "mouse_up":
            btn = data.get("button", "left")
            flag = MOUSEEVENTF_LEFTUP if btn == "left" else MOUSEEVENTF_RIGHTUP
            user32.mouse_event(flag, 0, 0, 0, 0)

        elif event_type == "mouse_move":
            x = data.get("x")
            y = data.get("y")
            if x is not None and y is not None:
                user32.SetCursorPos(int(x), int(y))

        elif event_type == "trackpad_move":
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            try:
                pos = pyautogui.position()
                new_x = max(0, min(self.screen_width - 1, pos.x + dx))
                new_y = max(0, min(self.screen_height - 1, pos.y + dy))
                user32.SetCursorPos(new_x, new_y)
                user32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
            except Exception:
                user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)

        elif event_type == "mouse_scroll":
            dy = int(data.get("dy", 0))
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, dy, 0)

        elif event_type == "keyboard_type":
            pyautogui.write(data.get("text", ""), interval=0.01)

        elif event_type == "keyboard_key":
            pyautogui.press(data.get("key", ""))

        elif event_type == "keyboard_hotkey":
            keys = data.get("keys", [])
            if keys:
                pyautogui.hotkey(*keys)

        elif event_type == "launch_osk":
            os.system("start osk.exe")

        elif event_type == "power":
            if data.get("action") == "lock":
                user32.LockWorkStation()

        elif event_type == "ai_action":
            prompt = data.get("prompt", "")
            if prompt:
                asyncio.create_task(self._run_ai_desktop_task(prompt))

    async def _run_ai_desktop_task(self, prompt: str):
        """Intelligent Autonomous Multi-Task Desktop Execution Engine."""
        _attach_to_default_desktop()
        p_raw = prompt.strip()
        p_low = p_raw.lower()

        # Check for Antigravity IDE launch request
        if any(a in p_low for a in ["antigravity", "antigravity ide", "agy"]):
            if "open" in p_low or "launch" in p_low or "start" in p_low:
                sys_ctl.launch_antigravity_ide()
                await asyncio.sleep(1.0)
                return

        # Check for ChatGPT / GPT compound flows (e.g. 'open chrome and open gpt and say hi')
        has_gpt = any(g in p_low for g in ["gpt", "chatgpt", "chat gpt", "openai"])
        if has_gpt:
            # Launch Chrome with ChatGPT or open URL
            if any(b in p_low for b in ["chrome", "browser"]):
                os.system('start chrome.exe "https://chatgpt.com"')
            else:
                os.startfile("https://chatgpt.com")
            await asyncio.sleep(2.8)

            # Check for words to type/send to ChatGPT
            for phrase in ["say ", "type ", "write ", "ask ", "prompt "]:
                if phrase in p_low:
                    idx = p_low.rfind(phrase) + len(phrase)
                    text_to_say = p_raw[idx:].strip().strip('"').strip("'")
                    if text_to_say:
                        await asyncio.sleep(0.5)
                        pyautogui.write(text_to_say, interval=0.03)
                        pyautogui.press("enter")
                    break
            return

        # Check for YouTube searches
        if any(y in p_low for y in ["youtube", "yt"]):
            query = ""
            for kw in ["play", "search", "with", "for"]:
                if kw in p_low:
                    query = p_raw[p_low.find(kw) + len(kw):].strip()
                    break
            if not query:
                query = p_raw.replace("open youtube", "").replace("open yt", "").strip()
            encoded = urllib.parse.quote_plus(query) if query else ""
            url = f"https://www.youtube.com/results?search_query={encoded}" if encoded else "https://www.youtube.com"
            os.startfile(url)
            await asyncio.sleep(1.5)
            return

        # Universal Sequential Pipeline for multi-step tasks
        steps = re.split(r'\s+and\s+then\s+|\s+then\s+|\s+and\s+|;\s*', p_raw, flags=re.IGNORECASE)
        for step in steps:
            s = step.strip()
            if not s:
                continue
            s_low = s.lower()

            if "notepad" in s_low:
                os.system("start notepad.exe")
                await asyncio.sleep(1.0)
            elif "calc" in s_low or "calculator" in s_low:
                os.system("start calc.exe")
                await asyncio.sleep(0.8)
            elif "spotify" in s_low:
                os.system("start spotify:")
                await asyncio.sleep(1.0)
            elif "code" in s_low or "vscode" in s_low:
                os.system("code .")
                await asyncio.sleep(1.0)
            elif "terminal" in s_low or "powershell" in s_low:
                os.system("start wt.exe")
                await asyncio.sleep(0.8)
            elif "chrome" in s_low:
                os.system("start chrome.exe")
                await asyncio.sleep(1.5)
            elif s_low.startswith("type ") or s_low.startswith("say ") or s_low.startswith("write "):
                words = s.split(" ", 1)[-1].strip().strip('"').strip("'")
                pyautogui.write(words, interval=0.02)
                await asyncio.sleep(0.3)
            elif s_low.startswith("press ") or s_low.startswith("hit "):
                key = s.split(" ", 1)[-1].strip().lower()
                pyautogui.press(key)
                await asyncio.sleep(0.2)
            elif s_low == "enter":
                pyautogui.press("enter")
                await asyncio.sleep(0.2)
            elif s_low in ["lock", "lock pc"]:
                user32.LockWorkStation()
            elif s_low.startswith("search ") or s_low.startswith("google "):
                q = s.split(" ", 1)[-1].strip()
                os.startfile(f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}")
                await asyncio.sleep(1.0)
            elif s_low.startswith("open "):
                target = s[5:].strip()
                sys_ctl.open_path_or_app(target)
                await asyncio.sleep(0.8)
            else:
                sys_ctl.open_path_or_app(s)
                await asyncio.sleep(0.5)

    async def _capture_stream_loop(self):
        """Hardware-Accelerated 50 FPS Video Pipeline via OpenCV SIMD."""
        _attach_to_default_desktop()

        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            mon_left = monitor["left"]
            mon_top = monitor["top"]

            base_cursor = np.array([
                [0, 0], [0, 17], [4, 13], [9, 21], [12, 20], [7, 12], [13, 12]
            ], dtype=np.int32)
            base_shadow = base_cursor + 1

            while self.is_running:
                if time.time() - self.last_activity > 300 and self.active_websockets:
                    user32.LockWorkStation()
                    for ws in list(self.active_websockets):
                        await ws.close()
                    self.active_websockets.clear()

                if not self.active_websockets:
                    await asyncio.sleep(0.15)
                    continue

                loop_start = time.time()
                try:
                    sct_img = sct.grab(monitor)
                    raw_bgra = np.array(sct_img, dtype=np.uint8)
                    frame = raw_bgra[:, :, :3]

                    try:
                        pos = pyautogui.position()
                        cx = int(pos.x - mon_left)
                        cy = int(pos.y - mon_top)
                        if 0 <= cx < frame.shape[1] and 0 <= cy < frame.shape[0]:
                            poly_cursor = base_cursor + [cx, cy]
                            poly_shadow = base_shadow + [cx, cy]
                            cv2.fillPoly(frame, [poly_shadow], (0, 0, 0))
                            cv2.fillPoly(frame, [poly_cursor], (255, 255, 255))
                            cv2.polylines(frame, [poly_cursor], True, (0, 0, 0), 1)
                            cv2.circle(frame, (cx, cy), 2, (0, 0, 255), -1)
                    except Exception:
                        pass

                    target_w = 1280
                    target_h = int(frame.shape[0] * (target_w / frame.shape[1]))
                    resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

                    _, enc = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 62])
                    frame_bytes = enc.tobytes()

                    dead_sockets = set()
                    for ws in list(self.active_websockets):
                        try:
                            await ws.send_bytes(frame_bytes)
                        except Exception:
                            dead_sockets.add(ws)

                    self.active_websockets.difference_update(dead_sockets)

                except Exception:
                    pass

                elapsed = time.time() - loop_start
                target_interval = 1.0 / 50.0
                if target_interval > elapsed:
                    await asyncio.sleep(target_interval - elapsed)
                else:
                    await asyncio.sleep(0.001)

    async def start(self) -> Tuple[str, str]:
        """Starts the server and generates a brand new dynamic token and 6-digit PIN."""
        url, pin = self.generate_session()

        # Invalidate old sessions
        for ws in list(self.active_websockets):
            try:
                await ws.close()
            except Exception:
                pass
        self.active_websockets.clear()

        if self.is_running:
            return url, pin

        self.app = web.Application()
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_post("/verify_pin", self.handle_verify_pin)
        self.app.router.add_get("/ws", self.handle_ws)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self.is_running = True
        self.capture_task = asyncio.create_task(self._capture_stream_loop())
        return url, pin

    async def stop(self):
        self.is_running = False
        self.active_token = None
        self.active_pin = None
        if self.capture_task:
            self.capture_task.cancel()
        for ws in list(self.active_websockets):
            try:
                await ws.close()
            except Exception:
                pass
        self.active_websockets.clear()

        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

# Global singleton instance
web_remote_server = WebRemoteServer(host="0.0.0.0", port=20129)

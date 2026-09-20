# Source Generated with Decompyle++
# File: main_window.pyc (Python 3.12)

'''
Main Window — layout CustomTkinter + RENDER pipeline.

Trái: ControlPanel (7 công cụ)
Phải: PreviewPanel (xem trước + hàng đợi)
Trên: thao tác toàn cục gọn nhẹ

RENDER: SRT → Edge-TTS → AudioSyncEngine → FFmpeg → MP4.
'''
from __future__ import annotations
import json
import logging
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_GOLD, ACCENT_HOVER, BG_CARD, BG_DARK, BG_HEADER, BORDER, DANGER, DANGER_HOVER, DROPDOWN_BG, INFO, ON_ACCENT, ON_DANGER, ON_SUCCESS, SUCCESS, SUCCESS_HOVER, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED, UI_FONT_FAMILY, WARNING, apply_global_theme, resolve, set_appearance
from app.core.state import AppState
from app.ui.fluent_icons import fluent_icon
APPEARANCE_LABEL = {
    'dark': 'Nền tối',
    'oled': 'Tối sâu (OLED)' }
APPEARANCE_MODE = {
    'Nền tối': 'dark',
    'Tối sâu (OLED)': 'oled',
    'Nền sáng': 'dark' }
TRANSLATION_API_KEY_URLS = {
    'Gemini': 'https://console.cloud.google.com/apis/credentials?project',
    'Groq': 'https://console.groq.com/keys',
    'OpenAI': 'https://platform.openai.com/api-keys',
    'DeepSeek': 'https://platform.deepseek.com/usage' }
ELEVENLABS_API_KEY_URL = 'https://elevenlabs.io/app/developers/api-keys'
from app.services.job_workspace import JOBS_ROOT, create_job_workspace
from app.ui.control_panel import ControlPanel
from app.ui.preview_panel import PreviewPanel
logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[2]

class MainWindow(ctk.CTk):
    pass
# WARNING: Decompyle incomplete


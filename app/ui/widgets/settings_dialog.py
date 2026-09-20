# Source Generated with Decompyle++
# File: settings_dialog.pyc (Python 3.12)

'''Hộp thoại Cài đặt toàn diện — Mumu Studio Pro.

Tách từ MainWindow để giữ code gọn gàng, tăng tốc độ nạp file và dễ bảo trì.
'''
from __future__ import annotations
import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_GOLD, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BG_HEADER, BORDER, DANGER, DANGER_HOVER, DROPDOWN_BG, INFO, ON_ACCENT, ON_DANGER, ON_SUCCESS, SUCCESS, SUCCESS_HOVER, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED, WARNING, apply_global_theme, resolve, set_appearance
from app.core.state import AppState
from app.ui.fluent_icons import fluent_icon
logger = logging.getLogger(__name__)
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

def open_settings_dialog(self = None, initial_tab = None):
    '''Single home for app settings and every translation API key.'''
    pass
# WARNING: Decompyle incomplete


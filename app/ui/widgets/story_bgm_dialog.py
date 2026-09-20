# Source Generated with Decompyle++
# File: story_bgm_dialog.pyc (Python 3.12)

'''Hộp thoại quản lý nhạc nền BGM Storytelling đa track với Timeline, Loop và Fade In/Out (Crossfade).'''
from __future__ import annotations
import logging
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BG_SUNKEN, BORDER, DANGER, DANGER_HOVER, DROPDOWN_BG, ON_ACCENT, ON_DANGER, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, resolve
from app.services.media_probe import probe_video_duration_s
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }
_CLIP_COLORS = [
    ('#1E3A8A', '#3B82F6'),
    ('#064E3B', '#10B981'),
    ('#78350F', '#F59E0B'),
    ('#581C87', '#8B5CF6'),
    ('#831843', '#EC4899'),
    ('#134E4A', '#14B8A6')]

def _format_time_s(seconds = None):
    s = max(0, float(seconds))
    m = int(s // 60)
    sec = s % 60
    return f'''{m:02d}:{sec:05.2f}'''


class StoryBgmDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


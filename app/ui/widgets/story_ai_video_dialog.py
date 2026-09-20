# Source Generated with Decompyle++
# File: story_ai_video_dialog.pyc (Python 3.12)

'''Cửa sổ Modal sinh video AI (Google Veo 3 / Omni Flash) cho phân cảnh Storytelling.'''
from __future__ import annotations
import logging
import threading
from pathlib import Path
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, DROPDOWN_BG, ON_ACCENT, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.services.story_video_service import assign_video_to_scene, generate_omni_flash_video, generate_veo_ai_video
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }

class StoryAiVideoDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


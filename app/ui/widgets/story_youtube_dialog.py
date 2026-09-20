# Source Generated with Decompyle++
# File: story_youtube_dialog.pyc (Python 3.12)

'''Cửa sổ Modal phân tích video YouTube đối thủ và tự động viết kịch bản độc bản (Storytelling).'''
from __future__ import annotations
import base64
import io
import logging
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable
import customtkinter as ctk
from PIL import Image
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BG_PANEL, BORDER, DANGER, DROPDOWN_BG, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED
from app.services.story_youtube_service import SUPPORTED_SCRIPT_LANGUAGES, build_youtube_web_gemini_prompt, extract_youtube_info, generate_youtube_competitor_story, parse_youtube_web_gemini_response
from app.ui.widgets.story_web_ai_dialog import URL_GEMINI, open_in_chrome
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }

class StoryYoutubeWebAiDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


class StoryYoutubeDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


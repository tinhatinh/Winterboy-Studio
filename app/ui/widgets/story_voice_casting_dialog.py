# Source Generated with Decompyle++
# File: story_voice_casting_dialog.pyc (Python 3.12)

'''Hộp thoại Bảng Phân Vai Nhân Vật (Multi-Character Voice Casting Modal) cho Mumu Studio Pro.

Cho phép người dùng:
- Xem toàn bộ nhân vật / vai diễn có trong kịch bản và số lượng phân cảnh tương ứng.
- Tự do chọn Nhà cung cấp TTS, Giọng đọc (Voice ID), Tốc độ cho từng vai diễn riêng biệt.
- Nghe thử giọng đọc mẫu ngay lập tức.
- Thêm nhân vật mới thủ công.
- 1-click Áp dụng cấu hình phân vai cho tất cả các phân cảnh.
- 1-click Sinh lại toàn bộ giọng đọc theo đúng bảng phân vai đa model và khóa timestamp SRT.
'''
from __future__ import annotations
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable
import customtkinter as ctk
from app.services.story_engine import StoryProject, StoryScene
from app.services.story_image_service import generate_scene_audio, get_story_provider_voices, sync_story_timeline_and_srt
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, DROPDOWN_BG, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, WARNING
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }

class StoryVoiceCastingDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


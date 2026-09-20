# Source Generated with Decompyle++
# File: story_competitor_dialog.pyc (Python 3.12)

'''Cửa sổ Modal Quản Lý Preset & Hồ Sơ Kênh Đối Thủ (Competitor Channel Profiles Dialog).

Cho phép người dùng:
1. Quản lý tập trung toàn bộ preset cho từng kênh đối thủ (ví dụ: Lady Jaki FitzHerbert).
2. Tùy chỉnh Art Style, Master Prompt, Nhân vật chuẩn (Character Bible), Giọng đọc AI, Tỉ lệ khung hình, Nhạc nền.
3. 1-Click đồng bộ toàn bộ nội dung kịch bản cho dự án hiện tại theo kênh đối thủ.
4. Tạo kịch bản mới được gán sẵn tag và phong cách của kênh đối thủ.
'''
from __future__ import annotations
import logging
from typing import Any, Callable
import customtkinter as ctk
from tkinter import messagebox
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BG_PANEL, BORDER, DANGER, DROPDOWN_BG, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.services.story_competitor_service import delete_competitor_channel, load_competitor_channels, save_or_update_competitor_channel
from app.services.story_engine import StoryProject, get_all_story_prompt_presets
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': '#1E293B',
    'button_color': '#334155',
    'button_hover_color': '#475569',
    'dropdown_fg_color': '#1E293B',
    'dropdown_hover_color': '#334155',
    'dropdown_text_color': '#F8FAFC',
    'text_color': '#F8FAFC' }

class StoryCompetitorDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


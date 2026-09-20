# Source Generated with Decompyle++
# File: story_ai_creator_dialog.pyc (Python 3.12)

'''Cửa sổ Modal Sáng Tạo Kịch Bản & Master Prompt Độc Bản (Story & Style AI Creator Dialog).

Cho phép người dùng:
1. Nhập hoặc bấm Random Ý tưởng, Nhân vật, Bối cảnh.
2. Chọn hoặc tùy biến Master Prompt theo các Preset điện ảnh mẫu.
3. Chọn độ dài kịch bản (kèm mức max ~100.000 ký tự với quy tắc độ dài nghiêm ngặt).
4. Thực hiện qua 2 nhánh:
   - Web Chrome (ChatGPT / Gemini Web - Miễn phí, Copy Prompt -> Tự động nhận JSON trả về).
   - Gemini API (Tự động 1-click với xoay vòng key).
5. Nạp trực tiếp kết quả (Tiêu đề, Chủ đề, Mô tả, Kịch bản, Master Prompt) vào StoryEditor.
'''
from __future__ import annotations
import json
import logging
import threading
from typing import Any, Callable
import customtkinter as ctk
from tkinter import messagebox
from app.config.theme import ACCENT, ACCENT_HOVER, BG_CARD, BG_DARK, BG_PANEL, BORDER, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.services.story_ai_creator_service import AI_CREATOR_LENGTH_MAP, build_ai_story_creator_prompt, generate_ai_random_all, generate_ai_random_character, generate_ai_random_idea, generate_ai_random_setting, generate_ai_story_via_api, get_random_all, get_random_character, get_random_idea, get_random_setting, _extract_clean_json_from_text
from app.services.story_engine import CUSTOM_PRESET_NAME, estimate_story_duration, get_all_story_prompt_presets
from app.ui.widgets.story_web_ai_dialog import URL_CHATGPT, URL_GEMINI, open_in_chrome
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': '#1E293B',
    'button_color': '#334155',
    'button_hover_color': '#475569',
    'dropdown_fg_color': '#1E293B',
    'dropdown_hover_color': '#334155',
    'dropdown_text_color': '#F8FAFC',
    'text_color': '#F8FAFC' }

class StoryAICreatorDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


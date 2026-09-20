# Source Generated with Decompyle++
# File: module_story.pyc (Python 3.12)

'''Module 12 — Tự Động Dựng Video Kể Chuyện (AI Storytelling / Cinematic Realism).

Giao diện đã được tối ưu tinh gọn (theo phong cách giống tab SRT):
- Phần kịch bản, master prompt và quản lý phân cảnh chi tiết được gom vào Modal riêng (StoryEditorDialog).
- Tab chính tập trung vào: Trạng thái kịch bản, Cấu hình giọng đọc/video và Nút render xuất bản.
'''
from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_SUNKEN, BORDER, DANGER, DANGER_SOFT, DANGER_SOFT_HOVER, DROPDOWN_BG, INFO, ON_ACCENT, ON_DANGER_SOFT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, WARNING
from app.core.state import AppState
from app.services.edge_tts_engine import VI_VOICES, VOICE_LABELS
from app.services.story_engine import BLEND_MODES, CAMERA_MOTION_LABELS, StoryProject, StoryScene, ensure_sample_textures, get_available_textures, get_blend_mode_display_name, get_blend_mode_id, segment_story_script
from app.ui.widgets.story_tour import InteractiveTourGuide, TourStep
from app.services.story_image_service import format_display_time, generate_gemini_image, generate_scene_audio, get_story_provider_voices, sync_story_timeline_and_srt
from app.services.story_video_assembler import assemble_story_video
from app.ui.modules.base_module import BaseModule
from app.ui.widgets.story_editor import StoryEditorDialog
from app.ui.fluent_icons import fluent_icon
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }

class ModuleStory(BaseModule):
    pass
# WARNING: Decompyle incomplete


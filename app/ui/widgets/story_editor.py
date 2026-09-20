# Source Generated with Decompyle++
# File: story_editor.pyc (Python 3.12)

'''Modal Dialog quản lý kịch bản, master prompt và các phân cảnh Storytelling.

Cung cấp không gian làm việc rộng rãi (1100x760) để:
- Nhập kịch bản, chọn Master Prompt preset hoặc tùy biến.
- Bóc tách phân cảnh (Gemini AI / Fallback).
- Quản lý timeline, nghe thử giọng đọc, gán ảnh / sinh ảnh AI cho từng cảnh.
- Thao tác hàng loạt: Sinh voice & Khóa SRT, Quét thư mục ảnh, Sinh ảnh Imagen.
'''
from __future__ import annotations
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable
import customtkinter as ctk
from PIL import Image
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, DANGER, DROPDOWN_BG, INFO, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, WARNING
from app.services.edge_tts_engine import VI_VOICES, VOICE_LABELS
from app.services.story_engine import CAMERA_MOTION_LABELS, CAMERA_MOTIONS, CUSTOM_PRESET_NAME, MASTER_PROMPT_PRESETS, StoryProject, StoryScene, delete_user_story_preset, estimate_story_duration, get_all_story_prompt_presets, load_user_story_presets, save_user_story_preset, segment_story_script
from app.ui.widgets.story_tour import InteractiveTourGuide, TourStep
from app.services.story_image_service import assign_image_to_scene, assign_images_from_folder, format_display_time, generate_gemini_image, generate_scene_audio, get_story_provider_voices, sync_story_timeline_and_srt
from app.services.story_video_service import assign_video_to_scene, assign_videos_from_folder
from app.ui.widgets.story_youtube_window import StoryYoutubeDialog
from app.ui.widgets.story_ai_creator_dialog import StoryAICreatorDialog
from app.ui.widgets.story_ai_video_dialog import StoryAiVideoDialog
from app.ui.widgets.story_prompts_dialog import StoryExportPromptsDialog, StoryPromptsDialog
from app.ui.widgets.story_prompt_builder_dialog import StoryPromptBuilderDialog
from app.ui.widgets.story_voice_casting_dialog import StoryVoiceCastingDialog
from app.services.story_prompt_service import generate_synchronized_scene_prompts
from app.services.story_sfx_service import assign_auto_sfx_to_scenes, detect_sfx_for_text, get_available_sfx, open_custom_sfx_folder
logger = logging.getLogger(__name__)
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }
SAMPLE_STORY = ''

def _resolve_color(col = None):
    '''Chuyển đổi CustomTkinter color tuple (light, dark) thành chuỗi hex màu chuẩn cho widget Tkinter thuần.'''
    if isinstance(col, (list, tuple)):
        if len(col) > 1:
            return str(col[1])
        return None(str[0])
    return None(col)


class _TextBufferProxy:
    '''Proxy đệm văn bản tương thích hoàn toàn giao diện CTkTextbox (get, delete, insert...).'''
    
    def __init__(self = None, initial_text = None, on_change = None):
        self._content = initial_text
        self._on_change = on_change
        self._textbox = self

    
    def get(self = None, start = None, end = None):
        return self._content + '\n'

    
    def delete(self = None, start = None, end = None):
        self._content = ''
        if self._on_change:
            
            try:
                self._on_change(self._content)
                return None
                return None
            except Exception:
                return None


    
    def insert(self = None, index = None, chars = None):
        if index == '1.0':
            self._content = str(chars) + self._content
        elif index == 'end':
            self._content = self._content + str(chars)
        else:
            self._content = str(chars)
        if self._on_change:
            
            try:
                self._on_change(self._content)
                return None
                return None
            except Exception:
                return None


    
    def set_text(self = None, text = None):
        self._content = str(text)
        if self._on_change:
            
            try:
                self._on_change(self._content)
                return None
                return None
            except Exception:
                return None


    
    def winfo_exists(self = None):
        return True

    
    def bind(self = None, *args, **kwargs):
        pass



class ScriptEditorPopup(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


class PromptEditorPopup(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


class FastSceneOptionMenu(tk.Frame):
    pass
# WARNING: Decompyle incomplete


class StoryLoadingOverlay(tk.Frame):
    pass
# WARNING: Decompyle incomplete


class StoryEditorDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


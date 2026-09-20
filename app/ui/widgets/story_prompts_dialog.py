# Source Generated with Decompyle++
# File: story_prompts_dialog.pyc (Python 3.12)

'''Bảng Xuất Prompts AI Siêu Nhẹ (Story Prompts & Motion Export Dialog).

Thiết kế tối giản, tải tức thì (<20ms), chuyên biệt 100% cho việc xuất và sao chép:
- Prompt Ảnh (Image Prompts) cho Midjourney, Flux, Leonardo, SDXL.
- Prompt Video AI (Motion Prompts) cho Veo 3, Runway Gen-3, Kling, Luma.
- Prompt Thumbnail (Ảnh bìa YouTube kịch tính triệu view).
- Xuất toàn bộ kịch bản & prompt ra file .TXT và bảng tính .CSV (UTF-8 BOM).
'''
from __future__ import annotations
import csv
import logging
import os
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable
import customtkinter as ctk
from app.services.story_ai_creator_service import generate_thumbnail_prompt_fallback
from app.services.story_engine import StoryProject, StoryScene
from app.services.story_image_service import format_srt_timestamp
logger = logging.getLogger(__name__)
BG_DARK = '#0F172A'
BG_CARD = '#1E293B'
BG_TEXT = '#0B1120'
BORDER = '#334155'
TEXT = '#F8FAFC'
TEXT_DIM = '#94A3B8'
ACCENT = '#0284C7'
ACCENT_HOVER = '#0369A1'
ACCENT_TEXT = '#38BDF8'
PURPLE = '#7C3AED'
PURPLE_HOVER = '#6D28D9'
AMBER = '#D97706'
AMBER_HOVER = '#B45309'
SUCCESS = '#10B981'
SURFACE_BTN = '#334155'
SURFACE_BTN_HOVER = '#475569'

class StoryExportPromptsDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete

StoryPromptsDialog = StoryExportPromptsDialog

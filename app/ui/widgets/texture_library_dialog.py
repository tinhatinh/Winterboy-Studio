# Source Generated with Decompyle++
# File: texture_library_dialog.pyc (Python 3.12)

'''Texture Library Dialog — Cửa sổ quản lý & chọn Thư viện Video Texture Overlay.

Hỗ trợ quét danh sách video texture trong thư mục `libraries/textures`,
`library_textures`, và `app/assets/texture_library`.
Cho phép chọn 1 hoặc nhiều texture cùng lúc với 2 cơ chế phân bổ:
1. Xoay vòng tuần tự (Rotating Cycle 15s/lần)
2. Hòa trộn đa tầng (Multi-layer Stacking)
'''
from __future__ import annotations
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
import customtkinter as ctk
from app.services.story_engine import ensure_sample_textures, get_blend_mode_display_name, get_texture_library_dirs
logger = logging.getLogger(__name__)
BG_DARK = '#0F1117'
BG_CARD = '#1A1D27'
SURFACE_BTN = '#242838'
SURFACE_BTN_HOVER = '#2E3448'
ACCENT = '#8B5CF6'
ACCENT_HOVER = '#7C3AED'
TEXT = '#F1F5F9'
TEXT_DIM = '#94A3B8'
BORDER = '#2E3448'
SUCCESS = '#10B981'
WARNING = '#F59E0B'
_VIDEO_EXTS = {
    '.avi',
    '.mkv',
    '.mov',
    '.mp4',
    '.webm'}
DISTRIBUTION_OPTIONS = {
    'Xoay vòng tuần tự (15s/lần)': 'cycle_15s',
    'Hòa trộn đa tầng (Chồng lớp)': 'stack' }

def _format_size(size_bytes = None):
    if size_bytes < 1024:
        return f'''{size_bytes} B'''
    if None < 1048576:
        return f'''{size_bytes / 1024:.1f} KB'''
    return f'''{None / 1048576:.1f} MB'''


def _suggest_blend_mode(filename = None):
    '''Gợi ý chế độ hòa trộn tối ưu dựa trên loại texture.'''
    pass
# WARNING: Decompyle incomplete


class TextureLibraryDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


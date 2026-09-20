# Source Generated with Decompyle++
# File: music_library_dialog.pyc (Python 3.12)

'''Thư viện nhạc nền có sẵn (No Copyright) — Chọn & nghe thử nhanh cho video.'''
from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, BG_CARD, BG_DARK, BORDER, ON_ACCENT, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.ui.fluent_icons import fluent_icon
logger = logging.getLogger(__name__)
_SUPPORTED_EXTS = {
    '.aac',
    '.m4a',
    '.mp3',
    '.ogg',
    '.wav',
    '.flac'}

def _format_time(seconds = None):
    s = int(round(seconds))
    m = s // 60
    s = s % 60
    return f'''{m:02d}:{s:02d}'''


def get_music_library_dirs():
    '''Trả về danh sách các thư mục chứa thư viện nhạc có sẵn.

    Thứ tự ưu tiên:
    1. Thư mục PyInstaller bundle (nếu đóng gói exe)
    2. Thư mục gom tài nguyên chuẩn: libraries/music
    3. Thư mục cũ: library_music ở root (tương thích ngược)
    4. Thư mục assets hệ thống: app/assets/music_library
    '''
    base_dirs = []
    root = Path(__file__).resolve().parents[3]
    cwd = Path.cwd()
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = Path(sys._MEIPASS)
        base_dirs.append(meipass / 'libraries' / 'music')
        base_dirs.append(meipass / 'library_music')
        base_dirs.append(meipass / 'app' / 'assets' / 'music_library')
    base_dirs.append(root / 'libraries' / 'music')
    base_dirs.append(cwd / 'libraries' / 'music')
    base_dirs.append(root / 'library_music')
    base_dirs.append(cwd / 'library_music')
    app_assets = Path(__file__).resolve().parent.parent.parent / 'assets' / 'music_library'
    base_dirs.append(app_assets)
    primary_dir = root / 'libraries' / 'music'
    
    try:
        primary_dir.mkdir(parents = True, exist_ok = True)
        existing_dirs = []
        seen = set()
        for d in base_dirs:
            if d.is_dir():
                resolved = str(d.resolve()).lower()
                if resolved not in seen:
                    seen.add(resolved)
                    existing_dirs.append(d)
        continue
        if not existing_dirs:
            existing_dirs
        return [
            primary_dir]
    except Exception:
        continue
        except Exception:
            continue



class MusicLibraryDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


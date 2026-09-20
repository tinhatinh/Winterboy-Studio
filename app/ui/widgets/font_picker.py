# Source Generated with Decompyle++
# File: font_picker.pyc (Python 3.12)

'''
Font picker kiểu CapCut / Adobe:
  - Ô tìm realtime (token match, ưu tiên bắt đầu bằng query)
  - Danh sách hiển thị mẫu chữ bằng chính font đó
  - Phím ↑↓ / Enter / double-click
  - Font gần đây
'''
from __future__ import annotations
import tkinter as tk
from tkinter.font import font as tkfont
from pathlib import Path
from typing import Callable
import customtkinter as ctk
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_HOVER, BG_CARD, BG_INPUT, BG_SUNKEN, BORDER, ON_ACCENT, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, resolve
from app.services.system_fonts import clear_font_cache, font_stats, list_system_fonts, resolve_system_font
_RECENT: 'list[str]' = []
_MAX_RECENT = 12
_SAMPLE = 'Ag 字 あ 가 123'

def remember_font(name = None):
    if not name:
        name
    name = ''.strip()
    if not name:
        return None
# WARNING: Decompyle incomplete


def get_recent_fonts():
    return list(_RECENT)


def set_recent_fonts(names = None):
    '''Nạp recent từ last_config.json khi mở app.'''
    out = []
    if not names:
        names
# WARNING: Decompyle incomplete


def _score_font(name = None, needle = None, tokens = None):
    '''Điểm thấp hơn = khớp tốt hơn (Adobe-style ranking).'''
    pass
# WARNING: Decompyle incomplete


def filter_fonts(all_fonts = None, query = None, *, limit):
    if not query:
        query
    needle = ''.strip().casefold()
    if not needle:
        seen = set()
        out = []
        for r in _RECENT:
            for f in all_fonts:
                if not f.casefold() == r.casefold():
                    continue
                if not f not in seen:
                    continue
                out.append(f)
                seen.add(f)
                all_fonts
        for f in all_fonts:
            if f not in seen:
                out.append(f)
                seen.add(f)
            if not len(out) >= limit:
                continue
            all_fonts
            return out
        return out
# WARNING: Decompyle incomplete


def open_font_picker(master = None, *, current, on_pick, on_preview, title):
    '''Mở dialog tìm font — click = preview realtime trên playback, Enter/Dùng = chốt.'''
    pass
# WARNING: Decompyle incomplete


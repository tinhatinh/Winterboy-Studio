# Source Generated with Decompyle++
# File: voice_history_dialog.pyc (Python 3.12)

'''Bảng chọn voice đã tạo gần đây — chọn xong là render bake thẳng, không TTS.

Đặt trong cửa sổ riêng thay vì nhét vào cột công cụ: mỗi dòng cần tên nguồn,
thời lượng, thời điểm tạo và nút nghe thử, cột trái chỉ rộng 367px nên nhồi
vào đó chắc chắn bị cắt.

Hai việc chậm đều đẩy sang luồng nền, vì cả hai đều từng làm cửa sổ đứng hình:
đo thời lượng bằng ffprobe (~95ms mỗi file) và nạp file để nghe thử (~560ms
với bản 5 phút). Luồng nền chỉ tính toán rồi hẹn Tk cập nhật, không đụng widget.
'''
from __future__ import annotations
import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_DARK, BG_PANEL, ON_ACCENT, SURFACE_ALT, SURFACE_ALT_2, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED, WARNING, on_appearance_change, resolve
from app.services.voice_history import delete_all_voice_entries, delete_voice_entry, format_duration, humanize_when, load_cached_durations, measure_durations, scan_voices
logger = logging.getLogger(__name__)
_ROW_BG = (SURFACE_ALT, SURFACE_ALT_2)
@dataclass
class _RowUI:
    entry: object
    frame: tk.Frame
    bar: tk.Frame
    widgets: list = field(default_factory=list)
    meta: tk.Label | None = None
    play: ctk.CTkButton | None = None

class VoiceHistoryDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


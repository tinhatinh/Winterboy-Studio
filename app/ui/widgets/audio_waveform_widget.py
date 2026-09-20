# Source Generated with Decompyle++
# File: audio_waveform_widget.pyc (Python 3.12)

'''
audio_waveform_widget.py — Widget dải sóng âm (Audio Waveform Display) tương tác
Hiển thị đỉnh sóng âm thanh, khoảng lặng (silence), kim thời gian (playhead)
và hỗ trợ nhấp chuột/rê chuột tua chính xác (click-to-seek / scrubbing).
'''
from __future__ import annotations
import logging
import tkinter as tk
from typing import Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, BG_CARD, BG_SUNKEN, BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM, on_appearance_change, resolve
from app.services.waveform_service import WaveformData
logger = logging.getLogger(__name__)

def _format_time(s = None):
    s = max(0, float(s))
    m = int(s // 60)
    sec = s % 60
    return f'''{m:02d}:{sec:05.2f}'''


class AudioWaveformView(ctk.CTkFrame):
    pass
# WARNING: Decompyle incomplete


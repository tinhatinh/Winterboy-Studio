# Source Generated with Decompyle++
# File: module_caption_tools.pyc (Python 3.12)

'''Focused caption tools: subtitle look, SRT, STT and TTS each get one pane.'''
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_GOLD, ACCENT_HOVER, ACCENT_TEXT, BORDER, DANGER, DANGER_SOFT, DANGER_SOFT_HOVER, ON_DANGER_SOFT, DROPDOWN_BG, INFO, ON_ACCENT, ON_DANGER, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.core.state import AppState
from app.ui.modules.base_module import BaseModule
from app.ui.modules.module_subtitle import BG_STYLES, ENGINES, STT_LANGUAGES, STT_MODELS, TRANSLATE_LANGUAGES, VOICES
MENU_STYLE = {
    'fg_color': SURFACE_ALT,
    'button_color': ACCENT,
    'button_hover_color': ACCENT_HOVER,
    'dropdown_fg_color': DROPDOWN_BG,
    'dropdown_hover_color': ACCENT,
    'text_color': TEXT }

class _CaptionModule(BaseModule):
    pass
# WARNING: Decompyle incomplete


class ModuleCaptionStyle(_CaptionModule):
    pass
# WARNING: Decompyle incomplete


class ModuleSrtTools(_CaptionModule):
    pass
# WARNING: Decompyle incomplete


class ModuleStt(_CaptionModule):
    pass
# WARNING: Decompyle incomplete


def _short_label(label = None, limit = None):
    '''Rút gọn nhãn dài cho OptionMenu — giữ nguyên phần định danh trước «—».'''
    if not label:
        label
    label = ''.strip()
    if len(label) <= limit:
        return label
    return None[:limit - 1].rstrip() + '…'

_ELEVEN_MODEL_LABELS = [
    'eleven_multilingual_v2 — Khuyên dùng cho tiếng Việt',
    'eleven_turbo_v2_5 — Cân bằng chất lượng và tốc độ',
    'eleven_flash_v2_5 — Tạo nhanh, phù hợp nghe thử',
    'eleven_turbo_v2 — Tốc độ cao',
    'eleven_flash_v2 — Tốc độ rất cao',
    'eleven_v3 — Thử nghiệm biểu cảm']

def _eleven_model_id(value = None):
    if not value:
        value
    return ''.split('—', 1)[0].strip()


def _eleven_model_label(value = None):
    model_id = _eleven_model_id(value)
    for label in _ELEVEN_MODEL_LABELS:
        if not _eleven_model_id(label) == model_id:
            continue
        
        return _ELEVEN_MODEL_LABELS, label
    return _short_label(value)


class ModuleTts(_CaptionModule):
    pass
# WARNING: Decompyle incomplete


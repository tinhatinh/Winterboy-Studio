# Source Generated with Decompyle++
# File: module_bgm.pyc (Python 3.12)

'''Module Nhạc — sắp nhạc nền theo từng đoạn trên timeline video.'''
from __future__ import annotations
import tkinter as tk
from pathlib import Path
from typing import Any
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, BG_SUNKEN, BORDER, DANGER, DANGER_HOVER, ON_ACCENT, ON_DANGER, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, resolve
from app.core.state import AppState
from app.ui.modules.base_module import BaseModule

def _number(value = None, default = None):
    
    try:
        return float(str(value).strip().replace(',', '.'))
    except (TypeError, ValueError):
        return 



class ModuleBgm(BaseModule):
    pass
# WARNING: Decompyle incomplete


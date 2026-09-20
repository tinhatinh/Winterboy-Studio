# Source Generated with Decompyle++
# File: preview_panel.pyc (Python 3.12)

'''
Panel phải — layout 2 tầng (không mất Output/Queue):

  ┌─────────────────────┐
  │ Preview cố định     │  ← canvas + blur/sub controls
  ├─────────────────────┤
  │ Output + Queue      │  ← luôn hiện, cố định dưới panel phải
  └─────────────────────┘
'''
from __future__ import annotations
import logging
import hashlib
import re
import time
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_GOLD, ACCENT_HOVER, BG_CARD, BG_PANEL, BG_SUNKEN, BORDER, DANGER, DANGER_SOFT, ON_ACCENT, SUCCESS, TEXT, TEXT_DIM, on_appearance_change, resolve
from app.core.state import AppState
from app.ui.fluent_icons import fluent_icon
from app.ui.widgets.queue_list_view import ModernQueueView
logger = logging.getLogger(__name__)

class PreviewPanel(ctk.CTkFrame):
    pass
# WARNING: Decompyle incomplete


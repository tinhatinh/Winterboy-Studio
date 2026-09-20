# Source Generated with Decompyle++
# File: update_notice_dialog.pyc (Python 3.12)

'''Cửa sổ thông báo & cập nhật khởi động (Startup Update & Notice Dialog).

Hiển thị tự động 1 lần duy nhất trong ngày khi có bản cập nhật mới hoặc thông báo quan trọng.
Hỗ trợ Tagline màu đỏ nổi bật hướng dẫn người dùng lên website tải bản mới cài chồng lên.
'''
from __future__ import annotations
import logging
import sys
import webbrowser
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, DANGER, INFO, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED, resolve
from app.services.notification_service import DEFAULT_DOWNLOAD_URL, DEFAULT_UPDATE_TAGLINE, mark_notification_shown_today
from app.ui.fluent_icons import fluent_icon
logger = logging.getLogger(__name__)

def show_startup_notification_dialog(parent = None, notif = None, on_close = None):
    '''Hiển thị cửa sổ pop-up thông báo nhỏ gọn khi khởi động app.'''
    pass
# WARNING: Decompyle incomplete


# Source Generated with Decompyle++
# File: notification_history_dialog.pyc (Python 3.12)

'''Hộp thoại Lịch Sử Thông Báo (Notification History Dialog).

Hiển thị danh sách 10 thông báo và bản cập nhật gần nhất từ hệ thống.
Tích hợp trong mục Tài Khoản qua biểu tượng cái chuông "🔔 Thông Báo".
Hỗ trợ Tagline màu đỏ quan trọng cho các bản cập nhật để người dùng biết tải file mới cài đè lên.
'''
from __future__ import annotations
import logging
import sys
import threading
import webbrowser
from datetime import datetime
from typing import Any
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, DANGER, INFO, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED, resolve
from app.services.notification_service import DEFAULT_DOWNLOAD_URL, DEFAULT_UPDATE_TAGLINE, get_recent_notifications
logger = logging.getLogger(__name__)

def _format_date(iso_str = None):
    if not iso_str:
        return ''
    
    try:
        clean = iso_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean)
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return 



def open_notification_history_dialog(parent = None):
    '''Mở hộp thoại hiển thị 10 thông báo và bản cập nhật gần nhất.'''
    pass
# WARNING: Decompyle incomplete


# Source Generated with Decompyle++
# File: queue_list_view.pyc (Python 3.12)

'''
ModernQueueView — Giao diện hàng đợi render siêu gọn nhẹ cho Winterboy Studio Pro.

Đặc điểm:
- Kích thước siêu gọn (chiều cao cố định ~32px), tiết kiệm diện tích tối đa.
- Không chiếm không gian của khối tiến trình hoặc khu vực preview video.
- Mỗi video hiển thị dạng hàng thanh thoát:
  • Icon 🎬 + Tên video
  • Pill badge trạng thái theo ngữ cảnh:
    - Xanh neon: Đang xử lý (FFmpeg, TTS, Timeline, Bake...)
    - Xanh lục: Hoàn tất, Sẵn sàng
    - Đỏ: Lỗi, Đã dừng
    - Xám: Chờ...
- Hỗ trợ cuộn mượt mà khi có nhiều video.
- Tương thích 100% API Treeview (exists, selection, selection_set, item, delete, insert, bind).
'''
from __future__ import annotations
import logging
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_TEXT, BG_CARD, BG_SUNKEN, BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM
logger = logging.getLogger(__name__)
ROW_BG_SELECTED = ('#E1F5FE', '#142836')
ROW_BG_NORMAL = 'transparent'
ROW_BG_HOVER = ('#EDF2F7', '#22242A')

class ModernQueueView(ctk.CTkFrame):
    pass
# WARNING: Decompyle incomplete


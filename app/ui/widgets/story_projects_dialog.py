# Source Generated with Decompyle++
# File: story_projects_dialog.pyc (Python 3.12)

'''Cửa sổ Modal hiển thị danh sách các Dự Án Dựng Truyện Đã Lưu (StoryProjectsDialog).

Cho phép người dùng:
- Xem danh sách các dự án Dựng Truyện đã lưu trong thư mục output/projects/.
- Xem tiêu đề, thời gian cập nhật, số phân cảnh và chủ đề Tiếng Việt.
- Mở dự án để tiếp tục làm việc trong Studio Kể Chuyện.
- Xóa vĩnh viễn dự án không còn dùng.
'''
from __future__ import annotations
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, BG_CARD, BG_DARK, BG_PANEL, BORDER, DANGER, ON_ACCENT, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.services.job_workspace import STORY_PROJECTS_ROOT
logger = logging.getLogger(__name__)

def list_story_projects():
    '''Lấy danh sách các dự án Dựng Truyện từ output/projects/ kèm thông tin video đã xuất, voice và media sẵn sàng.'''
    projects = []
    if not STORY_PROJECTS_ROOT.is_dir():
        return projects
# WARNING: Decompyle incomplete


class StoryProjectsDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


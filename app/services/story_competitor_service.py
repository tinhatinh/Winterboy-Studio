# Source Generated with Decompyle++
# File: story_competitor_service.pyc (Python 3.12)

__doc__ = 'Dịch vụ quản lý Hồ Sơ & Preset Kênh Đối Thủ (Competitor Channel Profiles & Presets).\n\nCho phép người dùng:\n1. Quản lý tập trung toàn bộ cấu hình mẫu cho từng Kênh Đối Thủ (Style ảnh, Prompt nhân vật, Tone giọng, Ngôn ngữ, Nhạc nền, Tỉ lệ).\n2. Đồng bộ hóa phong cách đồng nhất (Content Consistency) cho mọi video làm theo kênh đối thủ đó.\n3. Gắn Tag tên kênh đối thủ vào từng dự án để dễ dàng quản lý, lọc và tìm kiếm trong danh sách dự án.\n'
from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[2]
PRESETS_DIR = ROOT_DIR / 'presets'
COMPETITORS_FILE = PRESETS_DIR / 'story_competitors.json'
# WARNING: Decompyle incomplete

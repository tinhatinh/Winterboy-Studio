# Source Generated with Decompyle++
# File: preset_manager.pyc (Python 3.12)

__doc__ = '\nPreset Manager — Quản lý mẫu cấu hình 1-Click cho Mumu Studio Pro.\n\nCho phép lưu toàn bộ thiết lập hiện tại thành preset đặt tên riêng\n(ví dụ: "TikTok Shorts 9:16", "Review Phim Voice Hoài My", v.v.)\nvà nạp lại nhanh chỉ bằng một cú nhấp chuột.\n'
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
PRESETS_DIR = ROOT / 'presets'
DEFAULT_PRESET_NAME = '-- Không dùng (Mặc định) --'
# WARNING: Decompyle incomplete

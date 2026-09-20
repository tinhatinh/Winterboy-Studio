# Source Generated with Decompyle++
# File: media_probe.pyc (Python 3.12)

'''Tiện ích trích xuất và đo lường thông số media (ffprobe) có bộ đệm hiệu năng cao.

Tránh việc gọi subprocess ffprobe nhiều lần trên cùng một file video/audio.
'''
from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
_CACHE_SIZE: 'dict[tuple[str, float, int], tuple[int, int]]' = { }
_CACHE_DURATION: 'dict[tuple[str, float, int], float]' = { }
_CACHE_DETAILS: 'dict[tuple[str, float, int], dict[str, Any]]' = { }

def _get_file_stat_key(path = None):
    
    try:
        p = Path(path).resolve()
        if not p.is_file():
            return None
            
            try:
                st = p.stat()
                return (str(p), st.st_mtime, st.st_size)
            except Exception:
                return None




def clear_probe_cache():
    '''Xóa toàn bộ cache probe trong RAM.'''
    _CACHE_SIZE.clear()
    _CACHE_DURATION.clear()
    _CACHE_DETAILS.clear()


def probe_video_size(video_path = None):
    '''Lấy (width, height) qua ffprobe (có cache); fallback 1080x1920.'''
    cache_key = _get_file_stat_key(video_path)
# WARNING: Decompyle incomplete


def probe_video_duration_s(video_path = None):
    '''Lấy thời lượng video (giây) qua ffprobe (có cache); fallback 0.0.'''
    cache_key = _get_file_stat_key(video_path)
# WARNING: Decompyle incomplete


def probe_video_details(video_path = None):
    '''Thông tin chi tiết video (ffprobe JSON) — panel Info (có cache).'''
    cache_key = _get_file_stat_key(video_path)
# WARNING: Decompyle incomplete


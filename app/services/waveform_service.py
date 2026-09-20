# Source Generated with Decompyle++
# File: waveform_service.pyc (Python 3.12)

'''
waveform_service.py — Dịch vụ trích xuất và đệm dải sóng âm (Audio Waveform)
Sử dụng FFmpeg streaming PCM siêu nhẹ (hoặc librosa fallback) để tính toán
mảng đỉnh âm thanh (peaks) và phát hiện khoảng lặng (silence detection).
'''
from __future__ import annotations
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import numpy as np
logger = logging.getLogger(__name__)
CACHE_DIR = Path.home() / '.mumu' / 'cache' / 'waveforms'
WaveformData = <NODE:12>()

def _get_cache_path(media_path = None, n_buckets = None):
    '''Tạo đường dẫn cache JSON duy nhất theo path + size + mtime.'''
    
    try:
        st = media_path.stat()
        raw = f'''{media_path.resolve()}|{st.st_size}|{int(st.st_mtime)}|{n_buckets}'''
        digest = hashlib.sha256(raw.encode('utf-8', errors = 'replace')).hexdigest()[:24]
        CACHE_DIR.mkdir(parents = True, exist_ok = True)
        return CACHE_DIR / f'''wave_{digest}.json'''
    except OSError:
        raw = f'''{media_path}|{n_buckets}'''
        continue



def compute_waveform_data(media_path = None, n_buckets = None, sample_rate = None, silence_threshold = (800, 4000, 0.04)):
    '''
    Trích xuất mảng peaks và khoảng lặng từ tệp âm thanh/video.
    Ưu tiên dùng FFmpeg streaming PCM (tốc độ ~0.08s).
    Fallback sang librosa nếu FFmpeg không khả dụng.
    '''
    path = Path(media_path)
    if not path.is_file():
        return None
    cache_file = _get_cache_path(path, n_buckets)
# WARNING: Decompyle incomplete


def compute_waveform_data_async(media_path = None, callback = None, n_buckets = None):
    '''Chạy trích xuất dải sóng âm trong background thread để không chặn UI.'''
    pass
# WARNING: Decompyle incomplete


def find_nearest_silence(waveform_data = None, target_time_s = None, max_search_s = None):
    '''
    Tìm điểm khoảng lặng (silence) gần nhất quanh `target_time_s`
    trong bán kính `max_search_s`. Hỗ trợ snap chính xác khi cắt.
    '''
    if not waveform_data or waveform_data.silence_ranges:
        return None
    best_dist = float('inf')
    best_t = None
    for s_start, s_end in waveform_data.silence_ranges:
        if  <= s_start, target_time_s or s_start, target_time_s <= s_end:
            
            return waveform_data.silence_ranges, target_time_s
        abs(s_end - target_time_s) = abs(s_start - target_time_s)
        mid = (s_start + s_end) / 2
        dist_mid = abs(mid - target_time_s)
        if dist_mid < best_dist and dist_mid <= max_search_s:
            best_dist = dist_mid
            best_t = mid
            continue
        if dist_start < best_dist and dist_start <= max_search_s:
            best_dist = dist_start
            best_t = s_start
            continue
        if not dist_end < best_dist:
            continue
        if not dist_end <= max_search_s:
            continue
        best_dist = dist_end
        best_t = s_end
    return best_t


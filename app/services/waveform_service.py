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
CACHE_DIR = Path.home() / '.winterboy' / 'cache' / 'waveforms'


@dataclass
class WaveformData:
    peaks: list[float]
    rms: list[float]
    duration_s: float
    silence_ranges: list[list[float]]


def _get_cache_path(media_path: Path, n_buckets: int) -> Path:
    '''Tạo đường dẫn cache JSON duy nhất theo path + size + mtime.'''

    try:
        st = media_path.stat()
        raw = f'''{media_path.resolve()}|{st.st_size}|{int(st.st_mtime)}|{n_buckets}'''
    except OSError:
        raw = f'''{media_path}|{n_buckets}'''
    digest = hashlib.sha256(raw.encode('utf-8', errors = 'replace')).hexdigest()[:24]
    CACHE_DIR.mkdir(parents = True, exist_ok = True)
    return CACHE_DIR / f'''wave_{digest}.json'''


def compute_waveform_data(media_path: str | Path, n_buckets: int = 800, sample_rate: int = 4000, silence_threshold: float = 0.04) -> WaveformData | None:
    '''
    Trích xuất mảng peaks và khoảng lặng từ tệp âm thanh/video.
    Ưu tiên dùng FFmpeg streaming PCM (tốc độ ~0.08s).
    Fallback sang librosa nếu FFmpeg không khả dụng.
    '''
    # TODO(khôi phục hành vi): toàn bộ thân hàm mất từ sau `cache_file = ...`
    # (thiếu dấu trong bản decompile). Chưa đối chiếu dis phần FFmpeg/librosa.
    raise NotImplementedError('chưa khôi phục từ bytecode: waveform_service.compute_waveform_data')


def compute_waveform_data_async(media_path: str | Path, callback: Callable[[WaveformData | None], None], n_buckets: int = 800) -> None:
    '''Chạy trích xuất dải sóng âm trong background thread để không chặn UI.'''

    def _worker():
        try:
            res = compute_waveform_data(media_path, n_buckets = n_buckets)
        except Exception as e:
            logger.debug('compute_waveform_data_async error: %s', e)
            res = None
        callback(res)


    t = threading.Thread(target = _worker, daemon = True, name = 'winterboy-waveform-worker')
    t.start()
    return None


def find_nearest_silence(waveform_data: WaveformData, target_time_s: float, max_search_s: float = 1.0) -> float | None:
    '''
    Tìm điểm khoảng lặng (silence) gần nhất quanh `target_time_s`
    trong bán kính `max_search_s`. Hỗ trợ snap chính xác khi cắt.
    '''
    if not waveform_data or not waveform_data.silence_ranges:
        return None
    best_dist = float('inf')
    best_t = None
    for s_start, s_end in waveform_data.silence_ranges:
        if s_start <= target_time_s <= s_end:
            return target_time_s
        dist_start = abs(s_start - target_time_s)
        dist_end = abs(s_end - target_time_s)
        mid = (s_start + s_end) / 2.0
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

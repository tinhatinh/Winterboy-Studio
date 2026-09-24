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
_CACHE_SIZE: dict[tuple[str, float, int], tuple[int, int]] = { }
_CACHE_DURATION: dict[tuple[str, float, int], float] = { }
_CACHE_DETAILS: dict[tuple[str, float, int], dict[str, Any]] = { }


def _get_file_stat_key(path: str | Path) -> tuple[str, float, int] | None:
    try:
        p = Path(path).resolve()
        if not p.is_file():
            return None
        st = p.stat()
        return (str(p), st.st_mtime, st.st_size)
    except Exception:
        return None


def clear_probe_cache() -> None:
    '''Xóa toàn bộ cache probe trong RAM.'''
    _CACHE_SIZE.clear()
    _CACHE_DURATION.clear()
    _CACHE_DETAILS.clear()


def probe_video_size(video_path: str | Path) -> tuple[int, int]:
    '''Lấy (width, height) qua ffprobe (có cache); fallback 1080x1920.'''
    cache_key = _get_file_stat_key(video_path)
    if cache_key is not None and cache_key in _CACHE_SIZE:
        return _CACHE_SIZE[cache_key]
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return (1080, 1920)
    res = (1080, 1920)
    try:
        p = subprocess.run(
            [
                ffprobe,
                '-v',
                'error',
                '-select_streams',
                'v:0',
                '-show_entries',
                'stream=width,height',
                '-of',
                'csv=p=0:s=x',
                str(video_path)],
            capture_output = True,
            text = True,
            encoding = 'utf-8',
            errors = 'replace',
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            timeout = 30)
        if p.returncode == 0 and 'x' in (p.stdout or ''):
            w, h = p.stdout.strip().split('x')[:2]
            res = (max(1, int(w)), max(1, int(h)))
    except Exception as e:
        logger.warning('probe size fail: %s', e)
    if cache_key is not None:
        _CACHE_SIZE[cache_key] = res
    return res


def probe_video_duration_s(video_path: str | Path) -> float:
    '''Lấy thời lượng video (giây) qua ffprobe (có cache); fallback 0.0.'''
    cache_key = _get_file_stat_key(video_path)
    if cache_key is not None and cache_key in _CACHE_DURATION:
        return _CACHE_DURATION[cache_key]
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return 0.0
    duration = 0.0
    try:
        p = subprocess.run(
            [
                ffprobe,
                '-v',
                'error',
                '-show_entries',
                'format=duration',
                '-of',
                'default=noprint_wrappers=1:nokey=1',
                str(video_path)],
            capture_output = True,
            text = True,
            encoding = 'utf-8',
            errors = 'replace',
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            timeout = 30)
        if p.returncode == 0 and (p.stdout or '').strip():
            duration = max(0.0, float((p.stdout or '').strip()))
    except Exception as e:
        logger.warning('probe duration fail: %s', e)
    if cache_key is not None:
        _CACHE_DURATION[cache_key] = duration
    return duration


def probe_video_details(video_path: str | Path) -> dict[str, Any]:
    '''Thông tin chi tiết video (ffprobe JSON) — panel Info (có cache).'''
    cache_key = _get_file_stat_key(video_path)
    if cache_key is not None and cache_key in _CACHE_DETAILS:
        return dict(_CACHE_DETAILS[cache_key])
    video_path = Path(video_path)
    info = {
        'name': video_path.name if video_path else '',
        'path': str(video_path) if video_path else '',
        'exists': bool(video_path and video_path.is_file()),
        'width': 0,
        'height': 0,
        'fps': 0.0,
        'duration_s': 0.0,
        'size_bytes': 0,
        'video_codec': '',
        'audio_codec': '',
        'bitrate': 0,
        'format': '' }
    if not info['exists']:
        return info
    try:
        info['size_bytes'] = int(video_path.stat().st_size)
    except OSError:
        pass
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        w, h = probe_video_size(video_path)
        info['width'], info['height'] = w, h
        info['duration_s'] = probe_video_duration_s(video_path)
        if cache_key is not None:
            _CACHE_DETAILS[cache_key] = dict(info)
        return info
    try:
        p = subprocess.run(
            [
                ffprobe,
                '-v',
                'error',
                '-show_entries',
                'format=duration,size,bit_rate,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,bit_rate',
                '-of',
                'json',
                str(video_path)],
            capture_output = True,
            text = True,
            encoding = 'utf-8',
            errors = 'replace',
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            timeout = 30)
        if p.returncode != 0:
            if cache_key is not None:
                _CACHE_DETAILS[cache_key] = dict(info)
            return info
        data = json.loads(p.stdout or '{}')
        fmt = data.get('format') or { }
        try:
            info['duration_s'] = float(fmt.get('duration') or 0)
        except (TypeError, ValueError):
            pass
        try:
            info['bitrate'] = int(float(fmt.get('bit_rate') or 0))
        except (TypeError, ValueError):
            pass
        info['format'] = str(fmt.get('format_name') or '')
        try:
            sz = int(float(fmt.get('size') or 0))
            if sz > 0:
                info['size_bytes'] = sz
        except (TypeError, ValueError):
            pass
        for stream in data.get('streams') or [ ]:
            ctype = stream.get('codec_type')
            if ctype == 'video' and not info['width']:
                info['width'] = int(stream.get('width') or 0)
                info['height'] = int(stream.get('height') or 0)
                info['video_codec'] = str(stream.get('codec_name') or '')
                rate = stream.get('avg_frame_rate') or stream.get('r_frame_rate') or '0/1'
                try:
                    if isinstance(rate, str) and '/' in rate:
                        a, b = rate.split('/', 1)
                        info['fps'] = float(a) / float(b) if float(b) else 0.0
                    else:
                        info['fps'] = float(rate or 0)
                except (TypeError, ValueError, ZeroDivisionError):
                    info['fps'] = 0.0
            elif ctype == 'audio' and not info['audio_codec']:
                info['audio_codec'] = str(stream.get('codec_name') or '')
    except Exception as e:
        logger.debug('probe details: %s', e)
    if cache_key is not None:
        _CACHE_DETAILS[cache_key] = dict(info)
        if info['width'] and info['height']:
            _CACHE_SIZE[cache_key] = (info['width'], info['height'])
        if info['duration_s']:
            _CACHE_DURATION[cache_key] = info['duration_s']
    return info

# Source Generated with Decompyle++
# File: blur_region_editor.pyc (Python 3.12)

__doc__ = '\nBlurRegionEditor — preview playback + blur + subtitle VI live.\n\n- Playback / scrub (OpenCV / ffmpeg)\n- Kéo / crop vùng blur che sub gốc\n- Overlay phụ đề VI: font, size, style nền, kéo thả vị trí\n- Sync state AppState (blur + sub)\n'
from __future__ import annotations
import hashlib
import json
import logging
import math
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_GOLD, ACCENT_HOVER, BG_CARD, BG_DARK, BG_PANEL, BG_SUNKEN, BORDER, DROPDOWN_BG, INFO, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, on_appearance_change, resolve
from app.services.subtitle_layout import wrap_subtitle_lines
from app.services.system_fonts import list_system_fonts, resolve_system_font
from app.ui.fluent_icons import fluent_icon
from app.ui.widgets.audio_waveform_widget import AudioWaveformView
SHOW_AUDIO_WAVEFORM = True
logger = logging.getLogger(__name__)
HANDLE = 8
MIN_BOX = 12
PLAY_REFRESH_HZ = 60
SEEK_THROTTLE_MS = 55
PREVIEW_DECODE_MAX = 960

def _preview_source_key(video_path = None):
    '''Stable preview key; a changed source automatically invalidates its cache.'''
    st = video_path.stat()
    signature = (int(st.st_size), int(st.st_mtime_ns))
    raw = f'''{video_path.resolve()}|{signature[0]}|{signature[1]}'''
    return (hashlib.sha256(raw.encode('utf-8', errors = 'replace')).hexdigest(), signature)


def _preview_media_cache_paths(video_path = None):
    (key, _) = _preview_source_key(video_path)
    root = Path(tempfile.gettempdir()) / 'mumu_preview_audio'
    return (root / f'''{key}.meta.json''', root / f'''{key}.thumb.jpg''')


def _load_preview_media_cache(video_path = None):
    
    try:
        (meta_path, thumb_path) = _preview_media_cache_paths(video_path)
        metadata = { }
        if meta_path.is_file():
            payload = json.loads(meta_path.read_text(encoding = 'utf-8'))
            if isinstance(payload, dict):
                if not payload.get('version'):
                    payload.get('version')
                if int(0) == 1:
                    if not payload.get('metadata'):
                        payload.get('metadata')
                    metadata = dict({ })
        image = None
        if thumb_path.is_file():
            cached = Image.open(thumb_path)
            image = cached.convert('RGB').copy()
            
            try:
                None(None, None)
                return (metadata, image)
                with None:
                    if not None:
                        pass
                
                try:
                    continue
                except Exception:
                    exc = None
                    logger.debug('preview media cache miss: %s', exc)
                    del exc
                    return None
                    None = 
                    del exc





def _save_preview_media_cache(video_path = None, metadata = None, image = None):
    pass
# WARNING: Decompyle incomplete


def _frame_to_worker_image(frame = None, *, max_side, fast):
    '''Convert and shrink a decoded BGR frame before handing it to Tk.'''
    import cv2
    import numpy as np
    (h, w) = frame.shape[:2]
    longest = max(w, h)
    if longest > max_side:
        scale = max_side / float(longest)
        interp = cv2.INTER_LINEAR if fast else cv2.INTER_AREA
        frame = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation = interp)
    if not frame.flags['C_CONTIGUOUS']:
        frame = np.ascontiguousarray(frame)
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

_PreviewDecodeResult = <NODE:12>()

class _PreviewDecoderWorker:
    '''Single owner of VideoCapture; Tk only consumes already-decoded images.'''
    
    def __init__(self = None):
        self.results = queue.Queue(maxsize = 3)
        self._commands = queue.Queue()
        self._frame_lock = threading.Lock()
        self._pending_frame = None
        self._wake = threading.Event()
        self._closed = False
        self._latest_generation = 0
        self._cap = None
        self._path = None
        self._fps = 25
        self._frame_index = -1
        self._thread = threading.Thread(target = self._run, daemon = True, name = 'mumu-preview-decoder')
        self._thread.start()

    
    def load(self, generation = None, path = None, t_s = None, max_side = ('generation', 'int', 'path', 'Path', 't_s', 'float', 'max_side', 'int', 'return', 'None')):
        self._latest_generation = generation
        self._frame_lock
        self._pending_frame = None
        None(None, None)
        self._commands.put(('load', generation, path, t_s, max_side))
        self._wake.set()
        return None
        with None:
            if not None:
                pass
        continue

    
    def request_frame(self = None, generation = None, path = None, t_s = ('generation', 'int', 'path', 'Path', 't_s', 'float', 'max_side', 'int', 'force_seek', 'bool', 'sequential', 'bool', 'light', 'bool', 'return', 'None'), *, max_side, force_seek, sequential, light):
        self._frame_lock
        self._pending_frame = (generation, path, t_s, max_side, force_seek, sequential, light)
        None(None, None)
        self._wake.set()
        return None
        with None:
            if not None:
                pass
        continue

    
    def close(self = None):
        self._closed = True
        self._commands.put(('close',))
        self._wake.set()

    
    def unload(self = None, generation = None):
        self._latest_generation = generation
        self._frame_lock
        self._pending_frame = None
        None(None, None)
        self._commands.put(('unload', generation))
        self._wake.set()
        return None
        with None:
            if not None:
                pass
        continue

    
    def _push(self = None, result = None):
        
        try:
            self.results.put_nowait(result)
            return None
        except queue.Full:
            self.results.get_nowait()
        except queue.Empty:
            return None

        continue

    
    def _release(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _run(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _handle_load(self, generation = None, path = None, t_s = None, max_side = ('generation', 'int', 'path', 'Path', 't_s', 'float', 'max_side', 'int', 'return', 'None')):
        started = time.perf_counter()
        timings = { }
        self._release()
        (metadata, cached_image) = _load_preview_media_cache(path)
        if metadata:
            metadata
        cache_hit = bool(cached_image is not None)
        timings['cache_lookup'] = time.perf_counter() - started
    # WARNING: Decompyle incomplete

    
    def _handle_frame(self, generation, path, t_s, max_side = None, force_seek = None, sequential = None, light = ('generation', 'int', 'path', 'Path', 't_s', 'float', 'max_side', 'int', 'force_seek', 'bool', 'sequential', 'bool', 'light', 'bool', 'return', 'None')):
        pass
    # WARNING: Decompyle incomplete



def canvas_size_for_ratio(ratio = None, *, max_w, max_h, video_w, video_h):
    '''
    Khung preview theo tỉ lệ xuất / video — fill max box (to, dễ kéo blur/sub).
    9:16 portrait · 16:9 landscape · keep = theo video (fallback 9:16).
    '''
    pass
# WARNING: Decompyle incomplete

_WIN_FONTS = Path('C:\\Windows\\Fonts')
# WARNING: Decompyle incomplete

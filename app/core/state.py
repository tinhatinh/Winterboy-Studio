# Source Generated with Decompyle++
# File: state.pyc (Python 3.12)

'''
AppState — toàn bộ biến (CTk variables) map 1-1 với control UI.

Giai đoạn 2 sẽ đọc state.to_dict() để build FFmpeg.
Giai đoạn 3 sẽ dùng state cho Gemini / TTS.
'''
from __future__ import annotations
import json
import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator
import customtkinter as ctk
logger = logging.getLogger(__name__)
_CAPCUT_FIX_ASSET_DIR = Path(__file__).resolve().parents[1] / 'resources' / 'capcut_fix'

def bundled_capcut_fix_paths():
    '''Return the recovery BAT and Device JSON shipped with Winterboy Studio.'''
    return (_CAPCUT_FIX_ASSET_DIR / 'fix_shark.bat', _CAPCUT_FIX_ASSET_DIR / 'device.json')

from app.services.job_workspace import DEFAULT_VIDEO_OUTPUT
AppState = <NODE:12>()

def g_safe(v = None):
    
    try:
        return v.get()
    except Exception:
        return None



def default_config_path():
    '''File cấu hình mặc định (tự load khi mở app).'''
    if os.environ.get('WINTERBOY_PROJECT_ROOT'):
        root = Path(os.environ['WINTERBOY_PROJECT_ROOT']).resolve()
    elif getattr(sys, 'frozen', False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parents[2]
    candidates = [
        root / 'output' / 'last_config.json',
        root.parent.parent / 'output' / 'last_config.json',
        root / 'apps' / 'auto_render' / 'output' / 'last_config.json']
    for c in candidates:
        if not c.is_file():
            continue
        
        return candidates, c
    return root / 'output' / 'last_config.json'


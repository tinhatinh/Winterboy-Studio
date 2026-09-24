# Source Generated with Decompyle++
# File: capcut_tts_extractor.pyc (Python 3.12)

"""Dịch vụ trích xuất file âm thanh TTS từ Project CapCut Desktop.

Khi người dùng mở CapCut và dùng tính năng 'Đọc văn bản' (Text-To-Speech) của ByteDance,
CapCut sẽ sinh ra các đoạn âm thanh và lưu vết trong draft_content.json.
Dịch vụ này tự động:
1. Xác định project CapCut mới nhất (hoặc theo thư mục chỉ định).
2. Phân tích draft_content.json, bóc tách các file audio và vị trí timeline tương ứng.
3. Sử dụng FFmpeg ghép các đoạn audio theo đúng timeline của phụ đề thành 1 file master hoàn chỉnh.
4. Trả về đường dẫn file audio thành phẩm để Winterboy Studio Pro nạp vào luồng render.
"""
from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
WINDOWS_DRAFTS_ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'CapCut' / 'User Data' / 'Projects' / 'com.lveditor.draft'
US = 1000000

def _hidden_kwargs():
    if sys.platform.startswith('win'):
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 134217728)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
        startupinfo.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
        return {
            'creationflags': creationflags,
            'startupinfo': startupinfo }
    return { }


def get_default_drafts_root():
    override = (os.environ.get('MUMU_CAPCUT_DRAFTS') or '').strip()
    if override:
        return Path(override)
    return WINDOWS_DRAFTS_ROOT


def find_latest_capcut_project(drafts_root = None):
    '''Tìm thư mục project CapCut được cập nhật gần nhất.'''
    root = Path(drafts_root) if drafts_root else get_default_drafts_root()
    if not root.is_dir():
        return None
    candidates = []
    for item in root.iterdir():
        if not item.is_dir():
            continue
        if not (item / 'draft_content.json').is_file():
            continue
        candidates.append(item)
    if not candidates:
        return None
    
    def _mtime(p: Path) -> float:

        try:
            content = p / 'draft_content.json'
            if content.is_file():
                return content.stat().st_mtime
            return p.stat().st_mtime
        except OSError:
            return 0.0


    candidates.sort(key = _mtime, reverse = True)
    return candidates[0]


def extract_tts_audio_from_capcut(project_dir: 'Path | str | None' = None, output_dir: 'Path | str | None' = None) -> 'Path | None':
    '''Trích xuất và đồng bộ âm thanh TTS từ CapCut draft thành 1 file master.

    Args:
        project_dir: Thư mục dự án CapCut (nếu None sẽ lấy project mới nhất).
        output_dir: Nơi lưu file audio xuất ra (nếu None lưu vào thư mục project CapCut).

    Returns:
        Path tới file audio master (.mp3/.wav), hoặc None nếu không tìm thấy audio.
    '''
    # Bản decompile dừng ở bước chọn `content_file` (dòng 105 trong dis); phần đọc
    # draft_content.json, ghép audio theo timeline và chạy FFmpeg (~850 instruction)
    # mất hoàn toàn -> chưa có căn cứ để viết lại, không đoán.
    raise NotImplementedError('chưa khôi phục từ bytecode: capcut_tts_extractor.extract_tts_audio_from_capcut')


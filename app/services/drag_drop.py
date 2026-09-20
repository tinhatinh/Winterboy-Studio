# Source Generated with Decompyle++
# File: drag_drop.pyc (Python 3.12)

'''
Smart Drag & Drop Service — Tự động nhận diện và nạp tệp khi kéo thả từ Windows Explorer.

Hỗ trợ kéo thả:
  - Video (.mp4, .mkv, .avi, .mov, .webm...): nạp vào hàng đợi và xem trước
  - Nhạc (.mp3, .wav, .aac, .m4a, .flac...): nạp vào danh sách nhạc nền BGM
  - Phụ đề (.srt, .vtt, .ass): nạp vào bộ đệm phụ đề
  - Hình ảnh (.png, .jpg, .webp...): nạp làm logo / watermark
  - Thư mục: quét toàn bộ file video bên trong và nạp hàng loạt
'''
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Callable
logger = logging.getLogger(__name__)
VIDEO_EXTS = {
    '.avi',
    '.flv',
    '.m4v',
    '.mkv',
    '.mov',
    '.mp4',
    '.wmv',
    '.webm'}
AUDIO_EXTS = {
    '.aac',
    '.m4a',
    '.mp3',
    '.ogg',
    '.wav',
    '.flac'}
SUBTITLE_EXTS = {
    '.ass',
    '.srt',
    '.vtt'}
IMAGE_EXTS = {
    '.bmp',
    '.jpg',
    '.png',
    '.jpeg',
    '.webp'}

def install_drag_drop(window = None, on_drop_callback = None):
    '''Cài đặt hook kéo thả Windows Explorer lên cửa sổ chính (64-bit Unicode an toàn, không làm hỏng WndProc).'''
    pass
# WARNING: Decompyle incomplete


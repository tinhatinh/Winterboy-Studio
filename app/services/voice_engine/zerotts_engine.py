# Source Generated with Decompyle++
# File: zerotts_engine.pyc (Python 3.12)

__doc__ = '\nzerotts_engine — Lõi tổng hợp giọng nói ZeroTTS (AI tiếng Việt Offline 48kHz ONNX).\n\nĐặc điểm kiến trúc:\n1. Mô hình 202M tham số chạy hoàn toàn trên CPU qua ONNX Runtime + NumPy.\n2. Bộ giải mã âm thanh MOSS codec chất lượng cao 48kHz.\n3. Chuẩn hóa văn bản tiếng Việt tích hợp (số, tiền tệ, ngày tháng, từ viết tắt).\n4. Tự động tải và cache model từ Hugging Face Hub (zeroweight-ai/ZeroTTS) dạng lazy load.\n5. Danh mục 8 giọng chuẩn phòng thu với kho mẫu nghe thử tức thì 0ms.\n'
from __future__ import annotations
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import soundfile as sf
logger = logging.getLogger(__name__)
SAMPLE_RATE = 48000
AUDIO_EXTENSIONS = {
    '.m4a',
    '.ogg',
    '.flac',
    '.mp3',
    '.wav'}
ZEROTTS_PRESET_VOICES: 'List[Dict[str, str]]' = [
    {
        'id': 'maichi',
        'name': 'maichi',
        'display_name': 'Mai Chi',
        'gender': 'Nữ',
        'style': 'Kể chuyện',
        'description': 'Nữ trẻ, kể chuyện, nhẹ nhàng, thân thiện',
        'label': 'Mai Chi (Nữ - Kể chuyện nhẹ nhàng)' },
    {
        'id': 'baotrang',
        'name': 'baotrang',
        'display_name': 'Bảo Trang',
        'gender': 'Nữ',
        'style': 'Tin tức',
        'description': 'Nữ trưởng thành, tin tức, rõ ràng, trung tính',
        'label': 'Bảo Trang (Nữ - Tin tức chuẩn)' },
    {
        'id': 'kimoanh',
        'name': 'kimoanh',
        'display_name': 'Kim Oanh',
        'gender': 'Nữ',
        'style': 'Kể chuyện',
        'description': 'Nữ trung niên, kể chuyện, ấm áp, truyền cảm',
        'label': 'Kim Oanh (Nữ - Truyền cảm ấm áp)' },
    {
        'id': 'hamy',
        'name': 'hamy',
        'display_name': 'Hà My',
        'gender': 'Nữ',
        'style': 'Hoạt hình',
        'description': 'Nữ trẻ, hoạt hình, cao, biểu cảm',
        'label': 'Hà My (Nữ - Hoạt hình vui vẻ)' },
    {
        'id': 'giahuy',
        'name': 'giahuy',
        'display_name': 'Gia Huy',
        'gender': 'Nam',
        'style': 'Kể chuyện',
        'description': 'Nam trẻ, kể chuyện, trầm ấm, tâm tình',
        'label': 'Gia Huy (Nam - Kể chuyện trầm ấm)' },
    {
        'id': 'huuduc',
        'name': 'huuduc',
        'display_name': 'Hữu Đức',
        'gender': 'Nam',
        'style': 'Kể chuyện',
        'description': 'Nam lớn tuổi, kể chuyện, trầm, điềm đạm',
        'label': 'Hữu Đức (Nam - Điềm đạm lớn tuổi)' },
    {
        'id': 'quangminh',
        'name': 'quangminh',
        'display_name': 'Quang Minh',
        'gender': 'Nam',
        'style': 'Tin tức',
        'description': 'Nam trẻ, tin tức, rõ ràng, dứt khoát',
        'label': 'Quang Minh (Nam - Tin tức dứt khoát)' },
    {
        'id': 'tiendat',
        'name': 'tiendat',
        'display_name': 'Tiến Đạt',
        'gender': 'Nam',
        'style': 'Bình luận',
        'description': 'Nam trẻ, bình luận, sôi nổi, năng lượng cao',
        'label': 'Tiến Đạt (Nam - Sôi nổi năng lượng)' }]
# WARNING: Decompyle incomplete

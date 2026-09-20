# Source Generated with Decompyle++
# File: vieneu_engine.pyc (Python 3.12)

'''
vieneu_engine — Lõi tổng hợp giọng nói VieNeu-TTS v3 Turbo và Nhân bản giọng (Voice Cloning).

Học hỏi kiến trúc từ Mumu Voice:
1. Sử dụng thư viện vieneu v3 Turbo (48kHz).
2. Danh mục 20 giọng preset 3 miền Bắc, Trung, Nam.
3. Voice Cloning: Tự động trích đoạn 8 giây có năng lượng RMS lớn nhất từ file ghi âm/mẫu,
   khử ồn và đăng ký profile giọng cá nhân lưu trong thư mục voices/.
'''
import os
import re
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
import numpy as np
import soundfile as sf
from app.services.voice_engine.voices_config import PRESET_VOICES, VOICE_NAMES, VOICE_LABELS
logger = logging.getLogger(__name__)
VOICE_NAME_PATTERN = re.compile('^[\\w\\- ]{1,60}$', re.UNICODE)
SAMPLE_RATE = 48000
AUDIO_EXTENSIONS = {
    '.m4a',
    '.ogg',
    '.flac',
    '.mp3',
    '.wav'}

def select_loudest_reference_segment(source = None, maximum_seconds = None):
    '''
    Trích xuất đoạn audio 8 giây có năng lượng RMS cao nhất từ file âm thanh mẫu.
    Học hỏi từ select_loudest_reference_segment của Mumu Voice.
    '''
    (samples, sr) = sf.read(str(source), dtype = 'float32', always_2d = True)
    mono = samples.mean(axis = 1)
    max_frames = round(maximum_seconds * sr)
    if len(mono) <= max_frames:
        return (source, False)
    squared = None.square(mono, dtype = np.float64)
    cumulative_energy = np.concatenate(([
        0], np.cumsum(squared)))
    rolling_energy = cumulative_energy[max_frames:] - cumulative_energy[:-max_frames]
    start_frame = int(np.argmax(rolling_energy))
    chosen = samples[start_frame:start_frame + max_frames]
    temp_file = tempfile.NamedTemporaryFile(suffix = '.wav', delete = False)
    selected_path = Path(temp_file.name)
    None(None, None)
# WARNING: Decompyle incomplete


class VieneuEngine:
    pass
# WARNING: Decompyle incomplete


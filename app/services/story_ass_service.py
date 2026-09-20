# Source Generated with Decompyle++
# File: story_ass_service.pyc (Python 3.12)

'''Dịch vụ sinh file phụ đề ASS (Advanced SubStation Alpha) chuyên biệt cho Mumu Studio Pro.

Hỗ trợ:
- Phụ đề động TikTok (Word-by-word Karaoke bounce pop): Từng từ nảy to 120% rồi thu về 100% kèm màu Neon.
- Phụ đề TikTok Glow: Từng từ phát sáng viền và đổi màu Neon khi được đọc.
- Phụ đề Karaoke Wave: Hiệu ứng quét màu mượt mà \\kf centiseconds.
- Phụ đề tĩnh điện ảnh (Static subtitle).
- Thẻ tiêu đề mở đầu 3-Second Hook Master (Top Hook Badge) giữ chân người xem trong 3 giây đầu.
- Tự động ngắt cụm từ thông minh (3-5 từ cho video ngắn hoặc đầy đủ câu kịch bản).
- Phân bổ thời lượng từng từ có trọng số âm tiết và độ trễ ngắt nghỉ tự nhiên theo dấu câu.
'''
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
TIKTOK_NEON_COLORS = {
    'Vàng Neon': '#FFE600',
    'Xanh Neon': '#00F0FF',
    'Xanh Mint': '#00FF88',
    'Cam Rực': '#FFA500',
    'Hồng Neon': '#FF3399',
    'Trắng': '#FFFFFF' }

def hex_to_ass_color(hex_str = None, alpha = None):
    '''Chuyển đổi mã màu hex (#RRGGBB) sang định dạng màu ASS (&HAABBGGRR).'''
    if not hex_str:
        hex_str
    raw = '#FFFFFF'.strip().lstrip('#')
    if len(raw) == 3:
        raw = (lambda .0: pass# WARNING: Decompyle incomplete
)(raw())
    if len(raw) != 6:
        raw = 'FFFFFF'
    r = raw[0:2]
    g = raw[2:4]
    b = raw[4:6]
    alpha_clamped = max(0, min(1, float(alpha)))
    ass_alpha = int(round((1 - alpha_clamped) * 255))
    return f'''&H{ass_alpha:02X}{b}{g}{r}&'''


def format_ass_timestamp(seconds = None):
    '''Chuyển đổi số giây (float) sang định dạng thời gian ASS: H:MM:SS.cs (centiseconds).'''
    sec = max(0, float(seconds))
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        secs += 1
        cs = 0
        if secs >= 60:
            mins += 1
            secs = 0
            if mins >= 60:
                hrs += 1
                mins = 0
    return f'''{hrs}:{mins:02d}:{secs:02d}.{cs:02d}'''


def split_text_into_word_chunks(text = None, max_words_per_chunk = None):
    '''Phân tách văn bản kịch bản thành các cụm từ ngắn gọn (3-5 từ/cụm) chuẩn phong cách TikTok/Shorts.'''
    pass
# WARNING: Decompyle incomplete


def calculate_chunk_word_timings(chunks = None, total_duration = None):
    '''Phân bổ thời gian hiển thị từng cụm và từng từ trong cụm dựa trên trọng số ký tự và độ trễ ngắt nghỉ.'''
    pass
# WARNING: Decompyle incomplete


def build_story_ass_subtitles(scenes = None, output_ass_path = None, sub_options = None, aspect_ratio = (None, '16:9', ''), hook_title = ('scenes', 'list[dict[str, Any]]', 'output_ass_path', 'str | Path', 'sub_options', 'dict[str, Any] | None', 'aspect_ratio', 'str', 'hook_title', 'str', 'return', 'Path')):
    '''Tạo tệp phụ đề .ass hoàn chỉnh với hiệu ứng TikTok Bouncing Karaoke và Hook Master Banner.'''
    if not sub_options:
        sub_options
    opts = dict({ })
    out_file = Path(output_ass_path).resolve()
    out_file.parent.mkdir(parents = True, exist_ok = True)
    is_portrait = '9:16' in str(aspect_ratio)
    canvas_w = 1080 if is_portrait else 1920
    canvas_h = 1920 if is_portrait else 1080
    if not opts.get('sub_font'):
        opts.get('sub_font')
    raw_font = str('Arial').replace(',', ' ').strip()
    if not 'comica' in raw_font.lower() or raw_font:
        font_name = 'Arial'
    else:
        font_name = raw_font
    default_sz = 36 if is_portrait else 26
# WARNING: Decompyle incomplete

generate_story_ass_file = build_story_ass_subtitles

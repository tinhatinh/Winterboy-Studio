# Source Generated with Decompyle++
# File: subtitle_layout.pyc (Python 3.12)

'''Xuống dòng phụ đề — nguồn duy nhất cho cả xem trước và MP4.

Trước đây preview không xuống dòng còn ASS xuống dòng cứng ở 24 ký tự, nên câu
tiếng Việt dài hiện 1 dòng khi căn chỉnh nhưng ra 3 dòng trong file xuất. Vì ASS
dùng ``Alignment=8`` (neo mép trên), dòng dư mọc xuống và phụ đề chiếm nhiều
chiều cao hơn hẳn thứ người dùng nhìn thấy.

Module này đo bề rộng thật bằng Pillow với đúng file font người dùng chọn, nên:

* chỗ ngắt dòng phụ thuộc **cỡ chữ và bề rộng khung**, không phải số ký tự;
* preview và renderer gọi cùng một hàm nên luôn ngắt giống nhau — miễn là tỉ lệ
  ``font_size / max_width_px`` giữ nguyên (cả hai đều nhân cùng hệ số scale).

Nếu thiếu Pillow hoặc không tìm được font, tự rơi về cách đếm ký tự cũ để không
làm hỏng luồng render.
'''
from __future__ import annotations
import logging
from functools import lru_cache
from typing import Any
from app.services.srt_utils import wrap_subtitle_text
from app.services.system_fonts import resolve_system_font
logger = logging.getLogger(__name__)
FALLBACK_MAX_CHARS = 24
DEFAULT_MAX_LINES = 3
_load_font = (lambda font_name = None, size = None: pass# WARNING: Decompyle incomplete
)()

def _text_width(font = None, text = None, letter_spacing = None):
    if not text:
        return 0
    if not letter_spacing:
        letter_spacing
    spacing_extra = max(0, len(text) - 1) * max(0, float(0))
    
    try:
        return float(font.getlength(text)) + spacing_extra
    except Exception:
        pass

    
    try:
        return float(font.getsize(text)[0]) + spacing_extra
    except Exception:
        return 



def wrap_subtitle_lines(text = None, *, font_name, font_size, max_width_px, letter_spacing, max_lines):
    '''Cắt ``text`` thành các dòng vừa ``max_width_px`` khi vẽ bằng font đã chọn.

    Trả về list dòng (đã bỏ dòng rỗng). Dòng cuối bị rút gọn kèm "…" nếu vượt
    quá ``max_lines``, giống hành vi cũ.
    '''
    pass
# WARNING: Decompyle incomplete


def wrap_subtitle_block(text = None, *, font_name, font_size, max_width_px, letter_spacing, max_lines):
    '''Như :func:`wrap_subtitle_lines` nhưng trả chuỗi nối bằng ``\\n``.'''
    return '\n'.join(wrap_subtitle_lines(text, font_name = font_name, font_size = font_size, max_width_px = max_width_px, letter_spacing = letter_spacing, max_lines = max_lines))


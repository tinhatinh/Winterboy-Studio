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


@lru_cache(maxsize = 64)
def _load_font(font_name: str, size: int) -> Any | None:
    '''Font Pillow để ĐO bề rộng (cache theo tên + cỡ).'''

    try:
        from PIL import ImageFont
    except Exception:
        return None
    path = resolve_system_font(font_name)
    if path is None:
        return None
    try:
        return ImageFont.truetype(str(path), size = max(1, int(size)))
    except Exception:
        return None


def _text_width(font: Any, text: str, letter_spacing: float = 0.0) -> float:
    if not text:
        return 0.0
    spacing_extra = max(0, len(text) - 1) * max(0.0, float(letter_spacing or 0.0))
    try:
        return float(font.getlength(text)) + spacing_extra
    except Exception:
        pass
    try:
        return float(font.getsize(text)[0]) + spacing_extra
    except Exception:
        return float(len(text)) + spacing_extra


def wrap_subtitle_lines(
        text: str,
        *,
        font_name: str = 'Arial',
        font_size: int = 36,
        max_width_px: float = 0.0,
        letter_spacing: float = 0.0,
        max_lines: int = DEFAULT_MAX_LINES,
) -> list[str]:
    '''Cắt ``text`` thành các dòng vừa ``max_width_px`` khi vẽ bằng font đã chọn.

    Trả về list dòng (đã bỏ dòng rỗng). Dòng cuối bị rút gọn kèm "…" nếu vượt
    quá ``max_lines``, giống hành vi cũ.
    '''
    raw = ' '.join((text or '').split())
    if not raw:
        return []
    max_lines = max(1, int(max_lines))
    font = _load_font(font_name or 'Arial', int(font_size))
    if font is None or max_width_px <= 1:
        # Không đo được (thiếu Pillow / không tìm ra font): đếm ký tự như trước
        return [
            ln for ln in wrap_subtitle_text(raw, max_chars = FALLBACK_MAX_CHARS,
                                            max_lines = max_lines).split('\n') if ln]

    limit = float(max_width_px)
    if _text_width(font, raw, letter_spacing) <= limit:
        return [raw]

    def split_long_word(word: str) -> list[str]:
        '''Từ dài hơn cả khung (URL, chuỗi CJK không dấu cách) → cắt cứng.'''
        parts = []
        current = ''
        for ch in word:
            if current and _text_width(font, current + ch, letter_spacing) > limit:
                parts.append(current)
                current = ch
            else:
                current += ch
        if current:
            parts.append(current)
        return parts

    lines = []
    current = ''
    for word in raw.split(' '):
        if not word:
            continue
        if _text_width(font, word, letter_spacing) > limit:
            if current:
                lines.append(current)
                current = ''
            chunks = split_long_word(word)
            lines.extend(chunks[:-1])
            current = chunks[-1] if chunks else ''
            continue
        candidate = f'''{current} {word}''' if current else word
        if _text_width(font, candidate, letter_spacing) <= limit:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)

    if len(lines) > max_lines:
        head = lines[:max_lines - 1]
        tail = ' '.join(lines[max_lines - 1:])
        while tail and _text_width(font, tail + '…') > limit:
            tail = tail[:-1].rstrip()
        lines = head + [tail + '…' if tail else '…']

    return [ln for ln in lines if ln]


def wrap_subtitle_block(
        text: str,
        *,
        font_name: str = 'Arial',
        font_size: int = 36,
        max_width_px: float = 0.0,
        letter_spacing: float = 0.0,
        max_lines: int = DEFAULT_MAX_LINES,
) -> str:
    '''Như :func:`wrap_subtitle_lines` nhưng trả chuỗi nối bằng ``\\n``.'''
    return '\n'.join(wrap_subtitle_lines(text, font_name = font_name, font_size = font_size,
                                         max_width_px = max_width_px,
                                         letter_spacing = letter_spacing,
                                         max_lines = max_lines))

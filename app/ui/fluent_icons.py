'''Icon Fluent sắc nét cho CustomTkinter, render từ font icon có sẵn của Windows.

Không dùng emoji vì hình dáng/kích thước thay đổi theo máy. Segoe Fluent Icons
là bộ icon giao diện chuẩn của Windows; ảnh được raster ở 4x rồi thu nhỏ để nét
ở cả DPI 100–150%. Nếu font Fluent không tồn tại, helper tự vẽ fallback đơn giản.
'''
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

_GLYPHS = {
    'settings': 59155,
    'video': 59156,
    'stop': 59162,
    'info': 59718,
    'close': 59153,
    'volume': 59239,
    'play': 59240,
    'pause': 59241,
    'fullscreen': 59200,
    'back_window': 59199,
    'mute': 59215,
    'cc': 59376,
    'blur': 59366,
    'view': 59536,
    'previous': 59538,
    'document': 59331,
    'microphone': 59168,
    'music': 59606,
    'tag': 59628,
    'trim': 59274,
    'effects': 59280,
    'globe': 59252,
    'folder': 59448,
    'save': 59214,
    'cursor': 59337,
    'undo': 59303,
    'redo': 59302,
    'log': 59557,
    'delete': 59213,
    'trash': 59213,
    'zoom_in': 59555,
    'zoom_out': 59167,
    'fit': 59255,
    'user': 59259,
    'shield': 59928,
    'key': 59607,
    'copy': 59592,
    'bell': 60047,
    'megaphone': 59273,
}

def _font_path() -> Path | None:
    fonts = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
    for name in ('segmdl2.ttf', 'SegoeIcons.ttf'):
        path = fonts / name
        if path.is_file():
            return path
    return None

def _pair(color) -> tuple[str, str]:
    if isinstance(color, (tuple, list)) and len(color) >= 2:
        return (str(color[0]), str(color[1]))
    value = str(color)
    return (value, value)

def _render_undo(size: int, color: str) -> Image.Image:
    '''Vẽ icon Undo dạng cung tròn uốn cong hiện đại chuẩn Studio (Premiere/CapCut/Figma).'''
    scale = 8
    S = max(8, int(size)) * scale
    image = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx = S * 0.52
    cy = S * 0.54
    r = S * 0.31
    stroke = max(2, int(S * 0.115))
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=210, end=45, fill=color, width=stroke)
    tip_x = S * 0.16
    tip_y = S * 0.4
    draw.polygon([
        (tip_x, tip_y),
        (tip_x + S * 0.22, tip_y - S * 0.18),
        (tip_x + S * 0.18, tip_y - S * 0.03),
        (tip_x + S * 0.22, tip_y + S * 0.12),
    ], fill=color)
    return image.resize((max(8, int(size)), max(8, int(size))), Image.Resampling.LANCZOS)

def _render_redo(size: int, color: str) -> Image.Image:
    '''Vẽ icon Redo dạng cung tròn xuôi chiều đối xứng hoàn hảo.'''
    from PIL import ImageOps
    undo_img = _render_undo(size, color)
    return ImageOps.mirror(undo_img)

@lru_cache(maxsize=256)
def _render(name: str, size: int, color: str) -> Image.Image:
    if name == 'undo':
        return _render_undo(size, color)
    if name == 'redo':
        return _render_redo(size, color)
    scale = 4
    side = max(8, int(size)) * scale
    image = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    path = _font_path()
    codepoint = _GLYPHS.get(name, _GLYPHS['info'])
    if path is not None:
        font = ImageFont.truetype(str(path), max(8, int(side * 0.78)))
        glyph = chr(codepoint)
        box = draw.textbbox((0, 0), glyph, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        x = (side - width) / 2 - box[0]
        y = (side - height) / 2 - box[1]
        draw.text((x, y), glyph, font=font, fill=color)
    else:
        # không có font: vẽ khung bo góc thay hình, vẫn rõ ở cỡ nhỏ
        pad = max(2, side // 6)
        stroke = max(2, side // 12)
        draw.rounded_rectangle(
            (pad, pad, side - pad, side - pad),
            radius=max(2, side // 8), outline=color, width=stroke)

    return image.resize((max(8, int(size)), max(8, int(size))), Image.Resampling.LANCZOS)

def fluent_icon(name: str, *, size: int = 16, color='#FFFFFF') -> ctk.CTkImage:
    '''Tạo CTkImage tự đổi màu theo light/dark theme.'''
    light, dark = _pair(color)
    return ctk.CTkImage(
        light_image=_render(name, int(size), light),
        dark_image=_render(name, int(size), dark),
        size=(int(size), int(size)))

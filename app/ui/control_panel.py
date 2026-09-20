# Source Generated with Decompyle++
# File: control_panel.pyc (Python 3.12)

'''Compact CapCut-style tool rail and single active settings pane.'''
from __future__ import annotations
import logging
import sys
import customtkinter as ctk
from PIL import Image, ImageDraw
logger = logging.getLogger(__name__)
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_HOVER, BG_CARD, BG_PANEL, BG_SUNKEN, BORDER, ON_ACCENT, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.core.state import AppState
from app.ui.modules.module_bgm import ModuleBgm
from app.ui.modules.module_blur import ModuleBlur
from app.ui.modules.module_brand import ModuleBrand
from app.ui.modules.module_bypass import ModuleBypass
from app.ui.modules.module_caption_tools import ModuleCaptionStyle, ModuleSrtTools, ModuleStt, ModuleTts
from app.ui.modules.module_story import ModuleStory
from app.ui.modules.module_trim import ModuleTrim
from app.ui.modules.module_video import ModuleVideo

class _ToolScroll(ctk.CTkScrollableFrame):
    pass
# WARNING: Decompyle incomplete


def _draw_nav_icon(name = None, color = None):
    '''Bộ icon nét vẽ gốc của thanh công cụ bên trái.'''
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = 5
    if name == 'video':
        draw.rounded_rectangle((10, 15, 48, 48), radius = 6, outline = color, width = width)
        draw.polygon([
            (27, 24),
            (27, 40),
            (40, 32)], fill = color)
        return image
    if None == 'subtitle':
        draw.rounded_rectangle((8, 13, 56, 51), radius = 5, outline = color, width = width)
        draw.line((18, 27, 46, 27), fill = color, width = width)
        draw.line((18, 39, 39, 39), fill = color, width = width)
        return image
    if None == 'srt':
        draw.rounded_rectangle((15, 8, 49, 56), radius = 4, outline = color, width = width)
        draw.line((23, 24, 42, 24), fill = color, width = width)
        draw.line((23, 35, 42, 35), fill = color, width = width)
        draw.line((23, 46, 35, 46), fill = color, width = width)
        return image
    if None == 'stt':
        draw.rounded_rectangle((24, 10, 40, 37), radius = 8, outline = color, width = width)
        draw.arc((16, 23, 48, 50), 0, 180, fill = color, width = width)
        draw.line((32, 50, 32, 56), fill = color, width = width)
        return image
    if None == 'tts':
        draw.polygon([
            (10, 26),
            (22, 26),
            (37, 14),
            (37, 50),
            (22, 38),
            (10, 38)], outline = color, width = width)
        draw.arc((30, 20, 51, 44), -60, 60, fill = color, width = width)
        return image
    if None == 'blur':
        draw.ellipse((10, 10, 42, 42), outline = color, width = width)
        draw.ellipse((23, 23, 54, 54), outline = color, width = width)
        return image
    if None == 'bgm':
        draw.line((38, 12, 38, 43), fill = color, width = width)
        draw.line((38, 12, 53, 17), fill = color, width = width)
        draw.ellipse((18, 37, 34, 53), outline = color, width = width)
        draw.ellipse((37, 31, 53, 47), outline = color, width = width)
        return image
    if None == 'brand':
        draw.polygon([
            (32, 9),
            (54, 32),
            (32, 55),
            (10, 32)], outline = color, width = width)
        draw.ellipse((27, 27, 37, 37), fill = color)
        return image
    if None == 'trim':
        draw.ellipse((10, 36, 25, 51), outline = color, width = width)
        draw.ellipse((39, 36, 54, 51), outline = color, width = width)
        draw.line((22, 37, 49, 15), fill = color, width = width)
        draw.line((42, 37, 16, 15), fill = color, width = width)
        return image
    if None == 'story':
        draw.line((32, 14, 32, 50), fill = color, width = width)
        draw.line((12, 18, 32, 14), fill = color, width = width)
        draw.line((12, 18, 12, 48), fill = color, width = width)
        draw.line((12, 48, 32, 50), fill = color, width = width)
        draw.line((52, 18, 32, 14), fill = color, width = width)
        draw.line((52, 18, 52, 48), fill = color, width = width)
        draw.line((52, 48, 32, 50), fill = color, width = width)
        draw.line((18, 27, 26, 26), fill = color, width = 3)
        draw.line((18, 36, 26, 35), fill = color, width = 3)
        draw.line((38, 26, 46, 27), fill = color, width = 3)
        draw.line((38, 35, 46, 36), fill = color, width = 3)
        return image
    None.polygon([
        (32, 8),
        (37, 26),
        (56, 32),
        (37, 38),
        (32, 56),
        (26, 38),
        (8, 32),
        (26, 26)], fill = color)
    return image


class ControlPanel(ctk.CTkFrame):
    pass
# WARNING: Decompyle incomplete


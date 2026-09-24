'''Compact CapCut-style tool rail and single active settings pane.'''
from __future__ import annotations
import logging
import sys
import customtkinter as ctk
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# Màu + font lấy từ theme chung để thanh công cụ và các module luôn cùng bộ
# nhận diện.AppState là nguồn trạng thái duy nhất; callbacks là bundle hàm mà
# main window truyền xuống để module tự báo lỗi / tự xin vẽ lại.
from app.config.theme import ACCENT_TEXT, ACCENT, ACCENT_HOVER, BG_CARD, BG_PANEL, BG_SUNKEN, BORDER, ON_ACCENT, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.core.state import AppState
from app.ui.modules.module_bgm import ModuleBgm
from app.ui.modules.module_blur import ModuleBlur
from app.ui.modules.module_brand import ModuleBrand
from app.ui.modules.module_bypass import ModuleBypass
from app.ui.modules.module_caption_tools import ModuleCaptionStyle, ModuleSrtTools, ModuleStt, ModuleTts
from app.ui.modules.module_ocr import ModuleOcr
# ModuleStory là 'Dựng Truyện' (kịch bản nhiều phân đoạn) nên tách riêng khỏi
# module_caption_tools; ModuleTrim xử lý cắt video, ModuleVideo là bảng điều
# khiển thông số video gốc.
from app.ui.modules.module_story import ModuleStory
from app.ui.modules.module_trim import ModuleTrim
from app.ui.modules.module_video import ModuleVideo


class _ToolScroll(ctk.CTkScrollableFrame):
    '''Smooth and responsive wheel scrolling for the active tool pane.'''

    def _check_if_valid_scroll(self, widget):
        if widget is None:
            return False
        if super()._check_if_valid_scroll(widget):
            return True
        try:
            pane = getattr(self._parent_frame, 'master', None)
            p = widget
            while p is not None:
                if p == pane or p == self._parent_frame:
                    return True
                p = getattr(p, 'master', None)
            return False
        except Exception:
            return False

    def ensure_mouse_wheel(self) -> None:
        '''Đảm bảo sự kiện cuộn chuột luôn được gắn và hoạt động trơn tru.'''
        try:
            if 'linux' in sys.platform:
                self.bind_all('<Button-4>', self._mouse_wheel_all, add=True)
                self.bind_all('<Button-5>', self._mouse_wheel_all, add=True)

            else:
                self.bind_all('<MouseWheel>', self._mouse_wheel_all, add=True)
        except Exception:
            pass

    def _mouse_wheel_all(self, event):
        if not self._check_if_valid_scroll(event.widget):
            return
        if sys.platform.startswith('win'):
            delta = getattr(event, 'delta', 0)
            if not delta:
                return
            direction = -1 if delta > 0 else 1
            units = max(2, round(abs(delta) / 2.5))
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview('scroll', direction * units, 'units')
            elif self._parent_canvas.yview() != (0.0, 1.0):
                self._parent_canvas.yview('scroll', direction * units, 'units')
        elif sys.platform == 'darwin':
            delta = getattr(event, 'delta', 0)
            if not delta:
                return
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview('scroll', -delta, 'units')
            elif self._parent_canvas.yview() != (0.0, 1.0):
                self._parent_canvas.yview('scroll', -delta, 'units')
        else:
            direction = -1 if getattr(event, 'num', 0) == 4 else 1
            if self._shift_pressed:
                if self._parent_canvas.xview() != (0.0, 1.0):
                    self._parent_canvas.xview_scroll(direction, 'units')
            elif self._parent_canvas.yview() != (0.0, 1.0):
                self._parent_canvas.yview_scroll(direction, 'units')


def _draw_nav_icon(name: str, color: str) -> Image.Image:
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
    elif name == 'subtitle':
        draw.rounded_rectangle((8, 13, 56, 51), radius = 5, outline = color, width = width)
        draw.line((18, 27, 46, 27), fill = color, width = width)
        draw.line((18, 39, 39, 39), fill = color, width = width)
    elif name == 'srt':
        draw.rounded_rectangle((15, 8, 49, 56), radius = 4, outline = color, width = width)
        draw.line((23, 24, 42, 24), fill = color, width = width)
        draw.line((23, 35, 42, 35), fill = color, width = width)
        draw.line((23, 46, 35, 46), fill = color, width = width)
    elif name == 'stt':
        draw.rounded_rectangle((24, 10, 40, 37), radius = 8, outline = color, width = width)
        draw.arc((16, 23, 48, 50), 0, 180, fill = color, width = width)
        draw.line((32, 50, 32, 56), fill = color, width = width)
    elif name == 'tts':
        draw.polygon([
            (10, 26),
            (22, 26),
            (37, 14),
            (37, 50),
            (22, 38),
            (10, 38)],
            outline = color,
            width = width)
        draw.arc((30, 20, 51, 44), -60, 60, fill = color, width = width)
    elif name == 'blur':
        draw.ellipse((10, 10, 42, 42), outline = color, width = width)
        draw.ellipse((23, 23, 54, 54), outline = color, width = width)
    elif name == 'bgm':
        draw.line((38, 12, 38, 43), fill = color, width = width)
        draw.line((38, 12, 53, 17), fill = color, width = width)
        draw.ellipse((18, 37, 34, 53), outline = color, width = width)
        draw.ellipse((37, 31, 53, 47), outline = color, width = width)
    elif name == 'ocr':
        # khung quét 4 góc + hai dòng chữ đang đọc
        draw.line((10, 19, 10, 10), fill = color, width = width)
        draw.line((10, 10, 19, 10), fill = color, width = width)
        draw.line((54, 19, 54, 10), fill = color, width = width)
        draw.line((54, 10, 45, 10), fill = color, width = width)
        draw.line((10, 45, 10, 54), fill = color, width = width)
        draw.line((10, 54, 19, 54), fill = color, width = width)
        draw.line((54, 45, 54, 54), fill = color, width = width)
        draw.line((54, 54, 45, 54), fill = color, width = width)
        draw.line((19, 27, 45, 27), fill = color, width = width)
        draw.line((19, 38, 37, 38), fill = color, width = width)
    elif name == 'brand':
        draw.polygon([
            (32, 9),
            (54, 32),
            (32, 55),
            (10, 32)],
            outline = color, width = width)
        draw.ellipse((27, 27, 37, 37), fill = color)
    elif name == 'trim':
        draw.ellipse((10, 36, 25, 51), outline = color, width = width)
        draw.ellipse((39, 36, 54, 51), outline = color, width = width)
        draw.line((22, 37, 49, 15), fill = color, width = width)
        draw.line((42, 37, 16, 15), fill = color, width = width)
    elif name == 'story':
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
    else:
        draw.polygon([
            (18, 24),
            (22, 12),
            (30, 18),
            (34, 18),
            (42, 12),
            (46, 24),
            (54, 30),
            (56, 42),
            (60, 54),
            (46, 50),
            (32, 54),
            (18, 50),
            (4, 54),
            (8, 42),
            (10, 30)],
            fill = color)
    return image


class ControlPanel(ctk.CTkFrame):
    '''Left rail like CapCut: click one tool, edit it in one focused pane.'''

    NAV = [
        ('video', 'Video'),
        ('subtitle', 'Phụ đề'),
        ('stt', 'STT'),
        ('srt', 'SRT'),
        ('tts', 'TTS'),
        ('blur', 'Che mờ'),
        ('bgm', 'Nhạc'),
        ('ocr', 'OCR'),
        ('brand', 'Logo'),
        ('trim', 'Cắt'),
        ('fx', 'Hiệu ứng'),
        ('story', 'Dựng Truyện'),
    ]

    def __init__(self, master, state: AppState, callbacks: dict, **kwargs):
        super().__init__(master,
                         fg_color = BG_PANEL,
                         corner_radius = 4,
                         border_width = 1,
                         border_color = BORDER,
                         **kwargs)
        self.state = state
        self.cb = callbacks
        self.callbacks = callbacks
        self._active_key = ''
        self._nav_buttons = {}
        self.grid_columnconfigure(0, weight = 0, minsize = 94)
        self.grid_columnconfigure(1, weight = 1)
        self.grid_rowconfigure(0, weight = 1)
        rail = ctk.CTkFrame(self, fg_color = BG_SUNKEN, corner_radius = 4, width = 94)
        rail.grid(row = 0, column = 0, sticky = 'nsw', padx = (5, 3), pady = 5)
        rail.grid_propagate(False)
        ctk.CTkLabel(rail,
                     text = 'Features',
                     text_color = ACCENT_TEXT,
                     font = ctk.CTkFont(size = 11, weight = 'bold')).pack(pady = (12, 8))
        self._nav_images = {}
        for key, label in self.NAV:
            self._nav_images[key, False] = ctk.CTkImage(
                light_image = _draw_nav_icon(key, '#475569'),
                dark_image = _draw_nav_icon(key, '#AAB3C2'),
                size = (24, 24))
            self._nav_images[key, True] = ctk.CTkImage(
                light_image = _draw_nav_icon(key, '#FFFFFF'),
                dark_image = _draw_nav_icon(key, '#101010'),
                size = (24, 24))
            button = ctk.CTkButton(
                rail,
                text = label,
                image = self._nav_images[key, False],
                compound = 'top',
                width = 82,
                height = 46,
                corner_radius = 3,
                fg_color = 'transparent',
                hover_color = SURFACE_BTN_HOVER,
                text_color = TEXT_DIM,
                font = ctk.CTkFont(size = 11, weight = 'bold'),
                command = lambda selected = key: self.select_tool(selected))
            button.pack(padx = 6, pady = 2)
            self._nav_buttons[key] = button
        pane = ctk.CTkFrame(self, fg_color = 'transparent')
        pane.grid(row = 0, column = 1, sticky = 'nsew', padx = (2, 5), pady = 5)
        pane.grid_rowconfigure(1, weight = 1)
        pane.grid_columnconfigure(0, weight = 1)
        self._content_title = ctk.CTkLabel(pane,
                                           text = '',
                                           text_color = TEXT,
                                           anchor = 'w',
                                           font = ctk.CTkFont(size = 14, weight = 'bold'))
        self._content_title.grid(row = 0, column = 0, sticky = 'ew', padx = 10, pady = (8, 3))
        self.content = _ToolScroll(
            pane,
            fg_color = 'transparent',
            corner_radius = 0,
            scrollbar_button_color = ACCENT,
            scrollbar_button_hover_color = ACCENT_HOVER)
        # Một pane duy nhất: module nào được chọn thì pack vào đây, cái khác ẩn đi.
        self.content.grid(row = 1, column = 0, sticky = 'nsew')
        self._module_classes = {
            'video': ModuleVideo,
            'subtitle': ModuleCaptionStyle,
            'stt': ModuleStt,
            'srt': ModuleSrtTools,
            'tts': ModuleTts,
            'blur': ModuleBlur,
            'bgm': ModuleBgm,
            'ocr': ModuleOcr,
            'brand': ModuleBrand,
            'trim': ModuleTrim,
            'fx': ModuleBypass,
            'story': ModuleStory,
        }
        self._modules = {}
        self._titles = {key: label for key, label in self.NAV}
        # Mở sẵn Video vì đây là bảng điều khiển người dùng đụng nhiều nhất.
        self.select_tool('video')
        # Các module nặng không khởi tạo hết một lượt (đỡ treo cửa sổ lúc mở app):
        # chỉ tạo cái đang hiển thị, còn lại nạp dần khi idle.
        self._pending_preload = [
            'subtitle',
            'srt',
            'tts',
            'blur',
            'bgm',
            'brand',
            'trim',
            'fx',
            'stt',
            'story',
        ]
        self.after(600, self._idle_preload_step)

    def _get_module(self, key: str, create: bool = True):
        if key in self._modules:
            return self._modules[key]
        if not create:
            return
        cls = self._module_classes.get(key)
        if cls is None:
            return
        try:
            mod = cls(self.content, self.state, self.callbacks)
            mod.set_header_visible(False)
            mod.pack_forget()
            self._modules[key] = mod
            return mod
        except Exception:
            logger.exception('Error initializing module %s', key)

    def has_module(self, key: str) -> bool:
        '''Kiểm tra xem module đã được khởi tạo hay chưa (không tự tạo mới).'''
        return key in self._modules

    def _idle_preload_step(self) -> None:
        '''Nạp dần từng module ngầm khi idle, nghỉ 100ms giữa mỗi module.'''
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        while self._pending_preload:
            next_key = self._pending_preload.pop(0)
            if next_key not in self._modules:
                self._get_module(next_key, create = True)
                self.after(100, self._idle_preload_step)
                return

    @property
    def mod_video(self):
        # 11 property dưới đây chỉ là alias cho gọn khi main window cần đụng
        # trực tiếp tới module đang mở.
        return self._get_module('video')

    @property
    def mod_sub(self):
        return self._get_module('subtitle')

    @property
    def mod_srt(self):
        return self._get_module('srt')

    @property
    def mod_stt(self):
        return self._get_module('stt')

    @property
    def mod_tts(self):
        return self._get_module('tts')

    @property
    def mod_blur(self):
        return self._get_module('blur')

    @property
    def mod_bgm(self):
        return self._get_module('bgm')

    @property
    def mod_ocr(self):
        return self._get_module('ocr')

    @property
    def mod_brand(self):
        return self._get_module('brand')

    @property
    def mod_trim(self):
        return self._get_module('trim')

    @property
    def mod_bypass(self):
        return self._get_module('fx')

    @property
    def mod_story(self):
        return self._get_module('story')

    def select_tool(self, key: str) -> None:
        if key not in self._module_classes:
            return
        old_module = self._modules.get(self._active_key)
        if old_module and hasattr(old_module, 'on_tab_deactivated') and self._active_key != key:
            try:
                old_module.on_tab_deactivated()
            except Exception:
                logger.exception('Error in on_tab_deactivated for %s', self._active_key)
        module = self._get_module(key, create = True)
        for module_key, m in list(self._modules.items()):
            if module_key == key:
                m.pack(fill = 'x', expand = True, padx = 2, pady = (0, 8))
            else:
                m.pack_forget()
        self._active_key = key
        try:
            self.state.active_tool = key
        except Exception:
            pass
        if hasattr(self.content, 'ensure_mouse_wheel'):
            self.content.ensure_mouse_wheel()
        self._content_title.configure(text = self._titles.get(key, ''))
        for button_key, button in self._nav_buttons.items():
            active = button_key == key
            button.configure(
                fg_color = ACCENT if active else 'transparent',
                text_color = ON_ACCENT if active else TEXT_DIM,
                image = self._nav_images[button_key, active])
        # MainWindow / PreviewPanel có thể chưa tồn tại lúc đang dựng giao diện.
        top = self.winfo_toplevel()
        if hasattr(top, 'set_story_mode'):
            try:
                top.set_story_mode(key == 'story')
            except Exception as e:
                logger.debug('MainWindow.set_story_mode error: %s', e)
        preview = getattr(top, 'preview', None)
        if preview and hasattr(preview, 'set_story_mode'):
            try:
                preview.set_story_mode(key == 'story')
            except Exception as e:
                logger.debug('set_story_mode error: %s', e)
        if module and hasattr(module, 'on_tab_activated'):
            try:
                module.on_tab_activated()
            except Exception:
                logger.exception('Error in on_tab_activated for %s', key)
        # Cuộn về đầu khi đổi công cụ, nếu không pane cũ còn giữ nguyên offset.
        def reset_scroll() -> None:
            try:
                canvas = self.content._parent_canvas
                if self.winfo_exists() and canvas.winfo_exists():
                    canvas.yview_moveto(0)
            except Exception:
                pass
        # after_idle để Tk dọn layout xong rồi mới tính lại scroll.
        self.after_idle(reset_scroll)

    def refresh_lists(self) -> None:
        if 'video' in self._modules and self._modules['video']:
            try:
                self._modules['video'].refresh_list()
            except Exception:
                pass
        if 'tts' in self._modules and self._modules['tts']:
            try:
                self._modules['tts'].refresh_reuse_voice()
            except Exception:
                pass
        if 'bgm' in self._modules and self._modules['bgm']:
            try:
                self._modules['bgm'].refresh_list()
            except Exception:
                pass
        if 'srt' in self._modules and self._modules['srt']:
            try:
                self._modules['srt'].refresh_status()
            except Exception:
                pass
        if 'brand' in self._modules and self._modules['brand']:
            try:
                self._modules['brand'].refresh_logo_label()
            except Exception:
                pass
        if 'blur' in self._modules and self._modules['blur']:
            try:
                self._modules['blur']._refresh_region_picker()
            except Exception:
                pass
        if 'trim' in self._modules and self._modules['trim']:
            try:
                self._modules['trim'].refresh_segments()
            except Exception:
                pass
        if 'stt' in self._modules and self._modules['stt']:
            try:
                if hasattr(self._modules['stt'], 'refresh_stt_path'):
                    self._modules['stt'].refresh_stt_path()
            except Exception:
                pass

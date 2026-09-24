"""Bảng màu dùng chung — một bộ cho nền tối, một bộ cho nền sáng.

Mỗi hằng màu là cặp ``(sáng, tối)``. CustomTkinter hiểu thẳng dạng cặp này và
tự đổi màu mọi widget khi gọi :func:`set_appearance` — kể cả widget đã dựng
xong từ trước, nên không phải dựng lại giao diện.

Widget tk thuần và PIL thì không hiểu cặp; những chỗ đó gọi :func:`resolve` để
lấy đúng chuỗi màu của chế độ đang bật, và đăng ký :func:`on_appearance_change`
để tự tô lại khi người dùng chuyển chế độ.

Nền sáng dùng TRẮNG THUẦN #FFFFFF cho mọi mặt phẳng, không dùng trắng ngả xám.
Việc phân tách khối giao cho đường viền; màu xám chỉ xuất hiện ở trạng thái rê
chuột và ô nhấn, vì không có phản hồi thì nút bấm mất cảm giác.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode.appearance_mode_base_class import (
    CTkAppearanceModeBaseClass,
)

logger = logging.getLogger(__name__)

Color = tuple[str, str]

# ---------------------------------------------------------------- accent (cyan)
UI_FONT_FAMILY = 'Segoe UI'
MONO_FONT_FAMILY = 'Consolas'

ACCENT: Color = ('#0891B2', '#00C7D9')
ACCENT_HOVER: Color = ('#0E7490', '#12AAB9')
ACCENT_GOLD: Color = ('#0E7490', '#18C8D8')
ACCENT_TEXT: Color = ('#0E7490', '#00C7D9')
ACCENT_SOFT: Color = ('#E0F2FE', '#72DDE7')
ACCENT_BLUE: Color = ('#0891B2', '#00C7D9')
ACCENT_PINK: Color = ('#0E7490', '#12AAB9')

ON_ACCENT: Color = ('#FFFFFF', '#101010')

# ---------------------------------------------------------------------- surfaces
BG_DARK: Color = ('#F1F5F9', '#1B1B1B')
BG_PANEL: Color = ('#F8FAFC', '#222222')
BG_CARD: Color = ('#FFFFFF', '#2A2A2A')
BG_INPUT: Color = ('#FFFFFF', '#191919')
BG_HEADER: Color = ('#FFFFFF', '#1E1E1E')
BG_ELEVATED: Color = ('#E2E8F0', '#343434')
BG_SUNKEN: Color = ('#E2E8F0', '#151515')

SURFACE_BTN: Color = ('#E2E8F0', '#343434')
SURFACE_BTN_HOVER: Color = ('#CBD5E1', '#454545')
SURFACE_ALT: Color = ('#FFFFFF', '#252525')
SURFACE_ALT_2: Color = ('#F1F5F9', '#262626')
DROPDOWN_BG: Color = ('#FFFFFF', '#202020')
DROPDOWN_HOVER: Color = ('#E2E8F0', '#343434')

# -------------------------------------------------------------------- text
TEXT: Color = ('#0F172A', '#ECECEC')
TEXT_DIM: Color = ('#334155', '#A6A6A6')
TEXT_MUTED: Color = ('#64748B', '#7C7C7C')
TEXT_ON_DARK: Color = ('#0F172A', '#FFFFFF')

# ------------------------------------------------------------------- feedback
SUCCESS: Color = ('#16A34A', '#22C55E')
SUCCESS_HOVER: Color = ('#15803D', '#16A34A')
ON_SUCCESS: Color = ('#FFFFFF', '#FFFFFF')

DANGER: Color = ('#DC2626', '#E95364')
DANGER_HOVER: Color = ('#B91C1C', '#C43A3A')
DANGER_SOFT: Color = ('#FEE2E2', '#5A2A2A')
DANGER_SOFT_HOVER: Color = ('#FECACA', '#7A3535')
ON_DANGER: Color = ('#FFFFFF', '#FFFFFF')
ON_DANGER_SOFT: Color = ('#991B1B', '#FFFFFF')
WARNING: Color = ('#D97706', '#F6C344')
INFO: Color = ('#0891B2', '#00C7D9')

BORDER: Color = ('#CBD5E1', '#3A3A3A')
BORDER_SOFT: Color = ('#E2E8F0', '#303030')

SCROLLBAR: Color = ('#0891B2', '#00C7D9')
SCROLLBAR_HOVER: Color = ('#0E7490', '#12AAB9')

DEFAULT_MODE = 'dark'
_VALID = ('dark', 'oled')
_mode = DEFAULT_MODE
_listeners: list[Callable[[], None]] = []
_appearance_generation = 0
_APPEARANCE_BATCH_SIZE = 32
_APPEARANCE_BATCH_DELAY_MS = 4

ACCENT_PALETTES: dict[str, dict[str, Color]] = {
    'cyan': {
        'ACCENT': ('#0891B2', '#00C7D9'),
        'ACCENT_HOVER': ('#0E7490', '#12AAB9'),
        'ACCENT_GOLD': ('#0E7490', '#18C8D8'),
        'ACCENT_TEXT': ('#0E7490', '#00C7D9'),
        'ACCENT_SOFT': ('#E0F2FE', '#72DDE7'),
        'ON_ACCENT': ('#FFFFFF', '#101010'),
    },
    'blue': {
        'ACCENT': ('#2563EB', '#3B82F6'),
        'ACCENT_HOVER': ('#1D4ED8', '#60A5FA'),
        'ACCENT_GOLD': ('#1D4ED8', '#93C5FD'),
        'ACCENT_TEXT': ('#1D4ED8', '#3B82F6'),
        'ACCENT_SOFT': ('#DBEAFE', '#93C5FD'),
        'ON_ACCENT': ('#FFFFFF', '#FFFFFF'),
    },
    'purple': {
        'ACCENT': ('#7C3AED', '#A855F7'),
        'ACCENT_HOVER': ('#6D28D9', '#C084FC'),
        'ACCENT_GOLD': ('#6D28D9', '#E9D5FF'),
        'ACCENT_TEXT': ('#6D28D9', '#A855F7'),
        'ACCENT_SOFT': ('#F3E8FF', '#D8B4FE'),
        'ON_ACCENT': ('#FFFFFF', '#FFFFFF'),
    },
    'emerald': {
        'ACCENT': ('#059669', '#10B981'),
        'ACCENT_HOVER': ('#047857', '#34D399'),
        'ACCENT_GOLD': ('#047857', '#6EE7B7'),
        'ACCENT_TEXT': ('#047857', '#10B981'),
        'ACCENT_SOFT': ('#D1FAE5', '#A7F3D0'),
        'ON_ACCENT': ('#FFFFFF', '#101010'),
    },
    'amber': {
        'ACCENT': ('#D97706', '#F59E0B'),
        'ACCENT_HOVER': ('#B45309', '#FBBF24'),
        'ACCENT_GOLD': ('#B45309', '#FDE68A'),
        'ACCENT_TEXT': ('#B45309', '#F59E0B'),
        'ACCENT_SOFT': ('#FEF3C7', '#FDE68A'),
        'ON_ACCENT': ('#FFFFFF', '#101010'),
    },
    'rose': {
        'ACCENT': ('#E11D48', '#F43F5E'),
        'ACCENT_HOVER': ('#BE123C', '#FB7185'),
        'ACCENT_GOLD': ('#BE123C', '#FECDD3'),
        'ACCENT_TEXT': ('#BE123C', '#F43F5E'),
        'ACCENT_SOFT': ('#FFE4E6', '#FDA4AF'),
        'ON_ACCENT': ('#FFFFFF', '#FFFFFF'),
    },
}

_current_accent_name = 'cyan'

_ACCENT_TUPLES = {pal['ACCENT'] for pal in ACCENT_PALETTES.values()}
_ACCENT_HOVER_TUPLES = {pal['ACCENT_HOVER'] for pal in ACCENT_PALETTES.values()}
_ACCENT_TEXT_TUPLES = {pal['ACCENT_TEXT'] for pal in ACCENT_PALETTES.values()}
_ACCENT_GOLD_TUPLES = {pal['ACCENT_GOLD'] for pal in ACCENT_PALETTES.values()}
_ACCENT_SOFT_TUPLES = {pal['ACCENT_SOFT'] for pal in ACCENT_PALETTES.values()}
_ON_ACCENT_TUPLES = {pal.get('ON_ACCENT', ('#FFFFFF', '#101010')) for pal in ACCENT_PALETTES.values()}

_ACCENT_HEXES = {c.upper() for pal in ACCENT_PALETTES.values() for c in pal['ACCENT']}
_ACCENT_HOVER_HEXES = {c.upper() for pal in ACCENT_PALETTES.values() for c in pal['ACCENT_HOVER']}
_ACCENT_TEXT_HEXES = {c.upper() for pal in ACCENT_PALETTES.values() for c in pal['ACCENT_TEXT']}


def current_accent_name() -> str:
    """Tên bộ màu nhấn đang bật ('cyan', 'blue', 'purple', 'emerald', 'amber', 'rose')."""
    return _current_accent_name


def current_mode() -> str:
    """'dark', 'light' hoặc 'oled' — chế độ đang bật."""
    return _mode


def is_light() -> bool:
    return _mode == 'light'


def is_oled() -> bool:
    return _mode == 'oled'


_OLED_MAP: dict[Color, str] = {
    BG_DARK: '#000000',
    BG_PANEL: '#080808',
    BG_CARD: '#121212',
    BG_INPUT: '#050505',
    BG_HEADER: '#080808',
    BG_ELEVATED: '#1A1A1A',
    BG_SUNKEN: '#040404',
    SURFACE_BTN: '#1A1A1A',
    SURFACE_BTN_HOVER: '#262626',
    SURFACE_ALT: '#0D0D0D',
    SURFACE_ALT_2: '#141414',
    DROPDOWN_BG: '#101010',
    DROPDOWN_HOVER: '#1E1E1E',
    BORDER: '#222222',
    BORDER_SOFT: '#181818',
}


def resolve(color) -> str:
    """Lấy chuỗi màu thật cho chế độ hiện tại.

    Dùng cho widget tk thuần, PIL, ttk — những nơi không hiểu cặp màu.
    Nhận sẵn cả chuỗi đơn để gọi được với màu ghi thẳng mà không phải kiểm tra.
    Tự động ánh xạ mọi tuple Accent cũ sang Accent của palette đang chọn.
    """
    if isinstance(color, (tuple, list)):
        tpl = tuple(color)
        if tpl in _ACCENT_TUPLES:
            color = ACCENT
        elif tpl in _ACCENT_HOVER_TUPLES:
            color = ACCENT_HOVER
        elif tpl in _ACCENT_TEXT_TUPLES:
            color = ACCENT_TEXT
        elif tpl in _ACCENT_GOLD_TUPLES:
            color = ACCENT_GOLD
        elif tpl in _ACCENT_SOFT_TUPLES:
            color = ACCENT_SOFT
        elif tpl in _ON_ACCENT_TUPLES:
            color = ON_ACCENT
        if _mode == 'oled':
            if tpl in _OLED_MAP:
                return _OLED_MAP[tpl]
            return color[1]
        return color[1]
    return color


def _enhanced_apply_appearance_mode(self, color):
    if color == 'transparent' or color is None:
        return color

    if isinstance(color, (tuple, list)):
        tpl = tuple(color)
        if tpl in _ACCENT_TUPLES:
            return resolve(ACCENT)
        elif tpl in _ACCENT_HOVER_TUPLES:
            return resolve(ACCENT_HOVER)
        elif tpl in _ACCENT_TEXT_TUPLES:
            return resolve(ACCENT_TEXT)
        elif tpl in _ACCENT_GOLD_TUPLES:
            return resolve(ACCENT_GOLD)
        elif tpl in _ACCENT_SOFT_TUPLES:
            return resolve(ACCENT_SOFT)
        elif tpl in _ON_ACCENT_TUPLES:
            return resolve(ON_ACCENT)
        return resolve(tpl)

    if isinstance(color, str):
        c_upper = color.upper()
        if c_upper in _ACCENT_HEXES:
            return resolve(ACCENT)
        elif c_upper in _ACCENT_HOVER_HEXES:
            return resolve(ACCENT_HOVER)
        elif c_upper in _ACCENT_TEXT_HEXES:
            return resolve(ACCENT_TEXT)
        return color

    return color


CTkAppearanceModeBaseClass._apply_appearance_mode = _enhanced_apply_appearance_mode


def _update_theme_manager_accents() -> None:
    """Cập nhật ThemeManager để các widget tạo mới dùng ngay accent mới."""
    try:
        t = ctk.ThemeManager.theme
        if not isinstance(t, dict):
            return
        accent_list = list(ACCENT)
        hover_list = list(ACCENT_HOVER)

        for w_name in ('CTkButton', 'CTkCheckBox', 'CTkRadioButton', 'CTkOptionMenu'):
            if w_name in t and isinstance(t[w_name], dict):
                t[w_name]['fg_color'] = accent_list
                if 'hover_color' in t[w_name]:
                    t[w_name]['hover_color'] = hover_list

        if 'CTkSlider' in t and isinstance(t['CTkSlider'], dict):
            t['CTkSlider']['button_color'] = accent_list
            t['CTkSlider']['progress_color'] = accent_list
            t['CTkSlider']['button_hover_color'] = hover_list

        if 'CTkProgressBar' in t and isinstance(t['CTkProgressBar'], dict):
            t['CTkProgressBar']['progress_color'] = accent_list

        if 'CTkSegmentedButton' in t and isinstance(t['CTkSegmentedButton'], dict):
            t['CTkSegmentedButton']['selected_color'] = accent_list
            t['CTkSegmentedButton']['selected_hover_color'] = hover_list

        if 'CTkSwitch' in t and isinstance(t['CTkSwitch'], dict):
            t['CTkSwitch']['progress_color'] = accent_list
    except Exception as exc:
        logger.debug('Lỗi cập nhật ThemeManager: %s', exc)


def _update_widget_tree_accents(widget) -> None:
    """Duyệt sâu cây widget và đồng bộ cấu hình màu sắc trực quan."""
    stack = [widget]
    while stack:
        cur = stack.pop()
        try:
            stack.extend(cur.winfo_children())
        except Exception:
            pass

        try:
            if isinstance(cur, ctk.CTkButton):
                cur_fg = getattr(cur, '_fg_color', None)
                cur_fg_tpl = tuple(cur_fg) if isinstance(cur_fg, (tuple, list)) else None
                if cur_fg_tpl in _ACCENT_TUPLES or (isinstance(cur_fg, str) and cur_fg.upper() in _ACCENT_HEXES):
                    cur.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT)
            elif isinstance(cur, ctk.CTkSlider):
                cur_prog = getattr(cur, '_progress_color', None)
                cur_prog_tpl = tuple(cur_prog) if isinstance(cur_prog, (tuple, list)) else None
                if cur_prog_tpl in _ACCENT_TUPLES or (isinstance(cur_prog, str) and cur_prog.upper() in _ACCENT_HEXES):
                    cur.configure(progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER)
            elif isinstance(cur, ctk.CTkCheckBox):
                cur_fg = getattr(cur, '_fg_color', None)
                cur_fg_tpl = tuple(cur_fg) if isinstance(cur_fg, (tuple, list)) else None
                if cur_fg_tpl in _ACCENT_TUPLES or (isinstance(cur_fg, str) and cur_fg.upper() in _ACCENT_HEXES):
                    cur.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER)
            elif isinstance(cur, ctk.CTkSegmentedButton):
                cur_sel = getattr(cur, '_selected_color', None)
                cur_sel_tpl = tuple(cur_sel) if isinstance(cur_sel, (tuple, list)) else None
                if cur_sel_tpl in _ACCENT_TUPLES or (isinstance(cur_sel, str) and cur_sel.upper() in _ACCENT_HEXES):
                    cur.configure(selected_color=ACCENT, selected_hover_color=ACCENT_HOVER)
            elif isinstance(cur, ctk.CTkSwitch):
                cur_prog = getattr(cur, '_progress_color', None)
                cur_prog_tpl = tuple(cur_prog) if isinstance(cur_prog, (tuple, list)) else None
                if cur_prog_tpl in _ACCENT_TUPLES or (isinstance(cur_prog, str) and cur_prog.upper() in _ACCENT_HEXES):
                    cur.configure(progress_color=ACCENT)
            elif isinstance(cur, ctk.CTkLabel):
                cur_txt = getattr(cur, '_text_color', None)
                cur_txt_tpl = tuple(cur_txt) if isinstance(cur_txt, (tuple, list)) else None
                if cur_txt_tpl in _ACCENT_TEXT_TUPLES or (isinstance(cur_txt, str) and cur_txt.upper() in _ACCENT_TEXT_HEXES):
                    cur.configure(text_color=ACCENT_TEXT)
            elif isinstance(cur, (ctk.CTk, ctk.CTkToplevel)):
                cur.configure(fg_color=resolve(BG_DARK))
        except Exception:
            continue


def set_accent_palette(name: str) -> None:
    """Đổi màu chủ đạo toàn ứng dụng và thông báo cho mọi widget vẽ lại."""
    global _current_accent_name, ACCENT, ACCENT_HOVER, ACCENT_GOLD, ACCENT_TEXT, ACCENT_SOFT, ON_ACCENT
    palette_key = (name or 'cyan').strip().lower()
    if palette_key not in ACCENT_PALETTES:
        palette_key = 'cyan'
    if palette_key == _current_accent_name:
        return
    _current_accent_name = palette_key
    pal = ACCENT_PALETTES[palette_key]
    ACCENT = pal['ACCENT']
    ACCENT_HOVER = pal['ACCENT_HOVER']
    ACCENT_GOLD = pal['ACCENT_GOLD']
    ACCENT_TEXT = pal['ACCENT_TEXT']
    ACCENT_SOFT = pal['ACCENT_SOFT']
    if 'ON_ACCENT' in pal:
        ON_ACCENT = pal['ON_ACCENT']
    _update_theme_manager_accents()
    try:
        from customtkinter import AppearanceModeTracker
        roots = list(AppearanceModeTracker.app_list)
        for r in roots:
            if not _tk_widget_exists(r):
                continue
            _update_widget_tree_accents(r)
    except Exception as exc:
        logger.debug('Lỗi cập nhật widget cho palette: %s', exc)
    _notify_appearance_listeners()


def on_appearance_change(callback: Callable[[], None]) -> None:
    """Đăng ký hàm tô lại cho widget tk thuần khi đổi chế độ.

    Hàm nào ném lỗi (thường vì widget đã bị hủy) sẽ bị gỡ khỏi danh sách, nếu
    không mỗi cửa sổ mở rồi đóng lại để lại một callback chết.
    """
    _listeners.append(callback)


def set_appearance(mode: str) -> str:
    """Chuyển chế độ mà không khóa UI khi ứng dụng đã có nhiều widget.

    CustomTkinter mặc định tô lại toàn bộ widget trong một vòng lặp đồng bộ.
    Với giao diện chính + cửa sổ Cài đặt, thao tác đó có thể chiếm hàng trăm
    mili giây trên UI thread. Khi đã có Tk root, chia danh sách callback thành
    các lô nhỏ để Windows vẫn vẽ khung và nhận sự kiện giữa các lô.
    """
    global _mode, _appearance_generation
    previous_mode = _mode
    mode = (mode or '').strip().lower()
    if mode not in _VALID:
        mode = DEFAULT_MODE
    _mode = mode

    try:
        from customtkinter import AppearanceModeTracker

        target = 1
        AppearanceModeTracker.appearance_mode_set_by = 'user'

        if AppearanceModeTracker.appearance_mode == target and previous_mode == mode:
            return _mode
        AppearanceModeTracker.appearance_mode = target
        callbacks = list(AppearanceModeTracker.callback_list)
        roots = list(AppearanceModeTracker.app_list)
        root = next(
            (item for item in roots if _tk_widget_exists(item)),
            None,
        )

        if root is None:
            AppearanceModeTracker.update_callbacks()
            _notify_appearance_listeners()
            return _mode

        _appearance_generation += 1
        generation = _appearance_generation
        appearance_label = 'Dark'

        def apply_batch(start: int = 0) -> None:
            if generation != _appearance_generation or not _tk_widget_exists(root):
                return
            end = min(len(callbacks), start + _APPEARANCE_BATCH_SIZE)
            for callback in callbacks[start:end]:
                try:
                    callback(appearance_label)
                except Exception:
                    pass
            if end < len(callbacks):
                root.after(_APPEARANCE_BATCH_DELAY_MS, lambda: apply_batch(end))
                return
            for r in roots:
                if not _tk_widget_exists(r):
                    continue
                _update_widget_tree_accents(r)
            _notify_appearance_listeners(root=root)

        root.after_idle(apply_batch)
    except Exception:
        try:
            AppearanceModeTracker.update_callbacks()
        except (NameError, AttributeError):
            ctk.set_appearance_mode(mode)
        _notify_appearance_listeners()
    return _mode


def _tk_widget_exists(widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def _notify_appearance_listeners(*, root=None) -> None:
    """Tô widget Tk/ttk; mỗi listener một nhịp để dialog lớn không khóa UI."""
    pending = list(_listeners)

    def run(index: int = 0) -> None:
        if index >= len(pending):
            return
        callback = pending[index]
        try:
            callback()
        except Exception:
            try:
                _listeners.remove(callback)
            except ValueError:
                pass
        if index + 1 < len(pending):
            if root is not None and _tk_widget_exists(root):
                root.after(1, lambda: run(index + 1))
                return
            run(index + 1)
            return

    run()


def apply_global_theme(mode: str | None = None) -> None:
    """Áp dụng theme toàn cục cho CustomTkinter (mặc định luôn luôn là nền tối Dark mode)."""
    target_mode = mode if mode and mode in _VALID else DEFAULT_MODE
    ctk.set_default_color_theme('dark-blue')
    ctk.set_appearance_mode('dark')

    font_theme = ctk.ThemeManager.theme.get('CTkFont')
    if isinstance(font_theme, dict):
        font_theme['family'] = UI_FONT_FAMILY

    for widget in ('CTkButton', 'CTkLabel', 'CTkCheckBox', 'CTkRadioButton', 'CTkSwitch', 'CTkOptionMenu', 'CTkComboBox', 'CTkEntry', 'CTkSegmentedButton', 'CTkTextbox'):
        entry = ctk.ThemeManager.theme.get(widget)
        if isinstance(entry, dict) and 'text_color' in entry:
            entry['text_color'] = list(TEXT)
    set_appearance(target_mode)


def section_title_kwargs() -> dict:
    return {
        'text_color': ON_ACCENT,
        'fg_color': ACCENT,
        'corner_radius': 8,
        'font': ctk.CTkFont(family=UI_FONT_FAMILY, size=13, weight='bold'),
        'anchor': 'w',
        'height': 30,
    }


def accent_button_kwargs() -> dict:
    return {
        'fg_color': ACCENT,
        'hover_color': ACCENT_HOVER,
        'text_color': ON_ACCENT,
        'font': ctk.CTkFont(family=UI_FONT_FAMILY, size=13, weight='bold'),
        'corner_radius': 10,
    }


def secondary_button_kwargs() -> dict:
    return {
        'fg_color': SURFACE_BTN,
        'hover_color': SURFACE_BTN_HOVER,
        'text_color': TEXT,
        'border_width': 1,
        'border_color': BORDER,
        'font': ctk.CTkFont(family=UI_FONT_FAMILY, size=12),
        'corner_radius': 10,
    }


def gold_button_kwargs() -> dict:
    """Nút phụ tông xanh."""
    return {
        'fg_color': ACCENT_BLUE,
        'hover_color': ACCENT_PINK,
        'text_color': ON_ACCENT,
        'font': ctk.CTkFont(family=UI_FONT_FAMILY, size=12, weight='bold'),
        'corner_radius': 10,
    }

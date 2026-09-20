# Source Generated with Decompyle++
# File: story_tour.pyc (Python 3.12)

'''Hệ thống hướng dẫn tương tác từng bước (Interactive Guided Tour) cho Mumu Studio Pro.

Tự động làm nổi bật (highlight) từng khối chức năng trên màn hình,
hiển thị thẻ chú thích ngắn gọn, súc tích và cung cấp các nút
Tiếp tục (Next), Quay lại (Back), Bỏ qua (Skip) chuẩn mực như các ứng dụng chuyên nghiệp.
'''
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BORDER, ON_ACCENT, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED
logger = logging.getLogger(__name__)
HIGHLIGHT_BORDER = ('#D97706', '#F59E0B')
HIGHLIGHT_BG = ('#FEF3C7', '#2D2415')
HIGHLIGHT_BADGE_BG = ('#FDE68A', '#451A03')
HIGHLIGHT_BADGE_TXT = ('#92400E', '#FCD34D')
TourStep = <NODE:12>()

class InteractiveTourGuide:
    '''Bộ điều hướng và hiển thị tour hướng dẫn từng bước trực quan với hiệu ứng Spotlight.'''
    
    def __init__(self = None, parent = None, steps = None, *, on_finish):
        self.parent = parent
    # WARNING: Decompyle incomplete

    
    def start(self = None):
        '''Bắt đầu chạy tour hướng dẫn từ bước đầu tiên.'''
        if not self.steps:
            return None
        self.current_step_idx = 0
        top = self.parent.winfo_toplevel()
        
        try:
            self._parent_configure_cid = top.bind('<Configure>', self._on_parent_configure, add = '+')
            self._show_step(0)
            return None
        except Exception:
            self._parent_configure_cid = None
            continue


    
    def _on_parent_configure(self = None, event = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _sync_positions(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _show_step(self = None, idx = None):
        if idx < 0 or idx >= len(self.steps):
            self.stop()
            return None
        self.current_step_idx = idx
        step = self.steps[idx]
        self._clear_highlight()
        self._apply_highlight(step.target_widget)
        self._render_callout_card(step)

    
    def _apply_highlight(self = None, widget = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _render_spotlight_overlay(self = None, widget = None):
        import tkinter as tk
    # WARNING: Decompyle incomplete

    
    def _clear_highlight(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _ensure_visible(self = None, widget = None):
        '''Cố gắng cuộn container cha nếu widget bị khuất.'''
        
        try:
            widget.update_idletasks()
            curr = widget
            if curr:
                parent = getattr(curr, 'master', None)
                if parent and hasattr(parent, '_parent_canvas'):
                    canvas = parent._parent_canvas
                    wy = widget.winfo_y()
                    if not canvas.winfo_height():
                        canvas.winfo_height()
                    ch = 1
                    if not parent.winfo_height():
                        parent.winfo_height()
                    total_h = 1
                    if total_h > ch:
                        fraction = max(0, min(1, (wy - 30) / float(total_h)))
                        canvas.yview_moveto(fraction)
                    return None
                    
                    try:
                        curr = parent
                        if curr:
                            continue
                        return None
                        return None
                    except Exception:
                        return None



    
    def _render_callout_card(self = None, step = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _position_card(self = None, target_widget = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _on_next(self = None):
        if self.current_step_idx + 1 < len(self.steps):
            self._show_step(self.current_step_idx + 1)
            return None
        self.stop()

    
    def _on_prev(self = None):
        if self.current_step_idx > 0:
            self._show_step(self.current_step_idx - 1)
            return None

    
    def stop(self = None):
        '''Dừng tour hướng dẫn, khôi phục màu sắc các widget.'''
        self._clear_highlight()
    # WARNING: Decompyle incomplete



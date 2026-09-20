# Source Generated with Decompyle++
# File: story_subtitle_dialog.pyc (Python 3.12)

'''Hộp thoại tùy chỉnh phụ đề chuyên biệt cho module Dựng Truyện (AI Storytelling).

Hoàn toàn độc lập với tab Reup Video. Lưu trực tiếp vào story_project.json (sub_options),
cập nhật live preview thời gian thực và tự động áp dụng khi xuất video thành phẩm.
'''
from __future__ import annotations
import logging
from typing import Any, Callable
from tkinter import colorchooser
import customtkinter as ctk
from app.services.story_engine import StoryProject
logger = logging.getLogger(__name__)
BG_DARK = '#0B0F19'
BG_CARD = '#151D2C'
SURFACE_ALT = '#1C273C'
SURFACE_BTN = '#24324D'
SURFACE_BTN_HOVER = '#2D3F60'
BORDER = '#2A3B58'
TEXT = '#F8FAFC'
TEXT_DIM = '#94A3B8'
ACCENT = '#00F0FF'
ACCENT_HOVER = '#00C8D6'
ACCENT_TEXT = '#00F0FF'
ON_ACCENT = '#05101A'
SUCCESS = '#10B981'
POPULAR_FONTS = [
    'Arial',
    'Segoe UI',
    'Roboto',
    'Montserrat',
    'Playfair Display',
    'Times New Roman',
    'Tahoma',
    'Verdana',
    'Calibri',
    'Georgia',
    'UTM Bebas']
POPULAR_COLORS = [
    ('#FFFFFF', 'Trắng'),
    ('#FFD700', 'Vàng Kim'),
    ('#FFF59D', 'Vàng Nhạt'),
    ('#00F0FF', 'Cyan'),
    ('#00FFB2', 'Mint'),
    ('#FFA500', 'Cam'),
    ('#FF7A59', 'Hồng Cam')]
SUBTITLE_STYLE_OPTIONS = [
    'TikTok Bouncing Word (Nảy từng từ + Đổi màu Neon)',
    'TikTok Glow Highlight (Phát sáng Neon từng từ)',
    'Karaoke Wave (Đổi màu mượt mà)',
    'Phụ đề tĩnh chuẩn điện ảnh (Static)']
HIGHLIGHT_COLORS = [
    ('#FFE600', 'Vàng Neon'),
    ('#00F0FF', 'Cyan Neon'),
    ('#00FF88', 'Mint Neon'),
    ('#FFA500', 'Cam Rực'),
    ('#FF3399', 'Hồng Neon'),
    ('#FFFFFF', 'Trắng')]
CHUNK_MODE_OPTIONS = [
    'TikTok Ngắn (3 - 5 từ / cụm - Khuyên dùng Shorts/Reels)',
    'Đầy đủ câu thoại kịch bản']
EFFECT_OPTIONS = [
    'Viền đen (Khuyên dùng)',
    'Bóng đổ điện ảnh (Shadow)',
    'Viền đậm',
    'Bóng đổ (Shadow)',
    'Phát sáng (Glow)',
    'Neon xanh',
    'Neon hồng',
    'Hộp nền mờ (Box)',
    'Không có',
    'Không viền (Chữ trơn)']

class StorySubtitleDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


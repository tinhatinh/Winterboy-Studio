# Source Generated with Decompyle++
# File: fluent_icons.pyc (Python 3.12)

__doc__ = 'Icon Fluent sắc nét cho CustomTkinter, render từ font icon có sẵn của Windows.\n\nKhông dùng emoji vì hình dáng/kích thước thay đổi theo máy. Segoe Fluent Icons\nlà bộ icon giao diện chuẩn của Windows; ảnh được raster ở 4x rồi thu nhỏ để nét\nở cả DPI 100–150%. Nếu font Fluent không tồn tại, helper tự vẽ fallback đơn giản.\n'
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
# WARNING: Decompyle incomplete

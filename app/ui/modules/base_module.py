# Source Generated with Decompyle++
# File: base_module.pyc (Python 3.12)

'''Base helpers cho các module panel.

Bộ primitive bên dưới thay cho cách cũ là ``pack(side="left")`` với chiều rộng
cứng cho từng ô. Cách cũ khiến hàng dài hơn panel bị cắt cụt (mất ô «Cao», mất
chữ «GPU», mất ô «Trễ (s)»…). Ở đây mọi hàng dùng ``grid`` với:

* cột 0 = nhãn, bề rộng CỐ ĐỊNH và giống nhau ở mọi module → thẳng hàng;
* cột 1 = widget, ``weight=1`` + ``sticky="ew"`` → co giãn theo panel, không tràn;
* chữ gợi ý tự xuống dòng theo bề rộng thật (``wraplength`` bám sự kiện resize).

Giá trị dài (tên font, tên giọng, model) dùng :meth:`stack` — nhãn nằm trên,
widget chiếm trọn bề ngang bên dưới. Panel thừa rất nhiều chiều dọc nên xếp dọc
là đổi chỗ trống lấy chỗ bị cắt.
'''
from __future__ import annotations
from typing import Any, Callable, Iterable, Sequence
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BORDER, TEXT, TEXT_DIM, section_title_kwargs
LABEL_W = 92
NUM_W = 62
UNIT_W = 18
DEFAULT_WRAP = 400

def _shrink(widget = None):
    '''Hạ ``width`` yêu cầu của widget CTk xuống tối thiểu.

    CustomTkinter giữ nguyên ``width`` mặc định (slider 200, entry/button 140,
    option menu 140) kể cả khi ô grid dùng ``sticky="ew"`` — widget không co lại
    mà bị xén. Đặt width=1 để ô grid/pack quyết định bề rộng thật.
    '''
    
    try:
        widget.configure(width = 1)
        return None
    except Exception:
        return None



def _apply_wrap(label = None, pixels = None):
    '''Đặt ``wraplength`` theo pixel THẬT trên màn hình.

    Hai cái bẫy ở đây:

    1. CustomTkinter NHÂN giá trị này với hệ số DPI scaling trước khi đưa xuống
       Tk, nên phải chia ngược lại — không thì ở màn hình scale 125% chữ vẫn
       tràn đúng 25% ra ngoài panel.
    2. ``cget("wraplength")`` đọc về giá trị ĐÃ nhân scaling, khác với giá trị
       vừa ghi vào. So sánh hai thứ đó thì điều kiện chặn không bao giờ khớp →
       mỗi lần đặt lại kích hoạt <Configure> → đệ quy vô hạn, UI treo cứng.
       Vì vậy giá trị đã áp được lưu riêng trên chính widget.
    '''
    
    try:
        scaling = float(ctk.ScalingTracker.get_widget_scaling(label)) or 1.0
    except Exception:
        scaling = 1.0
    target = max(100, int(pixels / scaling))
    if abs(int(getattr(label, '_mumu_wrap', -1)) - target) <= 6:
        return None
    label._mumu_wrap = target

    try:
        label.configure(wraplength = target)
    except Exception:
        return None




class BaseModule(ctk.CTkFrame):
    pass
# WARNING: Decompyle incomplete


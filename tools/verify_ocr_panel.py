# -*- coding: utf-8 -*-
'''Kiểm tra bảng điều khiển OCR trong BẢN ĐÃ CÀI ĐẶT, không cần mở cửa sổ.

Chạy thật chính ``ControlPanel`` của app (root ``withdraw()`` nên không loé màn
hình), dựng thẻ OCR rồi đi tìm widget. Làm vậy vì đọc code hay ``import`` suôn sẽ
không phát hiện được mấy lỗi chỉ nổ lúc tạo widget — ví dụ đặt tên hàm dựng UI là
``_setup``: tkinter có ``Widget._setup(master, cnf)`` nội bộ mà ``Frame.__init__``
gọi lại, ghi đè trúng là panel không dựng được nhưng import vẫn im lặng.

    python tools/verify_ocr_panel.py            # kiểm tra bản đã cài
    python tools/verify_ocr_panel.py --source   # kiểm tra source trong repo
'''
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = Path(r'C:\Users\Administrator\MumuStudioPro\{app}')

# chữ phải hiện ra trên panel OCR; thiếu cái nào là dựng UI hỏng
EXPECT = ('Video cần OCR', 'Chọn video', 'Ngôn ngữ', 'Dùng GPU (CUDA)', 'Trễ (s)',
          'Xem trước & chọn vùng', 'Giây', 'Nạp preview', 'Nạp lại', 'Xoá vùng',
          'Chỉ OCR vùng đã khoanh',
          'Chạy OCR', 'Dừng', 'Lưu .srt…', 'Mở thư mục', 'Kết quả', 'File .srt')

# chỉ những hàm không mở hộp thoại / không đụng file system
SAFE_CALLS = ('sync_from_state', 'refresh_engine', 'stop', 'clear_region', 'current_crop')


def _text_tree(widget) -> list[str]:
    out: list[str] = []

    def walk(w):
        for c in w.winfo_children():
            try:
                t = c.cget('text')
            except Exception:
                t = ''
            if t:
                out.append(str(t))
            walk(c)

    walk(widget)
    return out


def _pump_until(mod, predicate, seconds=25.0, step=0.05):
    """Chạy vòng `update()` thật để luồng chính hút hàng đợi _pump như khi mở app."""
    import time
    deadline = time.time() + seconds
    while time.time() < deadline:
        mod._pump()
        mod.update()
        if predicate():
            return True
        time.sleep(step)
    return predicate()


class _Evt:
    """Thay cho tkinter.Event khi mô phỏng kéo chuột."""

    def __init__(self, x, y):
        self.x, self.y = x, y


def _check_drag(mod, root) -> list[str]:
    """Kéo chuột giả lập trên canvas và đòi ra đúng crop pixel gốc."""
    fails = []
    root.update()
    mod._photo = 'x'                     # chỉ cần khác None để handler không bỏ qua
    mod._shown = (216, 384)              # ảnh preview hiển thị 1/5 video 1080x1920
    mod._src = (1080, 1920)
    mod._drag_start(_Evt(0, 320))
    mod._drag_motion(_Evt(108, 360))
    mod._drag_end(_Evt(216, 360))
    root.update()
    if mod.region != (0, 1600, 1080, 200):
        fails.append(f'kéo chuột ra crop sai: {mod.region}')
    if mod.current_crop() is None:
        fails.append('đã kéo vùng nhưng current_crop() trả None (sẽ OCR cả khung hình)')
    if mod._rect_id is None:
        fails.append('không có hình chữ nhật nào được vẽ lên canvas')
    else:
        coords = mod.canvas.coords(mod._rect_id)
        if [round(c) for c in coords] != [0, 320, 216, 360]:
            fails.append(f'ô vẽ trên canvas lệch so với chỗ đã kéo: {coords}')
    mod.var_use_region.set(False)
    if mod.current_crop() is not None:
        fails.append('tắt "chỉ OCR vùng" rồi mà current_crop() vẫn trả crop')
    mod.var_use_region.set(True)
    if mod.current_crop() != (0, 1600, 1080, 200):
        fails.append(f'4 ô số không theo kéo chuột: {[v.get() for v in mod.vars_crop]}')
    # tay nhập không cần kéo vẫn phải dùng được
    for var, value in zip(mod.vars_crop, ('100', '1700', '900', '120')):
        var.set(value)
    mod._crop_from_fields()
    if mod.current_crop() != (100, 1700, 900, 120):
        fails.append(f'nhập số trực tiếp không ăn khớp: {mod.current_crop()}')
    for var in mod.vars_crop:
        var.set('rác')
    if mod.current_crop() is not None:
        fails.append('ô số rác mà vẫn trả về vùng')
    mod.clear_region()
    if mod.region is not None or mod._rect_id is not None:
        fails.append('Xoá vùng không sạch')
    if any(v.get() for v in mod.vars_crop):
        fails.append('Xoá vùng nhưng 4 ô số còn nguyên')
    return fails


def _check_real_preview(mod, root, video) -> list[str]:
    """Đường đi thật: ffmpeg xuất frame -> PIL -> canvas -> kéo vùng."""
    from pathlib import Path

    fails = []
    path = Path(video)
    if not path.is_file():
        return [f'không có video test: {path}']
    mod.reset_preview()                      # _check_drag vừa để lại _photo/_shown giả
    mod.var_video.set(str(path))
    mod.var_t.set('3')
    mod.load_frame()
    if not _pump_until(mod, lambda: mod._photo is not None and mod._shown[0] > 0):
        return ['mất khung hình: load_frame() không ảnh nào sau 25s (thiếu ffmpeg?)']
    dw, dh = mod._shown
    sw, sh = mod._src
    if not (sw and sh):
        fails.append('probe_video_size không trả về kích thước gốc')
    if (dw, dh) == (216, 384):
        fails.append('kích thước preview y hệt giá trị giả của _check_drag -> ảnh thật chưa vẽ')
    root.update()
    real = [i for i in mod.canvas.find_all() if str(mod.canvas.type(i)) == 'image']
    if not real:
        fails.append(f'canvas không có item ảnh nào (preview {mod._shown})')
    print(f'  preview {mod._shown}px của video {mod._src}px, jpeg {mod._frame_path.name}')
    # headless thì canvas chưa map nên winfo_width()=1 (120px là sàn). Mở thật trong
    # app nó ăn hết bề rộng panel, nên phải kiểm riêng cả trường hợp 330px.
    big = mod._open_scaled(mod._frame_path, 330)
    if not big:
        fails.append('co ảnh 330px thất bại')
    else:
        pw, ph = big[1]
        sw, sh = mod._src
        if abs(pw / ph - sw / sh) > 0.05:
            fails.append(f'ảnh 330px sai tỉ lệ video: {pw}x{ph} vs {sw}x{sh}')
        if not (pw <= 330 and ph <= 300):
            fails.append(f'ảnh tràn ô canvas: {pw}x{ph}')
        print(f'  trong app thật preview sẽ là {pw}x{ph}px')
    mod._drag_start(_Evt(2, dh - 40))
    mod._drag_motion(_Evt(dw // 2, dh - 20))
    mod._drag_end(_Evt(dw - 2, dh - 4))
    rect = mod.canvas.coords(mod._rect_id) if mod._rect_id else None
    if rect and [round(c) for c in rect] != [2, dh - 40, dw - 2, dh - 4]:
        fails.append(f'ô vẽ không khớp điểm thả chuột: {rect}')
    if mod.region:
        x, y, cw, ch = mod.region
        if not (0 <= x and x + cw <= sw and 0 <= y and y + ch <= sh):
            fails.append(f'crop {mod.region} tràn ra ngoài video {mod._src}')
        print(f'  kéo {dw}x{dh}px -> crop gốc {mod.region}')
    else:
        fails.append(f'kéo vùng trên ảnh thật không ra crop ({mod.region})')
    return fails


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', action='store_true', help='dùng source repo thay vì bản đã cài')
    ap.add_argument('--video', help='video thật để test luôn bước nạp khung hình')
    args = ap.parse_args(argv)

    root_dir = REPO if args.source else APP / '_internal'
    if not args.source and not root_dir.is_dir():
        print(f'không thấy app ở {APP}')
        return 1
    sys.path.insert(0, str(root_dir))

    import customtkinter as ctk
    import app.ui.control_panel as cp_mod
    from app.core.state import AppState
    from app.ui.control_panel import ControlPanel
    from app.ui.modules.module_ocr import ModuleOcr

    print(f'control_panel: {cp_mod.__file__}')
    print(f'module_ocr   : {sys.modules["app.ui.modules.module_ocr"].__file__}')

    tk_root = ctk.CTk()
    tk_root.withdraw()                      # không hiện cửa sổ, không đụng màn hình người dùng
    # AppState() trần thì mọi CTkVar vẫn là None — app thật luôn đi qua create().
    state = AppState.create(tk_root)
    callbacks = {name: (lambda *a: None) for name in
                 ('add_videos', 'clear_videos', 'start', 'stop', 'open_output')}
    fails: list[str] = []
    try:
        nav = [title for _key, title in ControlPanel.NAV]
        print(f'NAV: {" ".join(nav)}')
        if 'OCR' not in nav:
            fails.append('thiếu mục OCR trong NAV')

        panel = ControlPanel(tk_root, state, callbacks)
        tk_root.update()

        mod = panel._get_module('ocr')
        tk_root.update()
        if not isinstance(mod, ModuleOcr):
            fails.append(f'không dựng được panel OCR: {mod!r}')
        else:
            texts = _text_tree(mod)
            # BaseModule.section HOA tiêu đề mục nên phải so không phân biệt hoa thường
            joined = '\n'.join(texts).upper()
            missing = [e for e in EXPECT if e.upper() not in joined]
            if missing:
                fails.append('thiếu widget: ' + ', '.join(missing))
            if '_setup' in ModuleOcr.__dict__:
                fails.append('vẫn ghi đè tkinter.Widget._setup')
            print(f'panel OCR: {type(mod).__name__}, {len(texts)} nhãn')
            print('  ' + ' | '.join(dict.fromkeys(texts))[:400])
            for fn in SAFE_CALLS:
                try:
                    getattr(mod, fn)()
                except Exception as exc:            # noqa: BLE001
                    fails.append(f'{fn}() nổ: {type(exc).__name__}: {exc}')

            fails += _check_drag(mod, tk_root)
            if args.video:
                fails += _check_real_preview(mod, tk_root, args.video)

            panel.select_tool('ocr')
            tk_root.update()
            shown = [w for w in panel.content.winfo_children() if w.winfo_ismapped()]
            if not shown:
                fails.append('select_tool("ocr") xong mà không có panel nào được map')
    except Exception:                                # noqa: BLE001
        traceback.print_exc()
        fails.append('ControlPanel dựng không xong')
    finally:
        tk_root.destroy()

    if fails:
        print('\nFAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('\nOK — thẻ OCR dựng được thật, đủ widget, các hàm phụ không nổ.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
'''Kiểm tra thẻ OCR trong BẢN ĐÃ CÀI ĐẶT mà không cần mở cửa sổ.

Dựng thật ``ControlPanel`` của app (root ``withdraw()`` nên không loé màn hình),
mở thẻ OCR rồi đi tìm widget, kéo chuột giả lập, nạp preview bằng video thật và
bấm Phát. Đọc code hay ``import`` suôn sẽ không bắt được nhóm lỗi chỉ nổ lúc tạo
widget — ví dụ đặt tên hàm dựng UI là ``_setup``, trùng ``tkinter.Widget._setup``
nội bộ mà ``Frame.__init__`` gọi lại.

    python tools/verify_ocr_panel.py                 # kiểm tra bản đã cài
    python tools/verify_ocr_panel.py --video X.mp4   # test luôn preview + phát
'''
from __future__ import annotations

import argparse
import re
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = Path(r'C:\Users\Administrator\MumuStudioPro\{app}')

# chữ phải hiện trên panel; thiếu cái nào là dựng UI hỏng. BaseModule.section HOA
# tiêu đề mục nên so không phân biệt hoa thường.
EXPECT = ('Video cần OCR', 'Chọn video', 'Ngôn ngữ', 'Dùng GPU (CUDA)', 'Trễ (s)',
          'Xem trước & chọn vùng', 'Phát', 'Chỉ OCR vùng đã khoanh', 'Nạp lại', 'Xoá vùng',
          'Rộng', 'Cao', 'Chạy OCR', 'Dừng', 'Lưu .srt…', 'Mở thư mục', 'Kết quả', 'File .srt')

# chỉ những hàm không mở hộp thoại / không đụng file system
SAFE_CALLS = ('refresh_engine', 'stop', 'clear_region', 'current_crop', 'typed_crop',
              '_stop_playback', '_report_region', '_update_time')

TIME_RE = re.compile(r'^\d\d:\d\d / \d\d:\d\d$')


class _Evt:
    '''Thay cho tkinter.Event khi mô phỏng kéo chuột.'''

    def __init__(self, x, y):
        self.x, self.y = x, y


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


def _pump(root, mod, seconds: float, until, step: float = 0.03) -> bool:
    """Chạy event loop thật để callback `after` và thread nền được phục vụ."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        root.update()
        try:
            mod._pump()
        except Exception:                              # noqa: BLE001
            pass
        if until():
            return True
        time.sleep(step)
    return bool(until())


def _walk_widget_tree(widget):
    stack = [widget]
    while stack:
        w = stack.pop()
        yield w
        stack.extend(w.winfo_children())


def _check_structure(mod, texts) -> list[str]:
    fails = []
    joined = '\n'.join(texts).upper()
    missing = [e for e in EXPECT if e.upper() not in joined]
    if missing:
        fails.append('thiếu widget: ' + ', '.join(missing))
    if 'ModuleOcr._setup' in joined or '_setup' in type(mod).__dict__:
        fails.append('vẫn ghi đè tkinter.Widget._setup')
    kinds = {}
    for w in _walk_widget_tree(mod):
        kinds[type(w).__name__] = kinds.get(type(w).__name__, 0) + 1
    for needed in ('CTkSlider', 'CTkCanvas'):
        if not kinds.get(needed):
            fails.append(f'panel không có {needed} nào')
    if not TIME_RE.search(str(mod.lbl_time.cget('text'))):
        fails.append(f'nhãn thời gian sai định dạng: {mod.lbl_time.cget("text")!r}')
    # dropdown ngôn ngữ: phải là tên đầy đủ và mọi lựa chọn đều là mã VideOCR nhận
    from app.services import videocr_ocr

    choices: list = []
    menu = [w for w in _walk_widget_tree(mod) if type(w).__name__ == 'CTkOptionMenu']
    if not menu:
        fails.append('không tìm thấy dropdown ngôn ngữ')
    else:
        choices = menu[0].cget('values')
        if 'Chinese & English' not in choices:
            fails.append('thiếu lựa chọn "Chinese & English"')
        if any(c in ('ch', 'en', 'vi', 'zh') for c in choices):
            fails.append(f'dropdown vẫn hiện mã thay vì tên: {choices[:6]}')
        bad = [c for c in choices if videocr_ocr.resolve_lang(c) is None]
        if bad:
            fails.append(f'có lựa chọn không map được sang mã hợp lệ: {bad}')
    if videocr_ocr.resolve_lang(mod.var_lang.get()) != 'ch':
        fails.append(f'mặc định không phải Chinese & English: {mod.var_lang.get()!r}')
    if 'ch' not in str(mod.lbl_lang.cget('text')):
        fails.append(f'nhãn không báo mã sẽ gửi: {mod.lbl_lang.cget("text")!r}')
    print('  dropdown:', len(choices), 'ngôn ngữ | mặc định', repr(mod.var_lang.get()),
          '|', mod.lbl_lang.cget('text'))
    print('  slider/canvas:', kinds.get('CTkSlider'), kinds.get('CTkCanvas'),
          '| nhãn giờ:', mod.lbl_time.cget('text'))
    return fails


def _check_drag(mod, root) -> list[str]:
    '''Kéo chuột giả lập và đòi ra đúng crop pixel gốc + 4 ô số theo sau.'''
    fails = []
    root.update()
    mod._photo = 'x'                     # chỉ cần khác None để handler không bỏ qua
    mod._shown = (216, 384)              # preview 1/5 của video 1080x1920
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
            fails.append(f'ô vẽ lệch so với chỗ đã kéo: {coords}')
    mod.var_use_region.set(False)
    if mod.current_crop() is not None:
        fails.append('tắt "chỉ OCR vùng" rồi mà current_crop() vẫn trả crop')
    mod.var_use_region.set(True)
    if mod.current_crop() != (0, 1600, 1080, 200):
        fails.append(f'4 ô số không theo kéo chuột: {[v.get() for v in mod.vars_crop]}')
    for var, value in zip(mod.vars_crop, ('100', '1700', '900', '120')):
        var.set(value)
    mod._crop_from_fields()
    if mod.current_crop() != (100, 1700, 900, 120):
        fails.append(f'nhập số trực tiếp không ăn khớp: {mod.current_crop()}')
    rect = mod.canvas.coords(mod._rect_id)
    # 100..1000 / 1080 của video -> 20..200 trên ảnh 216px, không cộng offset nào
    if [round(c) for c in rect] != [20, 340, 200, 364]:
        fails.append(f'sửa ô số mà ô vẽ không theo: {rect}')
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


def _check_preview(mod, root, video) -> list[str]:
    '''Cả đường đi thật: ffmpeg giải mã -> slider -> kéo -> Phát.'''
    path = Path(video)
    if not path.is_file():
        return [f'không có video test: {path}']
    fails = []
    mod.reset_preview()
    mod.var_video.set(str(path))
    mod.load_preview()
    if not _pump(root, mod, 20.0, lambda: mod._photo is not None and mod._shown[0] > 0):
        return ['load_preview() không ra khung hình nào sau 20s (thiếu ffmpeg?)']
    stream = mod._stream
    info = stream.info
    dw, dh = mod._shown
    sw, sh = mod._src
    print(f'  frame {dw}x{dh}px từ video {sw}x{sh}px, {info.total_frames} ảnh @ {info.fps:g}fps')
    # yêu cầu của người dùng: ảnh phải lấp kín khung, không nằm gọn một góc
    cw, ch = int(mod.canvas.cget('width')), int(mod.canvas.cget('height'))
    if (cw, ch) != (dw, dh):
        fails.append(f'canvas không ôm sát ảnh: canvas {cw}x{ch} còn ảnh {dw}x{dh}')
    if mod.canvas.pack_info().get('fill') not in (None, '', 'none'):
        fails.append(f'canvas vẫn pack(fill={mod.canvas.pack_info().get("fill")!r}) '
                     '-> bị kéo rộng hơn ảnh')
    # video DỌC thì ảnh hẹp hơn panel là ĐÚNG (bị chặn bởi chiều cao), nên đòi "lấp
    # kín" phải xét theo trục nào là trục giới hạn
    if dw < 300 and dh < 400:
        fails.append(f'preview quá nhỏ so với panel: {dw}x{dh}')
    if abs(dw / dh - sw / sh) > 0.06:
        fails.append(f'tỉ lệ frame sai: {dw}x{dh} so với {sw}x{sh}')
    if not [i for i in mod.canvas.find_all() if str(mod.canvas.type(i)) == 'image']:
        fails.append('canvas không có item ảnh nào')
    try:
        to = float(mod.slider.cget('to'))
    except (TypeError, ValueError):
        to = float(mod.slider['to'])
    if to < 10:
        fails.append(f'thanh trượt không có phạm vi: to={to}')

    _check_scrub(mod, root, fails)
    _check_playback(mod, root, fails)

    mod._on_scrub(0)
    mod._drag_start(_Evt(2, dh - 40))
    mod._drag_motion(_Evt(dw // 2, dh - 20))
    mod._drag_end(_Evt(dw - 2, dh - 4))
    rect = mod.canvas.coords(mod._rect_id) if mod._rect_id else None
    if rect and [round(c) for c in rect] != [2, dh - 40, dw - 2, dh - 4]:
        fails.append(f'ô vẽ không khớp điểm thả chuột: {rect}')
    if not mod.region:
        fails.append('kéo vùng trên ảnh thật không ra crop')
    else:
        x, y, cw, ch = mod.region
        if not (0 <= x and x + cw <= sw and 0 <= y and y + ch <= sh):
            fails.append(f'crop {mod.region} tràn ra ngoài video {(sw, sh)}')
        print(f'  kéo {dw}x{dh} -> crop gốc {mod.region}')
    mod.on_tab_deactivated()
    if mod._playing:
        fails.append('rời thẻ mà vẫn đang phát')
    return fails


def _check_scrub(mod, root, fails) -> None:
    '''Kéo thanh trượt phải đổi khung hình tức thì (không spawn ffmpeg mới).'''
    total = mod._stream.info.total_frames
    target = max(1, min(30, total - 1))
    # ffmpeg giải mã nền: phải đợi tới đúng frame sắp dùng, nếu không phép thử
    # "scrub có đổi ảnh không" sẽ kiểm vào chỗ trống và báo đỏ giả
    if not _pump(root, mod, 25.0, lambda: mod._stream.ready() > target):
        fails.append(f'buffer không tới frame {target} trong 25s (mới có {mod._stream.ready()})')
        return
    t0 = time.perf_counter()
    mod._on_scrub(target)
    took = time.perf_counter() - t0
    root.update()
    if mod._index != target:
        fails.append(f'scrub tới {target} nhưng index là {mod._index}')
    if took > 0.25:
        fails.append(f'scrub mất {took:.2f}s — phải tức thì vì frame đã giải mã sẵn')
    print(f'  scrub tới ảnh {target} trong {took * 1000:.0f}ms')


def _check_playback(mod, root, fails) -> None:
    '''Phát phải nhích đúng fps và tự dừng khi hết — cả hai chiều đều phải kiểm.'''
    total = mod._stream.info.total_frames
    mod._on_scrub(0)
    mod.toggle_play()
    if not mod._playing:
        fails.append('bấm Phát mà không vào trạng thái phát')
        return
    if 'dừng' not in str(mod.btn_play.cget('text')).lower():
        fails.append(f'nút Phát không đổi nhãn khi đang phát: {mod.btn_play.cget("text")!r}')
    _pump(root, mod, 0.6, lambda: False)
    moved = mod._index
    if moved < 2:
        fails.append(f'phát 0,6 giây chỉ nhích {moved} ảnh (mong ~4)')
    mod.toggle_play()
    if mod._playing:
        fails.append('bấm lần hai mà không dừng được')
    if mod._tick_job is not None:
        fails.append('dừng rồi mà còn hẹn tick tiếp')
    print(f'  phát 0,6s -> +{moved} ảnh')

    # bấm sát cuối: _tick phải tự dừng và trả nhãn về "Phát". Phải đợi ffmpeg giải
    # mã xong toàn bộ đã, nếu không _show_index(total-2) không có frame mà bỏ qua,
    # index đứng nguyên ở giữa video và phép thử này kiểm sai chỗ.
    total = mod._stream.info.total_frames
    if not _pump(root, mod, 25.0, lambda: mod._stream.ready() >= total):
        print(f'  SKIP: buffer mới có {mod._stream.ready()}/{total} ảnh, không kiểm được cuối video')
    else:
        mod._on_scrub(total - 2)
        if mod._index != total - 2:
            fails.append(f'scrub tới cuối không ăn: index {mod._index}/{total}')
        mod.toggle_play()
        _pump(root, mod, 1.5, lambda: not mod._playing)
        if mod._playing:
            fails.append('tới cuối video mà vẫn đánh dấu đang phát')
        if 'phát' not in str(mod.btn_play.cget('text')).lower():
            fails.append(f'hết video nhưng nút không trở lại "Phát": {mod.btn_play.cget("text")!r}')
        if mod._index != total - 1:
            fails.append(f'hết video nhưng dừng ở ảnh {mod._index}/{total}')


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', action='store_true', help='dùng source repo thay vì bản đã cài')
    ap.add_argument('--video', help='video thật để test preview + thanh trượt + Phát')
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
    if args.video:
        state.active_video_path = str(Path(args.video).resolve())
    callbacks = {name: (lambda *a: None) for name in
                 ('add_videos', 'clear_videos', 'start', 'stop', 'open_output')}
    fails: list[str] = []
    try:
        nav = [title for _key, title in ControlPanel.NAV]
        print(f'NAV: {" ".join(nav)}')
        if 'OCR' not in nav:
            fails.append('thiếu mục OCR trong NAV')

        panel = ControlPanel(tk_root, state, callbacks)
        _pump(tk_root, panel, 0.4, lambda: False)

        mod = panel._get_module('ocr')
        _pump(tk_root, mod, 0.4, lambda: False)
        if not isinstance(mod, ModuleOcr):
            fails.append(f'không dựng được panel OCR: {mod!r}')
        else:
            texts = _text_tree(mod)
            print(f'panel OCR: {type(mod).__name__}, {len(texts)} nhãn')
            fails += _check_structure(mod, texts)
            for fn in SAFE_CALLS:
                try:
                    getattr(mod, fn)()
                except Exception as exc:                    # noqa: BLE001
                    fails.append(f'{fn}() nổ: {type(exc).__name__}: {exc}')

            fails += _check_drag(mod, tk_root)
            if args.video:
                fails += _check_preview(mod, tk_root, args.video)
            else:
                fails.append('bỏ qua test preview — thêm --video <tập tin>')

            panel.select_tool('ocr')
            _pump(tk_root, mod, 0.2, lambda: False)
            shown = [w for w in panel.content.winfo_children() if w.winfo_ismapped()]
            if not shown:
                fails.append('select_tool("ocr") xong mà không có panel nào được map')
        mod_on_close = locals().get('mod')
        if isinstance(mod_on_close, ModuleOcr):
            mod_on_close._on_destroy()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        fails.append('ControlPanel dựng không xong')
    finally:
        tk_root.destroy()

    if fails:
        print('\nFAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('\nOK — thẻ OCR dựng thật, đủ widget, preview + thanh trượt + Phát chạy được.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

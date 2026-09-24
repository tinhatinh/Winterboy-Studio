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
          'Chạy OCR', 'Dừng', 'Lưu .srt…', 'Mở thư mục', 'Kết quả', 'File .srt')

# chỉ những hàm không mở hộp thoại / không đụng file system
SAFE_CALLS = ('sync_from_state', 'refresh_engine', 'stop')


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


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', action='store_true', help='dùng source repo thay vì bản đã cài')
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

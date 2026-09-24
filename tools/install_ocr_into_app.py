# -*- coding: utf-8 -*-
'''Cài / gỡ công cụ OCR vào bản Winterboy Studio đã cài đặt.

App này là bản PyInstaller onedir và KHÔNG nhúng module của app trong exe —
module được nạp từ ``_internal\\app\\**`` dưới dạng .pyc rời. Python ưu tiên ``.py``
hơn ``.pyc`` cùng tên, nên chỉ cần thả file .py vào là thêm được tính năng mà không
phải build lại toàn bộ. Vì vậy cũng gỡ được sạch bằng cách xoá đúng các file đó.

    python tools/install_ocr_into_app.py            # cài
    python tools/install_ocr_into_app.py --revert    # gỡ, trả lại nguyên trạng
'''
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = Path(r'C:\Users\Administrator\MumuStudioPro\{app}')
DESKTOP = Path.home() / 'Desktop'
SHORTCUT = DESKTOP / 'Winterboy OCR.lnk'

# (nguồn trong repo, đích trong app)
FILES = [
    (REPO / 'app/services/videocr_ocr.py', APP / '_internal/app/services/videocr_ocr.py'),
    (REPO / 'app/ui/modules/module_ocr.py', APP / '_internal/app/ui/modules/module_ocr.py'),
    # control_panel.py đã được khôi phục khớp bytecode 100% với bản phát hành, chỉ
    # chênh đúng 5 chỗ của tính năng OCR (xem `compare_bytecode`), nên thả vào app
    # để mục "OCR" xuất hiện trên thanh bên.
    (REPO / 'app/ui/control_panel.py', APP / '_internal/app/ui/control_panel.py'),
    (REPO / 'tools/ocr_tool.pyw', APP / 'ocr_tool.pyw'),
]
PYWARE = Path(sys.base_prefix) / 'pythonw.exe'


def install() -> int:
    if not APP.is_dir():
        print(f'không thấy app ở {APP}')
        return 1
    for src, dst in FILES:
        if not src.is_file():
            print(f'thiếu nguồn: {src}')
            return 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f'  + {dst.relative_to(APP)}')
    for p in APP.rglob('__pycache__'):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    _make_shortcut()
    print('\nXong. Mục "OCR" đã nằm trên thanh bên của cửa sổ chính.')
    print('     Bấm "Winterboy OCR" ngoài Desktop nếu muốn chạy riêng, khỏi mở app.')
    print('     Gỡ sạch: python tools/install_ocr_into_app.py --revert')
    return 0


def _make_shortcut() -> None:
    if not PYWARE.is_file():
        print(f'  ! không thấy {PYWARE}, bỏ qua lối tắt')
        return
    try:
        import subprocess
        ps = (
            "$ws=New-Object -ComObject WScript.Shell; "
            f"$s=$ws.CreateShortcut('{SHORTCUT}'); "
            f"$s.TargetPath='{PYWARE}'; "
            f"$s.Arguments='\"{APP / 'ocr_tool.pyw'}\"'; "
            f"$s.WorkingDirectory='{APP}'; "
            "$s.Description='OCR phụ đề cứng trên video thành .srt'; "
            "$s.Save()"
        )
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True,
                       capture_output=True, timeout=60)
        print(f'  + {SHORTCUT.name} (Desktop)')
    except Exception as exc:
        print(f'  ! không tạo được lối tắt: {exc}')


def revert() -> int:
    removed = 0
    for _src, dst in FILES:
        if dst.is_file():
            dst.unlink()
            removed += 1
            print(f'  - {dst.relative_to(APP) if APP in dst.parents else dst}')
    if SHORTCUT.is_file():
        SHORTCUT.unlink()
        print(f'  - {SHORTCUT.name}')
    for p in (APP / '_internal').rglob('__pycache__'):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    print(f'\nĐã gỡ {removed} file. App quay lại đúng bản gốc (.pyc vẫn còn nguyên).')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--revert', action='store_true')
    sys.exit(revert() if ap.parse_args().revert else install())

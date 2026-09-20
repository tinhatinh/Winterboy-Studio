# Source Generated with Decompyle++
# File: capcut_export.pyc (Python 3.12)

'''
CapCut export helpers.

Không có API Export chính thức →:
  1. open_project_in_explorer / open_capcut_app
  2. (tuỳ chọn) RPA pyautogui — chỉ khi user bật, rủi ro cao

Mặc định: mở folder project + hướng dẫn Export tay (an toàn).
'''
from __future__ import annotations
import logging
import os
import shutil
import subprocess
from pathlib import Path
logger = logging.getLogger(__name__)

def find_capcut_exe():
    bases = [
        Path(os.environ.get('LOCALAPPDATA', '')) / 'CapCut' / 'Apps',
        Path('C:\\Program Files\\CapCut'),
        Path('C:\\Program Files (x86)\\CapCut')]
    for base in bases:
        if not base.is_dir():
            continue
        for p in base.rglob('CapCut.exe'):
            
            
            return bases, base.rglob('CapCut.exe'), p
    if which:
        return Path(which)
    return shutil.which('CapCut')


def open_project_folder(project_dir = None):
    project_dir = Path(project_dir)
    if not project_dir.is_dir():
        return False
    
    try:
        os.startfile(str(project_dir))
        return True
    except Exception:
        e = None
        logger.warning('open folder fail: %s', e)
        e = None
        del e
        return False
        e = None
        del e



def launch_capcut():
    exe = find_capcut_exe()
    if not exe:
        logger.warning('Không tìm thấy CapCut.exe')
        return False
    
    try:
        subprocess.Popen([
            str(exe)], cwd = str(exe.parent))
        return True
    except Exception:
        e = None
        logger.warning('launch CapCut fail: %s', e)
        e = None
        del e
        return False
        e = None
        del e



def write_export_readme(project_dir = None, *, project_name):
    project_dir = Path(project_dir)
    if not project_name:
        project_name
    if not project_name:
        project_name
    text = f'''# Export CapCut — {project_dir.name}\n\nProject đã được Mumu Auto Render inject sẵn:\n- Phụ đề (text track)\n- Giọng đọc (audio text_to_audio / Edge-TTS)\n- (tuỳ chọn) BGM, logo, flip, mute gốc…\n\n## Cách export\n\n1. Mở CapCut PC\n2. Chọn project: **{project_dir.name}**\n3. Kiểm tra timeline (sub + voice)\n4. Bấm **Export** (góc phải) → chọn 1080p/60fps tuỳ ý\n5. Lưu file mp4\n\n## Lưu ý\n\n- Tool **không** bấm Generate Auto Captions / Start reading — đã inject sẵn.\n- Export Pro effects dùng quyền sử dụng CapCut của bạn.\n- RPA auto-export: tắt mặc định (dễ vỡ UI).\n\nFolder draft:\n{project_dir}\n'''
    out = project_dir / 'MUMU_EXPORT_README.txt'
    out.write_text(text, encoding = 'utf-8')
    return out


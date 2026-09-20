# Source Generated with Decompyle++
# File: main.pyc (Python 3.12)

'''
Điểm khởi chạy chính của Winterboy Studio.
Chạy:
    python main.py
'''
from __future__ import annotations
import logging
import os
import shutil
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if getattr(sys, 'frozen', False):
    os.environ['WINTERBOY_PROJECT_ROOT'] = str(Path(sys.executable).resolve().parent)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
os.environ.setdefault('HF_HUB_DISABLE_PROGRESS_BARS', '1')
os.environ.setdefault('TQDM_DISABLE', '1')

class _SafeStream:
    '''Fallback stream an toàn để ngăn ngừa lỗi "\'NoneType\' object has no attribute \'write\'"
    khi app chạy dưới dạng GUI/pythonw hoặc worker thread trên Windows.'''
    
    def __init__(self, target_stream = (None,)):
        self._target = target_stream
        self.encoding = 'utf-8'
        self.errors = 'replace'

    
    def write(self = None, s = None):
        pass
    # WARNING: Decompyle incomplete

    
    def flush(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def isatty(self = None):
        return False

    
    def readable(self = None):
        return False

    
    def writable(self = None):
        return True

    
    def seekable(self = None):
        return False

    
    def reconfigure(self = None, **kwargs):
        pass

    
    def writelines(self = None, lines = None):
        for line in lines:
            self.write(line)



def _ensure_safe_stdio():
    '''Đảm bảo sys.stdin, sys.stdout, sys.stderr không bao giờ là None trong suốt vòng đời của app.'''
    import io
# WARNING: Decompyle incomplete

_ensure_safe_stdio()

def _ensure_ffmpeg_on_path():
    '''Tự động tìm và bổ sung FFmpeg vào PATH nếu chưa có (ưu tiên thư mục bin nội bộ của app).'''
    current_path = os.environ.get('PATH', '')
    candidate_dirs = [
        Path(sys.executable).resolve().parent / 'bin',
        ROOT / 'bin',
        Path(sys.executable).resolve().parent]
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_dirs.insert(0, Path(sys._MEIPASS) / 'bin')
        candidate_dirs.insert(1, Path(sys._MEIPASS))
    for c_dir in candidate_dirs:
        if not c_dir.is_dir():
            continue
        if not (c_dir / 'ffmpeg.exe').exists() and (c_dir / 'ffmpeg').exists():
            continue
        if str(c_dir).casefold() not in current_path.casefold():
            os.environ['PATH'] = str(c_dir) + os.pathsep + current_path
            current_path = os.environ['PATH']
        candidate_dirs
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return None
    if sys.platform != 'win32':
        return None
    local_app_data = os.environ.get('LOCALAPPDATA')
    if not local_app_data:
        return None
    winget_links = Path(local_app_data) / 'Microsoft' / 'WinGet' / 'Links'
    if (winget_links / 'ffmpeg.exe').exists():
        if (winget_links / 'ffprobe.exe').exists():
            if str(winget_links).casefold() not in current_path.casefold():
                os.environ['PATH'] = str(winget_links) + os.pathsep + current_path
                return None
            return None
        return None


def _set_windows_app_id():
    '''Tách riêng process khỏi python.exe trên Windows Taskbar khi chạy từ source code.'''
    if sys.platform != 'win32':
        return None
    if getattr(sys, 'frozen', False):
        return None
    
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('WinterboyStudio.AutoRender.1.0')
        return None
    except Exception:
        return None



def setup_logging():
    _ensure_safe_stdio()
# WARNING: Decompyle incomplete


def _activate_existing_instance():
    '''Nếu ứng dụng đã đang chạy, kích hoạt cửa sổ hiện tại lên màn hình chính và trả về True để dừng instance mới.'''
    pass
# WARNING: Decompyle incomplete


def main():
    _ensure_ffmpeg_on_path()
    _set_windows_app_id()
    setup_logging()
    if _activate_existing_instance():
        logging.getLogger(__name__).info('Winterboy Studio Pro đã đang chạy. Đã kích hoạt cửa sổ hiện tại.')
        return 0
    logging.getLogger(__name__).info('Khởi động Winterboy Studio (CustomTkinter Engine)...')
    
    try:
        from app.config.theme import apply_global_theme
        from app.ui.main_window import MainWindow
        apply_global_theme()
        app = MainWindow()
        app.mainloop()
        logging.getLogger(__name__).info('Ứng dụng kết thúc. Thoát tiến trình an toàn.')
        import os
        os._exit(0)
        return 0
    except Exception:
        exc = None
        logging.getLogger('CRASH').critical('Lỗi nghiêm trọng trong luồng giao diện chính: %s', exc, exc_info = True)
        
        pass

if __name__ == '__main__':
    raise SystemExit(main())

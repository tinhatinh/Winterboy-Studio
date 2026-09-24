'''
Điểm khởi chạy chính của Winterboy studio.
Chạy:
    python main.py
'''
# Các hàm _SafeStream / _ensure_safe_stdio / setup_logging / _activate_existing_instance
# khôi phục từ bytecode của bản đã phát hành (Decompyle++ bỏ mất thân hàm). Ghi chú về
# mấy chỗ dễ đoán sai để ở dạng comment: docstring là hằng số trong .pyc, thêm chữ vào
# là lệch ngay so với bản phát hành.
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
    '''Fallback stream an toàn để ngăn ngừa lỗi "'NoneType' object has no attribute 'write'"
    khi app chạy dưới dạng GUI/pythonw hoặc worker thread trên Windows.'''

    def __init__(self, target_stream = None):
        self._target = target_stream
        self.encoding = 'utf-8'
        self.errors = 'replace'

    def write(self, s: str) -> int:
        if self._target is not None:
            try:
                return self._target.write(s)
            except Exception:
                pass
        return len(s) if s else 0

    def flush(self) -> None:
        if self._target is not None:
            try:
                self._target.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def reconfigure(self, **kwargs) -> None:
        pass

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)


def _ensure_safe_stdio() -> None:
    '''Đảm bảo sys.stdin, sys.stdout, sys.stderr không bao giờ là None trong suốt vòng đời của app.'''
    import io
    if sys.stdin is None:
        sys.stdin = io.StringIO('')
    if sys.stdout is None:
        sys.stdout = _SafeStream()
    if sys.stderr is None:
        sys.stderr = _SafeStream(sys.stdout if sys.stdout is not None else None)


_ensure_safe_stdio()


def _ensure_ffmpeg_on_path() -> None:
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
        if not (c_dir / 'ffmpeg.exe').exists() and not (c_dir / 'ffmpeg').exists():
            continue
        if str(c_dir).casefold() not in current_path.casefold():
            os.environ['PATH'] = str(c_dir) + os.pathsep + current_path
            current_path = os.environ['PATH']
        # bản phát hành dừng ngay ở ứng viên đầu tiên thật sự có ffmpeg, không lặp
        # hết danh sách — giữ nguyên, dù nghĩa là 'bin' thắng và các mục sau bị bỏ.
        break
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
    return None


def _set_windows_app_id() -> None:
    '''Tách riêng process khỏi python.exe trên Windows Taskbar khi chạy từ source code.'''
    if sys.platform != 'win32':
        return None
    if getattr(sys, 'frozen', False):
        return None

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('WinterboyStudio.AutoRender.1.01')
        return None
    except Exception:
        return None


def setup_logging() -> None:
    _ensure_safe_stdio()
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding = 'utf-8', errors = 'replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding = 'utf-8', errors = 'replace')
        except Exception:
            pass
    log_dir = ROOT / 'logs'
    log_dir.mkdir(parents = True, exist_ok = True)
    try:
        from app.services.log_cleaner import rotate_large_logs
        rotate_large_logs()
    except Exception:
        pass
    stream_target = sys.stdout if sys.stdout is not None else _SafeStream()
    logging.basicConfig(level = logging.INFO,
                        format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                        handlers = [
                            logging.StreamHandler(stream_target),
                            logging.FileHandler(log_dir / 'auto_render.log', encoding = 'utf-8')])

    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger('CRASH').critical('CỰC KỲ NGHIÊM TRỌNG: Ngoại lệ chưa được xử lý làm sập ứng dụng!',
                                            exc_info = (exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_uncaught_exception
    import threading

    def handle_thread_exception(args):
        logging.getLogger('CRASH').critical(
            f"Ngoại lệ chưa xử lý trong thread '{args.thread.name}': {args.exc_value}",
            exc_info = (args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = handle_thread_exception


def _activate_existing_instance() -> bool:
    '''Nếu ứng dụng đã đang chạy, kích hoạt cửa sổ hiện tại lên màn hình chính và trả về True để dừng instance mới.'''
    # Hai chỗ dễ đoán sai khi dựng lại hàm này từ bytecode:
    #   * ``AttachThreadInput`` thuộc user32, KHÔNG phải kernel32 — gọi sai thì ctypes
    #     ném AttributeError mà ``except Exception: return False`` nuốt lặng, thành ra
    #     bấm icon lần hai vẫn mở thêm cửa sổ mới;
    #   * tham số truyền theo thứ tự ``(curr_tid, fore_tid, ...``, đảo ngược so với
    #     idiom thường gặp.
    if sys.platform != 'win32':
        return False

    try:
        import ctypes
        from ctypes import wintypes

        mutex_name = 'Local\\WinterboyStudioPro_SingleInstance_Mutex'
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            user32 = ctypes.windll.user32
            found_hwnd = []

            def _enum_win_cb(hwnd, extra):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if 'Winterboy studio' in buff.value:
                        found_hwnd.append(hwnd)
                return True

            WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUM(_enum_win_cb), 0)

            if found_hwnd:
                target_hwnd = found_hwnd[0]
                SW_RESTORE = 9
                SW_SHOW = 5
                if user32.IsIconic(target_hwnd):
                    user32.ShowWindow(target_hwnd, SW_RESTORE)
                else:
                    user32.ShowWindow(target_hwnd, SW_SHOW)

                fore_hwnd = user32.GetForegroundWindow()
                if fore_hwnd and fore_hwnd != target_hwnd:
                    fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, None)
                    curr_tid = kernel32.GetCurrentThreadId()
                    if fore_tid != curr_tid:
                        user32.AttachThreadInput(curr_tid, fore_tid, True)
                        user32.BringWindowToTop(target_hwnd)
                        user32.SetForegroundWindow(target_hwnd)
                        user32.AttachThreadInput(curr_tid, fore_tid, False)
                    else:
                        user32.BringWindowToTop(target_hwnd)
                        user32.SetForegroundWindow(target_hwnd)
                else:
                    user32.BringWindowToTop(target_hwnd)
                    user32.SetForegroundWindow(target_hwnd)
            return True
        # giữ tham chiếu để mutex không bị GC giải phóng khi app còn chạy
        globals()['_SINGLE_INSTANCE_MUTEX'] = mutex
        return False
    except Exception:
        return False


def main() -> int:
    _ensure_ffmpeg_on_path()
    _set_windows_app_id()
    setup_logging()
    if _activate_existing_instance():
        logging.getLogger(__name__).info('Winterboy studio đã đang chạy. Đã kích hoạt cửa sổ hiện tại.')
        return 0
    logging.getLogger(__name__).info('Khởi động Winterboy studio (CustomTkinter Engine)...')

    try:
        from app.config.theme import apply_global_theme
        from app.ui.main_window import MainWindow

        apply_global_theme()
        app = MainWindow()
        app.mainloop()
    except Exception as exc:
        logging.getLogger('CRASH').critical('Lỗi nghiêm trọng trong luồng giao diện chính: %s', exc,
                                            exc_info = True)
        return 1
    finally:
        # ``os._exit`` nằm trong finally nên chạy cả khi mainloop xong lẫn khi crash:
        # chủ đích là diệt sạch thread nền còn sống, nên ``return 1`` ở trên thực tế
        # không bao giờ trả về được. Giữ nguyên như bản phát hành.
        logging.getLogger(__name__).info('Ứng dụng kết thúc. Thoát tiến trình an toàn.')
        import os
        os._exit(0)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

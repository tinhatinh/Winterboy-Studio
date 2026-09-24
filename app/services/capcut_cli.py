# Source Generated with Decompyle++
# File: capcut_cli.pyc (Python 3.12)

'''Tạo project CapCut bằng ``capcut-cli`` (Node) thay cho draft builder nội bộ.

Vì sao đổi hướng
----------------
``capcut_draft_builder.py`` tự sinh ``draft_content.json``. Schema nó viết ra
thực ra ĐÚNG (đối chiếu project thật: trùng 36/36 key, ``version=360000``,
``new_version=177.0.0``), nhưng project vẫn hỏng vì hai chuyện quanh nó:

1. CapCut 8.7+ ưu tiên đọc ``template-2.tmp``; ở mọi project thật file này là
   bản sao byte-for-byte của ``draft_content.json``. Builder cũ không hề ghi
   nó, nên CapCut đọc bản template rỗng còn sót lại rồi coi project là trống.
2. Không có chốt chặn khi CapCut.exe đang chạy — app ghi đè ngược lại.

``capcut-cli`` (MIT, https://github.com/renezander030/capcut-cli) xử lý sẵn cả
hai, cộng thêm dò phiên bản và bố cục phẳng/lồng nhau theo từng đời CapCut.

Yêu cầu: Node.js ≥ 18 trong PATH. Gói được nạp qua ``npx`` (cache lần đầu).
'''
from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
logger = logging.getLogger(__name__)
ProgressCb = Callable[([
    float,
    str], None)]
DEFAULT_CLI_SPEC = 'capcut-cli@0.15.0'
WINDOWS_DRAFTS_ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'CapCut' / 'User Data' / 'Projects' / 'com.lveditor.draft'
FIRST_RUN_TIMEOUT = 600
COMMAND_TIMEOUT = 300

class CapCutCliError(RuntimeError):
    '''Lỗi có thông điệp đọc được cho người dùng cuối.'''
    pass

@dataclass
class CapCutBuildResult:
    ok: bool
    project_name: str = ''
    project_dir: Path | None = None
    n_captions: int = 0
    n_audio: int = 0
    message: str = ''
    warnings: list[str] = field(default_factory = list)


def node_path():
    return shutil.which('node')


def npx_path():
    return shutil.which('npx')


def cli_spec():
    return (os.environ.get('MUMU_CAPCUT_CLI') or DEFAULT_CLI_SPEC).strip()


def default_drafts_root():
    override = (os.environ.get('MUMU_CAPCUT_DRAFTS') or '').strip()
    if override:
        return Path(override)
    return WINDOWS_DRAFTS_ROOT


def capcut_is_running():
    '''True nếu CapCut.exe đang mở.

    Ghi draft khi app đang chạy thì CapCut ghi đè lại — chính CLI cũng từ chối.
    Kiểm tra trước để báo lỗi dễ hiểu thay vì để CLI trả JSON lỗi.
    '''
    if not sys.platform.startswith('win'):
        return False
    
    try:
        out = subprocess.run([
            'tasklist',
            '/FI',
            'IMAGENAME eq CapCut.exe',
            '/NH'], capture_output = True, text = True, timeout = 20, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout or ''
        return 'capcut.exe' in out.casefold()
    except Exception:
        return False



def environment_report():
    '''Tóm tắt để UI báo thiếu gì trước khi chạy.'''
    root = default_drafts_root()
    return {
        'node': node_path(),
        'npx': npx_path(),
        'cli_spec': cli_spec(),
        'drafts_root': str(root),
        'drafts_exists': root.is_dir(),
        'capcut_running': capcut_is_running() }


def _kill_tree(pid = None):
    if pid <= 0:
        return None
    
    try:
        if sys.platform.startswith('win'):
            subprocess.run([
                'taskkill',
                '/F',
                '/T',
                '/PID',
                str(pid)], capture_output = True, text = True, timeout = 15)
            return None
        os.killpg(os.getpgid(pid), 9)
        return None
    except Exception as exc:
        logger.debug('kill capcut-cli %s: %s', pid, exc)
        return None

class CapCutCliRunner:
    '''Chạy capcut-cli, huỷ được giữa chừng.

    Có ``request_cancel``/``is_cancelled`` cùng chữ ký với ``FFmpegRenderer`` để
    RenderPipeline gắn làm ``_current_renderer`` — nhờ vậy nút Dừng dùng chung
    được cho cả render MP4 lẫn tạo project CapCut.
    '''
    
    def __init__(self, *, cancel_event = None, drafts_root = None):
        self._cancel = cancel_event if cancel_event is not None else threading.Event()
        self.drafts_root = Path(drafts_root) if drafts_root else default_drafts_root()
        self._proc = None
        self._first_run_done = False

    
    def request_cancel(self):
        self._cancel.set()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            _kill_tree(int(proc.pid))

    
    def is_cancelled(self):
        return self._cancel.is_set()

    
    def _raise_if_cancelled(self):
        if self._cancel.is_set():
            raise CapCutCliError('Đã dừng theo yêu cầu')

    
    def _run(self, args):
        self._raise_if_cancelled()
        npx = npx_path()
        if not npx:
            raise CapCutCliError('Không tìm thấy Node.js/npx trong PATH.\nCài Node.js ≥ 18 (https://nodejs.org) rồi mở lại app.')
        cmd = [
            npx,
            '--yes',
            cli_spec(),
            *args]
        timeout = COMMAND_TIMEOUT if self._first_run_done else FIRST_RUN_TIMEOUT
        logger.info('capcut-cli: %s', ' '.join(args[:4]))
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace' }
        if sys.platform.startswith('win'):
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        else:
            kwargs['start_new_session'] = True
        self._proc = subprocess.Popen(cmd, **kwargs)
        
        try:
            (out, err) = self._proc.communicate(timeout = timeout)
            code = self._proc.returncode
        except subprocess.TimeoutExpired:
            _kill_tree(int(self._proc.pid))
            raise CapCutCliError(f'''capcut-cli quá thời gian {timeout}s''')
        finally:
            self._proc = None

        self._first_run_done = True
        if self._cancel.is_set():
            raise CapCutCliError('Đã dừng theo yêu cầu')
        payload = _first_json_object(out) or _first_json_object(err) or { }
        if code != 0 or payload.get('error'):
            detail = str(payload.get('error') or '').strip()
            if not detail:
                detail = ((err or out or '').strip() or f'''exit {code}''')[-500:]
            raise CapCutCliError(_friendly(detail))
        return payload

    
    def build_project(self, *, name, video = None, srt = None, voice = None, voice_volume = 1.0, bgm_paths = (), bgm_clips = (), bgm_volume = 0.15, subtitle_only = False, progress = None):
        '''Tạo project CapCut: video nền + phụ đề + lồng tiếng + nhạc nền (hoặc chỉ phụ đề để tạo voice TTS).'''
        # Thân hàm này dài ~700 instruction trong dis và bản decompile chỉ còn `pass`
        # -> cần luồng khôi phục hành vi dựng lại theo bytecode, không đoán ở lượt này.
        raise NotImplementedError('chưa khôi phục từ bytecode: capcut_cli.CapCutCliRunner.build_project')

    
    def _add_audio(self, project_dir, audio, volume, track, *, start_s = 0.0, duration_s = None):
        duration = _probe_duration_s(audio)
        if duration <= 0:
            raise CapCutCliError(f'''không đọc được thời lượng {audio.name}''')
        use_duration = min(duration, max(0.01, duration_s)) if duration_s else duration
        self._run([
            'add-audio',
            str(project_dir),
            str(audio.resolve()),
            f'''{max(0.0, start_s):.3f}''',
            f'''{use_duration:.3f}''',
            '--volume',
            f'''{max(0.0, min(1.0, volume)):.3f}''',
            '--track-name',
            track])



def _first_json_object(text = None):
    '''Lấy object JSON đầu tiên trong output (CLI có thể in kèm dòng khác).'''
    if not text:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        if not line.endswith('}'):
            continue
        
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(parsed, dict):
            continue
        return parsed
    return None


def _friendly(detail = None):
    low = detail.casefold()
    if 'capcut.exe is running' in low:
        return 'CapCut đang mở — hãy ĐÓNG CapCut rồi bấm lại.\n\nGhi draft khi app đang chạy sẽ bị CapCut ghi đè.'
    if 'enoent' in low or 'not recognized' in low or 'cannot find' in low:
        return f'''Không chạy được capcut-cli. Kiểm tra Node.js ≥ 18 đã cài và có mạng cho lần tải gói đầu tiên.\n\nChi tiết: {detail}'''
    if 'version' in low and 'guard' in low:
        return f'''Phiên bản CapCut trên máy nằm ngoài dải capcut-cli hỗ trợ (6.x–9.x).\nChi tiết: {detail}'''
    return detail


def _probe_duration_s(path = None):
    ffprobe = shutil.which('ffprobe')
    if not ffprobe:
        return 0.0
    
    try:
        out = subprocess.run([
            ffprobe,
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            str(path)], capture_output = True, text = True, timeout = 60, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        return max(0.0, float(((out or '0').strip() or 0)))
    except Exception:
        return 0.0



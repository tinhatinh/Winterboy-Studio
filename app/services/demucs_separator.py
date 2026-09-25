'''Optional, cached Demucs separation for keeping music/SFX without dialogue.'''

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable
from app.services.artifact_manifest import DependencyManifest, file_dependency, stable_fingerprint

logger = logging.getLogger(__name__)
ProgressCb = Callable[[float, str], None]


def _hidden_kwargs() -> dict:
    if not sys.platform.startswith('win'):
        return {}
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 134217728)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
    startup.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
    return {
        'creationflags': flags,
        'startupinfo': startup}


def _find_executable(name: str) -> str | None:
    '''Tìm binary cả khi app được mở trước lúc WinGet cập nhật PATH.'''
    found = shutil.which(name)
    if found:
        return found
    executable = name if name.casefold().endswith('.exe') else f'''{name}.exe'''
    candidates = [Path(sys.base_prefix) / 'Scripts' / executable]
    if sys.platform.startswith('win'):
        local = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
        candidates.append(local / 'Microsoft' / 'WinGet' / 'Links' / executable)
        python_root = local / 'Programs' / 'Python'
        if python_root.is_dir():
            candidates.extend(sorted(python_root.glob(f'''Python*/Scripts/{executable}'''), reverse = True))
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def _demucs_command() -> list[str]:
    executable = _find_executable('demucs')
    if executable:
        return [executable]
    if not getattr(sys, 'frozen', False) and importlib.util.find_spec('demucs') is not None:
        return [sys.executable, '-m', 'demucs']
    raise RuntimeError(
        'Không tìm thấy Demucs trong Python/Scripts. Cài dependencies bằng: pip install -r requirements.txt')


def _version_from_command(command: 'list[str] | None') -> str:
    '''Suy phiên bản Demucs từ thư mục dist-info nằm cạnh chính file exe.

    Bản đóng gói (PyInstaller) chỉ thấy .dist-info nào được bỏ vào bundle, mà demucs
    thì KHÔNG nằm trong app — app chỉ gọi ``demucs.exe`` của một Python hệ thống. Vì vậy
    ``importlib.metadata.version('demucs')`` báo "No package metadata was found" dù lệnh
    chạy tốt. Đọc tên thư mục ``demucs-<version>.dist-info`` cạnh ``Scripts`` giải quyết
    đúng trường hợp này và giữ khoá cache ổn định giữa bản cài và bản chạy từ source.
    '''
    if not command:
        return ''
    head = Path(str(command[0]))
    if head.name.casefold() != 'demucs.exe':
        return ''
    scripts = head.parent
    for root in (scripts.parent / 'Lib' / 'site-packages', scripts / 'site-packages'):
        try:
            hits = sorted(root.glob('demucs-*.dist-info'))
        except OSError:
            continue
        if hits:
            name = hits[-1].name
            return name[len('demucs-'):-len('.dist-info')]
    return ''


def demucs_runtime_status() -> dict[str, object]:
    '''Trạng thái backend; chỉ được gọi trong worker khi người dùng bật Demucs.

    "Có chạy được hay không" chỉ phụ thuộc vào việc tìm thấy lệnh Demucs: Demucs chạy ở
    TIẾN TRÌNH CON bằng Python hệ thống, nên app đông lạnh không cần torch hay metadata
    của demucs bên trong bundle. Trước đây hai thông tin chẩn đoán (số phiên bản, torch)
    nằm chung một khối try với bước tìm lệnh, nên chỉ cần thiếu metadata là
    ``available`` thành False và cả lần render MP4 chết với lỗi
    "No package metadata was found for demucs".
    '''
    status = {
        'available': False,
        'command': None,
        'device': 'cpu',
        'torch_version': '',
        'demucs_version': ''}
    try:
        status['command'] = _demucs_command()
    except Exception as exc:
        status['error'] = str(exc)
        return status
    status['available'] = True
    try:
        from importlib.metadata import version
        status['demucs_version'] = version('demucs')
    except Exception:
        status['demucs_version'] = _version_from_command(status['command'])
    try:
        import torch
        status['torch_version'] = str(torch.__version__)
        status['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
    except Exception:
        pass                                       # torch không đi kèm app -> giữ 'cpu'
    return status


def _run_cancellable(
    command: list[str],
    *,
    cancel_event: threading.Event | None,
    log_path: Path,
    timeout_s: float = 7200.0,
) -> None:
    with log_path.open('w', encoding = 'utf-8', errors = 'replace') as log_file:
        process = subprocess.Popen(
            command,
            stdout = log_file,
            stderr = subprocess.STDOUT,
            text = True,
            **_hidden_kwargs())
        deadline = time.monotonic() + max(1.0, timeout_s)
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                process.kill()
                process.wait(timeout = 10)
                raise RuntimeError('Đã dừng tách lời Demucs')
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout = 10)
                raise RuntimeError(f'''Demucs quá thời gian chờ ({int(timeout_s)} giây)''')
            time.sleep(0.2)
        if process.returncode:
            try:
                detail = log_path.read_text(encoding = 'utf-8', errors = 'replace')[-1200:]
            except OSError:
                detail = ''
            raise RuntimeError(f'''Demucs lỗi (code={process.returncode}): {detail}''')


def separate_background(video_path: str | Path,
                        *,
                        cancel_event: threading.Event | None = None,
                        progress: ProgressCb | None = None,
                        model: str = 'htdemucs') -> Path:
    '''Return a cached ``no_vocals.wav`` for the source video.'''
    source = Path(video_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    ffmpeg = _find_executable('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Không tìm thấy ffmpeg để chuẩn bị audio cho Demucs')
    runtime = demucs_runtime_status()
    if not runtime.get('available'):
        raise RuntimeError(str(runtime.get('error') or 'Demucs chưa sẵn sàng'))
    device = str(runtime.get('device') or 'cpu')
    cache_root = Path(tempfile.gettempdir()) / 'winterboy_demucs_cache'
    cache_root.mkdir(parents = True, exist_ok = True)
    dependencies = {
        'version': 2,
        'source': file_dependency(source),
        'model': model,
        'stems': 'vocals',
        'sample_rate': 44100,
        'demucs_version': str(runtime.get('demucs_version') or '')}
    key = stable_fingerprint(dependencies)
    output = cache_root / f'''{key}_no_vocals.wav'''
    manifest = DependencyManifest(cache_root / 'artifact_manifest.json')
    if manifest.valid(f'''demucs:{key}''', dependencies, output = output, min_size = 1000):
        output.touch()
        logger.info('Demucs cache HIT · %s', key[:12])
        if progress:
            progress(1.0, 'Demucs · dùng cache nhạc/hiệu ứng')
        return output
    if progress:
        progress(0.02, 'Demucs · chuẩn bị tách lời…')
    demucs = list(runtime.get('command') or _demucs_command())
    with tempfile.TemporaryDirectory(prefix = 'winterboy_demucs_', dir = cache_root) as temp_name:
        temp_dir = Path(temp_name)
        audio_input = temp_dir / 'source_audio.wav'
        extract = [
            ffmpeg,
            '-y',
            '-hide_banner',
            '-loglevel',
            'error',
            '-i',
            str(source),
            '-vn',
            '-ac',
            '2',
            '-ar',
            '44100',
            str(audio_input)]
        _run_cancellable(
            extract,
            cancel_event = cancel_event,
            log_path = temp_dir / 'ffmpeg_extract.log',
            timeout_s = 3600)
        if not audio_input.is_file() or audio_input.stat().st_size < 1000:
            raise RuntimeError('Không trích được audio hợp lệ cho Demucs')
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError('Đã dừng tách lời Demucs')
        if progress:
            progress(0.12, f'''Demucs · đang tách lời thoại gốc bằng {device.upper()}…''')
        separated_root = temp_dir / 'separated'
        command = [
            *demucs,
            '--two-stems=vocals',
            '-n',
            model,
            '-d',
            device,
            '-j',
            '1',
            '-o',
            str(separated_root),
            str(audio_input)]
        try:
            _run_cancellable(
                command,
                cancel_event = cancel_event,
                log_path = temp_dir / 'demucs.log')
        except RuntimeError as exc:
            # CUDA/CPU tự chọn lại: chỉ thử lại bằng CPU khi người dùng không dừng
            detail = str(exc).casefold()
            cuda_error = device == 'cuda' and any(
                marker in detail for marker in ('cuda', 'cudnn', 'out of memory', 'gpu'))
            if not cuda_error or (cancel_event is not None and cancel_event.is_set()):
                raise
            logger.warning('Demucs CUDA lỗi; thử lại bằng CPU: %s', exc)
            if progress:
                progress(0.14, 'Demucs · GPU lỗi, tự chuyển sang CPU…')
            shutil.rmtree(separated_root, ignore_errors = True)
            command[command.index('cuda')] = 'cpu'
            device = 'cpu'
            _run_cancellable(
                command,
                cancel_event = cancel_event,
                log_path = temp_dir / 'demucs_cpu.log')
        candidate = separated_root / model / audio_input.stem / 'no_vocals.wav'
        if not candidate.is_file() or candidate.stat().st_size < 1000:
            found = list(separated_root.rglob('no_vocals.wav'))
            candidate = found[0] if found else candidate
        if not candidate.is_file() or candidate.stat().st_size < 1000:
            raise RuntimeError('Demucs hoàn tất nhưng không tạo được file no_vocals.wav')
        shutil.copy2(candidate, output)
    manifest.record(
        f'''demucs:{key}''',
        output,
        dependencies,
        metadata = {
            'source': str(source),
            'model': model,
            'device': device,
            'demucs_version': str(runtime.get('demucs_version') or ''),
            'torch_version': str(runtime.get('torch_version') or '')})
    logger.info('Demucs cache MISS → saved · %s', output)
    if progress:
        progress(1.0, 'Demucs · đã tách lời và lưu cache')
    return output

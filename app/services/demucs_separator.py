# Source Generated with Decompyle++
# File: demucs_separator.pyc (Python 3.12)

'''Optional, cached Demucs separation for keeping music/SFX without dialogue.'''
from __future__ import annotations
import importlib.util as importlib
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
ProgressCb = Callable[([
    float,
    str], None)]

def _hidden_kwargs():
    if not sys.platform.startswith('win'):
        return { }
    flags = None(subprocess, 'CREATE_NO_WINDOW', 134217728)
    startup = subprocess.STARTUPINFO()
    getattr(subprocess, 'SW_HIDE', 0) = startup, startup.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1), .dwFlags
    return {
        'creationflags': flags,
        'startupinfo': startup }


def _find_executable(name = None):
    '''Tìm binary cả khi app được mở trước lúc WinGet cập nhật PATH.'''
    found = shutil.which(name)
    if found:
        return found
    executable = name if None.casefold().endswith('.exe') else f'''{name}.exe'''
    candidates = [
        Path(sys.base_prefix) / 'Scripts' / executable]
    if sys.platform.startswith('win'):
        if not os.environ.get('LOCALAPPDATA'):
            os.environ.get('LOCALAPPDATA')
        local = Path(Path.home() / 'AppData' / 'Local')
        candidates.append(local / 'Microsoft' / 'WinGet' / 'Links' / executable)
        python_root = local / 'Programs' / 'Python'
        if python_root.is_dir():
            candidates.extend(sorted(python_root.glob(f'''Python*/Scripts/{executable}'''), reverse = True))
    for candidate in candidates:
        if candidate.is_file():
            
            return candidates, str(candidate)
    return None
    except OSError:
        continue


def _demucs_command():
    executable = _find_executable('demucs')
    if executable:
        return [
            executable]
# WARNING: Decompyle incomplete


def demucs_runtime_status():
    '''Trạng thái backend; chỉ được gọi trong worker khi người dùng bật Demucs.'''
    status = {
        'available': False,
        'command': None,
        'device': 'cpu',
        'torch_version': '',
        'demucs_version': '' }
    
    try:
        status['command'] = _demucs_command()
        version = version
        import importlib.metadata
        status['demucs_version'] = version('demucs')
        import torch
        status['torch_version'] = str(torch.__version__)
        status['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        status['available'] = True
        return status
    except Exception:
        exc = None
        status['error'] = str(exc)
        exc = None
        del exc
        return status
        exc = None
        del exc



def _run_cancellable(command = None, *, cancel_event, log_path, timeout_s):
    log_file = log_path.open('w', encoding = 'utf-8', errors = 'replace')
# WARNING: Decompyle incomplete


def separate_background(video_path = None, *, cancel_event, progress, model):
    '''Return a cached ``no_vocals.wav`` for the source video.'''
    pass
# WARNING: Decompyle incomplete


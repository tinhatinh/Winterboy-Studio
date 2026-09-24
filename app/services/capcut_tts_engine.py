# Source Generated with Decompyle++
# File: capcut_tts_engine.pyc (Python 3.12)

"""CapCut cloud TTS + STT engine for Winterboy studio.

Wraps ``capcut_common_task_client`` (from capcut-tts-api):

TTS:
  1. POST /lv/v1/common_task/new   (sami_text_to_speech)
  2. POST /lv/v1/common_task/query until succeed/failed
  3. Extract audio URL or base64 → local MP3/WAV

STT (alongside Whisper / ElevenLabs — does not replace them):
  1. Extract audio → upload VOD (upload_sign + Apply/CommitUploadInner)
  2. POST common_task/new (cc_audio_subtitle_asr)
  3. Poll query → utterances → SRT

Voice catalog ships as ``capcut_voices.json`` (from CapCut Voice.json).

Device/session overrides live in ``~/.winterboy/capcut_device.json`` so secrets
stay out of last_config / shared presets.  Without a valid device profile
CapCut may return ``shark block only`` (anti-bot).
"""
from __future__ import annotations
import base64
import json
import logging
import os
import re
import subprocess
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
logger = logging.getLogger(__name__)
_SERVICE_DIR = Path(__file__).resolve().parent
_VOICES_PATH = _SERVICE_DIR / 'capcut_voices.json'
_DEVICE_PATH = Path.home() / '.winterboy' / 'capcut_device.json'
_DEVICE_SOURCE_PATH = Path.home() / '.winterboy' / 'capcut_device_source.json'
CAPCUT_TTS_CACHE_ROOT = Path.home() / '.winterboy' / 'tts_cache' / 'capcut'
_device_cache_lock = threading.RLock()
_device_cache_stamp: 'tuple[Any, ...] | None' = None
_device_cache_value: 'dict[str, Any] | None' = None
_http_thread_local = threading.local()
DEFAULT_VOICE_TYPE = 'BV074_streaming'
DEFAULT_RESOURCE_ID = '7102355709945188865'
DEFAULT_VOICE_LABEL = f'''Cô Gái Hoạt Ngôn | {DEFAULT_VOICE_TYPE}:{DEFAULT_RESOURCE_ID}'''
_SUCCESS = {
    'ok',
    'done',
    'finish',
    'succeed',
    'success',
    'finished',
    'completed'}
_FAILED = {
    'fail',
    'error',
    'failed',
    'timeout',
    'canceled',
    'cancelled'}
_PENDING = {
    'queued',
    'created',
    'pending',
    'running',
    'waiting',
    'queueing',
    'processing'}
_URL_KEYS = ('audio_url', 'url', 'download_url', 'play_url', 'file_url', 'mp3_url', 'voice_url', 'audio', 'sami_audio_url')
_B64_KEYS = ('audio_data', 'audio_base64', 'data', 'base64', 'binary_data', 'audio_binary', 'sami_audio')

def device_config_path():
    return _DEVICE_PATH


def device_source_config_path():
    '''Path of the small preference file selecting the active device profile.'''
    return _DEVICE_SOURCE_PATH


def get_bundled_capcut_fix_paths():
    '''Return the bundled fix_shark.bat and device.json in the current workspace.'''
    base = Path(__file__).resolve().parent.parent / 'resources' / 'capcut_fix'
    return (base / 'fix_shark.bat', base / 'device.json')


def resolve_capcut_device_path(candidate: str | Path | None = None) -> Path:
    '''Resolve a valid CapCut device.json path with intelligent auto-detection.

    If candidate exists on disk, use it.
    Otherwise, automatically fallback to the bundled device.json in the workspace.
    This guarantees zero broken paths when moving folders, cloning repo, or running on another PC.
    '''
    (_bat, bundled_json) = get_bundled_capcut_fix_paths()
    if candidate:

        try:
            p = Path(candidate).expanduser()
            if p.is_file():
                return p
        except Exception:
            pass

    return bundled_json


def resolve_capcut_fix_bat_path(candidate: str | Path | None = None) -> Path:
    '''Resolve a valid fix_shark.bat path with intelligent auto-detection.'''
    (bundled_bat, _json) = get_bundled_capcut_fix_paths()
    if candidate:

        try:
            p = Path(candidate).expanduser()
            if p.is_file():
                return p
        except Exception:
            pass

    return bundled_bat


def load_device_source_preferences():
    '''Return the user-selected profile source without exposing device data.'''
    defaults = {
        'use_backup': False,
        'backup_path': '' }
    path = _DEVICE_SOURCE_PATH
    if not path.is_file():
        return defaults

    try:
        data = json.loads(path.read_text(encoding = 'utf-8'))
        if not isinstance(data, dict):
            return defaults
        raw_backup = str(data.get('backup_path') or '').strip()
        return {
            'use_backup': bool(data.get('use_backup', False)),
            'backup_path': raw_backup }
    except Exception as exc:
        logger.warning('Không đọc được lựa chọn Device CapCut: %s', exc)
        return defaults


def save_device_source_preferences(*, use_backup, backup_path):
    '''Persist whether to use one explicit, user-selected profile file.'''
    path = _DEVICE_SOURCE_PATH
    path.parent.mkdir(parents = True, exist_ok = True)
    data = {
        'use_backup': bool(use_backup),
        'backup_path': str(backup_path).strip() }
    path.write_text(json.dumps(data, ensure_ascii = False, indent = 2) + '\n', encoding = 'utf-8')
    return path


def load_device_overrides():
    path = _DEVICE_PATH
    if not path.is_file():
        return { }

    try:
        data = json.loads(path.read_text(encoding = 'utf-8'))
        if isinstance(data, dict):
            return data
        return { }
    except Exception as exc:
        logger.warning('Không đọc được capcut_device.json: %s', exc)
        return { }


def load_selected_device_overrides() -> dict[str, Any]:
    '''Load the active profile; each new request sees auto-fix JSON updates.'''
    preferences = load_device_source_preferences()
    if not preferences['use_backup']:
        return load_device_overrides()

    raw_path = preferences.get('backup_path')
    backup_path = Path(raw_path).expanduser() if raw_path else None
    if backup_path is None or not backup_path.is_file():

        resolved = resolve_capcut_device_path(backup_path)
        if resolved.is_file():
            logger.info('Tự động khôi phục đường dẫn Device JSON hợp lệ trên máy này: %s', resolved)
            save_device_source_preferences(use_backup = preferences['use_backup'], backup_path = resolved)
            backup_path = resolved
        else:
            raise RuntimeError(f'''Đã bật Device dự phòng nhưng không tìm thấy file JSON đã chọn: {backup_path}''')

    try:
        # Device dự phòng được auto-fix ghi đè thường xuyên -> đọc lại mỗi lần cần.
        data = json.loads(backup_path.read_text(encoding = 'utf-8-sig'))
    except Exception as exc:
        raise RuntimeError(f'Không đọc được Device dự phòng: {exc}') from exc
    if not isinstance(data, dict):
        raise RuntimeError('Device dự phòng phải là một file JSON object.')
    logger.info('CapCut dùng Device dự phòng đã chọn: %s', backup_path)
    return data


def save_device_overrides(data: dict[str, Any]) -> Path:
    path = _DEVICE_PATH
    path.parent.mkdir(parents = True, exist_ok = True)
    # Bỏ key nội bộ (_) và ghi chú (comment/source) trước khi ghi file.
    clean = {
        k: v
        for k, v in data.items()
        if not str(k).startswith('_') and k not in {'comment', 'source'}}
    path.write_text(json.dumps(clean, ensure_ascii = False, indent = 2) + '\n', encoding = 'utf-8')
    return path


def _file_stamp(path: Path) -> tuple[str, int, int]:
    '''Cheap identity used to invalidate in-memory config/cache state.'''

    try:
        stat = path.stat()
        return (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return (str(path), -1, -1)


def _active_device_stamp() -> tuple[Any, ...]:
    preferences = load_device_source_preferences()
    active = (Path(preferences['backup_path']).expanduser()
              if preferences['use_backup'] and preferences['backup_path'] else _DEVICE_PATH)
    return (bool(preferences['use_backup']), _file_stamp(_DEVICE_SOURCE_PATH), _file_stamp(active))


def extract_device_from_local_capcut(*, save: bool = True) -> dict[str, Any]:
    '''Đọc device_id / iid thật từ log CapCut Pro PC trên máy.

    CapCut Pro lưu request URL trong ``%LOCALAPPDATA%\\CapCut\\User Data\\Log``.
    Dùng device đó thay DEFAULT_DEVICE public (hay bị shark block).
    '''
    raise NotImplementedError('chưa khôi phục từ bytecode: capcut_tts_engine.extract_device_from_local_capcut')


def get_device() -> dict[str, Any]:
    '''Merge DEFAULT_DEVICE with the profile source chosen before the job.'''
    global _device_cache_stamp, _device_cache_value

    from app.services import capcut_common_task_client as cc

    stamp_before = _active_device_stamp()
    with _device_cache_lock:
        if _device_cache_value is not None and _device_cache_stamp == stamp_before:
            return deepcopy(_device_cache_value)

    device = deepcopy(cc.DEFAULT_DEVICE)
    overrides = load_selected_device_overrides()
    if not overrides:

        try:
            overrides = extract_device_from_local_capcut(save = True)
        except Exception as exc:
            logger.warning(
                'Chưa có %s và không auto-extract được (%s). Dùng DEFAULT_DEVICE (dễ shark block). '
                'Mở CapCut Pro rồi Cài đặt → «Lấy từ CapCut Pro».', _DEVICE_PATH, exc)

    if overrides:
        # Chỉ nhận giá trị vô hại; key nội bộ và ghi chú bị loại.
        device.update({
            k: (str(v) if not isinstance(v, (dict, list)) else v)
            for k, v in overrides.items()
            if not str(k).startswith('_') and k not in {'comment', 'source'}})

    with _device_cache_lock:
        _device_cache_stamp = _active_device_stamp()
        _device_cache_value = deepcopy(device)
    return deepcopy(device)


def _load_voice_catalog():
    '''Đọc ``capcut_voices.json`` — snapshot danh sách giọng CapCut cloud.

    Mỗi phần tử: ``display_name, voice_type, resource_id, lang, lan, captured_at``.
    Khoá lạ bị bỏ qua nên có thể thêm ``verified`` / ``note`` để tra cứu.
    Thiếu file thì trả về [] để UI còn rơi xuống giọng mặc định.
    '''
    if not _VOICES_PATH.is_file():
        return []

    try:
        data = json.loads(_VOICES_PATH.read_text(encoding = 'utf-8-sig'))
    except Exception as exc:
        logger.warning('Không đọc được capcut_voices.json: %s', exc)
        return []
    if isinstance(data, dict):
        data = data.get('voices') or data.get('data') or []
    return data if isinstance(data, list) else []


def voice_lang(item):
    '''Mã ngôn ngữ của một phần tử catalog (``lang`` đầy đủ hoặc ``lan`` viết tắt).'''
    return str(item.get('lang') or item.get('lan') or '').strip()


def _lang_matches(have, want):
    '''Lọc lỏng: ``vi`` khớp với ``vi-VN`` và ngược lại.'''
    if not want:
        return True
    have = str(have or '').casefold()
    want = str(want).casefold()
    if not have:
        return False
    return want in have or have in want or have.startswith(want.split('-')[0])


def list_capcut_voices(*, lang = 'vi-VN'):
    '''Return ``(label, voice_key)`` for UI OptionMenu.

    Label: ``Display Name | voice_type:resource_id``
    voice_key: ``voice_type:resource_id``
    '''
    result = []
    seen = set()
    for item in _load_voice_catalog():
        if not isinstance(item, dict):
            continue
        voice_type = str(item.get('voice_type') or '').strip()
        resource_id = str(item.get('resource_id') or '').strip()
        if not voice_type or not resource_id:
            continue
        if not _lang_matches(voice_lang(item), lang):
            continue
        key = f'''{voice_type}:{resource_id}'''
        if key in seen:
            continue
        seen.add(key)
        name = str(item.get('display_name') or voice_type).strip()
        result.append((f'''{name} | {key}''', key))
    if not result:
        result.append((DEFAULT_VOICE_LABEL, f'''{DEFAULT_VOICE_TYPE}:{DEFAULT_RESOURCE_ID}'''))
    return result


def list_capcut_voices_all():
    '''All languages from catalog (for advanced use).'''
    return list_capcut_voices(lang = None)


def parse_voice_key(voice = None):
    '''Tách ``(voice_type, resource_id)`` từ khoá giọng.

    Nhận cả ba dạng: ``BV074_streaming``, ``voice_type:resource_id`` và nhãn UI
    đầy đủ ``Tên hiển thị | voice_type:resource_id``. Thiếu resource_id thì dùng
    ``DEFAULT_RESOURCE_ID``.
    '''
    raw = str(voice or '').strip()
    if '|' in raw:
        raw = raw.rsplit('|', 1)[-1].strip()
    if ':' in raw:
        voice_type, _, resource_id = raw.partition(':')
        voice_type = voice_type.strip()
        resource_id = resource_id.strip()
        if voice_type and resource_id:
            return (voice_type, resource_id)
    return (raw or DEFAULT_VOICE_TYPE, DEFAULT_RESOURCE_ID)


def normalize_rate(speed: str | float | None) -> str:

    try:
        rate = float(speed if speed is not None else 1.0)
    except (TypeError, ValueError):
        rate = 1.0
    rate = max(0.5, min(2.0, rate))
    text = f'{rate:.2f}'.rstrip('0').rstrip('.')
    if '.' not in text:
        text = f'{text}.0'
    return text


def normalize_cache_text(text: str) -> str:
    '''Match CapCut's spoken input without erasing meaningful punctuation.'''
    value = (text or '').replace('\r', ' ').replace('\n', ' ')
    value = re.sub('<[^>]+>', ' ', value)
    value = re.sub('\\{[^}]*\\}', ' ', value)
    return re.sub('\\s+', ' ', value).strip()


def is_speakable_text(text: str) -> bool:
    '''Kiểm tra xem văn bản có chứa ít nhất một ký tự chữ hoặc số để phát âm hay không.'''
    if not text:
        return False
    cleaned = re.sub('<[^>]+>', ' ', text)
    cleaned = re.sub('\\{[^}]*\\}', ' ', cleaned)
    return bool(re.search('[\\w\\d]', cleaned, flags = re.UNICODE))


def _make_silence_audio(output: Path, duration_s: float = 0.2) -> Path:
    '''Tạo file audio im lặng (mp3 hoặc wav) khi câu thoại không có nội dung phát âm.'''
    import shutil
    import subprocess

    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)
    ff = shutil.which('ffmpeg') or 'ffmpeg'
    dur = max(0.05, float(duration_s))

    cmd = [
        ff,
        '-y',
        '-f',
        'lavfi',
        '-i',
        'anullsrc=r=44100:cl=mono',
        '-t',
        f'''{dur:.3f}''',
        str(output)]
    try:
        p = subprocess.run(
            cmd,
            capture_output = True,
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode == 0 and output.is_file() and output.stat().st_size >= 32:
            return output
    except Exception as exc:
        logger.debug('ffmpeg anullsrc không thành công: %s, dùng byte fallback', exc)

    # Không có ffmpeg (hoặc ffmpeg fail): tự dựng khung WAV/MP3 im lặng tối thiểu.
    if output.suffix.lower() in ('.wav', '.wave'):
        num_samples = int(44100 * dur)
        data_size = num_samples * 2
        wav_bytes = bytearray(b'RIFF')
        wav_bytes.extend((data_size + 36).to_bytes(4, 'little'))
        wav_bytes.extend(
            b'WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data')
        wav_bytes.extend(data_size.to_bytes(4, 'little'))
        wav_bytes.extend(b'\x00' * data_size)
        output.write_bytes(wav_bytes)
    else:
        output.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 413)
    return output



# Giả lập trình duyệt khi gọi curl_curl/requests; CapCut chặn UA Python mặc định.
_CURL_IMPERSONATE = 'chrome131'
_MIN_SUBMIT_INTERVAL_S = 0.45
_last_submit_mono = 0.0
_submit_pace_lock = threading.Lock()
_edge_fallback_active = False
_edge_fallback_reason = ''
_FIX_SHARK_EVERY_CUES = 90
_FIX_SHARK_STALL_S = 60.0
_FIX_SHARK_MIN_INTERVAL_S = 60.0


class _CapCutAutoFixApplied(RuntimeError):
    '''Internal signal: reload the selected device and resubmit this cue.'''


class _FixSharkBatchRunner:
    '''Run one user-selected recovery batch per cue milestone/problem.

    The instance belongs to one CapCut TTS render, so counters and duplicate
    guards never leak into the next job.  It does not inspect log text: the
    request timer and the caught provider exception are more reliable signals.
    '''



    def __init__(self, *, enabled: bool, path: str | Path, device_path: str | Path = '',
                 every_cues: int = _FIX_SHARK_EVERY_CUES, stall_s: float = _FIX_SHARK_STALL_S,
                 min_interval_s: float = _FIX_SHARK_MIN_INTERVAL_S) -> None:
        self.enabled = bool(enabled)
        self.path = Path(path).expanduser() if str(path).strip() else Path()
        self.device_path = (
            Path(device_path).expanduser() if str(device_path).strip() else None)
        self.every_cues = max(1, int(every_cues))
        self.stall_s = max(1.0, float(stall_s))
        self.min_interval_s = max(0.0, float(min_interval_s))
        self.success_count = 0
        self._results = {}
        self._lock = threading.RLock()
        self._last_run_mono = 0.0


    def start_watchdog(self, text: str,
                       cancel_event: threading.Event | None = None) -> threading.Timer | None:
        '''Chạy batch auto-fix khi một request CapCut treo quá ``stall_s``.

        Timer là daemon nên không giữ tiến trình sống; đã cancel thì bỏ qua.
        '''
        if not self.enabled:
            return None

        def on_stall() -> None:
            if cancel_event is not None and cancel_event.is_set():
                return
            self.run_for_problem(
                text,
                f'request CapCut chờ quá {int(self.stall_s)} giây')

        timer = threading.Timer(
            self.stall_s,
            on_stall)
        timer.daemon = True
        timer.start()
        return timer


    def run_for_problem(self, text: str, detail: str, *, cue_key: str = '') -> bool:
        key = f'problem:{cue_key or text.strip()}'
        return self._run_once(key, f'CapCut TTS bị nghẽn · {detail}')


    def on_success(self, text: str = '', *, cue_key: str = '') -> None:
        if not self.enabled:
            return
        with self._lock:
            self.success_count += 1
            count = self.success_count
            problem_ran_for_same_cue = bool(
                (cue_key or text.strip())
                and self._results.get(f'problem:{cue_key or text.strip()}'))

        if count % self.every_cues == 0:
            if problem_ran_for_same_cue:
                # Cue này vừa được auto-fix vì sự cố thì mốc đếm không chạy nữa:
                # gọi liên tiếp 2 batch trong vài giây chỉ tổ bị chặn thêm.
                with self._lock:
                    self._results[f'milestone:{count}'] = True
                logger.info(
                    'Bỏ lần auto-fix mốc %s vì cùng cue vừa chạy batch do sự cố', count)
                return
            self._run_once(
                f'milestone:{count}',
                f'đã tạo thành công {count} cue CapCut TTS')


    def _run_once(self, key: str, reason: str) -> bool:
        if not self.enabled:
            return False
        with self._lock:
            if key in self._results:
                return self._results[key]
            since_last = time.monotonic() - self._last_run_mono
            if self._last_run_mono and since_last < self.min_interval_s:
                logger.info('Bỏ auto-fix CapCut vì lần trước mới chạy %.0fs trước (giới hạn %.0fs)',
                            since_last, self.min_interval_s)
                self._results[key] = False
                return False
            self._results[key] = False
            self._last_run_mono = time.monotonic()
            result = self._execute(reason)
            self._results[key] = result
            return result

    @staticmethod
    def _profile_snapshot(path: Path) -> tuple[Path, tuple[str, str, str] | None, int]:
        '''Return one Device JSON's three IDs and mtime for BAT validation.'''

        if not path.is_file():
            return (path, None, 0)

        try:
            data = json.loads(path.read_text(encoding = 'utf-8-sig'))
            if not isinstance(data, dict):
                return (path, None, path.stat().st_mtime_ns)
            ids = tuple(str(data.get(key) or '').strip() for key in ('device_id', 'iid', 'tdid'))
            return (path, ids, path.stat().st_mtime_ns)
        except Exception:
            return (path, None, path.stat().st_mtime_ns)

    @classmethod
    def _active_profile_snapshot(cls) -> tuple[Path, tuple[str, str, str] | None, int]:
        '''Return the current selected Device JSON's IDs and mtime.'''
        preferences = load_device_source_preferences()
        path = (Path(preferences['backup_path']).expanduser()
                if preferences['use_backup'] and preferences['backup_path'] else _DEVICE_PATH)
        return cls._profile_snapshot(path)

    @staticmethod
    def _batch_device_json_paths(batch: Path) -> list[Path]:
        '''Return literal JSON paths declared with ``set NAME=...`` in a BAT.'''

        try:
            content = batch.read_text(encoding = 'utf-8-sig', errors = 'replace')
        except OSError as exc:
            logger.warning('Không đọc được đường dẫn Device JSON trong %s: %s', batch, exc)
            return []
        variables = {}
        assignment = re.compile(
            '^\\s*set\\s+(?:/a\\s+)?"?([A-Za-z_][A-Za-z0-9_]*)"?\\s*=\\s*(.*?)\\s*$',
            re.IGNORECASE)
        for line in content.splitlines():
            match = assignment.match(line)
            if not match:
                continue
            (name, value) = match.groups()
            variables[name.casefold()] = value.strip().strip('"')

        def expand_batch_variables(value: str) -> str:
            return re.sub('%([^%]+)%',
                          lambda match: variables.get(match.group(1).casefold(), match.group(0)),
                          value)

        paths = []
        for value in variables.values():
            expanded = os.path.expandvars(expand_batch_variables(value)).strip().strip('"')
            if not expanded.casefold().endswith('.json'):
                continue
            candidate = Path(expanded).expanduser()
            if not candidate.is_absolute():
                candidate = batch.parent / candidate

            try:
                candidate = candidate.resolve()
            except OSError:
                pass

            if candidate not in paths:
                paths.append(candidate)
        return paths

    @staticmethod
    def _valid_device_ids(ids: tuple[str, str, str] | None) -> bool:
        return bool(ids and all(re.fullmatch('\\d{19,20}', value) for value in ids))


    def _execute(self, reason: str) -> bool:
        batch = resolve_capcut_fix_bat_path(self.path).resolve()
        if not batch.is_file():
            logger.error('Không chạy fix shark: không tìm thấy file BAT: %s', batch)
            return False
        if batch.suffix.casefold() not in {'.bat', '.cmd'}:
            logger.error('Không chạy fix shark: file không phải .bat/.cmd: %s', batch)
            return False
        if os.name != 'nt':
            logger.error('Không chạy fix shark: Windows batch chỉ hỗ trợ trên Windows')
            return False

        (before_path, before_ids, before_mtime) = self._active_profile_snapshot()
        # Profile nào BAT có thể ghi?  File người dùng chọn + mấy đường dẫn JSON
        # khai báo trong BAT + device.json nằm cạnh BAT.
        batch_profile_paths = (
            [self.device_path.resolve()]
            if self.device_path is not None and self.device_path.is_file()
            else self._batch_device_json_paths(batch))
        companion_json = (batch.parent / 'device.json').resolve()
        if companion_json not in batch_profile_paths:
            batch_profile_paths.append(companion_json)
        # Chụp trạng thái trước khi chạy để biết file nào thực sự đổi.
        batch_profiles_before = {path: self._profile_snapshot(path)
                                 for path in batch_profile_paths}
        logger.warning('CapCut TTS auto-fix → chạy %s (%s)', batch, reason)
        comspec = os.environ.get('COMSPEC') or 'cmd.exe'
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

        try:
            completed = subprocess.run(
                [comspec, '/d', '/c', 'call', str(batch)],
                cwd = str(batch.parent),
                capture_output = True,
                text = True,
                encoding = 'utf-8',
                errors = 'replace',
                timeout = 120,
                check = False,
                creationflags = creationflags)
        except Exception as exc:
            logger.error('Chạy fix shark thất bại: %s', exc)
            return False
        output = ' '.join(
            part.strip()
            for part in (completed.stdout or '', completed.stderr or '')
            if part.strip())
        (after_path, after_ids, after_mtime) = self._active_profile_snapshot()
        profile_valid = self._valid_device_ids(after_ids)
        # Chỉ nhận khi đúng profile đang dùng đổi và ID mới còn hợp lệ.
        profile_updated = bool((after_path == before_path)
                               and profile_valid
                               and (after_ids != before_ids or after_mtime != before_mtime))
        if profile_updated:
            if completed.returncode != 0:
                logger.warning(
                    'fix_shark.bat trả mã %s nhưng Device JSON đã cập nhật hợp lệ; tiếp tục dùng profile mới: %s',
                    completed.returncode,
                    after_path)
            else:
                logger.info('fix_shark.bat đã cập nhật Device JSON hợp lệ: %s', after_path)
            return True
        for (profile_path, (_, ids_before, mtime_before)) in batch_profiles_before.items():
            (candidate_path, candidate_ids, candidate_mtime) = self._profile_snapshot(profile_path)
            candidate_updated = (self._valid_device_ids(candidate_ids)
                                  and (candidate_ids != ids_before
                                       or candidate_mtime != mtime_before))
            if not candidate_updated:
                continue
            save_device_source_preferences(use_backup = True, backup_path = candidate_path)
            logger.info(
                'fix_shark.bat đã cập nhật Device JSON theo đường dẫn trong BAT; đã tự chọn profile này: %s',
                candidate_path)
            return True
        if completed.returncode != 0:
            logger.error(
                'fix_shark.bat trả mã lỗi %s: %s',
                completed.returncode,
                output[-500:] or 'không có output')
            return False
        logger.error(
            'fix_shark.bat chạy xong nhưng Device JSON không được cập nhật hợp lệ (%s): %s',
            after_path,
            output[-500:] or 'không có output')
        return False


def reset_edge_fallback() -> None:
    '''Gọi đầu mỗi job render nếu muốn thử lại CapCut.'''
    global _edge_fallback_active, _edge_fallback_reason
    _edge_fallback_active = False
    _edge_fallback_reason = ''


def is_edge_fallback_active() -> bool:
    return _edge_fallback_active


def _activate_edge_fallback(reason: str) -> None:
    global _edge_fallback_active, _edge_fallback_reason

    if not _edge_fallback_active:
        logger.warning(
            'CapCut TTS → tự chuyển Edge TTS (device_id vẫn OK; CapCut shark/rate-limit). Lý do: %s',
            reason[:200])
    _edge_fallback_active = True
    _edge_fallback_reason = reason


def _is_shark_or_busy(err: BaseException | str) -> bool:
    msg = str(err).casefold()

    return any(k in msg for k in ('shark', 'ret=-6', 'ret=1014', 'system busy',
                                  'chặn request', 'http 429'))


def _is_retryable_strict_tts_error(err: BaseException | str) -> bool:
    '''Return whether strict CapCut mode should wait and retry this error.

    CapCut often accepts ``tts-new`` then marks its own queued task as
    ``failed`` without returning shark/ret=-6.  In a long render that is the
    same practical condition as a temporary block: no audio exists yet, so
    strict mode must wait for CapCut rather than turn that cue into silence.
    This broader classification is intentionally used *only* when the user
    chose strict CapCut mode; the normal fallback behaviour is unchanged.
    '''
    msg = str(err).casefold()
    queued_task_failed = 'capcut tts' in msg and any(
        marker in msg for marker in ('failed', 'fail', 'timeout', 'timed out', 'hết thời gian'))

    return (_is_shark_or_busy(err) or queued_task_failed
            or any(marker in msg for marker in (
                'capcut tts thất bại:', 'capcut tts timeout', 'capcut tts hết thời gian',
                'http 429', 'http 500', 'http 502', 'http 503', 'http 504',
                'connection reset', 'connection aborted', 'connection refused',
                'read timed out', 'connect timeout', 'connection timeout',
                'remote end closed', 'temporary failure', 'name resolution',
                'network is unreachable', 'winerror 10054', 'winerror 10060')))


def _edge_voice_for_capcut(voice: str | None) -> str:
    '''Map giọng CapCut UI → Edge Neural (gần nhất).'''
    raw = (voice or '').casefold()

    if any(k in raw for k in ('nam', 'male', 'thanh niên', 'bv075', 'bv070', 'bv107',
                              'man_', 'male_')):
        return 'vi-VN-NamMinhNeural'
    return 'vi-VN-HoaiMyNeural'


def _pace_tts_submit() -> None:
    '''Sleep ngắn nếu submit quá dày (CapCut hay shark sau ~80–100 request).'''
    global _last_submit_mono

    with _submit_pace_lock:
        now = time.monotonic()
        wait = _MIN_SUBMIT_INTERVAL_S - (now - _last_submit_mono)
        if wait > 0:
            time.sleep(wait)
        _last_submit_mono = time.monotonic()


def _require_requests():
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError('Chưa cài requests. Chạy: pip install requests') from exc
    return requests


def _http_post(url: str, headers: dict[str, str], body_text: str,
               *, timeout: int = 60) -> tuple[int, str]:
    '''POST body; trả (status_code, response_text). Ưu tiên TLS impersonation.

    curl_cffi (ngân hàng TLS Chrome) đi trước vì CapCut chặn fingerprint của
    requests thuần; chỉ rơi về requests khi curl_cffi chưa cài hoặc lỗi mạng.
    Session gắn theo thread để song song hoá mà không shared socket.
    '''
    data_bytes = body_text.encode('utf-8')

    try:
        from curl_cffi import requests as creq

        session = getattr(_http_thread_local, 'curl_session', None)
        if session is None:
            session = creq.Session()
            _http_thread_local.curl_session = session
        started = time.perf_counter()
        resp = session.post(
            url,
            headers = headers,
            data = data_bytes,
            timeout = timeout,
            impersonate = _CURL_IMPERSONATE)
        logger.debug(
            'CapCut HTTP session POST %.0fms status=%s',
            (time.perf_counter() - started) * 1000,
            resp.status_code)
        return (int(resp.status_code), resp.text or '')
    except ImportError:
        logger.debug('curl_cffi chưa cài — fallback requests (dễ shark hơn)')
    except Exception as exc:
        logger.warning('curl_cffi POST fail, fallback requests: %s', exc)

    requests = _require_requests()
    session = getattr(_http_thread_local, 'requests_session', None)
    if session is None:
        session = requests.Session()
        _http_thread_local.requests_session = session
    resp = session.post(url, headers = headers, data = data_bytes, timeout = timeout)
    return (int(resp.status_code), resp.text or '')


def _post_json(url: str, headers: dict[str, str], body_text: str,
               *, timeout: int = 60) -> dict[str, Any]:
    (status, text) = _http_post(url, headers, body_text, timeout = timeout)

    try:
        data = json.loads(text) if text else { }
    except Exception as exc:
        raise RuntimeError(f'CapCut HTTP {status} non-JSON: {(text or "")[:400]}') from exc
    if status >= 400:
        raise RuntimeError(f'CapCut HTTP {status}: {data}')
    if isinstance(data, dict):
        return data
    return {'data': data}


def _get_bytes(url: str, *, timeout: int = 120,
               headers: dict[str, str] | None = None) -> bytes:
    '''GET binary (audio URL). Ưu tiên curl_cffi.'''
    hdrs = headers or { }

    try:
        from curl_cffi import requests as creq

        session = getattr(_http_thread_local, 'curl_session', None)
        if session is None:
            session = creq.Session()
            _http_thread_local.curl_session = session
        resp = session.get(url, headers = hdrs, timeout = timeout,
                           impersonate = _CURL_IMPERSONATE)
        if resp.status_code >= 400:
            raise RuntimeError(f'HTTP {resp.status_code}: {(resp.text or "")[:200]}')
        return bytes(resp.content or b'')
    except ImportError:
        pass
    except Exception as exc:
        logger.warning('curl_cffi GET fail, fallback requests: %s', exc)

    requests = _require_requests()
    session = getattr(_http_thread_local, 'requests_session', None)
    if session is None:
        session = requests.Session()
        _http_thread_local.requests_session = session
    resp = session.get(url, headers = hdrs, timeout = timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f'HTTP {resp.status_code}: {(resp.text or "")[:200]}')
    return bytes(resp.content or b'')



def _check_api_ret(data: dict[str, Any], label: str) -> None:
    ret = str(data.get('ret') if data.get('ret') is not None else (data.get('code') or '0'))
    if ret in {'', 'ok', '0', 'success'}:
        return
    errmsg = str(data.get('errmsg') or data.get('message') or data.get('msg') or '').strip()
    if 'shark' in errmsg.casefold() or ret == '-6':
        raise RuntimeError(
            f'CapCut chặn request (shark block / ret={ret}). Device profile có thể vẫn đúng; '
            f'CapCut đang chặn tạm traffic TTS (thường sau nhiều câu liên tục hoặc fingerprint). '
            f'Chi tiết: {errmsg or data}')
    raise RuntimeError(f'CapCut {label} lỗi ret={ret}: {errmsg or data}')


def _first_task(data: dict[str, Any]) -> dict[str, Any]:
    tasks = ((data.get('data') or {}).get('tasks') if isinstance(data.get('data'), dict) else None)
    if not tasks and isinstance(data.get('tasks'), list):
        tasks = data['tasks']
    if not tasks:
        failed = None
        if isinstance(data.get('data'), dict):
            failed = data['data'].get('failed_tasks')
        raise RuntimeError(f'CapCut không trả task: {failed or data}')
    task = tasks[0]
    if not isinstance(task, dict):
        raise RuntimeError(f'CapCut task không hợp lệ: {task}')
    return task


def submit_tts(texts: list[str], *, voice_type: str = 'BV074_streaming',
               resource_id: str = '7102355709945188865', rate: str = '1.0',
               device: dict[str, Any] | None = None) -> tuple[str, str, str]:
    '''Create TTS task → ``(task_id, token, bind_id)``.

    Dấu ``sign``/``device-time`` phải tính lại cho *từng* lần thử vì nonce gắn
    với timestamp: retry với header cũ là CapCut chặn ngay.
    '''
    from app.services import capcut_common_task_client as cc

    clean = [re.sub('\\s+', ' ', (t or '').strip()) for t in texts]
    clean = [t for t in clean if t]
    if not clean:
        raise ValueError('text rỗng — không TTS được.')

    device = device or get_device()
    (babi, body) = cc.tts_new_body(clean, voice_type, resource_id, rate, device)
    path = '/lv/v1/common_task/new'
    query = cc.common_query(device, babi, include_region = True)
    body_text = cc.compact_json(body)
    url = cc.BASE + path + '?' + cc.urlencode(query)
    headers = cc.base_headers(device, body_text, appid = True)
    lower = {k.lower(): v for k, v in headers.items()}
    if 'sign' not in lower:
        headers['sign'] = cc.make_sign_header(url, device['appvr'], lower['device-time'],
                                              device['tdid'])

    # Nhịp gửi + retry shark: lỗi tạm thời thì đợi lâu dần, không biến câu thoại
    # thành im lặng chỉ vì CapCut chắn một request.
    _pace_tts_submit()
    last_err = None
    data = { }
    retry_delays_s = (0.0, 1.5, 6.0)
    max_attempts = len(retry_delays_s)
    for attempt in range(max_attempts):
        if attempt:
            delay = retry_delays_s[attempt]
            logger.warning('CapCut TTS retry %s/%s sau %.1fs: %s',
                           attempt + 1,
                           max_attempts,
                           delay,
                           last_err)
            time.sleep(delay)
            headers = cc.base_headers(device, body_text, appid = True)
            lower = {k.lower(): v for k, v in headers.items()}
            headers['sign'] = cc.make_sign_header(
                url, device['appvr'], lower['device-time'], device['tdid'])

        try:
            data = _post_json(url, headers, body_text)
            _check_api_ret(data, 'tts-new')
            last_err = None
            break
        except RuntimeError as exc:
            last_err = exc
            if _is_shark_or_busy(exc) and attempt + 1 < max_attempts:
                continue
            raise
    if last_err is not None:
        raise last_err
    task = _first_task(data)
    task_id = str(task.get('id') or '').strip()
    token = str(task.get('token') or '').strip()
    bind_id = str(body.get('bind_id') or task.get('bind_id') or '').strip()
    if not task_id or not token:
        raise RuntimeError(f'CapCut TTS thiếu id/token: {task}')
    logger.info('CapCut TTS submitted id=%s status=%s', task_id, task.get('status'))
    return (task_id, token, bind_id)


def query_common_task(task_id: str, token: str, *, req_key: str, bind_id: str = '',
                      device: dict[str, Any] | None = None, appid: bool = True,
                      label: str = 'query') -> dict[str, Any]:
    '''POST common_task/query; trả payload gốc đã kiểm tra ``ret``.

    Dùng chung cho TTS lẫn STT: chỉ ``req_key`` và sign là khác nhau.
    '''
    from app.services import capcut_common_task_client as cc

    device = device or get_device()
    body = cc.query_body(task_id, token, req_key, bind_id)
    path = '/lv/v1/common_task/query'
    query = cc.common_query(device, None, include_region = False)
    body_text = cc.compact_json(body)
    url = cc.BASE + path + '?' + cc.urlencode(query)
    headers = cc.base_headers(device, body_text, appid = appid)
    lower = {k.lower(): v for k, v in headers.items()}
    if 'sign' not in lower:
        headers['sign'] = cc.make_sign_header(url, device['appvr'], lower['device-time'],
                                              device['tdid'])
    data = _post_json(url, headers, body_text)
    _check_api_ret(data, label)
    return data


def query_tts(task_id: str, token: str, *, bind_id: str = '',
              device: dict[str, Any] | None = None) -> dict[str, Any]:
    return query_common_task(
        task_id,
        token,
        req_key = 'sami_text_to_speech',
        bind_id = bind_id,
        device = device,
        appid = True,
        label = 'tts-query')


def query_stt(task_id: str, token: str, *, bind_id: str = '',
              device: dict[str, Any] | None = None) -> dict[str, Any]:
    return query_common_task(
        task_id,
        token,
        req_key = 'cc_audio_subtitle_asr',
        bind_id = bind_id,
        device = device,
        appid = False,
        label = 'stt-query')


def poll_common_task(task_id: str, token: str, *, req_key: str, bind_id: str = '',
                     device: dict[str, Any] | None = None, timeout_s: float = 180.0,
                     interval_s: float = 1.2, appid: bool = True, label: str = 'task',
                     ready_fn: Callable[[dict[str, Any]], bool] | None = None,
                     status_callback: Callable[[float, str], None] | None = None,
                     cancel_event: threading.Event | None = None) -> dict[str, Any]:
    '''Poll until success/fail; return the finished task dict.

    ``ready_fn`` cho phép dừng sớm khi payload đã đủ (audio/utterances xuất hiện
    trước khi CapCut flip status).  Với TTS thì nhảy bậc wait: ngắn dần về đầu
    để câu ngắn không bị cộng thêm 1s chờ.
    '''
    device = device or get_device()
    started_at = time.monotonic()
    deadline = started_at + max(10.0, timeout_s)
    last_status = ''
    while time.monotonic() < deadline:
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError(f'Đã dừng khi đang chờ CapCut {label}.')
        data = query_common_task(
            task_id,
            token,
            req_key = req_key,
            bind_id = bind_id,
            device = device,
            appid = appid,
            label = f'{label}-query')
        task = _first_task(data)
        status = str(task.get('status') or '').strip().casefold()
        if status != last_status:
            logger.info('CapCut %s poll id=%s status=%s', label, task_id, status)
            last_status = status
        if status_callback is not None:
            status_callback(max(0.0, time.monotonic() - started_at), status or 'waiting')
        ready = ready_fn(task) if ready_fn else False
        if status in _SUCCESS or ready:
            return task
        if status in _FAILED:
            err = task.get('errmsg') or task.get('message') or task.get('payload') or status
            raise RuntimeError(f'CapCut {label} thất bại: {err}')

        elapsed_s = max(0.0, time.monotonic() - started_at)
        if label == 'TTS':
            wait_s = 0.55 if elapsed_s < 2.5 else (1.0 if elapsed_s < 10.0 else 2.0)
        else:
            wait_s = interval_s
        if cancel_event is not None:
            if cancel_event.wait(wait_s):
                raise RuntimeError(f'Đã dừng khi đang chờ CapCut {label}.')
        else:
            time.sleep(wait_s)
    raise RuntimeError(f'CapCut {label} timeout sau {int(timeout_s)}s '
                       f'(status={last_status or "?"})')


def poll_tts(task_id: str, token: str, *, bind_id: str = '',
             device: dict[str, Any] | None = None, timeout_s: float = 120.0,
             interval_s: float = 1.0,
             status_callback: Callable[[float, str], None] | None = None,
             cancel_event: threading.Event | None = None) -> dict[str, Any]:
    return poll_common_task(
        task_id,
        token,
        req_key = 'sami_text_to_speech',
        bind_id = bind_id,
        device = device,
        timeout_s = timeout_s,
        interval_s = interval_s,
        appid = True,
        label = 'TTS',
        ready_fn = _payload_has_audio,
        status_callback = status_callback,
        cancel_event = cancel_event)


def poll_stt(task_id: str, token: str, *, bind_id: str = '',
             device: dict[str, Any] | None = None, timeout_s: float = 300.0,
             interval_s: float = 1.5) -> dict[str, Any]:
    return poll_common_task(
        task_id,
        token,
        req_key = 'cc_audio_subtitle_asr',
        bind_id = bind_id,
        device = device,
        timeout_s = timeout_s,
        interval_s = interval_s,
        appid = False,
        label = 'STT',
        ready_fn = _payload_has_utterances)



def _parse_task_payload(task: dict[str, Any]) -> Any:
    payload = task.get('payload')
    if payload is None:
        return None
    if isinstance(payload, str):

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload
    return payload


def _payload_has_audio(task: dict[str, Any]) -> bool:
    obj = _parse_task_payload(task)
    if not isinstance(obj, dict):
        return False

    try:
        _find_audio_ref(obj)
        return True
    except Exception:
        return False


def _payload_has_utterances(task: dict[str, Any]) -> bool:
    obj = _parse_task_payload(task)
    if not isinstance(obj, dict):
        return False

    try:
        return bool(_find_utterances(obj))
    except Exception:
        return False


def _looks_like_url(value: str) -> bool:
    v = (value or '').strip()
    if not v.startswith(('http://', 'https://')):
        return False

    try:
        p = urlparse(v)
        return bool(p.netloc)
    except Exception:
        return False


def _looks_like_b64_audio(value: str) -> bool:
    v = (value or '').strip()
    if v.startswith('data:audio'):
        return True
    if len(v) < 200 or _looks_like_url(v):
        return False
    sample = v[:80].replace('\n', '').replace('\r', '')
    return bool(re.fullmatch('[A-Za-z0-9+/=_-]+', sample))


def _find_audio_ref(obj: Any, depth: int = 0) -> tuple[str, str]:
    '''Walk nested dict/list → ``("url"|"b64", value)``.'''
    if depth > 12:
        raise RuntimeError('payload quá sâu')
    if isinstance(obj, dict):

        for list_key in ('audio_list', 'audios', 'results', 'data_list', 'utterances'):
            items = obj.get(list_key)
            if not isinstance(items, list):
                continue
            for item in items:

                try:
                    return _find_audio_ref(item, depth + 1)
                except RuntimeError:
                    continue

        for key in _URL_KEYS:
            val = obj.get(key)
            if isinstance(val, str) and _looks_like_url(val):
                return ('url', val.strip())
            if isinstance(val, dict):

                try:
                    return _find_audio_ref(val, depth + 1)
                except RuntimeError:
                    continue

        for key in _B64_KEYS:
            val = obj.get(key)
            if isinstance(val, str) and _looks_like_b64_audio(val):
                return ('b64', val.strip())
            if isinstance(val, (bytes, bytearray)) and len(val) > 64:
                return ('b64', base64.b64encode(bytes(val)).decode('ascii'))

        for val in obj.values():
            if isinstance(val, (dict, list)):

                try:
                    return _find_audio_ref(val, depth + 1)
                except RuntimeError:
                    continue
            if isinstance(val, str) and _looks_like_url(val) and any(
                    ext in val.casefold() for ext in ('.mp3', '.wav', '.m4a', 'audio',
                                                       'tos-', 'byteimg', 'capcut')):
                return ('url', val.strip())

    elif isinstance(obj, list):

        for item in obj:

            try:
                return _find_audio_ref(item, depth + 1)
            except RuntimeError:
                continue

    elif isinstance(obj, str):
        if _looks_like_url(obj):
            return ('url', obj.strip())
        if _looks_like_b64_audio(obj):
            return ('b64', obj.strip())
    raise RuntimeError('Không tìm thấy audio URL/base64 trong payload CapCut TTS')


def _decode_b64(value: str) -> bytes:
    raw = value.strip()
    if raw.startswith('data:') and ',' in raw:
        raw = raw.split(',', 1)[1]
    raw = re.sub('\\s+', '', raw)

    try:
        return base64.b64decode(raw, validate = False)
    except Exception:
        return base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4))


def _download_url(url: str, timeout: int = 120) -> bytes:
    data = _get_bytes(
        url,
        timeout = timeout,
        headers = {
            'user-agent':
            'Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03',
            'accept': '*/*'})
    # CDN có thể trả 200 với body rỗng -> phải coi là lỗi để còn retry/fallback.
    if not data or len(data) < 64:
        raise RuntimeError('CapCut trả audio rỗng từ URL.')
    return data



def extract_audio_bytes(task: dict[str, Any]) -> bytes:
    payload = task.get('payload')
    if payload is None:
        raise RuntimeError('CapCut task không có payload audio.')
    if isinstance(payload, str):

        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            if _looks_like_b64_audio(payload):
                return _decode_b64(payload)
            raise RuntimeError(f'CapCut payload không parse được: {payload[:200]}')
    elif isinstance(payload, dict):
        obj = payload
    else:
        raise RuntimeError(f'CapCut payload kiểu lạ: {type(payload)}')
    (kind, value) = _find_audio_ref(obj)
    if kind == 'url':
        return _download_url(value)
    return _decode_b64(value)


def capcut_tts_generate(text: str, output: str | Path, *, voice: str | None = None,
                        speed: str | float = 1.0, timeout_s: float = 120.0,
                        status_callback: Callable[[float, str], None] | None = None,
                        cancel_event: threading.Event | None = None) -> Path:
    '''Synthesize one line → audio file (mp3/wav path as given).

    CapCut chỉ trả MP3, nên đường dẫn .wav được convert bằng ffmpeg sau khi tải.
    Đo từng bước (submit/poll/download) để biết render chậm ở đâu.
    '''
    total_started = time.perf_counter()
    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)

    text = normalize_cache_text(text)
    if not text:
        raise ValueError('text rỗng — không TTS được.')

    if not is_speakable_text(text):
        logger.info(
            "CapCut-TTS: text không có từ để phát âm ('%s') → tạo file audio im lặng.", text)
        return _make_silence_audio(output, duration_s = 0.2)

    (voice_type, resource_id) = parse_voice_key(voice)
    rate = normalize_rate(speed)
    device = get_device()

    logger.info(
        'CapCut-TTS: voice=%s resource=%s rate=%s text=%.40s…',
        voice_type,
        resource_id,
        rate,
        text)

    submit_started = time.perf_counter()
    (task_id, token, bind_id) = submit_tts(
        [text],
        voice_type = voice_type,
        resource_id = resource_id,
        rate = rate,
        device = device)
    submit_elapsed = time.perf_counter() - submit_started
    poll_started = time.perf_counter()
    task = poll_tts(
        task_id,
        token,
        bind_id = bind_id,
        device = device,
        timeout_s = timeout_s,
        status_callback = status_callback,
        cancel_event = cancel_event)

    poll_elapsed = time.perf_counter() - poll_started
    download_started = time.perf_counter()
    audio = extract_audio_bytes(task)
    download_elapsed = time.perf_counter() - download_started

    # .wav: ghi mp3 tạm rồi convert, vì pipeline render (sync/align) cần PCM.
    want_wav = output.suffix.lower() in {'.wave', '.wav'}
    if want_wav:
        mp3_tmp = output.with_suffix('.capcut.mp3')
        mp3_tmp.write_bytes(audio)
        _mp3_to_wav(mp3_tmp, output)

        try:
            mp3_tmp.unlink(missing_ok = True)
        except Exception:
            pass
    else:
        if output.suffix.lower() not in {'.mp3', '.mpeg'}:
            output = output.with_suffix('.mp3')
        output.write_bytes(audio)

    if not output.is_file() or output.stat().st_size < 64:
        raise RuntimeError(f'CapCut TTS file rỗng: {output}')
    logger.info(
        'CapCut TTS timing submit=%.2fs poll=%.2fs download=%.2fs total=%.2fs bytes=%s',
        submit_elapsed,
        poll_elapsed,
        download_elapsed,
        time.perf_counter() - total_started,
        output.stat().st_size)
    return output



def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    import shutil
    import subprocess

    ff = shutil.which('ffmpeg')
    if not ff:
        raise RuntimeError('Cần ffmpeg để convert CapCut mp3 → wav')
    cmd = [ff, '-y', '-i', str(mp3), '-ar', '44100', '-ac', '1', str(wav)]
    p = subprocess.run(
        cmd,
        capture_output = True,
        text = True,
        encoding = 'utf-8',
        errors = 'replace',
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0 or not wav.exists():
        raise RuntimeError(f'ffmpeg convert CapCut TTS lỗi: {(p.stderr or "")[-400:]}')



def make_capcut_tts_func(voice: str | None = None, speed: str | float = 1.0,
                         *, strict: bool = False, fast_mode: bool = False,
                         cancel_event: threading.Event | None = None,
                         fix_shark_enabled: bool = False, fix_shark_path: str | Path = '',
                         fix_shark_device_path: str | Path = '') -> Callable[[str, Path], Path]:
    '''CapCut TTS with optional wait-until-success strict mode.

    In the default mode, shark/rate-limit errors still activate the existing
    Edge fallback.  With ``strict=True``, no other provider is used: both
    shark/busy responses and a queued task ending in ``failed`` are retried
    until CapCut recovers or the caller cancels the render.
    '''
    # Một runner cho mỗi render: bộ đếm cue và cờ "đã auto-fix" không được rò rỉ
    # sang job sau.  ``parallel_degraded`` là tín hiệu cho scheduler biết fast
    # mode phải hạ về tuần tự vì CapCut đang chậm/chặn.
    voice_n = voice or DEFAULT_VOICE_LABEL
    rate = speed

    reset_edge_fallback()
    fix_runner = _FixSharkBatchRunner(
        enabled = fix_shark_enabled,
        path = fix_shark_path,
        device_path = fix_shark_device_path)

    status_callback_holder = [None]
    parallel_degraded = threading.Event()

    def _set_status_callback(callback: Callable[[str], None] | None) -> None:
        status_callback_holder[0] = callback

    def _emit_status(message: str) -> None:
        callback = status_callback_holder[0]
        if callback is not None:

            try:
                callback(message)
            except Exception:
                pass

    def _wait_retry(delay_s: float) -> None:
        deadline = time.monotonic() + max(0.0, delay_s)
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return
            _emit_status(f'chờ thử lại · còn {max(1, int(left + 0.999))} giây')
            step = min(1.0, left)
            if cancel_event is not None:
                if cancel_event.wait(step):
                    raise RuntimeError('Đã dừng khi đang chờ CapCut TTS.')
            else:
                time.sleep(step)

    def _fn(text: str, out_path: Path) -> Path:
        out_path = Path(out_path)
        if not is_speakable_text(text):
            logger.info("CapCut-TTS: text không chứa từ đọc được ('%s') → tạo file silence.", text)
            return _make_silence_audio(out_path, duration_s = 0.2)
        cue_key = f'{time.monotonic_ns()}:{text.strip()}'
        if _edge_fallback_active:
            if strict:
                reset_edge_fallback()
            else:
                return _tts_via_edge(text, out_path, voice = voice_n, speed = rate)
        retry_no = 0
        auto_fix_retry_used = False
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError('Đã dừng khi đang chờ CapCut TTS.')

            def _poll_status(elapsed_s: float, status: str) -> None:
                nonlocal auto_fix_retry_used
                status_n = (status or 'waiting').casefold()
                if fast_mode and elapsed_s >= 12.0 and status_n in _PENDING:
                    if not parallel_degraded.is_set():
                        logger.warning(
                            'CapCut fast mode → hạ về tuần tự: task chờ %.1fs status=%s',
                            elapsed_s,
                            status_n)
                    parallel_degraded.set()
                label = {
                    'queueing': 'đang xếp hàng',
                    'queued': 'đang xếp hàng',
                    'processing': 'đang xử lý',
                    'running': 'đang xử lý'}.get(status_n, 'đang chờ')
                _emit_status(f'{label} · {int(elapsed_s)} giây')
                if fix_shark_enabled:
                    if not auto_fix_retry_used:
                        if elapsed_s >= fix_runner.stall_s:
                            # Chờ quá ngưỡng: chạy batch auto-fix rồi nạp lại Device.
                            fixed = fix_runner.run_for_problem(
                                text,
                                f'request CapCut chờ quá {int(fix_runner.stall_s)} giây (status={status_n})',
                                cue_key = cue_key)
                            if fixed:
                                auto_fix_retry_used = True
                                raise _CapCutAutoFixApplied(
                                    'Device JSON đã được cập nhật; gửi lại đúng câu')
            try:
                generated = capcut_tts_generate(
                    text,
                    out_path,
                    voice = voice_n,
                    speed = rate,
                    status_callback = _poll_status,
                    cancel_event = cancel_event)
                fix_runner.on_success(text, cue_key = cue_key)
                return generated
            except _CapCutAutoFixApplied:
                logger.warning(
                    'CapCut TTS auto-fix đã cập nhật Device · nạp lại và gửi lại đúng câu ngay')
                _emit_status('đã đổi Device · đang gửi lại đúng câu')
                continue
            except Exception as exc:
                if fast_mode and _is_retryable_strict_tts_error(exc):
                    if not parallel_degraded.is_set():
                        logger.warning('CapCut fast mode → hạ về tuần tự: %s', str(exc)[:180])
                    parallel_degraded.set()
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError('Đã dừng khi đang chờ CapCut TTS.') from exc
                retryable = (_is_retryable_strict_tts_error(exc) if strict
                              else _is_shark_or_busy(exc))
                fix_retryable = bool(fix_shark_enabled and _is_retryable_strict_tts_error(exc))
                if not retryable and not fix_retryable:
                    raise
                fixed = fix_runner.run_for_problem(
                    text,
                    str(exc)[:220],
                    cue_key = cue_key)
                if fixed and not auto_fix_retry_used:
                    auto_fix_retry_used = True
                    logger.warning(
                        'CapCut TTS auto-fix đã chạy · thử lại đúng câu một lần trước fallback')
                    _emit_status('đã đổi Device · đang gửi lại đúng câu')
                    continue
                if not retryable:
                    raise
                if not strict:
                    _activate_edge_fallback(str(exc))
                    return _tts_via_edge(text, out_path, voice = voice_n, speed = rate)
                delay_s = min(60.0, 10.0 * 2 ** min(retry_no, 3))
                retry_no += 1
                if retry_no > 15:
                    if not strict:
                        _activate_edge_fallback(f'CapCut thất bại sau {retry_no} lần: {exc}')
                        return _tts_via_edge(text, out_path, voice = voice_n, speed = rate)
                    raise RuntimeError(
                        f'CapCut TTS thất bại sau {retry_no} lần thử lại: {exc}') from exc
                logger.warning(
                    'CapCut TTS chưa tạo được audio; chỉ dùng CapCut nên chờ %.0fs rồi thử lại đúng câu (lần %s): %s',
                    delay_s,
                    retry_no,
                    str(exc)[:180])

                _wait_retry(delay_s)

    setattr(_fn, 'set_status_callback', _set_status_callback)
    setattr(_fn, 'no_silence_on_error', bool(strict))
    # Render pipeline dùng các thuộc tính này để đặt tên file cache và quyết định
    # có được chạy song song hay không.
    setattr(_fn, 'raw_audio_suffix', '.mp3')
    setattr(_fn, 'tts_cache_root', CAPCUT_TTS_CACHE_ROOT)
    setattr(_fn, 'normalize_cache_text', normalize_cache_text)
    setattr(_fn, 'parallel_allowed', lambda: bool(fast_mode and not parallel_degraded.is_set()))
    return _fn



def _tts_via_edge(text: str, out_path: Path, *, voice: str | None,
                  speed: str | float) -> Path:
    '''Edge TTS là lối thoát khi CapCut shark: vẫn giữ tốc độ, chỉ đổi giọng.

    Import trong hàm để CapCut-only render không phải nạp edge_tts.
    '''
    from app.services.edge_tts_engine import edge_tts_generate

    edge_voice = _edge_voice_for_capcut(voice)
    logger.info('Edge-fallback TTS voice=%s text=%.40s…', edge_voice, (text or '')[:40])
    return edge_tts_generate(text, out_path, voice = edge_voice, rate = speed)



def capcut_tts_available() -> bool:

    try:
        _require_requests()
        from app.services import capcut_common_task_client
        return True
    except Exception:
        return False


# Map mã ngôn ngữ kiểu Whisper/UI → giá trị CapCut STT dùng trong payload.
_STT_LANG_MAP = {
    'auto': 'auto',
    'vi': 'vi-VN',
    'zh': 'zh-CN',
    'en': 'en-US',
    'th': 'th-TH',
    'ja': 'ja-JP',
    'ko': 'ko-KR',
    'id': 'id-ID',
    'pt': 'pt-BR',
    'es': 'es-ES',
    'fr': 'fr-FR',
    'de': 'de-DE',
    'vi-vn': 'vi-VN',
    'zh-cn': 'zh-CN',
    'en-us': 'en-US'}


def map_stt_language(language: str | None) -> str:
    '''Map Whisper-style / UI language → CapCut ``language`` field.'''
    raw = (language or 'auto').strip()
    if not raw or raw.casefold() in {'detect', 'none', 'auto'}:
        return _STT_LANG_MAP['auto']
    if '-' in raw and len(raw) <= 8:
        return raw
    code = raw.split(' ', 1)[0].split('(', 1)[0].strip().casefold()
    if code in _STT_LANG_MAP:
        return _STT_LANG_MAP[code]
    if code in {k.casefold() for k in _STT_LANG_MAP.values()}:
        for v in _STT_LANG_MAP.values():
            if v.casefold() == code:
                return v
    return raw if len(raw) >= 2 else 'zh-CN'


def prepare_media_for_upload(media_path: Path, work_dir: Path,
                            *, max_upload_mb: float = 80.0) -> Path:
    '''Prefer a compact MP3 for CapCut VOD upload (video → audio extract).'''
    import shutil
    import subprocess

    media_path = Path(media_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents = True, exist_ok = True)

    ext = media_path.suffix.lower()
    size_mb = media_path.stat().st_size / 1048576 if media_path.is_file() else 0
    # Audio đã gọn thì gửi thẳng, khỏi chạy ffmpeg cho mất thời gian.
    if ext in {'.mp3', '.m4a', '.wav', '.aac'} and size_mb <= max_upload_mb:
        return media_path

    ff = shutil.which('ffmpeg')
    if not ff:
        if ext in {'.mp3', '.m4a', '.mkv', '.mov', '.mp4'}:
            return media_path
        raise RuntimeError('Cần ffmpeg để tách audio trước khi CapCut STT')

    import hashlib

    source_key = hashlib.sha256(str(media_path.resolve()).encode('utf-8')).hexdigest()[:16]
    out_mp3 = work_dir / f'capcut_stt_{source_key}.mp3'
    cmd = [
        ff, '-y', '-i', str(media_path),
        '-vn', '-ac', '1', '-ar', '44100',
        '-c:a', 'libmp3lame', '-b:a', '128k',
        str(out_mp3)]
    p = subprocess.run(
        cmd,
        capture_output = True,
        text = True,
        encoding = 'utf-8',
        errors = 'replace',
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    output_size = out_mp3.stat().st_size if out_mp3.is_file() else 0
    if p.returncode != 0 or output_size < 128:
        raise RuntimeError(
            f'ffmpeg tách audio cho CapCut STT lỗi (rc={p.returncode}, output={output_size} bytes): '
            f'{(p.stderr or "")[-400:]}')
    return out_mp3


def upload_media_for_stt(media_path: Path,
                        *, device: dict[str, Any] | None = None) -> dict[str, Any]:
    '''Upload local media → CapCut VOD; returns vid/md5/duration_ms.'''
    from app.services import capcut_common_task_client as cc

    device = device or get_device()
    media_path = Path(media_path)
    if not media_path.is_file():
        raise RuntimeError(f'Không thấy file upload: {media_path}')
    logger.info('CapCut STT upload: %s (%.1f MB)', media_path.name,
                media_path.stat().st_size / 1000000.0)
    info = cc.upload_audio_file(str(media_path), device)
    if not info.get('vid') or not info.get('md5'):
        raise RuntimeError(f'CapCut upload thiếu vid/md5: {info}')
    return info


def submit_stt(*, audio_vid: str, audio_md5: str, duration_ms: int, language: str = 'auto',
               translation_language: str = 'vi-VN', use_translation: bool = False,
               device: dict[str, Any] | None = None) -> tuple[str, str, str]:
    '''Create STT task → ``(task_id, token, bind_id)``.

    STT dùng ``appid=False`` (req_key cc_audio_subtitle_asr) và timeout dài hơn
    vì payload dịch thuật có thể lớn.
    '''
    from app.services import capcut_common_task_client as cc

    device = device or get_device()
    (babi, body) = cc.stt_new_body(
        audio_vid,
        audio_md5,
        int(duration_ms) if duration_ms else 10000,
        language,
        translation_language,
        use_translation)
    path = '/lv/v1/common_task/new'
    query = cc.common_query(device, babi, include_region = True)
    body_text = cc.compact_json(body)
    url = cc.BASE + path + '?' + cc.urlencode(query)

    headers = cc.base_headers(device, body_text, appid = False)
    lower = {k.lower(): v for k, v in headers.items()}
    if 'sign' not in lower:
        headers['sign'] = cc.make_sign_header(url, device['appvr'], lower['device-time'],
                                              device['tdid'])
    data = _post_json(url, headers, body_text, timeout = 90)
    _check_api_ret(data, 'stt-new')
    task = _first_task(data)
    task_id = str(task.get('id') or '').strip()
    token = str(task.get('token') or '').strip()
    bind_id = str(body.get('bind_id') or task.get('bind_id') or '').strip()
    if not task_id or not token:
        raise RuntimeError(f'CapCut STT thiếu id/token: {task}')
    logger.info('CapCut STT submitted id=%s status=%s lang=%s', task_id, task.get('status'),
                language)
    return (task_id, token, bind_id)



def _ms_to_s(value: Any) -> float:
    '''CapCut STT dùng millisecond cho start_time/end_time/start_ms/end_ms.

    KHÔNG đoán đơn vị theo độ lớn nữa. Nhánh cũ ``if n >= 1000`` khiến mọi mốc
    dưới 1000 ms — tức là cả giây đầu tiên của video — bị hiểu là "giây":
    ``start_time=200`` thành 200 s (03:20) nên câu thoại mở đầu luôn bị đẩy ra
    khỏi màn hình. Chỉ giữ lối thoát cho payload dùng microsecond.
    '''

    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    if n <= 0:
        return 0.0
    if n > 21600000:
        return n / 1000000.0
    return n / 1000.0


def _find_utterances(obj: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 14:
        return []
    if isinstance(obj, dict):

        for key in ('utterances', 'captions', 'sentences', 'segments', 'subtitle_list', 'items'):
            items = obj.get(key)
            if not isinstance(items, list):
                continue
            if not items:
                continue
            if not isinstance(items[0], dict):
                continue
            sample = items[0]
            if any(k in sample for k in ('text', 'content', 'sentence', 'start_time', 'start',
                                         'start_ms')):
                return [x for x in items if isinstance(x, dict)]

        for val in obj.values():
            found = _find_utterances(val, depth + 1)
            if found:
                return found

    elif isinstance(obj, list):

        for item in obj:
            found = _find_utterances(item, depth + 1)
            if found:
                return found
    return []


def utterances_to_cues(payload: Any) -> list:
    '''Convert CapCut STT payload → list[SrtCue].'''
    from app.services.srt_utils import SrtCue

    if isinstance(payload, str):

        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f'CapCut STT payload không parse được: {payload[:200]}') from exc
    utterances = _find_utterances(payload)
    if not utterances:
        raise RuntimeError('CapCut STT không có utterances trong payload.')
    cues = []
    for item in utterances:
        text = str(item.get('text') or item.get('content') or item.get('sentence')
                   or item.get('attribute_text') or '').strip()
        if not text:
            continue
        if 'start_time' in item or 'end_time' in item:
            start = _ms_to_s(item.get('start_time') if item.get('start_time') is not None
                              else item.get('start'))
            end = _ms_to_s(item.get('end_time') if item.get('end_time') is not None
                            else item.get('end'))
        elif 'start_ms' in item or 'end_ms' in item:
            start = _ms_to_s(item.get('start_ms'))
            end = _ms_to_s(item.get('end_ms'))
        else:
            start = float(item.get('start') or item.get('begin') or 0)
            end = float(item.get('end') or (start + 0.3))
            if start > 1000 or end > 1000:
                (start, end) = (start / 1000.0, end / 1000.0)
        if end <= start:
            end = start + 0.25
        cues.append(SrtCue(index = len(cues) + 1, start_s = start, end_s = end, text = text))
    if not cues:
        raise RuntimeError('CapCut STT: utterances rỗng (không có text).')
    if any((b.start_s < a.start_s for a, b in zip(cues, cues[1:]))):
        logger.warning('CapCut STT trả cue không tăng dần theo thời gian — đã sắp lại %s cue',
                       len(cues))
        cues.sort(key = lambda c: (c.start_s, c.end_s))
        for (i, c) in enumerate(cues, start = 1):
            c.index = i
    return cues


def extract_stt_cues(task: dict[str, Any]) -> list:
    payload = _parse_task_payload(task)
    if payload is None:
        raise RuntimeError('CapCut STT task không có payload.')
    return utterances_to_cues(payload)


def capcut_transcribe_to_srt(media_path: Path, out_srt: Path,
                             *, language: str | None = None,
                             work_dir: Path | None = None,
                             translation_language: str = 'vi-VN',
                             use_translation: bool = False,
                             timeout_s: float = 300.0) -> tuple[Path, int, str | None]:
    '''Full CapCut STT: prepare → upload → task → poll → SRT.

    Returns ``(srt_path, n_cues, language_tag)``.
    '''
    from app.services.srt_utils import write_srt

    media_path = Path(media_path)
    out_srt = Path(out_srt)
    out_srt.parent.mkdir(parents = True, exist_ok = True)
    work = Path(work_dir) if work_dir else out_srt.parent / f'{media_path.stem}_capcut_stt'
    work.mkdir(parents = True, exist_ok = True)

    lang = map_stt_language(language)
    device = get_device()

    audio_path = prepare_media_for_upload(media_path, work)
    upload_info = upload_media_for_stt(audio_path, device = device)
    duration_ms = int(upload_info.get('duration_ms') or 0)
    if duration_ms <= 0:
        # VOD không trả về độ dài thì đo bằng ffprobe; cũng không được thì giả định 10s.
        try:
            from app.services.audio_sync_engine import probe_duration_s

            duration_ms = int(max(0.1, probe_duration_s(audio_path)) * 1000)
        except Exception:
            duration_ms = 10000

    (task_id, token, bind_id) = submit_stt(
        audio_vid = str(upload_info['vid']),
        audio_md5 = str(upload_info['md5']),
        duration_ms = duration_ms,
        language = lang,
        translation_language = translation_language,
        use_translation = use_translation,
        device = device)
    task = poll_stt(task_id, token, bind_id = bind_id, device = device, timeout_s = timeout_s)
    cues = extract_stt_cues(task)
    write_srt(cues, out_srt)
    logger.info('CapCut STT OK: %s cues → %s (lang=%s)', len(cues), out_srt.name, lang)
    return (out_srt, len(cues), lang)



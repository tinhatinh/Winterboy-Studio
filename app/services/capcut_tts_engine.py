# Source Generated with Decompyle++
# File: capcut_tts_engine.pyc (Python 3.12)

__doc__ = 'CapCut cloud TTS + STT engine for Winterboy Studio.\n\nWraps ``capcut_common_task_client`` (from capcut-tts-api):\n\nTTS:\n  1. POST /lv/v1/common_task/new   (sami_text_to_speech)\n  2. POST /lv/v1/common_task/query until succeed/failed\n  3. Extract audio URL or base64 → local MP3/WAV\n\nSTT (alongside Whisper / ElevenLabs — does not replace them):\n  1. Extract audio → upload VOD (upload_sign + Apply/CommitUploadInner)\n  2. POST common_task/new (cc_audio_subtitle_asr)\n  3. Poll query → utterances → SRT\n\nVoice catalog ships as ``capcut_voices.json`` (from CapCut Voice.json).\n\nDevice/session overrides live in ``~/.winterboy/capcut_device.json`` so secrets\nstay out of last_config / shared presets.  Without a valid device profile\nCapCut may return ``shark block only`` (anti-bot).\n'
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


def resolve_capcut_device_path(candidate = None):
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
            return bundled_json
            return bundled_json
        except Exception:
            return bundled_json



def resolve_capcut_fix_bat_path(candidate = None):
    '''Resolve a valid fix_shark.bat path with intelligent auto-detection.'''
    (bundled_bat, _json) = get_bundled_capcut_fix_paths()
    if candidate:
        
        try:
            p = Path(candidate).expanduser()
            if p.is_file():
                return p
            return bundled_bat
            return bundled_bat
        except Exception:
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
        if not data.get('backup_path'):
            data.get('backup_path')
        raw_backup = None('').strip()
        return {
            'use_backup': bool(data.get('use_backup', False)),
            'backup_path': raw_backup }
    except Exception:
        exc = None
        logger.warning('Không đọc được lựa chọn Device CapCut: %s', exc)
        del exc
        return None
        None = 
        del exc



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
        return None
    except Exception:
        exc = None
        logger.warning('Không đọc được capcut_device.json: %s', exc)
        del exc
        return None
        None = 
        del exc



def load_selected_device_overrides():
    '''Load the active profile; each new request sees auto-fix JSON updates.'''
    preferences = load_device_source_preferences()
    if not preferences['use_backup']:
        return load_device_overrides()
    raw_path = None.get('backup_path')
    backup_path = Path(raw_path).expanduser() if raw_path else None
# WARNING: Decompyle incomplete


def save_device_overrides(data = None):
    path = _DEVICE_PATH
    path.parent.mkdir(parents = True, exist_ok = True)
# WARNING: Decompyle incomplete


def _file_stamp(path = None):
    '''Cheap identity used to invalidate in-memory config/cache state.'''
    
    try:
        stat = path.stat()
        return (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return 



def _active_device_stamp():
    preferences = load_device_source_preferences()
    active = Path(preferences['backup_path']).expanduser() if preferences['use_backup'] and preferences['backup_path'] else _DEVICE_PATH
    return (bool(preferences['use_backup']), _file_stamp(_DEVICE_SOURCE_PATH), _file_stamp(active))


def extract_device_from_local_capcut(*, save):
    '''Đọc device_id / iid thật từ log CapCut Pro PC trên máy.

    CapCut Pro lưu request URL trong ``%LOCALAPPDATA%\\CapCut\\User Data\\Log``.
    Dùng device đó thay DEFAULT_DEVICE public (hay bị shark block).
    '''
    pass
# WARNING: Decompyle incomplete


def get_device():
    '''Merge DEFAULT_DEVICE with the profile source chosen before the job.'''
    cc = capcut_common_task_client
    import app.services
    stamp_before = _active_device_stamp()
    _device_cache_lock
# WARNING: Decompyle incomplete


def _load_voice_catalog():
    if not _VOICES_PATH.is_file():
        return []
    
    try:
        data = json.loads(_VOICES_PATH.read_text(encoding = 'utf-8'))
        if isinstance(data, list):
            return data
        return None
    except Exception:
        exc = None
        logger.warning('Không đọc được capcut_voices.json: %s', exc)
        del exc
        return None
        None = 
        del exc



def list_capcut_voices(*, lang):
    '''Return ``(label, voice_key)`` for UI OptionMenu.

    Label: ``Display Name | voice_type:resource_id``
    voice_key: ``voice_type:resource_id``
    '''
    catalog = _load_voice_catalog()
    result = []
    seen = set()
    for item in catalog:
        if not isinstance(item, dict):
            continue
        if not item.get('voice_type'):
            item.get('voice_type')
        voice_type = str('').strip()
        if not item.get('resource_id'):
            item.get('resource_id')
        resource_id = str('').strip()
        if not voice_type or resource_id:
            continue
        if not item.get('lang'):
            item.get('lang')
            if not item.get('lan'):
                item.get('lan')
        item_lang = str('').strip()
        if lang:
            want = lang.casefold()
            have = item_lang.casefold()
            if not want not in have and have not in want and have.startswith(want.split('-')[0]):
                continue
        key = f'''{voice_type}:{resource_id}'''
        if key in seen:
            continue
        seen.add(key)
        if not item.get('display_name'):
            item.get('display_name')
        name = str(voice_type).strip()
        result.append((f'''{name} | {key}''', key))
    if not result:
        result.append((DEFAULT_VOICE_LABEL, f'''{DEFAULT_VOICE_TYPE}:{DEFAULT_RESOURCE_ID}'''))
    return result


def list_capcut_voices_all():
    '''All languages from catalog (for advanced use).'''
    return list_capcut_voices(lang = None)


def parse_voice_key(voice = None):

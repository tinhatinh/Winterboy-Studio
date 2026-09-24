# Source Generated with Decompyle++
# File: cloud_voice.pyc (Python 3.12)

'''Cloud voice providers used by Winterboy Studio.

Providers are independent:
  - Edge TTS  → free Microsoft voices (edge_tts_engine.py)
  - CapCut    → CapCut common_task TTS (capcut_tts_engine.py)
  - ElevenLabs → REST binary TTS + Scribe STT (this module)
  - Google Cloud TTS → official Google client, including Chirp3-HD voices

Keys live outside render configs in ``~/.winterboy``.  This keeps API secrets out of
``last_config.json`` and shared project presets.
'''
from __future__ import annotations
import json
import hashlib
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable
from app.services.srt_utils import SrtCue, write_srt
logger = logging.getLogger(__name__)
ELEVEN_BASE_URL = 'https://api.elevenlabs.io/v1'
ELEVEN_BASE_URL_V2 = 'https://api.elevenlabs.io/v2'
ELEVEN_DEFAULT_TTS_MODELS: 'list[tuple[str, str]]' = [
    ('eleven_multilingual_v2', 'Lifelike · 29 ngôn ngữ · chất lượng cao (khuyên dùng VI)'),
    ('eleven_turbo_v2_5', 'Cân bằng chất lượng/tốc độ · 32 ngôn ngữ'),
    ('eleven_turbo_v2', 'Cân bằng · chỉ tiếng Anh'),
    ('eleven_flash_v2_5', 'Nhanh nhất · 32 ngôn ngữ · latency thấp'),
    ('eleven_flash_v2', 'Nhanh · chỉ tiếng Anh'),
    ('eleven_v3', 'Model mới (nếu account hỗ trợ)')]
ELEVEN_DEFAULT_MODEL_ID = 'eleven_multilingual_v2'
ELEVEN_STT_MODEL_ID = 'scribe_v2'
ELEVEN_OUTPUT_FORMAT = 'mp3_44100_128'

def _secret_path(name = None):
    return Path.home() / '.winterboy' / f'''{name}.txt'''


def get_secret(name = None, env_name = None):
    value = (os.environ.get(env_name) or '').strip()
    if value:
        return value
    path = _secret_path(name)
    if path.is_file():
        return path.read_text(encoding = 'utf-8').strip()
    return ''


def set_secret(name = None, env_name = None, value = None):
    value = (value or '').strip()
    os.environ[env_name] = value
    path = _secret_path(name)
    path.parent.mkdir(parents = True, exist_ok = True)
    if value:
        path.write_text(value, encoding = 'utf-8')
        return None
    if path.exists():
        path.unlink()
        return None
    return None


def get_elevenlabs_api_key():
    # TODO(khôi phục hành vi): bản decompile dừng ở danh sách config.json ứng viên;
    # phần đọc/hiện key từ các nguồn (~430 instruction) mất hẳn -> không đoán.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.get_elevenlabs_api_key')


def _split_elevenlabs_api_keys(value = None):
    """One secret per line, unique and in the user's preferred order."""
    seen = set()
    result = []
    for raw in (value or '').splitlines():
        key = raw.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def get_elevenlabs_api_keys():
    return _split_elevenlabs_api_keys(get_elevenlabs_api_key())

_ELEVEN_KEY_CURSOR = 0
_ELEVEN_KEY_COOLDOWN: 'dict[str, float]' = { }
_ELEVEN_KEY_LOCK = threading.Lock()

def _reset_elevenlabs_key_rotation():
    global _ELEVEN_KEY_CURSOR
    
    with _ELEVEN_KEY_LOCK:
        _ELEVEN_KEY_CURSOR = 0
        _ELEVEN_KEY_COOLDOWN.clear()


def save_elevenlabs_api_key(key = None):
    # TODO(khôi phục hành vi): sau bước set_secret hàm còn ghi lại key vào
    # config.json (~520 instruction) — bản decompile mất phần đó.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.save_elevenlabs_api_key')

_GOOGLE_CHIRP3_HD_STYLES: 'tuple[tuple[str, str], ...]' = (('Achernar', 'FEMALE'), ('Achird', 'MALE'), ('Algenib', 'MALE'), ('Algieba', 'MALE'), ('Alnilam', 'MALE'), ('Aoede', 'FEMALE'), ('Autonoe', 'FEMALE'), ('Callirrhoe', 'FEMALE'), ('Charon', 'MALE'), ('Despina', 'FEMALE'), ('Enceladus', 'MALE'), ('Erinome', 'FEMALE'), ('Fenrir', 'MALE'), ('Gacrux', 'FEMALE'), ('Iapetus', 'MALE'), ('Kore', 'FEMALE'), ('Laomedeia', 'FEMALE'), ('Leda', 'FEMALE'), ('Orus', 'MALE'), ('Puck', 'MALE'), ('Pulcherrima', 'FEMALE'), ('Rasalgethi', 'MALE'), ('Sadachbia', 'MALE'), ('Sadaltager', 'MALE'), ('Schedar', 'MALE'), ('Sulafat', 'FEMALE'), ('Umbriel', 'MALE'), ('Vindemiatrix', 'FEMALE'), ('Zephyr', 'FEMALE'), ('Zubenelgenubi', 'MALE'))

def _google_voice_label(name = None, gender = None):
    gender = (gender or '').split('.')[-1].upper() or '?'
    style = name.rsplit('-', 1)[-1] if name else ''
    if gender == 'FEMALE':
        gender_vi = 'Nữ'
    elif gender == 'MALE':
        gender_vi = 'Nam'
    else:
        gender_vi = gender
    return f'''{style} ({gender_vi}) · {name} | {name}'''


def get_google_tts_credentials_path():
    '''Return a service-account JSON path without ever reading/storing its key.

    ``GOOGLE_APPLICATION_CREDENTIALS`` remains supported for deployments.  The
    desktop setting is only a local path in ``~/.winterboy`` so render configs and
    job folders cannot accidentally leak a Google private key.
    '''
    return get_secret('google_tts_credentials_path', 'GOOGLE_APPLICATION_CREDENTIALS')


def save_google_tts_credentials_path(path = None):
    set_secret('google_tts_credentials_path', 'GOOGLE_APPLICATION_CREDENTIALS', path)


def list_google_cloud_voices_catalog():
    '''Bundled vi-VN Chirp3-HD catalog (no network / credentials required).'''
    records = []
    for style, gender in _GOOGLE_CHIRP3_HD_STYLES:
        name = f'''vi-VN-Chirp3-HD-{style}'''
        records.append((_google_voice_label(name, gender), name))
    return records


def _google_tts_client():
    '''Create the official Google Cloud Text-to-Speech client on demand.'''
    # TODO(khôi phục hành vi): các nhánh try/except (ImportError -> RuntimeError
    # from exc) bị decompile lồng sai chỗ, không còn thứ tự đúng.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice._google_tts_client')


def list_google_cloud_voices(*, live = True):
    '''List Vietnamese Chirp3-HD voices.

    With credentials, prefer the live API list for the current project.
    Without credentials (or on API failure), return the official offline catalog
    so the UI still shows every vi-VN-Chirp3-HD style.
    '''
    # TODO(khôi phục hành vi): vòng lặp đọc response sống và `sorted(...)` bị
    # decompile thành `name = str('')` / `return None(records, ...)`.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.list_google_cloud_voices')


def google_cloud_tts_generate(text = None, output = None, *, voice_name = None, speed = 1.0):
    '''Synthesize a single cue to MP3 using Google Cloud Chirp3-HD.'''
    # TODO(khôi phục hành vi): thân chính + các nhánh except bị mất thứ tự trong bản
    # decompile (raise ... , exc).
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.google_cloud_tts_generate')


def _json_request(url: str, *, method = 'GET', headers = None, body = None, timeout = 120) -> 'dict[str, Any] | list[Any]':
    # TODO(khôi phục hành vi): HTTP JSON helper — thân hàm mất hẳn trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice._json_request')


def _parse_eleven_error(detail = None, code = None):
    '''Map ElevenLabs JSON error body → human message (VN).

    HTTP 402 is NOT always “hết credit”. Free tier often gets 402 for
    library/shared voices used via API even when characters remain.
    '''
    # TODO(khôi phục hành vi): các so sánh `code == 429/422/...` và `in low` bị
    # decompile thành `None == 429` / `None in low`; cần dựng lại từ dis để không
    # đoán nhầm nhánh nào đi với mã nào.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice._parse_eleven_error')


def _binary_request(url: str, *, method = 'POST', headers = None, body = None, timeout = 180) -> bytes:
    # TODO(khôi phục hành vi): HTTP binary helper — thân hàm mất hẳn trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice._binary_request')


def _clamp01(value: float, default: float = 0.5) -> float:
    
    try:
        return max(0, min(1, float(value)))
    except (TypeError, ValueError):
        return default


def _clamp_speed(value: 'str | float | None', default: float = 1.0) -> float:
    '''ElevenLabs speed is typically ~0.7–1.2; clamp wider for safety.'''
    
    try:
        return max(0.7, min(1.2, float(value if value is not None else default)))
    except (TypeError, ValueError):
        return default


def build_voice_settings(*, stability = 0.5, similarity_boost = 0.75, style = 0.0, use_speaker_boost = True, speed = 1.0):
    '''Map UI / app values → nested ``voice_settings`` body field.

    UI tools often expose 0–100; pass already-normalized 0–1 here, or values
    >1 will be treated as percent and scaled by /100.
    '''
    
    def _norm(v = None, default = None):
        
        try:
            n = float(v)
            if n > 1:
                n = n / 100
            return _clamp01(n, default)
        except (TypeError, ValueError):
            return default


    settings = {
        'stability': _norm(stability, 0.5),
        'similarity_boost': _norm(similarity_boost, 0.75),
        'style': _norm(style, 0),
        'use_speaker_boost': bool(use_speaker_boost) }
    if speed is not None:
        settings['speed'] = _clamp_speed(speed, 1.0)
    return settings

class ElevenLabsTTSClient:
    '''Production ElevenLabs surface used by Mumu (desktop, no tkinter).

    Methods mirror the integration contract:
      synthesize / get_voice / search_voices / list_models / validate_api_key
    '''
    
    def __init__(self, api_key = None):
        raw = api_key if api_key is not None else get_elevenlabs_api_key()
        keys = _split_elevenlabs_api_keys(raw)
        self.api_key = keys[0] if keys else ''

    
    def _require_key(self):
        if not self.api_key:
            raise RuntimeError('Thiếu ElevenLabs API key trong Cài đặt (hoặc env MUMU_ELEVENLABS_API_KEY).')
        return self.api_key

    
    def _headers(self, *, accept = None, content_type = 'application/json'):
        headers = {
            'xi-api-key': self._require_key() }
        if content_type:
            headers['Content-Type'] = content_type
        if accept:
            headers['Accept'] = accept
        return headers

    @staticmethod
    def _normalize_voice(voice):
        if not voice:
            return { }
        return {
            'voice_id': str(voice.get('voice_id') or voice.get('id') or '').strip(),
            'name': str(voice.get('name') or '').strip(),
            'preview_url': voice.get('preview_url'),
            'category': str(voice.get('category') or '').strip(),
            'description': str(voice.get('description') or '')[:120],
            'info': voice }

    
    def synthesize(self, text = None, voice_id = None, *, model_id = None, settings = None, output_format = None, timeout = 180):
        '''POST /v1/text-to-speech/{voice_id} → MP3 bytes.

        Does **not** use history_item_id / download flow.
        '''
        text = (text or '').strip()
        if not text:
            raise ValueError('text rỗng — không TTS được.')
        voice_id = (voice_id or '').strip()
        if not voice_id:
            raise RuntimeError('Chọn hoặc tải giọng ElevenLabs trước khi render.')
        model_id = (model_id or ELEVEN_DEFAULT_MODEL_ID).strip()
        body = {
            'text': text,
            'model_id': model_id }
        if settings:
            body['voice_settings'] = settings
        query = urllib.parse.urlencode({
            'output_format': output_format })
        url = f'''{ELEVEN_BASE_URL}/text-to-speech/{urllib.parse.quote(voice_id)}?{query}'''
        audio = _binary_request(url, method = 'POST', headers = self._headers(accept = 'audio/mpeg'), body = body, timeout = timeout)
        if not audio or len(audio) < 128:
            raise RuntimeError('ElevenLabs trả audio rỗng.')
        return audio

    
    def synthesize_to_file(self = None, text = None, output = None, *, voice_id, model_id, settings, output_format):
        audio = self.synthesize(text, voice_id, model_id = model_id, settings = settings, output_format = output_format)
        output = Path(output)
        output.parent.mkdir(parents = True, exist_ok = True)
        output.write_bytes(audio)
        return output

    
    def get_voice(self, voice_id: str) -> 'dict[str, Any]':
        '''GET /v1/voices/{voice_id} → name, preview_url, labels, settings…'''
        # TODO(khôi phục hành vi): sau lời gọi _json_request, phần chuẩn hoá payload
        # (~100 instruction) mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.get_voice')

    
    def search_voices(self, query = '', *, page_size = 100) -> 'list[dict[str, Any]]':
        '''GET /v2/voices?search=… (falls back to /v1/voices).'''
        # TODO(khôi phục hành vi): bản decompile dừng ở `qs = urlencode(params)`;
        # nhánh gọi /v2 rồi fallback /v1 (~300 instruction) mất hẳn.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.search_voices')

    
    def search_voices_by_query(self, query: str, *, page_size = 20) -> 'list[dict[str, Any]]':
        '''Tìm voice theo Voice ID hoặc tên/từ khóa.

        Thứ tự (giống tts_tool_elevenLabs/voice_fetcher):
          1) exact ID  GET /v1/voices/{id}
          2) account   GET /v2/voices?search=
          3) library   GET /v1/shared-voices?search=
        '''
        # TODO(khôi phục hành vi): thân hàm (~660 instruction) mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.search_voices_by_query')

    
    def list_voices(self):
        '''Friendly labels for UI OptionMenu: ``Name | voice_id`` → voice_id.'''
        voices = self.search_voices('')
        result = []
        for item in voices:
            voice_id = str(item.get('voice_id') or '').strip()
            name = str(item.get('name') or voice_id).strip()
            if not voice_id:
                continue
            result.append((f'''{name} | {voice_id}''', voice_id))
        if not result:
            raise RuntimeError('ElevenLabs không trả về giọng nào cho API key này.')
        return result

    
    def list_models(self) -> 'list[dict[str, Any]]':
        '''GET /v1/models, filter can_do_text_to_speech.'''
        # TODO(khôi phục hành vi): phần lọc model sau dòng kiểm tra isinstance mất
        # trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.list_models')

    
    def list_model_choices(self) -> 'list[tuple[str, str]]':
        '''UI labels: ``(label_with_id, model_id)``. Live API with static fallback.'''
        # TODO(khôi phục hành vi): thân hàm (~290 instruction) mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.list_model_choices')

    
    def validate_api_key(self) -> bool:
        '''Light call (models) so invalid keys fail early.'''
        self.list_models()
        return True

    
    def transcribe(self, media_path, *, language = None, model_id = None, timestamps_granularity = 'word') -> 'dict[str, Any]':
        # TODO(khôi phục hành vi): các nhánh `with urllib.request.urlopen(...)` và
        # except HTTPError/URLError (raise ... from exc) bị decompile lồng sai chỗ.
        raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.ElevenLabsTTSClient.transcribe')







def _eleven_key_fingerprint(key = None):
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]


def _eleven_key_failover_error(error: 'BaseException | str') -> bool:
    text = str(error).casefold()
    markers = ('invalid_api_key', 'api key không hợp lệ', 'rate-limit', 'rate limit', '429', 'quota', 'credit', '402', '401', '403', 'authentication', 'permission')
    return any((marker in text for marker in markers))


def _eleven_key_cooldown(error: 'BaseException | str') -> float:
    text = str(error).casefold()
    if 'invalid' in text and '401' in text or 'authentication' in text:
        return 3600
    if 'quota' in text and 'credit' in text or '402' in text:
        return 900
    return 60


def _with_elevenlabs_key(operation, *, label):
    '''Run one ElevenLabs operation with persistent round-robin key failover.'''
    # TODO(khôi phục hành vi): vòng xoay vòng key + cooldown (~700 instruction) mất
    # sau dòng `start = _ELEVEN_KEY_CURSOR % len(keys)` -> không đoán chính sách failover.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice._with_elevenlabs_key')


def list_elevenlabs_voices():
    return _with_elevenlabs_key((lambda client: client.list_voices()), label = 'tải giọng')


def get_elevenlabs_subscription(api_key = None):
    '''Lấy thông tin số dư (Subscription & Quota) của API key từ ElevenLabs.'''
    # TODO(khôi phục hành vi): ngữ cảnh `with urllib.request.urlopen(...)` và các
    # nhánh except HTTPError/Exception bị decompile vỡ (gây lỗi cú pháp tại dòng 450).
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.get_elevenlabs_subscription')


def validate_elevenlabs_api_keys(value = None):
    '''Validate each configured secret independently and return real quota / balance details.'''
    # TODO(khôi phục hành vi): thân hàm (~185 instruction) mất trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.validate_elevenlabs_api_keys')


def search_elevenlabs_voices(query: str, *, page_size = 20) -> 'list[dict[str, Any]]':
    '''Public helper: search by Voice ID or name keyword (for UI Search box).'''
    # TODO(khôi phục hành vi): thân hàm mất trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.search_elevenlabs_voices')


def list_elevenlabs_models() -> 'list[tuple[str, str]]':
    '''Return ``(label, model_id)`` for the TTS model OptionMenu.'''
    # TODO(khôi phục hành vi): nhánh fallback khi chưa có API key mất trong bản
    # decompile (chỉ còn dòng return đầu tiên).
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.list_elevenlabs_models')


def download_elevenlabs_voice_preview(voice_id: str, output: 'str | Path') -> Path:
    """Download ElevenLabs' existing voice preview without spending TTS characters."""
    # TODO(khôi phục hành vi): ~395 instruction tải file nghe thử — mất trong bản
    # decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.download_elevenlabs_voice_preview')


def elevenlabs_tts_generate(text: str, output: Path, *, voice_id: str, speed: 'str | float' = 1.0, model_id: str = 'eleven_multilingual_v2', stability: float = 0.5, similarity_boost: float = 0.75, style: float = 0.0, use_speaker_boost: bool = True) -> Path:
    '''Synthesize one line → MP3 file (render pipeline entry point).'''
    # TODO(khôi phục hành vi): thân hàm (~150 instruction) mất trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.elevenlabs_tts_generate')


def make_cloud_tts(provider: str, voice_id: str, speed: 'str | float', *, model_id = None, stability = 0.5, similarity_boost = 0.75, style = 0.0, use_speaker_boost = True, capcut_strict = False, capcut_fast_mode = False, cancel_event = None, fix_shark_enabled = False, fix_shark_path = '', fix_shark_device_path = '') -> 'Callable[[str, Path], Path]':
    '''Build a ``(text, path) -> path`` callable for AudioSyncEngine.

    Edge TTS is handled outside this module.  CapCut / ElevenLabs / Google stay
    independent — only the selected provider is wired.
    '''
    # TODO(khôi phục hành vi): hàm nối provider (~370 instruction, có closure) mất
    # trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.make_cloud_tts')


def _multipart_body(fields = None, file_field = None, file_path = None):
    boundary = f'''----Mumu{uuid.uuid4().hex}'''
    chunks = []
    for key, value in fields.items():
        chunks.extend((f'''--{boundary}\r\n'''.encode(), f'''Content-Disposition: form-data; name="{key}"\r\n\r\n'''.encode(), str(value).encode('utf-8'), b'\r\n'))
    chunks.extend((f'''--{boundary}\r\n'''.encode(), f'''Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'''.encode(), b'Content-Type: application/octet-stream\r\n\r\n', file_path.read_bytes(), b'\r\n', f'''--{boundary}--\r\n'''.encode()))
    return (b''.join(chunks), boundary)


def elevenlabs_transcribe_to_srt(media_path: Path, out_srt: Path, *, language = None) -> 'tuple[Path, int, str | None]':
    '''STT via Scribe — model is fixed to scribe_v2 (not a TTS model).'''
    # TODO(khôi phục hành vi): ~500 instruction chuyển kết quả Scribe thành cue SRT.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.elevenlabs_transcribe_to_srt')


def _get_vieneu_engine():
    
    try:
        from app.services.voice_engine.vieneu_engine import VieneuEngine
        return VieneuEngine()
    except Exception as exc:
        logger.warning('Không thể khởi tạo VieneuEngine: %s', exc)
        return None


def list_vieneu_voices():
    '''Trả về danh sách 20 giọng preset + các giọng cá nhân đã nhân bản.'''
    results = []
    
    try:
        from app.services.voice_engine.voices_config import PRESET_VOICES
        for v in PRESET_VOICES:
            name = v['name']
            label = v['label']
            results.append((f'''{label} | {name}''', name))
    except Exception as exc:
        logger.warning('Không thể đọc PRESET_VOICES: %s', exc)

    engine = _get_vieneu_engine()
    if engine:
        for cloned in engine.list_cloned_voices():
            results.append((f'''🧬 [Clone] {cloned} | {cloned}''', cloned))
    return results


def vieneu_tts_generate(text = None, output = None, *, voice_name = None, temperature = 0.7):
    '''Tổng hợp câu thoại bằng VieNeu-TTS v3 Turbo local'''
    text = (text or '').strip()
    if not text:
        raise ValueError('Văn bản rỗng, không thể tổng hợp bằng VieNeu.')
    engine = _get_vieneu_engine()
    if not engine:
        raise RuntimeError('VieNeu-TTS engine chưa sẵn sàng hoặc thiếu thư viện vieneu.')
    clean_voice = (voice_name or '').rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)
    engine.synthesize(text = text, voice = clean_voice, temperature = temperature, out_path = str(output))
    return output


def download_vieneu_voice_preview(voice_name = None, output = None):
    '''Phát mẫu nghe thử của VieNeu: ưu tiên file pre-generated 0ms'''
    clean_voice = (voice_name or '').rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
    if not clean_voice:
        raise RuntimeError('Chưa chọn giọng VieNeu để nghe thử.')
    target = Path(output)
    target.parent.mkdir(parents = True, exist_ok = True)
    import sys
    candidates = [
        Path(__file__).resolve().parents[1] / 'assets' / 'tts_samples' / 'vieneu' / f'''{clean_voice}.wav''',
        Path(__file__).resolve().parents[2] / 'preview' / 'vieneu' / f'''{clean_voice}.wav''',
        Path.cwd() / 'preview' / 'vieneu' / f'''{clean_voice}.wav''']
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = Path(sys._MEIPASS)
        candidates.insert(0, meipass / 'preview' / 'vieneu' / f'''{clean_voice}.wav''')
        candidates.insert(1, meipass / 'app' / 'assets' / 'tts_samples' / 'vieneu' / f'''{clean_voice}.wav''')
    for cand in candidates:
        if not cand.is_file():
            continue
        if not cand.stat().st_size >= 102400:
            continue
        import shutil
        shutil.copy2(cand, target)
        return target
    sample_text = f'''Xin chào! Đây là bản nghe thử giọng đọc tiếng Việt của {clean_voice}.'''
    return vieneu_tts_generate(sample_text, target, voice_name = clean_voice, temperature = 0.7)


def _get_zerotts_engine():
    
    try:
        from app.services.voice_engine.zerotts_engine import ZeroTTSEngine
        return ZeroTTSEngine()
    except Exception as exc:
        logger.warning('Không thể khởi tạo ZeroTTSEngine: %s', exc)
        return None


def list_zerotts_voices():
    '''Trả về danh sách 8 giọng preset chuẩn của ZeroTTS.'''
    engine = _get_zerotts_engine()
    if engine:
        return engine.list_voice_tuples()
    return []


def zerotts_tts_generate(text = None, output = None, *, voice_name = 'maichi', speed = 1.0):
    '''Tổng hợp giọng đọc bằng ZeroTTS AI offline 48kHz.'''
    text = (text or '').strip()
    if not text:
        raise ValueError('Văn bản rỗng, không thể tổng hợp bằng ZeroTTS.')
    engine = _get_zerotts_engine()
    if not engine:
        raise RuntimeError('ZeroTTS engine chưa sẵn sàng hoặc thiếu thư viện.')
    clean_voice = (voice_name or '').rsplit('|', 1)[-1].strip()
    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)
    
    try:
        spd_val = float(speed or 1.0)
    except (TypeError, ValueError):
        spd_val = 1.0

    engine.synthesize(text = text, voice = clean_voice, speed = spd_val, out_path = str(output))
    return output


def download_zerotts_voice_preview(voice_name: str, output: 'str | Path') -> Path:
    '''Phát mẫu nghe thử của ZeroTTS: ưu tiên file đóng gói sẵn 0ms.'''
    # TODO(khôi phục hành vi): file decompile dừng ngay dòng def — thân hàm (~175
    # instruction) không được sinh ra.
    raise NotImplementedError('chưa khôi phục từ bytecode: cloud_voice.download_zerotts_voice_preview')


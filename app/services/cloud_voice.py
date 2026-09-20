# Source Generated with Decompyle++
# File: cloud_voice.pyc (Python 3.12)

'''Cloud voice providers used by Mumu Studio.

Providers are independent:
  - Edge TTS  → free Microsoft voices (edge_tts_engine.py)
  - CapCut    → CapCut common_task TTS (capcut_tts_engine.py)
  - ElevenLabs → REST binary TTS + Scribe STT (this module)
  - Google Cloud TTS → official Google client, including Chirp3-HD voices

Keys live outside render configs in ``~/.mumu``.  This keeps API secrets out of
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
import urllib.error as urllib
import urllib.parse as urllib
import urllib.request as urllib
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
    return Path.home() / '.mumu' / f'''{name}.txt'''


def get_secret(name = None, env_name = None):
    if not os.environ.get(env_name):
        os.environ.get(env_name)
    value = ''.strip()
    if value:
        return value
    path = None(name)
    if path.is_file():
        return path.read_text(encoding = 'utf-8').strip()


def set_secret(name = None, env_name = None, value = None):
    if not value:
        value
    value = ''.strip()
    os.environ[env_name] = value
    path = _secret_path(name)
    path.parent.mkdir(parents = True, exist_ok = True)
    if value:
        path.write_text(value, encoding = 'utf-8')
        return None
    if path.exists():
        path.unlink()
        return None


def get_elevenlabs_api_key():
    val = get_secret('elevenlabs_api_key', 'MUMU_ELEVENLABS_API_KEY')
    if val:
        return val
    cfg_candidates = [
        None.cwd() / 'config.json',
        Path(__file__).resolve().parents[3] / 'config.json']
    if getattr(sys, 'frozen', False):
        cfg_candidates.insert(0, Path(sys.executable).resolve().parent / 'config.json')
# WARNING: Decompyle incomplete


def _split_elevenlabs_api_keys(value = None):
    """One secret per line, unique and in the user's preferred order."""
    seen = set()
    result = []
    if not value:
        value
    for raw in ''.splitlines():
        key = raw.strip()
        if not key:
            continue
        if not key not in seen:
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
    _ELEVEN_KEY_LOCK
    _ELEVEN_KEY_CURSOR = 0
    _ELEVEN_KEY_COOLDOWN.clear()
    None(None, None)
    return None
    with None:
        if not None:
            pass


def save_elevenlabs_api_key(key = None):
    keys = _split_elevenlabs_api_keys(key)
    normalized = '\n'.join(keys)
    set_secret('elevenlabs_api_key', 'MUMU_ELEVENLABS_API_KEY', normalized)
    _reset_elevenlabs_key_rotation()
    cfg_candidates = [
        Path.cwd() / 'config.json',
        Path(__file__).resolve().parents[3] / 'config.json']
    if getattr(sys, 'frozen', False):
        cfg_candidates.insert(0, Path(sys.executable).resolve().parent / 'config.json')
# WARNING: Decompyle incomplete

_GOOGLE_CHIRP3_HD_STYLES: 'tuple[tuple[str, str], ...]' = (('Achernar', 'FEMALE'), ('Achird', 'MALE'), ('Algenib', 'MALE'), ('Algieba', 'MALE'), ('Alnilam', 'MALE'), ('Aoede', 'FEMALE'), ('Autonoe', 'FEMALE'), ('Callirrhoe', 'FEMALE'), ('Charon', 'MALE'), ('Despina', 'FEMALE'), ('Enceladus', 'MALE'), ('Erinome', 'FEMALE'), ('Fenrir', 'MALE'), ('Gacrux', 'FEMALE'), ('Iapetus', 'MALE'), ('Kore', 'FEMALE'), ('Laomedeia', 'FEMALE'), ('Leda', 'FEMALE'), ('Orus', 'MALE'), ('Puck', 'MALE'), ('Pulcherrima', 'FEMALE'), ('Rasalgethi', 'MALE'), ('Sadachbia', 'MALE'), ('Sadaltager', 'MALE'), ('Schedar', 'MALE'), ('Sulafat', 'FEMALE'), ('Umbriel', 'MALE'), ('Vindemiatrix', 'FEMALE'), ('Zephyr', 'FEMALE'), ('Zubenelgenubi', 'MALE'))

def _google_voice_label(name = None, gender = None):
    if not gender:
        gender
    if not ''.split('.')[-1].upper():
        ''.split('.')[-1].upper()
    gender = '?'
    style = name.rsplit('-', 1)[-1] if name else ''
    if gender == 'FEMALE':
        pass
    elif gender == 'MALE':
        pass
    
    gender_vi = gender
    return f'''{style} ({gender_vi}) · {name} | {name}'''


def get_google_tts_credentials_path():
    '''Return a service-account JSON path without ever reading/storing its key.

    ``GOOGLE_APPLICATION_CREDENTIALS`` remains supported for deployments.  The
    desktop setting is only a local path in ``~/.mumu`` so render configs and
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
    
    try:
        texttospeech = texttospeech
        import google.cloud
        credential_path = get_google_tts_credentials_path()
        if credential_path:
            path = Path(credential_path).expanduser()
            if not path.is_file():
                raise RuntimeError('Không tìm thấy file Service Account JSON của Google Cloud. Chọn lại file trong Cài đặt.')
            
            try:
                service_account = service_account
                import google.oauth2
                credentials = service_account.Credentials.from_service_account_file(str(path))
                return texttospeech.TextToSpeechClient(credentials = credentials)
                
                try:
                    return texttospeech.TextToSpeechClient()
                    except ImportError:
                        exc = None
                        raise RuntimeError('Chưa cài Google Cloud TTS. Chạy: pip install -r requirements.txt'), exc
                        exc = None
                        del exc
                    except Exception:
                        exc = None
                        raise RuntimeError(f'''Không mở được Service Account JSON Google: {exc}'''), exc
                        exc = None
                        del exc
                except Exception:
                    exc = None
                    raise RuntimeError(f'''Chọn Service Account JSON trong Cài đặt, hoặc đặt GOOGLE_APPLICATION_CREDENTIALS. Chi tiết: {exc}'''), exc
                    exc = None
                    del exc





def list_google_cloud_voices(*, live):
    '''List Vietnamese Chirp3-HD voices.

    With credentials, prefer the live API list for the current project.
    Without credentials (or on API failure), return the official offline catalog
    so the UI still shows every vi-VN-Chirp3-HD style.
    '''
    if not live or get_google_tts_credentials_path():
        return list_google_cloud_voices_catalog()
    
    try:
        client = _google_tts_client()
        response = client.list_voices(language_code = 'vi-VN')
        records = []
        for voice in response.voices:
            if not getattr(voice, 'name', ''):
                getattr(voice, 'name', '')
            name = str('')
            if 'Chirp3-HD' not in name:
                continue
            if not getattr(voice, 'ssml_gender', ''):
                getattr(voice, 'ssml_gender', '')
            gender = str('').split('.')[-1]
            records.append((_google_voice_label(name, gender), name))
        if not records:
            logger.warning('Google list_voices returned no Chirp3-HD; using local catalog')
            return list_google_cloud_voices_catalog()
        return None(records, key = (lambda item: item[1]))
    except Exception:
        exc = None
        logger.warning('Google list_voices failed; using local Chirp3-HD catalog: %s', exc)
        del exc
        return None
        None = 
        del exc



def google_cloud_tts_generate(text = None, output = None, *, voice_name, speed):
    '''Synthesize a single cue to MP3 using Google Cloud Chirp3-HD.'''
    del speed
    
    try:
        texttospeech = texttospeech
        import google.cloud
        if not text:
            text
        text = ''.strip()
        if not text:
            raise RuntimeError('Không có nội dung để đọc.')
        if not voice_name:
            voice_name
        voice_name = ''.rsplit('|', 1)[-1].strip()
        if not voice_name.startswith('vi-VN-Chirp3-HD-'):
            raise RuntimeError('Chọn một giọng vi-VN-Chirp3-HD trong danh sách (hoặc bấm «Tải giọng») trước khi render.')
        
        try:
            response = _google_tts_client().synthesize_speech(input = texttospeech.SynthesisInput(text = text), voice = texttospeech.VoiceSelectionParams(language_code = 'vi-VN', name = voice_name), audio_config = texttospeech.AudioConfig(audio_encoding = texttospeech.AudioEncoding.MP3))
            if not response.audio_content:
                raise RuntimeError('Google Cloud TTS trả audio rỗng.')
            output = Path(output)
            output.parent.mkdir(parents = True, exist_ok = True)
            output.write_bytes(response.audio_content)
            return output
            except ImportError:
                exc = None
                raise RuntimeError('Chưa cài Google Cloud TTS. Chạy: pip install -r requirements.txt'), exc
                exc = None
                del exc
        except Exception:
            exc = None
            raise RuntimeError(f'''Google Cloud TTS tạo audio thất bại: {exc}'''), exc
            exc = None
            del exc




def _json_request(url = None, *, method, headers, body, timeout):
    pass
# WARNING: Decompyle incomplete


def _parse_eleven_error(detail = None, code = None):
    '''Map ElevenLabs JSON error body → human message (VN).

    HTTP 402 is NOT always “hết credit”. Free tier often gets 402 for
    library/shared voices used via API even when characters remain.
    '''
    msg = ''
    status = ''
    err_code = ''
    
    try:
        payload = json.loads(detail)
        d = payload.get('detail') if isinstance(payload, dict) else None
        if isinstance(d, dict):
            if not d.get('message'):
                d.get('message')
            msg = str('').strip()
            if not d.get('status'):
                d.get('status')
                if not d.get('type'):
                    d.get('type')
            status = str('').strip()
            if not d.get('code'):
                d.get('code')
            err_code = str('').strip()
        elif isinstance(d, str):
            msg = d.strip()
        low = f'''{msg} {status} {err_code}'''.casefold()
        if ('invalid_api_key' in low or code in frozenset({401, 400})) and 'invalid' in low and 'api' in low:
            return 'ElevenLabs API key không hợp lệ. Hãy dán secret key được hiển thị khi tạo/rotate key; API Key ID không dùng để gọi API. Nếu đã nhập nhiều key, app sẽ tự thử dòng kế tiếp.'
        if 'paid_plan_required' in low and 'library voices' in low or 'free users cannot' in low:
            if not msg:
                msg
            return f'''ElevenLabs (402): gói Free không dùng được voice thư viện/library qua API.\n→ Bấm «Tải giọng» rồi chọn giọng có sẵn trong account (premade/cloned), hoặc nâng cấp gói, hoặc clone voice về My Voices.\nChi tiết: {detail[:300]}'''
        if None in low and 'quota' in low or 'credit' in low:
            if not msg:
                msg
            return f'''ElevenLabs hết character/credit (HTTP {code}): {detail[:300]}'''
        if None == 429:
            return f'''ElevenLabs rate-limit (429). Thử lại sau vài giây. {msg}'''.strip()
        if None == 422:
            if not msg:
                msg
            return f'''ElevenLabs từ chối request (422): {detail[:400]}'''
        if None:
            return f'''ElevenLabs HTTP {code}: {msg}'''
        return f'''{code}: {detail[:400]}'''
    except Exception:
        if not detail:
            detail
        msg = ''.strip()[:400]
        continue



def _binary_request(url = None, *, method, headers, body, timeout):
    pass
# WARNING: Decompyle incomplete


def _clamp01(value = None, default = None):
    
    try:
        return max(0, min(1, float(value)))
    except (TypeError, ValueError):
        return 



def _clamp_speed(value = None, default = None):
    '''ElevenLabs speed is typically ~0.7–1.2; clamp wider for safety.'''
    pass
# WARNING: Decompyle incomplete


def build_voice_settings(*, stability, similarity_boost, style, use_speaker_boost, speed):
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
            return 


    settings = {
        'stability': _norm(stability, 0.5),
        'similarity_boost': _norm(similarity_boost, 0.75),
        'style': _norm(style, 0),
        'use_speaker_boost': bool(use_speaker_boost) }
# WARNING: Decompyle incomplete


class ElevenLabsTTSClient:
    '''Production ElevenLabs surface used by Mumu (desktop, no tkinter).

    Methods mirror the integration contract:
      synthesize / get_voice / search_voices / list_models / validate_api_key
    '''
    
    def __init__(self = None, api_key = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _require_key(self = None):
        if not self.api_key:
            raise RuntimeError('Thiếu ElevenLabs API key trong Cài đặt (hoặc env MUMU_ELEVENLABS_API_KEY).')
        return self.api_key

    
    def _headers(self = None, *, accept, content_type):
        headers = {
            'xi-api-key': self._require_key() }
        if content_type:
            headers['Content-Type'] = content_type
        if accept:
            headers['Accept'] = accept
        return headers

    
    def synthesize(self = None, text = None, voice_id = None, *, model_id, settings, output_format, timeout):
        '''POST /v1/text-to-speech/{voice_id} → MP3 bytes.

        Does **not** use history_item_id / download flow.
        '''
        if not text:
            text
        text = ''.strip()
        if not text:
            raise ValueError('text rỗng — không TTS được.')
        if not voice_id:
            voice_id
        voice_id = ''.strip()
        if not voice_id:
            raise RuntimeError('Chọn hoặc tải giọng ElevenLabs trước khi render.')
        if not model_id:
            model_id
        model_id = ELEVEN_DEFAULT_MODEL_ID.strip()
        body = {
            'text': text,
            'model_id': model_id }
        if settings:
            body['voice_settings'] = settings
        query = urllib.parse.urlencode({
            'output_format': output_format })
        url = f'''{ELEVEN_BASE_URL}/text-to-speech/{urllib.parse.quote(voice_id)}?{query}'''
        audio = _binary_request(url, method = 'POST', headers = self._headers(accept = 'audio/mpeg'), body = body, timeout = timeout)
        if audio or len(audio) < 128:
            raise RuntimeError('ElevenLabs trả audio rỗng.')
        return audio

    
    def synthesize_to_file(self = None, text = None, output = None, *, voice_id, model_id, settings, output_format):
        audio = self.synthesize(text, voice_id, model_id = model_id, settings = settings, output_format = output_format)
        output = Path(output)
        output.parent.mkdir(parents = True, exist_ok = True)
        output.write_bytes(audio)
        return output

    
    def get_voice(self = None, voice_id = None):
        '''GET /v1/voices/{voice_id} → name, preview_url, labels, settings…'''
        if not voice_id:
            voice_id
        voice_id = ''.strip()
        if not voice_id:
            raise ValueError('voice_id rỗng.')
        payload = _json_request(f'''{ELEVEN_BASE_URL}/voices/{urllib.parse.quote(voice_id)}''', headers = self._headers(content_type = None), timeout = 30)
    # WARNING: Decompyle incomplete

    _normalize_voice = (lambda voice = None: if not voice:
{ }if not voice.get('voice_id'):
voice.get('voice_id')if not voice.get('id'):
voice.get('id')if not voice.get('name'):
voice.get('name')if not voice.get('category'):
voice.get('category')if not voice.get('description'):
voice.get('description'){
'voice_id': None('').strip(),
'name': str('').strip(),
'preview_url': voice.get('preview_url'),
'category': str('').strip(),
'description': str('')[:120],
'info': voice })()
    
    def search_voices(self = None, query = None, *, page_size):
        '''GET /v2/voices?search=… (falls back to /v1/voices).'''
        headers = self._headers(content_type = None)
        page_size = max(1, min(100, int(page_size)))
        params = {
            'page_size': str(page_size) }
        if not query:
            query
        if ''.strip():
            params['search'] = query.strip()
        qs = urllib.parse.urlencode(params)
    # WARNING: Decompyle incomplete

    
    def search_voices_by_query(self = None, query = None, *, page_size):
        '''Tìm voice theo Voice ID hoặc tên/từ khóa.

        Thứ tự (giống tts_tool_elevenLabs/voice_fetcher):
          1) exact ID  GET /v1/voices/{id}
          2) account   GET /v2/voices?search=
          3) library   GET /v1/shared-voices?search=
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def list_voices(self = None):
        '''Friendly labels for UI OptionMenu: ``Name | voice_id`` → voice_id.'''
        voices = self.search_voices('')
        result = []
        for item in voices:
            if not item.get('voice_id'):
                item.get('voice_id')
            voice_id = str('').strip()
            if not item.get('name'):
                item.get('name')
            name = str(voice_id).strip()
            if not voice_id:
                continue
            result.append((f'''{name} | {voice_id}''', voice_id))
        if not result:
            raise RuntimeError('ElevenLabs không trả về giọng nào cho API key này.')
        return result

    
    def list_models(self = None):
        '''GET /v1/models, filter can_do_text_to_speech.'''
        payload = _json_request(f'''{ELEVEN_BASE_URL}/models''', headers = self._headers(content_type = None), timeout = 30)
        models = payload if isinstance(payload, list) else []
    # WARNING: Decompyle incomplete

    
    def list_model_choices(self = None):
        '''UI labels: ``(label_with_id, model_id)``. Live API with static fallback.'''
        pass
    # WARNING: Decompyle incomplete

    
    def validate_api_key(self = None):
        '''Light call (models) so invalid keys fail early.'''
        self.list_models()
        return True

    
    def transcribe(self = None, media_path = None, *, language, model_id, timestamps_granularity):
        if not model_id:
            model_id
        fields = {
            'model_id': ELEVEN_STT_MODEL_ID,
            'timestamps_granularity': timestamps_granularity }
        if language:
            fields['language_code'] = language
        (data, boundary) = _multipart_body(fields, 'file', Path(media_path))
        req = urllib.request.Request(f'''{ELEVEN_BASE_URL}/speech-to-text''', data = data, method = 'POST', headers = {
            'xi-api-key': self._require_key(),
            'Content-Type': f'''multipart/form-data; boundary={boundary}''' })
        
        try:
            response = urllib.request.urlopen(req, timeout = 600)
            
            try:
                None(None, None)
                return 
                with None:
                    if not None, json.loads(response.read().decode('utf-8')):
                        pass
                
                try:
                    return None
                    
                    try:
                        pass
                    except urllib.error.HTTPError:
                        exc.read().decode('utf-8', errors = 'replace')[:600] = None
                        raise RuntimeError(f'''ElevenLabs STT HTTP {exc.code}: {detail}'''), exc
                        exc = None
                        del exc
                        except urllib.error.URLError:
                            exc = None
                            raise RuntimeError(f'''Không kết nối được ElevenLabs STT: {exc.reason}'''), exc
                            exc = None
                            del exc







def _eleven_key_fingerprint(key = None):
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]


def _eleven_key_failover_error(error = None):
    pass
# WARNING: Decompyle incomplete


def _eleven_key_cooldown(error = None):
    text = str(error).casefold()
    if 'invalid' in text and '401' in text or 'authentication' in text:
        return 3600
    if 'quota' in text and 'credit' in text or '402' in text:
        return 900
    return 60


def _with_elevenlabs_key(operation = None, *, label):
    '''Run one ElevenLabs operation with persistent round-robin key failover.'''
    keys = get_elevenlabs_api_keys()
    if not keys:
        raise RuntimeError('Thiếu ElevenLabs API key. Mở Cài đặt và dán mỗi secret key trên một dòng.')
    now = time.monotonic()
    _ELEVEN_KEY_LOCK
    start = _ELEVEN_KEY_CURSOR % len(keys)
# WARNING: Decompyle incomplete


def list_elevenlabs_voices():
    return _with_elevenlabs_key((lambda client: client.list_voices()), label = 'tải giọng')


def get_elevenlabs_subscription(api_key = None):
    '''Lấy thông tin số dư (Subscription & Quota) của API key từ ElevenLabs.'''
    if not api_key:
        api_key
    key = get_elevenlabs_api_key().strip()
    if not key:
        return {
            'ok': False,
            'error': 'Chưa có API key' }
    keys = None(key)
    target_key = keys[0] if keys else key
    url = f'''{ELEVEN_BASE_URL}/user/subscription'''
    req = urllib.request.Request(url, headers = {
        'xi-api-key': target_key })
    
    try:
        resp = urllib.request.urlopen(req, timeout = 15)
        data = json.loads(resp.read().decode('utf-8'))
        char_count = int(data.get('character_count', 0))
        char_limit = int(data.get('character_limit', 0))
        remaining = max(0, char_limit - char_count)
        tier = data.get('tier', 'free')
        status = data.get('status', 'active')
        pct = round((char_count / char_limit) * 100, 1) if char_limit > 0 else 100
        
        try:
            None(None, None)
            return 
            with None:
                if not None, {
                    'ok': True,
                    'character_count': char_count,
                    'character_limit': char_limit,
                    'remaining': remaining,
                    'tier': tier,
                    'status': status,
                    'percent_used': pct,
                    'next_invoice': data.get('next_invoice', { }) }:
                    pass
            
            try:
                return None
                
                try:
                    pass
                except urllib.error.HTTPError:
                    exc.read().decode('utf-8', errors = 'replace')[:500] = None
                    del exc
                    return None
                    None = 
                    del exc
                    except Exception:
                        exc = None
                        del exc
                        return None
                        None = 
                        del exc






def validate_elevenlabs_api_keys(value = None):
    '''Validate each configured secret independently and return real quota / balance details.'''
    pass
# WARNING: Decompyle incomplete


def search_elevenlabs_voices(query = None, *, page_size):
    '''Public helper: search by Voice ID or name keyword (for UI Search box).'''
    pass
# WARNING: Decompyle incomplete


def list_elevenlabs_models():
    '''Return ``(label, model_id)`` for the TTS model OptionMenu.'''
    if get_elevenlabs_api_keys():
        return _with_elevenlabs_key((lambda client: client.list_model_choices()), label = 'tải model')
# WARNING: Decompyle incomplete


def download_elevenlabs_voice_preview(voice_id = None, output = None):
    """Download ElevenLabs' existing voice preview without spending TTS characters."""
    pass
# WARNING: Decompyle incomplete


def elevenlabs_tts_generate(text = None, output = None, *, voice_id, speed, model_id, stability, similarity_boost, style, use_speaker_boost):
    '''Synthesize one line → MP3 file (render pipeline entry point).'''
    pass
# WARNING: Decompyle incomplete


def make_cloud_tts(provider = None, voice_id = None, speed = None, *, model_id, stability, similarity_boost, style, use_speaker_boost, capcut_strict, capcut_fast_mode, cancel_event, fix_shark_enabled, fix_shark_path, fix_shark_device_path):
    '''Build a ``(text, path) -> path`` callable for AudioSyncEngine.

    Edge TTS is handled outside this module.  CapCut / ElevenLabs / Google stay
    independent — only the selected provider is wired.
    '''
    pass
# WARNING: Decompyle incomplete


def _multipart_body(fields = None, file_field = None, file_path = None):
    boundary = f'''----Mumu{uuid.uuid4().hex}'''
    chunks = []
    for key, value in fields.items():
        chunks.extend((f'''--{boundary}\r\n'''.encode(), f'''Content-Disposition: form-data; name="{key}"\r\n\r\n'''.encode(), str(value).encode('utf-8'), b'\r\n'))
    chunks.extend((f'''--{boundary}\r\n'''.encode(), f'''Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'''.encode(), b'Content-Type: application/octet-stream\r\n\r\n', file_path.read_bytes(), b'\r\n', f'''--{boundary}--\r\n'''.encode()))
    return (b''.join(chunks), boundary)


def elevenlabs_transcribe_to_srt(media_path = None, out_srt = None, *, language):
    '''STT via Scribe — model is fixed to scribe_v2 (not a TTS model).'''
    pass
# WARNING: Decompyle incomplete


def _get_vieneu_engine():
    
    try:
        VieneuEngine = VieneuEngine
        import app.services.voice_engine.vieneu_engine
        return VieneuEngine()
    except Exception:
        exc = None
        logger.warning('Không thể khởi tạo VieneuEngine: %s', exc)
        exc = None
        del exc
        return None
        exc = None
        del exc



def list_vieneu_voices():
    '''Trả về danh sách 20 giọng preset + các giọng cá nhân đã nhân bản.'''
    results = []
    
    try:
        PRESET_VOICES = PRESET_VOICES
        import app.services.voice_engine.voices_config
        for v in PRESET_VOICES:
            name = v['name']
            label = v['label']
            results.append((f'''{label} | {name}''', name))
        engine = _get_vieneu_engine()
        if engine:
            for cloned in engine.list_cloned_voices():
                results.append((f'''🧬 [Clone] {cloned} | {cloned}''', cloned))
        return results
    except Exception:
        exc = None
        logger.warning('Không thể đọc PRESET_VOICES: %s', exc)
        exc = None
        del exc
        continue
        exc = None
        del exc



def vieneu_tts_generate(text = None, output = None, *, voice_name, temperature):
    '''Tổng hợp câu thoại bằng VieNeu-TTS v3 Turbo local'''
    if not text:
        text
    text = ''.strip()
    if not text:
        raise ValueError('Văn bản rỗng, không thể tổng hợp bằng VieNeu.')
    engine = _get_vieneu_engine()
    if not engine:
        raise RuntimeError('VieNeu-TTS engine chưa sẵn sàng hoặc thiếu thư viện vieneu.')
    if not voice_name:
        voice_name
    clean_voice = ''.rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)
    engine.synthesize(text = text, voice = clean_voice, temperature = temperature, out_path = str(output))
    return output


def download_vieneu_voice_preview(voice_name = None, output = None):
    '''Phát mẫu nghe thử của VieNeu: ưu tiên file pre-generated 0ms'''
    if not voice_name:
        voice_name
    clean_voice = ''.rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
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
        
        return candidates, target
    return vieneu_tts_generate(sample_text, target, voice_name = clean_voice, temperature = 0.7)


def _get_zerotts_engine():
    
    try:
        ZeroTTSEngine = ZeroTTSEngine
        import app.services.voice_engine.zerotts_engine
        return ZeroTTSEngine()
    except Exception:
        exc = None
        logger.warning('Không thể khởi tạo ZeroTTSEngine: %s', exc)
        exc = None
        del exc
        return None
        exc = None
        del exc



def list_zerotts_voices():
    '''Trả về danh sách 8 giọng preset chuẩn của ZeroTTS.'''
    engine = _get_zerotts_engine()
    if engine:
        return engine.list_voice_tuples()


def zerotts_tts_generate(text = None, output = None, *, voice_name, speed):
    '''Tổng hợp giọng đọc bằng ZeroTTS AI offline 48kHz.'''
    if not text:
        text
    text = ''.strip()
    if not text:
        raise ValueError('Văn bản rỗng, không thể tổng hợp bằng ZeroTTS.')
    engine = _get_zerotts_engine()
    if not engine:
        raise RuntimeError('ZeroTTS engine chưa sẵn sàng hoặc thiếu thư viện.')
    if not voice_name:
        voice_name
    clean_voice = ''.rsplit('|', 1)[-1].strip()
    output = Path(output)
    output.parent.mkdir(parents = True, exist_ok = True)
    
    try:
        if not speed:
            speed
        spd_val = float(1)
        engine.synthesize(text = text, voice = clean_voice, speed = spd_val, out_path = str(output))
        return output
    except (TypeError, ValueError):
        spd_val = 1
        continue



def download_zerotts_voice_preview(voice_name = None, output = None):

import requests
import tkinter as tk
import websocket
import json
import os
import tkinter.ttk as ttk

class ElevenLabsApiError(Exception):
    '''
    Lớp ngoại lệ chi tiết cho lỗi ElevenLabs API chứa đầy đủ thuộc tính:
    status_code, code, type, message, request_id, param, raw_text.
    '''

    def __init__(self, status_code: int, error_data: dict, raw_text: str = ''):
        self.status_code = status_code
        self.error_data = error_data if isinstance(error_data, dict) else {}
        self.raw_text = raw_text
        detail = self.error_data.get('detail', {})
        if isinstance(detail, dict):
            self.code = detail.get('code') or detail.get('status') or 'unknown_error'
            self.type = detail.get('type') or 'api_error'
            self.message = detail.get('message') or raw_text
            self.request_id = detail.get('request_id') or ''
            self.param = detail.get('param') or ''
        elif isinstance(detail, str):
            self.code = 'unknown_error'
            self.type = 'api_error'
            self.message = detail
            self.request_id = ''
            self.param = ''
        else:
            self.code = 'unknown_error'
            self.type = 'api_error'
            self.message = raw_text
            self.request_id = ''
            self.param = ''
        super().__init__(self.message)


def get_headers(api_key):
    return {
        'Content-Type': 'application/json',
        'xi-api-key': api_key.strip() }


def _handle_api_error(resp):
    try:
        data = resp.json()
        raise ElevenLabsApiError(resp.status_code, data, resp.text)
    except ElevenLabsApiError:
        raise
    except Exception:
        raise ElevenLabsApiError(resp.status_code, {}, resp.text)


def get_voice_info_by_id(voice_id: str, api_key: str, public_user_id: str = None) -> dict:
    '''
    Lấy thông tin voice (name, preview_url, ...) từ voice_id.
    1. Thử lấy trực tiếp từ /v1/voices/{voice_id} (voices trong tài khoản / premade).
    2. Nếu không có, tìm kiếm trong /v1/shared-voices (Voice Library).
    3. Nếu có public_user_id, thử similar-voices-by-id.
    '''
    voice_id = voice_id.strip()
    api_key = api_key.strip()
    if not api_key:
        raise ElevenLabsApiError(400, {
            'detail': {
                'code': 'missing_api_key',
                'type': 'authentication_error',
                'message': 'Chưa nhập ElevenLabs API Key.',
                'param': 'api_key' } })
    if not api_key.startswith('sk_'):
        raise ElevenLabsApiError(400, {
            'detail': {
                'code': 'api_key_id_used_as_api_key',
                'type': 'authentication_error',
                'message': "API key ID used as API key - only valid API keys can be used. API keys start with 'sk_'.",
                'param': 'api_key' } })
    headers = get_headers(api_key)
    # 1. Giọng của tài khoản / premade
    url_direct = f'''https://api.elevenlabs.io/v1/voices/{voice_id}'''
    try:
        resp = requests.get(url_direct, headers = headers)
        if resp.status_code == 200:
            voice = resp.json()
            return {
                'name': voice.get('name'),
                'preview_url': voice.get('preview_url'),
                'info': voice }
        if resp.status_code in (400, 401, 403):
            _handle_api_error(resp)
    except requests.exceptions.RequestException as req_err:
        if hasattr(req_err, 'response') and req_err.response is not None:
            _handle_api_error(req_err.response)
        raise
    # 2. Similar voices (cần public_user_id)
    if public_user_id:
        try:
            voices = get_voices_by_similar_id(voice_id, api_key, public_user_id)
            for voice in voices:
                if not voice.get('voice_id') == voice_id:
                    continue
                return {
                    'name': voice.get('name'),
                    'preview_url': voice.get('preview_url'),
                    'info': voice }
            if voices:
                return {
                    'name': voices[0].get('name'),
                    'preview_url': voices[0].get('preview_url'),
                    'info': voices[0] }
        except Exception:
            pass
    # 3. Voice Library (shared-voices)
    url_shared = 'https://api.elevenlabs.io/v1/shared-voices'
    params = {
        'page_size': 30,
        'search': voice_id }
    try:
        resp_shared = requests.get(url_shared, params = params, headers = headers)
        if resp_shared.status_code == 200:
            data = resp_shared.json()
            voices = data.get('voices', [])
            for voice in voices:
                if not voice.get('voice_id') == voice_id:
                    continue
                return {
                    'name': voice.get('name'),
                    'preview_url': voice.get('preview_url'),
                    'info': voice }
            if voices:
                return {
                    'name': voices[0].get('name'),
                    'preview_url': voices[0].get('preview_url'),
                    'info': voices[0] }
        elif resp_shared.status_code in (400, 401, 403):
            _handle_api_error(resp_shared)
    except requests.exceptions.RequestException as req_err:
        if hasattr(req_err, 'response') and req_err.response is not None:
            _handle_api_error(req_err.response)
        raise
    return None


def get_voices_by_similar_id(voice_id, api_key, public_user_id):
    url = 'https://api.us.elevenlabs.io/v1/similar-voices-by-id'
    payload = {
        'voice_id': voice_id.strip(),
        'public_user_id': public_user_id.strip() }
    headers = get_headers(api_key)
    print('Payload:', payload)
    print('Headers:', headers)
    resp = requests.post(url, json = payload, headers = headers)
    print('Status code:', resp.status_code)
    print('Response text:', resp.text)
    resp.raise_for_status()
    data = resp.json()
    if data and isinstance(data, dict) and 'voices' in data:
        return data['voices']
    return []


def find_voice_in_list(voices, voice_id):
    for voice in voices:
        if not voice.get('voice_id') == voice_id:
            continue
        return voice
    return None


def get_voice_info_auto(voice_id, api_key, public_user_id = None):
    if public_user_id:
        info = get_voices_by_similar_id(voice_id, api_key, public_user_id)
        if info:
            return info
    url = 'https://api.us.elevenlabs.io/v1/shared-voices'
    params = {
        'page_size': 30,
        'category': 'professional',
        'search': voice_id,
        'sort': 'trending',
        'min_notice_period_days': 0 }
    headers = get_headers(api_key)
    resp = requests.get(url, params = params, headers = headers)
    resp.raise_for_status()
    data = resp.json()
    for voice in data.get('voices', []):
        if not voice.get('voice_id') == voice_id:
            continue
        return voice
    return None


def get_voice_info_public(voice_id, api_key):
    url = 'https://api.us.elevenlabs.io/v1/shared-voices'
    params = {
        'page_size': 30,
        'category': 'professional',
        'search': voice_id,
        'sort': 'trending',
        'min_notice_period_days': 0 }
    headers = get_headers(api_key)
    resp = requests.get(url, params = params, headers = headers)
    resp.raise_for_status()
    data = resp.json()
    for voice in data.get('voices', []):
        if not voice.get('voice_id') == voice_id:
            continue
        return voice
    return None


def search_voice(voice_id, api_key):
    url = 'https://api.elevenlabs.io/v2/voices'
    headers = get_headers(api_key)
    params = {
        'search': voice_id,
        'page_size': 10 }
    resp = requests.get(url, headers = headers, params = params)
    resp.raise_for_status()
    return resp.json()


def get_voice_metadata(voice_id, api_key):
    url = f'''https://api.elevenlabs.io/v1/voices/{voice_id}'''
    headers = get_headers(api_key)
    resp = requests.get(url, headers = headers)
    resp.raise_for_status()
    return resp.json()


def synthesize_speech(voice_id, text, api_key, model_id = 'eleven_v3', voice_settings = None):
    url = f'''https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'''
    headers = get_headers(api_key)
    data = {
        'text': text,
        'model_id': model_id }
    if voice_settings:
        data['voice_settings'] = voice_settings
    response = requests.post(url, headers = headers, json = data)
    if response.status_code != 200:
        _handle_api_error(response)
    return response.content


def get_user_subscription(api_key: str) -> dict:
    '''
    Truy vấn số dư credits (Balance) và thông tin gói tài khoản từ ElevenLabs API:
    GET /v1/user/subscription
    Trả về dict:
    {
        "ok": True,
        "tier": "free",
        "character_limit": 10000,
        "character_count": 7476,
        "remaining": 2524,
        "percent_used": 74.8,
        "percent_remaining": 25.2,
        "status": "active"
    }
    '''
    api_key = (api_key or '').strip()
    if not api_key:
        return {
            'ok': False,
            'error': 'Chưa nhập API Key',
            'status': 'missing_key' }
    url = 'https://api.elevenlabs.io/v1/user/subscription'
    headers = get_headers(api_key)
    try:
        resp = requests.get(url, headers = headers, timeout = 12)
        if resp.status_code == 200:
            data = resp.json()
            limit = int(data.get('character_limit') or 0)
            count = int(data.get('character_count') or 0)
            remaining = max(0, limit - count)
            pct_used = round(count / max(1, limit) * 100, 1)
            pct_rem = round(remaining / max(1, limit) * 100, 1)
            tier = data.get('tier') or 'free'
            status = data.get('status') or 'active'
            return {
                'ok': True,
                'tier': tier,
                'character_limit': limit,
                'character_count': count,
                'remaining': remaining,
                'percent_used': pct_used,
                'percent_remaining': pct_rem,
                'status': status,
                'raw': data }
        if resp.status_code in (401, 403):
            return {
                'ok': False,
                'error': 'API Key không hợp lệ hoặc hết hạn',
                'status': 'unauthorized',
                'status_code': resp.status_code }
        return {
            'ok': False,
            'error': f'''Lỗi HTTP {resp.status_code}''',
            'status': 'error',
            'status_code': resp.status_code }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e),
            'status': 'network_error' }


def on_message(ws, message):
    print('Received:', message)


def on_open(ws):
    ws.send(json.dumps({
        'text': ' ',
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.8,
            'speed': 1 } }))
    ws.send(json.dumps({
        'text': 'Hello World',
        'try_trigger_generation': True }))


def create_websocket(voice_id, api_key):
    headers = [
        f'''xi-api-key: {api_key}''']
    ws = websocket.WebSocketApp(f'''wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input''', header = headers, on_message = on_message, on_open = on_open)
    return ws

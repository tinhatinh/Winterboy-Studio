# Source Generated with Decompyle++
# File: tts_generator.pyc (Python 3.12)

import requests
from gui.config import ELEVENLABS_API_KEY, ELEVENLABS_BASE_URL, DEFAULT_MODEL

def generate_tts(text = None, voice_id = None, model_id = None, settings = (None, None)):
    '''
    Gửi yêu cầu tạo TTS, trả về JSON response chứa history_item_id.
    '''
    url = f'''{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}'''
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json' }
    if not model_id:
        model_id
    if not settings:
        settings
# WARNING: Decompyle incomplete


def poll_history(history_item_id = None, timeout = None):
    """
    (Tùy chọn) Poll status của history item nếu cần, ví dụ cho trạng thái 'processing'.
    """
    import time
    url = f'''{ELEVENLABS_BASE_URL}/history/{history_item_id}'''
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY }
    elapsed = 0
    if elapsed < timeout:
        resp = requests.get(url, headers = headers)
        resp.raise_for_status()
        state = resp.json().get('state')
        if state == 'completed' or state == 'created':
            return None
        time.sleep(1)
        elapsed += 1
        if elapsed < timeout:
            continue
    raise TimeoutError(f'''TTS generation chưa hoàn tất sau {timeout}s''')


def text_to_speech_and_download(text = None, voice_id = None, output_dir = None, model_id = (None, None), settings = ('text', str, 'voice_id', str, 'output_dir', str, 'model_id', str | None, 'settings', dict | None, 'return', str)):
    '''
    Tích hợp generate + download: trả về đường dẫn file MP3.
    '''
    result = generate_tts(text, voice_id, model_id, settings)
    history_item_id = result['history_item_id']
    poll_history(history_item_id)
    download_audio = download_audio
    import downloader
    return download_audio(history_item_id, output_dir)


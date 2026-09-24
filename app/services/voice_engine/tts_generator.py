import requests
from ..gui.config import ELEVENLABS_API_KEY, ELEVENLABS_BASE_URL, DEFAULT_MODEL

def generate_tts(text: str, voice_id: str, model_id: str | None = None,
                 settings: dict | None = None) -> dict:
    '''
    Gửi yêu cầu tạo TTS, trả về JSON response chứa history_item_id.
    '''
    url = f'''{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}'''
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY,
        'Content-Type': 'application/json' }
    payload = {
        'text': text,
        'model_id': model_id or DEFAULT_MODEL,
        **(settings or {}) }
    resp = requests.post(url, json = payload, headers = headers)
    resp.raise_for_status()
    return resp.json()


def poll_history(history_item_id: str, timeout: int = 30) -> None:
    """
    (Tùy chọn) Poll status của history item nếu cần, ví dụ cho trạng thái 'processing'.
    """
    import time
    url = f'''{ELEVENLABS_BASE_URL}/history/{history_item_id}'''
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY }
    elapsed = 0
    while elapsed < timeout:
        resp = requests.get(url, headers = headers)
        resp.raise_for_status()
        state = resp.json().get('state')
        if state == 'completed' or state == 'created':
            return
        time.sleep(1)
        elapsed += 1
    raise TimeoutError(f'''TTS generation chưa hoàn tất sau {timeout}s''')


def text_to_speech_and_download(text: str, voice_id: str, output_dir: str,
                                model_id: str | None = None,
                                settings: dict | None = None) -> str:
    '''
    Tích hợp generate + download: trả về đường dẫn file MP3.
    '''
    result = generate_tts(text, voice_id, model_id, settings)
    history_item_id = result['history_item_id']
    poll_history(history_item_id)
    from .downloader import download_audio
    return download_audio(history_item_id, output_dir)

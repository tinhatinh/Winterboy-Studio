'''
stt_service — Dịch vụ trích xuất âm thanh từ Video và nhận dạng tiếng nói (Speech-to-Text).

Học hỏi kiến trúc từ whisper_stt.py và cloud_voice.py của Winterboy studio:
1. Trích xuất âm thanh từ Video (MP4, MKV, MOV, AVI, WEBM,...) bằng FFmpeg:
   Chuyển thành 16kHz Mono PCM WAV nhỏ gọn, tối ưu dung lượng tải lên.
2. Tích hợp trực tiếp ElevenLabs Scribe v2 (POST /v1/speech-to-text):
   - Sử dụng chính API Key ElevenLabs của người dùng.
   - Nhận diện cực nhanh không cần tải model nặng hay GPU.
   - Trả về word timestamps chi tiết (từng từ kèm thời gian bắt đầu và kết thúc).
3. Tự động gom nhóm từ thành các khối phụ đề (SRT Cues):
   - Cắt câu theo dấu câu (. ! ? ;), nhịp ngắt (pause > 0.75s), hoặc tối đa 10-12 từ / 5.5 giây.
   - Tạo file .srt chuẩn UTF-8 và danh sách entries nạp thẳng vào bảng phụ đề của App.
'''
import os
import shutil
import subprocess
import tempfile
import logging
import requests
from typing import Callable, Optional
from app.services.voice_engine.file_handler import seconds_to_srt_timestamp, save_subtitles_to_srt
from app.services.voice_engine.voice_fetcher import ElevenLabsApiError
logger = logging.getLogger(__name__)
ELEVEN_STT_URL = 'https://api.elevenlabs.io/v1/speech-to-text'
ELEVEN_STT_MODEL_ID = 'scribe_v2'

def find_ffmpeg() -> str:
    ff = shutil.which('ffmpeg')
    if ff:
        return ff
    common_paths = [
        os.path.expandvars('%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffmpeg.exe'),
        'C:\\ffmpeg\\bin\\ffmpeg.exe']
    for p in common_paths:
        if not os.path.isfile(p):
            continue
        return p
    raise FileNotFoundError('Không tìm thấy FFmpeg trong hệ thống để tách audio.')


def extract_audio_from_media(media_path: str, out_wav_path: str, sample_rate: int = 16000) -> str:
    '''
    Dùng FFmpeg trích xuất luồng audio từ file Video/Audio thành file WAV 16kHz mono.
    '''
    ffmpeg_bin = find_ffmpeg()
    os.makedirs(os.path.dirname(os.path.abspath(out_wav_path)), exist_ok = True)
    cmd = [
        ffmpeg_bin,
        '-y',
        '-i',
        media_path,
        '-vn',
        '-ac',
        '1',
        '-ar',
        str(sample_rate),
        '-c:a',
        'pcm_s16le',
        out_wav_path]
    p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0 or not os.path.isfile(out_wav_path):
        err = (p.stderr or p.stdout or '')[-400:]
        raise RuntimeError(f'''FFmpeg trích xuất audio thất bại: {err}''')
    return out_wav_path


def transcribe_elevenlabs_scribe(audio_path: str, api_key: str,
                                 language_code: Optional[str] = None) -> dict:
    '''
    Gửi file âm thanh đến ElevenLabs Scribe v2 API để nhận dạng tiếng nói kèm word timestamps.
    '''
    api_key = (api_key or '').strip()
    if not api_key:
        raise ElevenLabsApiError(400, {
            'detail': {
                'code': 'missing_api_key',
                'type': 'authentication_error',
                'message': 'Vui lòng nhập ElevenLabs API Key trước khi nhận diện giọng nói.' } })
    headers = {
        'xi-api-key': api_key }
    data = {
        'model_id': ELEVEN_STT_MODEL_ID,
        'timestamps_granularity': 'word' }
    if language_code and language_code.strip():
        data['language_code'] = language_code.strip()
    with open(audio_path, 'rb') as f:
        files = {
            'file': (os.path.basename(audio_path), f, 'audio/wav') }
        resp = requests.post(ELEVEN_STT_URL, headers = headers, data = data, files = files, timeout = 600)
    if resp.status_code != 200:
        try:
            err_data = resp.json()
            raise ElevenLabsApiError(resp.status_code, err_data, resp.text)
        except ElevenLabsApiError:
            raise
        except Exception:
            raise ElevenLabsApiError(resp.status_code, {}, resp.text)
    return resp.json()


def words_to_srt_entries(words: list[dict],
                         out_srt_path: Optional[str] = None) -> list[dict]:
    """
    Chuyển danh sách word timestamps từ ElevenLabs Scribe thành các câu phụ đề SRT tự nhiên.
    Mỗi word: {'text': '...', 'start': 1.2, 'end': 1.5, 'type': 'word'}
    """
    valid_words = [
        w for w in words if str(w.get('type', 'word')) == 'word' and str(w.get('text', '')).strip() ]

    if not valid_words:
        return []
    entries = []
    current_words = []
    cue_start = 0.0
    cue_end = 0.0
    last_word_end = 0.0
    # dấu câu được phép kết thúc một câu phụ đề
    punctuation_marks = {
        '.',
        '?',
        '!',
        ';',
        '？',
        '！',
        '。',
        '…' }

    for item in valid_words:
        raw_text = str(item.get('text', '')).strip()
        word_start = float(item.get('start') or 0.0)
        word_end = float(item.get('end') or word_start + 0.15)
        if not current_words:
            cue_start = word_start
            cue_end = word_end
            current_words.append(raw_text)
            last_word_end = word_end
            continue
        pause = word_start - last_word_end
        prev_word = current_words[-1]
        ends_with_punc = any(prev_word.endswith(p) for p in punctuation_marks)
        too_long = len(current_words) >= 12 or word_end - cue_start >= 5.5
        long_pause = pause > 0.75
        if ends_with_punc or long_pause or too_long:
            idx = len(entries) + 1
            entry_text = ' '.join(current_words).strip()
            timing = f'''{seconds_to_srt_timestamp(cue_start)} --> {seconds_to_srt_timestamp(cue_end)}'''
            entries.append({
                'id': idx,
                'text': entry_text,
                'timing': timing,
                'start_s': cue_start,
                'end_s': cue_end,
                'start_ts': seconds_to_srt_timestamp(cue_start),
                'end_ts': seconds_to_srt_timestamp(cue_end) })
            current_words = [ raw_text ]
            cue_start = word_start
            cue_end = word_end
        else:
            current_words.append(raw_text)
            cue_end = max(cue_end, word_end)
        last_word_end = word_end

    if current_words:
        idx = len(entries) + 1
        entry_text = ' '.join(current_words).strip()
        timing = f'''{seconds_to_srt_timestamp(cue_start)} --> {seconds_to_srt_timestamp(cue_end)}'''
        entries.append({
            'id': idx,
            'text': entry_text,
            'timing': timing,
            'start_s': cue_start,
            'end_s': cue_end,
            'start_ts': seconds_to_srt_timestamp(cue_start),
            'end_ts': seconds_to_srt_timestamp(cue_end) })

    if out_srt_path:
        save_subtitles_to_srt(entries, out_srt_path)
    return entries


def import_media_and_transcribe(media_path: str, api_key: str,
                                language_code: Optional[str] = None,
                                out_srt_path: Optional[str] = None,
                                progress_cb: Optional[Callable[[float, str], None]] = None) -> dict:
    '''
    Quy trình một chạm (all-in-one):
    1. Trích xuất audio từ file Video/Audio.
    2. Gửi nhận diện bằng ElevenLabs Scribe v2.
    3. Phân tách và tạo file SRT.
    4. Trả về cấu trúc entries để nạp ngay vào bảng UI.
    '''
    if not os.path.isfile(media_path):
        raise FileNotFoundError(f'''Không tìm thấy file media: {media_path}''')
    base_name = os.path.splitext(os.path.basename(media_path))[0]
    media_dir = os.path.dirname(os.path.abspath(media_path))
    if not out_srt_path:
        out_srt_path = os.path.join(media_dir, f'''{base_name}_subtitles.srt''')
    with tempfile.TemporaryDirectory(prefix = 'winterboy_stt_') as temp_dir:
        temp_wav = os.path.join(temp_dir, f'''{base_name}_16k.wav''')
        if progress_cb:
            progress_cb(0.15, '🎬 Đang trích xuất âm thanh từ video (16kHz Mono)...')
        extract_audio_from_media(media_path, temp_wav)
        if progress_cb:
            progress_cb(0.4, '🧠 Đang gửi âm thanh tới ElevenLabs Scribe v2 STT...')
        stt_result = transcribe_elevenlabs_scribe(temp_wav, api_key, language_code = language_code)
        if progress_cb:
            progress_cb(0.85, '📝 Đang xử lý mốc thời gian và định dạng phụ đề SRT...')
        words = stt_result.get('words', [])
        if not words:
            full_text = (stt_result.get('text') or '').strip()
            if not full_text:
                raise RuntimeError('ElevenLabs Scribe không nhận diện được lời thoại nào trong file.')
            entries = [
                {
                    'id': 1,
                    'text': full_text,
                    'timing': '00:00:00,000 --> 00:00:05,000',
                    'start_s': 0.0,
                    'end_s': 5.0,
                    'start_ts': '00:00:00,000',
                    'end_ts': '00:00:05,000' }]
            save_subtitles_to_srt(entries, out_srt_path)
        else:
            entries = words_to_srt_entries(words, out_srt_path)
        detected_lang = stt_result.get('language_code', language_code or 'auto')
        if progress_cb:
            progress_cb(1.0, f'''✅ Đã tạo thành công {len(entries)} câu phụ đề ({detected_lang})!''')
        return {
            'ok': True,
            'entries': entries,
            'srt_path': out_srt_path,
            'language': detected_lang,
            'total_cues': len(entries),
            'media_path': media_path }

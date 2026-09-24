# Source Generated with Decompyle++
# File: story_image_service.pyc (Python 3.12)

'''Dịch vụ hình ảnh, khớp nối thư mục và đồng bộ timeline/SRT cho AI Storytelling.

Hỗ trợ:
- Gọi API Gemini Imagen 3 để sinh ảnh chất lượng cao theo prompt kịch bản.
- Quét thư mục ảnh người dùng chọn và tự động gán thông minh vào từng Scene.
- Đo thời lượng audio TTS chính xác tới từng mili-giây và khóa cứng timestamp ảnh khớp 100% với SRT.
'''
from __future__ import annotations
import base64
import json
import logging
import math
import os
import re
import urllib.error as urllib
import urllib.request as urllib
from pathlib import Path
from typing import Any, Callable
from app.services.edge_tts_engine import edge_tts_generate, speed_to_edge_rate
from app.services.gemini_translate import get_gemini_api_key
from app.services.media_probe import probe_video_duration_s
logger = logging.getLogger(__name__)
SUPPORTED_IMG_EXTS = {
    '.bmp',
    '.jpg',
    '.jpeg',
    '.webp',
    '.png'}

def _natural_sort_key(s = None):
    '''Sắp xếp chuỗi tự nhiên (scene_1 < scene_2 < scene_10 thay vì 1, 10, 2).'''
    pass
# WARNING: Decompyle incomplete


def extract_scene_index_from_filename(filename = None):
    '''Trích xuất số thứ tự phân cảnh từ tên file ảnh hoặc video.

    Hỗ trợ linh hoạt mọi tiền tố số thứ tự:
    - 01, 001, 1 (chỉ có số: 01.jpeg, 001.png, 1.mp4...)
    - 01_xxx, 001_xxx, 1_xxx, 02-intro, 003.clip, 4 xxx (số ở đầu kèm ký tự phân cách _, -, ., space...)
    - [01], (001), #1, 【02】 (số ở đầu trong ngoặc hoặc dấu #)
    - 01scene, 001video, 1intro (số ở đầu liền kề chữ cái)
    - scene_01, cảnh 002, video_03, vid_004, clip_5, shot_6, img_7, ảnh 08, tap_09, tập 10...
    - forest_01, battle_002, intro_3 (số ở cuối sau ký tự phân cách)
    '''
    stem = Path(filename).stem.strip()
    if not stem:
        return None
    if stem.isdigit():
        if len(stem) <= 4:
            
            try:
                val = int(stem)
                if val < 1900 or val > 2100:
                    return val
            except ValueError:
                pass
        return None
    m = re.match(r'^[\[\(\{#【\s]*(\d+)[\]\)\}】\s._\-]', stem)
    if m:
        digits = m.group(1)
        if len(digits) <= 4:
            
            try:
                val = int(digits)
                if val < 1900 or val > 2100:
                    return val
            except ValueError:
                pass
    m = re.match(r'^[\[\(\{#【\s]*(\d+)(?=[A-Za-z\u00C0-\u024F\u1EA0-\u1EF9])', stem)
    if m:
        digits = m.group(1)
        if len(digits) <= 4:
            
            try:
                val = int(digits)
                if val < 1900 or val > 2100:
                    return val
            except ValueError:
                pass
    m = re.search(r'(?:^|[._\s\-])(?:scene|canh|cảnh|img|image|pic|photo|clip|shot|video|vid|anh|ảnh|tap|tập|part|pt|p|phancanh|phân cảnh)[._\s\-#\[\(]*(\d{1,4})(?!\d)', stem, re.IGNORECASE)
    if m:
        
        try:
            val = int(m.group(1))
            if val < 1900 or val > 2100:
                return val
        except ValueError:
            pass
    m = re.search(r'[._\s\-#\[\(](\d{1,4})[\]\)]?$', stem)
    if m:
        
        try:
            val = int(m.group(1))
            if val < 1900 or val > 2100:
                return val
        except ValueError:
            pass
    nums = re.findall(r'\b\d+\b', stem)
    if len(nums) == 1 and len(nums[0]) <= 4:
        
        try:
            val = int(nums[0])
            if val < 1900 or val > 2100:
                return val
        except ValueError:
            pass
    return None








def media_sort_key(p = None):
    '''Khóa sắp xếp thông minh ưu tiên số thứ tự phân cảnh trích xuất từ tên file.'''
    path_obj = Path(p)
    idx = extract_scene_index_from_filename(path_obj.name)
# WARNING: Decompyle incomplete


def format_srt_timestamp(seconds = None):
    '''Chuyển đổi giây thành định dạng timestamp SRT tiêu chuẩn: HH:MM:SS,mmm.'''
    if seconds < 0:
        seconds = 0
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3600000
    remainder = total_ms % 3600000
    minutes = remainder // 60000
    remainder %= 60000
    secs = remainder // 1000
    milli = remainder % 1000
    return f'''{hours:02d}:{minutes:02d}:{secs:02d},{milli:03d}'''


def format_display_time(seconds = None):
    '''Hiển thị thời gian ngắn gọn trên giao diện: MM:SS.s.'''
    pass
# WARNING: Decompyle incomplete


def generate_gemini_image(prompt = None, output_path = None, api_key = None, aspect_ratio = (None, '16:9', 'imagen-3.0-generate-002'), model = ('prompt', 'str', 'output_path', 'str | Path', 'api_key', 'str | None', 'aspect_ratio', 'str', 'model', 'str', 'return', 'Path')):
    '''Sinh ảnh từ prompt bằng Gemini Imagen 3 API và lưu về file.'''
    prompt = prompt.strip()
    if not prompt:
        raise ValueError('Prompt hình ảnh không được để trống')
    if not api_key:
        api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError('Chưa cấu hình API key Gemini. Hãy cấu hình trong Cài Đặt hoặc biến môi trường.')
    out_file = Path(output_path)
    out_file.parent.mkdir(parents = True, exist_ok = True)
    ar = aspect_ratio.strip()
    if ar not in ('16:9', '9:16', '1:1', '4:3', '3:4'):
        ar = '16:9'
    url = f'''https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}'''
    payload = {
        'instances': [
            {
                'prompt': prompt }],
        'parameters': {
            'sampleCount': 1,
            'aspectRatio': ar,
            'personGeneration': 'ALLOW_ADULT' } }
    req = urllib.request.Request(url, data = json.dumps(payload).encode('utf-8'), headers = {
        'Content-Type': 'application/json' }, method = 'POST')
# WARNING: Decompyle incomplete


def match_folder_images_to_scenes(folder_path = None, scenes = None, project_dir = None):
    '''Quét thư mục ảnh và tự động gán chính xác theo số thứ tự tên file (01, 001, 1...) vào từng phân cảnh.'''
    folder = Path(folder_path)
    if not folder.is_dir():
        return scenes
# WARNING: Decompyle incomplete

assign_images_from_folder = match_folder_images_to_scenes

def assign_image_to_scene(scene = None, image_path = None, project_dir = None):
    '''Gán một ảnh cụ thể vào phân cảnh chỉ định và đóng gói vào thư mục ảnh của dự án nếu có.'''
    p = Path(image_path).resolve()
    if p.is_file():
        final_path = p
        if project_dir:
            
            try:
                import shutil
                p_dir = Path(project_dir).resolve()
                img_dir = p_dir / 'images'
                img_dir.mkdir(parents = True, exist_ok = True)
                if not str(p).startswith(str(p_dir)):
                    ext = p.suffix if p.suffix else '.png'
                    sc_id = scene.get('scene_id', 'sc')
                    dest = img_dir / f'''{sc_id}{ext}'''
                    shutil.copy2(p, dest)
                    final_path = dest.resolve()
            except Exception as e:
                logger.warning('Không thể copy ảnh vào thư mục dự án: %s', e)
                final_path = p
        scene['image_path'] = str(final_path)
        scene['image_source'] = scene.get('image_source') or 'manual'
        scene['media_type'] = 'image'
        scene['video_path'] = ''
        scene['video_source'] = ''
        if scene.get('status') in ('pending', '', None):
            scene['status'] = 'image_ready'
    return scene



def apply_single_image_to_all_scenes(scenes = None, image_path = None, project_dir = None):
    """Áp dụng 1 file ảnh duy nhất cho toàn bộ các phân cảnh trong kịch bản.

    - Sao chép ảnh vào thư mục images/ của dự án (nếu có project_dir) dưới tên cover_all.<ext>
      để đảm bảo tính độc lập và di động của dự án mà không tốn dung lượng sao chép nhiều lần.
    - Cập nhật image_path, media_type='image', image_source='single_for_all' cho tất cả scenes.
    - Xóa sạch video_path và video_source cũ để không bị nhận nhầm là video scene.
    - Duy trì status nếu đã có audio_ready / ready, hoặc nâng lên image_ready nếu pending.
    - Trả về số phân cảnh đã được cập nhật.
    """
    p = Path(image_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f'''Không tìm thấy file ảnh: {image_path}''')
    final_path = p
    if project_dir:
        
        try:
            import shutil
            p_dir = Path(project_dir).resolve()
            img_dir = p_dir / 'images'
            img_dir.mkdir(parents = True, exist_ok = True)
            ext = p.suffix.lower() if p.suffix else '.png'
            dest = img_dir / f'''cover_all{ext}'''
            if p.resolve() != dest.resolve():
                shutil.copy2(p, dest)
            final_path = dest.resolve()
        except Exception as err:
            logger.warning('Không thể copy ảnh vào thư mục dự án: %s', err)
            final_path = p
    final_path_str = str(final_path)
    count = 0
    for sc in scenes:
        if isinstance(sc, dict):
            sc['image_path'] = final_path_str
            sc['image_source'] = 'single_for_all'
            sc['media_type'] = 'image'
            sc['video_path'] = ''
            sc['video_source'] = ''
            if sc.get('status') in ('pending', '', None):
                sc['status'] = 'image_ready'
            count += 1
            continue
        if not hasattr(sc, 'image_path'):
            continue
        sc.image_path = final_path_str
        sc.image_source = 'single_for_all'
        sc.media_type = 'image'
        if hasattr(sc, 'video_path'):
            sc.video_path = ''
        if hasattr(sc, 'video_source'):
            sc.video_source = ''
        if getattr(sc, 'status', '') in ('pending', '', None):
            sc.status = 'image_ready'
        count += 1
    logger.info('Đã áp dụng 1 ảnh duy nhất cho %d phân cảnh: %s', count, final_path_str)
    return count



def get_story_provider_voices(provider = None):
    '''Trả về danh sách các cặp (tên_hiển_thị, mã_giọng_hoặc_key) cho nhà cung cấp TTS.
    Tất cả nhãn hiển thị đều chuyên nghiệp, không chứa icon/emoji.
    '''
    provider = (provider or 'Edge TTS').strip()
    records = []
    if provider == 'Edge TTS':
        list_all_edge_voices = list_all_edge_voices
        import app.services.edge_tts_engine
        for vid, lbl in list_all_edge_voices():
            records.append((lbl, vid))
# WARNING: Decompyle incomplete


def generate_scene_audio(scene = None, output_path = None, voice = None, speed = None, *, provider, model_id):
    '''Sinh giọng đọc (Edge-TTS, CapCut, ElevenLabs, VieNeu, Google) cho phân cảnh và đo thời lượng (giây).'''
    text = (scene.get('text_segment') or '').strip()
    if not text:
        return 0.0
    out_file = Path(output_path)
    out_file.parent.mkdir(parents = True, exist_ok = True)
    provider_norm = (provider or 'Edge TTS').strip()
    if provider_norm == 'Edge TTS':
        rate_str = speed_to_edge_rate(speed)
        raw_voice = voice.rsplit('|', 1)[-1].strip() if '|' in voice else voice
        edge_tts_generate(text, out_file, voice = raw_voice, rate = rate_str)
    else:
        make_cloud_tts = make_cloud_tts
        import app.services.cloud_voice
        tts_func = make_cloud_tts(provider_norm, voice, speed, model_id = model_id)
        tts_func(text, out_file)
    duration = probe_video_duration_s(out_file)
    if duration <= 0:
        duration = max(2.5, len(text.split()) * 0.35 / max(0.5, speed))
    scene['audio_path'] = str(out_file.resolve())
    scene['duration_s'] = round(duration, 3)
    scene['voice_provider'] = provider_norm
    scene['voice_id'] = voice
    scene['voice_speed'] = float(speed)
    if scene.get('status') in ('pending', ''):
        scene['status'] = 'audio_ready'
    return duration


def wrap_cue_text(text = None, max_line = None):
    '''Ngắt dòng tự nhiên tối đa 55 ký tự/dòng để vừa vặn khung hình 1-2 dòng thanh thoát.'''
    words = text.split()
    if not words:
        return ''
    lines = []
    cur_line = []
    cur_len = 0
    for w in words:
        add_len = len(w) + 1 if cur_line else 0
        if cur_len + add_len <= max_line:
            cur_line.append(w)
            cur_len += add_len
            continue
        if cur_line:
            lines.append(' '.join(cur_line))
        cur_line = [
            w]
        cur_len = len(w)
    if cur_line:
        lines.append(' '.join(cur_line))
    return '\n'.join(lines[:2])


def split_scene_text_to_cues(text = None, duration = None, max_chars_per_cue = None, max_line = (75, 55)):
    '''Phân tách các đoạn văn thoại dài (>75 ký tự) thành các subtitle cue ngắn gọn, tự nhiên.

    Giúp phụ đề chuẩn điện ảnh chỉ hiển thị 1-2 dòng ngắn dưới đáy màn hình thay vì
    bị dồn thành khối văn bản khổng lồ che khuất nội dung hình ảnh.
    '''
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars_per_cue:
        return [
            (0.0, duration, wrap_cue_text(text, max_line = max_line))]
# WARNING: Decompyle incomplete


def sync_story_timeline_and_srt(scenes = None, srt_output_path = None):
    '''Tính toán lại timeline lũy kế (cumulative) và sinh file SRT chuẩn đồng bộ 100% với ảnh.

    Khóa chính xác:
    start_time_s -> end_time_s cho từng phân cảnh.
    Bức ảnh của phân cảnh sẽ hiển thị chính xác từ start_time_s đến end_time_s.
    '''
    current_time = 0
    srt_blocks = []
    cue_idx = 1
    for scene in scenes:
        if not scene.get('duration_s'):
            scene.get('duration_s')
        duration = float(0)
        if duration <= 0:
            duration = 4
            scene['duration_s'] = duration
        start_s = current_time
        end_s = current_time + duration
        scene['start_time_s'] = round(start_s, 3)
        scene['end_time_s'] = round(end_s, 3)
        if scene.get('video_source') == 'single_for_all':
            scene['video_start_s'] = round(start_s, 3)
        current_time = end_s
        text = scene.get('text_segment', '').strip()
        sub_cues = split_scene_text_to_cues(text, duration, max_chars_per_cue = 65)
        if not sub_cues:
            t_start = format_srt_timestamp(start_s)
            t_end = format_srt_timestamp(end_s)
            srt_blocks.append(f'''{cue_idx}\n{t_start} --> {t_end}\n{text}\n''')
            cue_idx += 1
            continue
        for rel_st, rel_en, cue_txt in sub_cues:
            c_start = format_srt_timestamp(start_s + rel_st)
            c_end = format_srt_timestamp(start_s + rel_en)
            srt_blocks.append(f'''{cue_idx}\n{c_start} --> {c_end}\n{cue_txt}\n''')
            cue_idx += 1
    if srt_output_path:
        p = Path(srt_output_path)
        p.parent.mkdir(parents = True, exist_ok = True)
        p.write_text('\n'.join(srt_blocks), encoding = 'utf-8')
        logger.info('Đã xuất file SRT kịch bản: %s (Tổng thời lượng: %.2fs)', p.name, current_time)
    return scenes


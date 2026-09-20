# Source Generated with Decompyle++
# File: story_engine.pyc (Python 3.12)

'''Dịch vụ bóc tách kịch bản kể chuyện (AI Storytelling Engine) cho Mumu Studio Pro.

Bóc tách kịch bản thành từng Scene phân cảnh chuẩn điện ảnh, gán gợi ý hình ảnh
tiếng Việt (visual concept) và prompt tiếng Anh chuẩn cho AI Image Generator.
Hỗ trợ lưu / mở dự án story_project.json.
'''
from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import urllib.error as urllib
import urllib.request as urllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from app.services.gemini_translate import GEMINI_MODELS, get_gemini_api_key, get_translation_api_keys, normalize_gemini_model
logger = logging.getLogger(__name__)
CUSTOM_PRESET_NAME = 'Tùy Chỉnh (Tự Nhập Master Prompt)'
MASTER_PROMPT_PRESETS: 'dict[str, dict[str, str]]' = {
    'drama_life': {
        'name': 'Đời Sống / Chân Thực & Cảm Động',
        'prompt': 'Cinematic authentic storytelling shot, photorealistic, true-to-life documentary style, warm moody natural lighting, shallow depth of field, 35mm film photography, highly detailed, expressive human emotions, 8k' },
    'true_crime_doc': {
        'name': 'Tài Liệu Điều Tra / Vụ Án Bí Ẩn',
        'prompt': 'Cinematic true-crime documentary, hyperrealistic 35mm photograph, dramatic chiaroscuro archival lighting, dramatic shadows, atmospheric moody forensic realism, gritty authentic textures, 8k resolution' },
    'history_real': {
        'name': 'Lịch Sử / Sự Kiện Chân Thực',
        'prompt': 'Photorealistic historical cinematic film still, accurate period details, authentic atmosphere, natural dramatic lighting, 35mm anamorphic lens, documentary realism, 8k' },
    'philosophical': {
        'name': 'Triết Lý / Sâu Lắng & Hoài Niệm',
        'prompt': 'Minimalist cinematic shot, poetic solitude, golden hour soft light, atmospheric perspective, vintage color grading, nostalgic film grain, contemplation mood, 8k' },
    'gothic_mystery': {
        'name': 'Bí Ẩn / Không Khí Kịch Tính',
        'prompt': 'Cinematic dramatic realism, deep mystery, dark atmospheric fog, chiaroscuro lighting, dramatic shadows, vintage textured canvas, mysterious mood, 8k resolution' },
    'myth_fantasy': {
        'name': 'Cung Đấu / Cổ Tích Huyền Bí',
        'prompt': 'Epic oriental fantasy art, ancient royal palace aesthetic, mystical ethereal glow, intricate silk robes, dramatic cinematic lighting, masterpiece digital painting, 8k' },
    'custom': {
        'name': CUSTOM_PRESET_NAME,
        'prompt': '' } }

def estimate_story_duration(text_or_chars = None, wpm = None):
    """Dự đoán thời lượng video (tổng số giây và chuỗi hiển thị 'X phút Ys' hoặc 'X giờ Y phút')
    dựa trên số lượng ký tự hoặc từ ngữ kịch bản trước khi render.

    Quy chuẩn đọc voice-over AI (Tiếng Anh / Tiếng Việt):
    - Tốc độ đọc tự nhiên: ~130 - 150 từ/phút (WPM)
    - Hoặc ~14 ký tự/giây (~840 ký tự/phút).
    """
    if isinstance(text_or_chars, str):
        raw = text_or_chars.strip()
        words = len(raw.split()) if raw else 0
        chars = len(raw)
        if words > 0:
            total_sec = max(0, (words / max(1, wpm)) * 60)
        else:
            total_sec = max(0, chars / 14)
    elif not text_or_chars:
        text_or_chars
    chars = int(0)
    total_sec = max(0, chars / 14)
    total_sec = round(total_sec)
    if total_sec < 60:
        display_str = f'''{total_sec} giây'''
    elif total_sec < 3600:
        mins = total_sec // 60
        secs = total_sec % 60
        if secs >= 45:
            mins += 1
            display_str = f'''{mins} phút'''
        elif secs >= 15:
            display_str = f'''{mins} phút {secs:02d}s'''
        else:
            display_str = f'''{mins} phút'''
    else:
        hrs = total_sec // 3600
        rem_sec = total_sec % 3600
        mins = round(rem_sec / 60)
        if mins >= 60:
            hrs += 1
            mins = 0
        if mins > 0:
            display_str = f'''{hrs}h{mins:02d}p'''
        else:
            display_str = f'''{hrs} giờ'''
    return (float(total_sec), display_str)


def get_user_story_presets_file():
    presets_dir = Path(__file__).resolve().parents[2] / 'presets'
    presets_dir.mkdir(parents = True, exist_ok = True)
    return presets_dir / 'story_prompts.json'


def load_user_story_presets():
    '''Trả về dict: {preset_name: prompt_text}'''
    f = get_user_story_presets_file()
    if not f.is_file():
        return { }
# WARNING: Decompyle incomplete


def save_user_story_preset(name = None, prompt = None):
    '''Lưu preset mới của người dùng vào file presets/story_prompts.json.'''
    name = name.strip()
    if name or name == CUSTOM_PRESET_NAME:
        return None
    presets = load_user_story_presets()
    presets[name] = prompt.strip()
    f = get_user_story_presets_file()
    f.write_text(json.dumps(presets, ensure_ascii = False, indent = 2), encoding = 'utf-8')


def delete_user_story_preset(name = None):
    '''Xóa một preset người dùng khỏi presets/story_prompts.json.'''
    name = name.strip()
    presets = load_user_story_presets()
    if name in presets:
        del presets[name]
        f = get_user_story_presets_file()
        f.write_text(json.dumps(presets, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        return True
    return False


def get_all_story_prompt_presets():
    '''Trả về danh sách đầy đủ gồm Tùy Chỉnh, các preset mẫu điện ảnh và preset người dùng đã lưu: {display_name: prompt_text}.'''
    presets = {
        CUSTOM_PRESET_NAME: '' }
    for k, v in MASTER_PROMPT_PRESETS.items():
        if not k != 'custom':
            continue
        if not isinstance(v, dict):
            continue
        if not 'name' in v:
            continue
        if not 'prompt' in v:
            continue
        presets[v['name']] = v['prompt']
    presets.update(load_user_story_presets())
    return presets

CAMERA_MOTIONS = [
    'hook_crash_zoom',
    'hook_shake',
    'hook_whip_pan',
    'zoom_in',
    'zoom_out',
    'pan_left',
    'pan_right',
    'tilt_up',
    'tilt_down',
    'static']
CAMERA_MOTION_LABELS = {
    'hook_crash_zoom': '3s Hook: Phóng cực nhanh (Crash Zoom)',
    'hook_shake': '3s Hook: Rung lắc kịch tính (Camera Shake)',
    'hook_whip_pan': '3s Hook: Lướt nhanh (Whip Pan)',
    'zoom_in': 'Phóng to (Zoom In)',
    'zoom_out': 'Thu nhỏ (Zoom Out)',
    'pan_left': 'Lướt sang trái (Pan Left)',
    'pan_right': 'Lướt sang phải (Pan Right)',
    'tilt_up': 'Lướt lên trên (Tilt Up)',
    'tilt_down': 'Lướt xuống dưới (Tilt Down)',
    'static': 'Cố định (Static)' }
StoryScene = <NODE:12>()
StoryProject = <NODE:12>()

def get_texture_library_dirs():
    '''Trả về danh sách các thư mục chứa thư viện video texture.

    Thứ tự ưu tiên:
    1. Thư mục PyInstaller bundle (nếu đóng gói exe)
    2. Thư mục gom tài nguyên chuẩn: libraries/textures
    3. Thư mục cũ: library_textures (tương thích ngược)
    4. Thư mục assets hệ thống: app/assets/texture_library
    '''
    base_dirs = []
    root = Path(__file__).resolve().parents[2]
    cwd = Path.cwd()
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = Path(sys._MEIPASS)
        base_dirs.append(meipass / 'libraries' / 'textures')
        base_dirs.append(meipass / 'library_textures')
        base_dirs.append(meipass / 'app' / 'assets' / 'texture_library')
    base_dirs.append(root / 'libraries' / 'textures')
    base_dirs.append(cwd / 'libraries' / 'textures')
    base_dirs.append(root / 'library_textures')
    base_dirs.append(cwd / 'library_textures')
    app_assets = Path(__file__).resolve().parent.parent / 'assets' / 'texture_library'
    primary_dir = root / 'libraries' / 'textures'
    
    try:
        primary_dir.mkdir(parents = True, exist_ok = True)
        existing_dirs = []
        seen = set()
        for d in base_dirs:
            if d.is_dir():
                resolved = str(d.resolve()).lower()
                if resolved not in seen:
                    seen.add(resolved)
                    existing_dirs.append(d)
        continue
        if not existing_dirs:
            existing_dirs
        return [
            primary_dir]
    except Exception:
        continue
        except Exception:
            continue


PRIMARY_TEXTURE_DIR = Path.cwd() / 'libraries' / 'textures'
TEXTURE_DIR = PRIMARY_TEXTURE_DIR
BLEND_MODES: 'list[tuple[str, str]]' = [
    ('Screen (Sáng & Khử đen - Khuyên dùng)', 'screen'),
    ('Overlay (Tương phản điện ảnh)', 'overlay'),
    ('Multiply (Làm tối / Giấy cũ)', 'multiply'),
    ('Soft Light (Ánh sáng dịu)', 'softlight'),
    ('Lighten (Làm sáng)', 'lighten'),
    ('Addition (Tia sáng rực rỡ)', 'addition')]

def get_blend_mode_id(display_name = None):
    """Chuyển đổi nhãn hiển thị UI thành mã mode FFmpeg (ví dụ: 'screen')."""
    if not display_name:
        display_name
    d_clean = ''.strip().lower()
    for disp, mode_id in BLEND_MODES:
        if not mode_id in d_clean and disp.lower() == d_clean:
            continue
        
        return BLEND_MODES, mode_id
    return 'screen'


def get_blend_mode_display_name(mode_id = None):
    '''Chuyển đổi mã FFmpeg thành nhãn hiển thị tiếng Việt trên UI.'''
    if not mode_id:
        mode_id
    m_clean = ''.strip().lower()
    for disp, mid in BLEND_MODES:
        if not mid == m_clean:
            continue
        
        return BLEND_MODES, disp
    return BLEND_MODES[0][0]


def apply_texture_blend(base_img = None, tex_img = None, mode = None, opacity = ('base_img', 'Any', 'tex_img', 'Any', 'mode', 'str', 'opacity', 'float', 'return', 'Any')):
    '''Hòa trộn frame texture lên frame video theo blend mode và opacity chuẩn điện ảnh.'''
    pass
# WARNING: Decompyle incomplete


class TextureFrameReader:
    '''Bộ giải mã và cung cấp khung hình texture video vòng lặp mượt mà cho preview playback (hỗ trợ đa texture).'''
    
    def __init__(self = None):
        self._readers = { }

    
    def close(self = None):
        pass
    # WARNING: Decompyle incomplete

    
    def _get_single_path_frame(self, path = None, t_s = None, w = None, h = ('path', 'str', 't_s', 'float', 'w', 'int', 'h', 'int', 'return', 'Any | None')):
        if not path:
            return None
        p_str = str(path)
        r = self._readers.get(p_str)
    # WARNING: Decompyle incomplete

    
    def get_frame(self, path = None, t_s = None, w = None, h = ('cycle_15s',), distribution = ('path', 'Any', 't_s', 'float', 'w', 'int', 'h', 'int', 'distribution', 'str', 'return', 'Any | None')):
        if not path:
            self.close()
            return None
    # WARNING: Decompyle incomplete



def ensure_sample_textures():
    '''Tạo sẵn các video texture mẫu chất lượng cao, dung lượng nhẹ nếu các thư mục texture rỗng.'''
    pass
# WARNING: Decompyle incomplete


def get_available_textures():
    '''Quét các thư mục texture (libraries/textures, library_textures, assets) và trả về danh sách tuple (Tên hiển thị, Đường dẫn file tuyệt đối).'''
    ensure_sample_textures()
    dirs = get_texture_library_dirs()
    results = []
    seen_names = set()
    valid_exts = {
        '.avi',
        '.mkv',
        '.mov',
        '.mp4',
        '.webm'}
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            if not p.suffix.lower() in valid_exts:
                continue
            norm_name = p.name.lower()
            if norm_name in seen_names:
                continue
            seen_names.add(norm_name)
            disp = p.stem.replace('Sample_', '').replace('_', ' ').replace('Film Grain 35mm', 'Film Grain (Hạt phim 35mm)').replace('Warm Light Leak', 'Light Leak (Tia sáng ấm)').replace('Vintage Vignette', 'Vintage Vignette (Khung cổ điển)')
            results.append((disp, str(p.resolve())))
    return results


def split_text_into_smart_chunks(script_text = None, max_chunk_chars = None):
    '''Cắt kịch bản dài (lên tới 60.000+ ký tự) thành các đoạn ngữ nghĩa an toàn (< 8.000 ký tự).
    
    Quy tắc ngắt:
    1. Ưu tiên ngắt theo đầu mục chương/phần (Chương X, Phần X, Hồi X, Chapter X) hoặc đoạn văn (

).
    2. Nếu đoạn văn vượt quá giới hạn, ngắt theo dấu chấm câu (. ! ? …).
    3. Tuyệt đối không cắt ngang giữa câu hoặc giữa từ ngữ.
    '''
    text = script_text.strip()
    if not text:
        return []
    if None(text) <= max_chunk_chars:
        return [
            text]
# WARNING: Decompyle incomplete


def fallback_split_script(script_text = None, master_prompt = None, start_index = None):
    '''Phân tách kịch bản theo câu/đoạn bằng thuật toán nội bộ (khi không có API key hoặc offline).'''
    text = script_text.strip()
    if not text:
        return []
# WARNING: Decompyle incomplete

SYSTEM_INSTRUCTION_STORY_CHUNKER = 'Bạn là đạo diễn kịch bản và chuyên gia sản xuất video storytelling điện ảnh đỉnh cao (phong cách tài liệu chân thực, kịch tính, điện ảnh sâu sắc bám sát thực tế dành cho khán giả quốc tế trưởng thành).\n\nNhiệm vụ của bạn:\nPhân tích đoạn kịch bản được giao (Phần {chunk_num}/{total_chunks}) thành các Phân Cảnh (Scenes) điện ảnh lôi cuốn.\n\nQUY TẮC ĐẶT TÊN, CHỦ ĐỀ, MÔ TẢ VÀ THUMBNAIL VIDEO (YOUTUBE / TIKTOK):\n1. video_title: Sinh ra MỘT tiêu đề video SIÊU THU HÚT (clickbait, drama, tò mò) tóm tắt toàn bộ cốt truyện (giữ theo ngôn ngữ kịch bản). Tiêu đề này trả về ở cấp cao nhất của JSON.\n2. video_topic_vi: Tóm tắt chủ đề / ý nghĩa kịch bản bằng 1 câu Tiếng Việt ngắn gọn, súc tích (ví dụ: \'Vụ án bí ẩn được phơi bày sau 10 năm điều tra\' hoặc \'Hành trình vượt nghịch cảnh phi thường\') để người dùng nắm rõ chủ đề kịch bản.\n3. video_description: Viết MỘT ĐOẠN MÔ TẢ VIDEO HOÀN CHỈNH chuẩn SEO YouTube / TikTok / Facebook: gồm mở đầu tóm tắt hấp dẫn khơi gợi sự tò mò (hook), 1-2 đoạn tóm tắt câu chuyện không spoil cái kết, lời kêu gọi Subscribe/Like tương tác, và 5-8 hashtags thịnh hành (#Storytelling, #Drama, v.v.) bằng ngôn ngữ kịch bản.\n4. thumbnail_prompt: Viết một MASTER PROMPT TẠO ẢNH BÌA THUMBNAIL YOUTUBE (hoàn toàn bằng Tiếng Anh) siêu kịch tính, cinematic 8k, photorealistic, góc nhìn đặc tả cảm xúc cao trào nhất của câu chuyện, ánh sáng tương phản chiaroscuro, kèm chữ text overlay giật gân để hút triệu view.\n5. Trong suốt các phân cảnh, phân cảnh nào chứa khoảnh khắc CAO TRÀO NHẤT (dramatic nhất), hãy thêm chữ của `video_title` vào `image_prompt` (ví dụ: Text "[video_title]" overlaid on the image).\n\nQUY TẮC CỐT TRUYỆN (BẮT BUỘC):\n1. CƠ CHẾ GIỮ CHÂN 3 GIÂY ĐẦU (3-SECOND HOOK MASTER): Nếu đoạn này chứa Phân Cảnh 1 (index = 1), câu thoại mở đầu BẮT BUỘC phải là một HOOK giật gân, khơi gợi tò mò cực độ (câu hỏi bí ẩn, sự thật gây sốc, hoặc vào thẳng cao trào in media res). TUYỆT ĐỐI không chào hỏi hay mở đầu bằng lời giới thiệu dài dòng. Hình ảnh Phân Cảnh 1 phải có góc máy cận cảnh (close-up/crash zoom), ánh mắt biểu cảm nghẹt thở, và camera_motion là \'hook_crash_zoom\'.\n2. text_segment: Cắt kịch bản gốc thành từng phân đoạn thoại vừa vặn (mỗi phân cảnh gồm 1-2 câu, thời lượng đọc khoảng 6 - 12 giây).\n3. TUYỆT ĐỐI GIỮ NGUYÊN BẢN: Sử dụng 100% câu chữ nguyên gốc từ kịch bản của tác giả (giữ nguyên văn ngôn ngữ gốc: Tiếng Anh, Tiếng Việt, Tiếng Trung, v.v.). KHÔNG được tự ý dịch sang ngôn ngữ khác, KHÔNG tự ý tóm tắt sơ sài, KHÔNG thêm thắt nội dung ngoài, KHÔNG bỏ sót câu từ.\n4. TRÁNH LẶP LẠI & LAN MAN: Tập trung vào trọng tâm cảm xúc và cao trào của từng phân cảnh.\n\nQUY TẮC HÌNH ẢNH ĐIỆN ẢNH (DÀNH CHO KHÁN GIẢ TRƯỞNG THÀNH):\n1. visual_hint_vi: 1 câu tiếng Việt ngắn gọn tóm tắt cảnh để người dùng dễ chọn ảnh.\n2. image_prompt: Viết hoàn toàn bằng TIẾNG ANH, kết hợp Master Prompt phong cách mỹ thuật. Mô tả chi tiết:\n   - Chủ thể chính (nhân vật, biểu cảm sâu sắc, ánh mắt, trang phục).\n   - Bối cảnh và không khí (atmosphere, moody, dark mystery, dramatic lighting, volumetric haze).\n   - Phân cảnh kịch tính nhất: Phải chèn thêm mô tả text overlay giống `video_title`.\n   - Chất lượng cao cấp: photorealistic, cinematic 8k, Unreal Engine 5 aesthetic, master composition, 35mm film grain.\n3. ĐA DẠNG GÓC MÁY: Tuyệt đối KHÔNG lặp lại một góc máy liên tiếp. Luôn chuyển giữa: wide establishing shot, medium close-up, dramatic low-angle, over-the-shoulder, atmospheric deep focus.\n4. video_motion_prompt: Viết hoàn toàn bằng TIẾNG ANH mô tả chuyển động video sống động cho các model Video AI (Google Veo 3, Runway Gen-3, Luma Dream Machine, Kling AI, Pika, Sora). Mô tả chuyển động camera (slow push-in, pan, tracking), hành động nhân vật, tương tác vật lý (gió thổi, mưa rơi, khói sương), 24fps film look.\n5. camera_motion: Chọn một trong [\'hook_crash_zoom\', \'hook_shake\', \'hook_whip_pan\', \'zoom_in\', \'zoom_out\', \'pan_left\', \'pan_right\', \'tilt_up\', \'tilt_down\', \'static\']. Đặc biệt Phân Cảnh 1 nên ưu tiên \'hook_crash_zoom\' hoặc \'hook_shake\'.\n6. speaker: Tên nhân vật đang nói đoạn thoại này (ví dụ: \'John\', \'Sarah\', \'Thám tử Nam\') hoặc \'narrator\' nếu là lời người dẫn chuyện/kể chuyện.\n\nQUY TẮC ĐÁNH SỐ:\n- Phân cảnh đầu tiên của đoạn này BẮT ĐẦU từ số thứ tự index = {start_index}.\n{context_note}\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY:\n{{\n  "video_title": "Tiêu đề video cực thu hút ở đây",\n  "video_topic_vi": "Tóm tắt chủ đề kịch bản bằng Tiếng Việt ở đây",\n  "video_description": "Mô tả video hoàn chỉnh chuẩn SEO YouTube/TikTok kèm hashtags...",\n  "thumbnail_prompt": "Prompt tiếng Anh mô tả chi tiết hình ảnh Thumbnail YouTube triệu view kịch tính",\n  "scenes": [\n    {{\n      "index": {start_index},\n      "speaker": "narrator",\n      "text_segment": "...",\n      "visual_hint_vi": "...",\n      "image_prompt": "...",\n      "video_motion_prompt": "...",\n      "camera_motion": "zoom_in"\n    }}\n  ]\n}}'
PROVIDER_ENDPOINTS = {
    'Gemini': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
    'Groq': 'https://api.groq.com/openai/v1/chat/completions',
    'DeepSeek': 'https://api.deepseek.com/chat/completions',
    'OpenAI': 'https://api.openai.com/v1/chat/completions' }
STORY_AI_MODELS: 'dict[str, list[str]]' = {
    'Gemini': [
        'gemini-3.8-flash',
        'gemini-3.7-flash',
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-3.5-flash-lite',
        'gemini-3.1-flash-lite',
        'gemini-3-flash-preview',
        'gemini-2.5-flash',
        'gemini-2.5-pro',
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-1.5-flash'],
    'Groq': [
        'openai/gpt-oss-120b',
        'openai/gpt-oss-20b',
        'groq/compound',
        'qwen/qwen3.6-27b',
        'llama-3.1-8b-instant'],
    'DeepSeek': [
        'deepseek-chat',
        'deepseek-reasoner'],
    'OpenAI': [
        'gpt-4o-mini',
        'gpt-4o',
        'o3-mini',
        'o1-mini',
        'gpt-4.5-preview',
        'gpt-3.5-turbo'] }

def get_story_provider_keys(provider = None):
    '''Lấy danh sách API key khả dụng cho provider tương ứng (loại bỏ trùng lặp và key rỗng).'''
    if not provider:
        provider
    p = ''.strip()
    keys = []
    if p in ('Gemini', 'Google Gemini'):
        keys = get_translation_api_keys('Gemini')
        if not keys:
            single = get_gemini_api_key()
            if single:
                keys = [
                    single]
            elif p in ('Groq', 'Groq Cloud'):
                keys = get_translation_api_keys('Groq')
            elif p in ('DeepSeek', 'DeepSeek AI'):
                keys = get_translation_api_keys('DeepSeek')
            elif p in ('OpenAI', 'OpenAI GPT'):
                keys = get_translation_api_keys('OpenAI')
# WARNING: Decompyle incomplete


def _call_gemini_story(api_key = None, model = None, system_instruction = None, user_content = (50,), timeout = ('api_key', 'str', 'model', 'str', 'system_instruction', 'str', 'user_content', 'str', 'timeout', 'int', 'return', 'str')):
    '''Gọi Google Gemini REST API trả về chuỗi JSON bóc tách kịch bản.'''
    if not model:
        model
    norm_model = normalize_gemini_model('gemini-2.5-flash')
    if not model:
        model
    norm_model = normalize_gemini_model('gemini-flash-latest')
    url = f'''https://generativelanguage.googleapis.com/v1beta/models/{norm_model}:generateContent?key={api_key}'''
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [
                    {
                        'text': f'''{system_instruction}\n\n{user_content}''' }] }],
        'generationConfig': {
            'temperature': 0.3,
            'responseMimeType': 'application/json',
            'maxOutputTokens': 8192,
            'thinkingConfig': {
                'thinkingBudget': 0 } } }
    req = urllib.request.Request(url, data = json.dumps(payload).encode('utf-8'), headers = {
        'Content-Type': 'application/json' }, method = 'POST')
    resp = urllib.request.urlopen(req, timeout = timeout)
    data = json.loads(resp.read().decode('utf-8'))
    None(None, None)
# WARNING: Decompyle incomplete


def _call_openai_compatible_story(provider, api_key = None, model = None, system_instruction = None, user_content = (50,), timeout = ('provider', 'str', 'api_key', 'str', 'model', 'str', 'system_instruction', 'str', 'user_content', 'str', 'timeout', 'int', 'return', 'str')):
    '''Gọi OpenAI-compatible API (Groq Cloud, DeepSeek AI, OpenAI GPT).'''
    endpoint = PROVIDER_ENDPOINTS.get(provider)
    if not endpoint:
        raise ValueError(f'''Không tìm thấy endpoint cho provider {provider}''')
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': system_instruction },
            {
                'role': 'user',
                'content': user_content }],
        'temperature': 0.3,
        'max_tokens': 8192,
        'response_format': {
            'type': 'json_object' } }
    if provider == 'Groq':
        if 'gpt-oss' in model or 'compound' in model:
            payload['reasoning_effort'] = 'low'
    req_data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'''Bearer {api_key}''',
        'User-Agent': 'MumuStudio/3.0' }
    req = urllib.request.Request(endpoint, data = req_data, headers = headers, method = 'POST')
# WARNING: Decompyle incomplete


def _parse_and_build_scenes(raw_text = None, master_prompt = None, start_index = None):
    '''Phân tích chuỗi JSON trả về từ LLM (bất kể Gemini, Groq, DeepSeek, OpenAI, Web ChatGPT/Gemini) và dựng danh sách Scene.'''
    if not raw_text:
        raw_text
    raw_text = ''.strip()
    fence_m = re.search('```(?:json)?\\s*([\\s\\S]*?)\\s*```', raw_text)
    candidate_text = fence_m.group(1).strip() if fence_m else raw_text
    if candidate_text.startswith('```json'):
        candidate_text = candidate_text[7:]
    elif candidate_text.startswith('```'):
        candidate_text = candidate_text[3:]
    if candidate_text.endswith('```'):
        candidate_text = candidate_text[:-3]
    candidate_text = candidate_text.strip()
    parsed = None
# WARNING: Decompyle incomplete


def generate_story_description_fallback(title = None, topic_vi = None, scenes = None, language = ('', None, 'English')):
    '''Tự động sinh mô tả video thuần túy (chỉ chứa nội dung mô tả kịch bản, không kèm CTA).'''
    if not title:
        title
    t = ''.strip()
    if not topic_vi:
        topic_vi
    topic = ''.strip()
    text_pieces = []
    if scenes:
        for s in scenes:
            if not getattr(s, 'text_segment', None):
                getattr(s, 'text_segment', None)
            txt = s.get('text_segment') if isinstance(s, dict) else ''
            if not txt:
                continue
            t_str = str(txt).strip()
            if not t_str:
                continue
            text_pieces.append(t_str)
            if not len(text_pieces) >= 3:
                continue
            scenes
    parts = []
    if t:
        parts.append(t)
    if text_pieces:
        full_text = ' '.join(text_pieces)
        if len(full_text) > 400:
            full_text = full_text[:400].rsplit(' ', 1)[0] + '...'
        parts.append(full_text)
    elif topic:
        parts.append(topic)
    return '\n\n'.join(parts)


def _process_chunk_multi_llm(chunk_text, master_prompt, provider_plans, start_plan_idx, key_cursors, chunk_num = None, total_chunks = None, start_index = None, context_note = (None,), progress_callback = ('chunk_text', 'str', 'master_prompt', 'str', 'provider_plans', 'list[dict[str, Any]]', 'start_plan_idx', 'int', 'key_cursors', 'dict[str, int]', 'chunk_num', 'int', 'total_chunks', 'int', 'start_index', 'int', 'context_note', 'str', 'progress_callback', 'Any | None', 'return', 'tuple[list[dict[str, Any]], int]')):
    '''Xử lý 1 đoạn kịch bản với kiến trúc đa tầng LLM:
    Ưu tiên Gemini & Groq -> DeepSeek -> OpenAI -> Fallback cục bộ.
    '''
    import time
    system_instruction = SYSTEM_INSTRUCTION_STORY_CHUNKER.format(chunk_num = chunk_num, total_chunks = total_chunks, start_index = start_index, context_note = context_note)
    user_content = f'''MASTER PROMPT PHONG CÁCH:\n{master_prompt}\n\nKỊCH BẢN PHẦN {chunk_num}/{total_chunks}:\n{chunk_text}'''
    num_plans = len(provider_plans)
    for p_offset in range(num_plans):
        p_idx = (start_plan_idx + p_offset) % num_plans
        plan = provider_plans[p_idx]
        provider = plan['provider']
        keys = plan['keys']
        models = plan['models']
        if not keys:
            continue
        k_idx = key_cursors.get(provider, 0)
        max_attempts = min(max(len(keys) * 2, len(models)), 6)
        for attempt in range(max_attempts):
            active_key = keys[k_idx % len(keys)]
            active_model = models[attempt // len(keys) % len(models)]
            if callable(progress_callback):
                progress_callback(f'''Đoạn {chunk_num}/{total_chunks}: Đang bóc tách bằng {provider} ({active_model})...''', (chunk_num - 1) / float(total_chunks))
            scenes = _parse_and_build_scenes(raw_text, master_prompt, start_index)
            if scenes:
                logger.info('Đoạn %d/%d bóc tách thành công: %d phân cảnh (Dùng %s · Model %s · Key #%d/%d)', chunk_num, total_chunks, len(scenes), provider, active_model, k_idx % len(keys) + 1, len(keys))
                key_cursors[provider] = (k_idx + 1) % len(keys)
                
                
                return None, range(num_plans) if provider == 'Gemini' else range(max_attempts), (scenes, p_idx)
        if not p_offset < num_plans - 1:
            continue
        next_plan['provider'] = provider_plans[(p_idx + 1) % num_plans]
        msg = f'''{provider} chạm giới hạn -> Tự động chuyển sang {next_p}...'''
        logger.warning(msg)
        if callable(progress_callback):
            progress_callback(msg, (chunk_num - 1) / float(total_chunks))
        time.sleep(0.4)
    logger.warning('Đoạn %d/%d: Toàn bộ AI LLM đều thất bại -> Sử dụng thuật toán fallback nội bộ', chunk_num, total_chunks)
    fb_scenes = fallback_split_script(chunk_text, master_prompt, start_index = start_index)
    return (fb_scenes, start_plan_idx)
    except Exception:
        continue
    except urllib.error.HTTPError:
        e = None
        err_body = ''
        if hasattr(e, 'read') and callable(e.read):
            err_body = e.read().decode('utf-8', errors = 'replace')[:300]
        else:
            except Exception:
                pass
            logger.warning('Đoạn %d/%d gọi %s (%s) Key #%d bị HTTP %d: %s', chunk_num, total_chunks, provider, active_model, k_idx % len(keys) + 1, e.code, err_body)
            if e.code == 404:
                e = None
                del e
                continue
        if e.code in (429, 500, 502, 503) and 'quota' in err_body.lower() or 'rate' in err_body.lower():
            k_idx += 1
            time.sleep(0.4)
            e = None
            del e
            continue
        k_idx += 1
        time.sleep(0.8)
        e = None
        del e
        continue
        e = None
        del e
    except Exception:
        exc = None
        logger.warning('Đoạn %d/%d gọi %s gặp lỗi: %s', chunk_num, total_chunks, provider, exc)
        k_idx += 1
        time.sleep(0.5)
        exc = None
        del exc
        continue
        exc = None
        del exc
    except Exception:
        continue


def _process_chunk_with_gemini(chunk_text, master_prompt, keys, start_key_idx, chunk_num = None, total_chunks = None, start_index = None, context_note = ('gemini-2.5-flash',), model = ('chunk_text', 'str', 'master_prompt', 'str', 'keys', 'list[str]', 'start_key_idx', 'int', 'chunk_num', 'int', 'total_chunks', 'int', 'start_index', 'int', 'context_note', 'str', 'model', 'str', 'return', 'tuple[list[dict[str, Any]], int]')):
    '''Wrapper tương thích ngược cho việc gọi Gemini phân tách đoạn kịch bản.'''
    if not model:
        model
    provider_plans = [
        {
            'provider': 'Gemini',
            'keys': keys,
            'models': [
                'gemini-flash-latest',
                'gemini-2.5-flash',
                'gemini-flash-lite-latest',
                'gemini-1.5-flash'] }]
    key_cursors = {
        'Gemini': start_key_idx }
    (scenes, _) = _process_chunk_multi_llm(chunk_text = chunk_text, master_prompt = master_prompt, provider_plans = provider_plans, start_plan_idx = 0, key_cursors = key_cursors, chunk_num = chunk_num, total_chunks = total_chunks, start_index = start_index, context_note = context_note)
    return (scenes, key_cursors.get('Gemini', (start_key_idx + 1) % max(len(keys), 1)))


def segment_story_script(script_text, master_prompt = None, api_key = None, model = None, progress_callback = ('', None, 'gemini-2.5-flash', None, 'Auto'), provider = ('script_text', 'str', 'master_prompt', 'str', 'api_key', 'str | None', 'model', 'str', 'progress_callback', 'Any | None', 'provider', 'str', 'return', 'list[dict[str, Any]]')):
    '''Phân tách kịch bản dài thành danh sách Scene chuẩn cấu trúc điện ảnh.

    Hỗ trợ 4 nhà cung cấp AI: Gemini, Groq, DeepSeek, OpenAI.
    Ưu tiên hàng đầu: Gemini & Groq với failover tự động và xoay vòng key thông minh.
    Nếu người dùng chưa cấu hình key cho DeepSeek / OpenAI, hệ thống tự động bỏ qua an toàn.
    '''
    pass
# WARNING: Decompyle incomplete


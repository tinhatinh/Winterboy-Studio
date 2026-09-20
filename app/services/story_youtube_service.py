# Source Generated with Decompyle++
# File: story_youtube_service.pyc (Python 3.12)

'''Dịch vụ phân tích video YouTube đối thủ và tự động viết kịch bản độc bản (YouTube Competitor Reverse-Engineering Engine).

Khai thác:
- yt-dlp: Trích xuất metadata (Title, Thumbnail, Description, Tags, Transcript/Captions).
- Gemini Multimodal: Phân tích Thumbnail, cấu trúc video và giải mã công thức Viral Hook.
- Multi-Act Narrative Generator: Sinh kịch bản nhiều Hồi với xoay vòng 6 API Key Gemini chống lặp từ và quá tải token.
'''
from __future__ import annotations
import base64
import json
import logging
import re
import time
import urllib.error as urllib
import urllib.request as urllib
from pathlib import Path
from typing import Any, Callable
from app.services.story_engine import get_gemini_api_key, get_translation_api_keys, normalize_gemini_model
logger = logging.getLogger(__name__)

def _extract_gemini_text(candidates = None):
    '''Trích xuất text an toàn từ Gemini candidates, tự động bỏ qua internal thought tokens.'''
    if not candidates:
        return ''
    content = candidates[0].get('content', { })
    parts = content.get('parts', [])
    texts = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        if not p.get('text'):
            continue
        if p.get('thought'):
            continue
        texts.append(p.get('text', ''))
    return ''.join(texts).strip()


def _get_fallback_model_list(model = None):
    '''Tạo chuỗi model ưu tiên để fallback tức thì nếu gặp 404 (model deprecated).'''
    if not model:
        model
    primary = normalize_gemini_model('gemini-flash-latest')
    candidates = [
        primary,
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-2.5-flash']
    res = []
    for c in candidates:
        if not c:
            continue
        if not c not in res:
            continue
        res.append(c)
    return res

ProgressCb = Callable[([
    float,
    str], None)]

def extract_youtube_video_id(url_or_id = None):
    '''Trích xuất mã video ID 11 ký tự của YouTube từ mọi định dạng URL.'''
    s = url_or_id.strip()
    if re.fullmatch('[A-Za-z0-9_-]{11}', s):
        return s
    m = None.search('(?:v=|\\/v\\/|youtu\\.be\\/|\\/embed\\/|\\/shorts\\/)([A-Za-z0-9_-]{11})', s)
    if m:
        return m.group(1)


def _download_and_parse_subtitle_track(c_list = None):
    '''Tải và trích xuất nội dung văn bản từ danh sách định dạng phụ đề YouTube.'''
    pass
# WARNING: Decompyle incomplete


def extract_youtube_info(url_or_id = None):
    '''Trích xuất tiêu đề, mô tả, tags, thumbnail, chapters và phụ đề/transcript của video YouTube.
    
    Tầng 1: yt-dlp với player client Android, Web & TV để lấy đầy đủ metadata và phụ đề gốc/tự động.
    Tầng 2: Fallback YouTube oEmbed API siêu tốc khi yt-dlp gặp sự cố mạng.
    '''
    pass
# WARNING: Decompyle incomplete


def get_gemini_keys_pool(custom_key = None):
    '''Lấy danh sách các API Key Gemini khả dụng (từ cài đặt hoặc tham số).'''
    pass
# WARNING: Decompyle incomplete

SUPPORTED_SCRIPT_LANGUAGES = [
    'Tự động (Tiếng Anh)',
    'Tiếng Anh (English)',
    'Tiếng Việt (Vietnamese)',
    'Tiếng Trung (Chinese - 中文)',
    'Tiếng Nhật (Japanese - 日本語)',
    'Tiếng Hàn (Korean - 한국어)',
    'Tiếng Tây Ban Nha (Spanish - Español)',
    'Tiếng Pháp (French - Français)',
    'Tiếng Đức (German - Deutsch)',
    'Tiếng Thái (Thai - ไทย)',
    'Tiếng Bồ Đào Nha (Portuguese - Português)',
    'Tiếng Indonesia (Indonesian - Bahasa)',
    'Tiếng Nga (Russian - Русский)',
    'Tiếng Ý (Italian - Italiano)',
    'Tiếng Thổ Nhĩ Kỳ (Turkish - Türkçe)',
    'Tiếng Ả Rập (Arabic - العربية)',
    'Tiếng Hindi (Hindi - हिन्दी)']

def resolve_target_language_name(choice = None):
    """Chuẩn hóa tên ngôn ngữ đích cho prompt chỉ dẫn AI.
    Mặc định nếu là 'auto' hoặc 'Tự động (Tiếng Anh)' -> Tiếng Anh (English).
    """
    if not choice:
        choice
    raw = ''.strip()
    if raw and 'tự động' in raw.casefold() or 'auto' in raw.casefold():
        return 'English (Tiếng Anh chuẩn quốc tế)'
    low = raw.casefold()
    if 'tiếng anh' in low or 'english' in low:
        return 'English (Tiếng Anh chuẩn quốc tế)'
    if 'tiếng việt' in low or 'vietnamese' in low:
        return 'Tiếng Việt (Vietnamese thuần Việt)'
    if 'trung' in low or 'chinese' in low:
        return 'Chinese (Tiếng Trung - 中文)'
    if 'nhật' in low or 'japanese' in low:
        return 'Japanese (Tiếng Nhật - 日本語)'
    if 'hàn' in low or 'korean' in low:
        return 'Korean (Tiếng Hàn - 한국어)'
    if 'tây ban nha' in low or 'spanish' in low:
        return 'Spanish (Tiếng Tây Ban Nha - Español)'
    if 'pháp' in low or 'french' in low:
        return 'French (Tiếng Pháp - Français)'
    if 'đức' in low or 'german' in low:
        return 'German (Tiếng Đức - Deutsch)'
    if 'thái' in low or 'thai' in low:
        return 'Thai (Tiếng Thái - ภาษาไทย)'
    if 'bồ đào nha' in low or 'portuguese' in low:
        return 'Portuguese (Tiếng Bồ Đào Nha - Português)'
    if 'indonesia' in low or 'bahasa' in low:
        return 'Indonesian (Tiếng Indonesia - Bahasa)'
    if 'nga' in low or 'russian' in low:
        return 'Russian (Tiếng Nga - Русский)'
    if '\xc3\xbd' in low or 'italian' in low:
        return 'Italian (Tiếng Ý - Italiano)'
    if 'thổ nhĩ kỳ' in low or 'turkish' in low:
        return 'Turkish (Tiếng Thổ Nhĩ Kỳ - Türkçe)'
    if 'ả rập' in low or 'arabic' in low:
        return 'Arabic (Tiếng Ả Rập - العربية)'
    if 'hindi' in low:
        return 'Hindi (Tiếng Hindi - हिन्दी)'
    return raw

SYSTEM_REVERSE_ENGINEER_PROMPT = 'Bạn là chuyên gia phân tích kịch bản YouTube triệu view (YouTube Reverse-Engineering Expert) và đạo diễn điện ảnh quốc tế hàng đầu.\n\nNHIỆM VỤ CỦA BẠN:\nPhân tích video YouTube và Thumbnail đối thủ được cung cấp, giải mã bí mật tâm lý thu hút khán giả quốc tế trưởng thành (Adult foreign audience), và xây dựng một Ý TƯỞNG KỊCH BẢN ĐỘC BẢN MỚI 100% (Zero Copyright) thuộc cùng ngách (Niche) đó.\n\nQUY TRÌNH PHÂN TÍCH VÀ SÁNG TẠO (NGƯỜI THẬT VIỆC THẬT - BÁM SÁT VIDEO GỐC):\n1. ĐỌC THẬT VÀ BÓC TÁCH CHÍNH XÁC NỘI DUNG VIDEO ĐỐI THỦ:\n   - Dựa trên Transcript (lời thoại gốc), Tiêu đề, Mô tả, Timeline Chapters và Thumbnail thực tế được cung cấp, xác định chính xác đề tài của video:\n     + Vụ án / Phá án / Tội phạm có thật (True Crime)\n     + Phóng sự điều tra / Góc khuất xã hội (Investigative Documentary)\n     + Câu chuyện cuộc đời / Nhân vật có thật (Real-Life Biography & Survival)\n     + Biến cố lịch sử / Sự kiện có thật (Historical Truth)\n     + Đời sống xã hội, tâm lý sâu sắc, bi kịch gia đình, nhân quả thực tế.\n   - TUYỆT ĐỐI KHÔNG tự ý gán ghép hoặc biến câu chuyện thành cổ tích hoàng gia hay "Queen Stories" trừ khi chính video gốc thực sự nói về chủ đề đó. Phải phản ánh đúng tinh thần "người thật việc thật" và bối cảnh thực tế.\n   - Bắt buộc bám sát sự thật, bối cảnh thời đại, nhân vật chính, địa điểm và dòng thời gian thực tế đã diễn ra trong video.\n\n2. GIẢI MÃ VIRAL HOOK & TÂM LÝ:\n   - Giải mã Hook 15s đầu tiên: Tại sao khán giả không thể rời mắt? Yếu tố chấn động nào giữ chân người xem?\n   - Mối xung đột tâm lý, đạo đức, bi kịch hay sự thật gây sốc nào là trọng tâm?\n   - Giải mã Thumbnail: Bố cục, ánh sáng, góc nhìn nhân vật tạo nên sự tò mò kích thích click.\n\n3. MASTER PROMPT MỸ THUẬT ĐIỆN ẢNH (TIẾNG ANH):\n   - Phải được thiết kế đồng nhất dựa trên CHÍNH BỐI CẢNH THỰC TẾ của video đối thủ:\n     + Nếu là vụ án/điều tra: Cinematic true-crime investigative documentary, photorealistic 8k, authentic 35mm photograph, dramatic archival chiaroscuro lighting, natural gritty textures, serious realistic mood.\n     + Nếu là đời sống/cảm động: True-to-life emotional storytelling, natural lighting, candid 35mm film look, authentic human emotions.\n     + Nếu là sự kiện lịch sử: Photorealistic historical cinematic film still, accurate period details, atmospheric lighting, 35mm anamorphic lens, documentary realism.\n   - Luôn viết hoàn toàn bằng TIẾNG ANH để phục vụ AI sinh ảnh/video (Midjourney, Imagen, Flux, Runway, Veo, Kling).\n\n4. BÓC TÁCH KINH THÁNH NHÂN VẬT & BỐI CẢNH THỜI ĐẠI (CHARACTER & VISUAL BIBLE):\n   - Bóc tách chính xác các nhân vật trung tâm trong câu chuyện có thật / kịch bản:\n     + Nhân vật chính 1 (character_lead_1): Tên, độ tuổi, vóc dáng, gương mặt, trang phục cố định đặc trưng.\n     + Nhân vật chính 2 (character_lead_2): Bạn đồng hành / người yêu / đối tác / nhân vật phụ quan trọng.\n     + Kẻ phản diện / Đối đầu (character_antagonist): Kẻ chủ mưu, thế lực đối lập hoặc thử thách lớn nhất.\n     + Bối cảnh & Không gian (setting_location): Địa danh, không gian thực tế diễn ra câu chuyện.\n     + Thập niên & Kỷ nguyên (era_setting): Mô tả chi tiết thời kỳ lịch sử bằng tiếng Anh (ví dụ: Victorian 1880s London, 1920s Prohibition Chicago, 19th-century English Regency, Contemporary 2020s...).\n   - Danh sách "characters" chi tiết cho từng nhân vật để khóa gương mặt và trang phục (visual continuity):\n     Tên, giới tính, tuổi, đặc điểm nhận dạng khuôn mặt/tóc bằng tiếng Anh (features), và bộ trang phục đặc trưng cố định bằng tiếng Anh (signature_attire).\n\n5. CẤU TRÚC 4 HỒI (4 ACTS) CHẶT CHẼ (100% ĐỘC QUYỀN - ZERO COPYRIGHT):\n   - Tái hiện lại câu chuyện có thật đó với văn phong điện ảnh sâu sắc, kịch tính, lôi cuốn bằng NGÔN NGỮ ĐƯỢC YÊU CẦU:\n     + Hồi 1: Sự cố khởi đầu bí ẩn & Cú Hook chấn động (Bắt đầu từ sự kiện châm ngòi có thật)\n     + Hồi 2: Rơi vào mê hồn trận & Những manh mối / biến cố phơi bày\n     + Hồi 3: Đỉnh điểm căng thẳng, cao trào đối đầu hoặc bi kịch bùng nổ\n     + Hồi 4: Cú twist sự thật, kết cục nhân quả & Dư âm sâu sắc đọng lại\n   - Mỗi Hồi trong "acts" phải có "outline" chi tiết (nêu rõ các sự kiện có thật cần kể trong Hồi đó).\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY (KHÔNG KÈM TEXT NGOÀI):\n{\n  "niche_name": "Tên đề tài/ngách thực tế (ví dụ: Phóng sự điều tra vụ án có thật / Real-Life Investigative True Crime)",\n  "hook_analysis": "Phân tích chi tiết công thức Hook và tâm lý người xem của video này",\n  "thumbnail_prompt": "Prompt tiếng Anh chi tiết để tạo ảnh Thumbnail điện ảnh hấp dẫn dựa trên chủ đề video",\n  "master_prompt": "Master Prompt tiếng Anh photorealistic chuẩn điện ảnh bám sát bối cảnh thực tế của video",\n  "character_lead_1": "Mô tả ngắn gọn nhân vật chính 1 (Tên, độ tuổi, diện mạo, trang phục)",\n  "character_lead_2": "Mô tả ngắn gọn nhân vật chính 2 / bạn đồng hành",\n  "character_antagonist": "Mô tả kẻ phản diện / thế lực đối đầu / xung đột chính",\n  "setting_location": "Bối cảnh địa điểm, không gian diễn ra câu chuyện",\n  "era_setting": "Detailed era & setting description in English (e.g. Victorian 1880s London, misty streets...)",\n  "characters": [\n    {\n      "name": "Tên nhân vật",\n      "gender": "male / female",\n      "age": "32 years old",\n      "features": "Sharp jawline, brown wavy hair, hazel eyes, intense expression",\n      "signature_attire": "Dark wool double-breasted trench coat with brass buttons and charcoal trousers"\n    }\n  ],\n  "new_story": {\n    "title": "Tiêu đề kịch bản điện ảnh giật gân, cuốn hút bằng ngôn ngữ yêu cầu",\n    "premise": "Tóm tắt cốt truyện bám sát sự kiện thực tế trong 2-3 câu bằng ngôn ngữ yêu cầu",\n    "acts": [\n      {"act": 1, "title": "Tiêu đề Hồi 1", "outline": "Tóm tắt chi tiết diễn biến Hồi 1"},\n      {"act": 2, "title": "Tiêu đề Hồi 2", "outline": "Tóm tắt chi tiết diễn biến Hồi 2"},\n      {"act": 3, "title": "Tiêu đề Hồi 3", "outline": "Tóm tắt chi tiết diễn biến Hồi 3"},\n      {"act": 4, "title": "Tiêu đề Hồi 4", "outline": "Tóm tắt chi tiết diễn biến Hồi 4"}\n    ]\n  }\n}\n'

def reverse_engineer_competitor(metadata = None, keys = None, *, model, target_length_mode, tone_style, language, progress_cb):
    '''Phân tích video đối thủ và sinh cấu trúc ý tưởng mới cùng Master Prompt.'''
    if not keys:
        raise ValueError('Chưa có API Key Gemini nào để phân tích.')
    model_list = _get_fallback_model_list(model)
    key_idx = 0
    max_attempts = max(len(keys) * 3, 6)
    parts = []
    tags_str = ', '.join(metadata.get('tags', [])[:20])
    if not metadata.get('description', ''):
        metadata.get('description', '')
    desc_str = ''[:3000]
    target_lang_str = resolve_target_language_name(language)
    context_lines = [
        SYSTEM_REVERSE_ENGINEER_PROMPT,
        '',
        'THÔNG TIN VIDEO ĐỐI THỦ CẦN PHÂN TÍCH (QUY TRÌNH ĐỌC THẬT VIDEO GỐC):',
        f'''- Link: {metadata.get('url', '')}''',
        f'''- Tiêu đề: {metadata.get('title', '')}''',
        f'''- Kênh: {metadata.get('channel', '')}''',
        f'''- Thời lượng: {metadata.get('duration', 0)}s''',
        f'''- Mô tả video: {desc_str}''',
        f'''- Tags: {tags_str}''',
        f'''- Yêu cầu độ dài: {target_length_mode}''',
        f'''- Định hướng tông giọng: {tone_style}''',
        f'''- NGÔN NGỮ KỊCH BẢN YÊU CẦU: {target_lang_str}''']
    if not metadata.get('chapters_text'):
        metadata.get('chapters_text')
    chapters = ''.strip()
    if chapters:
        context_lines.extend([
            '',
            'CÁC CHƯƠNG MỤC DÒNG THỜI GIAN CỦA VIDEO GỐC (TIMELINE CHAPTERS):',
            chapters])
    if not metadata.get('transcript_text'):
        metadata.get('transcript_text')
    transcript = ''.strip()
    if transcript:
        if len(transcript) > 12000:
            transcript_excerpt = transcript[:7500] + '\n\n[... phần giữa kịch bản ...] \n\n' + transcript[-4500:]
        if len(transcript) > 50000:
            transcript_excerpt = transcript[:35000] + '\n\n[... phần diễn biến tiếp theo ...]\n\n' + transcript[-15000:]
        else:
            transcript_excerpt = transcript
        context_lines.extend([
            '',
            'NỘI DUNG LỜI THOẠI / TRANSCRIPT THỰC TẾ CỦA VIDEO ĐỐI THỦ (NGƯỜI THẬT VIỆC THẬT):',
            f'''NỘI DUNG LỜI THOẠI / TRANSCRIPT THỰC TẾ CỦA VIDEO ĐỐI THỦ ({len(transcript):,} ký tự):''',
            transcript_excerpt,
            '',
            'HÃY ĐỌC KỸ TRANSCRIPT TRÊN: Bóc tách chính xác sự kiện có thật, nhân vật, bối cảnh thực tế và tạo ra kịch bản độc bản cùng Master Prompt chuẩn phong cách tài liệu / chân thực bám sát video gốc.',
            'HÃY ĐỌC THẬT KỸ TRANSCRIPT TRÊN: Bóc tách chính xác các sự kiện có thật, con người, địa điểm, bối cảnh thời đại và tái hiện lại kịch bản cùng Master Prompt chuẩn phong cách tài liệu / chân thực điện ảnh bám sát video gốc.'])
    else:
        context_lines.extend([
            '',
            'LƯU Ý VỀ DỮ LIỆU: Video không có phụ đề transcript trực tiếp. Hãy phân tích thật sâu Tiêu đề, Mô tả chi tiết, Tags và hình ảnh Thumbnail đối thủ để giải mã chính xác chủ đề người thật việc thật của video này.',
            'LƯU Ý VỀ DỮ LIỆU: Video không có phụ đề transcript trực tiếp. Hãy phân tích thật sâu Tiêu đề, Mô tả chi tiết, Tags và hình ảnh Thumbnail đối thủ để giải mã chính xác câu chuyện có thật của video này.'])
    parts.append({
        'text': '\n'.join(context_lines) })
    if metadata.get('thumbnail_base64'):
        parts.append({
            'inlineData': {
                'mimeType': 'image/jpeg',
                'data': metadata['thumbnail_base64'] } })
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': parts }],
        'generationConfig': {
            'temperature': 0.4,
            'responseMimeType': 'application/json',
            'maxOutputTokens': 8192,
            'thinkingConfig': {
                'thinkingBudget': 0 } } }
    model_idx = 0
# WARNING: Decompyle incomplete

SYSTEM_ACT_WRITER_PROMPT = 'Bạn là nhà văn điện ảnh bậc thầy chuyên viết kịch bản truyện kể người thật việc thật, chân thực và kịch tính dành cho khán giả quốc tế trưởng thành (Adult mature storytelling: True-to-life Real Stories, Investigative Documentary, Psychological Drama, Historical Truth, Deep Human Karma).\n\nTIÊU CHÍ NỘI DUNG (BẮT BUỘC):\n1. BÁM SÁT SỰ THẬT & CHI TIẾT CÓ THẬT: Khai thác các sự kiện, chi tiết đời sống, mốc thời gian và nhân vật thực tế từ dữ liệu video gốc. Tuyệt đối không biến tướng sang thể loại cổ tích, hoàng gia hư cấu trừ khi đề tài gốc là như vậy.\n2. TUYỆT ĐỐI TRÁNH LẶP TỪ, LAN MAN: Không dùng những mẫu câu sáo rỗng, không tua đi tua lại một ý nghĩ. Tập trung vào hành động, giác quan, đối thoại nội tâm đắt giá và bối cảnh chân thực đời sống.\n3. NHỊP CẢM XÚC HÚT MẮT: Mỗi câu văn đều phải kéo người xem muốn nghe tiếp câu sau. Tạo không khí điện ảnh đậm đặc, chân thực và lôi cuốn.\n4. PHÙ HỢP KHÁN GIẢ TRƯỞNG THÀNH: Đào sâu vào góc khuất tâm lý, số phận con người, sự thật bị che giấu và quy luật nhân quả sâu sắc.\n5. ĐỘ DÀI & NGÔN NGỮ: Viết chi tiết, đầy đặn, không tóm tắt, khoảng {target_chars_per_act} ký tự văn xuôi thuần khiết hoàn toàn bằng {target_language}. TUYỆT ĐỐI KHÔNG dùng ngôn ngữ khác ngoài {target_language}.\n\nBẮT ĐẦU VIẾT TRỰC TIẾP VĂN BẢN KỊCH BẢN BẰNG {target_language_upper} (KHÔNG KÈM LỜI GIỚI THIỆU HAY GHI CHÚ NGOÀI):\n'

def write_single_act(act_info = None, story_concept = None, previous_context = None, keys = None, key_idx = {
    'source_transcript_slice': '',
    'model': 'gemini-flash-latest',
    'target_chars_per_act': 3000,
    'language': 'Tự động (Tiếng Anh)',
    'progress_cb': None,
    'act_num': 1,
    'total_acts': 4 }, *, source_transcript_slice, model, target_chars_per_act, language, progress_cb, act_num, total_acts):
    '''Viết một Hồi cụ thể của câu chuyện, tự động dùng key tiếp theo và kiểm soát token.'''
    model_list = _get_fallback_model_list(model)
    max_attempts = max(len(keys) * 3, 6)
    target_lang_str = resolve_target_language_name(language)
    prompt_lines = [
        SYSTEM_ACT_WRITER_PROMPT.format(target_chars_per_act = target_chars_per_act, target_language = target_lang_str, target_language_upper = target_lang_str.upper()),
        '',
        f'''TÊN CÂU CHUYỆN: {story_concept.get('new_story', { }).get('title', '')}''',
        f'''TIỀN ĐỀ: {story_concept.get('new_story', { }).get('premise', '')}''',
        f'''HỒI ĐANG VIẾT: Hồi {act_info.get('act', 1)}: {act_info.get('title', '')}''',
        f'''DÀN Ý HỒI NÀY: {act_info.get('outline', '')}''']
    if source_transcript_slice:
        prompt_lines.extend([
            '',
            'DỮ LIỆU LỜI THOẠI / DIỄN BIẾN THỰC TẾ TỪ VIDEO GỐC (THAM KHẢO ĐỂ BÁM SÁT SỰ KIỆN CÓ THẬT):',
            source_transcript_slice[:12000],
            '',
            'HÃY BÁM SÁT CÁC TÌNH TIẾT CÓ THẬT TRÊN ĐỂ KỂ LẠI MỘT CÁCH SÂU SẮC, ĐIỆN ẢNH VÀ CHÂN THỰC.'])
    prompt_lines.extend([
        '',
        'NGỮ CẢNH CÁC HỒI TRƯỚC ĐÃ VIẾT (ĐỂ NỐI TIẾP LIỀN MẠCH):',
        previous_context[-2500:] if previous_context else '(Đây là Hồi mở đầu, hãy tạo một cú Hook thật sốc bám sát sự kiện khởi đầu có thật)',
        '',
        f'''HÃY VIẾT NỘI DUNG CHI TIẾT HỒI NÀY HOÀN TOÀN BẰNG {target_lang_str.upper()}:'''])
    prompt = '\n'.join(prompt_lines)
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [
                    {
                        'text': prompt }] }],
        'generationConfig': {
            'temperature': 0.65,
            'maxOutputTokens': 8192,
            'thinkingConfig': {
                'thinkingBudget': 0 } } }
    model_idx = 0
# WARNING: Decompyle incomplete


def generate_youtube_competitor_story(youtube_url = None, *, keys, target_length, tone_style, language, progress_cb):
    '''Quy trình toàn diện: Đọc video đối thủ -> Giải mã ngách -> Viết kịch bản độc quyền nhiều Hồi kèm Master Prompt.'''
    if not keys:
        keys
    key_pool = get_gemini_keys_pool()
    if not key_pool:
        raise ValueError('Không tìm thấy API Key Gemini nào. Vui lòng thêm ít nhất 1 Key.')
    if progress_cb:
        progress_cb(0.1, 'Đang phân tích liên kết YouTube đối thủ & tải Thumbnail...')
    meta = extract_youtube_info(youtube_url)
    target_lang_display = resolve_target_language_name(language)
    if progress_cb:
        progress_cb(0.25, f'''AI đang bóc tách ngách \'{meta.get('title', '')[:30]}…\' ({target_lang_display}) & tạo Master Prompt...''')
    (concept, curr_key) = reverse_engineer_competitor(metadata = meta, keys = key_pool, target_length_mode = target_length, tone_style = tone_style, language = language, progress_cb = progress_cb)
    acts = concept.get('new_story', { }).get('acts', [])
    if not acts:
        acts = [
            {
                'act': 1,
                'title': 'Khởi Đầu Bí Ẩn',
                'outline': 'Sự cố kích hoạt câu chuyện.' },
            {
                'act': 2,
                'title': 'Rơi Vào Cạm Bẫy',
                'outline': 'Những bí mật dần phơi bày.' },
            {
                'act': 3,
                'title': 'Cao Trào Đối Đầu',
                'outline': 'Căng thẳng lên tới đỉnh điểm.' },
            {
                'act': 4,
                'title': 'Cú Twist Cuối Cùng',
                'outline': 'Sự thật ngỡ ngàng và lắng đọng.' }]
    target_map = {
        'short': 1200,
        'medium': 2800,
        'long': 8000 }
    per_act_chars = target_map.get(target_length, 2800)
    written_acts = []
    full_context = ''
    total_acts = len(acts)
    if not meta.get('transcript_text'):
        meta.get('transcript_text')
    trans = ''.strip()
    trans_len = len(trans)
    for i, act in enumerate(acts, start = 1):
        if i > 1:
            time.sleep(1.5)
        pct = 0.3 + 0.65 * ((i - 1) / total_acts)
        key_num = curr_key % len(key_pool) + 1
        if progress_cb:
            progress_cb(pct, f'''Đang viết Hồi {i}/{total_acts}: {act.get('title', '')} bằng {target_lang_display} (Key #{key_num}/{len(key_pool)})...''')
        act_transcript_slice = ''
        if trans_len > 0:
            seg_size = trans_len // total_acts
            start_pos = max(0, (i - 1) * seg_size - 500)
            end_pos = min(trans_len, i * seg_size + 1000)
            act_transcript_slice = trans[start_pos:end_pos]
        (act_text, curr_key) = write_single_act(act_info = act, story_concept = concept, previous_context = full_context, source_transcript_slice = act_transcript_slice, keys = key_pool, key_idx = curr_key, target_chars_per_act = per_act_chars, language = language, progress_cb = progress_cb, act_num = i, total_acts = total_acts)
        written_acts.append(f'''### {act.get('title', f'''HỒI {i}''')}\n\n{act_text}''')
        full_context += '\n\n' + act_text
    full_script = '\n\n'.join(written_acts)
    if progress_cb:
        progress_cb(1, f'''Hoàn tất kịch bản độc quyền ({len(full_script):,} ký tự)!''')
    if not concept.get('new_story', { }).get('title'):
        concept.get('new_story', { }).get('title')
    if not concept.get('master_prompt'):
        concept.get('master_prompt')
    if not concept.get('thumbnail_prompt'):
        concept.get('thumbnail_prompt')
    if not concept.get('niche_name'):
        concept.get('niche_name')
    if not concept.get('hook_analysis'):
        concept.get('hook_analysis')
    if not concept.get('character_lead_1'):
        concept.get('character_lead_1')
    if not concept.get('character_lead_2'):
        concept.get('character_lead_2')
    if not concept.get('character_antagonist'):
        concept.get('character_antagonist')
    if not concept.get('setting_location'):
        concept.get('setting_location')
    if not concept.get('era_setting'):
        concept.get('era_setting')
    if not concept.get('characters'):
        concept.get('characters')
    return {
        'title': meta.get('title', 'Chuyện Chưa Kể'),
        'master_prompt': '',
        'thumbnail_prompt': '',
        'niche_name': '',
        'hook_analysis': '',
        'character_lead_1': '',
        'character_lead_2': '',
        'character_antagonist': '',
        'setting_location': '',
        'era_setting': '',
        'characters': [],
        'script_text': full_script,
        'metadata': meta,
        'language': language }


def build_youtube_web_gemini_prompt(youtube_url = None, *, target_length, tone_style, language):
    '''Tạo câu lệnh Master Prompt tối ưu hóa cho Gemini Web (Chrome) kèm link YouTube.'''
    target_lang_str = resolve_target_language_name(language)
    len_desc_map = {
        'short': 'Ngắn (~4.000 - 6.000 ký tự / Video 3-5 phút)',
        'medium': 'Vừa (~10.000 - 15.000 ký tự / Video 8-12 phút)',
        'long': 'Dài chuyên sâu (~30.000 - 50.000 ký tự / Video 25-45 phút)',
        'max': 'Cực đại (~100.000 ký tự / Siêu trường ca, Video chuyên sâu 1-2 tiếng)' }
    target_length_desc = len_desc_map.get(target_length, 'Vừa (~10.000 ký tự)')
    return f'''Hãy truy cập và phân tích toàn bộ nội dung của video YouTube sau:\nLink video: {youtube_url}\n\nBẠN LÀ CHUYÊN GIA BÓC TÁCH KỊCH BẢN YOUTUBE TRIỆU VIEW (YOUTUBE REVERSE-ENGINEERING EXPERT) VÀ ĐẠO DIỄN BIÊN KỊCH ĐIỆN ẢNH QUỐC TẾ.\n\nYÊU CẦU CẤU HÌNH & QUY TẮC ĐỘ DÀI BẮT BUỘC (TUYỆT ĐỐI TUÂN THỦ):\n- Độ dài kịch bản mong muốn: {target_length_desc}\n- QUY TẮC ĐỘ DÀI NGHIÊM NGẶT: Kịch bản BẮT BUỘC phải viết ĐỦ VÀ ĐÚNG số lượng ký tự yêu cầu là {target_length_desc} (cho phép chênh lệch nhẹ ít hơn hoặc nhiều hơn một chút khoảng 5-10%). TUYỆT ĐỐI KHÔNG ĐƯỢC VIẾT QUÁ NGẮN, không được tóm tắt sơ sài, không được cắt bớt nội dung hay tình tiết. TUYỆT ĐỐI KHÔNG ĐƯỢC VIẾT QUÁ DÀI vượt hạn mức yêu cầu. Từng Hồi phải được viết chi tiết, đầy đặn từng câu từng chữ văn xuôi điện ảnh bám sát đúng thời lượng mong muốn.\n- Định hướng tông giọng: {tone_style}\n- Ngôn ngữ kịch bản: {target_lang_str}\n\nHÃY THỰC HIỆN CÁC BƯỚC PHÂN TÍCH & SÁNG TẠO:\n1. ĐỌC THẬT NỘI DUNG VIDEO: Xem và bóc tách toàn bộ phụ đề/transcript, các mốc thời gian, nhân vật, bối cảnh thực tế và sự kiện có thật trong video (Tuyệt đối không bịa đặt hoặc biến tướng sang cổ tích hoàng gia trừ khi chính video gốc là như vậy).\n2. GIẢI MÃ VIRAL HOOK: Phân tích chi tiết công thức Hook 15-30 giây đầu tiên và tâm lý giữ chân khán giả của video này.\n3. TẠO MASTER PROMPT MỸ THUẬT (TIẾNG ANH): Viết 1 prompt phong cách điện ảnh (Cinematic photorealistic 8k, dramatic lighting, 35mm film still, gritty textures, atmospheric depth) bám sát đúng bối cảnh thực tế của video để dùng cho AI sinh ảnh đồng bộ (Midjourney / Flux).\n4. TẠO THUMBNAIL PROMPT (TIẾNG ANH): Viết prompt mô tả ảnh bìa Thumbnail kích thích tò mò, giật gân, cuốn hút.\n5. BÓC TÁCH KINH THÁNH NHÂN VẬT & BỐI CẢNH (CHARACTER & VISUAL BIBLE): Xác định các nhân vật chủ chốt và bối cảnh thời đại cụ thể để khóa ngoại hình nhất quán xuyên suốt các phân cảnh.\n6. VIẾT TOÀN BỘ KỊCH BẢN HOÀN CHỈNH (FULL SCRIPT): Tái hiện lại câu chuyện với cấu trúc 4 Hồi điện ảnh chặt chẽ, sâu sắc, không tóm tắt, giàu cảm xúc và kịch tính hoàn toàn bằng {target_lang_str}:\n   - Hồi 1: Cú Hook chấn động & Sự cố châm ngòi (Bắt đầu từ sự kiện châm ngòi có thật)\n   - Hồi 2: Rơi vào mê hồn trận & Những manh mối / biến cố phơi bày\n   - Hồi 3: Đỉnh điểm căng thẳng & Cao trào đối đầu\n   - Hồi 4: Cú Twist sự thật, quy luật nhân quả & Dư âm lắng đọng\n\nBẮT BUỘC TRẢ VỀ DƯỚI ĐỊNH DẠNG JSON THUẦN TÚY (NẰM TRONG KHỐI ```json ... ```) THEO CẤU TRÚC SAU:\n```json\n{{\n  "niche_name": "Tên ngách / thể loại cụ thể của video",\n  "hook_analysis": "Phân tích chi tiết công thức Hook 15s đầu và tâm lý giữ chân khán giả",\n  "master_prompt": "Prompt tiếng Anh mô tả phong cách hình ảnh toàn bộ kịch bản (Cinematic, lighting, textures, camera angle...)",\n  "thumbnail_prompt": "Prompt tiếng Anh mô tả chi tiết hình ảnh Thumbnail YouTube triệu view",\n  "character_lead_1": "Tên và diện mạo nhân vật chính 1 bằng tiếng Anh",\n  "character_lead_2": "Tên và diện mạo nhân vật chính 2 hoặc người đồng hành nếu có",\n  "character_antagonist": "Kẻ phản diện / đối đầu / xung đột chính nếu có",\n  "setting_location": "Bối cảnh địa lý, thành phố diễn ra câu chuyện",\n  "era_setting": "Era and setting description in English (e.g. 1980s urban gritty, Victorian 1890s...)",\n  "characters": [\n    {{\n      "name": "Character Name in English",\n      "gender": "male hoặc female",\n      "age": "Age (e.g. 30s, mid-40s)",\n      "features": "Detailed facial features, hair, eyes, body build in English",\n      "signature_attire": "Fixed recognizable clothing in English for visual continuity"\n    }}\n  ],\n  "new_story": {{\n    "title": "Tiêu đề kịch bản điện ảnh hấp dẫn bằng {target_lang_str}",\n    "premise": "Tiền đề tóm tắt câu chuyện trong 2-3 câu bằng {target_lang_str}",\n    "acts_outline": [\n      {{"act": 1, "title": "Tiêu đề Hồi 1", "outline": "Tóm tắt sự kiện Hồi 1"}},\n      {{"act": 2, "title": "Tiêu đề Hồi 2", "outline": "Tóm tắt sự kiện Hồi 2"}},\n      {{"act": 3, "title": "Tiêu đề Hồi 3", "outline": "Tóm tắt sự kiện Hồi 3"}},\n      {{"act": 4, "title": "Tiêu đề Hồi 4", "outline": "Tóm tắt sự kiện Hồi 4"}}\n    ],\n    "full_script": "### HỒI 1: [TÊN HỒI 1]\\n\\n[Nội dung chi tiết văn xuôi Hồi 1...]\\n\\n### HỒI 2: [TÊN HỒI 2]\\n\\n[Nội dung chi tiết văn xuôi Hồi 2...]\\n\\n### HỒI 3: [TÊN HỒI 3]\\n\\n[Nội dung chi tiết văn xuôi Hồi 3...]\\n\\n### HỒI 4: [TÊN HỒI 4]\\n\\n[Nội dung chi tiết văn xuôi Hồi 4...]"\n  }}\n}}\n```\n'''


def parse_youtube_web_gemini_response(raw_text = None):
    '''Phân tích văn bản hoặc JSON copy từ Gemini Web thành cấu trúc kịch bản Winterboy Studio.'''
    pass
# WARNING: Decompyle incomplete


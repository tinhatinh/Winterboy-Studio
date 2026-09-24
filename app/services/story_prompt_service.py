# Source Generated with Decompyle++
# File: story_prompt_service.pyc (Python 3.12)

'''Dịch vụ sinh Image Prompts đồng bộ điện ảnh cho từng phân cảnh kịch bản / SRT.

Đảm bảo chuẩn Hollywood Visual Continuity:
- Khởi tạo và duy trì "Kinh Thánh Tạo Hình" (Visual Continuity Bible):
  + Thập niên & Bối cảnh lịch sử (Era & Setting)
  + Phong cách mỹ thuật & Ánh sáng (Art Style & Lighting)
  + Đặc điểm nhân vật & Trang phục đặc trưng cố định (Character Anchors & Fixed Signature Attire)
- Tự động sinh Image Prompt tiếng Anh chi tiết bám sát từng dòng phụ đề / phân cảnh SRT.
- Đa dạng hóa góc máy quay, chống lặp góc liên tiếp.
- Hỗ trợ xuất file Prompt (.txt, .csv) và sao chép Clipboard linh hoạt cho người dùng tạo ảnh thủ công (Midjourney, Flux, Leonardo, ComfyUI).
'''
from __future__ import annotations
import csv
import json
import logging
import re
import time
import urllib.error as urllib
import urllib.request as urllib
from pathlib import Path
from typing import Any, Callable
from app.services.story_engine import normalize_gemini_model
from app.services.story_image_service import format_srt_timestamp
from app.services.story_youtube_service import get_gemini_keys_pool
logger = logging.getLogger(__name__)
ProgressCb = Callable[([
    str,
    float], None)]
SYSTEM_VISUAL_BIBLE_PROMPT = 'Bạn là Giám đốc Nghệ thuật & Đạo diễn Hình ảnh Điện ảnh (Hollywood Art Director & Visual Continuity Supervisor).\nNhiệm vụ: Phân tích toàn bộ câu chuyện/kịch bản để thiết lập "KINH THÁNH TẠO HÌNH" (VISUAL CONTINUITY BIBLE).\nMục đích tối thượng: Đảm bảo khi tạo hàng chục bức ảnh qua AI (Midjourney, Flux, Leonardo, SDXL), tất cả các ảnh đều ĐỒNG BỘ 100% về thời kỳ lịch sử, phong cách mỹ thuật, gương mặt nhân vật và trang phục.\n\nQUY TẮC BẮT BUỘC:\n1. THẬP NIÊN & BỐI CẢNH (era_setting):\n   - Xác định chính xác thập niên/kỷ nguyên (ví dụ: 1920s Prohibition, Victorian 1880s, 1970s Retro, Feudal Dynasty, Cyberpunk 2080s, Contemporary 2020s...).\n   - Mô tả kiến trúc, công nghệ, đạo cụ, không khí thời đại đặc trưng.\n2. PHONG CÁCH MỸ THUẬT (art_style):\n   - Thể loại điện ảnh (Cinematic 35mm film still, Panavision anamorphic lens, dramatic chiaroscuro lighting, desaturated filmic palette, photorealistic 8k, authentic film grain).\n   - Tương thích và tích hợp Master Prompt (nếu có).\n3. NHÂN VẬT & TRANG PHỤC CỐ ĐỊNH (characters):\n   - Liệt kê các nhân vật chính xuất hiện trong câu chuyện.\n   - Với mỗi nhân vật: Tên, giới tính, độ tuổi ước tính, đặc điểm khuôn mặt/tóc (face structure, eye color, hair style/color).\n   - BỘ TRANG PHỤC ĐẶC TRƯNG CỐ ĐỊNH (signature_attire): Quần áo, chất liệu, màu sắc, phụ kiện chuẩn theo thập niên đã định. Trang phục này sẽ được giữ cố định xuyên suốt câu chuyện để đảm bảo đồng bộ thị giác.\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY:\n{\n  "era_setting": "Detailed era and setting description in English...",\n  "era_setting_vi": "Tóm tắt ngắn gọn thập niên và bối cảnh bằng tiếng Việt...",\n  "art_style": "Detailed cinematic art style, camera, lighting, and medium in English...",\n  "characters": [\n    {\n      "name": "Tên nhân vật",\n      "gender": "male / female",\n      "age": "28 years old",\n      "features": "Pale skin, sharp jawline, emerald green eyes, braided chestnut hair",\n      "signature_attire": "Dark emerald velvet high-collar Victorian gown with silver cameo brooch and charcoal lace cuffs"\n    }\n  ]\n}\n'
SYSTEM_SCENE_PROMPTS_PROMPT = 'Bạn là Chuyên gia Prompt Điện ảnh (Master Cinematic Prompt Engineer).\nDựa trên "KINH THÁNH TẠO HÌNH" (VISUAL CONTINUITY BIBLE) dưới đây, hãy viết Image Prompt chi tiết bằng TIẾNG ANH cho từng phân cảnh kịch bản / dòng phụ đề SRT được giao.\n\n=== KINH THÁNH TẠO HÌNH (BẮT BUỘC TUÂN THỦ 100%) ===\n- THẬP NIÊN & BỐI CẢNH: {era_setting}\n- PHONG CÁCH NGHỆ THUẬT: {art_style}\n- NHÂN VẬT & TRANG PHỤC CỐ ĐỊNH:\n{characters_summary}\n\n=== QUY TẮC VIẾT PROMPT CHO TỪNG PHÂN CẢNH ===\n1. ĐỒNG BỘ NHÂN VẬT: Nếu cảnh có nhân vật xuất hiện, PHẢI sao chép đúng đặc điểm khuôn mặt/tóc và BỘ TRANG PHỤC CỐ ĐỊNH (signature attire) từ Kinh Thánh Tạo Hình. Tuyệt đối KHÔNG tự ý đổi màu tóc, tuổi tác hay trang phục giữa các cảnh.\n2. ĐỒNG BỘ THẬP NIÊN: Mọi chi tiết nền, xe cộ, nội thất, ánh đèn phải phản ánh đúng thập niên đã định ({era_setting}).\n3. BÁM SÁT CÂU PHỤ ĐỀ / PHÂN CẢNH SRT: Prompt phải miêu tả đúng hành động, tâm trạng hoặc sự việc diễn ra ở câu thoại đó.\n4. IMAGE PROMPT (image_prompt): Viết hoàn toàn bằng TIẾNG ANH dành cho Midjourney v6, Flux.1, Leonardo AI, SDXL. Tập trung vào bố cục, ánh sáng chiaroscuro, kết cấu da/vải, góc máy tĩnh ấn tượng.\n5. VIDEO AI PROMPT (video_motion_prompt): Viết hoàn toàn bằng TIẾNG ANH dành cho các model Video AI (Google Veo 3, Runway Gen-3, Luma Dream Machine, Kling AI, Pika, Sora).\n   - Mô tả chuyển động máy quay rõ ràng (slow cinematic push in, gentle pan, Steadicam tracking, slow motion).\n   - Mô tả chuyển động nhân vật, ánh mắt, biểu cảm vi mô (micro-expressions), cử chỉ tự nhiên.\n   - Mô tả chuyển động môi trường và vật lý (volumetric fog drifting, raindrops falling, wind blowing fabric, realistic light reflections, 24fps film look).\n6. ĐA DẠNG HÓA GÓC MÁY ĐIỆN ẢNH: Luân chuyển liên tục các góc máy:\n   - Wide atmospheric establishing shot\n   - Dramatic medium close-up\n   - Over-the-shoulder shot\n   - Low-angle heroic / menacing perspective\n   - Dutch angle / atmospheric deep focus\n   (Tuyệt đối KHÔNG lặp lại một góc máy ở 2 cảnh liên tiếp).\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY:\n{{\n  "scenes": [\n    {{\n      "index": 1,\n      "visual_hint_vi": "1 câu tóm tắt tiếng Việt ngắn gọn về cảnh",\n      "image_prompt": "Cinematic 35mm film still of...",\n      "video_motion_prompt": "Cinematic video shot, smooth camera dolly-in toward Elena turning slowly with apprehension, rain falling, realistic motion, 24fps"\n    }}\n  ]\n}}\n'

def _call_gemini_json(system_prompt, user_content = None, keys = None, key_idx = None, model = (0, 'gemini-2.5-flash', 0.3), temperature = ('system_prompt', 'str', 'user_content', 'str', 'keys', 'list[str]', 'key_idx', 'int', 'model', 'str', 'temperature', 'float', 'return', 'tuple[dict[str, Any] | list[Any], int]')):
    '''Gửi yêu cầu tới Gemini API với chế độ xoay vòng API Keys và tự động parse JSON.'''
    if not keys:
        raise ValueError('Không có API Key Gemini khả dụng.')
    primary_model = normalize_gemini_model(model or 'gemini-2.5-flash')
    fallback_models = [
        primary_model,
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash']
    primary_model = normalize_gemini_model(model or 'gemini-flash-latest')
    fallback_models = [
        primary_model,
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-2.5-flash']
# WARNING: Decompyle incomplete


def build_visual_continuity_bible(script_text = None, master_prompt = None, keys = None, model = ('', None, 'gemini-2.5-flash')):
    '''Phân tích câu chuyện để xây dựng Kinh Thánh Tạo Hình (Era, Art Style, Characters & Signature Costumes).'''
    key_pool = keys or get_gemini_keys_pool()
    if not key_pool:
        raise ValueError('Chưa cấu hình API Key Gemini nào.')
    user_content = f'''MASTER PROMPT GỢI Ý:\n{master_prompt or "Cinematic visual storytelling, photorealistic 8k"}\n\nTOÀN BỘ KỊCH BẢN CÂU CHUYỆN:\n{script_text[:12000]}'''
    (parsed, _) = _call_gemini_json(system_prompt = SYSTEM_VISUAL_BIBLE_PROMPT, user_content = user_content, keys = key_pool, model = model)
    if isinstance(parsed, dict):
        return {
            'era_setting': parsed.get('era_setting', '1950s cinematic era, moody atmosphere'),
            'era_setting_vi': parsed.get('era_setting_vi', 'Thập niên 1950, không khí bí ẩn'),
            'art_style': parsed.get('art_style', master_prompt or 'Cinematic 35mm film photography, 8k, photorealistic'),
            'characters': parsed.get('characters', []) }
    return {
        'era_setting': 'Cinematic narrative era',
        'era_setting_vi': 'Bối cảnh điện ảnh',
        'art_style': master_prompt or 'Cinematic 35mm film photography, 8k, photorealistic',
        'characters': [] }


def _format_characters_for_prompt(characters = None):
    '''Định dạng danh sách nhân vật thành chuỗi tóm tắt cho prompt.'''
    if not characters:
        return '- (Không có nhân vật cố định, tập trung vào không gian và bối cảnh điện ảnh)'
    lines = []
    for idx, c in enumerate(characters, start = 1):
        name = c.get('name', f'''Character {idx}''')
        features = c.get('features', '')
        attire = c.get('signature_attire', '')
        lines.append(f'''- {name} ({c.get('gender', '')}, {c.get('age', '')}):''')
        if features:
            lines.append(f'''  + Đặc điểm: {features}''')
        if not attire:
            continue
        lines.append(f'''  + Trang phục cố định (Signature Attire): {attire}''')
    return '\n'.join(lines)


def generate_synchronized_scene_prompts(scenes, master_prompt = None, visual_bible = None, keys = None, model = ('', None, None, 'gemini-2.5-flash', None), progress_cb = ('scenes', 'list[dict[str, Any]]', 'master_prompt', 'str', 'visual_bible', 'dict[str, Any] | None', 'keys', 'list[str] | None', 'model', 'str', 'progress_cb', 'ProgressCb | None', 'return', 'tuple[list[dict[str, Any]], dict[str, Any]]')):
    '''Sinh danh sách Image Prompts chi tiết bằng tiếng Anh cho từng phân cảnh kịch bản / SRT.

    Đảm bảo 100% nhất quán nhân vật, thập niên, bối cảnh và trang phục.
    '''
    key_pool = keys or get_gemini_keys_pool()
    if not key_pool:
        raise ValueError('Chưa cấu hình API Key Gemini nào.')
    if not scenes:
        return ([], visual_bible or { })
    bible = visual_bible or { }
    if not bible.get('era_setting') or not bible.get('characters'):
        if progress_cb:
            progress_cb('Đang phân tích kịch bản để thiết lập Kinh Thánh Tạo Hình (Visual Continuity Bible)...', 0.1)
        full_text = '\n\n'.join(f'''Phân cảnh {s.get('index', i)}: {s.get('text_segment', '')}''' for i, s in enumerate(scenes, start = 1))
        bible = build_visual_continuity_bible(script_text = full_text, master_prompt = master_prompt, keys = key_pool, model = model)
    chars_summary = _format_characters_for_prompt(bible.get('characters', []))
    era_setting = bible.get('era_setting', 'Cinematic era')
    art_style = bible.get('art_style', master_prompt or 'Cinematic 35mm film photography, 8k')
    system_instruction = SYSTEM_SCENE_PROMPTS_PROMPT.format(era_setting = era_setting, art_style = art_style, characters_summary = chars_summary)
    batch_size = 14
    total_scenes = len(scenes)
# WARNING: Decompyle incomplete


def refine_single_scene_prompt(scene, visual_bible, master_prompt = None, previous_context = None, next_context = None, keys = ('', '', '', None, 'gemini-2.5-flash'), model = ('scene', 'dict[str, Any]', 'visual_bible', 'dict[str, Any]', 'master_prompt', 'str', 'previous_context', 'str', 'next_context', 'str', 'keys', 'list[str] | None', 'model', 'str', 'return', 'dict[str, str]')):
    '''Viết lại / làm giàu cả Image Prompt và Video AI Prompt cho duy nhất một phân cảnh, giữ nguyên tính nhất quán của Visual Bible.'''
    key_pool = keys or get_gemini_keys_pool()
    chars_summary = _format_characters_for_prompt(visual_bible.get('characters', []))
    era_setting = visual_bible.get('era_setting', 'Cinematic era')
    art_style = visual_bible.get('art_style', master_prompt or 'Cinematic 35mm film photography, 8k')
    sys_prompt = f'''Bạn là Chuyên gia Prompt Điện ảnh (Cinematic Prompt Engineer).\nNhiệm vụ: Viết lại CẢ Image Prompt VÀ Video AI Prompt tiếng Anh chi tiết cho duy nhất MỘT phân cảnh kịch bản / phụ đề SRT.\n\nKINH THÁNH TẠO HÌNH (BẮT BUỘC TUÂN THỦ):\n- THẬP NIÊN & BỐI CẢNH: {era_setting}\n- PHONG CÁCH MỸ THUẬT: {art_style}\n- NHÂN VẬT & TRANG PHỤC CỐ ĐỊNH:\n{chars_summary}\n\nYÊU CẦU:\n1. Đảm bảo nhân vật và trang phục (nếu xuất hiện) chuẩn xác 100% theo Kinh Thánh Tạo Hình.\n2. image_prompt: Prompt ảnh tĩnh (Midjourney/Flux), chi tiết bố cục, ánh sáng chiaroscuro, kết cấu da/vải.\n3. video_motion_prompt: Prompt video AI (Veo 3/Runway/Kling), chi tiết chuyển động máy quay (push-in, pan, tracking), biểu cảm nhân vật, tương tác vật lý, 24fps.\n4. Trả về JSON:\n{{\n  "visual_hint_vi": "1 câu tóm tắt tiếng Việt",\n  "image_prompt": "Cinematic 35mm film still of...",\n  "video_motion_prompt": "Cinematic video shot, smooth camera dolly-in toward..."\n}}\n'''
    user_content = f'''Cảnh trước: {previous_context}\nPhân cảnh hiện tại #{scene.get('index', 1)}: {scene.get('text_segment', '')}\nCảnh tiếp theo: {next_context}'''
    
    try:
        (parsed, _) = _call_gemini_json(system_prompt = sys_prompt, user_content = user_content, keys = key_pool, model = model, temperature = 0.4)
        if isinstance(parsed, dict):
            img_p = str(parsed.get('image_prompt', '')).strip()
            vid_p = str(parsed.get('video_motion_prompt', '')).strip()
            if vid_p and img_p:
                vid_p = f'''Cinematic video clip, slow camera push in, {img_p}, 24fps'''
            return {
                'image_prompt': img_p,
                'video_motion_prompt': vid_p,
                'visual_hint_vi': str(parsed.get('visual_hint_vi', '')).strip() }
        return {
            'image_prompt': scene.get('image_prompt', ''),
            'video_motion_prompt': scene.get('video_motion_prompt', ''),
            'visual_hint_vi': scene.get('visual_hint_vi', '') }
    except Exception as exc:
        logger.warning('Lỗi refine single scene prompt: %s', exc)
        return {
            'image_prompt': scene.get('image_prompt', ''),
            'video_motion_prompt': scene.get('video_motion_prompt', ''),
            'visual_hint_vi': scene.get('visual_hint_vi', '') }



def format_prompts_for_clipboard(scenes = None, mode = None, prefix = None, suffix = ('full', '', '')):
    """Định dạng danh sách prompt thành văn bản để sao chép vào Clipboard.

    mode:
    - 'full': Bao gồm chỉ số cảnh, thời gian SRT, câu thoại, Prompt Ảnh và Prompt Video AI.
    - 'images_only' hoặc 'prompts_only': Mỗi dòng 1 Image Prompt thuần túy (cho Midjourney / bulk queue).
    - 'videos_only': Mỗi dòng 1 Video AI Motion Prompt thuần túy (cho Runway / Luma / Kling / Veo queue).
    - 'filename_mapped': Gắn liền tên file tương ứng (scene_001.png & scene_001.mp4).
    """
    lines = []
    p_clean = f'''{prefix.strip()} ''' if prefix.strip() else ''
    s_clean = f''' {suffix.strip()}''' if suffix.strip() else ''
    for idx, s in enumerate(scenes, start = 1):
        s_idx = s.get('index', idx)
        p_img = s.get('image_prompt', '').strip()
        p_vid = s.get('video_motion_prompt', '').strip()
        if p_vid and p_img:
            p_vid = f'''Cinematic video shot, camera motion, {p_img}, 24fps'''
        final_img = f'''{p_clean}{p_img}{s_clean}'''.strip()
        final_vid = f'''{p_clean}{p_vid}{s_clean}'''.strip()
        seg = s.get('text_segment', '').strip()
        t_start = float(s.get('start_time_s', 0))
        t_end = float(s.get('end_time_s', 0))
        time_str = f'''[{format_srt_timestamp(t_start)} --> {format_srt_timestamp(t_end)}]''' if t_end > 0 else ''
        if mode in ('images_only', 'prompts_only'):
            lines.append(final_img)
            continue
        if mode == 'videos_only':
            lines.append(final_vid)
            continue
        if mode == 'filename_mapped':
            lines.append(f'''scene_{s_idx:03d}.png: {final_img}''')
            lines.append(f'''scene_{s_idx:03d}.mp4: {final_vid}\n''')
            continue
        lines.append(f'''=== PHÂN CẢNH #{s_idx} {time_str} ===''')
        if seg:
            lines.append(f'''Câu thoại / SRT: {seg}''')
        if s.get('visual_hint_vi'):
            lines.append(f'''Gợi ý bối cảnh: {s.get('visual_hint_vi')}''')
        lines.append(f'''🖼 Prompt Ảnh AI (Midjourney/Flux): {final_img}''')
        lines.append(f'''🎬 Prompt Video AI (Veo 3/Runway/Kling): {final_vid}\n''')
    return '\n'.join(lines)


def export_prompts_to_txt(scenes = None, output_path = None, visual_bible = None, prefix = (None, '', ''), suffix = ('scenes', 'list[dict[str, Any]]', 'output_path', 'str | Path', 'visual_bible', 'dict[str, Any] | None', 'prefix', 'str', 'suffix', 'str', 'return', 'Path')):
    '''Xuất toàn bộ danh sách Prompts (Cả Ảnh và Video AI) cùng Kinh Thánh Tạo Hình thành file text (.txt).'''
    out_file = Path(output_path)
    out_file.parent.mkdir(parents = True, exist_ok = True)
    header = [
        '================================================================================',
        'DANH SÁCH PROMPT HÌNH ẢNH & VIDEO AI ĐỒNG BỘ CHO KỂ CHUYỆN (WINTERBOY STUDIO PRO)',
        '================================================================================\n']
    if visual_bible:
        header.append('--- KINH THÁNH TẠO HÌNH (VISUAL CONTINUITY BIBLE) ---')
        if visual_bible.get('era_setting'):
            header.append(f'''Thập niên & Bối cảnh: {visual_bible.get('era_setting')}''')
        if visual_bible.get('art_style'):
            header.append(f'''Phong cách mỹ thuật: {visual_bible.get('art_style')}''')
        chars = visual_bible.get('characters', [])
        if chars:
            header.append('Nhân vật & Trang phục cố định:')
            for c in chars:
                header.append(f'''  * {c.get('name')}: {c.get('features')} | Trang phục: {c.get('signature_attire')}''')
        header.append('\n================================================================================\n')
    body = format_prompts_for_clipboard(scenes, mode = 'full', prefix = prefix, suffix = suffix)
    content = '\n'.join(header) + '\n' + body
    out_file.write_text(content, encoding = 'utf-8')
    logger.info('Đã xuất file prompts: %s', out_file)
    return out_file


def export_prompts_to_csv(scenes = None, output_path = None, prefix = None, suffix = ('', '')):
    '''Xuất danh sách Prompts (Cả Ảnh và Video AI) thành bảng tính CSV/Excel để theo dõi và sản xuất media hàng loạt.'''
    out_file = Path(output_path)
    out_file.parent.mkdir(parents = True, exist_ok = True)
    p_clean = f'''{prefix.strip()} ''' if prefix.strip() else ''
    s_clean = f''' {suffix.strip()}''' if suffix.strip() else ''
    with open(out_file, 'w', encoding = 'utf-8-sig', newline = '') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Phân Cảnh',
            'Tên File Ảnh Tương Ứng',
            'Tên File Video Tương Ứng',
            'Thời Gian SRT Bắt Đầu',
            'Thời Gian SRT Kết Thúc',
            'Câu Thoại Kịch Bản / SRT',
            'Gợi Ý Tiếng Việt',
            'Prompt Hình Ảnh Tiếng Anh (Image Prompt)',
            'Prompt Video AI Tiếng Anh (Video Motion Prompt)',
            'Đã Có File Ảnh',
            'Đã Có File Video'])
        for idx, s in enumerate(scenes, start = 1):
            s_idx = s.get('index', idx)
            t_start = float(s.get('start_time_s', 0))
            t_end = float(s.get('end_time_s', 0))
            p_img = s.get('image_prompt', '').strip()
            p_vid = s.get('video_motion_prompt', '').strip()
            if p_vid and p_img:
                p_vid = f'''Cinematic video clip, camera motion, {p_img}, 24fps'''
            final_img = f'''{p_clean}{p_img}{s_clean}'''.strip()
            final_vid = f'''{p_clean}{p_vid}{s_clean}'''.strip()
            has_img = 'Đã có' if s.get('image_path') and Path(s.get('image_path')).is_file() else 'Chưa'
            has_vid = 'Đã có' if s.get('video_path') and Path(s.get('video_path')).is_file() else 'Chưa'
            writer.writerow([
                f'''Scene #{s_idx}''',
                f'''scene_{s_idx:03d}.png''',
                f'''scene_{s_idx:03d}.mp4''',
                format_srt_timestamp(t_start),
                format_srt_timestamp(t_end),
                s.get('text_segment', '').strip(),
                s.get('visual_hint_vi', '').strip(),
                final_img,
                final_vid,
                has_img,
                has_vid])
    logger.info('Đã xuất file CSV prompts: %s', out_file)
    return out_file


# Source Generated with Decompyle++
# File: story_ai_creator_service.pyc (Python 3.12)

'''Dịch vụ sáng tạo kịch bản & Master Prompt độc bản (AI Story & Style Creator Engine).

Cung cấp:
- Bộ dữ liệu ngẫu nhiên (Random Datasets) phong phú: Ý tưởng, Nhân vật, Bối cảnh.
- Trình dựng Prompt tối ưu hóa cho Web Chrome (ChatGPT / Gemini) và API với quy tắc độ dài nghiêm ngặt.
- Trình gọi API Gemini tự động với xoay vòng key và model dự phòng (Fallback).
'''
from __future__ import annotations
import json
import logging
import random
import time
import urllib.error as urllib
import urllib.request as urllib
from typing import Any, Callable
from app.services.story_engine import get_translation_api_keys, normalize_gemini_model
logger = logging.getLogger(__name__)
ProgressCb = Callable[([
    float,
    str], None)]
AI_CREATOR_LENGTH_MAP: 'dict[str, str]' = {
    'short': 'Ngắn (~4.000 ký tự · Dự đoán video ~3 - 5 phút)',
    'medium': 'Vừa (~10.000 ký tự · Dự đoán video ~10 - 14 phút)',
    'long': 'Dài chuyên sâu (~30.000 - 50.000 ký tự · Dự đoán video ~30 - 50 phút, Xoay 6 Key)',
    'max': 'Cực đại (~100.000 ký tự · Dự đoán video ~1h45 - 2h15, Xoay Key)' }
RANDOM_IDEAS: 'list[str]' = [
    'Một vụ mất tích bí ẩn tại thị trấn vùng cao bị tuyết cô lập, nơi mọi nhân chứng đều che giấu một sự thật kinh hoàng 10 năm trước.',
    'Bản di chúc kỳ lạ của một tỷ phú ẩn dật buộc 4 người thừa kế phải quay về ngôi biệt thự cổ và trải qua 7 đêm thử thách tâm lý.',
    'Cuộc trả thù âm thầm nhưng tàn khốc của một người thợ sửa đồng hồ già đối với kẻ từng hủy hoại gia đình ông 30 năm trước.',
    'Một kỹ sư an ninh mạng phát hiện phần mềm gián điệp tinh vi điều khiển hành vi của hàng triệu cư dân trong một đô thị thông minh.',
    'Hành trình sinh tồn khốc liệt của phi hành đoàn tàu thám hiểm mắc kẹt trên một hòn đảo hoang dã chứa những vết tích nền văn minh đã biến mất.',
    'Vụ án mạng trong phòng kín trên chuyến tàu đêm xuyên quốc gia, nơi hung thủ dường như không hề tồn tại trên danh sách hành khách.',
    'Câu chuyện có thật cảm động về người cha nghèo khổ vượt 2.000 cây số bằng chiếc xe đạp cọc cạch để tìm đứa con trai thất lạc.',
    'Một nhà khảo cổ học khai quật được cổ vật bằng đồng có khắc những cảnh báo trùng khớp đến rợn người với các thảm họa hiện đại.',
    'Một vụ tráo đổi thân phận tinh vi giữa hai chị em sinh đôi dẫn đến màn đấu trí sinh tử trong giới thượng lưu tài chính.',
    'Bí mật đen tối đằng sau sự thành công rực rỡ của một đầu bếp danh tiếng, liên quan đến một công thức gia truyền đẫm máu.',
    'Cuộc đào thoát nghẹt thở của một nhân chứng quan trọng khỏi sự truy sát của tổ chức tội phạm xuyên biên giới.',
    'Một người đàn ông tỉnh dậy sau cơn hôn mê và phát hiện mình có ký ức của một người lạ đã qua đời trong một vụ tai nạn bí ẩn.',
    'Cuộc đối đầu ngầm giữa một đặc vụ kỳ cựu và một tên trùm thao túng tâm lý khét tiếng trong trại giam bảo mật tối đa.',
    'Một ngôi làng ven biển bị nguyền rủa, nơi cứ mỗi đêm trăng tròn lại có một người dân bước xuống đại dương mà không bao giờ quay lại.',
    'Hành trình của một bác sĩ giải phẫu bệnh phát hiện dấu vết chất độc lạ trong cơ thể các nạn nhân của một chuỗi án tử bất thường.']
RANDOM_CHARACTERS: 'list[str]' = [
    'Cựu thanh tra cảnh sát mắc chứng mất ngủ kinh niên, bị ám ảnh bởi vụ án oan mà chính mình từng kết luận sai.',
    'Nữ tiến sĩ giám định pháp y lạnh lùng, luôn tin vào số liệu khoa học cho đến khi gặp manh mối vượt ngoài hiểu biết.',
    'Người thợ rèn trầm lặng mang vết sẹo dài trên gương mặt, che giấu quá khứ là tay súng bắn tỉa xuất sắc.',
    'Nhà báo điều tra dũng cảm, sẵn sàng mạo hiểm tính mạng để vạch trần đường dây tham nhũng nghìn tỷ.',
    'Kỹ sư phần mềm hướng nội tình cờ nắm giữ mã khóa bảo mật của một khối tài sản ngầm khổng lồ.',
    'Người phụ nữ đơn thân kiên cường, vừa làm việc quần quật vừa âm thầm thu thập bằng chứng rửa sạch thanh danh cho cha.',
    'Vị thẩm phán nghiêm khắc đứng trước lựa chọn sinh tử giữa việc giữ vững cán cân công lý hay cứu mạng con gái duy nhất.',
    "Một tay lừa đảo tài chính bậc thầy quyết định 'rửa tay gác kiếm' nhưng bị ép thực hiện phi vụ cuối cùng.",
    'Người thợ săn già sống cô độc nơi bìa rừng nguyên sinh, am hiểu từng dấu vết của thú hoang và con người.',
    'Bác sĩ tâm thần thiên tài có khả năng nhìn thấu lời nói dối của người khác nhưng lại không nhận ra sự phản bội của người đầu ấp tay gối.',
    'Người lính công binh giải ngũ mang chứng rối loạn căng thẳng sau chấn thương (PTSD), nhạy bén với mọi nguy hiểm.',
    'Nữ luật sư hình sự trẻ tuổi nhưng sắc sảo, chuyên nhận bào chữa cho những vụ án tưởng chừng vô phương cứu vãn.']
RANDOM_SETTINGS: 'list[str]' = [
    'Thị trấn mỏ than bỏ hoang chìm trong sương mù và mưa phùn lạnh giá ở vùng núi phía Bắc thập niên 1980.',
    'Khu phố cảng công nghiệp sầm uất với những container rỉ sét, cần cẩu khổng lồ và ánh đèn vàng mờ ảo trong đêm mưa.',
    'Dinh thự cổ phong cách Gothic biệt lập trên vách đá cheo leo nhìn ra đại dương cuộn sóng gầm gào.',
    'Thành phố ngầm hiện đại với những hành lang ánh sáng xanh neon, màn hình giám sát và hệ thống máy chủ ẩm thấp.',
    'Ngôi làng cổ kính ven sông với những mái ngói rêu phong, con hẻm lát đá hẹp và không khí tĩnh mịch đến ngột ngạt.',
    'Trạm nghiên cứu khí tượng đơn độc giữa biển băng tuyết Bắc Cực, cách xa nền văn minh hàng trăm hải lý.',
    'Khu chợ đêm sầm uất đầy mùi khói than, tiếng ồn ào và những ngõ ngách ngoằn ngoèo ẩn chứa góc khuất ngầm.',
    'Khu biệt thự nghỉ dưỡng xa hoa nhưng bị cắt đứt liên lạc bởi một cơn bão nhiệt đới dữ dội.',
    'Khu rừng thông nguyên sinh rậm rạp vào mùa thu, lá khô rụng đầy mặt đất và tiếng gió rít qua những khe núi sâu.',
    'Chuyến tàu hỏa tốc hành cổ điển vượt qua những hẻm núi tuyết hiểm trở vào một đêm mùa đông giá lạnh.']

def _extract_clean_json_from_text(raw_text = None):
    '''Bóc tách JSON an toàn từ phản hồi text của AI (hỗ trợ markdown block hoặc chuỗi thuần).'''
    if not raw_text:
        return None
    text = raw_text.strip()
    if '```json' in text:
        
        try:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end != -1:
                return json.loads(text[start:end].strip())
            return None.loads(text[start:].strip())
            if '```' in text:
                
                try:
                    start = text.find('```') + 3
                    end = text.find('```', start)
                    if end != -1:
                        return json.loads(text[start:end].strip())
                    return None.loads(text[start:].strip())
                    first_brace = text.find('{')
                    last_brace = text.rfind('}')
                    if first_brace != -1 and last_brace > first_brace:
                        
                        try:
                            candidate = text[first_brace:last_brace + 1]
                            return json.loads(candidate)
                            return None
                            except Exception:
                                continue
                            except Exception:
                                continue
                        except Exception:
                            return None





def get_random_idea():
    '''Trả về ngẫu nhiên một ý tưởng cốt truyện hấp dẫn.'''
    return random.choice(RANDOM_IDEAS)


def get_random_character():
    '''Trả về ngẫu nhiên một nhân vật chính có xung đột sâu sắc.'''
    return random.choice(RANDOM_CHARACTERS)


def get_random_setting():
    '''Trả về ngẫu nhiên một bối cảnh điện ảnh cuốn hút.'''
    return random.choice(RANDOM_SETTINGS)


def get_random_all():
    '''Trả về ngẫu nhiên bộ 3 (Ý tưởng, Nhân vật, Bối cảnh).'''
    return (get_random_idea(), get_random_character(), get_random_setting())


def generate_ai_random_all(keys = None, model = None):
    '''Sử dụng Gemini AI để sinh ngẫu nhiên 1 bộ 3 độc đáo (Ý tưởng, Nhân vật, Bối cảnh) trong 1 request.
    Nếu không có mạng hoặc lỗi, tự động fallback về bộ dữ liệu mẫu nội bộ.'''
    pass
# WARNING: Decompyle incomplete


def generate_ai_random_idea(keys = None, model = None):
    '''Sử dụng Gemini AI để sinh ngẫu nhiên 1 ý tưởng truyện kịch tính mới lạ.'''
    pass
# WARNING: Decompyle incomplete


def generate_ai_random_character(idea = None, keys = None, model = None):
    '''Sử dụng Gemini AI để sinh ngẫu nhiên 1 nhân vật chính có chiều sâu tâm lý và xung đột gay gắt (hài hòa với ý tưởng nếu có).'''
    pass
# WARNING: Decompyle incomplete


def generate_ai_random_setting(idea = None, keys = None, model = None):
    '''Sử dụng Gemini AI để sinh ngẫu nhiên 1 bối cảnh & không gian điện ảnh giàu cảm xúc (hài hòa với ý tưởng nếu có).'''
    pass
# WARNING: Decompyle incomplete


def build_ai_story_creator_prompt(idea, character, setting, master_prompt_style = None, tone_style = None, target_length = None, language = ('', '', '', 'Tài liệu / Vụ án bí ẩn kịch tính (True Crime & Mystery)', 'medium', 'Tiếng Việt', 'Tiếng Anh (English)'), desc_language = ('idea', 'str', 'character', 'str', 'setting', 'str', 'master_prompt_style', 'str', 'tone_style', 'str', 'target_length', 'str', 'language', 'str', 'desc_language', 'str', 'return', 'str')):
    '''Tạo Prompt tối ưu hóa cho ChatGPT Web, Gemini Web và Gemini API.

    Chứa QUY TẮC ĐỘ DÀI NGHIÊM NGẶT và cấu trúc JSON chuẩn xác để nạp thẳng vào StoryEditor.
    '''
    len_desc = AI_CREATOR_LENGTH_MAP.get(target_length, AI_CREATOR_LENGTH_MAP['medium'])
    if target_length == 'short':
        target_words = 'khoảng 800 - 1.000 từ'
        char_rule_num = '~4.000 ký tự'
    elif target_length == 'long':
        target_words = 'khoảng 6.000 - 10.000 từ'
        char_rule_num = '~30.000 - 50.000 ký tự'
    elif target_length == 'max':
        target_words = 'khoảng 18.000 - 25.000 từ (Siêu trường ca nhiều chương hồi chuyên sâu)'
        char_rule_num = '~100.000 ký tự'
    else:
        target_words = 'khoảng 2.000 - 2.500 từ'
        char_rule_num = '~10.000 ký tự'
    if not master_prompt_style.strip():
        master_prompt_style.strip()
    style_guide = 'Cinematic authentic storytelling shot, photorealistic, 35mm photograph, dramatic chiaroscuro lighting, moody atmosphere, 8k resolution'
    character_section = f'''- Nhân vật chính: {character}\n''' if character.strip() else ''
    setting_section = f'''- Bối cảnh & Không gian: {setting}\n''' if setting.strip() else ''
    return f'''Bạn là một nhà biên kịch điện ảnh tài hoa (Master Screenwriter) và đạo diễn sản xuất video kể chuyện (Storytelling Video Producer) triệu view quốc tế.\n\nNHIỆM VỤ:\nSáng tạo một KỊCH BẢN KỂ CHUYỆN NGUYÊN BẢN (100% Zero Copyright) lôi cuốn, kịch tính, chân thực và một MASTER PROMPT tạo hình ảnh đồng bộ chuẩn điện ảnh dựa trên các yêu cầu sau:\n\nTHÔNG TIN ĐẦU VÀO:\n- Ý tưởng cốt truyện: {idea}\n{character_section}{setting_section}- Phong cách hình ảnh mong muốn: {style_guide}\n- Tông giọng câu chuyện: {tone_style}\n- Ngôn ngữ kịch bản: {language}\n- Ngôn ngữ mô tả video: {desc_language} (Mặc định là Tiếng Anh)\n- Mức độ dài mục tiêu: {len_desc} ({target_words})\n\nQUY TẮC ĐỘ DÀI BẮT BUỘC (TUYỆT ĐỐI TUÂN THỦ):\n1. Kịch bản BẮT BUỘC phải viết ĐỦ VÀ ĐÚNG số lượng ký tự yêu cầu là {char_rule_num} ({len_desc}, {target_words}).\n2. Cho phép mức chênh lệch nhẹ trong phạm vi 5-10%, TUYỆT ĐỐI KHÔNG ĐƯỢC VIẾT QUÁ NGẮN, không được tóm tắt sơ sài, không được lược bỏ diễn biến hay cắt ngắn lời văn.\n3. TUYỆT ĐỐI KHÔNG ĐƯỢC VIẾT QUÁ DÀI vượt quá hạn mức yêu cầu.\n4. Triển khai đầy đủ các Hồi: Mở đầu gây tò mò kích thích (Hook), Thắt nút mâu thuẫn, Diễn biến nghẹt thở, Cao trào bùng nổ, Cú twist bất ngờ và Dư âm sâu sắc.\n5. Mỗi đoạn văn xuôi phải được trau chuốt từng câu chữ, giàu tính hình tượng và cảm xúc điện ảnh.\n\nQUY CÁCH ĐẶT TIÊU ĐỀ, CHỦ ĐỀ, MÔ TẢ & THUMBNAIL:\n1. video_title: Đặt một tiêu đề video SIÊU HẤP DẪN, kịch tính, khơi gợi sự tò mò mạnh mẽ (bằng ngôn ngữ kịch bản: {language}).\n2. video_topic_vi: Tóm tắt đề tài / ý nghĩa câu chuyện bằng MỘT câu Tiếng Việt súc tích, ngắn gọn (ví dụ: \'Bí ẩn vụ mất tích tại thị trấn mỏ than năm 1985\').\n3. video_description: Viết đoạn tóm tắt kịch bản / cốt truyện hấp dẫn, sâu sắc bằng {desc_language} (CHỈ CHỨA NỘI DUNG MÔ TẢ TRUYỆN THUẦN TÚY, TUYỆT ĐỐI KHÔNG CHÈN CÂU KÊU GỌI LIKE/SHARE/SUBSCRIBE, không chèn hashtag, không chèn lời chào thừa thãi).\n4. master_prompt: Viết hoàn toàn bằng TIẾNG ANH chuyên nghiệp (dành cho Midjourney, Flux, Imagen, Stable Diffusion). Mô tả chi tiết phong cách nghệ thuật, ánh sáng (lighting), góc máy (35mm film / cinematic), bảng màu (color palette), bối cảnh và cảm xúc nhân vật đồng bộ 100% với cốt truyện.\n5. thumbnail_prompt: Viết hoàn toàn bằng TIẾNG ANH prompt tạo ảnh Thumbnail YouTube triệu view: Cinematic 35mm film still, photorealistic 8k, góc nhìn cận cảnh đặc tả cảm xúc cao trào kịch tính nhất, ánh sáng tương phản chiaroscuro, bố cục vàng 16:9, kèm chữ text overlay giật gân (ví dụ: text overlay: "[SHORT_HOOK]").\n6. era_setting: Mô tả kỷ nguyên, thời đại và bối cảnh địa danh bằng Tiếng Anh (ví dụ: Victorian 1880s London, foggy cobblestone streets).\n7. characters: Danh sách nhân vật chính bằng tiếng Anh để khóa ngoại hình nhất quán (Visual Bible).\n8. script_text: Toàn bộ nội dung văn bản kịch bản chi tiết, chia thành các đoạn văn mạch lạc (mỗi đoạn xuống dòng để sau này dễ bóc tách thành các phân cảnh video).\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON DUY NHẤT (Chỉ trả về khối mã JSON trong cặp dấu ```json ... ```, KHÔNG viết bất kỳ lời chào, ghi chú hay giải thích nào bên ngoài):\n```json\n{{\n  "video_title": "Tiêu đề video cực thu hút ở đây",\n  "video_topic_vi": "Tóm tắt chủ đề kịch bản bằng 1 câu Tiếng Việt",\n  "video_description": "Pure narrative story synopsis in the requested description language without CTA...",\n  "master_prompt": "Cinematic authentic storytelling shot, photorealistic 8k, 35mm film photograph, dramatic atmospheric lighting...",\n  "thumbnail_prompt": "Cinematic 35mm film still, ultra-dramatic high-contrast YouTube thumbnail composition...",\n  "era_setting": "Detailed era & setting description in English",\n  "characters": [\n    {{\n      "name": "Character Name in English",\n      "gender": "male hoặc female",\n      "age": "Age in English",\n      "features": "Distinct facial features, hair, eye color in English",\n      "signature_attire": "Fixed recognizable attire in English for visual continuity"\n    }}\n  ],\n  "script_text": "Toàn bộ nội dung kịch bản văn xuôi điện ảnh đầy đủ chi tiết đúng số lượng ký tự yêu cầu..."\n}}\n```\n'''


def generate_ai_story_via_api(idea, character, setting, master_prompt_style, tone_style, target_length = None, language = None, desc_language = None, model = ('', '', '', 'Tài liệu / Vụ án bí ẩn kịch tính (True Crime & Mystery)', 'medium', 'Tiếng Việt', 'Tiếng Anh (English)', None, None), progress_cb = ('idea', 'str', 'character', 'str', 'setting', 'str', 'master_prompt_style', 'str', 'tone_style', 'str', 'target_length', 'str', 'language', 'str', 'desc_language', 'str', 'model', 'str | None', 'progress_cb', 'ProgressCb | None', 'return', 'dict[str, Any]')):
    '''Tự động gọi Gemini API với cơ chế xoay vòng Key và Fallback Model để sinh kịch bản & Master Prompt độc bản.'''
    pass
# WARNING: Decompyle incomplete


def generate_ai_story_description(title = None, topic = None, script_sample = None, language = ('', '', 'English', None), model = ('title', 'str', 'topic', 'str', 'script_sample', 'str', 'language', 'str', 'model', 'str | None', 'return', 'str')):
    '''Tự động dùng Gemini AI để viết mô tả video thuần túy theo ngôn ngữ được chọn (mặc định: English).

    Chỉ chứa nội dung mô tả cốt truyện/kịch bản, tuyệt đối không chứa câu kêu gọi like/share/subscribe.
    '''
    generate_story_description_fallback = generate_story_description_fallback
    import app.services.story_engine
    keys = get_translation_api_keys()
    if not keys:
        return generate_story_description_fallback(title, topic, language = language)
    lang_instruction = f'''{language}.'''
    lang_lower = language.lower()
    if 'english' in lang_lower or 'tiếng anh' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent, evocative, dramatic English.'
    elif 'tiếng việt' in lang_lower or 'vietnamese' in lang_lower:
        lang_instruction = 'Viết hoàn toàn bằng Tiếng Việt văn phong điện ảnh truyền cảm, hấp dẫn.'
    elif 'tiếng trung' in lang_lower or 'chinese' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent Chinese (Simplified).'
    elif 'tiếng nhật' in lang_lower or 'japanese' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent Japanese.'
    elif 'tiếng hàn' in lang_lower or 'korean' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent Korean.'
    elif 'tiếng pháp' in lang_lower or 'french' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent French.'
    elif 'tiếng tây ban nha' in lang_lower or 'spanish' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent Spanish.'
    elif 'tiếng đức' in lang_lower or 'german' in lang_lower:
        lang_instruction = 'Write ENTIRELY in fluent German.'
    prompt = f'''You are a master storyteller and professional film synopsis writer.\nWrite a captivating, dramatic synopsis/description for the following video story.\n\nStory Title: {title}\nTopic / Theme: {topic}\nStory Context / Script Excerpt:\n{script_sample[:3000]}\n\nSTRICT REQUIREMENTS:\n1. {lang_instruction}\n2. ONLY output the pure story description / synopsis (1 to 2 well-crafted paragraphs).\n3. DO NOT include call-to-action lines (DO NOT write \'Like, share, subscribe\', \'Stay tuned\', \'Click the bell\', etc.).\n4. DO NOT include introductory greetings (such as \'Here is the description\', \'Sure\', \'Synopsis:\').\n5. Output ONLY the pure narrative description text itself.\n'''
    if not model:
        model
    primary = normalize_gemini_model('gemini-flash-latest')
    candidate_models = [
        primary,
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-2.5-flash']
# WARNING: Decompyle incomplete


def generate_thumbnail_prompt_fallback(title = None, topic = None, master_prompt = None):
    '''Tạo Prompt Thumbnail dự phòng chuẩn điện ảnh YouTube khi không có API key.'''
    if not master_prompt:
        master_prompt
    if not ''.strip():
        ''.strip()
    base_style = 'Cinematic 35mm film still, photorealistic 8k, dramatic lighting, moody atmosphere'
    if not title:
        title
        if not topic:
            topic
    hook_title = 'THE SHOCKING TRUTH'.strip().upper()
    return f'''{base_style}, high-impact viral YouTube thumbnail composition, dramatic emotional climax, intense expressive character reaction, striking chiaroscuro rim lighting, shallow depth of field, vivid cinematic color grading, bold typography text overlay: "{hook_title}", master composition, 8k resolution --ar 16:9'''


def generate_ai_thumbnail_prompt(title = None, topic = None, script_sample = None, master_prompt = ('', '', '', None), model = ('title', 'str', 'topic', 'str', 'script_sample', 'str', 'master_prompt', 'str', 'model', 'str | None', 'return', 'str')):
    '''Tự động sinh Prompt Thumbnail YouTube triệu view, kịch tính, cinematic bằng tiếng Anh.'''
    keys = get_translation_api_keys('Gemini')
    if not keys:
        return generate_thumbnail_prompt_fallback(title, topic, master_prompt)
    if not master_prompt:
        master_prompt
    prompt = f'''{title}\n- Theme / Topic: {topic}\n- Art Style / Master Prompt: {'Cinematic 35mm film still, photorealistic 8k, dramatic chiaroscuro lighting'}\n- Story Excerpt:\n{script_sample[:2500]}\n\nSTRICT REQUIREMENTS:\n1. Write ENTIRELY in professional, evocative ENGLISH.\n2. Focus on an extreme emotional climax or shocking moment (a stunning character reaction, disbelief, tears, confrontation, or mystery).\n3. Specify cinematic composition: wide establishing or intense medium close-up, rule of thirds, dramatic chiaroscuro rim lighting, deep shadows, atmospheric mist, shallow depth of field.\n4. Include a short punchy curiosity text overlay directive (e.g., text overlay: "SHORT DRAMATIC HOOK").\n5. Output ONLY the pure prompt text in 1 powerful paragraph (no markdown, no quotes around the entire output, no explanations).\n'''
    if not model:
        model
    primary = normalize_gemini_model('gemini-flash-latest')
    candidate_models = [
        primary,
        'gemini-flash-latest',
        'gemini-flash-lite-latest',
        'gemini-2.5-flash']
# WARNING: Decompyle incomplete


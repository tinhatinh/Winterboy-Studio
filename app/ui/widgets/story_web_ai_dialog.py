# Source Generated with Decompyle++
# File: story_web_ai_dialog.pyc (Python 3.12)

'''Cửa sổ Modal hỗ trợ bóc tách phân cảnh qua Web ChatGPT / Gemini trên trình duyệt Chrome của người dùng.'''
from __future__ import annotations
import json
import logging
import os
import subprocess
import webbrowser
from typing import Any, Callable
import customtkinter as ctk
from app.config.theme import ACCENT, ACCENT_HOVER, BG_CARD, BG_DARK, BG_PANEL, BORDER, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM, TEXT_MUTED
from app.services.story_engine import CAMERA_MOTIONS, StoryScene, _parse_and_build_scenes
logger = logging.getLogger(__name__)
URL_CHATGPT = 'https://chatgpt.com'
URL_GEMINI = 'https://gemini.google.com'

def find_chrome_executable():
    '''Tìm đường dẫn tới file chrome.exe trên máy Windows.'''
    candidates = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        os.path.expanduser('~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe')]
    for p in candidates:
        if not os.path.isfile(p):
            continue
        
        return candidates, p


def open_in_chrome(url = None):
    '''Mở URL trực tiếp bằng trình duyệt Chrome hiện tại của người dùng.'''
    chrome_path = find_chrome_executable()
    if chrome_path:
        
        try:
            subprocess.Popen([
                chrome_path,
                url])
            return None
            webbrowser.open(url)
            return None
        except Exception:
            e = None
            logger.warning('Không thể mở Chrome trực tiếp: %s', e)
            e = None
            del e
            continue
            e = None
            del e



def build_web_ai_prompt(script_text = None, master_prompt = None):
    '''Tạo Prompt tối ưu hóa cho ChatGPT Web và Gemini Web để bóc tách toàn bộ kịch bản ra JSON chuẩn.'''
    if not master_prompt.strip():
        master_prompt.strip()
    style_part = 'Cinematic, photorealistic 8k, dramatic lighting, moody atmosphere, 35mm film look'
    return f'''Bạn là đạo diễn kịch bản và chuyên gia sản xuất video storytelling điện ảnh đỉnh cao (phong cách người thật việc thật, tài liệu kịch tính, điện ảnh chân thực, dành cho khán giả quốc tế).\n\nNhiệm vụ: Phân tích toàn bộ kịch bản bên dưới thành các Phân Cảnh (Scenes) điện ảnh lôi cuốn.\n\nQUY TẮC ĐẶT TÊN, CHỦ ĐỀ, MÔ TẢ VÀ THUMBNAIL VIDEO (YOUTUBE / TIKTOK):\n1. video_title: Sinh ra MỘT tiêu đề video SIÊU THU HÚT (clickbait, drama, gây tò mò) tóm tắt toàn bộ cốt truyện (bằng ngôn ngữ của kịch bản). Tiêu đề này trả về ở cấp cao nhất của JSON.\n2. video_topic_vi: Tóm tắt chủ đề / ý nghĩa kịch bản bằng 1 câu Tiếng Việt ngắn gọn, súc tích (ví dụ: \'Vụ án bí ẩn được phơi bày sau 10 năm điều tra\' hoặc \'Hành trình vượt nghịch cảnh phi thường\') để người dùng biết video đang làm về chủ đề gì.\n3. video_description: Viết MỘT ĐOẠN MÔ TẢ VIDEO HOÀN CHỈNH chuẩn SEO YouTube / TikTok: gồm mở đầu tóm tắt hấp dẫn khơi gợi sự tò mò (hook), 1-2 đoạn tóm tắt câu chuyện không spoil cái kết, lời kêu gọi Subscribe/Like tương tác, và 5-8 hashtags thịnh hành (#Storytelling, #Drama, v.v.) bằng ngôn ngữ kịch bản.\n4. thumbnail_prompt: Viết một MASTER PROMPT TẠO ẢNH BÌA THUMBNAIL YOUTUBE (hoàn toàn bằng Tiếng Anh) siêu kịch tính, cinematic 8k, photorealistic, góc nhìn đặc tả cảm xúc cao trào nhất của câu chuyện, ánh sáng tương phản chiaroscuro, kèm chữ text overlay giật gân để hút triệu view.\n5. Phân cảnh nào chứa khoảnh khắc CAO TRÀO NHẤT (dramatic nhất), hãy thêm chữ của video_title vào image_prompt (ví dụ: Text "[video_title]" overlaid on the image) để làm Thumbnail đồng bộ.\n\nQUY TẮC CỐT TRUYỆN (BẮT BUỘC):\n1. text_segment: Cắt kịch bản gốc thành từng phân đoạn thoại vừa vặn (mỗi phân cảnh gồm 1-2 câu, thời lượng đọc khoảng 6 - 12 giây).\n2. TUYỆT ĐỐI GIỮ NGUYÊN BẢN: Sử dụng 100% câu chữ nguyên gốc từ kịch bản của tác giả (giữ nguyên văn ngôn ngữ gốc: Tiếng Anh, Tiếng Việt, Tiếng Trung, v.v.). KHÔNG được tự ý dịch sang ngôn ngữ khác, KHÔNG tự ý tóm tắt sơ sài, KHÔNG thêm thắt nội dung ngoài, KHÔNG bỏ sót câu từ.\n3. TRÁNH LẶP LẠI & LAN MAN: Tập trung vào trọng tâm cảm xúc và cao trào của từng phân cảnh.\n\nQUY TẮC HÌNH ẢNH ĐIỆN ẢNH:\n1. visual_hint_vi: 1 câu tiếng Việt ngắn gọn tóm tắt cảnh để người dùng dễ chọn ảnh.\n2. image_prompt: Viết hoàn toàn bằng TIẾNG ANH, kết hợp Master Prompt phong cách mỹ thuật. Mô tả chi tiết: Chủ thể chính (nhân vật, biểu cảm sâu sắc, ánh mắt, trang phục), Bối cảnh và không khí (atmosphere, moody, dark mystery, dramatic lighting, volumetric haze), chất lượng cao cấp: photorealistic, cinematic 8k, Unreal Engine 5 aesthetic, master composition, 35mm film grain.\n3. ĐA DẠNG GÓC MÁY: Tuyệt đối KHÔNG lặp lại một góc máy liên tiếp. Luân chuyển giữa: wide establishing shot, medium close-up, dramatic low-angle, over-the-shoulder, atmospheric deep focus.\n4. video_motion_prompt: Viết hoàn toàn bằng TIẾNG ANH mô tả chuyển động video sống động cho các model Video AI (Google Veo 3, Runway Gen-3, Luma Dream Machine, Kling AI, Pika, Sora). Mô tả chuyển động camera (slow push-in, pan, tracking), hành động nhân vật, tương tác vật lý (gió thổi, mưa rơi, khói sương), 24fps film look.\n5. camera_motion: Chọn một trong [\'zoom_in\', \'zoom_out\', \'pan_left\', \'pan_right\', \'tilt_up\', \'tilt_down\', \'static\'].\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY (Chỉ trả về khối mã JSON, không thêm lời chào, không thêm giải thích ngoài code block):\n```json\n{{\n  "video_title": "Tiêu đề video cực thu hút ở đây",\n  "video_topic_vi": "Tóm tắt chủ đề kịch bản bằng Tiếng Việt ở đây",\n  "video_description": "Mô tả video hoàn chỉnh chuẩn SEO YouTube/TikTok kèm hashtags...",\n  "thumbnail_prompt": "Prompt tiếng Anh mô tả chi tiết hình ảnh Thumbnail YouTube triệu view kịch tính",\n  "scenes": [\n    {{\n      "index": 1,\n      "text_segment": "...",\n      "visual_hint_vi": "...",\n      "image_prompt": "...",\n      "video_motion_prompt": "...",\n      "camera_motion": "zoom_in"\n    }}\n  ]\n}}\n```\n\nMASTER PROMPT PHONG CÁCH:\n{style_part}\n\nKỊCH BẢN CẦN PHÂN TÍCH:\n{script_text}\n'''


class StoryWebAiDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


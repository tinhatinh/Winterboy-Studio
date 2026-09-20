# Source Generated with Decompyle++
# File: story_prompt_builder_dialog.pyc (Python 3.12)

'''Cửa sổ Modal Trình Tạo Prompt Kịch Bản & Tùy Biến Nhân Vật (Web Chrome Prompt Builder).

Cho phép người dùng:
1. Chọn mẫu kịch bản có sẵn (Regency Romance, Quý tộc báo thù, Án mạng Gothic, Hôn nhân sắp đặt, v.v.).
2. Tùy biến / Thay thế tên nhân vật, chủ đề, bối cảnh, tình huống xung đột theo ý muốn.
3. Tự động sinh Prompt chuẩn điện ảnh hoàn chỉnh kèm live preview.
4. Mở 1-click trên Web Chrome (ChatGPT, Gemini, Claude) để người dùng tự do sáng tạo trên Web.
5. Tự động lắng nghe Clipboard để nhận diện JSON kịch bản và nạp thẳng vào Studio Phân Cảnh.
'''
from __future__ import annotations
import json
import logging
import threading
import time
from typing import Any, Callable
import customtkinter as ctk
from tkinter import messagebox
from app.config.theme import ACCENT, ACCENT_HOVER, ACCENT_TEXT, BG_CARD, BG_DARK, BG_PANEL, BORDER, ON_ACCENT, SUCCESS, SURFACE_ALT, SURFACE_BTN, SURFACE_BTN_HOVER, TEXT, TEXT_DIM
from app.services.story_engine import CUSTOM_PRESET_NAME, estimate_story_duration, get_all_story_prompt_presets
from app.services.story_ai_creator_service import AI_CREATOR_LENGTH_MAP, _extract_clean_json_from_text
from app.ui.widgets.story_web_ai_dialog import URL_CHATGPT, URL_GEMINI, open_in_chrome
logger = logging.getLogger(__name__)
URL_CLAUDE = 'https://claude.ai'
MENU_STYLE = {
    'fg_color': '#1E293B',
    'button_color': '#334155',
    'button_hover_color': '#475569',
    'dropdown_fg_color': '#1E293B',
    'dropdown_hover_color': '#334155',
    'dropdown_text_color': '#F8FAFC',
    'text_color': '#F8FAFC' }
STORY_TEMPLATES: 'dict[str, dict[str, str]]' = {
    'regency_romance': {
        'name': '👑 Quý Tộc Anh & Tình Yêu Chậm Rãi (Regency Slow-burn)',
        'topic': 'Hôn nhân sắp đặt biến thành tình yêu sâu đậm vượt qua định kiến xã hội quý tộc Anh thế kỷ 19',
        'char_lead_1': 'Lady Elizabeth Thorne (Nữ thừa kế sắc sảo, kiêu hãnh nhưng mang gánh nặng gia tộc)',
        'char_lead_2': 'Julian Blackwood (Công tước xứ Blackwood - Lạnh lùng, quyền lực, che giấu vết thương quá khứ)',
        'char_antagonist': 'Lord Sterling (Bá tước tham lam, kẻ thao túng các khoản nợ của gia đình Thorne)',
        'setting': 'London và lâu đài Blackwood Manor mùa dạ tiệc vũ hội năm 1815, phòng dạ hội ánh nến và trang viên sương mù',
        'conflict': 'Một bản thỏa ước hôn nhân giả bị đe dọa vạch trần, buộc hai người phải đối mặt với tình cảm chân thật',
        'preset_style': 'Cinematic historical period drama, Regency aristocratic elegance, candlelit ballroom, 35mm photograph, 8k' },
    'aristocratic_revenge': {
        'name': '⚔️ Báo Thù Quý Tộc & Lật Đổ Gia Tộc (Aristocratic Revenge)',
        'topic': 'Một nữ thừa kế bị hãm hại tước đoạt tước vị quay trở lại với thân phận bí mật để trừng phạt từng kẻ phản bội',
        'char_lead_1': 'Victoria Vance (Từng là tiểu thư danh giá, nay trở về với biệt danh Nữ bá tước bóng đêm)',
        'char_lead_2': 'Lãnh chúa Alexander King (Chủ nhân ngân hàng danh giá nhất thủ đô, đồng minh bí mật)',
        'char_antagonist': 'Gia tộc Hầu tước Montagu (Những kẻ từng vu khống tội danh phản quốc cho cha của Victoria)',
        'setting': 'Trang viên Montagu Hall tráng lệ bên bờ biển bão tuyết và các câu lạc bộ thượng lưu ngầm',
        'conflict': 'Từng bí mật kinh hoàng trong bức thư tuyệt mệnh của người cha quá cố được phơi bày, kéo theo sự sụp đổ của một gia tộc',
        'preset_style': 'Dramatic aristocratic revenge, dark moody chiaroscuro, Victorian mansion interior, tension and mystery, 8k' },
    'gothic_mystery': {
        'name': '🔍 Án Mạng Trang Viên & Bí Ẩn Cổ Điển (Gothic Manor Mystery)',
        'topic': 'Cái chết bất thường của vị đại công tước giàu có và 7 đêm giông bão cô lập người thừa kế cùng những kẻ tình nghi',
        'char_lead_1': 'Thanh tra Arthur Pendelton (Điều tra viên sắc bén bị ám ảnh bởi một vụ án oan trong quá khứ)',
        'char_lead_2': 'Clara Ravenscroft (Cháu gái út kín tiếng, người duy nhất có mặt trong thư viện lúc nửa đêm)',
        'char_antagonist': 'Bóng ma trang viên / Kẻ giấu mặt trong gia tộc đang lần lượt thủ tiêu từng nhân chứng',
        'setting': 'Ravenscroft Manor trên đỉnh vách đá cheo leo, mưa bão cô lập hoàn toàn với thế giới bên ngoài',
        'conflict': 'Bản di chúc gốc bị xé làm đôi, và kẻ thủ ác để lại những manh mối kỳ lạ chỉ Clara mới có thể giải mã',
        'preset_style': 'Moody gothic mystery, rain lashed manor windows, deep shadows, 35mm film still, photorealistic 8k' },
    'royal_forbidden': {
        'name': '💔 Tình Yêu Cấm Đoán & Cung Đấu Vương Triều (Forbidden Royal Love)',
        'topic': 'Mối tình ngang trái giữa vị thái tử kế vị ngai vàng và cô gái mang thân phận hoàng tộc bị đánh tráo lúc sơ sinh',
        'char_lead_1': 'Evelyn (Cô gái thảo dược tài năng che giấu vết bớt hoàng gia hình chim ưng trên vai)',
        'char_lead_2': 'Thái tử Richard (Vị tướng lĩnh trẻ tuổi mang trên mình trọng trách giữ gìn vương triều đang lung lay)',
        'char_antagonist': 'Thái hậu Eleanor và Đại tư tế (Những kẻ sẵn sàng đổ máu để bảo vệ quyền lực tuyệt đối)',
        'setting': 'Đại hoàng cung đá cẩm thạch trắng và các dãy hành lang ngầm đầy cạm bẫy',
        'conflict': 'Chiếc mề đay cổ được mở ra trong đêm lễ đăng quang, buộc Richard phải chọn lựa giữa vương miện và tình yêu',
        'preset_style': 'Epic oriental royal palace aesthetic, mystical atmosphere, rich silk robes, masterpiece cinematic lighting, 8k' },
    'modern_billionaire': {
        'name': '💎 Hào Môn Thế Gia & Đấu Trí Thượng Lưu (Billionaire Romance)',
        'topic': 'Một nữ luật sư độc lập đối đầu với người thừa kế tập đoàn tài phiệt trước khi nhận ra họ có chung một kẻ thù',
        'char_lead_1': 'Elena Ross (Nữ luật sư tài ba, mạnh mẽ, kiên quyết vạch trần đường dây tài chính mờ ám)',
        'char_lead_2': 'Marcus Vance (Tổng giám đốc tập đoàn, người đang âm thầm thanh lọc hội đồng quản trị biến chất)',
        'char_antagonist': 'Phó chủ tịch Gavin Cole (Kẻ giật dây buôn bán thông tin nội gián)',
        'setting': 'Các tòa nhà chọc trời New York và biệt thự nghỉ dưỡng ven biển Hamptons',
        'conflict': 'Một cuộc hôn nhân hợp đồng bất đắc dĩ biến thành màn hợp tác sinh tử lật đổ âm mưu thôn tính tập đoàn',
        'preset_style': 'Modern luxury cinematic film shot, high-end architectural aesthetics, sharp tailored suits, 35mm film, 8k' },
    'custom': {
        'name': '✍️ Tự Do Sáng Tạo (Custom Blueprint)',
        'topic': '',
        'char_lead_1': '',
        'char_lead_2': '',
        'char_antagonist': '',
        'setting': '',
        'conflict': '',
        'preset_style': 'Cinematic storytelling shot, photorealistic 8k, dramatic lighting, moody atmospheric depth' } }

class StoryPromptBuilderDialog(ctk.CTkToplevel):
    pass
# WARNING: Decompyle incomplete


'''Dịch vụ quản lý Hồ Sơ & Preset Kênh Đối Thủ (Competitor Channel Profiles & Presets).

Cho phép người dùng:
1. Quản lý tập trung toàn bộ cấu hình mẫu cho từng Kênh Đối Thủ (Style ảnh, Prompt nhân vật, Tone giọng, Ngôn ngữ, Nhạc nền, Tỉ lệ).
2. Đồng bộ hóa phong cách đồng nhất (Content Consistency) cho mọi video làm theo kênh đối thủ đó.
3. Gắn Tag tên kênh đối thủ vào từng dự án để dễ dàng quản lý, lọc và tìm kiếm trong danh sách dự án.
'''
from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[2]
PRESETS_DIR = ROOT_DIR / 'presets'
COMPETITORS_FILE = PRESETS_DIR / 'story_competitors.json'

# Ba kênh mẫu dựng sẵn, lấy nguyên văn từ bản đã phát hành (không tự chế nội dung).
DEFAULT_COMPETITOR_CHANNELS = {
    'Lady Jaki FitzHerbert': {
        'id': 'lady_jaki_fitzherbert',
        'name': 'Lady Jaki FitzHerbert',
        'handle': '@LadyJakiFitzHerbert',
        'url': 'https://www.youtube.com/@LadyJakiFitzHerbert',
        'genre_topic': 'Quý Tộc Anh & Tình Cảm Chậm Rãi (Regency Romance & British Aristocracy)',
        'target_audience': 'Người lớn tuổi / Thị trường Hoa Kỳ & Anh (Tier 1 High CPM $15-$35)',
        'language': 'Tiếng Anh (English)',
        'aspect_ratio': '16:9',
        'voice_provider': 'Edge TTS',
        'voice_id': 'en-GB-SoniaNeural',
        'voice_speed': 0.95,
        'master_prompt_preset': 'regency_romance',
        'master_prompt_custom': 'Cinematic 19th-century English Regency period drama, classic Victorian aristocratic elegance, warm candlelight, grand English manor ballroom, soft volumetric lighting, nostalgic film grain, masterpiece digital oil painting, 35mm photograph, 8k resolution',
        'character_lead_1': 'Young impoverished noblewoman with proud posture and auburn hair',
        'character_lead_2': 'Julian Blackwood - Aloof, wealthy British Duke with dark coat and piercing gaze',
        'character_antagonist': 'Scheming aristocratic relative seeking to seize the family estate',
        'setting_location': 'English countryside estate, misty rose gardens, candlelit London ballrooms',
        'bgm_style': 'Classical Regency Strings / Melancholic Cello & Violin (Bridgerton style)',
        'notes': 'Kênh chuyên truyện quý tộc Anh, công tước, người hầu gái bí mật. Tỉ lệ giữ chân cao ở khán giả trên 50 tuổi tại Mỹ, Anh, Canada.',
        'created_at': 1789452000,
        'updated_at': 1789452000,
    },
    'Bedtime Wisdom & Life Stories': {
        'id': 'bedtime_wisdom_seniors',
        'name': 'Bedtime Wisdom Stories',
        'handle': '@BedtimeWisdomTales',
        'url': 'https://www.youtube.com/@BedtimeWisdomTales',
        'genre_topic': 'Chiêm Nghiệm Cuộc Sống & Chữa Lành (Inspirational Wisdom for Seniors)',
        'target_audience': 'Người già & Người trung niên (Thị trường Mỹ, Úc, Canada)',
        'language': 'Tiếng Anh (English)',
        'aspect_ratio': '16:9',
        'voice_provider': 'Edge TTS',
        'voice_id': 'en-US-ChristopherNeural',
        'voice_speed': 0.9,
        'master_prompt_preset': 'drama_life',
        'master_prompt_custom': 'Warm golden hour lighting, cozy nostalgic cabin in autumn forest, gentle emotional atmosphere, hyper-realistic cinematic portrait, peaceful mood, 8k photography',
        'character_lead_1': 'Wise elderly grandfather with gentle smile and silver hair',
        'character_lead_2': 'Kind compassionate traveler seeking life guidance',
        'character_antagonist': 'None / Personal hardships and life challenges',
        'setting_location': 'Cozy fireplace living room, quiet autumn countryside, serene lake porch',
        'bgm_style': 'Soft Acoustic Guitar & Warm Piano (Calming Sleep Tone)',
        'notes': 'Video dài 1-2 tiếng dành cho người già nghe lúc ngủ hoặc thư giãn buổi tối, RPM cực kỳ cao.',
        'created_at': 1789452000,
        'updated_at': 1789452000,
    },
    'Gothic Mystery & Victorian Crime': {
        'id': 'gothic_victorian_crime',
        'name': 'Victorian Gothic Chronicles',
        'handle': '@GothicVictorianTales',
        'url': 'https://www.youtube.com/@GothicVictorianTales',
        'genre_topic': 'Bí Ẩn Quý Tộc & Án Mạng Lâu Đài (Victorian Mystery / Gothic Suspense)',
        'target_audience': 'Khán giả yêu thích Sherlock Holmes / Agatha Christie (Mỹ, Anh)',
        'language': 'Tiếng Anh (English)',
        'aspect_ratio': '16:9',
        'voice_provider': 'Edge TTS',
        'voice_id': 'en-GB-RyanNeural',
        'voice_speed': 0.95,
        'master_prompt_preset': 'gothic_mystery',
        'master_prompt_custom': 'Cinematic dramatic realism, deep mystery, foggy Victorian London street lamps, chiaroscuro lighting, dramatic shadows, vintage textured canvas, mysterious atmospheric mood, 8k',
        'character_lead_1': 'Daring consulting detective in dark tweed overcoat',
        'character_lead_2': 'Mysterious veiled lady holding a sealed wax letter',
        'character_antagonist': 'Shadowy figure lurking near the Thames docks',
        'setting_location': 'Cobblestone alleys of 1888 London, grand ancestral libraries, stormy sea cliffs',
        'bgm_style': 'Dark Cinematic Orchestral / Suspense Strings',
        'notes': 'Chủ đề trinh thám lịch sử, cốt truyện giật gân, giữ chân người xem xuyên suốt 60-90 phút.',
        'created_at': 1789452000,
        'updated_at': 1789452000,
    },
}


def load_competitor_channels() -> dict[str, dict[str, Any]]:
    '''Đọc danh sách Hồ Sơ Kênh Đối Thủ, tự ghi lại bản mặc định nếu chưa có file.'''
    PRESETS_DIR.mkdir(parents = True, exist_ok = True)
    if not COMPETITORS_FILE.is_file():
        save_competitor_channels(DEFAULT_COMPETITOR_CHANNELS)
        return dict(DEFAULT_COMPETITOR_CHANNELS)
    try:
        data = json.loads(COMPETITORS_FILE.read_text(encoding = 'utf-8'))
        if isinstance(data, dict) and data:
            for def_key, def_val in DEFAULT_COMPETITOR_CHANNELS.items():
                # chỉ bù khi kênh mặc định biến mất hẳn và không ai khác giữ handle đó
                if def_key not in data and not any(v.get('handle') == def_val.get('handle') for v in data.values()):
                    data[def_key] = def_val
            return data
        return dict(DEFAULT_COMPETITOR_CHANNELS)
    except Exception as exc:
        logger.warning('Lỗi đọc story_competitors.json: %s -> Dùng mặc định', exc)
        return dict(DEFAULT_COMPETITOR_CHANNELS)


def save_competitor_channels(channels: dict[str, dict[str, Any]]) -> None:
    PRESETS_DIR.mkdir(parents = True, exist_ok = True)
    COMPETITORS_FILE.write_text(json.dumps(channels, ensure_ascii = False, indent = 2, default = str), 
       encoding = 'utf-8')


def get_competitor_channel(channel_name: str) -> dict[str, Any] | None:
    '''Tra theo tên chính xác, rồi mới thử khớp không phân biệt hoa thường/handle.'''
    all_ch = load_competitor_channels()
    if channel_name in all_ch:
        return all_ch[channel_name]
    norm = channel_name.strip().lower()
    for k, v in all_ch.items():
        if k.lower() == norm or v.get('handle', '').lower() == norm or v.get('name', '').lower() == norm:
            return v
    return None


def save_or_update_competitor_channel(channel_data: dict[str, Any]) -> str:
    '''Lưu mới hoặc ghi đè hồ sơ; giữ created_at cũ, luôn cập nhật updated_at.'''
    name = (channel_data.get('name') or channel_data.get('handle') or 'Kênh Đối Thủ Mới').strip()
    all_ch = load_competitor_channels()
    existing = all_ch.get(name, { })
    now = int(time.time())
    channel_data['name'] = name
    channel_data['created_at'] = existing.get('created_at', now)
    channel_data['updated_at'] = now
    all_ch[name] = channel_data
    save_competitor_channels(all_ch)
    return name


def delete_competitor_channel(channel_name: str) -> bool:
    all_ch = load_competitor_channels()
    if channel_name in all_ch:
        del all_ch[channel_name]
        save_competitor_channels(all_ch)
        return True
    return False


def get_all_competitor_names() -> list[str]:
    return list(load_competitor_channels().keys())

'''
Preset Manager — Quản lý mẫu cấu hình 1-Click cho Winterboy studio.

Cho phép lưu toàn bộ thiết lập hiện tại thành preset đặt tên riêng
(ví dụ: "TikTok Shorts 9:16", "Review Phim Voice Hoài My", v.v.)
và nạp lại nhanh chỉ bằng một cú nhấp chuột.
'''
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
PRESETS_DIR = ROOT / 'presets'

# Tên preset "trống" — nạp vào là trở về đúng cấu hình gốc của ứng dụng.
DEFAULT_PRESET_NAME = '-- Không dùng (Mặc định) --'

DEFAULT_PRESET: dict[str, Any] = {
    'description': 'Cấu hình chuẩn ban đầu: Tỉ lệ gốc, không zoom/lật, âm lượng chuẩn, không phụ đề/hiệu ứng.',
    'module1': {
        'ratio': 'Giữ nguyên',
        'zoom': '100% (Mặc định)',
        'speed': '100% (Chuẩn)',
        'mute': False,
        'keep_original_audio': True,
        'vocal_filter': False,
        'flip_h': False,
        'original_volume': 20.0,
        'tts_volume': 140.0,
        'adaptive_ducking': True,
        'normalize_audio': True,
        'demucs_enable': False,
    },
    'module2': {
        'enable_subtitle': False,
        'sub_karaoke': False,
        'enable_tts': False,
        'srt_mode': 'translated',
        'ai_engine': 'Gemini',
        'sub_font': 'Arial',
        'sub_size': 36,
        'sub_color': '#FFFFFF',
        'sub_letter_spacing': '0',
        'sub_stroke_width': '0',
        'sub_text_effect': 'Không có (Khuyên dùng)',
        'sub_bg_style': 'Không có (Khuyên dùng)',
        'sub_bg_enable': False,
        'translation_reflow': False,
        'natural_voice_sync': False,
        'soft_timing_enabled': False,
    },
    'module3': {
        'blur_enable': False,
        'blur_strength': 30.0,
        'blur_feather': 15.0,
        'blur_opacity': 100.0,
    },
    'module4': {
        'bgm_volume': 30.0,
        'bgm_delay': '0',
        'bgm_loop': True,
    },
    'module5': {
        'logo_enable': False,
        'static_text_enable': False,
        'watermark_enable': False,
    },
    'module6': {
        'trim_enable': False,
        'trim_head': '0',
        'trim_tail': '0',
    },
    'module7': {
        'bypass_subpixel': False,
        'bypass_noise': False,
        'bypass_colorspace': False,
        'bypass_tempo': False,
        'bypass_gop': False,
        'bypass_zoompan': False,
        'bypass_ultimate': False,
        'rotate': 0.0,
        'brightness': 0.0,
        'contrast': 1.0,
        'saturation': 1.0,
    },
}

# Mẫu dựng sẵn, không sửa từ giao diện. Khóa đầu tiên trỏ thẳng tới
# DEFAULT_PRESET (cùng một object) nên nạp 'mặc định' luôn là bản gốc.
BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    DEFAULT_PRESET_NAME: DEFAULT_PRESET,
    'TikTok Shorts Giật Gân (9:16)': {
        'description': 'Tỉ lệ dọc 9:16, zoom 110%, sub to nổi bật, lách bản quyền nhẹ.',
        'module1': {
            'ratio': '9:16',
            'zoom': '110%',
            'speed': '100% (Chuẩn)',
            'adaptive_ducking': True,
            'normalize_audio': True,
            'keep_original_audio': True,
            'original_volume': 35.0,
            'tts_volume': 100.0,
        },
        'module2': {
            'enable_subtitle': True,
            'sub_font': 'Arial',
            'sub_size': 52,
            'sub_bg_style': 'Viền đậm',
            'sub_bg_enable': False,
        },
        'module7': {
            'bypass_subpixel': True,
            'bypass_noise': True,
            'bypass_colorspace': True,
        },
    },
    'Review Phim / Kể Chuyện (16:9)': {
        'description': 'Tỉ lệ 16:9 ngang chuẩn, phụ đề 2 dòng dưới đáy, nhạc nền tự hạ khi đọc.',
        'module1': {
            'ratio': '16:9',
            'zoom': '100% (Mặc định)',
            'speed': '100% (Chuẩn)',
            'adaptive_ducking': True,
            'normalize_audio': True,
            'keep_original_audio': True,
            'original_volume': 20.0,
            'tts_volume': 100.0,
        },
        'module2': {
            'enable_subtitle': True,
            'sub_font': 'Segoe UI',
            'sub_size': 42,
            'sub_bg_style': 'Không có (Khuyên dùng)',
            'sub_bg_enable': False,
        },
    },
    'Tin Tức / Podcast Chuẩn': {
        'description': 'Khung chuẩn, phụ đề có nền chữ nhật mờ dễ nhìn, tối ưu lọc giọng nói.',
        'module1': {
            'ratio': 'keep',
            'zoom': '100% (Mặc định)',
            'speed': '100% (Chuẩn)',
            'vocal_filter': True,
            'adaptive_ducking': True,
            'normalize_audio': True,
            'tts_volume': 100.0,
        },
        'module2': {
            'enable_subtitle': True,
            'sub_font': 'Arial',
            'sub_size': 38,
            'sub_bg_style': 'Hộp chữ nhật mờ',
            'sub_bg_enable': True,
        },
    },
    'Lách Bản Quyền 100%': {
        'description': 'Bật đầy đủ 6 lớp hiệu ứng chống quét bản quyền tự động (lệch màu, dịch khung, nhiễu...).',
        'module1': {
            'flip_h': True,
            'zoom': '105%',
            'speed': '100% (Chuẩn)',
        },
        'module7': {
            'bypass_ultimate': True,
            'bypass_subpixel': True,
            'bypass_noise': True,
            'bypass_colorspace': True,
            'bypass_zoompan': True,
            'bypass_tempo': True,
            'bypass_gop': True,
        },
    },
}


def get_presets_dir() -> Path:
    PRESETS_DIR.mkdir(parents = True, exist_ok = True)
    return PRESETS_DIR


def list_presets() -> list[str]:
    '''Danh sách tên tất cả preset có sẵn (bao gồm built-in và preset người dùng lưu).'''
    names = list(BUILTIN_PRESETS.keys())
    p_dir = get_presets_dir()
    for file in sorted(p_dir.glob('*.json')):
        name = file.stem
        if name not in names:
            names.append(name)
    return names


def load_preset(name: str) -> dict[str, Any] | None:
    '''Đọc dữ liệu cấu hình của preset theo tên.'''
    s_name = str(name).strip()
    if s_name in (DEFAULT_PRESET_NAME, 'Không có', 'Mặc định', '-- Không dùng --', 'Default'):
        return json.loads(json.dumps(DEFAULT_PRESET))
    elif s_name in BUILTIN_PRESETS:
        return json.loads(json.dumps(BUILTIN_PRESETS[s_name]))
    target = get_presets_dir() / f'''{s_name}.json'''
    if target.is_file():
        try:
            return json.loads(target.read_text(encoding = 'utf-8'))
        except Exception as exc:
            logger.error('Không đọc được file preset %s: %s', target, exc)
    return None


def save_user_preset(name: str, state_dict: dict[str, Any]) -> Path:
    '''Lưu snapshot cấu hình hiện tại thành preset người dùng với tên tùy ý.'''
    clean_name = ''.join(c for c in str(name).strip() if c not in '\\/:*?"<>|')
    if not clean_name:
        clean_name = f'''Preset_{int(datetime.now().timestamp())}'''
    target = get_presets_dir() / f'''{clean_name}.json'''
    payload = dict(state_dict)
    payload['_meta'] = {
        'preset_name': clean_name,
        'saved_at': datetime.now(timezone.utc).isoformat(),
        'is_user_preset': True }
    target.write_text(json.dumps(payload, ensure_ascii = False, indent = 2), encoding = 'utf-8')
    logger.info('Đã lưu user preset: %s', target)
    return target


def delete_user_preset(name: str) -> bool:
    '''Xóa preset người dùng đã lưu (không xóa preset mặc định).'''
    if name in BUILTIN_PRESETS:
        return False
    target = get_presets_dir() / f'''{name}.json'''
    if target.is_file():
        try:
            target.unlink()
            return True
        except Exception as exc:
            logger.error('Không xóa được preset %s: %s', target, exc)
    return False

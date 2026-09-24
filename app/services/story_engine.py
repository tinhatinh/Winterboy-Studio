'''Dịch vụ bóc tách kịch bản kể chuyện (AI Storytelling Engine) cho Winterboy studio.

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
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from app.services.gemini_translate import GEMINI_MODELS, get_gemini_api_key, get_translation_api_keys, normalize_gemini_model

logger = logging.getLogger(__name__)

CUSTOM_PRESET_NAME = 'Tùy Chỉnh (Tự Nhập Master Prompt)'

MASTER_PROMPT_PRESETS: dict[str, dict[str, str]] = {
    'drama_life': {
        'name': 'Đời Sống / Chân Thực & Cảm Động',
        'prompt': 'Cinematic authentic storytelling shot, photorealistic, true-to-life documentary style, warm moody natural lighting, shallow depth of field, 35mm film photography, highly detailed, expressive human emotions, 8k'
    },
    'true_crime_doc': {
        'name': 'Tài Liệu Điều Tra / Vụ Án Bí Ẩn',
        'prompt': 'Cinematic true-crime documentary, hyperrealistic 35mm photograph, dramatic chiaroscuro archival lighting, dramatic shadows, atmospheric moody forensic realism, gritty authentic textures, 8k resolution'
    },
    'history_real': {
        'name': 'Lịch Sử / Sự Kiện Chân Thực',
        'prompt': 'Photorealistic historical cinematic film still, accurate period details, authentic atmosphere, natural dramatic lighting, 35mm anamorphic lens, documentary realism, 8k'
    },
    'philosophical': {
        'name': 'Triết Lý / Sâu Lắng & Hoài Niệm',
        'prompt': 'Minimalist cinematic shot, poetic solitude, golden hour soft light, atmospheric perspective, vintage color grading, nostalgic film grain, contemplation mood, 8k'
    },
    'gothic_mystery': {
        'name': 'Bí Ẩn / Không Khí Kịch Tính',
        'prompt': 'Cinematic dramatic realism, deep mystery, dark atmospheric fog, chiaroscuro lighting, dramatic shadows, vintage textured canvas, mysterious mood, 8k resolution'
    },
    'myth_fantasy': {
        'name': 'Cung Đấu / Cổ Tích Huyền Bí',
        'prompt': 'Epic oriental fantasy art, ancient royal palace aesthetic, mystical ethereal glow, intricate silk robes, dramatic cinematic lighting, masterpiece digital painting, 8k'
    },
    'custom': {
        'name': CUSTOM_PRESET_NAME,
        'prompt': ''
    }
}

def estimate_story_duration(text_or_chars: str | int, wpm: float = 140.0) -> tuple[float, str]:
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
            total_sec = max(0.0, (words / max(1.0, wpm)) * 60.0)
        else:
            total_sec = max(0.0, chars / 14.0)
    else:
        chars = int(text_or_chars or 0)
        total_sec = max(0.0, chars / 14.0)

    total_sec = round(total_sec)
    if total_sec < 60:
        display_str = f'{total_sec} giây'
    elif total_sec < 3600:
        mins = total_sec // 60
        secs = total_sec % 60
        if secs >= 45:
            mins += 1
            display_str = f'{mins} phút'
        elif secs >= 15:
            display_str = f'{mins} phút {secs:02d}s'
        else:
            display_str = f'{mins} phút'
    else:
        hrs = total_sec // 3600
        rem_sec = total_sec % 3600
        mins = round(rem_sec / 60)
        if mins >= 60:
            hrs += 1
            mins = 0
        if mins > 0:
            display_str = f'{hrs}h{mins:02d}p'
        else:
            display_str = f'{hrs} giờ'
    return float(total_sec), display_str

def get_user_story_presets_file() -> Path:
    presets_dir = Path(__file__).resolve().parents[2] / 'presets'
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir / 'story_prompts.json'

def load_user_story_presets() -> dict[str, str]:
    '''Trả về dict: {preset_name: prompt_text}'''
    f = get_user_story_presets_file()
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception as exc:
        logger.warning('Lỗi đọc story_prompts.json: %s', exc)
    return {}

def save_user_story_preset(name: str, prompt: str) -> None:
    '''Lưu preset mới của người dùng vào file presets/story_prompts.json.'''
    name = name.strip()
    if not name or name == CUSTOM_PRESET_NAME:
        return
    presets = load_user_story_presets()
    presets[name] = prompt.strip()
    f = get_user_story_presets_file()
    f.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding='utf-8')

def delete_user_story_preset(name: str) -> bool:
    '''Xóa một preset người dùng khỏi presets/story_prompts.json.'''
    name = name.strip()
    presets = load_user_story_presets()
    if name in presets:
        del presets[name]
        f = get_user_story_presets_file()
        f.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding='utf-8')
        return True
    return False

def get_all_story_prompt_presets() -> dict[str, str]:
    '''Trả về danh sách đầy đủ gồm Tùy Chỉnh, các preset mẫu điện ảnh và preset người dùng đã lưu: {display_name: prompt_text}.'''
    presets = {CUSTOM_PRESET_NAME: ''}
    for k, v in MASTER_PROMPT_PRESETS.items():
        if k != 'custom' and isinstance(v, dict) and 'name' in v and 'prompt' in v:
            presets[v['name']] = v['prompt']
    presets.update(load_user_story_presets())
    return presets

CAMERA_MOTIONS = [
    'hook_crash_zoom', 'hook_shake', 'hook_whip_pan',
    'zoom_in', 'zoom_out', 'pan_left', 'pan_right',
    'tilt_up', 'tilt_down', 'static']

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
    'static': 'Cố định (Static)'
}

@dataclass
class StoryScene:
    scene_id: str
    index: int
    text_segment: str
    visual_hint_vi: str = ''
    image_prompt: str = ''
    camera_motion: str = 'zoom_in'
    transition: str = 'fade'
    start_time_s: float = 0.0
    end_time_s: float = 0.0
    duration_s: float = 0.0
    audio_path: str = ''
    voice_provider: str = ''
    voice_id: str = ''
    voice_speed: float = 1.0
    speaker: str = 'narrator'
    sfx_path: str = ''
    sfx_volume: float = 0.5
    sfx_offset_s: float = 0.0
    image_path: str = ''
    image_source: str = ''
    media_type: str = 'image'
    video_path: str = ''
    video_source: str = ''
    video_motion_prompt: str = ''
    video_start_s: float = 0.0
    video_audio_muted: bool = False
    status: str = 'pending'

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, Path):
                d[k] = str(v)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryScene:
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

@dataclass
class StoryProject:
    project_id: str
    project_dir: str
    title: str = 'Chuyện Chưa Kể'
    topic_vi: str = ''
    description: str = ''
    master_prompt_preset: str = 'drama_life'
    master_prompt_custom: str = ''
    thumbnail_prompt: str = ''
    aspect_ratio: str = '16:9'
    voice_provider: str = 'Edge TTS'
    voice_id: str = 'vi-VN-HoaiMyNeural'
    voice_speed: float = 1.0
    audio_voice_provider: str = ''
    audio_voice_id: str = ''
    audio_voice_speed: float = 1.0
    voice_volume: float = 1.0
    video_volume: float = 1.0
    bgm_path: str = ''
    bgm_volume: float = 0.15
    bgm_loop: bool = True
    bgm_fade_in: float = 0.5
    bgm_fade_out: float = 0.5
    bgm_clips: list[dict[str, Any]] = field(default_factory=list)
    enable_subtitle: bool = True
    language: str = 'Tự động (Tiếng Anh)'
    texture_enabled: bool = False
    texture_path: str = ''
    texture_paths: list[str] = field(default_factory=list)
    texture_distribution: str = 'cycle_15s'
    texture_blend_mode: str = 'screen'
    texture_opacity: float = 0.35
    texture_loop: bool = True
    visual_bible: dict[str, Any] = field(default_factory=dict)
    sub_options: dict[str, Any] = field(default_factory=dict)
    hook_master_enabled: bool = False
    hook_title: str = ''
    hook_motion: str = 'hook_crash_zoom'
    hook_sfx: str = 'cinematic_impact.wav'
    channel_tag: str = ''
    channel_url: str = ''
    character_voice_map: dict[str, dict[str, Any]] = field(default_factory=dict)
    scenes: list[StoryScene] = field(default_factory=list)

    def get_unique_speakers(self) -> list[str]:
        '''Trả về danh sách tất cả các nhân vật xuất hiện trong các phân cảnh (luôn có narrator).'''
        speakers = ['narrator']
        for sc in self.scenes:
            sp = (getattr(sc, 'speaker', '') or 'narrator').strip()
            if sp and sp not in speakers:
                speakers.append(sp)
        if isinstance(self.character_voice_map, dict):
            for sp in self.character_voice_map.keys():
                sp_clean = str(sp).strip()
                if sp_clean and sp_clean not in speakers:
                    speakers.append(sp_clean)
        return speakers

    def apply_character_voice_map(self) -> int:
        '''Áp dụng cấu hình giọng đọc từ character_voice_map cho tất cả các phân cảnh tương ứng.'''
        if not isinstance(self.character_voice_map, dict) or not self.character_voice_map:
            return 0
        updated = 0
        for sc in self.scenes:
            sp = (getattr(sc, 'speaker', '') or 'narrator').strip()
            if sp in self.character_voice_map:
                cfg = self.character_voice_map[sp]
                if isinstance(cfg, dict):
                    if cfg.get('provider'):
                        sc.voice_provider = str(cfg['provider'])
                    if cfg.get('voice_id'):
                        sc.voice_id = str(cfg['voice_id'])
                    if cfg.get('voice_speed') is not None:
                        sc.voice_speed = float(cfg['voice_speed'])
                    updated += 1
        return updated

    def apply_competitor_preset(self, preset_data: dict[str, Any]) -> None:
        '''Đồng bộ hóa toàn bộ phong cách, giọng đọc, tỉ lệ và prompt của kênh đối thủ vào dự án.'''
        self.channel_tag = str(preset_data.get('name') or preset_data.get('handle') or '').strip()
        self.channel_url = str(preset_data.get('url') or '').strip()
        if preset_data.get('aspect_ratio'):
            self.aspect_ratio = preset_data['aspect_ratio']
        if preset_data.get('voice_provider'):
            self.voice_provider = preset_data['voice_provider']
        if preset_data.get('voice_id'):
            self.voice_id = preset_data['voice_id']
        if preset_data.get('voice_speed'):
            self.voice_speed = float(preset_data['voice_speed'])
        if preset_data.get('language'):
            self.language = preset_data['language']
        if preset_data.get('master_prompt_preset'):
            self.master_prompt_preset = preset_data['master_prompt_preset']
        if preset_data.get('master_prompt_custom'):
            self.master_prompt_custom = preset_data['master_prompt_custom']
        if preset_data.get('genre_topic') and not self.topic_vi:
            self.topic_vi = preset_data['genre_topic']

        if not isinstance(self.visual_bible, dict):
            self.visual_bible = {}
        if self.master_prompt_custom or self.master_prompt_preset:
            self.visual_bible['art_style'] = self.master_prompt_custom or self.master_prompt_preset
        if preset_data.get('era_setting'):
            self.visual_bible['era_setting'] = preset_data['era_setting']
        elif preset_data.get('setting_location') and not self.visual_bible.get('era_setting'):
            self.visual_bible['era_setting'] = preset_data['setting_location']
        if isinstance(preset_data.get('characters'), list) and preset_data['characters']:
            self.visual_bible['characters'] = [dict(c) for c in preset_data['characters']]
        else:
            chars_list = self.visual_bible.get('characters') or []
            if not chars_list:
                new_chars = []
                c1 = str(preset_data.get('character_lead_1') or '').strip()
                if c1:
                    new_chars.append({
                        'name': 'Main Character 1',
                        'gender': 'female' if any(w in c1.lower() for w in ('woman', 'girl', 'lady', 'female', 'nữ')) else 'male',
                        'age': '30s',
                        'features': c1,
                        'signature_attire': c1
                    })
                c2 = str(preset_data.get('character_lead_2') or '').strip()
                if c2:
                    new_chars.append({
                        'name': 'Companion / Lead 2',
                        'gender': 'female' if any(w in c2.lower() for w in ('woman', 'girl', 'lady', 'female', 'nữ')) else 'male',
                        'age': '30s',
                        'features': c2,
                        'signature_attire': c2
                    })
                if new_chars:
                    self.visual_bible['characters'] = new_chars

    def apply_single_image_to_all(self, image_path: str | Path) -> int:
        '''Áp dụng 1 ảnh duy nhất cho tất cả các phân cảnh trong dự án.'''
        from app.services.story_image_service import apply_single_image_to_all_scenes
        return apply_single_image_to_all_scenes(self.scenes, image_path, project_dir=self.project_dir)

    def apply_single_video_to_all(self, video_path: str | Path) -> int:
        '''Áp dụng 1 video duy nhất cho tất cả các phân cảnh và tự động khớp theo timestamp SRT.'''
        from app.services.story_video_service import apply_single_video_to_all_scenes
        return apply_single_video_to_all_scenes(self.scenes, video_path, project_dir=self.project_dir)

    def set_all_video_audio_muted(self, muted: bool = True) -> int:
        '''Tắt hoặc bật âm thanh gốc của video cho toàn bộ các phân cảnh.'''
        cnt = 0
        for sc in self.scenes:
            sc.video_audio_muted = bool(muted)
            cnt += 1
        return cnt

    def get_bgm_clips(self) -> list[dict[str, Any]]:
        '''Trả về danh sách BGM clips chuẩn hóa. Nếu bgm_clips rỗng nhưng bgm_path có giá trị, chuyển đổi sang clip.'''
        if self.bgm_clips:
            return [dict(c) for c in self.bgm_clips]
        if self.bgm_path and Path(self.bgm_path).is_file():
            vol = self.bgm_volume * 100.0 if self.bgm_volume <= 1.0 else self.bgm_volume
            return [{
                'path': str(self.bgm_path),
                'timeline_start': 0.0,
                'timeline_end': 0.0,
                'source_start': 0.0,
                'volume': vol,
                'loop': self.bgm_loop,
                'fade_in': self.bgm_fade_in,
                'fade_out': self.bgm_fade_out
            }]
        return []

    def set_bgm_clips(self, clips: list[dict[str, Any]]) -> None:
        self.bgm_clips = [dict(c) for c in clips]
        if clips:
            self.bgm_path = str(clips[0].get('path', ''))
            vol = float(clips[0].get('volume', 15.0))
            self.bgm_volume = vol / 100.0 if vol > 1.0 else vol
            self.bgm_loop = bool(clips[0].get('loop', True))
            self.bgm_fade_in = float(clips[0].get('fade_in', 0.5))
            self.bgm_fade_out = float(clips[0].get('fade_out', 0.5))
            return
        self.bgm_path = ''

    def get_total_duration(self) -> float:
        '''Tổng thời lượng video ước tính từ các phân cảnh (giây).'''
        if not self.scenes:
            return 0.0
        last_end = max((float(s.end_time_s or 0.0) for s in self.scenes), default=0.0)
        if last_end > 0.0:
            return last_end
        return sum(float(s.duration_s or 4.0) for s in self.scenes)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['project_dir'] = str(self.project_dir)
        d['scenes'] = [s.to_dict() for s in self.scenes]
        vol = getattr(self, 'voice_volume', None) or getattr(self, 'video_volume', 1.0)
        d['voice_volume'] = float(vol)
        d['video_volume'] = float(vol)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryProject:
        scenes_data = data.pop('scenes', [])
        scenes = [StoryScene.from_dict(s) for s in scenes_data]
        if 'voice_volume' not in data and 'video_volume' in data:
            data['voice_volume'] = float(data['video_volume'])
        elif 'voice_volume' in data:
            data['video_volume'] = float(data['voice_volume'])
        valid_keys = {f for f in cls.__dataclass_fields__ if f != 'scenes'}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if not filtered.get('texture_paths') and filtered.get('texture_path'):
            filtered['texture_paths'] = [str(filtered['texture_path'])]
        elif filtered.get('texture_paths') and not filtered.get('texture_path'):
            filtered['texture_path'] = str(filtered['texture_paths'][0])
        return cls(scenes=scenes, **filtered)

    def save(self, filepath: str | Path | None = None) -> Path:
        if filepath is None:
            p = Path(self.project_dir) / 'story_project.json'
        else:
            p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        return p

    def invalidate_preview_cache(self) -> None:
        '''Xóa toàn bộ file cache xem trước (preview_draft.mp4, preview_draft.sig.json, placeholder clips)
        để buộc tạo mới hoặc nạp lại trạng thái mới nhất của dự án khi media hoặc kịch bản thay đổi.'''
        try:
            p_dir = Path(self.project_dir)
            cache_dir = p_dir / '.cache'
            if cache_dir.is_dir():
                for f in cache_dir.glob('preview_draft*'):
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        continue
                for f in cache_dir.glob('ph_clip_*'):
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        continue
            old_draft = p_dir / 'preview_draft.mp4'
            if old_draft.is_file():
                try:
                    old_draft.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception as err:
            logger.debug('Lỗi khi dọn dẹp preview cache: %s', err)

    @classmethod
    def load(cls, filepath: str | Path) -> StoryProject:
        p = Path(filepath).resolve()
        if p.is_dir():
            candidates = [
                p / 'story_project.json',
                p / 'story.json'
            ]
            found_p = None
            for c in candidates:
                if c.is_file():
                    found_p = c
                    break
            if not found_p:
                for jf in sorted(p.glob('*.json')):
                    try:
                        with open(jf, 'r', encoding='utf-8') as f:
                            d = json.load(f)
                        if isinstance(d, dict) and 'scenes' in d:
                            found_p = jf
                            break
                    except Exception:
                        continue
            if not found_p:
                raise FileNotFoundError(f'Không tìm thấy file cấu hình story_project.json trong thư mục: {p}')
            p = found_p
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        proj = cls.from_dict(data)
        actual_dir = Path(p.parent).resolve()
        saved_pdir = data.get('project_dir')
        if saved_pdir and Path(saved_pdir).is_dir():
            proj.project_dir = str(Path(saved_pdir).resolve())
        else:
            proj.project_dir = str(actual_dir)
        for sc in proj.scenes:
            if sc.audio_path:
                ap = Path(sc.audio_path)
                if not ap.is_file():
                    if (actual_dir / sc.audio_path).is_file():
                        sc.audio_path = str((actual_dir / sc.audio_path).resolve())
                    elif (actual_dir / 'audio' / ap.name).is_file():
                        sc.audio_path = str((actual_dir / 'audio' / ap.name).resolve())
                    elif (actual_dir / ap.name).is_file():
                        sc.audio_path = str((actual_dir / ap.name).resolve())
            if sc.image_path:
                ip = Path(sc.image_path)
                if not ip.is_file():
                    if (actual_dir / sc.image_path).is_file():
                        sc.image_path = str((actual_dir / sc.image_path).resolve())
                    elif (actual_dir / 'images' / ip.name).is_file():
                        sc.image_path = str((actual_dir / 'images' / ip.name).resolve())
                    elif (actual_dir / 'thumbnails' / ip.name).is_file():
                        sc.image_path = str((actual_dir / 'thumbnails' / ip.name).resolve())
                    elif (actual_dir / ip.name).is_file():
                        sc.image_path = str((actual_dir / ip.name).resolve())
            if not sc.video_path: continue
            vp = Path(sc.video_path)
            if vp.is_file(): continue
            if (actual_dir / sc.video_path).is_file():
                sc.video_path = str((actual_dir / sc.video_path).resolve())
            elif (actual_dir / 'videos' / vp.name).is_file():
                sc.video_path = str((actual_dir / 'videos' / vp.name).resolve())
            elif (actual_dir / vp.name).is_file():
                sc.video_path = str((actual_dir / vp.name).resolve())
        if proj.bgm_path and not Path(proj.bgm_path).is_file():
            bp = Path(proj.bgm_path)
            if (actual_dir / proj.bgm_path).is_file():
                proj.bgm_path = str((actual_dir / proj.bgm_path).resolve())
            elif (actual_dir / 'bgm' / bp.name).is_file():
                proj.bgm_path = str((actual_dir / 'bgm' / bp.name).resolve())
            elif (actual_dir / bp.name).is_file():
                proj.bgm_path = str((actual_dir / bp.name).resolve())
        if proj.texture_path and not Path(proj.texture_path).is_file():
            tp = Path(proj.texture_path)
            if (actual_dir / proj.texture_path).is_file():
                proj.texture_path = str((actual_dir / proj.texture_path).resolve())
            elif (actual_dir / 'textures' / tp.name).is_file():
                proj.texture_path = str((actual_dir / 'textures' / tp.name).resolve())
            elif (actual_dir / tp.name).is_file():
                proj.texture_path = str((actual_dir / tp.name).resolve())
        resolved_paths = []
        for p_str in getattr(proj, 'texture_paths', []):
            if not p_str:
                continue
            if Path(p_str).is_file():
                resolved_paths.append(str(Path(p_str).resolve()))
                continue
            tp = Path(p_str)
            if (actual_dir / p_str).is_file():
                resolved_paths.append(str((actual_dir / p_str).resolve()))
            elif (actual_dir / 'textures' / tp.name).is_file():
                resolved_paths.append(str((actual_dir / 'textures' / tp.name).resolve()))
            elif (actual_dir / tp.name).is_file():
                resolved_paths.append(str((actual_dir / tp.name).resolve()))
            else:
                resolved_paths.append(p_str)
        if resolved_paths:
            proj.texture_paths = resolved_paths
            if not proj.texture_path or not Path(proj.texture_path).is_file():
                proj.texture_path = resolved_paths[0]
        elif proj.texture_path:
            proj.texture_paths = [proj.texture_path]
        return proj

def get_texture_library_dirs() -> list[Path]:
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
        primary_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    existing_dirs = []
    seen = set()
    for d in base_dirs:
        try:
            if d.is_dir():
                resolved = str(d.resolve()).lower()
                if resolved not in seen:
                    seen.add(resolved)
                    existing_dirs.append(d)
        except Exception:
            pass

    return existing_dirs or [primary_dir]

PRIMARY_TEXTURE_DIR = Path.cwd() / 'libraries' / 'textures'
TEXTURE_DIR = PRIMARY_TEXTURE_DIR

BLEND_MODES: list[tuple[str, str]] = [
    ('Screen (Sáng & Khử đen - Khuyên dùng)', 'screen'),
    ('Overlay (Tương phản điện ảnh)', 'overlay'),
    ('Multiply (Làm tối / Giấy cũ)', 'multiply'),
    ('Soft Light (Ánh sáng dịu)', 'softlight'),
    ('Lighten (Làm sáng)', 'lighten'),
    ('Addition (Tia sáng rực rỡ)', 'addition')
]

def get_blend_mode_id(display_name: str) -> str:
    """Chuyển đổi nhãn hiển thị UI thành mã mode FFmpeg (ví dụ: 'screen')."""
    d_clean = (display_name or '').strip().lower()
    for disp, mode_id in BLEND_MODES:
        if mode_id in d_clean or disp.lower() == d_clean:
            return mode_id
    return 'screen'

def get_blend_mode_display_name(mode_id: str) -> str:
    '''Chuyển đổi mã FFmpeg thành nhãn hiển thị tiếng Việt trên UI.'''
    m_clean = (mode_id or '').strip().lower()
    for disp, mid in BLEND_MODES:
        if mid == m_clean:
            return disp

    return BLEND_MODES[0][0]

def apply_texture_blend(base_img: Any, tex_img: Any, mode: str, opacity: float) -> Any:
    '''Hòa trộn frame texture lên frame video theo blend mode và opacity chuẩn điện ảnh.'''
    if opacity <= 0.005 or base_img is None or tex_img is None:
        return base_img

    try:
        from PIL import Image
        import numpy as np
        import cv2

        w, h = base_img.size
        base_arr = np.asarray(base_img)
        if isinstance(tex_img, Image.Image):
            if tex_img.size != (w, h):
                tex_img = tex_img.resize((w, h), Image.Resampling.BILINEAR)
            tex_arr = np.asarray(tex_img)
        else:
            tex_arr = tex_img
            if tex_arr.shape[1] != w or tex_arr.shape[0] != h:
                tex_arr = cv2.resize(tex_arr, (w, h), interpolation=cv2.INTER_AREA)

        if base_arr.shape[:2] != tex_arr.shape[:2]:
            return base_img

        b = base_arr.astype(np.float32) / 255.0
        t = tex_arr.astype(np.float32) / 255.0

        mode = (mode or 'screen').strip().lower()

        if 'screen' in mode:
            blended = 1.0 - (1.0 - b) * (1.0 - t)
        elif 'multiply' in mode:
            blended = b * t
        elif 'overlay' in mode:
            blended = np.where(b < 0.5, 2.0 * b * t, 1.0 - 2.0 * (1.0 - b) * (1.0 - t))
        elif 'softlight' in mode:
            blended = np.where(
                t < 0.5,
                b - (1.0 - 2.0 * t) * b * (1.0 - b),
                b + (2.0 * t - 1.0) * (np.sqrt(np.maximum(0, b)) - b)
            )
        elif 'lighten' in mode:
            blended = np.maximum(b, t)
        elif 'addition' in mode or 'dodge' in mode:
            blended = np.minimum(1.0, b + t)
        else:
            blended = 1.0 - (1.0 - b) * (1.0 - t)

        op = max(0.0, min(1.0, float(opacity)))
        out = b * (1.0 - op) + blended * op
        out_arr = (np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8)
        return Image.fromarray(out_arr)
    except Exception as exc:
        logger.debug('apply_texture_blend error: %s', exc)
        return base_img

class TextureFrameReader:
    '''Bộ giải mã và cung cấp khung hình texture video vòng lặp mượt mà cho preview playback (hỗ trợ đa texture).'''

    def __init__(self) -> None:
        self._readers = {}

    def close(self) -> None:
        for p, r in list(self._readers.items()):
            cap = r.get('cap')
            if cap is None: continue
            try:
                cap.release()
            except Exception:
                pass
        self._readers.clear()

    def _get_single_path_frame(self, path: str, t_s: float, w: int, h: int) -> Any | None:
        if not path:
            return None
        p_str = str(path)
        r = self._readers.get(p_str)
        if not (r and r.get('cap') is not None and getattr(r['cap'], 'isOpened', lambda: False)()):
            p_obj = Path(p_str)
            if not p_obj.is_file():
                return None
            try:
                import cv2
                cap = cv2.VideoCapture(p_str)
                fps = max(1.0, float(cap.get(cv2.CAP_PROP_FPS) or 30.0))
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                dur = max(0.1, frame_count / fps) if frame_count > 0 else 10.0
                r = {
                    'cap': cap,
                    'fps': fps,
                    'frame_count': frame_count,
                    'duration': dur,
                    'cur_frame_idx': -1,
                    'last_frame': None
                }
                self._readers[p_str] = r
            except Exception as exc:
                logger.debug('Không thể mở video texture: %s', exc)
                return None

        cap = r['cap']
        duration = r['duration']
        fps = r['fps']
        frame_count = r['frame_count']
        if not cap or not cap.isOpened() or duration <= 0:
            return None

        try:
            import cv2
            t_loop = max(0.0, float(t_s)) % duration
            target_idx = int(t_loop * fps)
            if frame_count > 0:
                target_idx = target_idx % frame_count

            last_f = r.get('last_frame')
            need_read = (
                target_idx != r.get('cur_frame_idx')
                or last_f is None
                or last_f.shape[1] != w
                or last_f.shape[0] != h
            )

            if need_read:
                if target_idx != r.get('cur_frame_idx', -1) + 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        return last_f
                    target_idx = 0
                r['cur_frame_idx'] = target_idx
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
                r['last_frame'] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            return r.get('last_frame')
        except Exception as exc:
            logger.debug('TextureFrameReader error on %s: %s', path, exc)
            return r.get('last_frame')

    def get_frame(self, path: Any, t_s: float, w: int, h: int, distribution: str = 'cycle_15s') -> Any | None:
        if not path:
            self.close()
            return None

        if isinstance(path, (list, tuple)):
            valid = [str(p) for p in path if p and Path(p).is_file()]
            if not valid:
                return None
            if len(valid) == 1:
                return self._get_single_path_frame(valid[0], t_s, w, h)
            if distribution == 'stack':
                f1 = self._get_single_path_frame(valid[0], t_s, w, h)
                f2 = self._get_single_path_frame(valid[1], t_s, w, h)
                if f1 is not None and f2 is not None:
                    try:
                        import cv2
                        return cv2.addWeighted(f1, 0.5, f2, 0.5, 0)
                    except Exception:
                        return f1
                return f1 or f2

            cycle_len = 15.0
            idx = int(max(0.0, float(t_s)) // cycle_len) % len(valid)
            sub_t = max(0.0, float(t_s)) % cycle_len
            return self._get_single_path_frame(valid[idx], sub_t, w, h)

        return self._get_single_path_frame(str(path), t_s, w, h)

def ensure_sample_textures() -> None:
    '''Tạo sẵn các video texture mẫu chất lượng cao, dung lượng nhẹ nếu các thư mục texture rỗng.'''
    try:
        dirs = get_texture_library_dirs()
        primary_dir = dirs[0]
        ffmpeg_bin = shutil.which('ffmpeg')

        sample_configs = [
            (
                'Sample_Film_Grain_35mm.mp4',
                ['-f', 'lavfi', '-i', 'color=c=gray:s=640x360:r=24:d=3', '-filter_complex',
                 'noise=alls=28:allf=t+u,format=yuv420p', '-c:v', 'libx264', '-crf', '26']
            ),
            (
                'Sample_Warm_Light_Leak.mp4',
                ['-f', 'lavfi', '-i', 'gradients=s=640x360:c0=black:c1=0xff8822:type=radial:speed=0.015:d=4:r=24',
                 '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '24']
            ),
            (
                'Sample_Vintage_Vignette.mp4',
                ['-f', 'lavfi', '-i', 'color=c=black:s=640x360:r=24:d=4', '-filter_complex',
                 'vignette=PI/4:mode=forward,format=yuv420p', '-c:v', 'libx264', '-crf', '24']
            )
        ]

        valid_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

        for d in dirs[1:]:
            if d.is_dir():
                for p in d.iterdir():
                    if p.is_file() and p.suffix.lower() in valid_exts:
                        target = primary_dir / p.name
                        if target.is_file(): continue
                        try:
                            shutil.copy2(str(p), str(target))
                        except Exception:
                            continue

        has_any = any(p.suffix.lower() in valid_exts for p in primary_dir.iterdir() if p.is_file())
        if not has_any and ffmpeg_bin:
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            for name, args in sample_configs:
                target_file = primary_dir / name
                if target_file.is_file(): continue
                cmd = [ffmpeg_bin, '-y', *args, str(target_file)]
                subprocess.run(cmd, capture_output=True, creationflags=flags)
    except Exception as exc:
        logger.debug('Không thể sinh sample textures: %s', exc)

def get_available_textures() -> list[tuple[str, str]]:
    '''Quét các thư mục texture (libraries/textures, library_textures, assets) và trả về danh sách tuple (Tên hiển thị, Đường dẫn file tuyệt đối).'''
    ensure_sample_textures()
    dirs = get_texture_library_dirs()
    results = []
    seen_names = set()
    valid_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() in valid_exts:
                norm_name = p.name.lower()
                if norm_name in seen_names:
                    continue
                seen_names.add(norm_name)

                disp = (
                    p.stem.replace('Sample_', '')
                    .replace('_', ' ')
                    .replace('Film Grain 35mm', 'Film Grain (Hạt phim 35mm)')
                    .replace('Warm Light Leak', 'Light Leak (Tia sáng ấm)')
                    .replace('Vintage Vignette', 'Vintage Vignette (Khung cổ điển)')
                )
                results.append((disp, str(p.resolve())))

    return results

def split_text_into_smart_chunks(script_text: str, max_chunk_chars: int = 6800) -> list[str]:
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
    if len(text) <= max_chunk_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 2

        if para_len > max_chunk_chars:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_len = 0

            sentences = re.split(r'(?<=[.!?…])\s+', para)
            sent_chunk = []
            sent_len = 0
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if sent_len + len(s) + 1 > max_chunk_chars and sent_chunk:
                    chunks.append(' '.join(sent_chunk))
                    sent_chunk = [s]
                    sent_len = len(s)
                else:
                    sent_chunk.append(s)
                    sent_len += len(s) + 1
            if sent_chunk:
                chunks.append(' '.join(sent_chunk))
            continue

        elif current_len + para_len > max_chunk_chars and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_len = para_len
        else:
            current_chunk.append(para)
            current_len += para_len

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks

def fallback_split_script(script_text: str, master_prompt: str = '', start_index: int = 1) -> list[dict[str, Any]]:
    '''Phân tách kịch bản theo câu/đoạn bằng thuật toán nội bộ (khi không có API key hoặc offline).'''
    text = script_text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    raw_segments = []

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?…])\s+', para)
        current = ''
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if not current:
                current = s
            elif len(current) + len(s) < 140:
                current += ' ' + s
            else:
                raw_segments.append(current)
                current = s
        if current:
            raw_segments.append(current)

    if not raw_segments:
        raw_segments = [text]

    scenes = []
    motions = ['zoom_in', 'pan_left', 'zoom_out', 'pan_right']

    for idx, seg in enumerate(raw_segments, start=start_index):
        motion = motions[(idx - 1) % len(motions)]
        hint_vi = seg[:80] + ('...' if len(seg) > 80 else '')
        prompt = f'{master_prompt}, scene depiction: {hint_vi}'.strip(', ')
        vid_prompt = f'Cinematic video clip, camera {motion}, {prompt}, realistic motion, 24fps'
        scenes.append({
            'scene_id': f'scene_{idx:03d}',
            'index': idx,
            'text_segment': seg,
            'visual_hint_vi': hint_vi,
            'image_prompt': prompt,
            'video_motion_prompt': vid_prompt,
            'camera_motion': motion,
            'transition': 'fade',
            'start_time_s': 0.0,
            'end_time_s': 0.0,
            'duration_s': 0.0,
            'audio_path': '',
            'image_path': '',
            'image_source': '',
            'media_type': 'image',
            'video_path': '',
            'video_source': '',
            **{
                'speaker': 'narrator',
                'sfx_path': '',
                'sfx_volume': 0.5,
                'sfx_offset_s': 0.0,
                'status': 'pending'
            }
        })

    return scenes

SYSTEM_INSTRUCTION_STORY_CHUNKER = 'Bạn là đạo diễn kịch bản và chuyên gia sản xuất video storytelling điện ảnh đỉnh cao (phong cách tài liệu chân thực, kịch tính, điện ảnh sâu sắc bám sát thực tế dành cho khán giả quốc tế trưởng thành).\n\nNhiệm vụ của bạn:\nPhân tích đoạn kịch bản được giao (Phần {chunk_num}/{total_chunks}) thành các Phân Cảnh (Scenes) điện ảnh lôi cuốn.\n\nQUY TẮC ĐẶT TÊN, CHỦ ĐỀ, MÔ TẢ VÀ THUMBNAIL VIDEO (YOUTUBE / TIKTOK):\n1. video_title: Sinh ra MỘT tiêu đề video SIÊU THU HÚT (clickbait, drama, tò mò) tóm tắt toàn bộ cốt truyện (giữ theo ngôn ngữ kịch bản). Tiêu đề này trả về ở cấp cao nhất của JSON.\n2. video_topic_vi: Tóm tắt chủ đề / ý nghĩa kịch bản bằng 1 câu Tiếng Việt ngắn gọn, súc tích (ví dụ: \'Vụ án bí ẩn được phơi bày sau 10 năm điều tra\' hoặc \'Hành trình vượt nghịch cảnh phi thường\') để người dùng nắm rõ chủ đề kịch bản.\n3. video_description: Viết MỘT ĐOẠN MÔ TẢ VIDEO HOÀN CHỈNH chuẩn SEO YouTube / TikTok / Facebook: gồm mở đầu tóm tắt hấp dẫn khơi gợi sự tò mò (hook), 1-2 đoạn tóm tắt câu chuyện không spoil cái kết, lời kêu gọi Subscribe/Like tương tác, và 5-8 hashtags thịnh hành (#Storytelling, #Drama, v.v.) bằng ngôn ngữ kịch bản.\n4. thumbnail_prompt: Viết một MASTER PROMPT TẠO ẢNH BÌA THUMBNAIL YOUTUBE (hoàn toàn bằng Tiếng Anh) siêu kịch tính, cinematic 8k, photorealistic, góc nhìn đặc tả cảm xúc cao trào nhất của câu chuyện, ánh sáng tương phản chiaroscuro, kèm chữ text overlay giật gân để hút triệu view.\n5. Trong suốt các phân cảnh, phân cảnh nào chứa khoảnh khắc CAO TRÀO NHẤT (dramatic nhất), hãy thêm chữ của `video_title` vào `image_prompt` (ví dụ: Text "[video_title]" overlaid on the image).\n\nQUY TẮC CỐT TRUYỆN (BẮT BUỘC):\n1. CƠ CHẾ GIỮ CHÂN 3 GIÂY ĐẦU (3-SECOND HOOK MASTER): Nếu đoạn này chứa Phân Cảnh 1 (index = 1), câu thoại mở đầu BẮT BUỘC phải là một HOOK giật gân, khơi gợi tò mò cực độ (câu hỏi bí ẩn, sự thật gây sốc, hoặc vào thẳng cao trào in media res). TUYỆT ĐỐI không chào hỏi hay mở đầu bằng lời giới thiệu dài dòng. Hình ảnh Phân Cảnh 1 phải có góc máy cận cảnh (close-up/crash zoom), ánh mắt biểu cảm nghẹt thở, và camera_motion là \'hook_crash_zoom\'.\n2. text_segment: Cắt kịch bản gốc thành từng phân đoạn thoại vừa vặn (mỗi phân cảnh gồm 1-2 câu, thời lượng đọc khoảng 6 - 12 giây).\n3. TUYỆT ĐỐI GIỮ NGUYÊN BẢN: Sử dụng 100% câu chữ nguyên gốc từ kịch bản của tác giả (giữ nguyên văn ngôn ngữ gốc: Tiếng Anh, Tiếng Việt, Tiếng Trung, v.v.). KHÔNG được tự ý dịch sang ngôn ngữ khác, KHÔNG tự ý tóm tắt sơ sài, KHÔNG thêm thắt nội dung ngoài, KHÔNG bỏ sót câu từ.\n4. TRÁNH LẶP LẠI & LAN MAN: Tập trung vào trọng tâm cảm xúc và cao trào của từng phân cảnh.\n\nQUY TẮC HÌNH ẢNH ĐIỆN ẢNH (DÀNH CHO KHÁN GIẢ TRƯỞNG THÀNH):\n1. visual_hint_vi: 1 câu tiếng Việt ngắn gọn tóm tắt cảnh để người dùng dễ chọn ảnh.\n2. image_prompt: Viết hoàn toàn bằng TIẾNG ANH, kết hợp Master Prompt phong cách mỹ thuật. Mô tả chi tiết:\n   - Chủ thể chính (nhân vật, biểu cảm sâu sắc, ánh mắt, trang phục).\n   - Bối cảnh và không khí (atmosphere, moody, dark mystery, dramatic lighting, volumetric haze).\n   - Phân cảnh kịch tính nhất: Phải chèn thêm mô tả text overlay giống `video_title`.\n   - Chất lượng cao cấp: photorealistic, cinematic 8k, Unreal Engine 5 aesthetic, master composition, 35mm film grain.\n3. ĐA DẠNG GÓC MÁY: Tuyệt đối KHÔNG lặp lại một góc máy liên tiếp. Luôn chuyển giữa: wide establishing shot, medium close-up, dramatic low-angle, over-the-shoulder, atmospheric deep focus.\n4. video_motion_prompt: Viết hoàn toàn bằng TIẾNG ANH mô tả chuyển động video sống động cho các model Video AI (Google Veo 3, Runway Gen-3, Luma Dream Machine, Kling AI, Pika, Sora). Mô tả chuyển động camera (slow push-in, pan, tracking), hành động nhân vật, tương tác vật lý (gió thổi, mưa rơi, khói sương), 24fps film look.\n5. camera_motion: Chọn một trong [\'hook_crash_zoom\', \'hook_shake\', \'hook_whip_pan\', \'zoom_in\', \'zoom_out\', \'pan_left\', \'pan_right\', \'tilt_up\', \'tilt_down\', \'static\']. Đặc biệt Phân Cảnh 1 nên ưu tiên \'hook_crash_zoom\' hoặc \'hook_shake\'.\n6. speaker: Tên nhân vật đang nói đoạn thoại này (ví dụ: \'John\', \'Sarah\', \'Thám tử Nam\') hoặc \'narrator\' nếu là lời người dẫn chuyện/kể chuyện.\n\nQUY TẮC ĐÁNH SỐ:\n- Phân cảnh đầu tiên của đoạn này BẮT ĐẦU từ số thứ tự index = {start_index}.\n{context_note}\n\nBẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY:\n{{\n  "video_title": "Tiêu đề video cực thu hút ở đây",\n  "video_topic_vi": "Tóm tắt chủ đề kịch bản bằng Tiếng Việt ở đây",\n  "video_description": "Mô tả video hoàn chỉnh chuẩn SEO YouTube/TikTok kèm hashtags...",\n  "thumbnail_prompt": "Prompt tiếng Anh mô tả chi tiết hình ảnh Thumbnail YouTube triệu view kịch tính",\n  "scenes": [\n    {{\n      "index": {start_index},\n      "speaker": "narrator",\n      "text_segment": "...",\n      "visual_hint_vi": "...",\n      "image_prompt": "...",\n      "video_motion_prompt": "...",\n      "camera_motion": "zoom_in"\n    }}\n  ]\n}}'

PROVIDER_ENDPOINTS = {
    'Gemini': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
    'Groq': 'https://api.groq.com/openai/v1/chat/completions',
    'DeepSeek': 'https://api.deepseek.com/chat/completions',
    'OpenAI': 'https://api.openai.com/v1/chat/completions'
}

STORY_AI_MODELS: dict[str, list[str]] = {
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
        'gemini-1.5-flash'
    ],
    'Groq': [
        'openai/gpt-oss-120b',
        'openai/gpt-oss-20b',
        'groq/compound',
        'qwen/qwen3.6-27b',
        'llama-3.1-8b-instant'
    ],
    'DeepSeek': [
        'deepseek-chat',
        'deepseek-reasoner'
    ],
    'OpenAI': [
        'gpt-4o-mini',
        'gpt-4o',
        'o3-mini',
        'o1-mini',
        'gpt-4.5-preview',
        'gpt-3.5-turbo'
    ]
}

def get_story_provider_keys(provider: str) -> list[str]:
    '''Lấy danh sách API key khả dụng cho provider tương ứng (loại bỏ trùng lặp và key rỗng).'''
    p = (provider or '').strip()
    keys = []
    if p in ('Gemini', 'Google Gemini'):
        keys = get_translation_api_keys('Gemini')
        if not keys:
            single = get_gemini_api_key()
            if single:
                keys = [single]
    elif p in ('Groq', 'Groq Cloud'):
        keys = get_translation_api_keys('Groq')
    elif p in ('DeepSeek', 'DeepSeek AI'):
        keys = get_translation_api_keys('DeepSeek')
    elif p in ('OpenAI', 'OpenAI GPT'):
        keys = get_translation_api_keys('OpenAI')
    return [k.strip() for k in keys if k and k.strip()]

def _call_gemini_story(api_key: str,
                       model: str,
                       system_instruction: str,
                       user_content: str,
                       timeout: int = 50) -> str:
    '''Gọi Google Gemini REST API trả về chuỗi JSON bóc tách kịch bản.'''
    norm_model = normalize_gemini_model(model or 'gemini-2.5-flash')
    norm_model = normalize_gemini_model(model or 'gemini-flash-latest')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{norm_model}:generateContent?key={api_key}'
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': f'{system_instruction}\n\n{user_content}'}]
            }
        ],
        'generationConfig': {
            'temperature': 0.3,
            'responseMimeType': 'application/json',
            'maxOutputTokens': 8192,
            'thinkingConfig': {'thinkingBudget': 0}
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    candidates = data.get('candidates', [])
    if not candidates:
        raise ValueError(f'Gemini ({norm_model}) không trả về candidate: {data}')
    parts = candidates[0].get('content', {}).get('parts', [])
    if not parts:
        raise ValueError(f'Gemini candidate không có part text: {data}')
    if False:  # nhánh chết, giữ lại vì `text` là biến hàm khai báo nhưng không dùng
        text = ''
    return parts[0].get('text', '').strip()

def _call_openai_compatible_story(provider: str,
                                  api_key: str,
                                  model: str,
                                  system_instruction: str,
                                  user_content: str,
                                  timeout: int = 50) -> str:
    '''Gọi OpenAI-compatible API (Groq Cloud, DeepSeek AI, OpenAI GPT).'''
    endpoint = PROVIDER_ENDPOINTS.get(provider)
    if not endpoint:
        raise ValueError(f'Không tìm thấy endpoint cho provider {provider}')

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': user_content}
        ],
        'temperature': 0.3,
        'max_tokens': 8192,
        'response_format': {'type': 'json_object'}
    }
    if provider == 'Groq' and ('gpt-oss' in model or 'compound' in model):
        payload['reasoning_effort'] = 'low'

    req_data = json.dumps(payload).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'User-Agent': 'WinterboyStudio/3.0'
    }
    req = urllib.request.Request(endpoint, data=req_data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as he:
        err_text = ''
        if hasattr(he, 'read') and callable(he.read):
            try:
                err_text = he.read().decode('utf-8', errors='replace')
            except Exception:
                pass
        if he.code == 400 and 'response_format' in err_text.lower():
            payload.pop('response_format', None)
            req2 = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                data = json.loads(resp2.read().decode('utf-8'))
        else:
            raise urllib.error.HTTPError(he.url, he.code, err_text, he.hdrs, None)
    choices = data.get('choices') or []
    if not choices:
        raise ValueError(f'{provider} ({model}) không trả về choices: {data}')
    content = (choices[0].get('message') or {}).get('content') or ''
    return content.strip()

def _parse_and_build_scenes(raw_text: str, master_prompt: str, start_index: int) -> list[dict[str, Any]]:
    '''Phân tích chuỗi JSON trả về từ LLM (bất kể Gemini, Groq, DeepSeek, OpenAI, Web ChatGPT/Gemini) và dựng danh sách Scene.'''
    raw_text = (raw_text or '').strip()

    fence_m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
    candidate_text = fence_m.group(1).strip() if fence_m else raw_text

    if candidate_text.startswith('```json'):
        candidate_text = candidate_text[7:]
    elif candidate_text.startswith('```'):
        candidate_text = candidate_text[3:]
    if candidate_text.endswith('```'):
        candidate_text = candidate_text[:-3]
    candidate_text = candidate_text.strip()

    parsed = None
    try:
        parsed = json.loads(candidate_text, strict=False)
    except Exception:
        m = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', candidate_text)
        if m:
            try:
                parsed = json.loads(m.group(1), strict=False)
            except Exception:
                parsed = None
        if parsed is None and candidate_text != raw_text:
            m2 = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', raw_text)
            if m2:
                try:
                    parsed = json.loads(m2.group(1), strict=False)
                except Exception:
                    parsed = None

    if parsed is None:
        raise ValueError(f'Không thể phân tích JSON từ kết quả AI: {raw_text[:200]}')

    raw_scenes = []
    if isinstance(parsed, list):
        raw_scenes = parsed
    elif isinstance(parsed, dict):
        raw_scenes = parsed.get('scenes') or parsed.get('data') or parsed.get('story') or []
        if not raw_scenes and 'text_segment' in parsed:
            raw_scenes = [parsed]
    elif isinstance(parsed, str):
        try:
            inner = json.loads(parsed)
            if isinstance(inner, list):
                raw_scenes = inner
            elif isinstance(inner, dict):
                raw_scenes = inner.get('scenes') or inner.get('data') or inner.get('story') or []
        except Exception:
            pass

    if not raw_scenes or not isinstance(raw_scenes, list):
        raise ValueError(f'AI không trả về danh sách phân cảnh hợp lệ (Dữ liệu nhận: {type(parsed)})')

    video_title = ''
    video_topic_vi = ''
    video_description = ''
    thumbnail_prompt = ''
    if isinstance(parsed, dict):
        if 'video_title' in parsed:
            video_title = str(parsed['video_title']).strip()
        if 'video_topic_vi' in parsed:
            video_topic_vi = str(parsed['video_topic_vi']).strip()
        elif 'topic_vi' in parsed:
            video_topic_vi = str(parsed['topic_vi']).strip()
        if 'video_description' in parsed:
            video_description = str(parsed['video_description']).strip()
        elif 'description' in parsed:
            video_description = str(parsed['description']).strip()
        if 'thumbnail_prompt' in parsed:
            thumbnail_prompt = str(parsed['thumbnail_prompt']).strip()

    scenes = []
    for s_offset, s in enumerate(raw_scenes):
        idx = start_index + s_offset
        if isinstance(s, str):
            s = {'text_segment': s}
        elif not isinstance(s, dict): continue

        motion = s.get('camera_motion')
        if not motion or motion not in CAMERA_MOTIONS:
            motion = 'hook_crash_zoom' if idx == 1 else 'zoom_in'
        elif idx == 1 and motion == 'zoom_in':
            motion = 'hook_crash_zoom'
        img_p = str(s.get('image_prompt', '')).strip()
        vid_p = str(s.get('video_motion_prompt', '')).strip()
        if not vid_p and img_p:
            vid_p = f'Cinematic video clip, camera {motion}, {img_p}, realistic motion, 24fps'

        hint_vi = str(s.get('visual_hint_vi', '')).strip()
        text_seg = str(s.get('text_segment', '')).strip()
        if not hint_vi and text_seg:
            hint_vi = text_seg[:80] + ('...' if len(text_seg) > 80 else '')

        if not video_topic_vi and hint_vi:
            video_topic_vi = hint_vi

        speaker = str(s.get('speaker') or 'narrator').strip()
        if not speaker:
            speaker = 'narrator'

        scene_dict = {
            'scene_id': f'scene_{idx:03d}',
            'index': idx,
            'text_segment': text_seg,
            'visual_hint_vi': hint_vi,
            'image_prompt': img_p or f'{master_prompt}, {hint_vi}'.strip(', '),
            'video_motion_prompt': vid_p,
            'camera_motion': motion,
            'transition': 'fade',
            'start_time_s': 0.0,
            'end_time_s': 0.0,
            'duration_s': 0.0,
            'audio_path': '',
            'speaker': speaker,
            'sfx_path': str(s.get('sfx_path') or '').strip(),
            'sfx_volume': float(s.get('sfx_volume', 0.5)),
            'sfx_offset_s': float(s.get('sfx_offset_s', 0.0)),
            'image_path': '',
            **{
                'image_source': '',
                'media_type': 'image',
                'video_path': '',
                'video_source': '',
                'status': 'pending'
            }
        }

        if s_offset == 0:
            if video_title:
                scene_dict['video_title'] = video_title
            if video_topic_vi:
                scene_dict['video_topic_vi'] = video_topic_vi
            if video_description:
                scene_dict['video_description'] = video_description
            if thumbnail_prompt:
                scene_dict['thumbnail_prompt'] = thumbnail_prompt

        scenes.append(scene_dict)
    return scenes

def generate_story_description_fallback(title: str, topic_vi: str = '', scenes: list[Any] | None = None,
                                        language: str = 'English') -> str:
    '''Tự động sinh mô tả video thuần túy (chỉ chứa nội dung mô tả kịch bản, không kèm CTA).'''
    t = (title or '').strip()
    topic = (topic_vi or '').strip()

    text_pieces = []
    if scenes:
        for s in scenes:
            txt = getattr(s, 'text_segment', None) or (s.get('text_segment') if isinstance(s, dict) else '')
            if not txt: continue
            t_str = str(txt).strip()
            if not t_str: continue
            text_pieces.append(t_str)
            if len(text_pieces) >= 3:
                break

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

def _process_chunk_multi_llm(chunk_text: str, master_prompt: str, provider_plans: list[dict[str, Any]],
                             start_plan_idx: int, key_cursors: dict[str, int], chunk_num: int,
                             total_chunks: int, start_index: int, context_note: str,
                             progress_callback: Any | None = None) -> tuple[list[dict[str, Any]], int]:
    '''Xử lý 1 đoạn kịch bản với kiến trúc đa tầng LLM:
    Ưu tiên Gemini & Groq -> DeepSeek -> OpenAI -> Fallback cục bộ.
    '''
    import time
    system_instruction = SYSTEM_INSTRUCTION_STORY_CHUNKER.format(
        chunk_num=chunk_num,
        total_chunks=total_chunks,
        start_index=start_index,
        context_note=context_note)

    user_content = f'MASTER PROMPT PHONG CÁCH:\n{master_prompt}\n\nKỊCH BẢN PHẦN {chunk_num}/{total_chunks}:\n{chunk_text}'

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
                try:
                    progress_callback(
                        f'Đoạn {chunk_num}/{total_chunks}: Đang bóc tách bằng {provider} ({active_model})...',
                        (chunk_num - 1) / float(total_chunks))

                except Exception:
                    pass

            try:
                if provider == 'Gemini':
                    raw_text = _call_gemini_story(
                        api_key=active_key,
                        model=active_model,
                        system_instruction=system_instruction,
                        user_content=user_content)
                else:
                    raw_text = _call_openai_compatible_story(
                        provider=provider,
                        api_key=active_key,
                        model=active_model,
                        system_instruction=system_instruction,
                        user_content=user_content)

                scenes = _parse_and_build_scenes(raw_text, master_prompt, start_index)
                if scenes:
                    logger.info(
                        'Đoạn %d/%d bóc tách thành công: %d phân cảnh (Dùng %s · Model %s · Key #%d/%d)',
                        chunk_num, total_chunks, len(scenes), provider, active_model,
                        k_idx % len(keys) + 1, len(keys))

                    key_cursors[provider] = (k_idx + 1) % len(keys)
                    return scenes, p_idx

            except urllib.error.HTTPError as e:
                err_body = ''
                if hasattr(e, 'read') and callable(e.read):
                    try:
                        err_body = e.read().decode('utf-8', errors='replace')[:300]
                    except Exception:
                        pass
                logger.warning(
                    'Đoạn %d/%d gọi %s (%s) Key #%d bị HTTP %d: %s',
                    chunk_num, total_chunks, provider, active_model,
                    k_idx % len(keys) + 1, e.code, err_body)

                if e.code == 404:
                    continue
                if e.code in (429, 500, 502, 503) or 'quota' in err_body.lower() or 'rate' in err_body.lower():
                    k_idx += 1
                    time.sleep(0.4)
                    continue

                k_idx += 1
                time.sleep(0.8)
                continue
            except Exception as exc:
                logger.warning('Đoạn %d/%d gọi %s gặp lỗi: %s', chunk_num, total_chunks, provider, exc)
                k_idx += 1
                time.sleep(0.5)
                continue

        if p_offset < num_plans - 1:
            next_plan = provider_plans[(p_idx + 1) % num_plans]
            next_p = next_plan['provider']
            msg = f'{provider} chạm giới hạn -> Tự động chuyển sang {next_p}...'
            logger.warning(msg)
            if callable(progress_callback):
                try:
                    progress_callback(msg, (chunk_num - 1) / float(total_chunks))
                except Exception:
                    pass
            time.sleep(0.4)

    logger.warning('Đoạn %d/%d: Toàn bộ AI LLM đều thất bại -> Sử dụng thuật toán fallback nội bộ', chunk_num, total_chunks)
    fb_scenes = fallback_split_script(chunk_text, master_prompt, start_index=start_index)
    return fb_scenes, start_plan_idx

def _process_chunk_with_gemini(chunk_text: str, master_prompt: str, keys: list[str], start_key_idx: int,
                               chunk_num: int, total_chunks: int, start_index: int, context_note: str,
                               model: str = 'gemini-2.5-flash') -> tuple[list[dict[str, Any]], int]:
    '''Wrapper tương thích ngược cho việc gọi Gemini phân tách đoạn kịch bản.'''
    provider_plans = [
        {
            'provider': 'Gemini',
            'keys': keys,
            'models': [model or 'gemini-flash-latest', 'gemini-2.5-flash', 'gemini-flash-lite-latest', 'gemini-1.5-flash']
        }
    ]
    key_cursors = {'Gemini': start_key_idx}
    scenes, _ = _process_chunk_multi_llm(
        chunk_text=chunk_text,
        master_prompt=master_prompt,
        provider_plans=provider_plans,
        start_plan_idx=0,
        key_cursors=key_cursors,
        chunk_num=chunk_num,
        total_chunks=total_chunks,
        start_index=start_index,
        context_note=context_note)
    return scenes, key_cursors.get('Gemini', (start_key_idx + 1) % max(len(keys), 1))

def segment_story_script(script_text: str, master_prompt: str = '', api_key: str | None = None,
                         model: str = 'gemini-2.5-flash', progress_callback: Any | None = None,
                         provider: str = 'Auto') -> list[dict[str, Any]]:
    '''Phân tách kịch bản dài thành danh sách Scene chuẩn cấu trúc điện ảnh.

    Hỗ trợ 4 nhà cung cấp AI: Gemini, Groq, DeepSeek, OpenAI.
    Ưu tiên hàng đầu: Gemini & Groq với failover tự động và xoay vòng key thông minh.
    Nếu người dùng chưa cấu hình key cho DeepSeek / OpenAI, hệ thống tự động bỏ qua an toàn.
    '''
    import time
    script_text = script_text.strip()
    if not script_text:
        return []

    p_norm = (provider or 'Auto').strip()
    if 'gemini' in p_norm.lower() and 'ưu tiên' not in p_norm.lower():
        preference_order = ['Gemini', 'Groq', 'DeepSeek', 'OpenAI']
    elif 'groq' in p_norm.lower() and 'ưu tiên' not in p_norm.lower():
        preference_order = ['Groq', 'Gemini', 'DeepSeek', 'OpenAI']
    elif 'deepseek' in p_norm.lower():
        preference_order = ['DeepSeek', 'Gemini', 'Groq', 'OpenAI']
    elif 'openai' in p_norm.lower():
        preference_order = ['OpenAI', 'Gemini', 'Groq', 'DeepSeek']
    else:
        preference_order = ['Gemini', 'Groq', 'DeepSeek', 'OpenAI']

    provider_plans = []
    for p_name in preference_order:
        if api_key and p_name == preference_order[0]:
            keys = [k.strip() for k in api_key.splitlines() if k.strip()]
        else:
            keys = get_story_provider_keys(p_name)

        if not keys:
            continue

        base_models = list(STORY_AI_MODELS.get(p_name, []))
        if model:
            if p_name == 'Gemini' and 'gemini' in model.lower():
                m_norm = normalize_gemini_model(model)
                if m_norm in base_models:
                    base_models.remove(m_norm)
                base_models.insert(0, m_norm)
            elif p_name == 'Groq' and any(k in model.lower() for k in ('groq', 'gpt-oss', 'llama', 'qwen', 'mixtral')):
                if model in base_models:
                    base_models.remove(model)
                base_models.insert(0, model)
            elif p_name == 'DeepSeek' and 'deepseek' in model.lower():
                if model in base_models:
                    base_models.remove(model)
                base_models.insert(0, model)
            elif p_name == 'OpenAI' and 'gpt' in model.lower() and 'oss' not in model.lower():
                if model in base_models:
                    base_models.remove(model)
                base_models.insert(0, model)

        provider_plans.append({
            'provider': p_name,
            'keys': keys,
            'models': base_models
        })

    if not provider_plans:
        logger.info('Không có API key nào (Gemini, Groq, DeepSeek, OpenAI), sử dụng bộ tách kịch bản nội bộ (fallback)')
        return fallback_split_script(script_text, master_prompt)

    chunks = split_text_into_smart_chunks(script_text, max_chunk_chars=6800)
    total_chunks = len(chunks)
    active_providers_str = ' -> '.join(f"{pl['provider']}({len(pl['keys'])} keys)" for pl in provider_plans)
    logger.info(
        'Bắt đầu bóc tách kịch bản: Tổng %d ký tự -> Chia thành %d đoạn xử lý. Kế hoạch AI: %s',
        len(script_text), total_chunks, active_providers_str)

    all_scenes = []
    active_plan_idx = 0
    key_cursors = {}
    current_scene_idx = 1
    last_scene_summary = ''

    for c_idx, chunk_text in enumerate(chunks, start=1):
        if last_scene_summary:
            context_note = (
                f"LƯU Ý KẾT NỐI MẠCH TRUYỆN: Cảnh trước đó vừa kết thúc tại: '{last_scene_summary}'. Hãy tiếp tục phân cảnh cho câu chuyện từ điểm này, đảm bảo mạch cảm xúc và tính liên tục."
            )
        else:
            context_note = 'Đây là phần mở đầu của câu chuyện.'

        chunk_scenes, active_plan_idx = _process_chunk_multi_llm(
            chunk_text=chunk_text,
            master_prompt=master_prompt,
            provider_plans=provider_plans,
            start_plan_idx=active_plan_idx,
            key_cursors=key_cursors,
            chunk_num=c_idx,
            total_chunks=total_chunks,
            start_index=current_scene_idx,
            context_note=context_note,
            progress_callback=progress_callback)

        if chunk_scenes:
            all_scenes.extend(chunk_scenes)
            current_scene_idx += len(chunk_scenes)
            last_scene = chunk_scenes[-1]
            last_scene_summary = last_scene.get('visual_hint_vi') or last_scene.get('text_segment', '')[:60]

        if c_idx < total_chunks:
            time.sleep(0.4)

    if callable(progress_callback):
        try:
            progress_callback(f'Đã hoàn tất bóc tách {len(all_scenes)} phân cảnh.', 1.0)
        except Exception:
            pass

    logger.info('Hoàn tất bóc tách toàn bộ kịch bản: Tổng %d phân cảnh', len(all_scenes))
    return all_scenes

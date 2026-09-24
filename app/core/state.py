# Source Generated with Decompyle++
# File: state.pyc (Python 3.12)

'''
AppState — toàn bộ biến (CTk variables) map 1-1 với control UI.

Giai đoạn 2 sẽ đọc state.to_dict() để build FFmpeg.
Giai đoạn 3 sẽ dùng state cho Gemini / TTS.
'''
from __future__ import annotations
import json
import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator
import customtkinter as ctk
logger = logging.getLogger(__name__)
_CAPCUT_FIX_ASSET_DIR = Path(__file__).resolve().parents[1] / 'resources' / 'capcut_fix'

def bundled_capcut_fix_paths():
    '''Return the recovery BAT and Device JSON shipped with Winterboy Studio.'''
    return (_CAPCUT_FIX_ASSET_DIR / 'fix_shark.bat', _CAPCUT_FIX_ASSET_DIR / 'device.json')

from app.services.job_workspace import DEFAULT_VIDEO_OUTPUT
@dataclass
class AppState:
    """Container biến UI + danh sách file (không phải CTk var)."""
    video_paths: list[str] = field(default_factory=list)
    active_video_path: str | None = None
    srt_path: str | None = None
    logo_path: str | None = None
    bgm_paths: list[str] = field(default_factory=list)
    bgm_clips: list[dict[str, Any]] = field(default_factory=list)
    bgm_active_index: int = 0
    trim_segments: list[dict[str, str]] = field(default_factory=list)
    thumbnail_path: str | None = None
    output_dir: str = field(default_factory=lambda: str(DEFAULT_VIDEO_OUTPUT))
    reuse_voice_path: str | None = None
    recent_fonts: list[str] = field(default_factory=list)
    edit_target: str = 'sub'
    active_tool: str = 'video'
    blur_regions: list[dict[str, Any]] = field(default_factory=list)
    blur_active_index: int = 0
    _batch_update_depth: int = 0
    ratio: ctk.StringVar = None
    fps: ctk.StringVar = None
    zoom: ctk.StringVar = None
    speed: ctk.StringVar = None
    mute: ctk.BooleanVar = None
    vocal_filter: ctk.BooleanVar = None
    flip_h: ctk.BooleanVar = None
    use_gpu: ctk.BooleanVar = None
    gpu_backend: ctk.StringVar = None
    video_codec: ctk.StringVar = None
    enable_windows_toast: ctk.BooleanVar = None
    capcut_sub_only: ctk.BooleanVar = None
    original_volume: ctk.DoubleVar = None
    tts_volume: ctk.DoubleVar = None
    keep_original_audio: ctk.BooleanVar = None
    adaptive_ducking: ctk.BooleanVar = None
    normalize_audio: ctk.BooleanVar = None
    demucs_enable: ctk.BooleanVar = None
    enable_subtitle: ctk.BooleanVar = None
    sub_karaoke: ctk.BooleanVar = None
    enable_tts: ctk.BooleanVar = None
    srt_mode: ctk.StringVar = None
    ai_engine: ctk.StringVar = None
    appearance_mode: ctk.StringVar = None
    accent_palette: ctk.StringVar = None
    show_waveform: ctk.BooleanVar = None
    gemini_model: ctk.StringVar = None
    translation_reflow: ctk.BooleanVar = None
    natural_voice_sync: ctk.BooleanVar = None
    soft_timing_enabled: ctk.BooleanVar = None
    weak_pc: ctk.BooleanVar = None
    stt_model: ctk.StringVar = None
    stt_language: ctk.StringVar = None
    stt_provider: ctk.StringVar = None
    translate_source: ctk.StringVar = None
    translate_target: ctk.StringVar = None
    voice_id: ctk.StringVar = None
    tts_provider: ctk.StringVar = None
    capcut_strict: ctk.BooleanVar = None
    capcut_fast_mode: ctk.BooleanVar = None
    capcut_fix_shark_enabled: ctk.BooleanVar = None
    capcut_fix_shark_path: ctk.StringVar = None
    capcut_fix_shark_device_path: ctk.StringVar = None
    capcut_use_backup: ctk.BooleanVar = None
    capcut_backup_path: ctk.StringVar = None
    elevenlabs_model: ctk.StringVar = None
    eleven_stability: ctk.DoubleVar = None
    eleven_similarity: ctk.DoubleVar = None
    eleven_style: ctk.DoubleVar = None
    eleven_speaker_boost: ctk.BooleanVar = None
    tts_speed: ctk.StringVar = None
    sub_font: ctk.StringVar = None
    sub_size: ctk.StringVar = None
    sub_opacity: ctk.DoubleVar = None
    sub_delay: ctk.StringVar = None
    sub_text_effect: ctk.StringVar = None
    sub_stroke_width: ctk.StringVar = None
    sub_color: ctk.StringVar = None
    sub_letter_spacing: ctk.StringVar = None
    sub_bg_style: ctk.StringVar = None
    sub_bg_enable: ctk.BooleanVar = None
    sub_pad_x: ctk.StringVar = None
    sub_pad_y: ctk.StringVar = None
    sub_x: ctk.StringVar = None
    sub_y: ctk.StringVar = None
    sub_box_w: ctk.StringVar = None
    sub_box_h: ctk.StringVar = None
    srt_text_buffer: ctk.StringVar = None
    blur_enable: ctk.BooleanVar = None
    blur_x: ctk.StringVar = None
    blur_y: ctk.StringVar = None
    blur_w: ctk.StringVar = None
    blur_h: ctk.StringVar = None
    blur_canvas_w: ctk.StringVar = None
    blur_canvas_h: ctk.StringVar = None
    blur_start: ctk.StringVar = None
    blur_end: ctk.StringVar = None
    blur_strength: ctk.DoubleVar = None
    blur_feather: ctk.DoubleVar = None
    blur_opacity: ctk.DoubleVar = None
    bgm_volume: ctk.DoubleVar = None
    bgm_delay: ctk.StringVar = None
    bgm_loop: ctk.BooleanVar = None
    logo_enable: ctk.BooleanVar = None
    logo_size: ctk.DoubleVar = None
    logo_opacity: ctk.DoubleVar = None
    logo_motion: ctk.StringVar = None
    logo_position: ctk.StringVar = None
    logo_motion_speed: ctk.DoubleVar = None
    logo_delay: ctk.StringVar = None
    static_text_enable: ctk.BooleanVar = None
    static_text: ctk.StringVar = None
    static_font: ctk.StringVar = None
    static_size: ctk.StringVar = None
    static_opacity: ctk.DoubleVar = None
    static_motion: ctk.StringVar = None
    static_position: ctk.StringVar = None
    static_motion_speed: ctk.DoubleVar = None
    static_delay: ctk.StringVar = None
    watermark_enable: ctk.BooleanVar = None
    watermark_text: ctk.StringVar = None
    watermark_opacity: ctk.DoubleVar = None
    watermark_motion: ctk.StringVar = None
    watermark_position: ctk.StringVar = None
    watermark_motion_speed: ctk.DoubleVar = None
    watermark_delay: ctk.StringVar = None
    brand_motion_cycle: ctk.DoubleVar = None
    brand_safe_margin: ctk.DoubleVar = None
    brand_safe_zone: ctk.StringVar = None
    trim_enable: ctk.BooleanVar = None
    trim_head: ctk.StringVar = None
    trim_tail: ctk.StringVar = None
    bypass_subpixel: ctk.BooleanVar = None
    bypass_noise: ctk.BooleanVar = None
    bypass_colorspace: ctk.BooleanVar = None
    bypass_tempo: ctk.BooleanVar = None
    bypass_gop: ctk.BooleanVar = None
    bypass_zoompan: ctk.BooleanVar = None
    bypass_ultimate: ctk.BooleanVar = None
    rotate: ctk.DoubleVar = None
    brightness: ctk.DoubleVar = None
    contrast: ctk.DoubleVar = None
    saturation: ctk.DoubleVar = None
    story_provider: ctk.StringVar = None
    story_voice: ctk.StringVar = None
    story_speed: ctk.DoubleVar = None
    story_voice_volume: ctk.DoubleVar = None
    story_video_volume: ctk.DoubleVar = None
    story_duck_volume: ctk.DoubleVar = None
    story_ratio: ctk.StringVar = None
    story_sub_burn_in: ctk.BooleanVar = None
    story_master_prompt_preset: ctk.StringVar = None
    story_last_project_path: ctk.StringVar = None
    story_youtube_length: ctk.StringVar = None
    story_youtube_tone: ctk.StringVar = None
    story_youtube_language: ctk.StringVar = None
    story_ai_video_model: ctk.StringVar = None
    story_ai_video_duration: ctk.IntVar = None
    story_texture_enabled: ctk.BooleanVar = None
    story_texture_path: ctk.StringVar = None
    story_texture_paths: list[str] = field(default_factory=list)
    story_texture_distribution: ctk.StringVar = None
    story_texture_blend_mode: ctk.StringVar = None
    story_texture_opacity: ctk.DoubleVar = None
    story_texture_loop: ctk.BooleanVar = None
    story_output_dir: ctk.StringVar = None
    re_render_only: ctk.BooleanVar = None
    loop_video_to_audio: ctk.BooleanVar = None
    fast_ffmpeg_render: ctk.BooleanVar = None

def g_safe(v = None):
    
    try:
        return v.get()
    except Exception:
        return None



def default_config_path():
    '''File cấu hình mặc định (tự load khi mở app).'''
    if os.environ.get('WINTERBOY_PROJECT_ROOT'):
        root = Path(os.environ['WINTERBOY_PROJECT_ROOT']).resolve()
    elif getattr(sys, 'frozen', False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parents[2]
    candidates = [
        root / 'output' / 'last_config.json',
        root.parent.parent / 'output' / 'last_config.json',
        root / 'apps' / 'auto_render' / 'output' / 'last_config.json']
    for c in candidates:
        if not c.is_file():
            continue
        
        return candidates, c
    return root / 'output' / 'last_config.json'


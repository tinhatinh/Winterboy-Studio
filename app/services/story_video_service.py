# Source Generated with Decompyle++
# File: story_video_service.pyc (Python 3.12)

'''Dịch vụ sinh video AI (Google Veo 3 / Omni Flash) và quản lý tài sản Video Clips cho Storytelling.

Hỗ trợ:
- Gán video thủ công từ máy tính (.mp4, .mov, .webm, .mkv).
- Quét và khớp video tự động từ thư mục (Folder Batch Import).
- Trích xuất poster thumbnail từ file video bằng FFmpeg.
- Tích hợp sinh video AI bằng Google Veo (veo-2.0 / veo-3) với xoay vòng 6 API Key.
- Chế độ Omni Flash Video Motion tốc độ cao.
'''
from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error as urllib
import urllib.request as urllib
from pathlib import Path
from typing import Any, Callable
from app.services.story_engine import get_gemini_api_key, get_translation_api_keys
from app.services.story_image_service import extract_scene_index_from_filename, media_sort_key, probe_video_duration_s, sync_story_timeline_and_srt
logger = logging.getLogger(__name__)
SUPPORTED_VIDEO_EXTS = {
    '.m4v',
    '.mkv',
    '.mov',
    '.webm',
    '.mp4'}

def _ffmpeg():
    exe = shutil.which('ffmpeg')
    if not exe:
        raise RuntimeError('Không tìm thấy công cụ FFmpeg trong hệ thống.')
    return exe


def _hidden_kwargs():
    if not sys.platform.startswith('win'):
        return { }
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 134217728)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
    startupinfo.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
    return {
        'creationflags': creationflags,
        'startupinfo': startupinfo }


def _natural_sort_key(s = None):
    pass
# WARNING: Decompyle incomplete


def extract_video_thumbnail(video_path = None, output_image_path = None, time_s = None):
    '''Trích xuất một khung hình (poster frame) từ video bằng FFmpeg để hiển thị thumbnail trên giao diện.'''
    ffmpeg_bin = _ffmpeg()
    v_path = Path(video_path).resolve()
    out_img = Path(output_image_path).resolve()
    out_img.parent.mkdir(parents = True, exist_ok = True)
    cmd = [
        ffmpeg_bin,
        '-y',
        '-ss',
        f'''{time_s:.2f}''',
        '-i',
        str(v_path),
        '-vframes',
        '1',
        '-q:v',
        '2',
        str(out_img)]
# WARNING: Decompyle incomplete


def assign_video_to_scene(scene = None, video_path = None, project_dir = None, start_time_s = (None, None)):
    '''Gán một video clip cụ thể vào phân cảnh và tự động trích xuất ảnh poster thumbnail tại đúng timestamp SRT.'''
    v_path = Path(video_path).resolve()
    if not v_path.is_file():
        return scene
    final_path = None
# WARNING: Decompyle incomplete


def apply_single_video_to_all_scenes(scenes = None, video_path = None, project_dir = None):
    """Áp dụng 1 video duy nhất cho toàn bộ các phân cảnh trong kịch bản.

    - Sao chép file video 1 lần duy nhất vào videos/source_all.<ext> để tiết kiệm dung lượng ổ cứng.
    - Tự động đồng bộ timeline SRT (nếu chưa có) để có timestamp chuẩn xác cho từng phân cảnh.
    - Cập nhật video_path, media_type='video', video_source='single_for_all' cho tất cả scenes.
    - Khóa video_start_s = scene.start_time_s để mỗi phân cảnh tự động cắt đúng timestamp của SRT.
    - Trích xuất ảnh poster thumbnail riêng cho từng phân cảnh tại đúng khoảnh khắc của phân cảnh đó.
    - Trả về số phân cảnh đã được cập nhật.
    """
    v = Path(video_path).resolve()
    if not v.is_file():
        raise FileNotFoundError(f'''Không tìm thấy file video: {video_path}''')
    final_path = v
# WARNING: Decompyle incomplete


def match_folder_videos_to_scenes(folder_path = None, scenes = None, project_dir = None):
    '''Quét thư mục chứa các video clips và tự động gán tuần tự / thông minh vào từng phân cảnh.'''
    folder = Path(folder_path)
    if not folder.is_dir():
        return scenes
# WARNING: Decompyle incomplete

assign_videos_from_folder = match_folder_videos_to_scenes

def generate_veo_ai_video(prompt = None, output_video_path = None, *, aspect_ratio, duration_s, keys, progress_cb):
    '''Sinh video AI điện ảnh bằng Google Veo (veo-2.0 / veo-3) API.'''
    prompt = prompt.strip()
    if not prompt:
        raise ValueError('Prompt sinh video không được để trống')
    key_pool = keys or get_translation_api_keys('Gemini')
    if not key_pool:
        single = get_gemini_api_key()
        if single:
            key_pool = [
                single]
    if not key_pool:
        raise ValueError('Chưa có API Key Gemini nào để sinh video Veo.')
    out_file = Path(output_video_path).resolve()
    out_file.parent.mkdir(parents = True, exist_ok = True)
    ar = '16:9' if '16:9' in aspect_ratio else '9:16'
    model = 'veo-2.0-generate-video'
    key_idx = 0
    max_attempts = max(len(key_pool) * 2, 4)
    payload = {
        'instances': [
            {
                'prompt': prompt,
                'aspectRatio': ar,
                'durationSeconds': min(8, max(5, duration_s)),
                'personGeneration': 'ALLOW_ADULT' }] }
    if progress_cb:
        progress_cb(0.15, 'Đang gửi yêu cầu sinh video sang Google Veo AI...')
    operation_name = ''
    active_key = ''
# WARNING: Decompyle incomplete


def generate_omni_flash_video(prompt = None, output_video_path = None, *, aspect_ratio, duration_s, keys, progress_cb):
    '''Sinh video Omni Flash tốc độ cao kết hợp sinh hình ảnh photorealistic và hiệu ứng chuyển động đa chiều.'''
    generate_gemini_image = generate_gemini_image
    import app.services.story_image_service
    out_file = Path(output_video_path).resolve()
    out_file.parent.mkdir(parents = True, exist_ok = True)
    if progress_cb:
        progress_cb(0.7, 'Omni Flash: Đang sinh hình ảnh gốc độ nét cao...')
    temp_img = out_file.parent / f'''omni_base_{out_file.stem}.png'''
    key_pool = keys or get_gemini_keys_pool()
    api_k = key_pool[0] if key_pool else None
    generate_gemini_image(prompt, temp_img, api_key = api_k, aspect_ratio = aspect_ratio)
    if progress_cb:
        progress_cb(0.85, 'Omni Flash: Đang tổng hợp chuyển động camera điện ảnh...')
    ffmpeg_bin = _ffmpeg()
    (width, height) = (1920, 1080) if '16:9' in aspect_ratio else (1080, 1920)
    dur = max(4, float(duration_s))
    fps = 60
    total_frames = max(1, int(round(dur * fps)))
    hi_w = width * 2
    build_ken_burns_vf = build_ken_burns_vf
    import app.services.story_video_assembler
    vf = build_ken_burns_vf('zoom_in', dur, width, height, fps = fps, with_fade = True)
    cmd = [
        ffmpeg_bin,
        '-y',
        '-framerate',
        str(fps),
        '-loop',
        '1',
        '-i',
        str(temp_img),
        '-t',
        f'''{dur:.2f}''',
        '-vf',
        vf,
        '-c:v',
        'libx264',
        '-preset',
        'fast',
        '-crf',
        '18',
        '-pix_fmt',
        'yuv420p',
        '-an',
        str(out_file)]
# WARNING: Decompyle incomplete


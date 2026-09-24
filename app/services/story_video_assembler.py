# Source Generated with Decompyle++
# File: story_video_assembler.pyc (Python 3.12)

'''Bộ lắp ráp và render video kể chuyện (Story Video Assembler) bằng FFmpeg & GPU NVENC.

Áp dụng:
- Ken Burns Effect (Pan & Zoom đa dạng góc máy: Zoom In, Zoom Out, Pan Left, Pan Right, Static).
- Chuyển cảnh mềm mại (Cinematic fade).
- Nối âm thanh lời dẫn và trộn nhạc nền (BGM) có chế độ Auto-ducking (hạ âm lượng khi có lời đọc).
- Tùy chọn khắc phụ đề (burn-in subtitle) đồng bộ 100% với SRT.
- Tăng tốc phần cứng GPU NVIDIA RTX 4050 Laptop (h264_nvenc) và tự động fallback CPU (libx264).
'''
from __future__ import annotations
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable
from PIL import Image, ImageDraw, ImageFont
from app.services.ffmpeg_renderer import detect_gpu_encoder
from app.services.media_probe import probe_video_duration_s
logger = logging.getLogger(__name__)
ProgressCb = Callable[([
    float,
    str], None)]

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


def _has_audio_stream(file_path = None):
    '''Kiểm tra tệp video có chứa track âm thanh hay không.'''
    pass
# WARNING: Decompyle incomplete


def _create_placeholder_image(output_path = None, width = None, height = None, title = ('',), subtitle = ('output_path', 'Path', 'width', 'int', 'height', 'int', 'title', 'str', 'subtitle', 'str', 'return', 'Path')):
    '''Tạo ảnh nền phân cảnh điện ảnh (Cinematic Storyboard Card) nếu phân cảnh chưa có ảnh gán.'''
    output_path.parent.mkdir(parents = True, exist_ok = True)
    img = Image.new('RGB', (width, height), color = (15, 23, 42))
    draw = ImageDraw.Draw(img)
    for y in range(0, height, 4):
        ratio = y / max(1, height)
        r = int(15 * (1 - ratio) + 30 * ratio)
        g = int(23 * (1 - ratio) + 41 * ratio)
        b = int(42 * (1 - ratio) + 59 * ratio)
        draw.line([
            (0, y),
            (width, y + 3)], fill = (r, g, b), width = 4)
    m = int(min(width, height) * 0.05)
    draw.rectangle([
        m,
        m,
        width - m,
        height - m], outline = (51, 65, 85), width = 3)
    draw.rectangle([
        m + 12,
        m + 12,
        width - m - 12,
        height - m - 12], outline = (14, 165, 233), width = 1)
    
    try:
        font_lg = ImageFont.truetype('arial.ttf', size = int(min(width, height) * 0.042))
        font_sm = ImageFont.truetype('arial.ttf', size = int(min(width, height) * 0.024))
    except Exception:
        font_lg = ImageFont.load_default()
        font_sm = ImageFont.load_default()
    top_label = 'MUMU STORYTELLING  ·  STORYBOARD'
    draw.text((width // 2, int(height * 0.38)), top_label, fill = (56, 189, 248), anchor = 'mm', font = font_sm)
    main_title = f'''PHÂN CẢNH: {title[:45]}'''
    draw.text((width // 2, int(height * 0.48)), main_title, fill = (241, 245, 249), anchor = 'mm', font = font_lg)
    sub_note = subtitle[:60] if subtitle else 'Âm thanh & Phụ đề sẵn sàng  ·  Chờ nạp Hình ảnh / Video AI'
    draw.text((width // 2, int(height * 0.58)), sub_note, fill = (148, 163, 184), anchor = 'mm', font = font_sm)
    img.save(output_path)
    return output_path



def build_ken_burns_vf(motion, duration, width, height, fps = None, with_fade = None, fade_in = None, fade_out = (60, True, True, True, False), fast = ('motion', 'str', 'duration', 'float', 'width', 'int', 'height', 'int', 'fps', 'int', 'with_fade', 'bool', 'fade_in', 'bool', 'fade_out', 'bool', 'fast', 'bool', 'return', 'str')):
    '''
    Xây dựng chuỗi bộ lọc Ken Burns điện ảnh tinh tế (subtle cinematic Ken Burns).
    - Tôn trọng tối đa bố cục khung hình gốc (không crop lẹm 20-40% chi tiết ảnh).
    - zoom_in / zoom_out: Zoom nhẹ 5% chuẩn điện ảnh, căn tâm hoàn hảo 100%.
    - static: 0% crop thừa, giữ nguyên 100% hình ảnh vừa khít khung canvas.
    - pan / tilt: Mở rộng vừa đủ chiều cần di chuyển (5%), chiều còn lại giữ nguyên 100%.
    - Hook: Zoom / Shake / Whip pan mượt mà, hạn chế tối đa phóng đại làm vỡ bố cục.
    '''
    total_frames = max(1, int(round(duration * fps)))
    motion = (motion or 'zoom_in').lower().strip()
    interp = 'cubic'
    filters = []
    p_lin = f'''(in/{total_frames})'''
    p_expr = f'''({p_lin}*{p_lin}*(3-2*{p_lin}))'''
    if motion == 'static':
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
    elif motion in ('zoom_in', 'zoom_out'):
        z = 0.05
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z / 2))
        dy = int(round(height * z / 2))
        filters.append(persp)
    elif motion in ('pan_left', 'pan_right'):
        z = 0.08
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z))
        dy = int(round(height * z))
        y_top = dy / 2
        y_bot = height - dy / 2
        filters.append(persp)
    elif motion in ('tilt_up', 'tilt_down'):
        z = 0.08
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z))
        dy = int(round(height * z))
        x_left = dx / 2
        x_right = width - dx / 2
        filters.append(persp)
    elif motion == 'hook_crash_zoom':
        z = 0.08
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z / 2))
        dy = int(round(height * z / 2))
        n_crash = max(1, min(total_frames, int(round(0.6 * fps))))
        remain_frames = max(1, total_frames - n_crash)
        p_crash = f'''if(lt(in\\,{n_crash})\\,pow(in/{n_crash}\\,0.35)\\,min(1.0\\,0.90+0.10*(in-{n_crash})/{remain_frames}))'''
        persp = []["perspective=x0='"][f'''{dx}''']['*'][f'''{p_crash}''']["':y0='"][f'''{dy}''']['*'][f'''{p_crash}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_crash}''']["':y1='"][f'''{dy}''']['*'][f'''{p_crash}''']["':x2='"][f'''{dx}''']['*'][f'''{p_crash}''']["':y2='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_crash}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_crash}''']["':y3='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_crash}''']["':interpolation="][f'''{interp}''']([]["perspective=x0='"][f'''{dx}''']['*'][f'''{p_crash}''']["':y0='"][f'''{dy}''']['*'][f'''{p_crash}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_crash}''']["':y1='"][f'''{dy}''']['*'][f'''{p_crash}''']["':x2='"][f'''{dx}''']['*'][f'''{p_crash}''']["':y2='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_crash}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_crash}''']["':y3='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_crash}''']["':interpolation="][f'''{interp}'''][':eval=frame'])
        filters.append(persp)
    elif motion == 'hook_shake':
        pad = 1.03
        scale_w = int(round(width * pad))
        scale_h = int(round(height * pad))
        if scale_w % 2 != 0:
            scale_w += 1
        if scale_h % 2 != 0:
            scale_h += 1
        dw = scale_w - width
        dh = scale_h - height
        filters.append(f'''scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={scale_w}:{scale_h},setsar=1''')
        n_decay = max(1, int(round(0.8 * fps)))
        sx = f'''{int(width * 0.015)}*sin(in*1.7)*exp(-in/{n_decay})'''
        sy = f'''{int(height * 0.015)}*cos(in*2.1)*exp(-in/{n_decay})'''
        persp = []["perspective=x0='"][f'''{dw / 2:.2f}''']['+'][f'''{sx}''']["':y0='"][f'''{dh / 2:.2f}''']['+'][f'''{sy}''']["':x1='"][f'''{scale_w - dw / 2:.2f}''']['+'][f'''{sx}''']["':y1='"][f'''{dh / 2:.2f}''']['+'][f'''{sy}''']["':x2='"][f'''{dw / 2:.2f}''']['+'][f'''{sx}''']["':y2='"][f'''{scale_h - dh / 2:.2f}''']['+'][f'''{sy}''']["':x3='"][f'''{scale_w - dw / 2:.2f}''']['+'][f'''{sx}''']["':y3='"][f'''{scale_h - dh / 2:.2f}''']['+'][f'''{sy}''']["':interpolation="][f'''{interp}''']([]["perspective=x0='"][f'''{dw / 2:.2f}''']['+'][f'''{sx}''']["':y0='"][f'''{dh / 2:.2f}''']['+'][f'''{sy}''']["':x1='"][f'''{scale_w - dw / 2:.2f}''']['+'][f'''{sx}''']["':y1='"][f'''{dh / 2:.2f}''']['+'][f'''{sy}''']["':x2='"][f'''{dw / 2:.2f}''']['+'][f'''{sx}''']["':y2='"][f'''{scale_h - dh / 2:.2f}''']['+'][f'''{sy}''']["':x3='"][f'''{scale_w - dw / 2:.2f}''']['+'][f'''{sx}''']["':y3='"][f'''{scale_h - dh / 2:.2f}''']['+'][f'''{sy}''']["':interpolation="][f'''{interp}'''][':eval=frame'])
        filters.append(persp)
        filters.append(f'''crop={width}:{height}:{dw // 2}:{dh // 2},setsar=1''')
    elif motion == 'hook_whip_pan':
        z = 0.08
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z))
        dy = int(round(height * z))
        y_top = dy / 2
        y_bot = height - dy / 2
        n_whip = max(1, min(total_frames, int(round(0.5 * fps))))
        p_whip = f'''if(lt(in\\,{n_whip})\\,pow(in/{n_whip}\\,0.38)\\,1.0)'''
        persp = []["perspective=x0='"][f'''{dx}''']['*(1-'][f'''{p_whip}'''][")':y0='"][f'''{y_top:.2f}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_whip}''']["':y1='"][f'''{y_top:.2f}''']["':x2='"][f'''{dx}''']['*(1-'][f'''{p_whip}'''][")':y2='"][f'''{y_bot:.2f}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_whip}''']["':y3='"][f'''{y_bot:.2f}''']["':interpolation="][f'''{interp}''']([]["perspective=x0='"][f'''{dx}''']['*(1-'][f'''{p_whip}'''][")':y0='"][f'''{y_top:.2f}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_whip}''']["':y1='"][f'''{y_top:.2f}''']["':x2='"][f'''{dx}''']['*(1-'][f'''{p_whip}'''][")':y2='"][f'''{y_bot:.2f}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_whip}''']["':y3='"][f'''{y_bot:.2f}''']["':interpolation="][f'''{interp}'''][':eval=frame'])
        filters.append(persp)
    else:
        z = 0.05
        filters.append(f'''scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1''')
        dx = int(round(width * z / 2))
        dy = int(round(height * z / 2))
        persp = []["perspective=x0='"][f'''{dx}''']['*'][f'''{p_expr}''']["':y0='"][f'''{dy}''']['*'][f'''{p_expr}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_expr}''']["':y1='"][f'''{dy}''']['*'][f'''{p_expr}''']["':x2='"][f'''{dx}''']['*'][f'''{p_expr}''']["':y2='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_expr}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_expr}''']["':y3='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_expr}''']["':interpolation="][f'''{interp}''']([]["perspective=x0='"][f'''{dx}''']['*'][f'''{p_expr}''']["':y0='"][f'''{dy}''']['*'][f'''{p_expr}''']["':x1='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_expr}''']["':y1='"][f'''{dy}''']['*'][f'''{p_expr}''']["':x2='"][f'''{dx}''']['*'][f'''{p_expr}''']["':y2='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_expr}''']["':x3='"][f'''{width}''']['-'][f'''{dx}''']['*'][f'''{p_expr}''']["':y3='"][f'''{height}''']['-'][f'''{dy}''']['*'][f'''{p_expr}''']["':interpolation="][f'''{interp}'''][':eval=frame'])
        filters.append(persp)
    if with_fade and duration >= 1:
        fade_dur = min(0.35, duration / 4)
        fade_out_start = max(0, duration - fade_dur)
        if fade_in:
            filters.append(f'''fade=t=in:st=0:d={fade_dur:.3f}''')
        if fade_out:
            filters.append(f'''fade=t=out:st={fade_out_start:.3f}:d={fade_dur:.3f}''')
    return ','.join(filters)


def scene_media_key(sc = None):
    '''Xác định khóa đại diện cho media của phân cảnh (tôn trọng media_type).'''
    m_type = sc.get('media_type', 'image')
    v = sc.get('video_path')
    img = sc.get('image_path')
    if m_type == 'video' and v and Path(v).is_file():
        return f'''v:{Path(v).resolve()}'''
    if img and Path(img).is_file():
        return f'''i:{Path(img).resolve()}'''
    if v and Path(v).is_file():
        return f'''v:{Path(v).resolve()}'''
    return f'''none:{sc.get('scene_id') or sc.get('index')}'''


def render_scene_clip(scene, output_path, width, height, fps, encoder, encoder_args = None, fast = None, with_fade = None, fade_in = (1920, 1080, 60, 'h264_nvenc', None, False, True, True, True), fade_out = ('scene', 'dict[str, Any]', 'output_path', 'str | Path', 'width', 'int', 'height', 'int', 'fps', 'int', 'encoder', 'str', 'encoder_args', 'list[str] | None', 'fast', 'bool', 'with_fade', 'bool', 'fade_in', 'bool', 'fade_out', 'bool', 'return', 'Path')):
    '''Render một phân cảnh đơn lẻ thành video clip MP4 (ảnh + hiệu ứng chuyển động + voice).'''
    ffmpeg_bin = _ffmpeg()
    out_clip = Path(output_path).resolve()
    out_clip.parent.mkdir(parents = True, exist_ok = True)
    duration = float(scene.get('duration_s') or 0.0)
    if duration <= 0:
        duration = 4
    m_type = scene.get('media_type', 'image')
    video_path = scene.get('video_path')
    img_path = scene.get('image_path')
    if m_type == 'video':
        is_video_scene = bool(video_path and Path(video_path).is_file())
    elif m_type == 'image':
        is_video_scene = False
    else:
        is_video_scene = bool(video_path and Path(video_path).is_file() and not (img_path and Path(img_path).is_file()))
    audio_path = scene.get('audio_path')
    has_audio = bool(audio_path and Path(audio_path).is_file())
    motion = scene.get('camera_motion', 'zoom_in')
    video_start = float(scene.get('video_start_s') or 0.0)
# WARNING: Decompyle incomplete


def _hex_to_ass_color(hex_color = None, alpha = None):
    '''Chuyển đổi mã màu hex (#RRGGBB) sang định dạng màu ASS (&HAABBGGRR).'''
    hex_str = str(hex_color or '#FFFFFF').lstrip('#')
    if len(hex_str) != 6:
        hex_str = 'FFFFFF'
    
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
    except Exception:
        (r, g, b) = (255, 255, 255)
    a_int = max(0, min(255, int(round((1 - alpha) * 255))))
    return f'''&H{a_int:02X}{b:02X}{g:02X}{r:02X}'''



def assemble_story_video(project_dir, scenes, output_mp4, voice_volume, video_volume, bgm_path, bgm_volume, bgm_clips, enable_subtitle, srt_path, aspect_ratio, texture_path, texture_paths, texture_distribution, texture_blend_mode, texture_opacity, texture_loop, progress_cb = None, fast_preview = None, sub_options = None, cancel_event = (1, None, None, 0.15, None, True, None, '16:9', None, None, 'cycle_15s', 'screen', 0.35, True, None, False, None, None, None), fps = ('project_dir', 'str | Path', 'scenes', 'list[dict[str, Any]]', 'output_mp4', 'str | Path', 'voice_volume', 'float', 'video_volume', 'float | None', 'bgm_path', 'str | Path | None', 'bgm_volume', 'float', 'bgm_clips', 'list[dict[str, Any]] | None', 'enable_subtitle', 'bool', 'srt_path', 'str | Path | None', 'aspect_ratio', 'str', 'texture_path', 'str | Path | None', 'texture_paths', 'list[str | Path] | None', 'texture_distribution', 'str', 'texture_blend_mode', 'str', 'texture_opacity', 'float', 'texture_loop', 'bool', 'progress_cb', 'ProgressCb | None', 'fast_preview', 'bool', 'sub_options', 'dict[str, Any] | None', 'cancel_event', 'threading.Event | None', 'fps', 'int | None', 'return', 'Path')):
    '''Nối tất cả các phân cảnh, hòa trộn video texture loop, trộn nhạc nền ducking đa track và khắc phụ đề SRT.'''
    pass
# WARNING: Decompyle incomplete


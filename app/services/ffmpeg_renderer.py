# Source Generated with Decompyle++
# File: ffmpeg_renderer.pyc (Python 3.12)

'''Render MP4 thành phẩm bằng FFmpeg.

CapCut là tuỳ chọn chỉnh tay; module này là luồng xuất mặc định và không phụ
thuộc draft JSON nội bộ của CapCut.  Mọi layer được bake vào MP4 cuối cùng.
'''
from __future__ import annotations
import hashlib
import json
import logging
import math
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from app.services.artifact_manifest import file_dependency, stable_fingerprint
from app.services.audio_sync_engine import probe_duration_s
from app.services.srt_utils import SrtCue, load_srt
from app.services.subtitle_layout import wrap_subtitle_block
from app.services.system_fonts import resolve_system_font
logger = logging.getLogger(__name__)
ProgressCb = Callable[([
    float,
    str], None)]
_FAST_VISUAL_CACHE_VERSION = 'fast-visual-v3-hd-blur'
_VISUAL_OPTION_KEYS = ('ratio', 'use_gpu', 'flip_h', 'speed', 'zoom', 'trim_enable', 'trim_head_s', 'trim_tail_s', 'rotate', 'brightness', 'contrast', 'saturation', 'bypass_ultimate', 'bypass_subpixel', 'bypass_noise', 'bypass_colorspace', 'bypass_zoompan', 'enable_subtitle', 'sub_font', 'sub_size', 'sub_opacity', 'sub_bg_style', 'sub_bg_enable', 'sub_x', 'sub_y', 'sub_box_w', 'sub_box_h', 'sub_pad_x', 'sub_pad_y', 'sub_delay', 'sub_color', 'sub_stroke_color', 'sub_stroke_width', 'sub_letter_spacing', 'sub_karaoke', 'sub_text_effect', 'sub_color_preset', 'blur_enable', 'blur_x', 'blur_y', 'blur_w', 'blur_h', 'blur_regions', 'blur_strength', 'blur_feather', 'blur_opacity', 'blur_canvas_w', 'blur_canvas_h', 'logo_enable', 'logo_path', 'logo_size', 'logo_opacity', 'logo_motion', 'logo_position', 'logo_motion_speed', 'logo_delay', 'static_text_enable', 'static_text', 'static_font', 'static_size', 'static_opacity', 'static_motion', 'static_position', 'static_motion_speed', 'static_delay', 'watermark_enable', 'watermark_text', 'watermark_opacity', 'watermark_motion', 'watermark_position', 'watermark_motion_speed', 'watermark_delay', 'brand_motion_cycle', 'brand_safe_margin', 'brand_safe_zone', 'video_codec')

def _hidden_process_kwargs(*, new_process_group):
    '''Keep FFmpeg/FFprobe subprocesses invisible on Windows.'''
    if not sys.platform.startswith('win'):
        return { }
    creationflags = None(subprocess, 'CREATE_NO_WINDOW', 134217728)
    if new_process_group:
        creationflags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
    startupinfo = subprocess.STARTUPINFO()
    getattr(subprocess, 'SW_HIDE', 0) = startupinfo, startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1), .dwFlags
    return {
        'creationflags': creationflags,
        'startupinfo': startupinfo }


def _kill_process_tree(pid = None):
    '''Dừng process + con (ffmpeg filtergraph) trên Windows/Unix.'''
    if pid <= 0:
        return None
# WARNING: Decompyle incomplete

MP4RenderResult = <NODE:12>()

def _ffmpeg():
    value = shutil.which('ffmpeg')
    if not value:
        raise RuntimeError('Không tìm thấy ffmpeg trong PATH')
    return value


def _ffprobe():
    value = shutil.which('ffprobe')
    if not value:
        raise RuntimeError('Không tìm thấy ffprobe trong PATH')
    return value


def _number(value = None, default = None):
    
    try:
        return float(value)
    except (TypeError, ValueError):
        return 



def _brand_motion_kind(value = None):
    if not value:
        value
    raw = str('').strip().casefold()
    if 'chéo' in raw or 'diagonal' in raw:
        return 'diagonal'
    if 'trái' in raw or 'horizontal' in raw:
        return 'horizontal'
    if 'lên' in raw or 'vertical' in raw:
        return 'vertical'
    return 'none'


def _brand_position_kind(value = None):
    if not value:
        value
    raw = str('').strip().casefold()
    if raw and 'mặc định' in raw or 'default' in raw:
        return None
    horizontal = 'center'
    vertical = 'middle'
    if 'trái' in raw or 'left' in raw:
        horizontal = 'left'
    elif 'phải' in raw or 'right' in raw:
        horizontal = 'right'
    if 'trên' in raw or 'top' in raw:
        vertical = 'top'
        return (horizontal, vertical)
    if None in raw or 'bottom' in raw:
        vertical = 'bottom'
    return (horizontal, vertical)


def _brand_fixed_position(position = None, *, default_x, default_y, canvas_w, canvas_h, item_w, item_h, margin):
    kind = _brand_position_kind(position)
# WARNING: Decompyle incomplete


def _brand_motion_expr(motion = None, *, delay, default_x, default_y, canvas_w, canvas_h, item_w, item_h, cycle, margin, safe_zone, position):
    '''Return smooth, frame-evaluated x/y expressions for Brand overlays.'''
    kind = _brand_motion_kind(motion)
    if not cycle:
        cycle
    cycle = max(2, min(3600, float(8)))
    if not margin:
        margin
    margin = max(0, min(500, float(0)))
    phase = f'''(0.5-0.5*cos(2*PI*(t-{max(0, delay):.3f})/{cycle:.3f}))'''
    (fixed_x, fixed_y, position_kind) = _brand_fixed_position(position, default_x = default_x, default_y = default_y, canvas_w = canvas_w, canvas_h = canvas_h, item_w = item_w, item_h = item_h, margin = margin)
    m = f'''{margin:.3f}'''
    min_y = m
    max_y = f'''{canvas_h}-{item_h}-{m}'''
    if not safe_zone:
        safe_zone
    zone = str('').casefold()
    if 'nửa trên' in zone or 'upper' in zone:
        max_y = f'''{canvas_h}/2-{item_h}-{m}'''
    elif 'nửa dưới' in zone or 'lower' in zone:
        min_y = f'''{canvas_h}/2+{m}'''
    phase_x = phase
    phase_y = phase
# WARNING: Decompyle incomplete


def _brand_effective_cycle(base_cycle = None, motion_speed = None):
    '''Đổi tốc độ phần trăm của một lớp thành chu kỳ chuyển động thực tế.'''
    cycle = max(2, min(60, _number(base_cycle, 8)))
    speed = max(0, min(100, _number(motion_speed, 100))) / 100
    if speed <= 0:
        return cycle
    return None(3600, cycle / speed)


def _brand_motion_at_speed(motion = None, motion_speed = None):
    '''0% đứng yên hoàn toàn; các mức còn lại giữ loại chuyển động đã chọn.'''
    if _number(motion_speed, 100) > 0:
        return motion


def _bool(value = None):
    return bool(value)


def _even(n = None):
    '''Làm số chẵn ≥ 2 (libx264/yuv420p).'''
    n = int(n)
    if n < 2:
        return 2
    if n % 2 == 0:
        return n
    return None - 1


def probe_video_size(path = None):
    '''Trả về (width, height) stream video đầu; fallback 1920x1080.'''
    pass
# WARNING: Decompyle incomplete


def probe_video_bitrate(path = None):
    '''Return the first video stream bitrate in bits/s, or zero when absent.'''
    pass
# WARNING: Decompyle incomplete


def _path_fingerprint(path = None, *, content_hash):
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_file():
        return {
            'path': str(p.resolve()),
            'missing': True }
    stat = None.stat()
    item = {
        'path': str(p.resolve()),
        'size': stat.st_size,
        'mtime_ns': stat.st_mtime_ns }
    if content_hash:
        item['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    return item


def _visual_cache_key(video = None, srt_path = None, options = None):
    '''Fingerprint every input that can change a baked video pixel.'''
    pass
# WARNING: Decompyle incomplete


def _visual_cache_root():
    return Path(tempfile.gettempdir()) / 'mumu_ffmpeg_visual_cache'


def _prune_visual_cache(root = None, keep = None, *, max_files, max_bytes):
    '''Bound the opt-in cache so long videos cannot fill the system drive.'''
    
    try:
        files = (lambda .0: pass# WARNING: Decompyle incomplete
)(root.glob('*.mp4')(), key = (lambda p: p.stat().st_mtime_ns), reverse = True)
        total = (lambda .0: pass# WARNING: Decompyle incomplete
)(files())
        kept = 0
        for path in files:
            if path == keep:
                kept += 1
                continue
            size = path.stat().st_size
            if kept >= max_files or total > max_bytes:
                path.unlink()
                total -= size
                
                try:
                    continue
                    kept += 1
                    continue
                    return None
                    except OSError:
                        sorted
                        
                        try:
                            continue
                            
                            try:
                                pass
                            except OSError:
                                exc = None
                                logger.debug('visual cache prune failed: %s', exc)
                                exc = None
                                del exc
                                return None
                                exc = None
                                del exc






def _fast_nvenc_args(video = None, width = None, height = None, codec = ('h264',)):
    '''Fast NVENC preset with high visual clarity and resolution-aware bitrate.'''
    if not codec:
        codec
    c = 'h264'.lower().strip()
    if not 'hevc' in c:
        'hevc' in c
    is_hevc = '265' in c
    is_av1 = 'av1' in c
    pixels = max(1, width * height)
    if pixels <= 921600:
        (floor_bps, ceiling_bps) = (6000000, 14000000)
    elif pixels <= 2073600:
        (floor_bps, ceiling_bps) = (14000000, 28000000)
    elif pixels <= 3686400:
        (floor_bps, ceiling_bps) = (22000000, 38000000)
    else:
        (floor_bps, ceiling_bps) = (35000000, 60000000)
    source_bps = probe_video_bitrate(video)
    target = int(max(floor_bps, min(ceiling_bps, source_bps * 1.5 if source_bps else floor_bps)))
    if is_hevc:
        cq = '20'
        target = int(target * 0.75)
        codec_name = 'HEVC'
    elif is_av1:
        cq = '22'
        target = int(target * 0.65)
        codec_name = 'AV1'
    else:
        cq = '18'
        codec_name = 'H.264'
    maxrate = int(target * 1.5)
    bufsize = int(target * 2)
    logger.info('FFmpeg fast NVENC P4/CQ%s (%s) · source=%.2fMbps target=%.2fMbps max=%.2fMbps', cq, codec_name, source_bps / 1e+06, target / 1e+06, maxrate / 1e+06)
    args = [
        '-preset',
        'p4',
        '-rc',
        'vbr',
        '-cq',
        cq,
        '-b:v',
        str(target),
        '-maxrate',
        str(maxrate),
        '-bufsize',
        str(bufsize),
        '-spatial-aq',
        '1',
        '-temporal-aq',
        '1',
        '-rc-lookahead',
        '20',
        '-b_ref_mode',
        'middle',
        '-multipass',
        'qres']
    if is_hevc:
        args.extend([
            '-tag:v',
            'hvc1'])
    return args


def _escape_filter_path(path = None):
    '''Escaping cho filename trong filtergraph FFmpeg trên Windows.'''
    resolved = Path(path).resolve()
    return str(resolved).replace('\\', '/').replace(':', '\\:').replace("'", "\\'")


def _ass_time(seconds = None):
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f'''{h}:{m:02d}:{s:05.2f}'''


def _ass_text(text = None, *, font_name, font_size, max_width_px, letter_spacing):
    '''Xuống dòng theo bề rộng khung thật rồi escape cho ASS.

    Dùng chung ``wrap_subtitle_block`` với preview để hai bên ngắt dòng giống
    hệt nhau (trước đây ASS cắt cứng ở 24 ký tự còn preview không cắt).
    '''
    wrapped = wrap_subtitle_block(text, font_name = font_name, font_size = font_size, max_width_px = max_width_px, letter_spacing = letter_spacing)
    return wrapped.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('\n', '\\N')


def _font_name(name = None):
    if not name:
        name
    return 'Arial'.replace(',', ' ')


def _ass_filter(ass_path = None, font_name = None):
    """Ask libass to scan the selected system font's folder when available."""
    ass_arg = _escape_filter_path(ass_path)
    font_path = resolve_system_font(font_name)
    if font_path:
        return f'''ass=\'{ass_arg}\':fontsdir=\'{_escape_filter_path(font_path.parent)}\''''
    return f'''{ass_arg}\''''


def _stage_ass_for_libass(source = None):
    '''Copy ASS to a short ASCII path before FFmpeg/libass reads it.

    Some Windows libass builds still open subtitle files through ``fopen`` and
    fail around MAX_PATH even when Python itself can read the original path.
    The original ASS remains in the job workspace; this compact copy is only
    an input bridge for the FFmpeg filter.
    '''
    source = Path(source)
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()[:20]
    root = Path(tempfile.gettempdir()) / 'mumu_ass'
    root.mkdir(parents = True, exist_ok = True)
    staged = root / f'''{digest}.ass'''
    needs_copy = True
    
    try:
        if not not staged.is_file():
            not staged.is_file()
        needs_copy = staged.stat().st_size != len(payload)
        if needs_copy:
            building = root / f'''{digest}.{threading.get_ident()}.{time.time_ns()}.tmp'''
            
            try:
                building.write_bytes(payload)
                building.replace(staged)
                
                try:
                    if building.exists():
                        building.unlink()
                    cutoff = time.time() - 604800
                    
                    try:
                        for candidate in root.glob('*.ass'):
                            if not candidate != staged:
                                continue
                                
                                try:
                                    if not candidate.stat().st_mtime < cutoff:
                                        continue
                                        
                                        try:
                                            candidate.unlink()
                                            continue
                                            logger.info('ASS staged for libass · original_len=%d · staged_len=%d · %s', len(str(source)), len(str(staged)), staged)
                                            return staged
                                            except OSError:
                                                needs_copy = True
                                                continue
                                            except OSError:
                                                continue
                                            if building.exists():
                                                building.unlink()
                                        except OSError:
                                            continue








def _short_ass_work_path(srt_path = None, output = None):
    '''Return a short ASCII ASS path safe for legacy Windows file APIs.'''
    root = Path(tempfile.gettempdir()) / 'mumu_ass'
    root.mkdir(parents = True, exist_ok = True)
    identity = f'''{srt_path.resolve()}\x00{output.resolve()}'''
    digest = hashlib.sha256(identity.encode('utf-8', errors = 'ignore')).hexdigest()[:20]
    return root / f'''render_{digest}.ass'''


def write_ass_subtitles(srt_path = None, out_path = None, options = None, *, trim_head_s):
    '''Sinh file ASS.

    ``trim_head_s`` là số giây đã bị cắt ở đầu video. Timestamp trong SRT nằm
    trên timeline nguồn, còn MP4 sau ``trim`` + ``setpts=PTS-STARTPTS`` bắt đầu
    lại từ 0, nên phải trừ offset này để phụ đề không trễ đúng bằng đoạn cắt.
    '''
    pass
# WARNING: Decompyle incomplete


def _atempo_filters(rate = None):
    rate = max(0.25, min(8, rate))
    parts = []
    if rate > 2:
        parts.append('atempo=2.0')
        rate /= 2
        if rate > 2:
            continue
    if rate < 0.5:
        parts.append('atempo=0.5')
        rate /= 0.5
        if rate < 0.5:
            continue
    parts.append(f'''atempo={rate:.5f}''')
    return parts

_CACHED_GPU_ENCODER: 'dict[str, tuple[str, list[str], bool]]' = { }
_CACHED_GPU_NAMES: 'dict[str, str]' = { }
_CACHED_AVAILABLE_GPUS: 'list[dict] | None' = None
_CACHED_SYSTEM_GPUS: 'list[str] | None' = None
_CACHED_HARDWARE_BADGE: 'dict[str, dict]' = { }
_CACHED_PROBED_ENCODERS: 'dict[str, bool]' = { }

def clear_gpu_cache():
    '''Xóa bộ nhớ đệm nhận diện GPU để cho phép quét lại phần cứng.'''
    global _CACHED_AVAILABLE_GPUS, _CACHED_SYSTEM_GPUS
    _CACHED_GPU_ENCODER.clear()
    _CACHED_GPU_NAMES.clear()
    _CACHED_AVAILABLE_GPUS = None
    _CACHED_SYSTEM_GPUS = None
    _CACHED_HARDWARE_BADGE.clear()
    _CACHED_PROBED_ENCODERS.clear()


def detect_system_gpu(force_rescan = None):
    '''Quét phần cứng GPU hệ thống.'''
    if force_rescan:
        clear_gpu_cache()
    return detect_gpu_encoder()


def _probe_encoder_hardware(ffmpeg_bin = None, enc = None, timeout = None, retries = (8, 1)):
    '''Kiểm tra thực tế encoder phần cứng có chạy được trên máy không (1 frame 256x256).

    Hỗ trợ timeout lên đến 8s và retry để đảm bảo card rời (NVIDIA Optimus) kịp thức tỉnh từ D3 state.
    '''
    pass


def _probe_encoder_hardware(ffmpeg_bin = None, enc = None, timeout = None, retries = (6, 1)):
    '''Kiểm tra thực tế encoder phần cứng có chạy được trên máy không (có memoization).'''
    if enc in _CACHED_PROBED_ENCODERS:
        return _CACHED_PROBED_ENCODERS[enc]
# WARNING: Decompyle incomplete


def get_gpu_device_name(enc = None):
    '''Lấy tên card đồ hoạ thực tế từ hệ thống tương ứng với encoder đã phát hiện.'''
    pass
# WARNING: Decompyle incomplete


def detect_gpu_encoder(preferred = None, codec = None):
    """Phát hiện GPU encoder khả dụng (NVENC / AMF / QSV) và CPU theo chuẩn Codec yêu cầu.

    Args:
        preferred: 'auto' (ưu tiên card rời tốt nhất), 'nvenc', 'qsv', 'amf', hoặc 'cpu'.
        codec: 'h264', 'hevc' (H.265), hoặc 'av1'.
    """
    if not preferred:
        preferred
    pref = 'auto'.lower().strip()
    if not codec:
        codec
    c = 'h264'.lower().strip()
    if 'hevc' in c or '265' in c:
        target_codec = 'hevc'
    elif 'av1' in c:
        target_codec = 'av1'
    else:
        target_codec = 'h264'
    cache_key = f'''{pref}:{target_codec}'''
    if cache_key in _CACHED_GPU_ENCODER:
        return _CACHED_GPU_ENCODER[cache_key]
    if None == 'hevc':
        cpu_res = ('libx265', [
            '-preset',
            'fast',
            '-crf',
            '20',
            '-tag:v',
            'hvc1'], False)
    elif target_codec == 'av1':
        cpu_res = ('libsvtav1', [
            '-preset',
            '6',
            '-crf',
            '24'], False)
    else:
        cpu_res = ('libx264', [
            '-preset',
            'fast',
            '-crf',
            '18'], False)
    if pref in ('cpu', 'libx264', 'none', 'false'):
        _CACHED_GPU_ENCODER[cache_key] = cpu_res
        return cpu_res
# WARNING: Decompyle incomplete


def list_available_gpu_devices(force_rescan = None):
    '''Trả về danh sách tất cả các bộ mã hóa / card đồ hoạ khả dụng trên máy.'''
    global _CACHED_AVAILABLE_GPUS
    if force_rescan:
        _CACHED_AVAILABLE_GPUS = None
        _CACHED_GPU_ENCODER.clear()
# WARNING: Decompyle incomplete


def get_gpu_hardware_badge(preferred = None, force_rescan = None):
    '''Trả về thông tin chi tiết về phần cứng GPU và encoder hỗ trợ (có memoization).'''
    if not preferred:
        preferred
    pref = 'auto'.lower().strip()
    if force_rescan and pref in _CACHED_HARDWARE_BADGE:
        return dict(_CACHED_HARDWARE_BADGE[pref])
    (enc, args, is_gpu) = None(preferred = pref)
    dev_name = get_gpu_device_name(enc) if is_gpu else 'Không có card đồ họa rời'
    if is_gpu:
        if 'nvenc' in enc:
            badge_text = f'''NVIDIA NVENC ({dev_name})'''
            status = 'Sẵn sàng (Tăng tốc phần cứng NVIDIA NVENC)'
        elif 'amf' in enc:
            badge_text = f'''AMD AMF ({dev_name})'''
            status = 'Sẵn sàng (Tăng tốc phần cứng AMD AMF)'
        elif 'qsv' in enc:
            badge_text = f'''Intel QuickSync ({dev_name})'''
            status = 'Sẵn sàng (Tăng tốc phần cứng Intel QSV)'
        else:
            badge_text = f'''{enc.upper()} ({dev_name})'''
            status = 'Sẵn sàng (Tăng tốc phần cứng)'
    else:
        badge_text = 'Chỉ dùng CPU (libx264)'
        status = 'Không phát hiện card đồ họa hỗ trợ. FFmpeg sẽ dùng CPU để render ổn định.'
    if not pref:
        pref
    res = {
        'is_gpu': is_gpu,
        'encoder': enc,
        'device_name': dev_name,
        'badge_text': badge_text,
        'status': status,
        'selected_backend': 'auto' }
    _CACHED_HARDWARE_BADGE[pref] = res
    return dict(res)


class FFmpegRenderer:
    '''Bake video/audio/layer vào MP4 và kiểm tra output sau render.'''
    
    def __init__(self = None, work_dir = None, *, cancel_event):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents = True, exist_ok = True)
    # WARNING: Decompyle incomplete

    
    def request_cancel(self = None):
        '''Huỷ bake đang chạy (kill FFmpeg).'''
        self._cancel.set()
        self._kill_current()

    
    def is_cancelled(self = None):
        return self._cancel.is_set()

    
    def _kill_current(self = None):
        proc = self._proc
    # WARNING: Decompyle incomplete

    
    def _run_cancellable(self = None, cmd = None, *, timeout, on_progress, duration_s, dedupe_progress):
        '''
        Chạy FFmpeg có thể dừng + report % thật.

        Quan trọng:
        - Phải ĐỌC stdout/stderr liên tục (không để pipe đầy → FFmpeg treo im).
        - `-progress pipe:1` đưa out_time_ms ra stdout để UI nhích %.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _encoder(self = None, use_gpu = None, preferred_backend = None, codec = ('auto', 'h264')):

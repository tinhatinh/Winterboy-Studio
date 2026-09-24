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

def _hidden_process_kwargs(*, new_process_group = False):
    '''Keep FFmpeg/FFprobe subprocesses invisible on Windows.'''
    if not sys.platform.startswith('win'):
        return { }
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 134217728)
    if new_process_group:
        creationflags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
    startupinfo.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
    return {
        'creationflags': creationflags,
        'startupinfo': startupinfo }


def _kill_process_tree(pid: int) -> None:
    '''Dừng process + con (ffmpeg filtergraph) trên Windows/Unix.'''
    # TODO(khôi phục hành vi): bản decompile mất thân sau dòng kiểm tra pid.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer._kill_process_tree')


@dataclass
class MP4RenderResult:
    ok: bool
    output_path: Path | None = None
    manifest_path: Path | None = None
    duration_s: float = 0.0
    message: str = ''

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


def _number(value: Any, default: float = 0.0) -> float:
    
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _brand_motion_kind(value: Any) -> str:
    raw = str(value or '').strip().casefold()
    if 'chéo' in raw or 'diagonal' in raw:
        return 'diagonal'
    if 'trái' in raw or 'horizontal' in raw:
        return 'horizontal'
    if 'lên' in raw or 'vertical' in raw:
        return 'vertical'
    return 'none'


def _brand_position_kind(value: Any) -> 'tuple[str, str] | None':
    raw = str(value or '').strip().casefold()
    if not raw or 'mặc định' in raw or 'default' in raw:
        return None
    horizontal = 'center'
    vertical = 'middle'
    if 'trái' in raw or 'left' in raw:
        horizontal = 'left'
    elif 'phải' in raw or 'right' in raw:
        horizontal = 'right'
    if 'trên' in raw or 'top' in raw:
        vertical = 'top'
    elif 'dưới' in raw or 'bottom' in raw:
        vertical = 'bottom'
    return (horizontal, vertical)


def _brand_fixed_position(position: Any, *, default_x: str, default_y: str, canvas_w: str, canvas_h: str, item_w: str, item_h: str, margin: float) -> 'tuple[str, str, tuple[str, str] | None]':
    kind = _brand_position_kind(position)
    if kind is None:
        return (default_x, default_y, None)
    (horizontal, vertical) = kind
    m = f'''{margin:.3f}'''
    x = {
        'left': m,
        'center': f'''({canvas_w}-{item_w})/2''',
        'right': f'''{canvas_w}-{item_w}-{m}''' }[horizontal]
    y = {
        'top': m,
        'middle': f'''({canvas_h}-{item_h})/2''',
        'bottom': f'''{canvas_h}-{item_h}-{m}''' }[vertical]
    return (x, y, kind)


def _brand_motion_expr(motion: Any, *, delay: float, default_x: str, default_y: str, canvas_w: str, canvas_h: str, item_w: str, item_h: str, cycle: float = 8.0, margin: float = 32.0, safe_zone: Any = 'Toàn khung', position: Any = 'Mặc định') -> 'tuple[str, str]':
    '''Return smooth, frame-evaluated x/y expressions for Brand overlays.'''
    # TODO(khôi phục hành vi): bản decompile dừng ở `phase_x = phase`; phần sinh
    # biểu thức x/y theo từng kiểu chuyển động (~250 instruction) mất hẳn.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer._brand_motion_expr')


def _brand_effective_cycle(base_cycle: Any, motion_speed: Any) -> float:
    '''Đổi tốc độ phần trăm của một lớp thành chu kỳ chuyển động thực tế.'''
    cycle = max(2.0, min(60.0, _number(base_cycle, 8.0)))
    speed = max(0.0, min(100.0, _number(motion_speed, 100.0))) / 100.0
    if speed <= 0.0:
        return cycle
    return min(3600.0, cycle / speed)


def _brand_motion_at_speed(motion: Any, motion_speed: Any) -> Any:
    '''0% đứng yên hoàn toàn; các mức còn lại giữ loại chuyển động đã chọn.'''
    if _number(motion_speed, 100.0) > 0.0:
        return motion
    return 'Đứng yên'


def _bool(value: Any) -> bool:
    return bool(value)


def _even(n: int) -> int:
    '''Làm số chẵn ≥ 2 (libx264/yuv420p).'''
    n = int(n)
    if n < 2:
        return 2
    if n % 2 == 0:
        return n
    return n - 1


def probe_video_size(path: Path) -> 'tuple[int, int]':
    '''Trả về (width, height) stream video đầu; fallback 1920x1080.'''
    # TODO(khôi phục hành vi): thân hàm (lệnh ffprobe + parse JSON) mất trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.probe_video_size')


def probe_video_bitrate(path: Path) -> int:
    '''Return the first video stream bitrate in bits/s, or zero when absent.'''
    # TODO(khôi phục hành vi): thân hàm (lệnh ffprobe + parse JSON) mất trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.probe_video_bitrate')


def _path_fingerprint(path: 'str | Path | None', *, content_hash: bool = False) -> 'dict[str, Any] | None':
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_file():
        return {
            'path': str(p.resolve()),
            'missing': True }
    stat = p.stat()
    item = {
        'path': str(p.resolve()),
        'size': stat.st_size,
        'mtime_ns': stat.st_mtime_ns }
    if content_hash:
        item['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    return item


def _visual_cache_key(video: Path, srt_path: 'str | Path | None', options: 'dict[str, Any]') -> str:
    '''Fingerprint every input that can change a baked video pixel.'''
    # TODO(khôi phục hành vi): thân hàm (gom _VISUAL_OPTION_KEYS + fingerprint) mất
    # trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer._visual_cache_key')


def _visual_cache_root():
    return Path(tempfile.gettempdir()) / 'mumu_ffmpeg_visual_cache'


def _prune_visual_cache(root: Path, keep: Path, *, max_files: int = 8, max_bytes: int = 20000000000) -> None:
    '''Bound the opt-in cache so long videos cannot fill the system drive.'''
    
    try:
        files = sorted((p for p in root.glob('*.mp4') if p.is_file()), key = (lambda p: p.stat().st_mtime_ns), reverse = True)
        total = sum(p.stat().st_size for p in files)
        kept = 0
        for path in files:
            if path == keep:
                kept += 1
                continue
            size = path.stat().st_size
            if kept >= max_files or total > max_bytes:
                
                try:
                    path.unlink()
                    total -= size
                    continue
                except OSError:
                    continue

            kept += 1
    except OSError as exc:
        logger.debug('visual cache prune failed: %s', exc)
        return None


def _fast_nvenc_args(video: Path, width: int, height: int, codec: str = 'h264') -> 'list[str]':
    '''Fast NVENC preset with high visual clarity and resolution-aware bitrate.'''
    c = (codec or 'h264').lower().strip()
    is_hevc = 'hevc' in c or '265' in c
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


def _font_name(name: str) -> str:
    return (name or 'Arial').replace(',', ' ')


def _ass_filter(ass_path: Path, font_name: str) -> str:
    """Ask libass to scan the selected system font's folder when available."""
    ass_arg = _escape_filter_path(ass_path)
    font_path = resolve_system_font(font_name)
    if font_path:
        return f"ass='{ass_arg}':fontsdir='{_escape_filter_path(font_path.parent)}'"
    return f"ass='{ass_arg}'"


def _stage_ass_for_libass(source: Path) -> Path:
    '''Copy ASS to a short ASCII path before FFmpeg/libass reads it.

    Some Windows libass builds still open subtitle files through ``fopen`` and
    fail around MAX_PATH even when Python itself can read the original path.
    The original ASS remains in the job workspace; this compact copy is only
    an input bridge for the FFmpeg filter.
    '''
    # TODO(khôi phục hành vi): phần ghi file tạm + dọn file cũ (~500 instruction) bị
    # decompile thành nhánh lồng nhau không đọc được, cần dựng lại từ dis.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer._stage_ass_for_libass')


def _short_ass_work_path(srt_path = None, output = None):
    '''Return a short ASCII ASS path safe for legacy Windows file APIs.'''
    root = Path(tempfile.gettempdir()) / 'mumu_ass'
    root.mkdir(parents = True, exist_ok = True)
    identity = f'''{srt_path.resolve()}\x00{output.resolve()}'''
    digest = hashlib.sha256(identity.encode('utf-8', errors = 'ignore')).hexdigest()[:20]
    return root / f'''render_{digest}.ass'''


def write_ass_subtitles(srt_path: Path, out_path: Path, options: 'dict[str, Any]', *, trim_head_s: float = 0.0) -> Path:
    '''Sinh file ASS.

    ``trim_head_s`` là số giây đã bị cắt ở đầu video. Timestamp trong SRT nằm
    trên timeline nguồn, còn MP4 sau ``trim`` + ``setpts=PTS-STARTPTS`` bắt đầu
    lại từ 0, nên phải trừ offset này để phụ đề không trễ đúng bằng đoạn cắt.
    '''
    # TODO(khôi phục hành vi): ~2900 instruction sinh header/style/mọi event ASS —
    # bản decompile chỉ còn `pass`. Hàm này cần lượt khôi phục hành vi riêng.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.write_ass_subtitles')


def _atempo_filters(rate: float) -> 'list[str]':
    rate = max(0.25, min(8.0, rate))
    parts = []
    while rate > 2.0:
        parts.append('atempo=2.0')
        rate /= 2.0
    while rate < 0.5:
        parts.append('atempo=0.5')
        rate /= 0.5
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


def _probe_encoder_hardware(ffmpeg_bin: str, enc: str, timeout: int = 6, retries: int = 1) -> bool:
    '''Kiểm tra thực tế encoder phần cứng có chạy được trên máy không (có memoization).'''
    # TODO(khôi phục hành vi): chạy ffmpeg 1 frame 256x256 + retry (~200 instruction),
    # bản decompile chỉ còn nhánh kiểm tra cache đầu tiên.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer._probe_encoder_hardware')


def get_gpu_device_name(enc: 'str | None' = None) -> str:
    '''Lấy tên card đồ hoạ thực tế từ hệ thống tương ứng với encoder đã phát hiện.'''
    # TODO(khôi phục hành vi): ~890 instruction dò nvidia-smi / WMI / amdconf, mất
    # hoàn toàn trong bản decompile.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.get_gpu_device_name')


def detect_gpu_encoder(preferred: str = 'auto', codec: str = 'h264') -> 'tuple[str, list[str], bool]':
    """Phát hiện GPU encoder khả dụng (NVENC / AMF / QSV) và CPU theo chuẩn Codec yêu cầu.

    Args:
        preferred: 'auto' (ưu tiên card rời tốt nhất), 'nvenc', 'qsv', 'amf', hoặc 'cpu'.
        codec: 'h264', 'hevc' (H.265), hoặc 'av1'.
    """
    # TODO(khôi phục hành vi): phần quét encoder thật (~450 instruction sau khi dựng
    # cpu_res) mất trong bản decompile -> không đoán thứ tự ưu tiên NVENC/QSV/AMF.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.detect_gpu_encoder')


def list_available_gpu_devices(force_rescan: bool = False) -> 'list[dict]':
    '''Trả về danh sách tất cả các bộ mã hóa / card đồ hoạ khả dụng trên máy.'''
    # TODO(khôi phục hành vi): ~450 instruction, bản decompile dừng sau bước clear cache.
    raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.list_available_gpu_devices')


def get_gpu_hardware_badge(preferred: str = 'auto', force_rescan: bool = False) -> dict:
    '''Trả về thông tin chi tiết về phần cứng GPU và encoder hỗ trợ (có memoization).'''
    pref = (preferred or 'auto').lower().strip()
    if not force_rescan and pref in _CACHED_HARDWARE_BADGE:
        return dict(_CACHED_HARDWARE_BADGE[pref])
    (enc, args, is_gpu) = detect_gpu_encoder(preferred = pref)
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
    res = {
        'is_gpu': is_gpu,
        'encoder': enc,
        'device_name': dev_name,
        'badge_text': badge_text,
        'status': status,
        'selected_backend': pref or 'auto' }
    _CACHED_HARDWARE_BADGE[pref] = res
    return dict(res)


class FFmpegRenderer:
    '''Bake video/audio/layer vào MP4 và kiểm tra output sau render.'''
    
    def __init__(self, work_dir: 'str | Path', *, cancel_event: 'threading.Event | None' = None) -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents = True, exist_ok = True)
        self._cancel = cancel_event if cancel_event is not None else threading.Event()
        self._proc = None

    
    def request_cancel(self) -> None:
        '''Huỷ bake đang chạy (kill FFmpeg).'''
        self._cancel.set()
        self._kill_current()

    
    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    
    def _kill_current(self) -> None:
        proc = self._proc
        if proc is None:
            return None
        if proc.poll() is not None:
            return None
        
        try:
            _kill_process_tree(int(proc.pid))
        except Exception:
            
            try:
                proc.kill()
            except Exception:
                return None

        return None

    
    def _run_cancellable(self, cmd: 'list[str]', *, timeout: float = 3600, on_progress: 'Callable[[float, str], None] | None' = None, duration_s: 'float | None' = None, dedupe_progress: bool = False) -> 'subprocess.CompletedProcess[str]':
        '''
        Chạy FFmpeg có thể dừng + report % thật.

        Quan trọng:
        - Phải ĐỌC stdout/stderr liên tục (không để pipe đầy → FFmpeg treo im).
        - `-progress pipe:1` đưa out_time_ms ra stdout để UI nhích %.
        '''
        # TODO(khôi phục hành vi): ~1500 instruction (luồng đọc pipe, parse
        # out_time_ms, huỷ tiến trình) — bản decompile chỉ còn `pass`.
        raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.FFmpegRenderer._run_cancellable')

    
    def _encoder(self, use_gpu: bool, preferred_backend: str = 'auto', codec: str = 'h264') -> 'tuple[str, list[str], bool]':
        if use_gpu:
            (enc, args, is_gpu) = detect_gpu_encoder(preferred = preferred_backend, codec = codec)
            if is_gpu:
                return (enc, args, True)
        return detect_gpu_encoder(preferred = 'cpu', codec = codec)

    
    def _validate(self, output: Path, expected_layers: 'dict[str, bool]', *, dependencies: 'dict[str, Any] | None' = None) -> 'MP4RenderResult':
        # TODO(khôi phục hành vi): ~540 instruction kiểm tra output sau render; bản
        # decompile bị cắt ngay ở `def _encoder` nên không sinh ra hàm này.
        raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.FFmpegRenderer._validate')

    
    def render(self, video_path: 'str | Path', output_path: 'str | Path', *, srt_path: 'str | Path | None' = None, voice_path: 'str | Path | None' = None, options: 'dict[str, Any] | None' = None, progress: 'ProgressCb | None' = None) -> 'MP4RenderResult':
        # TODO(khôi phục hành vi): hàm chính của module (~11500 instruction) mất hoàn
        # toàn trong bản decompile. Đây là việc của lượt khôi phục hành vi.
        raise NotImplementedError('chưa khôi phục từ bytecode: ffmpeg_renderer.FFmpegRenderer.render')

    
    @staticmethod
    def _cleanup_partial(output: Path) -> None:
        
        try:
            if output.is_file():
                output.unlink()
                return None
            return None
        except OSError:
            return None

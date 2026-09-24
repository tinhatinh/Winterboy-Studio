# -*- coding: utf-8 -*-
'''
Tiền xử lý video/audio bằng ffmpeg trước khi inject CapCut.

CapCut draft JSON không hỗ trợ ổn định brightness/noise/GOP…
→ bake thật bằng ffmpeg → file trong Resources → CapCut chỉ phát.
'''
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _ffmpeg() -> str | None:
    return shutil.which('ffmpeg')


def needs_video_preprocess(options: dict[str, Any] | None) -> bool:
    if not options:
        return False
    try:
        b = float(options.get('brightness') or 0)
        c = float(options.get('contrast') or 1.0)
        s = float(options.get('saturation') or 1.0)
    except (TypeError, ValueError):
        b, c, s = 0.0, 1.0, 1.0
    if abs(b) > 0.01 or abs(c - 1.0) > 0.01 or abs(s - 1.0) > 0.01:
        return True
    return any(options.get(k)
               for k in ('bypass_noise', 'bypass_colorspace', 'bypass_zoompan',
                         'bypass_gop', 'bypass_ultimate'))


def needs_audio_fx(options: dict[str, Any] | None) -> bool:
    if not options:
        return False
    return bool(options.get('bypass_tempo')
                or options.get('bypass_ultimate')
                or options.get('vocal_filter'))


def preprocess_main_video(src: str | Path, dest: str | Path,
                          options: dict[str, Any] | None = None) -> Path | None:
    '''
    Áp eq / noise / colorbalance / crop-zoom / GOP lên bản copy video.
    Trả về dest nếu OK; None nếu bỏ qua hoặc lỗi (caller dùng src gốc).
    '''
    options = options or {}
    src = Path(src)
    dest = Path(dest)
    if not src.is_file():
        return None
    if not needs_video_preprocess(options):
        return None
    ff = _ffmpeg()
    if not ff:
        logger.warning('ffmpeg missing — skip video preprocess')
        return None

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        try:
            brightness = float(options.get('brightness') or 0.0)
        except (TypeError, ValueError):
            brightness = 0.0
        try:
            contrast = float(options.get('contrast') or 1.0)
        except (TypeError, ValueError):
            contrast = 1.0
        try:
            saturation = float(options.get('saturation') or 1.0)
        except (TypeError, ValueError):
            saturation = 1.0

        ultimate = bool(options.get('bypass_ultimate'))
        noise = ultimate or bool(options.get('bypass_noise'))
        colorspace = ultimate or bool(options.get('bypass_colorspace'))
        zoompan = ultimate or bool(options.get('bypass_zoompan'))
        gop = ultimate or bool(options.get('bypass_gop'))

        brightness = max(-0.5, min(0.5, brightness))
        contrast = max(0.5, min(1.5, contrast))
        saturation = max(0.5, min(1.5, saturation))

        vf_parts = []
        if abs(brightness) > 0.01 or abs(contrast - 1.0) > 0.01 or abs(saturation - 1.0) > 0.01:
            vf_parts.append(
                f'eq=brightness={brightness:.4f}:contrast={contrast:.4f}'
                f':saturation={saturation:.4f}')
        if colorspace:
            vf_parts.append('colorbalance=rs=0.06:gs=0.0:bs=-0.05:rm=0.02:bm=-0.02')
        if noise:
            vf_parts.append('noise=alls=10:allf=t+u')
        if zoompan:
            vf_parts.append(
                'scale=iw*1.04:ih*1.04,'
                'crop=iw/1.04:ih/1.04:(in_w-out_w)/2+4*sin(n/25):(in_h-out_h)/2')

        vf = ','.join(vf_parts) if vf_parts else 'null'

        cmd = [
            ff, '-y', '-i', str(src),
            '-vf', vf,
            '-map', '0:v:0',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '20',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
        ]
        if gop:
            cmd.extend(['-g', '48', '-keyint_min', '24'])
        else:
            cmd.extend(['-g', '60'])
        cmd.append(str(dest))

        p = subprocess.run(cmd, capture_output=True, timeout=600,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode != 0 or not dest.is_file() or dest.stat().st_size < 1000:
            err = (p.stderr or b'')[-400:].decode('utf-8', errors='replace')
            logger.warning('video preprocess fail: %s', err)
            if dest.is_file():
                try:
                    dest.unlink()
                except OSError:
                    pass
            return None
        logger.info('Preprocessed video FX → %s', dest.name)
        return dest
    except Exception as e:                                # noqa: BLE001 - bỏ FX, dùng src
        logger.warning('video preprocess exception: %s', e)
        return None


def audio_filter_chain(options: dict[str, Any] | None) -> str | None:
    '''Chuỗi -af cho extract original audio (tempo / vocal).'''
    if not needs_audio_fx(options):
        return None
    options = options or {}
    parts = []
    if options.get('bypass_tempo') or options.get('bypass_ultimate'):
        parts.append('atempo=1.02')
    if options.get('vocal_filter'):
        parts.append('highpass=f=100,lowpass=f=8000')
    return ','.join(parts) if parts else None

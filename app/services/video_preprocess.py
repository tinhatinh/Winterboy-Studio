# Source Generated with Decompyle++
# File: video_preprocess.pyc (Python 3.12)

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

def _ffmpeg():
    return shutil.which('ffmpeg')


def needs_video_preprocess(options = None):
    if not options:
        return False
    
    try:
        if not options.get('brightness'):
            options.get('brightness')
        b = float(0)
        if not options.get('contrast'):
            options.get('contrast')
        c = float(1)
        if not options.get('saturation'):
            options.get('saturation')
        s = float(1)
        if abs(b) > 0.01 and abs(c - 1) > 0.01 or abs(s - 1) > 0.01:
            return True
        for k in ('bypass_noise', 'bypass_colorspace', 'bypass_zoompan', 'bypass_gop', 'bypass_ultimate'):
            if not options.get(k):
                continue
            ('bypass_noise', 'bypass_colorspace', 'bypass_zoompan', 'bypass_gop', 'bypass_ultimate')
            return True
        return False
    except (TypeError, ValueError):
        (b, c, s) = (0, 1, 1)
        continue



def needs_audio_fx(options = None):
    if not options:
        return False
    if not options.get('bypass_tempo'):
        options.get('bypass_tempo')
        if not options.get('bypass_ultimate'):
            options.get('bypass_ultimate')
    return bool(options.get('vocal_filter'))


def preprocess_main_video(src = None, dest = None, options = None):
    '''
    Áp eq / noise / colorbalance / crop-zoom / GOP lên bản copy video.
    Trả về dest nếu OK; None nếu bỏ qua hoặc lỗi (caller dùng src gốc).
    '''
    if not options:
        options
    options = { }
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
    dest.parent.mkdir(parents = True, exist_ok = True)
    
    try:
        if not options.get('brightness'):
            options.get('brightness')
        brightness = float(0)
        
        try:
            if not options.get('contrast'):
                options.get('contrast')
            contrast = float(1)
            
            try:
                if not options.get('saturation'):
                    options.get('saturation')
                saturation = float(1)
                ultimate = bool(options.get('bypass_ultimate'))
                if not ultimate:
                    ultimate
                noise = bool(options.get('bypass_noise'))
                if not ultimate:
                    ultimate
                colorspace = bool(options.get('bypass_colorspace'))
                if not ultimate:
                    ultimate
                zoompan = bool(options.get('bypass_zoompan'))
                if not ultimate:
                    ultimate
                gop = bool(options.get('bypass_gop'))
                brightness = max(-0.5, min(0.5, brightness))
                contrast = max(0.5, min(1.5, contrast))
                saturation = max(0.5, min(1.5, saturation))
                vf_parts = []
                if abs(brightness) > 0.01 and abs(contrast - 1) > 0.01 or abs(saturation - 1) > 0.01:
                    vf_parts.append(f'''eq=brightness={brightness:.4f}:contrast={contrast:.4f}:saturation={saturation:.4f}''')
                if colorspace:
                    vf_parts.append('colorbalance=rs=0.06:gs=0.0:bs=-0.05:rm=0.02:bm=-0.02')
                if noise:
                    vf_parts.append('noise=alls=10:allf=t+u')
                if zoompan:
                    vf_parts.append('scale=iw*1.04:ih*1.04,crop=iw/1.04:ih/1.04:(in_w-out_w)/2+4*sin(n/25):(in_h-out_h)/2')
                vf = ','.join(vf_parts) if vf_parts else 'null'
                cmd = [
                    ff,
                    '-y',
                    '-i',
                    str(src),
                    '-vf',
                    vf,
                    '-map',
                    '0:v:0',
                    '-map',
                    '0:a?',
                    '-c:v',
                    'libx264',
                    '-preset',
                    'veryfast',
                    '-crf',
                    '20',
                    '-pix_fmt',
                    'yuv420p',
                    '-c:a',
                    'aac',
                    '-b:a',
                    '192k',
                    '-movflags',
                    '+faststart']
                if gop:
                    cmd.extend([
                        '-g',
                        '48',
                        '-keyint_min',
                        '24'])
                else:
                    cmd.extend([
                        '-g',
                        '60'])
                cmd.append(str(dest))
                
                try:
                    p = subprocess.run(cmd, capture_output = True, timeout = 600, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    if p.returncode != 0 and dest.is_file() or dest.stat().st_size < 1000:
                        if not p.stderr:
                            p.stderr
                        err = b''[-400:].decode('utf-8', errors = 'replace')
                        logger.warning('video preprocess fail: %s', err)
                        if dest.is_file():
                            
                            try:
                                dest.unlink()
                                return None
                                return None
                                
                                try:
                                    logger.info('Preprocessed video FX → %s', dest.name)
                                    return dest
                                    except (TypeError, ValueError):
                                        brightness = 0
                                        continue
                                    except (TypeError, ValueError):
                                        contrast = 1
                                        continue
                                    except (TypeError, ValueError):
                                        saturation = 1
                                        continue
                                    except OSError:
                                        
                                        try:
                                            return None
                                            
                                            try:
                                                pass
                                            except Exception:
                                                e = None
                                                logger.warning('video preprocess exception: %s', e)
                                                e = None
                                                del e
                                                return None
                                                e = None
                                                del e










def audio_filter_chain(options = None):
    '''Chuỗi -af cho extract original audio (tempo / vocal).'''
    if not needs_audio_fx(options):
        return None
    if not options:
        options
    options = { }
    parts = []
    if options.get('bypass_tempo') or options.get('bypass_ultimate'):
        parts.append('atempo=1.02')
    if options.get('vocal_filter'):
        parts.append('highpass=f=100,lowpass=f=8000')
    if parts:
        return ','.join(parts)


# Source Generated with Decompyle++
# File: whisper_stt.pyc (Python 3.12)

'''
Whisper STT — tạo SRT từ video/audio khi không có phụ đề.

Ưu tiên:
  1. faster-whisper
  2. openai-whisper
  3. (fail rõ ràng kèm pip install)

Luồng: video → ffmpeg extract wav 16k mono → whisper → SRT.
'''
from __future__ import annotations
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from app.services.srt_utils import SrtCue, format_ts, write_srt
logger = logging.getLogger(__name__)
@dataclass
class SttResult:
    ok: bool
    srt_path: Path | None
    n_cues: int = 0
    engine: str = ''
    language: str | None = None
    message: str = ''


def _which(name: str) -> str | None:
    return shutil.which(name)


def extract_audio_wav(media_path: Path, out_wav: Path, *, sample_rate: int = 16000) -> Path:
    ff = _which('ffmpeg')
    if not ff:
        raise RuntimeError('Cần ffmpeg trong PATH để tách audio cho Whisper')
    out_wav.parent.mkdir(parents = True, exist_ok = True)
    cmd = [
        ff,
        '-y',
        '-i',
        str(media_path),
        '-vn',
        '-ac',
        '1',
        '-ar',
        str(sample_rate),
        '-c:a',
        'pcm_s16le',
        str(out_wav)]
    p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0 or not out_wav.exists():
        raise RuntimeError(f'''ffmpeg extract audio lỗi: {(p.stderr or '')[-400:]}''')
    return out_wav


def _transcribe_faster(wav: Path, *, model_size: str, language: str | None, weak_pc: bool) -> 'tuple[list[SrtCue], str | None]':
    from faster_whisper import WhisperModel
    size = 'tiny' if weak_pc and model_size in ('base', 'small') else model_size
    if weak_pc and size not in ('tiny', 'base'):
        size = 'base'
    device = 'cpu'
    compute = 'int8'
    
    try:
        import torch
        if torch.cuda.is_available() and not weak_pc:
            device = 'cuda'
            compute = 'float16'
    except Exception:
        pass

    logger.info('faster-whisper model=%s device=%s', size, device)
    model = WhisperModel(size, device = device, compute_type = compute)
    (segments, info) = model.transcribe(str(wav), language = language, vad_filter = True)
    cues = []
    for i, seg in enumerate(segments):
        text = (seg.text or '').strip()
        if not text:
            continue
        end = seg.end if seg.end > seg.start else seg.start + 0.3
        cues.append(SrtCue(index = i, start_s = float(seg.start), end_s = float(end), text = text))
    lang = getattr(info, 'language', language)
    return (cues, lang)


def _transcribe_openai_whisper(wav: Path, *, model_size: str, language: str | None, weak_pc: bool) -> 'tuple[list[SrtCue], str | None]':
    import whisper
    size = 'tiny' if weak_pc else model_size
    logger.info('openai-whisper model=%s', size)
    model = whisper.load_model(size)
    kwargs = {
        'fp16': False }
    if language:
        kwargs['language'] = language
    result = model.transcribe(str(wav), **kwargs)
    cues = []
    for i, seg in enumerate(result.get('segments') or []):
        text = (seg.get('text') or '').strip()
        if not text:
            continue
        start = float(seg.get('start') or 0)
        end = float(seg.get('end') or start + 0.3)
        cues.append(SrtCue(index = i, start_s = start, end_s = end, text = text))
    return (cues, result.get('language') or language)


def transcribe_to_srt(media_path: str | Path, out_srt: str | Path | None = None, *, work_dir: str | Path | None = None, model_size: str = 'base', language: str | None = None, weak_pc: bool = True, provider: str = 'Whisper (local)') -> SttResult:
    # Bản decompile của hàm này rối hoàn toàn (thân các nhánh try/except lồng sai
    # chỗ, `None(cues, out)`, `except ImportError:` đặt sau return). Phần thân thật
    # dài ~500 instruction trong dis -> để luồng khôi phục hành vi xử lý, không đoán.
    raise NotImplementedError('chưa khôi phục từ bytecode: whisper_stt.transcribe_to_srt')

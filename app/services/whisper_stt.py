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
SttResult = <NODE:12>()

def _which(name = None):
    return shutil.which(name)


def extract_audio_wav(media_path = None, out_wav = None, *, sample_rate):
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
    if not p.returncode != 0 or out_wav.exists():
        if not p.stderr:
            p.stderr
        raise RuntimeError(f'''ffmpeg extract audio lỗi: {''[-400:]}''')
    return out_wav


def _transcribe_faster(wav = None, *, model_size, language, weak_pc):
    WhisperModel = WhisperModel
    import faster_whisper
    size = 'tiny' if weak_pc and model_size in ('base', 'small') else model_size
    if weak_pc and size not in ('tiny', 'base'):
        size = 'base'
    device = 'cpu'
    compute = 'int8'
    
    try:
        import torch
        if not torch.cuda.is_available() and weak_pc:
            device = 'cuda'
            compute = 'float16'
        logger.info('faster-whisper model=%s device=%s', size, device)
        model = WhisperModel(size, device = device, compute_type = compute)
        (segments, info) = model.transcribe(str(wav), language = language, vad_filter = True)
        cues = []
        for i, seg in enumerate(segments):
            if not seg.text:
                seg.text
            text = ''.strip()
            if not text:
                continue
            end = seg.end if seg.end > seg.start else seg.start + 0.3
            cues.append(SrtCue(index = i, start_s = float(seg.start), end_s = float(end), text = text))
        lang = getattr(info, 'language', language)
        return (cues, lang)
    except Exception:
        continue



def _transcribe_openai_whisper(wav = None, *, model_size, language, weak_pc):
    import whisper
    size = 'tiny' if weak_pc else model_size
    logger.info('openai-whisper model=%s', size)
    model = whisper.load_model(size)
    kwargs = {
        'fp16': False }
    if language:
        kwargs['language'] = language
# WARNING: Decompyle incomplete


def transcribe_to_srt(media_path = None, out_srt = None, *, work_dir, model_size, language, weak_pc, provider):
    media_path = Path(media_path)
    if not media_path.is_file():
        return SttResult(False, None, message = f'''Không thấy media: {media_path}''')
    work = Path(work_dir) if None else media_path.parent / '_stt_work'
    work.mkdir(parents = True, exist_ok = True)
    wav = work / f'''{media_path.stem}_16k.wav'''
    out = Path(out_srt) if out_srt else work / f'''{media_path.stem}.srt'''
    if provider == 'ElevenLabs':
        
        try:
            elevenlabs_transcribe_to_srt = elevenlabs_transcribe_to_srt
            import app.services.cloud_voice
            (srt_path, count, detected) = elevenlabs_transcribe_to_srt(media_path, out, language = language)
            return SttResult(True, srt_path, n_cues = count, engine = 'elevenlabs-scribe_v2', language = detected, message = f'''STT {count} cues → {srt_path.name} (ElevenLabs Scribe)''')
            if provider in frozenset({'CapCut STT', 'CapCut', 'capcut'}):
                
                try:
                    capcut_transcribe_to_srt = capcut_transcribe_to_srt
                    import app.services.capcut_tts_engine
                    (srt_path, count, detected) = capcut_transcribe_to_srt(media_path, out, language = language, work_dir = work / 'capcut')
                    return SttResult(True, srt_path, n_cues = count, engine = 'capcut-asr', language = detected, message = f'''STT {count} cues → {srt_path.name} (CapCut ASR)''')
                    
                    try:
                        extract_audio_wav(media_path, wav)
                        engine = ''
                        
                        try:
                            import faster_whisper
                            (cues, lang) = _transcribe_faster(wav, model_size = model_size, language = language, weak_pc = weak_pc)
                            engine = 'faster-whisper'
                            
                            try:
                                if not cues:
                                    return SttResult(False, None, engine = engine, message = 'Whisper không nhận được lời thoại')
                                None(cues, out)
                                return SttResult(ok = True, srt_path = out, n_cues = len(cues), engine = engine, language = lang, message = f'''STT {len(cues)} cues → {out.name} ({engine})''')
                                except Exception:
                                    e = None
                                    logger.exception('ElevenLabs STT fail')
                                    del e
                                    return None
                                    None = 
                                    del e
                                except Exception:
                                    e = None
                                    logger.exception('CapCut STT fail')
                                    del e
                                    return None
                                    None = 
                                    del e
                                except Exception:
                                    e = None
                                    del e
                                    return None
                                    None = 
                                    del e
                                except ImportError:
                                    import whisper
                                    (cues, lang) = _transcribe_openai_whisper(wav, model_size = model_size, language = language, weak_pc = weak_pc)
                                    engine = 'openai-whisper'
                                except ImportError:
                                    
                                    try:
                                        return 
                                        
                                        try:
                                            continue
                                            
                                            try:
                                                pass
                                            except Exception:
                                                logger.exception('STT fail')
                                                del e
                                                return None
                                                None = 
                                                del e










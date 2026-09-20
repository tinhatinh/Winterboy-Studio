# Source Generated with Decompyle++
# File: audio_sync_engine.pyc (Python 3.12)

'''
AudioSyncEngine — Khâu 2: đồng bộ TTS với timeline SRT, chống đè giọng.

Thuật toán (mỗi block SRT):
    D_sub   = End - Start  (giây)
    D_voice = độ dài file TTS thực tế (giây)

    Nếu D_voice > D_sub:
        # Giọng dài hơn khung sub → ép nói nhanh hơn để vừa khít
        speed_rate = D_voice / D_sub
        → FFmpeg atempo (chuỗi filter nếu rate ngoài [0.5, 2.0])
    Nếu D_voice <= D_sub:
        # Giọng ngắn hơn → giữ nguyên tốc độ, pad silence cho đủ D_sub
        pad = D_sub - D_voice

Sau khi mỗi đoạn đã = đúng D_sub:
    - Chèn silence cho khoảng trống giữa các cue (và từ 0 → cue đầu)
    - Concat → final_voice.mp3  (align theo timeline video)

Giai đoạn này: TTS có thể inject bằng mock (generate tone/silence).
Bước 3: thay mock bằng Edge-TTS / Azure / Google.
'''
from __future__ import annotations
import hashlib
import json
import logging
import math
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any, Callable, Protocol
from app.services.artifact_manifest import DependencyManifest, stable_fingerprint
logger = logging.getLogger(__name__)

def is_speakable_text(text = None):
    '''Kiểm tra xem văn bản có chứa ít nhất một ký tự chữ hoặc số để phát âm hay không.'''
    if not text:
        return False
    cleaned = re.sub('<[^>]+>', ' ', text)
    cleaned = re.sub('\\{[^}]*\\}', ' ', cleaned)
    return bool(re.search('[\\w\\d]', cleaned, flags = re.UNICODE))

TtsProgressCb = Callable[([
    float,
    str], None)]
_raw_cache_locks_guard = threading.Lock()
_raw_cache_locks: 'dict[str, threading.Lock]' = { }

def _raw_cache_lock(key = None):
    _raw_cache_locks_guard
    lock = _raw_cache_locks.get(key)
# WARNING: Decompyle incomplete

SubBlock = <NODE:12>()
SegmentReport = <NODE:12>()
SyncResult = <NODE:12>()

class TTSFunc(Protocol):
    
    def __call__(self = None, text = None, out_path = None):
        pass



def _which(name = dataclass):
    p = shutil.which(name)
    if p:
        return p
    ff = None.which('ffmpeg')
    if ff:
        cand = Path(ff).with_name(name + '.exe' if not name.endswith('.exe') else '')
        if cand.exists():
            return str(cand)
        cand2 = None(ff).with_name(name + '.exe')
        if cand2.exists():
            return str(cand2)
        raise None(f'''Không tìm thấy {name} trong PATH''')


def _run(cmd = None, timeout = None):
    logger.debug('FFmpeg CMD: %s', ' '.join(cmd[:14]) + '...' if len(cmd) > 14 else '')
    p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', timeout = timeout, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0:
        if not p.stderr:
            p.stderr
            if not p.stdout:
                p.stdout
        err = ''[-800:]
        raise RuntimeError(f'''FFmpeg lỗi (code={p.returncode}): {err}''')


def probe_duration_s(path = None, ffprobe_bin = None):
    '''Đo D_voice (giây) bằng ffprobe.'''
    if not ffprobe_bin:
        ffprobe_bin
    ffprobe = _which('ffprobe')
    cmd = [
        ffprobe,
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        str(path)]
    p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0:
        raise RuntimeError(f'''ffprobe lỗi: {p.stderr[-400:]}''')
    if not p.stdout:
        p.stdout
    if not '0'.strip():
        '0'.strip()
    return max(0, float(0))


def build_atempo_filters(speed_rate = None):
    '''
    FFmpeg atempo chỉ chấp nhận [0.5, 100] (thường an toàn 0.5–2.0 mỗi bậc).
    speed_rate > 1  → nói NHANH hơn (rút ngắn audio).
    speed_rate < 1  → nói CHẬM hơn.

    Công thức user (trường hợp đè giọng):
        speed_rate = D_voice / D_sub   (> 1 khi voice dài hơn sub)
    '''
    if speed_rate <= 0:
        raise ValueError('speed_rate phải > 0')
    factors = []
    r = float(speed_rate)
    if r > 2:
        factors.append(2)
        r /= 2
        if r > 2:
            continue
    if r < 0.5:
        factors.append(0.5)
        r /= 0.5
        if r < 0.5:
            continue
    factors.append(max(0.5, min(2, r)))
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(factors())


def load_srt_blocks(srt_path = None):
    '''
    Đọc SRT bằng pysrt.
    N = số block (bắt buộc giữ nguyên khi dịch — dùng ở Bước 3 / Gemini).
    '''
    import pysrt
    subs = pysrt.open(str(srt_path), encoding = 'utf-8')
    blocks = []
    for i, item in enumerate(subs):
        start_s = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
        end_s = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
        if not item.text:
            item.text
        text = ''.replace('\n', ' ').strip()
        if not text:
            continue
        if end_s <= start_s:
            end_s = start_s + 0.3
        blocks.append(SubBlock(index = i, start_s = start_s, end_s = end_s, text = text))
    ordered = sorted(blocks, key = (lambda block: (block.start_s, block.end_s, block.index)))
    if ordered != blocks:
        logger.warning('SRT %s có cue không theo timestamp; đã tự sắp xếp cho TTS timeline', srt_path)
    blocks = ordered
    logger.info('SRT %s → N=%d block', srt_path, len(blocks))
    return blocks


class AudioSyncEngine:
    '''
    Engine đồng bộ TTS ↔ SRT.

    Normal mode fits every voice to its SRT slot.  ``natural_voice_sync`` is
    an explicit opt-in mode: it never speeds speech beyond ``max_speed_rate``
    and mixes any remaining tail at its original SRT timestamp, so speech may
    overlap rather than sound unnaturally fast.

    ``tts_func`` phải là provider TTS thật (Edge, CapCut, ElevenLabs hoặc Google).
    '''
    
    def __init__(self = None, work_dir = None, *, tts_func, ffmpeg_bin, ffprobe_bin, sample_rate, max_speed_rate, min_segment_s, natural_voice_sync, soft_timing_enabled, soft_max_drift_s, soft_min_gap_s, soft_max_atempo, fast_tts_workers, voice_signature, resume_metadata, resume_job_key):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents = True, exist_ok = True)
        self.seg_dir = self.work_dir / 'segments'
        self.seg_dir.mkdir(parents = True, exist_ok = True)
        if not ffmpeg_bin:
            ffmpeg_bin
        self.ffmpeg = _which('ffmpeg')
        if not ffprobe_bin:
            ffprobe_bin
        self.ffprobe = _which('ffprobe')
        self.sample_rate = sample_rate
        self.max_speed_rate = max_speed_rate
        self.min_segment_s = min_segment_s
        self.natural_voice_sync = natural_voice_sync
        self.soft_timing_enabled = soft_timing_enabled
        self.soft_max_drift_s = max(0, float(soft_max_drift_s))
        self.soft_min_gap_s = max(0, float(soft_min_gap_s))
        self.soft_max_atempo = max(1, float(soft_max_atempo))
        if not fast_tts_workers:
            fast_tts_workers
        self.fast_tts_workers = 2 if int(1) >= 2 else 1
        self.voice_signature = voice_signature
        if not resume_metadata:
            resume_metadata
        self.resume_metadata = dict({ })
        if not resume_job_key:
            resume_job_key
        requested_resume = str('').strip().casefold()
        self.resume_job_key = requested_resume if len(requested_resume) == 64 and (lambda .0: pass# WARNING: Decompyle incomplete
)(requested_resume()) else ''
    # WARNING: Decompyle incomplete

    
    def count_srt_lines(self = None, srt_path = None):
        """Trả về N — dùng cho prompt dịch 'đúng N dòng'."""
        return len(load_srt_blocks(Path(srt_path)))

    
    def _resume_identity(self = None, srt_path = None):
        '''Return stable hashes for a resumable voice job and its SRT source.'''
        srt_hash = hashlib.sha256(srt_path.read_bytes()).hexdigest()
        payload = {
            'version': 1,
            'srt_sha256': srt_hash,
            'voice_signature': self.voice_signature,
            'sample_rate': self.sample_rate,
            'max_speed_rate': self.max_speed_rate,
            'min_segment_s': self.min_segment_s,
            'natural_voice_sync': self.natural_voice_sync,
            'soft_timing_enabled': self.soft_timing_enabled,
            'soft_max_drift_s': self.soft_max_drift_s,
            'soft_min_gap_s': self.soft_min_gap_s,
            'soft_max_atempo': self.soft_max_atempo }
        if self.natural_voice_sync:
            payload['natural_sync_policy'] = 'overlap_v1'
        if self.soft_timing_enabled:
            payload['soft_timing_policy'] = 'shift_compress_report_v1'
        stable = json.dumps(payload, ensure_ascii = False, sort_keys = True, separators = (',', ':'))
        return (hashlib.sha256(stable.encode('utf-8')).hexdigest(), srt_hash)

    
    def _cue_dependencies(self = None, block = None, d_sub = None):
        '''Inputs that determine one fitted cue, independent of cue position/job.'''
        return {
            'version': 1,
            'voice_signature': self.voice_signature,
            'text': block.text,
            'duration_s': round(d_sub, 6),
            'sample_rate': self.sample_rate,
            'max_speed_rate': self.max_speed_rate,
            'min_segment_s': self.min_segment_s,
            'natural_voice_sync': self.natural_voice_sync,
            'soft_timing_enabled': self.soft_timing_enabled,
            'soft_max_atempo': self.soft_max_atempo }

    _read_resume_manifest = (lambda path = None, job_key = None: if not path.is_file():
{
'version': 1,
'job_key': job_key,
'completed': { } }try:
data = json.loads(path.read_text(encoding = 'utf-8'))if isinstance(data, dict) and data.get('job_key') == job_key:
entries = data.get('completed')if isinstance(entries, dict):
data{
'version': None,
'job_key': job_key,
'completed': { } }except Exception:
exc = Nonelogger.warning('Cannot read TTS resume manifest %s: %s', path, exc)exc = Nonedel exccontinueexc = Nonedel exc)()
    _write_resume_manifest = (lambda path = None, manifest = None: try:
path.parent.mkdir(parents = True, exist_ok = True)temp = path.with_suffix('.tmp')temp.write_text(json.dumps(manifest, ensure_ascii = False, indent = 2), encoding = 'utf-8')temp.replace(path)Noneexcept Exception:
exc = Nonelogger.warning('Cannot write TTS resume manifest %s: %s', path, exc)exc = Nonedel excNoneexc = Nonedel exc)()
    
    def build_voice_track(self = None, srt_path = None, output_path = None, *, align_to_timeline, progress, cancel_event, engine_label):
        '''
        Xử lý toàn bộ SRT → 1 file final_voice (mp3/wav).

        align_to_timeline=True:
            chèn silence theo khoảng trống giữa các cue (sync với video).
        align_to_timeline=False:
            chỉ concat tuần tự các đoạn đã fit D_sub (không pad gap).

        progress: callback(0..1 local, message) — từng câu TTS (ElevenLabs hay chậm).
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _normalised_tts_text(self = None, text = None):
        normalizer = getattr(self.tts_func, 'normalize_cache_text', None)
        if callable(normalizer):
            
            try:
                return str(normalizer(text))
                if not text:
                    text
                return str('')
            except Exception:
                continue


    _read_duration_meta = (lambda path = None, audio = None: try:
data = json.loads(path.read_text(encoding = 'utf-8'))if not isinstance(data, dict):
0try:
stat = audio.stat()if not data.get('audio_size'):
data.get('audio_size')if int(-1) != int(stat.st_size):
0try:
if not data.get('duration_s'):
data.get('duration_s')duration = float(0)if duration > 0:
durationNoneexcept (OSError, ValueError, TypeError, json.JSONDecodeError):
0)()
    _write_duration_meta = (lambda path = None, audio = None, duration_s = staticmethod: if duration_s <= 0:
Nonetry:
payload = {
'version': 1,
'audio_file': audio.name,
'audio_size': audio.stat().st_size,
'duration_s': round(float(duration_s), 6),
'updated_at': time.time() }temp = path.with_suffix(path.suffix + '.tmp')temp.write_text(json.dumps(payload, ensure_ascii = False, indent = 2), encoding = 'utf-8')temp.replace(path)Noneexcept OSError:
exc = Nonelogger.debug('Cannot write TTS duration metadata %s: %s', path, exc)exc = Nonedel excNoneexc = Nonedel exc)()
    _copy_atomic = (lambda source = None, target = None: target.parent.mkdir(parents = True, exist_ok = True)temp = target.with_suffix(target.suffix + f'''.{threading.get_ident()}.tmp''')shutil.copy2(source, temp)temp.replace(target))()
    
    def _prepare_raw_tts(self = None, block = None):
        '''Return provider audio plus duration, preserving every legacy cache.'''
        if not getattr(self.tts_func, 'raw_audio_suffix', '.wav'):
            getattr(self.tts_func, 'raw_audio_suffix', '.wav')
        suffix = str('.wav')
        if suffix.startswith('.') or len(suffix) > 8:
            suffix = '.wav'
        normalized = self._normalised_tts_text(block.text)
        cache_key = f'''{self.voice_signature}\x1f{normalized}'''
        raw_legacy_key = f'''{self.voice_signature}\x1f{block.text}'''
        cache_hash = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()
        legacy_sha = hashlib.sha256(raw_legacy_key.encode('utf-8')).hexdigest()
        legacy_md5 = hashlib.md5(raw_legacy_key.encode('utf-8')).hexdigest()
        persistent_dir = Path.home() / '.mumu' / 'tts_sentences'
        persistent_dir.mkdir(parents = True, exist_ok = True)
        configured_root = getattr(self.tts_func, 'tts_cache_root', None)
        cache_dir = Path(configured_root).expanduser() if configured_root else persistent_dir
        legacy_dir = Path(tempfile.gettempdir()) / 'mumu_tts_cache'
        cache_dir.mkdir(parents = True, exist_ok = True)
        meta_path = cache_dir / f'''{cache_hash}.json'''
        primary = cache_dir / f'''{cache_hash}{suffix}'''
        persistent_wav = cache_dir / f'''{cache_hash}.wav'''
        candidates = [
            primary]
        if persistent_wav != primary:
            candidates.append(persistent_wav)
        for candidate in (legacy_dir / f'''{legacy_sha}.wav''', legacy_dir / f'''{legacy_md5}.wav'''):
            if not candidate not in candidates:
                continue
            candidates.append(candidate)
        started = time.perf_counter()
        _raw_cache_lock(cache_hash)
        source = (lambda .0: pass# WARNING: Decompyle incomplete
)(candidates(), None)
    # WARNING: Decompyle incomplete

    
    def _process_one_block(self = None, block = None, d_sub = None, *, max_duration, prepared_raw):
        '''
        Áp dụng thuật toán chống đè cho 1 block.

        Trả về path file audio đã fit đúng d_sub giây.
        '''
        fitted = self.seg_dir / f'''tts_fit_{block.index:04d}.wav'''
        if not is_speakable_text(block.text):
            dur = max(0.05, float(d_sub))
            logger.info("Block #%s text không chứa từ cần đọc ('%s') → đệm silence %.2fs.", block.index, block.text, dur)
            self._make_silence(fitted, dur)
            return (fitted, SegmentReport(block.index, block.text, d_sub, 0, 'skip', pad_s = d_sub, segment_path = str(fitted)))
    # WARNING: Decompyle incomplete

    
    def _apply_soft_timing_plan(self = None, blocks = None, fitted = None, reports = ('blocks', 'list[SubBlock]', 'fitted', 'list[Path]', 'reports', 'list[SegmentReport]', 'return', 'tuple[list[SubBlock], list[Path], dict[str, Any]]')):
        '''Plan the complete voice timeline without modifying the source SRT.'''
        effective_blocks = []
        effective_paths = list(fitted)
    # WARNING: Decompyle incomplete

    _write_quality_report = (lambda path = None, payload = None: path.parent.mkdir(parents = True, exist_ok = True)temp = path.with_suffix(path.suffix + '.tmp')temp.write_text(json.dumps(payload, ensure_ascii = False, indent = 2), encoding = 'utf-8')temp.replace(path)path)()
    
    def _apply_atempo(self = None, src = None, dst = None, speed_rate = None, *, exact_duration):
        '''Tăng/giảm tốc độ audio bằng chuỗi atempo (không đổi pitch mạnh như asetrate).'''
        filt = build_atempo_filters(speed_rate)
    # WARNING: Decompyle incomplete

    
    def _pad_silence_end(self = None, src = None, dst = None, pad_s = None, *, exact_duration):
        '''Ghép silence vào CUỐI audio (apad / concat).'''
        filt = f'''apad=pad_dur={pad_s:.4f}'''
    # WARNING: Decompyle incomplete

    
    def _force_exact_duration(self = None, path = None, duration_s = None):
        '''
        Ép file đúng duration_s:
        - dài hơn → atrim
        - ngắn hơn → apad
        Ghi đè path (qua file temp).
        '''
        tmp = path.with_suffix('.exact.wav')
        cmd = [
            self.ffmpeg,
            '-y',
            '-i',
            str(path),
            '-af',
            f'''atrim=0:{duration_s:.4f},apad=whole_dur={duration_s:.4f}''',
            '-ar',
            str(self.sample_rate),
            '-ac',
            '1',
            str(tmp)]
        _run(cmd)
        tmp.replace(path)

    
    def _make_silence(self = None, path = None, duration_s = None):
        cmd = [
            self.ffmpeg,
            '-y',
            '-f',
            'lavfi',
            '-i',
            f'''anullsrc=r={self.sample_rate}:cl=mono''',
            '-t',
            f'''{duration_s:.4f}''',
            str(path)]
        _run(cmd)

    
    def _copy_audio(self = None, src = None, dst = None, *, exact_duration):
        cmd = [
            self.ffmpeg,
            '-y',
            '-i',
            str(src)]
    # WARNING: Decompyle incomplete

    
    def _concat_sequential(self = None, parts = None, output = None):
        '''Nối tuần tự (không pad gap timeline).'''
        list_file = self.work_dir / 'concat_list.txt'
        lines = []
        for p in parts:
            ap = str(p.resolve()).replace("'", "'\\''")
            lines.append(f'''file \'{ap}\'''')
        list_file.write_text('\n'.join(lines), encoding = 'utf-8')
        return self._ffmpeg_concat_list(list_file, output)

    
    def _mix_with_timeline_overlap(self = None, blocks = None, fitted = None, output = None, *, cache_dir, artifact_manifest):
        '''Mix every fitted cue at its original SRT start time.

        Used only by the opt-in natural voice mode.  Unlike concat, this is a
        real timeline mix: a sentence that remains longer after the 1.35x cap
        continues naturally and overlaps the following sentence if necessary.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _mix_timeline_batch(self = None, assets = None, output = None, *, origin_s):
        '''Mix a bounded group of timeline assets using timestamps relative to origin.'''
        if not assets:
            raise RuntimeError('Không có audio trong nhóm trộn timeline')
        cmd = [
            self.ffmpeg,
            '-y']
        for audio, _start_s in assets:
            cmd += [
                '-i',
                str(audio)]
        filter_parts = []
        labels = []
        for _audio, start_s in enumerate(assets):
            delay_ms = max(0, int(round((start_s - origin_s) * 1000)))
            label = f'''nv{index}'''
            filter_parts.append(f'''[{index}:a]adelay={delay_ms}:all=1,aresample={self.sample_rate}[{label}]''')
            labels.append(f'''[{label}]''')
        filter_parts.append(''.join(labels) + f'''amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.95[aout]''')
        codec = [
            '-c:a',
            'pcm_s16le'] if output.suffix.lower() == '.wav' else [
            '-c:a',
            'libmp3lame',
            '-b:a',
            '192k']
        cmd += cmd[str(output)]
        _run(cmd)

    
    def _concat_with_timeline_gaps(self = None, blocks = None, fitted = None, output = None, *, cache_dir, artifact_manifest):
        '''
        Chèn silence:
          - 0 → start block[0]
          - end[i] → start[i+1]
        để final_voice align timestamp video.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _ffmpeg_concat_list(self = None, list_file = None, output = None):
        out = Path(output)
        if out.suffix.lower() == '.wav':
            codec = [
                '-c',
                'copy']
        else:
            codec = [
                '-c:a',
                'libmp3lame',
                '-b:a',
                '192k']
        cmd = None[str(out)]
        
        try:
            _run(cmd)
            return out
        except RuntimeError:
            cmd = [
                self.ffmpeg,
                '-y',
                '-f',
                'concat',
                '-safe',
                '0',
                '-i',
                str(list_file),
                '-ar',
                str(self.sample_rate),
                '-ac',
                '1',
                '-c:a',
                'libmp3lame',
                '-b:a',
                '192k',
                str(out.with_suffix('.mp3'))]
            _run(cmd)
            out = out.with_suffix('.mp3')
            return out




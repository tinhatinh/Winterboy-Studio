# -*- coding: utf-8 -*-
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


def is_speakable_text(text: str) -> bool:
    '''Kiểm tra xem văn bản có chứa ít nhất một ký tự chữ hoặc số để phát âm hay không.'''
    if not text:
        return False
    cleaned = re.sub('<[^>]+>', ' ', text)
    cleaned = re.sub('\\{[^}]*\\}', ' ', cleaned)
    return bool(re.search('[\\w\\d]', cleaned, flags=re.UNICODE))


TtsProgressCb = Callable[[float, str], None]

_raw_cache_locks_guard = threading.Lock()
_raw_cache_locks: 'dict[str, threading.Lock]' = {}


def _raw_cache_lock(key: str) -> threading.Lock:
    with _raw_cache_locks_guard:
        lock = _raw_cache_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _raw_cache_locks[key] = lock
        return lock


@dataclass
class SubBlock:
    '''Một dòng / block phụ đề sau khi parse SRT.'''
    index: int
    start_s: float
    end_s: float
    text: str

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_s - self.start_s)


@dataclass
class SegmentReport:
    '''Báo cáo xử lý 1 block (debug / UI).'''
    index: int
    text: str
    d_sub: float
    d_voice: float
    mode: str
    speed_rate: float | None = None
    pad_s: float | None = None
    segment_path: str | None = None
    error: str | None = None
    effective_start_s: float | None = None
    shift_s: float = 0.0
    overlap_s: float = 0.0


@dataclass
class SyncResult:
    '''Kết quả toàn bộ engine.'''
    ok: bool
    final_voice_path: Path | None
    n_blocks: int
    reports: list[SegmentReport] = field(default_factory=list)
    message: str = ''
    total_duration_s: float = 0.0
    quality_report_path: Path | None = None


class TTSFunc(Protocol):
    '''Chữ ký hàm TTS: (text, out_path) -> Path file audio.'''

    def __call__(self, text: str, out_path: Path) -> Path:
        ...


def _which(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    ff = shutil.which('ffmpeg')
    if ff:
        cand = Path(ff).with_name(name + ('' if name.endswith('.exe') else '.exe'))
        if cand.exists():
            return str(cand)
        cand2 = Path(ff).with_name(name + '.exe')
        if cand2.exists():
            return str(cand2)
    raise FileNotFoundError(f'Không tìm thấy {name} trong PATH')


def _run(cmd: list[str], timeout: int = 600) -> None:
    logger.debug('FFmpeg CMD: %s', ' '.join(cmd[:14]) + ('...' if len(cmd) > 14 else ''))
    p = subprocess.run(cmd,
                       capture_output=True,
                       text=True,
                       encoding='utf-8',
                       errors='replace',
                       timeout=timeout,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0:
        err = (p.stderr or p.stdout or '')[:-800]
        raise RuntimeError(f'FFmpeg lỗi (code={p.returncode}): {err}')


def probe_duration_s(path: Path, ffprobe_bin: str | None = None) -> float:
    '''Đo D_voice (giây) bằng ffprobe.'''
    ffprobe = ffprobe_bin or _which('ffprobe')
    cmd = [
        ffprobe,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(path)]
    p = subprocess.run(cmd,
                       capture_output=True,
                       text=True,
                       encoding='utf-8',
                       errors='replace',
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode != 0:
        raise RuntimeError(f'ffprobe lỗi: {p.stderr[-400:]}')
    return max(0.0, float(((p.stdout or '0').strip() or 0)))


def build_atempo_filters(speed_rate: float) -> str:
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
    while r > 2.0:
        factors.append(2.0)
        r /= 2.0
    while r < 0.5:
        factors.append(0.5)
        r /= 0.5
    factors.append(max(0.5, min(2.0, r)))
    return ','.join(f'atempo={f:.6f}' for f in factors)


def load_srt_blocks(srt_path: Path) -> list[SubBlock]:
    '''
    Đọc SRT bằng pysrt.
    N = số block (bắt buộc giữ nguyên khi dịch — dùng ở Bước 3 / Gemini).
    '''
    import pysrt
    subs = pysrt.open(str(srt_path), encoding='utf-8')
    blocks: list[SubBlock] = []
    for i, item in enumerate(subs):
        start_s = (item.start.hours * 3600 + item.start.minutes * 60
                   + item.start.seconds + item.start.milliseconds / 1000.0)
        end_s = (item.end.hours * 3600 + item.end.minutes * 60
                 + item.end.seconds + item.end.milliseconds / 1000.0)
        text = (item.text or '').replace('\n', ' ').strip()
        if not text:
            continue
        if end_s <= start_s:
            # cue 0 độ dài vẫn phải có chỗ đứng trên timeline
            end_s = start_s + 0.3
        blocks.append(SubBlock(index=i, start_s=start_s, end_s=end_s, text=text))
    ordered = sorted(blocks, key=lambda block: (block.start_s, block.end_s, block.index))
    if ordered != blocks:
        logger.warning('SRT %s có cue không theo timestamp; đã tự sắp xếp cho TTS timeline',
                       srt_path)
    blocks = ordered
    logger.info('SRT %s → N=%d block', srt_path, len(blocks))
    return blocks


class AudioSyncEngine:
    '''Engine đồng bộ TTS ↔ SRT.

Normal mode fits every voice to its SRT slot.  ``natural_voice_sync`` is
an explicit opt-in mode: it never speeds speech beyond ``max_speed_rate``
and mixes any remaining tail at its original SRT timestamp, so speech may
overlap rather than sound unnaturally fast.

``tts_func`` phải là provider TTS thật (Edge, CapCut, ElevenLabs hoặc Google).'''

    def __init__(self, work_dir: str | Path, *,
                 tts_func: 'Callable[[str, Path], Path] | None' = None,
                 ffmpeg_bin: str | None = None,
                 ffprobe_bin: str | None = None,
                 sample_rate: int = 44100,
                 max_speed_rate: float = 1.85,
                 min_segment_s: float = 0.08,
                 natural_voice_sync: bool = False,
                 soft_timing_enabled: bool = False,
                 soft_max_drift_s: float = 1.5,
                 soft_min_gap_s: float = 0.12,
                 soft_max_atempo: float = 1.1,
                 fast_tts_workers: int = 1,
                 voice_signature: str = '',
                 resume_metadata: 'dict[str, Any] | None' = None,
                 resume_job_key: str = '') -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.seg_dir = self.work_dir / 'segments'
        self.seg_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = ffmpeg_bin or _which('ffmpeg')
        self.ffprobe = ffprobe_bin or _which('ffprobe')
        self.sample_rate = sample_rate
        self.max_speed_rate = max_speed_rate
        self.min_segment_s = min_segment_s
        self.natural_voice_sync = natural_voice_sync
        self.soft_timing_enabled = soft_timing_enabled
        self.soft_max_drift_s = max(0.0, float(soft_max_drift_s))
        self.soft_min_gap_s = max(0.0, float(soft_min_gap_s))
        self.soft_max_atempo = max(1.0, float(soft_max_atempo))
        self.fast_tts_workers = 2 if int(fast_tts_workers or 1) >= 2 else 1
        self.voice_signature = voice_signature
        self.resume_metadata = dict(resume_metadata or {})
        requested_resume = str(resume_job_key or '').strip().casefold()
        self.resume_job_key = (
            requested_resume
            if len(requested_resume) == 64
            and all(ch in '0123456789abcdef' for ch in requested_resume)
            else '')
        if tts_func is None:
            raise ValueError('AudioSyncEngine cần tts_func của một provider TTS thật')
        self.tts_func = tts_func

    def count_srt_lines(self, srt_path: str | Path) -> int:
        """Trả về N — dùng cho prompt dịch 'đúng N dòng'."""
        return len(load_srt_blocks(Path(srt_path)))

    def _resume_identity(self, srt_path: Path) -> 'tuple[str, str]':
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
            'soft_max_atempo': self.soft_max_atempo,
        }
        if self.natural_voice_sync:
            payload['natural_sync_policy'] = 'overlap_v1'
        if self.soft_timing_enabled:
            payload['soft_timing_policy'] = 'shift_compress_report_v1'
        stable = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                            separators=(',', ':'))
        return (hashlib.sha256(stable.encode('utf-8')).hexdigest(), srt_hash)

    def _cue_dependencies(self, block: SubBlock, d_sub: float) -> 'dict[str, Any]':
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
            'soft_max_atempo': self.soft_max_atempo,
        }

    @staticmethod
    def _read_resume_manifest(path: Path, job_key: str) -> 'dict[str, Any]':
        try:
            if not path.is_file():
                return {'version': 1, 'job_key': job_key, 'completed': {}}
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and data.get('job_key') == job_key:
                entries = data.get('completed')
                if isinstance(entries, dict):
                    return data
        except Exception as exc:                       # noqa: BLE001 - manifest phụ
            logger.warning('Cannot read TTS resume manifest %s: %s', path, exc)
        return {'version': 1, 'job_key': job_key, 'completed': {}}

    @staticmethod
    def _write_resume_manifest(path: Path, manifest: 'dict[str, Any]') -> None:
        '''Atomically persist completed cues so a cancelled job can resume.'''
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                            encoding='utf-8')
            temp.replace(path)
        except Exception as exc:                       # noqa: BLE001 - manifest phụ
            logger.warning('Cannot write TTS resume manifest %s: %s', path, exc)

    @staticmethod
    def _read_duration_meta(path: Path, audio: Path) -> float:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return 0.0
            stat = audio.stat()
            if int(data.get('audio_size') or -1) != int(stat.st_size):
                return 0.0
            duration = float(data.get('duration_s') or 0.0)
            return duration if duration > 0 else 0.0
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0.0

    @staticmethod
    def _write_duration_meta(path: Path, audio: Path, duration_s: float) -> None:
        if duration_s <= 0:
            return
        try:
            payload = {
                'version': 1,
                'audio_file': audio.name,
                'audio_size': audio.stat().st_size,
                'duration_s': round(float(duration_s), 6),
                'updated_at': time.time(),
            }
            temp = path.with_suffix(path.suffix + '.tmp')
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding='utf-8')
            temp.replace(path)
        except OSError as exc:                         # noqa: BLE001 - cache phụ
            logger.debug('Cannot write TTS duration metadata %s: %s', path, exc)

    @staticmethod
    def _copy_atomic(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + f'.{threading.get_ident()}.tmp')
        shutil.copy2(source, temp)
        temp.replace(target)

    def _normalised_tts_text(self, text: str) -> str:
        normalizer = getattr(self.tts_func, 'normalize_cache_text', None)
        if callable(normalizer):
            try:
                return str(normalizer(text))
            except Exception:                          # noqa: BLE001 - fallback chữ gốc
                pass
        return str(text or '')

    def _prepare_raw_tts(self, block: SubBlock) -> 'tuple[Path, float]':
        '''Return provider audio plus duration, preserving every legacy cache.'''
        suffix = str(getattr(self.tts_func, 'raw_audio_suffix', '.wav') or '.wav')
        if suffix.startswith('.') or len(suffix) > 8:
            suffix = '.wav'
        normalized = self._normalised_tts_text(block.text)
        cache_key = f'{self.voice_signature}\x1f{normalized}'
        raw_legacy_key = f'{self.voice_signature}\x1f{block.text}'
        cache_hash = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()
        legacy_sha = hashlib.sha256(raw_legacy_key.encode('utf-8')).hexdigest()
        legacy_md5 = hashlib.md5(raw_legacy_key.encode('utf-8')).hexdigest()

        persistent_dir = Path.home() / '.winterboy' / 'tts_sentences'
        persistent_dir.mkdir(parents=True, exist_ok=True)
        configured_root = getattr(self.tts_func, 'tts_cache_root', None)
        cache_dir = (Path(configured_root).expanduser()
                     if configured_root else persistent_dir)
        legacy_dir = Path(tempfile.gettempdir()) / 'winterboy_tts_cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        meta_path = cache_dir / f'{cache_hash}.json'
        primary = cache_dir / f'{cache_hash}{suffix}'
        persistent_wav = cache_dir / f'{cache_hash}.wav'
        candidates = [primary]
        if persistent_wav != primary:
            candidates.append(persistent_wav)
        for candidate in (legacy_dir / f'{legacy_sha}.wav', legacy_dir / f'{legacy_md5}.wav'):
            if candidate not in candidates:
                candidates.append(candidate)

        started = time.perf_counter()
        with _raw_cache_lock(cache_hash):
            source = next((p for p in candidates
                           if p.is_file() and p.stat().st_size > 100), None)
            if source is not None:
                raw_tts = self.seg_dir / f'tts_raw_{block.index:04d}{source.suffix.lower()}'
                shutil.copy2(source, raw_tts)
                duration = self._read_duration_meta(meta_path, source)
                if duration <= 0:
                    duration = probe_duration_s(raw_tts, self.ffprobe)
                    self._write_duration_meta(meta_path, source, duration)
                persistent_target = cache_dir / f'{cache_hash}{source.suffix.lower()}'
                if source != persistent_target and not persistent_target.exists():
                    try:
                        self._copy_atomic(source, persistent_target)
                        self._write_duration_meta(meta_path, persistent_target, duration)
                    except OSError:
                        pass
                logger.info('TTS raw cache hit block=%s format=%s duration=%.3fs lookup=%.0fms',
                            block.index, source.suffix.lower(), duration,
                            (time.perf_counter() - started) * 1000)
                return raw_tts, duration

            raw_tts = self.seg_dir / f'tts_raw_{block.index:04d}{suffix}'
            if not is_speakable_text(block.text):
                logger.info("Block #%s text không chứa từ cần đọc ('%s') → sinh silence.",
                            block.index, block.text)
                self._make_silence(raw_tts, max(0.1, min(block.duration_s, 0.5)))
                duration = probe_duration_s(raw_tts, self.ffprobe)
                return raw_tts, duration

            generated = Path(self.tts_func(block.text, raw_tts))
            if generated.is_file() and generated.resolve() != raw_tts.resolve():
                raw_tts = generated
            if not raw_tts.is_file() or raw_tts.stat().st_size <= 100:
                raise RuntimeError(f'TTS không tạo được audio hợp lệ: {raw_tts}')
            duration = probe_duration_s(raw_tts, self.ffprobe)
            if duration <= 0:
                raise RuntimeError(f'Không đo được thời lượng TTS: {raw_tts}')
            stored = cache_dir / f'{cache_hash}{raw_tts.suffix.lower()}'
            try:
                self._copy_atomic(raw_tts, stored)
                self._write_duration_meta(meta_path, stored, duration)
            except OSError as exc:                     # noqa: BLE001 - cache phụ
                logger.debug('Cannot persist raw TTS cache %s: %s', stored, exc)
            logger.info('TTS raw generated block=%s format=%s duration=%.3fs total=%.2fs',
                        block.index, raw_tts.suffix.lower(), duration,
                        time.perf_counter() - started)
            return raw_tts, duration

    def _process_one_block(self, block: SubBlock, d_sub: float, *,
                           max_duration: float | None = None,
                           prepared_raw: 'tuple[Path, float] | Future[tuple[Path, float]] | None' = None,
                           ) -> 'tuple[Path, SegmentReport]':
        '''
        Áp dụng thuật toán chống đè cho 1 block.

        Trả về path file audio đã fit đúng d_sub giây.
        '''
        fitted = self.seg_dir / f'tts_fit_{block.index:04d}.wav'

        # Block chỉ có ký tự không đọc được → giữ chỗ bằng silence, không gọi TTS
        if not is_speakable_text(block.text):
            dur = max(0.05, float(d_sub))
            logger.info("Block #%s text không chứa từ cần đọc ('%s') → đệm silence %.2fs.",
                        block.index, block.text, dur)
            self._make_silence(fitted, dur)
            return fitted, SegmentReport(block.index, block.text, d_sub, 0.0, 'skip',
                                         pad_s=d_sub, segment_path=str(fitted))
        try:
            if isinstance(prepared_raw, Future):
                raw_tts, d_voice = prepared_raw.result()
            elif prepared_raw is not None:
                raw_tts, d_voice = prepared_raw
            else:
                raw_tts, d_voice = self._prepare_raw_tts(block)
        except Exception as e:
            if bool(getattr(self.tts_func, 'no_silence_on_error', False)):
                raise
            err = str(e)
            logger.warning('Block #%s TTS fail → silence %.2fs: %s | text=%.60s',
                           block.index, d_sub, err, block.text)
            self._make_silence(fitted, d_sub)
            return fitted, SegmentReport(block.index, block.text, d_sub, 0.0, 'skip',
                                         pad_s=d_sub, segment_path=str(fitted), error=err)

        if d_voice <= 0:
            self._make_silence(fitted, d_sub)
            return fitted, SegmentReport(block.index, block.text, d_sub, 0.0, 'skip',
                                         pad_s=d_sub, segment_path=str(fitted))

        if self.soft_timing_enabled:
            # Soft timing: giữ nguyên tốc độ tự nhiên, việc đẩy/trễ do _apply_soft_timing_plan
            self._copy_audio(raw_tts, fitted)
            actual = probe_duration_s(fitted, self.ffprobe) or d_voice
            logger.info('Block #%s SOFT source=%.3fs · slot=%.3fs | %s',
                        block.index, actual, d_sub, block.text[:40])
            return fitted, SegmentReport(index=block.index, text=block.text, d_sub=d_sub,
                                         d_voice=actual, mode='soft', speed_rate=1.0,
                                         segment_path=str(fitted))

        eps = 0.02
        # Bản đã phát hành không đọc ``max_duration`` trong thân hàm (chữ ký giữ nguyên)
        target_duration = d_sub

        if d_voice > target_duration + eps:
            speed_rate = d_voice / target_duration
            applied = min(speed_rate, self.max_speed_rate)
            if applied < speed_rate:
                logger.warning('Block #%s: needs %.3fx but cue is %.3fs; clamp → %.3fx',
                               block.index, speed_rate, target_duration, applied)
            keep_tail_for_overlap = (self.natural_voice_sync
                                     and applied < speed_rate)
            self._apply_atempo(raw_tts, fitted, applied,
                               exact_duration=None if keep_tail_for_overlap else target_duration)
            fitted_duration = target_duration
            if keep_tail_for_overlap:
                fitted_duration = probe_duration_s(fitted, self.ffprobe)
                if fitted_duration <= 0:
                    fitted_duration = d_voice / max(applied, 0.01)
            report = SegmentReport(index=block.index, text=block.text,
                                   d_sub=fitted_duration, d_voice=d_voice, mode='atempo',
                                   speed_rate=applied, segment_path=str(fitted))
            if keep_tail_for_overlap:
                logger.info('Block #%s NATURAL OVERLAP rate=%.3f | D_voice=%.3f → audio=%.3fs (cue=%.3fs) | %s',
                            block.index, applied, d_voice, fitted_duration,
                            target_duration, block.text[:40])
            else:
                logger.info('Block #%s ATEMPO rate=%.3f | D_voice=%.3f → slot=%.3f | %s',
                            block.index, applied, d_voice, target_duration, block.text[:40])
            return fitted, report

        pad_s = max(0.0, d_sub - d_voice)
        if pad_s > eps:
            self._pad_silence_end(raw_tts, fitted, pad_s, exact_duration=d_sub)
        else:
            self._copy_audio(raw_tts, fitted, exact_duration=d_sub)
        report = SegmentReport(index=block.index, text=block.text, d_sub=d_sub,
                               d_voice=d_voice, mode='pad', pad_s=pad_s,
                               segment_path=str(fitted))
        logger.info('Block #%s PAD silence=%.3fs | D_voice=%.3f → D_sub=%.3f | %s',
                    block.index, pad_s, d_voice, d_sub, block.text[:40])
        return fitted, report

    def _apply_soft_timing_plan(self, blocks: 'list[SubBlock]', fitted: 'list[Path]',
                                reports: 'list[SegmentReport]'
                                ) -> 'tuple[list[SubBlock], list[Path], dict[str, Any]]':
        '''Plan the complete voice timeline without modifying the source SRT.'''
        effective_blocks: list[SubBlock] = []
        effective_paths = list(fitted)
        durations = [max(0.0, probe_duration_s(path, self.ffprobe)) for path in fitted]
        prev_end = float('-inf')
        shifted = compressed = overlapped = 0
        max_shift, total_overlap = 0.0, 0.0
        issues: list[dict[str, Any]] = []

        for i, (block, duration) in enumerate(zip(blocks, durations)):
            natural_start = block.start_s
            start = max(natural_start, prev_end + self.soft_min_gap_s)
            start = min(start, natural_start + self.soft_max_drift_s)
            shift = max(0.0, start - natural_start)
            overlap = max(0.0, prev_end + self.soft_min_gap_s - start)

            atempo = 1.0
            if duration > 0.0 and i + 1 < len(blocks):
                next_start = blocks[i + 1].start_s
                latest_end = next_start + self.soft_max_drift_s - self.soft_min_gap_s
                available = latest_end - start
                if available > 0.0 and duration > available:
                    wanted = duration / available
                    if wanted >= 1.02:
                        atempo = min(self.soft_max_atempo, wanted)
            if atempo > 1.0001 and reports[i].mode != 'skip':
                destination = self.seg_dir / f'tts_soft_{block.index:04d}.wav'
                self._apply_atempo(effective_paths[i], destination, atempo)
                effective_paths[i] = destination
                duration = probe_duration_s(destination, self.ffprobe) or duration / atempo
                compressed += 1
                reports[i].mode = 'atempo'
                reports[i].speed_rate = atempo

            if shift > 0.05:
                shifted += 1
                max_shift = max(max_shift, shift)
            if overlap > 0.01:
                overlapped += 1
                total_overlap += overlap

            reports[i].effective_start_s = start
            reports[i].shift_s = shift
            reports[i].overlap_s = overlap
            reports[i].segment_path = str(effective_paths[i])
            issue: dict[str, Any] = {}
            if shift > 0.05:
                issue['shift_s'] = round(shift, 3)
            if atempo > 1.0001:
                issue['atempo'] = round(atempo, 4)
            if overlap > 0.01:
                issue['overlap_s'] = round(overlap, 3)
            if issue:
                issue.update({'index': block.index, 'text': block.text})
                issues.append(issue)

            effective_blocks.append(
                SubBlock(index=block.index,
                         start_s=start,
                         end_s=start + duration,
                         text=block.text))
            prev_end = max(prev_end, start + duration)

        report = {
            'version': 1,
            'mode': 'soft_timing',
            'source_srt_unchanged': True,
            'settings': {
                'max_drift_s': self.soft_max_drift_s,
                'min_gap_s': self.soft_min_gap_s,
                'max_atempo': self.soft_max_atempo,
            },
            'summary': {
                'segments_total': len(blocks),
                'segments_shifted': shifted,
                'max_shift_s': round(max_shift, 3),
                'segments_compressed': compressed,
                'segments_overlapped': overlapped,
                'total_overlap_s': round(total_overlap, 3),
                'tts_failed': sum(1 for item in reports if item.mode == 'skip'),
            },
            'issues': issues,
        }
        logger.info('Soft Timing · total=%d shifted=%d compressed=%d overlap=%d (%.3fs)',
                    len(blocks), shifted, compressed, overlapped, total_overlap)
        return effective_blocks, effective_paths, report

    @staticmethod
    def _write_quality_report(path: Path, payload: 'dict[str, Any]') -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(path)
        return path

    def _apply_atempo(self, src: Path, dst: Path, speed_rate: float, *,
                      exact_duration: float | None = None) -> None:
        '''Tăng/giảm tốc độ audio bằng chuỗi atempo (không đổi pitch mạnh như asetrate).'''
        filt = build_atempo_filters(speed_rate)
        if exact_duration is not None:
            filt += (f',atrim=0:{exact_duration:.4f}'
                     f',apad=whole_dur={exact_duration:.4f}')
        cmd = [
            self.ffmpeg, '-y', '-i', str(src),
            '-filter:a', filt,
            '-ar', str(self.sample_rate), '-ac', '1',
            str(dst)]
        _run(cmd)

    def _pad_silence_end(self, src: Path, dst: Path, pad_s: float, *,
                         exact_duration: float | None = None) -> None:
        '''Ghép silence vào CUỐI audio (apad / concat).'''
        filt = f'apad=pad_dur={pad_s:.4f}'
        if exact_duration is not None:
            filt += (f',atrim=0:{exact_duration:.4f}'
                     f',apad=whole_dur={exact_duration:.4f}')
        cmd = [
            self.ffmpeg, '-y', '-i', str(src),
            '-af', filt,
            '-ar', str(self.sample_rate), '-ac', '1',
            str(dst)]
        _run(cmd)

    def _force_exact_duration(self, path: Path, duration_s: float) -> None:
        '''
        Ép file đúng duration_s:
        - dài hơn → atrim
        - ngắn hơn → apad
        Ghi đè path (qua file temp).
        '''
        tmp = path.with_suffix('.exact.wav')
        cmd = [
            self.ffmpeg, '-y', '-i', str(path),
            '-af', f'atrim=0:{duration_s:.4f},apad=whole_dur={duration_s:.4f}',
            '-ar', str(self.sample_rate), '-ac', '1',
            str(tmp)]
        _run(cmd)
        tmp.replace(path)

    def _make_silence(self, path: Path, duration_s: float) -> None:
        cmd = [
            self.ffmpeg, '-y',
            '-f', 'lavfi', '-i', f'anullsrc=r={self.sample_rate}:cl=mono',
            '-t', f'{duration_s:.4f}',
            str(path)]
        _run(cmd)

    def _copy_audio(self, src: Path, dst: Path, *,
                    exact_duration: float | None = None) -> None:
        cmd = [self.ffmpeg, '-y', '-i', str(src)]
        if exact_duration is not None:
            cmd.extend(['-af',
                        f'atrim=0:{exact_duration:.4f},apad=whole_dur={exact_duration:.4f}'])
        cmd.extend(['-ar', str(self.sample_rate), '-ac', '1', str(dst)])
        _run(cmd)

    def _concat_sequential(self, parts: 'list[Path]', output: Path) -> Path:
        '''Nối tuần tự (không pad gap timeline).'''
        list_file = self.work_dir / 'concat_list.txt'
        lines = []
        for p in parts:
            ap = str(p.resolve()).replace("'", "'\\''")
            lines.append(f"file '{ap}'")
        list_file.write_text('\n'.join(lines), encoding='utf-8')
        return self._ffmpeg_concat_list(list_file, output)

    def _mix_with_timeline_overlap(self, blocks: 'list[SubBlock]', fitted: 'list[Path]',
                                   output: Path, *, cache_dir: 'Path | None' = None,
                                   artifact_manifest: 'DependencyManifest | None' = None) -> Path:
        '''Mix every fitted cue at its original SRT start time.

Used only by the opt-in natural voice mode.  Unlike concat, this is a
real timeline mix: a sentence that remains longer after the 1.35x cap
continues naturally and overlaps the following sentence if necessary.
'''
        if not fitted:
            raise RuntimeError('Không có segment TTS để trộn timeline')
        # Gộp theo bậc để ffmpeg không phải mở hàng trăm input một lúc
        batch_size = 24
        assets = [(audio, max(0.0, block.start_s)) for block, audio in zip(blocks, fitted)]
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

        def cached_group(group: 'list[tuple[Path, float]]', origin_s: float,
                         fallback_output: Path) -> Path:
            if cache_dir is None or artifact_manifest is None:
                self._mix_timeline_batch(group, fallback_output, origin_s=origin_s)
                return fallback_output
            dependencies = {
                'version': 1,
                'mode': 'natural_mix_group',
                'sample_rate': self.sample_rate,
                'origin_s': round(origin_s, 6),
                'inputs': [
                    {
                        'path': str(path),
                        'start_s': round(start_s, 6),
                        'size': path.stat().st_size if path.is_file() else -1,
                        'mtime_ns': path.stat().st_mtime_ns if path.is_file() else -1,
                    }
                    for path, start_s in group
                ],
            }
            key = stable_fingerprint(dependencies)
            cached_output = cache_dir / f'mix_{key}.wav'
            record_name = f'timeline_chunk:mix:{key}'
            if artifact_manifest.valid(record_name, dependencies, output=cached_output,
                                       min_size=100):
                logger.info('TTS timeline group HIT · %s', key[:12])
                return cached_output
            self._mix_timeline_batch(group, cached_output, origin_s=origin_s)
            artifact_manifest.record(record_name, cached_output, dependencies,
                                     metadata={'inputs': len(group)}, save=False)
            return cached_output

        with tempfile.TemporaryDirectory(prefix='natural_mix_', dir=self.work_dir) as temp_name:
            temp_dir = Path(temp_name)
            level = 0
            while len(assets) > batch_size:
                next_assets: list[tuple[Path, float]] = []
                for group_index, offset in enumerate(range(0, len(assets), batch_size)):
                    group = assets[offset:offset + batch_size]
                    if len(group) == 1:
                        next_assets.append(group[0])
                        continue
                    group_start = min(start_s for _path, start_s in group)
                    group_output = temp_dir / f'level_{level:02d}_{group_index:04d}.wav'
                    group_output = cached_group(group, origin_s=group_start,
                                                fallback_output=group_output)
                    next_assets.append((group_output, group_start))
                logger.info('Natural timeline mix level %d: %d input → %d group',
                            level, len(assets), len(next_assets))
                assets = next_assets
                level += 1
            self._mix_timeline_batch(assets, output, origin_s=0.0)

        if cache_dir is not None and artifact_manifest is not None:
            artifact_manifest.save()
        logger.info('Natural voice timeline mix: %d cue, batch=%d, overlap allowed',
                    len(fitted), batch_size)
        return output

    def _mix_timeline_batch(self, assets: 'list[tuple[Path, float]]', output: Path, *,
                            origin_s: float) -> None:
        '''Mix a bounded group of timeline assets using timestamps relative to origin.'''
        if not assets:
            raise RuntimeError('Không có audio trong nhóm trộn timeline')
        cmd = [self.ffmpeg, '-y']
        for audio, _start_s in assets:
            cmd += ['-i', str(audio)]
        filter_parts = []
        labels = []
        for index, (_audio, start_s) in enumerate(assets):
            delay_ms = max(0, int(round((start_s - origin_s) * 1000)))
            label = f'nv{index}'
            filter_parts.append(
                f'[{index}:a]adelay={delay_ms}:all=1,aresample={self.sample_rate}[{label}]')
            labels.append(f'[{label}]')
        filter_parts.append(''.join(labels)
                            + f'amix=inputs={len(labels)}:normalize=0:duration=longest'
                              ',alimiter=limit=0.95[aout]')
        codec = ['-c:a', 'pcm_s16le'] if output.suffix.lower() == '.wav' else \
            ['-c:a', 'libmp3lame', '-b:a', '192k']
        cmd += ['-filter_complex', ';'.join(filter_parts), '-map', '[aout]',
                '-ar', str(self.sample_rate), '-ac', '1', *codec, str(output)]
        _run(cmd)

    def _concat_with_timeline_gaps(self, blocks: 'list[SubBlock]', fitted: 'list[Path]',
                                   output: Path, *, cache_dir: 'Path | None' = None,
                                   artifact_manifest: 'DependencyManifest | None' = None) -> Path:
        '''
        Chèn silence:
          - 0 → start block[0]
          - end[i] → start[i+1]
        để final_voice align timestamp video.
        '''
        specs: list[tuple[SubBlock, Path, float]] = []
        # cursor = vị trí trên timeline sau khi đã đặt các cue trước
        cursor = 0.0
        overlaps = 0
        for i, (block, audio) in enumerate(zip(blocks, fitted)):
            gap = block.start_s - cursor
            safe_gap = gap if gap > 0.01 else 0.0
            if safe_gap:
                cursor += gap
            elif gap < -0.01:
                # cue chồng nhau: không cắt audio, chỉ ghi nhận để báo cáo
                overlaps += 1
            specs.append((block, audio, safe_gap))
            cursor += max(self.min_segment_s, block.duration_s)
        if overlaps:
            logger.warning('SRT có %d cue chồng lên cue trước — giọng ở các cue đó bị đẩy trễ'
                           ' (không cắt bớt audio đã tạo); phần còn lại vẫn đúng nhịp.', overlaps)

        def materialize_group(group: 'list[tuple[SubBlock, Path, float]]', group_index: int,
                              destination: Path) -> Path:
            pieces: list[Path] = []
            for local_index, (_block, audio, gap) in enumerate(group):
                if gap > 0.0:
                    silence = self.seg_dir / f'gap_{group_index:04d}_{local_index:04d}.wav'
                    self._make_silence(silence, gap)
                    pieces.append(silence)
                pieces.append(audio)
            list_file = self.work_dir / f'concat_timeline_{group_index:04d}.txt'
            lines = []
            for piece in pieces:
                absolute = str(piece.resolve()).replace("'", "'\\''")
                lines.append(f"file '{absolute}'")
            list_file.write_text('\n'.join(lines), encoding='utf-8')
            return self._ffmpeg_concat_list(list_file, destination)

        group_size = 120
        if cache_dir is None or artifact_manifest is None or len(specs) <= group_size:
            return materialize_group(specs, 0, output)
        cache_dir.mkdir(parents=True, exist_ok=True)
        chunks: list[Path] = []
        for group_index, offset in enumerate(range(0, len(specs), group_size)):
            group = specs[offset:offset + group_size]
            dependencies = {
                'version': 1,
                'mode': 'timeline_gap_group',
                'sample_rate': self.sample_rate,
                'inputs': [
                    {
                        'index': block.index,
                        'start_s': round(block.start_s, 6),
                        'end_s': round(block.end_s, 6),
                        'gap_s': round(gap, 6),
                        'path': str(audio),
                        'size': audio.stat().st_size if audio.is_file() else -1,
                        'mtime_ns': audio.stat().st_mtime_ns if audio.is_file() else -1,
                    }
                    for block, audio, gap in group
                ],
            }
            key = stable_fingerprint(dependencies)
            chunk = cache_dir / f'gap_{key}.wav'
            record_name = f'timeline_chunk:gap:{key}'
            if artifact_manifest.valid(record_name, dependencies, output=chunk, min_size=100):
                logger.info('TTS timeline group HIT · %s', key[:12])
            else:
                materialize_group(group, group_index, chunk)
                artifact_manifest.record(record_name, chunk, dependencies,
                                         metadata={'inputs': len(group)}, save=False)
            chunks.append(chunk)
        artifact_manifest.save()
        final_list = self.work_dir / 'concat_timeline_chunks.txt'
        final_list.write_text('\n'.join(
            f"file '{str(chunk.resolve()).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'"
            for chunk in chunks), encoding='utf-8')
        logger.info('TTS timeline chunked concat: %d cue → %d group (size=%d)',
                    len(specs), len(chunks), group_size)
        return self._ffmpeg_concat_list(final_list, output)

    def _ffmpeg_concat_list(self, list_file: Path, output: Path) -> Path:
        out = Path(output)
        codec = ['-c', 'copy'] if out.suffix.lower() == '.wav' \
            else ['-c:a', 'libmp3lame', '-b:a', '192k']
        cmd = [self.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
               *codec, str(out)]
        try:
            _run(cmd)
        except RuntimeError:
            cmd = [self.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
                   '-ar', str(self.sample_rate), '-ac', '1',
                   '-c:a', 'libmp3lame', '-b:a', '192k', str(out.with_suffix('.mp3'))]
            _run(cmd)
            out = out.with_suffix('.mp3')
        return out

    def build_voice_track(self, srt_path: str | Path, output_path: str | Path, *,
                          align_to_timeline: bool = True,
                          progress: 'TtsProgressCb | None' = None,
                          cancel_event: 'threading.Event | None' = None,
                          engine_label: str = 'TTS') -> SyncResult:
        '''
        Xử lý toàn bộ SRT → 1 file final_voice (mp3/wav).

        align_to_timeline=True:
            chèn silence theo khoảng trống giữa các cue (sync với video).
        align_to_timeline=False:
            chỉ concat tuần tự các đoạn đã fit D_sub (không pad gap).

        progress: callback(0..1 local, message) — từng câu TTS (ElevenLabs hay chậm).
        '''
        srt_path = Path(srt_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not srt_path.exists():
            return SyncResult(False, None, 0, message=f'SRT không tồn tại: {srt_path}')
        blocks = load_srt_blocks(srt_path)
        n = len(blocks)
        if n == 0:
            return SyncResult(False, None, 0, message='SRT rỗng / không parse được block')

        resume_identity, srt_hash = self._resume_identity(srt_path)
        if self.resume_job_key:
            resume_key = self.resume_job_key
            logger.info('TTS tiếp tục dự án dang dở · mã tiến độ=%s', resume_key[:12])
        else:
            # Job mới: khoá tiến độ dẫn xuất từ chính nội dung SRT + engine
            fresh_seed = f'{resume_identity}|{self.work_dir.resolve()}'
            resume_key = hashlib.sha256(fresh_seed.encode('utf-8')).hexdigest()
            logger.info('TTS tạo nhật ký tiến độ mới · mã tiến độ=%s', resume_key[:12])
        resume_dir = Path(tempfile.gettempdir()) / 'winterboy_tts_resume' / resume_key
        resume_manifest_path = resume_dir / 'manifest.json'
        resume_manifest = self._read_resume_manifest(resume_manifest_path, resume_key)
        saved_identity = str(resume_manifest.get('resume_identity') or '')
        legacy_identity_ok = not saved_identity or resume_key == resume_identity
        if self.resume_job_key and saved_identity != resume_identity and not legacy_identity_ok:
            return SyncResult(
                False,
                None,
                n,
                # Không được trộn checkpoint của giọng/tốc độ khác
                message='Dữ liệu tiếp tục TTS không khớp SRT/giọng/tốc độ hiện tại. '
                        'Hãy nạp lại đúng dự án TTS dang dở.')

        artifact_root = Path(tempfile.gettempdir()) / 'winterboy_tts_artifacts'
        cue_artifact_dir = artifact_root / 'cues'
        cue_artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_manifest = DependencyManifest(artifact_root / 'manifest.json')
        job_artifact_manifest = DependencyManifest(resume_dir / 'artifact_manifest.json')
        resume_manifest.update({
            'version': 1,
            'job_key': resume_key,
            'srt_sha256': srt_hash,
            'resume_identity': resume_identity,
            'voice_signature': self.voice_signature,
            'source_srt': str(srt_path.resolve()),
            'total_cues': n,
            'natural_voice_sync': self.natural_voice_sync,
            'soft_timing_enabled': self.soft_timing_enabled,
            'resume_metadata': self.resume_metadata,
            'resume_metadata_version': 2,
            'status': 'in_progress',
            'updated_at': time.time(),
        })

        completed_segments = resume_manifest.setdefault('completed', {})
        self._write_resume_manifest(resume_manifest_path, resume_manifest)

        def _prog(frac: float, msg: str) -> None:
            if progress:
                try:
                    progress(max(0.0, min(1.0, frac)), msg)
                except Exception:
                    pass

        def _cancelled() -> bool:
            return bool(cancel_event is not None and cancel_event.is_set())

        reports: list[SegmentReport] = []
        fitted_paths: list[Path] = []
        t0 = time.perf_counter()
        cue_times: list[float] = []
        consecutive_provider_fail = 0
        # Provider chết ngay từ đầu → dừng sớm; chết giữa chừng → chỉ nghỉ rồi retry
        hard_fail_after = 3
        midrun_cooldown_done = False
        midrun_ok_threshold = 8

        def _is_hard_provider_fail(err: str | None) -> bool:
            e = (err or '').casefold()
            return any(
                k in e
                for k in ('shark', 'ret=-6', 'ret=1014', 'system busy', 'chặn request',
                          'unauthorized', '401', '403', 'device profile', 'capcut_device'))

        def _hard_fail_message(err: str | None) -> str:
            base = (err or 'TTS provider lỗi').strip()
            el = base.casefold()
            if 'shark' in el or 'ret=-6' in el:
                return (f'{engine_label} bị CapCut chặn (shark block / ret=-6).\n\n'
                        'Lưu ý: device_id từ CapCut Pro trên máy bạn CÓ THỂ vẫn đúng.\n'
                        'Shark là lớp chặn traffic API (rate-limit / anti-bot), không phải lỗi '
                        '«chưa lấy device».\n\nCách xử lý:\n'
                        '1) Đợi 15–30 phút rồi Render lại bằng CapCut.\n'
                        '2) Hoặc chọn provider → Edge TTS (ổn định, render ngay).\n'
                        '3) App mới sẽ tự chuyển Edge khi CapCut shark cứng.\n\n'
                        f'Chi tiết: {base}')
            if '1014' in el or 'system busy' in el:
                return (f'{engine_label}: CapCut server bận (ret=1014 system busy).\n\n'
                        'Mỗi câu đã retry nhiều lần → render sẽ rất lâu và gần như không có giọng.\n'
                        'Cách xử lý:\n1) Dừng render · mở CapCut Pro (đã login) · đợi vài phút · '
                        'Render lại.\n2) Hoặc tạm dùng Edge TTS (nhanh, ổn định).\n\n'
                        f'Chi tiết: {base}')
            return (f'{engine_label} lỗi liên tục {hard_fail_after} câu — dừng render.\n\n'
                    f'{base}')

        def _ok_count() -> int:
            return sum(1 for r in reports if r.mode != 'skip')

        resume_dirty = False
        artifact_dirty = False
        job_artifact_dirty = False
        pending_checkpoint_updates = 0
        last_checkpoint_flush = time.monotonic()

        def _flush_checkpoint_state(*, force: bool = False) -> None:
            nonlocal resume_dirty, artifact_dirty, job_artifact_dirty
            nonlocal pending_checkpoint_updates, last_checkpoint_flush
            due = (
                force
                or pending_checkpoint_updates >= 25
                or (pending_checkpoint_updates > 0
                    and time.monotonic() - last_checkpoint_flush >= 2.0))
            if not due:
                return
            if resume_dirty:
                resume_manifest['updated_at'] = time.time()
                self._write_resume_manifest(resume_manifest_path, resume_manifest)
                resume_dirty = False
            if artifact_dirty:
                artifact_manifest.save()
                artifact_dirty = False
            if job_artifact_dirty:
                job_artifact_manifest.save()
                job_artifact_dirty = False
            pending_checkpoint_updates = 0
            last_checkpoint_flush = time.monotonic()

        def _mark_checkpoint_dirty(*, resume: bool = False, artifact: bool = False,
                                   job_artifact: bool = False) -> None:
            nonlocal resume_dirty, artifact_dirty, job_artifact_dirty
            nonlocal pending_checkpoint_updates
            resume_dirty = resume_dirty or resume
            artifact_dirty = artifact_dirty or artifact
            job_artifact_dirty = job_artifact_dirty or job_artifact
            pending_checkpoint_updates += 1
            _flush_checkpoint_state()

        def _usable_audio(path: Path) -> bool:
            try:
                return path.is_file() and path.stat().st_size > 100
            except OSError:
                return False

        # Preflight: câu nào đã có checkpoint/artifact thì không gọi TTS lại
        reusable_segments: dict[int, tuple[Path, SegmentReport, str]] = {}
        repaired_manifest_entries = 0
        invalid_manifest_entries = 0
        preflight_t0 = time.perf_counter()
        for block in blocks:
            entry = completed_segments.get(str(block.index))
            if isinstance(entry, dict):
                try:
                    checkpoint = Path(str(entry.get('segment_path') or ''))
                    report_data = entry.get('report')
                    report = (SegmentReport(**report_data)
                              if isinstance(report_data, dict) else None)
                    if (report is not None
                            and report.mode != 'skip'
                            and report.text == block.text
                            and _usable_audio(checkpoint)):
                        reusable_segments[block.index] = (checkpoint, report, 'checkpoint')
                        continue
                except Exception:
                    pass
            completed_segments.pop(str(block.index), None)
            invalid_manifest_entries += 1
            resume_dirty = True

            duration = max(self.min_segment_s, block.duration_s)
            dependencies = self._cue_dependencies(block, duration)
            content_key = stable_fingerprint(dependencies)
            artifact = cue_artifact_dir / f'{content_key}.wav'
            record_name = f'cue:{content_key}'
            if not artifact_manifest.valid(record_name, dependencies, output=artifact,
                                           min_size=100):
                continue
            try:
                record = artifact_manifest.get(record_name) or {}
                metadata = record.get('metadata') or {}
                raw_report = metadata.get('report')
                report = (SegmentReport(**raw_report)
                          if isinstance(raw_report, dict)
                          else SegmentReport(
                              block.index,
                              block.text,
                              duration,
                              probe_duration_s(artifact, self.ffprobe),
                              'soft' if self.soft_timing_enabled else 'pad',
                              segment_path=str(artifact)))
                # Nội dung file mới là chuẩn: metadata có thể của lần chạy cũ
                report.index = block.index
                report.text = block.text
                report.segment_path = str(artifact)
                reusable_segments[block.index] = (artifact, report, 'artifact')
                completed_segments[str(block.index)] = {
                    'segment_path': str(artifact),
                    'report': asdict(report)}
                repaired_manifest_entries += 1
                resume_dirty = True
            except Exception as exc:
                logger.warning('Ignore invalid cue artifact %s: %s', artifact, exc)

        if resume_dirty:
            pending_checkpoint_updates = max(1, repaired_manifest_entries + invalid_manifest_entries)
            _flush_checkpoint_state(force=True)
        logger.info('TTS resume preflight · reusable=%d/%d · repaired=%d · invalid=%d · %.0fms',
                    len(reusable_segments), n, repaired_manifest_entries,
                    invalid_manifest_entries, (time.perf_counter() - preflight_t0) * 1000)
        _prog(0.0, f'{engine_label}: đã kiểm tra {len(reusable_segments)}/{n} câu có thể dùng lại')

        prefetch_executor = None
        raw_futures: dict[int, Future] = {}
        parallel_allowed = getattr(self.tts_func, 'parallel_allowed', None)
        if self.fast_tts_workers > 1 and callable(parallel_allowed) and parallel_allowed():
            prefetch_executor = ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix='winterboy-capcut-tts')
            logger.info('TTS fast prefetch enabled · max_in_flight=2')

        def _needs_raw_tts(position: int) -> bool:
            if position < 0 or position >= n:
                return False
            return blocks[position].index not in reusable_segments

        def _fill_prefetch(current: int) -> None:
            if prefetch_executor is None:
                return
            try:
                if not parallel_allowed():
                    return
            except Exception:
                return
            for position in range(current, n):
                if len(raw_futures) >= 2:
                    return
                if position in raw_futures or not _needs_raw_tts(position):
                    continue
                raw_futures[position] = prefetch_executor.submit(
                    self._prepare_raw_tts, blocks[position])

        _prog(0.0, f'{engine_label}: chuẩn bị {n} câu…')

        for i, block in enumerate(blocks):
            if _cancelled():
                _flush_checkpoint_state(force=True)
                return SyncResult(
                    False,
                    None,
                    n,
                    reports,
                    'Đã dừng render (TTS)')
            preview = (block.text or '').replace('\n', ' ').strip()
            if len(preview) > 42:
                preview = preview[:40] + '…'
            frac = i / max(n, 1) * 0.92
            eta = ''
            if cue_times:
                avg = sum(cue_times) / len(cue_times)
                left = avg * (n - i)
                if left >= 60:
                    eta = f' · còn ~{int(left // 60)}p{int(left % 60):02d}s'
                elif left >= 1:
                    eta = f' · còn ~{int(left)}s'
            reused = reusable_segments.get(block.index)
            # Câu đầu/cuối và mỗi 100 câu vẫn báo tiến độ khi dùng lại nhanh
            if reused is None or i == 0 or i + 1 == n or (i + 1) % 100 == 0:
                _prog(frac, f'{engine_label} {i + 1}/{n}{eta} · {preview or "(trống)"}')
            d_sub = max(self.min_segment_s, block.duration_s)
            # d_sub là hạn chót của block; không cho voice tràn sang cue kế
            max_duration = d_sub
            cue_dependencies = self._cue_dependencies(block, d_sub)
            cue_key = stable_fingerprint(cue_dependencies)
            cue_artifact = cue_artifact_dir / f'{cue_key}.wav'
            cue_record_name = f'cue:{cue_key}'
            if reused is not None:
                reused_path, report, reuse_source = reused
                if _usable_audio(reused_path):
                    report.index = block.index
                    report.text = block.text
                    report.segment_path = str(reused_path)
                    reports.append(report)
                    fitted_paths.append(reused_path)
                    cue_times.append(0.001)
                    if i == 0 or i + 1 == n or (i + 1) % 100 == 0:
                        _prog((i + 1) / max(n, 1) * 0.92,
                              f'{engine_label} {i + 1}/{n} · nạp nhanh từ {reuse_source}')
                    continue
                # Checkpoint biến mất giữa chừng: làm lại câu này, không im lặng dùng kết quả cũ
                reusable_segments.pop(block.index, None)
                completed_segments.pop(str(block.index), None)
                _mark_checkpoint_dirty(resume=True)
                logger.warning('TTS checkpoint disappeared before use: %s', reused_path)
            cue_t0 = time.perf_counter()
            provider_status_setter = getattr(self.tts_func, 'set_status_callback', None)
            if callable(provider_status_setter) and prefetch_executor is not None:
                provider_status_setter(
                    lambda provider_msg, _i=i, _frac=frac: _prog(
                        _frac, f'{engine_label} {_i + 1}/{n} · {provider_msg}'))
            elif callable(provider_status_setter):
                # Không còn luồng nền: giải phóng callback để không giữ tiến độ cũ
                provider_status_setter(None)
            _fill_prefetch(i)
            prepared_raw = raw_futures.pop(i, None)
            try:
                seg_path, report = self._process_one_block(
                    block,
                    d_sub,
                    max_duration=max_duration,
                    prepared_raw=prepared_raw)
                # Rate-limit giữa chừng (đã chạy được k câu ok): nghỉ rồi retry đúng 1 lần
                if (report.mode == 'skip'
                        and _is_hard_provider_fail(report.error)
                        and _ok_count() >= midrun_ok_threshold
                        and not midrun_cooldown_done):
                    midrun_cooldown_done = True
                    wait_s = 18.0
                    logger.warning('CapCut rate-limit giữa chừng (ok=%d/%d) — nghỉ %.0fs rồi retry block #%s',
                                   _ok_count(), n, wait_s, block.index)
                    _prog(frac, f'{engine_label}: rate-limit · nghỉ {int(wait_s)}s rồi tiếp…')
                    deadline = time.monotonic() + wait_s
                    while time.monotonic() < deadline:
                        if _cancelled():
                            _flush_checkpoint_state(force=True)
                            return SyncResult(
                                False,
                                None,
                                n,
                                reports,
                                'Đã dừng render (TTS)')
                        time.sleep(0.4)
                    seg_path, report = self._process_one_block(block, d_sub,
                                                               max_duration=max_duration)
                reports.append(report)
                fitted_paths.append(seg_path)
                if (report.mode != 'skip' and seg_path.is_file()
                        and seg_path.stat().st_size > 100):
                    persisted_path = seg_path
                    shared_artifact_saved = False
                    try:
                        if seg_path.resolve() != cue_artifact.resolve():
                            shutil.copy2(seg_path, cue_artifact)
                        persisted_path = cue_artifact
                        artifact_manifest.record(
                            cue_record_name,
                            cue_artifact,
                            cue_dependencies,
                            metadata={'report': asdict(report)},
                            save=False)
                        job_artifact_manifest.record(
                            f'cue:{block.index}',
                            cue_artifact,
                            cue_dependencies,
                            metadata={'content_key': cue_key},
                            save=False)
                        shared_artifact_saved = True
                    except Exception as exc:
                        logger.warning('Cannot persist cue dependency artifact #%s: %s',
                                       block.index, exc)
                        # Still keep a job-local checkpoint so a cancelled render can resume.
                        checkpoint = resume_dir / f'fit_{block.index:04d}.wav'
                        try:
                            if seg_path.resolve() != checkpoint.resolve():
                                shutil.copy2(seg_path, checkpoint)
                            persisted_path = checkpoint
                        except Exception as checkpoint_exc:
                            logger.warning('Cannot checkpoint fallback TTS block #%s: %s',
                                           block.index, checkpoint_exc)
                    try:
                        checkpoint_report = asdict(report)
                        checkpoint_report['segment_path'] = str(persisted_path)
                        report.segment_path = str(persisted_path)
                        fitted_paths[-1] = persisted_path
                        completed_segments[str(block.index)] = {
                            'segment_path': str(persisted_path),
                            'report': checkpoint_report}
                        _mark_checkpoint_dirty(
                            resume=True,
                            artifact=shared_artifact_saved,
                            job_artifact=shared_artifact_saved)
                    except Exception as exc:
                        logger.warning('Cannot checkpoint TTS block #%s: %s', block.index, exc)
                if report.mode == 'skip':
                    consecutive_provider_fail += 1
                    # Provider chết ngay từ đầu → dừng sớm, đừng chờ hàng chục phút
                    early_job = _ok_count() < midrun_ok_threshold
                    if (early_job and consecutive_provider_fail >= hard_fail_after
                            and _is_hard_provider_fail(report.error)):
                        _flush_checkpoint_state(force=True)
                        return SyncResult(
                            False,
                            None,
                            n,
                            reports,
                            _hard_fail_message(report.error))
                consecutive_provider_fail = 0
            except Exception as e:
                if callable(provider_status_setter):
                    provider_status_setter(None)
                logger.exception('Lỗi block #%s', block.index)
                _flush_checkpoint_state(force=True)
                return SyncResult(False, None, n, reports, f'Block #{block.index} lỗi: {e}')
            if callable(provider_status_setter):
                provider_status_setter(None)
            cue_times.append(max(0.05, time.perf_counter() - cue_t0))

        if prefetch_executor is not None:
            prefetch_executor.shutdown(wait=True, cancel_futures=True)
            logger.info('TTS fast prefetch finished')
        _flush_checkpoint_state(force=True)
        if _cancelled():
            return SyncResult(
                False,
                None,
                n,
                reports,
                'Đã dừng render (TTS)')
        skip_n = sum(1 for r in reports if r.mode == 'skip')
        ok_n = n - skip_n
        natural_limit_n = sum(
            1
            for r in reports
            if self.natural_voice_sync
            and r.mode == 'atempo'
            and (r.speed_rate or 0.0) >= self.max_speed_rate - 0.001)
        if ok_n == 0:
            last_err = next((r.error for r in reversed(reports) if r.error), None)
            return SyncResult(
                False,
                None,
                n,
                reports,
                _hard_fail_message(last_err) if _is_hard_provider_fail(last_err)
                else f'{engine_label}: 0/{n} câu TTS thành công — không có giọng để render.')
        if skip_n > n * 0.5:
            logger.warning('%s: %d/%d câu TTS fail (skip→silence) — track lồng tiếng sẽ thiếu',
                           engine_label, skip_n, n)

        timeline_blocks = blocks
        timeline_paths = fitted_paths
        quality_report_path = None
        if self.soft_timing_enabled:
            _prog(0.925, f'{engine_label}: lập Soft Timing {n} câu…')
            try:
                timeline_blocks, timeline_paths, quality_payload = self._apply_soft_timing_plan(
                    blocks, fitted_paths, reports)
                quality_payload.update({
                    'source_srt': str(srt_path),
                    'voice_signature': self.voice_signature})
                quality_report_path = self._write_quality_report(
                    output_path.parent / 'tts_quality_report.json',
                    quality_payload)
                logger.info('Soft Timing quality report: %s', quality_report_path)
            except Exception as exc:
                logger.exception('Soft Timing planner failed')
                _flush_checkpoint_state(force=True)
                return SyncResult(False, None, n, reports, f'Soft Timing lỗi: {exc}')
        timeline_dependencies = {
            'version': 1,
            # Chế độ ghép phải nằm trong khoá cache, nếu không resume sẽ trộn timeline sai
            'mode': 'soft_timing' if self.soft_timing_enabled
            else 'natural_overlap' if self.natural_voice_sync
            else 'legacy_slots',
            'align_to_timeline': align_to_timeline,
            'sample_rate': self.sample_rate,
            'segments': [
                {
                    'index': block.index,
                    'start_s': round(block.start_s, 6),
                    'end_s': round(block.end_s, 6),
                    'path': str(path),
                    'size': path.stat().st_size if path.is_file() else -1,
                    'mtime_ns': path.stat().st_mtime_ns if path.is_file() else -1,
                }
                for block, path in zip(timeline_blocks, timeline_paths)],
        }
        timeline_key = stable_fingerprint(timeline_dependencies)
        timeline_cache_dir = artifact_root / 'timelines'
        timeline_cache_dir.mkdir(parents=True, exist_ok=True)
        timeline_chunk_dir = artifact_root / 'timeline_chunks'
        timeline_chunk_dir.mkdir(parents=True, exist_ok=True)
        timeline_cache = timeline_cache_dir / f'{timeline_key}{output_path.suffix or ".mp3"}'
        timeline_record = f'timeline:{timeline_key}'

        _prog(0.93, f'{engine_label}: ghép timeline {n} câu…')
        try:
            if artifact_manifest.valid(timeline_record, timeline_dependencies,
                                       output=timeline_cache, min_size=100):
                shutil.copy2(timeline_cache, output_path)
                final = output_path
                logger.info('TTS timeline artifact HIT · %s', timeline_key[:12])
            elif align_to_timeline and (self.soft_timing_enabled or self.natural_voice_sync):
                final = self._mix_with_timeline_overlap(
                    timeline_blocks,
                    timeline_paths,
                    output_path,
                    cache_dir=timeline_chunk_dir,
                    artifact_manifest=artifact_manifest)
            elif align_to_timeline:
                final = self._concat_with_timeline_gaps(
                    timeline_blocks,
                    timeline_paths,
                    output_path,
                    cache_dir=timeline_chunk_dir,
                    artifact_manifest=artifact_manifest)
            else:
                final = self._concat_sequential(timeline_paths, output_path)
            shutil.copy2(final, timeline_cache)
            artifact_manifest.record(
                timeline_record,
                timeline_cache,
                timeline_dependencies,
                metadata={'quality_report': str(quality_report_path or '')})
            job_artifact_manifest.record(
                'voice_timeline',
                final,
                timeline_dependencies,
                metadata={'content_key': timeline_key,
                          'quality_report': str(quality_report_path or '')})
            total = probe_duration_s(final, self.ffprobe)
        except Exception as e:
            logger.exception('Concat lỗi')
            _flush_checkpoint_state(force=True)
            return SyncResult(False, None, n, reports, str(e))

        elapsed = time.perf_counter() - t0
        resume_manifest.update({
            'status': 'complete',
            'completed_at': time.time(),
            'updated_at': time.time()})
        self._write_resume_manifest(resume_manifest_path, resume_manifest)
        _flush_checkpoint_state(force=True)
        logger.info('OK final_voice=%s | N=%d ok=%d skip=%d natural-limit=%d | duration=%.3fs | wall=%.1fs',
                    final, n, ok_n, skip_n, natural_limit_n, total, elapsed)
        _prog(1.0, f'{engine_label}: xong {ok_n}/{n} câu · {elapsed:.0f}s')
        if self.soft_timing_enabled:
            msg = 'Soft Timing xong — ưu tiên khoảng lặng, nén tối đa 1.10×'
        elif self.natural_voice_sync:
            msg = 'Đồng bộ xong — tối đa 1.35×, cho phép chồng giọng khi cue quá ngắn'
        else:
            msg = 'Đồng bộ xong — không đè giọng (mỗi đoạn = D_sub)'
        if skip_n:
            msg += f' · cảnh báo: {skip_n} câu silence (TTS fail)'
        if self.natural_voice_sync and natural_limit_n:
            msg += f' · báo cáo: {natural_limit_n} cue chạm giới hạn 1.35×'
        return SyncResult(
            ok=True,
            final_voice_path=final,
            n_blocks=n,
            reports=reports,
            message=msg,
            total_duration_s=total,
            quality_report_path=quality_report_path)

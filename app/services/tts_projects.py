'''Discover and safely clean durable TTS project checkpoints.'''
from __future__ import annotations
import hashlib
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from app.services.audio_sync_engine import load_srt_blocks
from app.services.job_workspace import JOBS_ROOT
logger = logging.getLogger(__name__)
TTS_RESUME_ROOT = Path(tempfile.gettempdir()) / 'mumu_tts_resume'


@dataclass
class TtsProject:
    resume_dir: Path
    manifest_path: Path
    srt_path: Path
    source_video: Path | None
    target: str
    provider: str
    voice_id: str
    tts_speed: str
    model_id: str
    voice_signature: str
    total_cues: int
    completed_cues: int
    remaining_cues: int
    status: str
    updated_at: str
    updated_epoch: float
    natural_voice_sync: bool
    soft_timing_enabled: bool
    # resume_metadata v2 mới lưu hai cờ CapCut; bản cũ phải để None, không suy đoán
    capcut_strict: bool | None
    capcut_fast_mode: bool | None

    @property
    def label(self) -> str:
        try:
            job_name = self.srt_path.parents[1].name
        except IndexError:
            job_name = ''
        return (job_name or self.srt_path.stem or self.resume_dir.name)[:100]

    @property
    def is_complete(self) -> bool:
        return self.status == 'complete'

    @property
    def status_label(self) -> str:
        if self.status == 'complete':
            return 'Đã hoàn thành'
        if self.status == 'tts_ready':
            return 'Đã đủ câu · chờ hoàn tất'
        if self.status == 'needs_repair':
            return 'Thiếu file · cần khôi phục'
        if self.status == 'not_started':
            return 'Chưa tạo câu nào'
        return 'Đang thực hiện'


@dataclass
class TtsCheckpointCleanup:
    kept: int
    removed_projects: int
    removed_files: int
    reclaimed_bytes: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda : handle.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _legacy_voice_parts(signature: str) -> tuple[str, str, str, str]:
    '''Recover provider/model/voice/speed from a legacy voice signature.'''
    (engine, sep, remainder) = (signature or '').partition('|')
    if not sep:
        return ('', '', '', '1.0')
    (voice, sep, speed) = remainder.rpartition('|')
    if not sep:
        speed = '1.0'
        voice = remainder
    if engine == 'CapCut':
        (provider, model) = ('CapCut', '')
    elif engine == 'edge-tts':
        (provider, model) = ('Edge TTS', '')
    elif engine.startswith('ElevenLabs/'):
        (provider, model) = ('ElevenLabs', engine.split('/', 1)[1])
    elif engine.startswith('Google Cloud TTS'):
        (provider, model) = ('Google Cloud TTS', engine.split('/', 1)[-1])
    else:
        (provider, model) = (engine, '')
    return (provider, model, voice, speed or '1.0')


def _legacy_sync_modes(payload: dict[str, Any], *, srt_hash: str, resume_key: str) -> tuple[bool, bool]:
    '''Infer timing mode for v1 journals that did not store mode metadata.

    Old resume directory names were the SHA-256 of the complete sync settings,
    so trying the small set of modes historically supported is exact and safer
    than accepting a checkpoint only because its SRT/voice happen to match.
    '''
    if 'natural_voice_sync' in payload or 'soft_timing_enabled' in payload:
        return (bool(payload.get('natural_voice_sync')), bool(payload.get('soft_timing_enabled')))
    signature = str(payload.get('voice_signature') or '')
    candidates = ((1.35, True, False), (3.0, False, True), (3.0, False, False), 
                  (1.85, False, False))
    for max_speed_rate, natural, soft in candidates:
        identity = {
            'version': 1,
            'srt_sha256': srt_hash,
            'voice_signature': signature,
            'sample_rate': 44100,
            'max_speed_rate': max_speed_rate,
            'min_segment_s': 0.08,
            'natural_voice_sync': natural,
            'soft_timing_enabled': soft,
            'soft_max_drift_s': 1.5,
            'soft_min_gap_s': 0.12,
            'soft_max_atempo': 1.1 }
        if natural:
            identity['natural_sync_policy'] = 'overlap_v1'
        if soft:
            identity['soft_timing_policy'] = 'shift_compress_report_v1'
        stable = json.dumps(identity, ensure_ascii = False, sort_keys = True, separators = (
                                                ',', ':'))
        if hashlib.sha256(stable.encode('utf-8')).hexdigest() == resume_key:
            return (natural, soft)
    return (False, False)


def _valid_completed_count(payload: dict[str, Any]) -> int:
    count = 0
    completed = payload.get('completed')
    if not isinstance(completed, dict):
        return 0
    for entry in completed.values():
        if not isinstance(entry, dict):
            continue
        report = entry.get('report')
        if isinstance(report, dict) and str(report.get('mode') or '').casefold() == 'skip':
            continue
        raw_path = str(entry.get('segment_path') or '').strip()
        try:
            segment = Path(raw_path)
            if segment.is_file() and segment.stat().st_size > 100:
                count += 1
        except OSError:
            continue
    return count


def _resolve_srt(payload: dict[str, Any], legacy_hashes: dict[str, Path]) -> Path | None:
    raw = str(payload.get('source_srt') or '').strip()
    expected = str(payload.get('srt_sha256') or '').strip().casefold()
    if raw:
        candidate = Path(raw).expanduser()
        try:
            if candidate.is_file() and (not expected or _sha256(candidate) == expected):
                return candidate
        except OSError:
            pass

    return legacy_hashes.get(expected)


def _legacy_srt_lookup(required_hashes: set[str]) -> dict[str, Path]:
    '''Hash job SRT files only when old manifests have no source path.'''
    if not required_hashes or not JOBS_ROOT.is_dir():
        return {}
    found = {}
    try:
        for candidate in JOBS_ROOT.rglob('*.srt'):
            if len(found) >= len(required_hashes):
                break
            try:
                digest = _sha256(candidate)
                if digest in required_hashes and digest not in found:
                    found[digest] = candidate
            except OSError:
                continue
    except OSError as exc:
        logger.warning('Cannot scan legacy TTS source SRTs: %s', exc)
    return found


def list_tts_projects(*, limit: int = 100) -> list[TtsProject]:
    '''Return all usable TTS projects, including completed projects.'''
    if not TTS_RESUME_ROOT.is_dir():
        return []
    raw_manifests = []
    legacy_hashes_needed = set()
    try:
        for manifest_path in TTS_RESUME_ROOT.glob('*/manifest.json'):
            try:
                payload = json.loads(manifest_path.read_text(encoding = 'utf-8'))
                if not isinstance(payload, dict) or not isinstance(payload.get('completed'), dict):
                    continue
                raw_manifests.append((manifest_path, payload))
                if not str(payload.get('source_srt') or '').strip():
                    digest = str(payload.get('srt_sha256') or '').strip().casefold()
                    if digest:
                        legacy_hashes_needed.add(digest)
            except (OSError, json.JSONDecodeError, TypeError) as exc:
                logger.debug('Skip damaged TTS checkpoint %s: %s', manifest_path, exc)
    except OSError as exc:
        logger.warning('Cannot scan TTS checkpoints: %s', exc)
        return []

    legacy_lookup = _legacy_srt_lookup(legacy_hashes_needed)
    projects = []
    for manifest_path, payload in raw_manifests:
        srt_path = _resolve_srt(payload, legacy_lookup)
        if srt_path is None:
            continue
        try:
            total = int(payload.get('total_cues') or 0)
            if total <= 0:
                total = len(load_srt_blocks(srt_path))
            completed = min(total, _valid_completed_count(payload))
            remaining = max(0, total - completed)
            if total <= 0:
                continue
            saved_status = str(payload.get('status') or '').strip().casefold()
            if saved_status == 'complete' and remaining == 0:
                project_status = 'complete'
            elif saved_status == 'complete':
                # đánh dấu complete nhưng vẫn thiếu câu -> phải chạy lại mới an toàn
                project_status = 'needs_repair'
            elif remaining == 0:
                # chưa ghi trạng thái cuối nhưng audio của mọi câu đã nằm trên đĩa
                project_status = 'tts_ready'
            elif completed <= 0:
                project_status = 'not_started'
            else:
                project_status = 'in_progress'
            signature = str(payload.get('voice_signature') or '')
            (legacy_provider, legacy_model, legacy_voice, legacy_speed) = _legacy_voice_parts(signature)
            metadata = payload.get('resume_metadata')
            if not isinstance(metadata, dict):
                metadata = {}
            try:
                metadata_version = int(payload.get('resume_metadata_version') or 0)
            except (TypeError, ValueError):
                metadata_version = 0

            if 'natural_voice_sync' in metadata or 'soft_timing_enabled' in metadata:
                natural_voice_sync = bool(metadata.get('natural_voice_sync'))
                soft_timing_enabled = bool(metadata.get('soft_timing_enabled'))
            else:
                (natural_voice_sync, soft_timing_enabled) = _legacy_sync_modes(
                    payload, 
                    srt_hash = str(payload.get('srt_sha256') or ''), 
                    resume_key = manifest_path.parent.name)
            video_raw = str(metadata.get('source_video') or payload.get('source_video') or '').strip()
            source_video = Path(video_raw) if video_raw else None
            if source_video is not None and not source_video.is_file():
                source_video = None
            updated_epoch = float(payload.get('updated_at') or manifest_path.stat().st_mtime)
            updated_at = datetime.fromtimestamp(updated_epoch).strftime('%Y-%m-%d %H:%M:%S')
            projects.append(TtsProject(resume_dir = manifest_path.parent, 
                   manifest_path = manifest_path, srt_path = srt_path, source_video = source_video, 
                   target = str(metadata.get('target') or 'mp4'), provider = str(metadata.get('provider') or legacy_provider), 
                   voice_id = str(metadata.get('voice_id') or legacy_voice), tts_speed = str(metadata.get('tts_speed') or legacy_speed or '1.0'), 
                   model_id = str(metadata.get('model_id') or legacy_model), voice_signature = signature, 
                   total_cues = total, completed_cues = completed, remaining_cues = remaining, 
                   status = project_status, updated_at = updated_at, updated_epoch = updated_epoch, 
                   natural_voice_sync = natural_voice_sync, soft_timing_enabled = soft_timing_enabled, 
                   capcut_strict = bool(metadata.get('capcut_strict')) if metadata_version >= 2 and 'capcut_strict' in metadata else None, 
                   capcut_fast_mode = bool(metadata.get('capcut_fast_mode'))
                   if metadata_version >= 2 and 'capcut_fast_mode' in metadata else None))
        except (OSError, TypeError, ValueError) as exc:
            logger.debug('Skip unusable TTS checkpoint %s: %s', manifest_path, exc)

    projects.sort(key = lambda item: item.updated_epoch, reverse = True)
    return projects[:max(1, int(limit))]


def list_unfinished_tts_projects(*, limit: int = 100) -> list[TtsProject]:
    '''Backward-compatible view containing only projects that can resume.'''
    projects = list_tts_projects(limit = 100000)
    unfinished = [project for project in projects if not project.is_complete]
    return unfinished[:max(1, int(limit))]


def cleanup_old_tts_checkpoints(*, keep: int = 1) -> TtsCheckpointCleanup:
    '''Remove old resume-only folders while preserving the newest project.'''
    keep = max(1, int(keep))
    projects = list_tts_projects(limit = 100000)
    removed_projects = 0
    removed_files = 0
    reclaimed_bytes = 0
    root = TTS_RESUME_ROOT.resolve()
    for project in projects[keep:]:
        try:
            resume_dir = project.resume_dir.resolve()
            resume_dir.relative_to(root)
            if resume_dir.parent != root or not resume_dir.is_dir():
                continue
            files = [path for path in resume_dir.rglob('*') if path.is_file()]
            reclaimed_bytes += sum((path.stat().st_size for path in files))
            removed_files += len(files)
            shutil.rmtree(resume_dir)
            removed_projects += 1
        except (OSError, ValueError) as exc:
            logger.warning('Cannot remove old TTS checkpoint %s: %s', project.resume_dir, exc)
    return TtsCheckpointCleanup(kept = min(keep, len(projects)), removed_projects = removed_projects, 
       removed_files = removed_files, reclaimed_bytes = reclaimed_bytes)

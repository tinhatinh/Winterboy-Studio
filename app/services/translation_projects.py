'''Discover durable, unfinished subtitle-translation checkpoints.'''
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from app.services.job_workspace import JOBS_ROOT
logger = logging.getLogger(__name__)


@dataclass
class TranslationProject:
    progress_path: Path
    srt_path: Path
    log_path: Path
    source_path: Path | None
    status: str
    engine: str
    model: str
    total_cues: int
    remaining_cues: int
    last_source_cue: int
    updated_at: str
    note: str

    @property
    def label(self) -> str:
        '''
        Nhãn hiển thị: tên thư mục job nếu có, không thì tên file SRT nguồn.

        Cắt tối đa 100 ký tự để không vỡ dòng trong UI.
        '''
        job_name = self.progress_path.parent.parent.name
        if job_name:
            return job_name[:100]
        source = self.source_path.name if self.source_path else self.srt_path.name
        return source[:100] or self.srt_path.name


@dataclass
class TranslationLogCleanup:
    '''Result of discarding only old checkpoint/log sidecars.'''
    kept: int
    removed_projects: int
    removed_files: int
    reclaimed_bytes: int


def list_unfinished_translation_projects(*, limit: int = 100) -> list[TranslationProject]:
    '''Return recoverable projects sorted by most recently checkpointed first.'''
    if not JOBS_ROOT.is_dir():
        return []
    projects = []
    try:
        candidates = JOBS_ROOT.rglob('*.srt.progress.json')
        for progress_path in candidates:
            try:
                payload = json.loads(progress_path.read_text(encoding = 'utf-8'))
                if not isinstance(payload, dict):
                    continue
                remaining = int(payload.get('remaining_cues') or 0)
                if remaining <= 0:
                    continue
                output_raw = str(payload.get('output_srt') or '').strip()
                srt_path = Path(output_raw) if output_raw else Path(progress_path.name.removesuffix(
                    '.progress.json'))
                if not srt_path.is_absolute():
                    srt_path = progress_path.parent / srt_path
                if not srt_path.is_file():
                    continue
                source_raw = str(payload.get('source_srt') or '').strip()
                source_path = Path(source_raw) if source_raw else None
                if source_path is not None and not source_path.is_absolute():
                    source_path = progress_path.parent / source_path
                if source_path is not None and not source_path.is_file():
                    source_path = None
                projects.append(TranslationProject(progress_path = progress_path, srt_path = srt_path, 
                   log_path = progress_path.with_name(f'''{progress_path.name.removesuffix('.progress.json')}.translation.jsonl'''), 
                   source_path = source_path, status = str(payload.get('status') or 'unknown'), 
                   engine = str(payload.get('engine') or ''), model = str(payload.get('model') or ''), 
                   total_cues = int(payload.get('total_cues') or 0), remaining_cues = remaining, 
                   last_source_cue = int(payload.get('last_source_cue') or 0), updated_at = str(payload.get('updated_at') or ''), 
                   note = str(payload.get('note') or '')))
            except Exception as exc:
                logger.debug('Skip translation checkpoint %s: %s', progress_path, exc)
    except OSError as exc:
        logger.warning('Cannot scan translation projects: %s', exc)

    projects.sort(key = lambda project: (project.updated_at, project.progress_path.stat().st_mtime
                                          if project.progress_path.exists() else 0), reverse = True)
    return projects[:max(1, limit)]


def cleanup_old_translation_logs(*, keep: int = 1) -> TranslationLogCleanup:
    '''Keep the newest unfinished checkpoint and remove older log sidecars.

    The partial translated SRT itself is deliberately never deleted: it is
    still a useful user document. Removing its progress and JSONL sidecars
    only hides old jobs from the resume list and reclaims their log space.
    '''
    keep = max(1, int(keep))
    projects = list_unfinished_translation_projects(limit = 100000)
    removable = projects[keep:]
    removed_files = 0
    reclaimed_bytes = 0
    removed_projects = 0
    for project in removable:
        removed_this_project = False
        for candidate in (project.progress_path, project.log_path):
            try:
                # chỉ được xoá bên trong JOBS_ROOT; lọt ra ngoài là ValueError
                candidate.resolve().relative_to(JOBS_ROOT.resolve())
                if candidate.is_file():
                    reclaimed_bytes += candidate.stat().st_size
                    candidate.unlink()
                    removed_files += 1
                    removed_this_project = True
            except (OSError, ValueError) as exc:
                logger.warning('Cannot remove old translation sidecar %s: %s', candidate, exc)
        if not removed_this_project:
            continue
        removed_projects += 1
    return TranslationLogCleanup(kept = min(keep, len(projects)), removed_projects = removed_projects, removed_files = removed_files, reclaimed_bytes = reclaimed_bytes)

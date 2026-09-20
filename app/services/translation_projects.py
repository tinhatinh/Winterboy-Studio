# Source Generated with Decompyle++
# File: translation_projects.pyc (Python 3.12)

'''Discover durable, unfinished subtitle-translation checkpoints.'''
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from app.services.job_workspace import JOBS_ROOT
logger = logging.getLogger(__name__)
TranslationProject = <NODE:12>()
TranslationLogCleanup = <NODE:12>()

def list_unfinished_translation_projects(*, limit):
    '''Return recoverable projects sorted by most recently checkpointed first.'''
    if not JOBS_ROOT.is_dir():
        return []
    projects = None
# WARNING: Decompyle incomplete


def cleanup_old_translation_logs(*, keep):
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
            candidate.resolve().relative_to(JOBS_ROOT.resolve())
            if candidate.is_file():
                reclaimed_bytes += candidate.stat().st_size
                candidate.unlink()
                removed_files += 1
                removed_this_project = True
    if not removed_this_project:
        continue
    removed_projects += 1
    continue
    return TranslationLogCleanup(kept = min(keep, len(projects)), removed_projects = removed_projects, removed_files = removed_files, reclaimed_bytes = reclaimed_bytes)
    except (OSError, ValueError):
        exc = None
        logger.warning('Cannot remove old translation sidecar %s: %s', candidate, exc)
        exc = None
        del exc
        continue
        exc = None
        del exc


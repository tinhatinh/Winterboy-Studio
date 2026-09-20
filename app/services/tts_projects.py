# Source Generated with Decompyle++
# File: tts_projects.pyc (Python 3.12)

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
TtsProject = <NODE:12>()
TtsCheckpointCleanup = <NODE:12>()

def _sha256(path = None):
    pass
# WARNING: Decompyle incomplete


def _legacy_voice_parts(signature = None):
    '''Recover provider/model/voice/speed from a legacy voice signature.'''
    if not signature:
        signature
    (engine, sep, remainder) = ''.partition('|')
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
        model = engine.split('/', 1)[1]
        provider = 'ElevenLabs'
    elif engine.startswith('Google Cloud TTS'):
        model = engine.split('/', 1)[-1]
        provider = 'Google Cloud TTS'
    else:
        model = ''
        provider = engine
    if not speed:
        speed
    return (provider, model, voice, '1.0')


def _legacy_sync_modes(payload = None, *, srt_hash, resume_key):
    '''Infer timing mode for v1 journals that did not store mode metadata.

    Old resume directory names were the SHA-256 of the complete sync settings,
    so trying the small set of modes historically supported is exact and safer
    than accepting a checkpoint only because its SRT/voice happen to match.
    '''
    if 'natural_voice_sync' in payload or 'soft_timing_enabled' in payload:
        return (bool(payload.get('natural_voice_sync')), bool(payload.get('soft_timing_enabled')))
    if not payload.get('voice_signature'):
        payload.get('voice_signature')
    signature = None('')
    candidates = ((1.35, True, False), (3, False, True), (3, False, False), (1.85, False, False))
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
        stable = json.dumps(identity, ensure_ascii = False, sort_keys = True, separators = (',', ':'))
        if not hashlib.sha256(stable.encode('utf-8')).hexdigest() == resume_key:
            continue
        
        return candidates, (natural, soft)
    return (False, False)


def _valid_completed_count(payload = None):
    count = 0
    completed = payload.get('completed')
    if not isinstance(completed, dict):
        return 0
    for entry in completed.values():
        if not isinstance(entry, dict):
            continue
        report = entry.get('report')
        if isinstance(report, dict):
            if not report.get('mode'):
                report.get('mode')
            if str('').casefold() == 'skip':
                continue
        if not entry.get('segment_path'):
            entry.get('segment_path')
        raw_path = str('').strip()
        segment = Path(raw_path)
        if segment.is_file() and segment.stat().st_size > 100:
            count += 1
    continue
    return count
    except OSError:
        continue


def _resolve_srt(payload = None, legacy_hashes = None):
    if not payload.get('source_srt'):
        payload.get('source_srt')
    raw = str('').strip()
    if not payload.get('srt_sha256'):
        payload.get('srt_sha256')
    expected = str('').strip().casefold()
    if raw:
        candidate = Path(raw).expanduser()
        
        try:
            if candidate.is_file():
                if expected or _sha256(candidate) == expected:
                    return candidate
                return None.get(expected)
            except OSError:
                continue



def _legacy_srt_lookup(required_hashes = None):
    '''Hash job SRT files only when old manifests have no source path.'''
    if not required_hashes or JOBS_ROOT.is_dir():
        return { }
    found = None
    
    try:
        for candidate in JOBS_ROOT.rglob('*.srt'):
            if len(found) >= len(required_hashes):
                JOBS_ROOT.rglob('*.srt')
                return found
            digest = _sha256(candidate)
            if digest in required_hashes and digest not in found:
                found[digest] = candidate
                
                try:
                    continue
                    return found
                    except OSError:
                        
                        try:
                            continue
                            
                            try:
                                pass
                            except OSError:
                                exc = None
                                logger.warning('Cannot scan legacy TTS source SRTs: %s', exc)
                                exc = None
                                del exc
                                return found
                                exc = None
                                del exc






def list_tts_projects(*, limit):
    '''Return all usable TTS projects, including completed projects.'''
    if not TTS_RESUME_ROOT.is_dir():
        return []
    raw_manifests = None
    legacy_hashes_needed = set()
# WARNING: Decompyle incomplete


def list_unfinished_tts_projects(*, limit):
    '''Backward-compatible view containing only projects that can resume.'''
    projects = list_tts_projects(limit = 100000)
# WARNING: Decompyle incomplete


def cleanup_old_tts_checkpoints(*, keep):
    '''Remove old resume-only folders while preserving the newest project.'''
    keep = max(1, int(keep))
    projects = list_tts_projects(limit = 100000)
    removed_projects = 0
    removed_files = 0
    reclaimed_bytes = 0
    root = TTS_RESUME_ROOT.resolve()
# WARNING: Decompyle incomplete


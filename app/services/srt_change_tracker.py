# Source Generated with Decompyle++
# File: srt_change_tracker.pyc (Python 3.12)

'''Compare SRT edits and persist the cue-level rebuild intent.'''
from __future__ import annotations
import difflib
import hashlib
import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from app.services.artifact_manifest import DependencyManifest, stable_fingerprint
from app.services.srt_utils import SrtCue, parse_srt_string
CueChange = <NODE:12>()
SrtEditSummary = <NODE:12>()

def _same_time(a = None, b = dataclass):
    return abs(float(a) - float(b)) <= 0.002


def _classify_pair(old = None, new = None, summary = None):
    if old.text != new.text:
        summary.tts_rebuild_indices.append(new.index)
        summary.changes.append(CueChange('text', old.index, new.index, old.text, new.text))
        return None
    old_duration = old.end_s - old.start_s
    new_duration = new.end_s - new.start_s
    if not _same_time(old_duration, new_duration):
        summary.tts_rebuild_indices.append(new.index)
        summary.changes.append(CueChange('duration', old.index, new.index, old.text, new.text))
        return None
    if not _same_time(old.start_s, new.start_s) or _same_time(old.end_s, new.end_s):
        summary.timeline_only_indices.append(new.index)
        summary.changes.append(CueChange('timing', old.index, new.index, old.text, new.text))
        return None


def compare_srt_text(before = None, after = None):
    old_cues = parse_srt_string(before)
    new_cues = parse_srt_string(after)
    summary = SrtEditSummary(old_count = len(old_cues), new_count = len(new_cues))
# WARNING: Decompyle incomplete


def _text_sha256(value = None):
    if not value:
        value
    return hashlib.sha256(''.encode('utf-8')).hexdigest()


def record_srt_edit(source_path = None, before = None, after = None):
    '''Compare and atomically record one save from the SRT editor.'''
    summary = compare_srt_text(before, after)
    if not summary.changed:
        return summary
    source = None(source_path)
    root = Path(tempfile.gettempdir()) / 'mumu_tts_artifacts' / 'srt_edits'
    root.mkdir(parents = True, exist_ok = True)
    source_key = stable_fingerprint({
        'source': str(source.resolve()) })[:24]
    after_hash = _text_sha256(after)
    journal = root / f'''{source_key}_{after_hash[:16]}.json'''
# WARNING: Decompyle incomplete


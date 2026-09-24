# -*- coding: utf-8 -*-
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


@dataclass
class CueChange:
    kind: str
    old_index: int | None = None
    new_index: int | None = None
    old_text: str = ''
    new_text: str = ''


@dataclass
class SrtEditSummary:
    changed: bool = False
    old_count: int = 0
    new_count: int = 0
    tts_rebuild_indices: list[int] = field(default_factory=list)
    timeline_only_indices: list[int] = field(default_factory=list)
    removed_count: int = 0
    changes: list[CueChange] = field(default_factory=list)
    journal_path: Path | None = None

    @property
    def timeline_only_count(self) -> int:
        return len(self.timeline_only_indices)

    @property
    def tts_rebuild_count(self) -> int:
        return len(self.tts_rebuild_indices)


def _same_time(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= 0.002


def _classify_pair(old: SrtCue, new: SrtCue, summary: SrtEditSummary) -> None:
    '''Một cặp cue cùng vị trí: đổi chữ thì phải TTS lại, đổi giờ thì chỉ sửa timeline.'''
    if old.text != new.text:
        summary.tts_rebuild_indices.append(new.index)
        summary.changes.append(
            CueChange('text', old.index, new.index, old.text, new.text))
        return
    old_duration = old.end_s - old.start_s
    new_duration = new.end_s - new.start_s
    if not _same_time(old_duration, new_duration):
        summary.tts_rebuild_indices.append(new.index)
        summary.changes.append(
            CueChange('duration', old.index, new.index, old.text, new.text))
        return
    if not _same_time(old.start_s, new.start_s) or not _same_time(old.end_s, new.end_s):
        summary.timeline_only_indices.append(new.index)
        summary.changes.append(
            CueChange('timing', old.index, new.index, old.text, new.text))
        return


def compare_srt_text(before: str, after: str) -> SrtEditSummary:
    old_cues = parse_srt_string(before)
    new_cues = parse_srt_string(after)
    summary = SrtEditSummary(old_count=len(old_cues), new_count=len(new_cues))
    matcher = difflib.SequenceMatcher(
        None,
        [cue.text for cue in old_cues],
        [cue.text for cue in new_cues],
        autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == 'equal':
            for old, new in zip(old_cues[old_start:old_end], new_cues[new_start:new_end]):
                _classify_pair(old, new, summary)
        elif tag == 'replace':
            old_group = old_cues[old_start:old_end]
            new_group = new_cues[new_start:new_end]
            common = min(len(old_group), len(new_group))
            for offset in range(common):
                _classify_pair(old_group[offset], new_group[offset], summary)
            for cue in new_group[common:]:
                summary.tts_rebuild_indices.append(cue.index)
                summary.changes.append(
                    CueChange('added', None, cue.index, '', cue.text))
            for cue in old_group[common:]:
                summary.removed_count += 1
                summary.changes.append(
                    CueChange('removed', cue.index, None, cue.text, ''))
        elif tag == 'insert':
            for cue in new_cues[new_start:new_end]:
                summary.tts_rebuild_indices.append(cue.index)
                summary.changes.append(
                    CueChange('added', None, cue.index, '', cue.text))
        elif tag == 'delete':
            for cue in old_cues[old_start:old_end]:
                summary.removed_count += 1
                summary.changes.append(
                    CueChange('removed', cue.index, None, cue.text, ''))
    summary.tts_rebuild_indices = sorted(set(summary.tts_rebuild_indices))
    summary.timeline_only_indices = sorted(set(summary.timeline_only_indices))
    summary.changed = bool(summary.changes)
    return summary


def _text_sha256(value: str) -> str:
    return hashlib.sha256((value or '').encode('utf-8')).hexdigest()


def record_srt_edit(source_path: str | Path, before: str, after: str) -> SrtEditSummary:
    '''Compare and atomically record one save from the SRT editor.'''
    summary = compare_srt_text(before, after)
    if not summary.changed:
        return summary

    source = Path(source_path)
    root = Path(tempfile.gettempdir()) / 'winterboy_tts_artifacts' / 'srt_edits'
    root.mkdir(parents=True, exist_ok=True)
    source_key = stable_fingerprint({'source': str(source.resolve())})[:24]
    after_hash = _text_sha256(after)
    journal = root / f'{source_key}_{after_hash[:16]}.json'

    payload = {
        'version': 1,
        'source': str(source),
        'saved_at': time.time(),
        'before_sha256': _text_sha256(before),
        'after_sha256': after_hash,
        'old_count': summary.old_count,
        'new_count': summary.new_count,
        'tts_rebuild_indices': summary.tts_rebuild_indices,
        'timeline_only_indices': summary.timeline_only_indices,
        'removed_count': summary.removed_count,
        'changes': [asdict(item) for item in summary.changes],
    }
    temp = journal.with_suffix(journal.suffix + '.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(journal)
    summary.journal_path = journal

    dependencies = {
        'source': str(source.resolve()),
        'before_sha256': payload['before_sha256'],
        'after_sha256': after_hash,
    }
    DependencyManifest(root / 'artifact_manifest.json').record(
        f'srt:{source_key}',
        journal,
        dependencies,
        metadata={
            'tts_rebuild_indices': summary.tts_rebuild_indices,
            'timeline_only_indices': summary.timeline_only_indices,
            'removed_count': summary.removed_count,
        })
    return summary

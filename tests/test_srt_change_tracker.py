# -*- coding: utf-8 -*-
'''Đối chiếu app.services.srt_change_tracker với bản đã phát hành.

Module này quyết định lần sửa phụ đề nào phải gọi TTS lại và lần sửa nào chỉ đổi
timestamp — sai một cái là tốn tiền API hoặc render ra tiếng lệch hình.
'''
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from _parity import block_modules, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.srt_change_tracker'

SRT_A = ("1\n00:00:01,000 --> 00:00:02,000\nA\n\n"
         "2\n00:00:03,000 --> 00:00:04,000\nB\n\n"
         "3\n00:00:05,000 --> 00:00:06,000\nC\n")

# (trước, sau) — mỗi cặp là một ý định sửa khác nhau của người dùng
PAIRS = [
    (SRT_A, SRT_A),
    ('', ''),
    ('', SRT_A),
    (SRT_A, ''),
    (SRT_A, SRT_A.replace('>00:02,000', '>00:02,500')),          # đổi độ dài cue 1
    (SRT_A, SRT_A.replace('00:00:03,000', '00:00:03,500')),      # chỉ đổi giờ cue 2
    (SRT_A, SRT_A.replace('\nB\n', '\nb\n')),                    # đổi chữ cue 2
    (SRT_A, SRT_A + "\n4\n00:00:07,000 --> 00:00:08,000\nD\n"),  # thêm cue
    (SRT_A, "1\n00:00:01,000 --> 00:00:02,000\nA\n\n"
            "2\n00:00:03,000 --> 00:00:04,000\nC\n"),            # xoá cue
    (SRT_A, SRT_A.replace('\nC\n', '\n  \n')),                   # chữ rỗng sau khi strip
    ("1\n00:00:01,000 --> 00:00:02,000\nXin chào\n",
     "1\n00:00:01,000 --> 00:00:02,000\nXin chào\n"),            # unicode y hệt
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n\n2\n00:00:02,000 --> 00:00:03,000\nB\n",
     "1\n00:00:02,000 --> 00:00:03,000\nB\n\n2\n00:00:01,000 --> 00:00:02,000\nA\n"),
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n\n2\n00:00:03,000 --> 00:00:04,000\nB\n",
     "1\n00:00:01,000 --> 00:00:02,000\nA\n"),                   # xoá 1 cue giữa
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n",
     "1\n00:00:01,000 --> 00:00:02,001\nA\n"),                   # lệch 1ms -> dưới ngưỡng
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n",
     "1\n00:00:01,000 --> 00:00:02,010\nA\n"),                   # lệch 10ms -> qua ngưỡng
    ("rác không phải srt", "cũng rác"),
]


def _summary(mod, before, after):
    s = mod.compare_srt_text(before, after)
    return (s.changed, s.old_count, s.new_count, s.tts_rebuild_indices,
            s.timeline_only_indices, s.removed_count, s.tts_rebuild_count,
            s.timeline_only_count,
            [(c.kind, c.old_index, c.new_index, c.old_text, c.new_text) for c in s.changes])


def test_dataclass_fields_match_reference():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a = rep.CueChange('text', 1, 2, 'x', 'y')
    b = ref.CueChange('text', 1, 2, 'x', 'y')
    assert repr(a) == repr(b), f'{a!r} != {b!r}'
    empty = rep.SrtEditSummary()
    assert empty.tts_rebuild_indices == [] and empty.changes == []
    assert empty.timeline_only_indices is not empty.changes
    assert (empty.tts_rebuild_count, empty.timeline_only_count, empty.journal_path) == (0, 0, None)


def test_same_time_threshold():
    bad = same_result(DOTTED, '_same_time', [
        ((0.0, 0.0), {}), ((0.0, 0.001), {}), ((0.0, 0.002), {}), ((0.0, 0.0021), {}),
        ((1.5, 1.5 - 0.002), {}), ((0.0, 0.01), {}), (('1.5', 1.5), {}),
        ((None, 1.0), {}), (('a', 'b'), {}), ((-1.0, 1.0), {})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_text_sha256():
    bad = same_result(DOTTED, '_text_sha256', [
        (('',), {}), ((None,), {}), (('Xin chào',), {}), (('a\n\n',), {}),
        (('  ',), {}), (('́',), {}), ((0,), {})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_compare_srt_text():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for before, after in PAIRS:
        # bản đã cài có pysrt, máy test thì không -> chặn để hai bên cùng một nhánh parse
        with block_modules('pysrt'):
            got, want = _summary(rep, before, after), _summary(ref, before, after)
        assert got == want, (before, after, got, want)


def test_classify_pair_directly():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    cases = [
        ((1.0, 2.0, 'A'), (1.0, 2.0, 'A')),        # không đổi gì
        ((1.0, 2.0, 'A'), (1.0, 2.0, 'B')),        # đổi chữ
        ((1.0, 2.0, 'A'), (1.0, 3.0, 'A')),        # đổi độ dài
        ((1.0, 2.0, 'A'), (2.0, 3.0, 'A')),        # trượt cả cụm -> chỉ timeline
        ((1.0, 2.0, 'A'), (1.0, 2.001, 'A')),      # dưới ngưỡng 2ms
        ((1.0, 2.0, 'A'), (1.5, 2.0, 'A')),        # end giữ nguyên, start đổi
    ]
    for old_spec, new_spec in cases:
        rows = {}
        for tag, m in (('rep', rep), ('ref', ref)):
            summary = m.SrtEditSummary()
            old = m.SrtCue(1, old_spec[0], old_spec[1], old_spec[2])
            new = m.SrtCue(2, new_spec[0], new_spec[1], new_spec[2])
            m._classify_pair(old, new, summary)
            rows[tag] = (summary.tts_rebuild_indices, summary.timeline_only_indices,
                         [(c.kind, c.old_index, c.new_index) for c in summary.changes])
        assert rows['rep'] == rows['ref'], (old_spec, new_spec, rows)


def test_record_srt_edit_matches_reference():
    '''Ghi nhật ký sửa SRT: hai bản phải đi tới cùng một kết quả.

    Hiện cả hai đều dừng ở bước ``DependencyManifest.record()`` vì
    ``app/services/artifact_manifest.py`` trong repo vẫn còn hỏng chữ ký (thiếu
    default của ``metadata``/``save``) — cùng một lỗi nên vẫn so được.  Phần nhật
    ký được ghi TRƯỚC bước đó nên cũng so được nội dung.
    '''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    tmp = Path(tempfile.mkdtemp())
    src = tmp / 'demo.srt'
    src.write_text(SRT_A, encoding='utf-8')
    after = SRT_A.replace('\nB\n', '\nb\n')
    bad = same_result(DOTTED, 'record_srt_edit', [
        ((str(src), SRT_A, SRT_A), {}),
        ((str(src), SRT_A, ''), {}),
        (('', SRT_A, SRT_A), {}),
        ((str(src), SRT_A, after), {})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]

    journals = {}
    for tag, mod in (('rep', rep), ('ref', ref)):
        same = mod.record_srt_edit(str(src), SRT_A, SRT_A)     # không đổi gì → không ghi
        assert same.changed is False and same.journal_path is None
        try:
            mod.record_srt_edit(str(src), SRT_A, after)
        except TypeError as exc:
            assert 'save' in str(exc), exc
        key = mod.stable_fingerprint({'source': str(src.resolve())})[:24]
        journal = (Path(tempfile.gettempdir()) / 'winterboy_tts_artifacts' / 'srt_edits'
                   / f"{key}_{mod._text_sha256(after)[:16]}.json")
        assert journal.is_file(), journal
        journals[tag] = json.loads(journal.read_text(encoding='utf-8'))
    a, b = journals['rep'], journals['ref']
    assert sorted(a) == sorted(b) == sorted(
        ['version', 'source', 'saved_at', 'before_sha256', 'after_sha256', 'old_count',
         'new_count', 'tts_rebuild_indices', 'timeline_only_indices', 'removed_count',
         'changes']), (a, b)
    for key in sorted(a):
        if key != 'saved_at':
            assert a[key] == b[key], (key, a[key], b[key])
    change, = a['changes']
    assert change['kind'] == 'text' and change['old_text'] == 'B' and change['new_text'] == 'b'
    assert change['old_index'] == change['new_index']
    assert a['tts_rebuild_indices'] == [change['new_index']]
    assert a['timeline_only_indices'] == [] and a['removed_count'] == 0
    assert a['version'] == 1 and a['old_count'] == a['new_count'] == 3
    assert a['before_sha256'] == rep._text_sha256(SRT_A)


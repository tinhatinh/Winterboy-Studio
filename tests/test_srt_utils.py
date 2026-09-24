# -*- coding: utf-8 -*-
'''Đối chiếu app.services.srt_utils với bản đã phát hành.

srt_utils là nền của cả luồng lồng tiếng (parse SRT, viết SRT, xuống dòng sub),
nên khôi phục nó trước và dùng làm mẫu cho các module khác.
'''
from __future__ import annotations

import tempfile
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.srt_utils'

SRT_SAMPLE = (
    "1\n00:00:01,000 --> 00:00:02,500\nXin chào\n\n"
    "2\n00:00:02,500 --> 00:00:03,000\nhai dòng\nkết thúc\n\n")

SRT_EDGE = [
    '',
    '   \n  ',
    'not an srt at all',
    "1\n00:00:05,000 --> 00:00:05,000\na\n",                      # end == start
    "1\n00:00:05,000 --> 00:00:02,000\na\n",                      # end < start
    "1\n00:00:01,000 --> 00:00:02,000\nA\n\n1\n00:00:03,000 --> 00:00:04,000\nB\n",
    "```srt\n1\n00:00:01,000 --> 00:00:02,000\nA\n```",           # fenced markdown
    "1\n00:00:01.000 --> 00:00:02.000\nchấm thay phẩy\n",
    "1\n00:00:01,000 --> 00:00:02,000\n",                         # thiếu text
    "1\n00:00:01,000 --> 00:00:02,000\ncó 2 dòng\ndư\n\n2\n00:00:02,000 --> 00:00:03,000\nkế\ttiếp\n",
    "1\n0:0:1,0 --> 0:0:2,0\nkhông pad số 0\n",
]

TS_EDGE = ['00:00:00,000', '00:00:01,500', '01:02:03,456', 'garbage', '', '00:00:01.000',
           '0:0:1,0', '99:99:99,999']

WRAP_EDGE = [
    '', '   ', 'ngắn', 'a' * 22, 'a' * 23, 'a' * 72, 'một ' * 30,
    'một đoạn văn rất dài cần phải xuống dòng vì quá số ký tự cho phép của một dòng phụ đề',
    'học máy lượng tử và rối lượng', 'x' * 200, 'không\ncó\nsẵn\nxuống\ndòng',
    'tab\tvà\hkhoảng trắng lạ', '    leading and trailing    ',
]


def _cues(mod, raw):
    return mod.parse_srt_string(raw)


def test_srtcue_fields():
    ref = ref_module(DOTTED)
    rep = repo_module(DOTTED)
    a = rep.SrtCue(1, 0.0, 2.5, 'x')
    b = ref.SrtCue(1, 0.0, 2.5, 'x')
    assert repr(a) == repr(b), f'{a!r} != {b!r}'
    assert a.duration_s == b.duration_s == 2.5, (a.duration_s, b.duration_s)


def test_format_ts():
    bad = same_result(DOTTED, 'format_ts', [((v,), {}) for v in
                                            [-1, 0, 0.0004, 1.5, 59.999, 60, 3661.5, 359999.999]])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_parse_ts():
    bad = same_result(DOTTED, 'parse_ts', [((v,), {}) for v in TS_EDGE])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_text():
    cases = [((t,), {}) for t in WRAP_EDGE]
    cases += [((t,), {'max_chars': 10}) for t in WRAP_EDGE]
    cases += [((t,), {'max_chars': 8, 'max_lines': 1}) for t in WRAP_EDGE]
    cases += [((t,), {'max_chars': 42, 'max_lines': 2}) for t in WRAP_EDGE]
    cases += [(('',), {'max_chars': 5, 'max_lines': 2}), ((None,), {})]
    bad = same_result(DOTTED, 'wrap_subtitle_text', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_parse_srt_string():
    # bản đã cài có pysrt, máy test thì không -> chặn để cả hai cùng chạy nhánh regex
    bad = same_result(DOTTED, 'parse_srt_string', [((t,), {}) for t in SRT_EDGE]
                      + [((SRT_SAMPLE,), {})], block=('pysrt',))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_cues_to_plain_lines():
    def build(mod, raw):
        return mod.cues_to_plain_lines(mod.parse_srt_string(raw))
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a = build(rep, SRT_SAMPLE)
    b = build(ref, SRT_SAMPLE)
    assert a == b, f'{a!r} != {b!r}'


def test_write_and_load_roundtrip():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    cues = ref.parse_srt_string(SRT_SAMPLE)
    tmp = Path(tempfile.mkdtemp())
    pa, pb = tmp / 'repo.srt', tmp / 'ref.srt'
    rep.write_srt([rep.SrtCue(c.index, c.start_s, c.end_s, c.text) for c in cues], pa)
    ref.write_srt(cues, pb)
    assert pa.read_text(encoding='utf-8') == pb.read_text(encoding='utf-8'), \
        (pa.read_text(encoding='utf-8'), pb.read_text(encoding='utf-8'))
    got = repo_module(DOTTED).load_srt(str(pa))
    want = ref_module(DOTTED).load_srt(str(pb))
    assert [tuple(vars(c).items()) for c in got] == [tuple(vars(c).items()) for c in want]
    assert repo_module(DOTTED).load_srt(str(tmp / 'khong-ton-tai.srt')) == []


def test_load_srt_missing_file():
    bad = same_result(DOTTED, 'load_srt', [(('/khong/co.srt',), {}), (('',), {})],
                      block=('pysrt',))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]

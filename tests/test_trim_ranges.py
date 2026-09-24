# -*- coding: utf-8 -*-
'''Đối chiếu app.services.trim_ranges với bản đã phát hành.

Decompyle++ dựng được chữ ký nhưng thân hàm thì mất (``parse_timecode`` thành
``pass``) và ``normalize_trim_segments`` ra mã đọc được nhưng phá dữ liệu
(``raw_start = str('').strip()`` -> mọi In/Out đều rỗng). Nên test ở đây so cả
giá trị trả về lẫn thông báo lỗi, không chỉ kiểu exception.
'''
from __future__ import annotations

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.trim_ranges'

TIMECODES = [
    None, '', '   ', '0', '5', '5.5', '5,5', '5.05', 'abc', '0:05', '1:30', '01:30',
    '1:30:15', '1:30:15.500', '1:30:15,500', '0:00:02,500', ':', '::', '1:', ':30',
    '1:2:3:4', '1:2:3:4:5', '-3', '1:-5', '60:60', '0:60', '1:60', '1:75', '0:59.999',
    '99:99:99', 'inf', 'nan', '-inf', '1e3', '0x10', '1.2.3', '+5', '5.', '.5',
    '  12  ', '1 : 2', '1:  2  :3', '999999999999', '2:59:59.5', '0:0:0,04',
    0, 0.0, 12, 12.5, True, False, [], {}, (1, 2),
]

# Mỗi phần tử là (raw_segments, kwargs_of_source_duration).
SEGMENTS = [
    ([], {}),
    ([], {'source_duration': 5}),
    (({'start': 1, 'end': 2},), {'source_duration': 30}),
    (None, {}),
    ('chuỗi', {}),
    ({'start': '0'}, {}),
    (({'start': 1},), {}),
    ([{}], {}),
    (['không phải dict'], {}),
    ([1, 2], {}),
    ([{'start': '0', 'end': '5'}], {}),
    ([{'start': '0', 'end': '5'}], {'source_duration': 10}),
    ([{'start': '0'}], {'source_duration': 10}),
    ([{'start': '0'}], {}),
    ([{'start': '0'}], {'source_duration': 0}),
    ([{'start': '0'}], {'source_duration': None}),
    ([{'start': '', 'end': ''}], {'source_duration': 12.0}),
    ([{'start': None, 'end': None}], {'source_duration': 0}),
    ([{'end': '5'}], {}),
    ([{'end': '5'}], {'source_duration': 3}),
    ([{'start': '5', 'end': '1'}], {}),
    ([{'start': '5', 'end': '5'}], {}),
    ([{'start': '5', 'end': '5.03'}], {}),
    ([{'start': '5', 'end': '5.04'}], {}),
    ([{'start': '5', 'end': '5.05'}], {}),
    ([{'start': '5', 'end': '5.04'}], {'source_duration': 6}),
    ([{'start': 'abc', 'end': '5'}], {}),
    ([{'start': '0', 'end': 'xyz'}], {}),
    ([{'start': '0', 'end': '-1'}], {}),
    ([{'start': '1:70', 'end': '2:00'}], {}),
    ([{'start': '-1', 'end': '2'}], {}),
    ([{'start': '10', 'end': '20'}], {'source_duration': 10}),
    ([{'start': '10', 'end': '20'}], {'source_duration': 15}),
    ([{'start': '0', 'end': '20'}], {'source_duration': 15}),
    ([{'start': '0', 'end': '15.04'}], {'source_duration': 15}),
    ([{'start': '0', 'end': '15.06'}], {'source_duration': 15}),
    ([{'start': '0', 'end': '999'}], {'source_duration': 15}),
    ([{'start': '0', 'end': '0.5'}], {'source_duration': 0.05}),
    ([{'start': '0:00:10,500', 'end': '0:00:20'}], {'source_duration': 30}),
    ([{'name': '   ', 'start': 0, 'end': 2}], {}),
    ([{'name': 'Đoạn mở đầu', 'start': 0, 'end': 2}], {}),
    ([{'name': 0, 'start': 0, 'end': 2}], {}),
    ([{'name': 5, 'start': 0, 'end': 2}], {}),
    ([{'name': True, 'start': 0, 'end': 2}], {}),
    ([{'start': 0, 'end': 1 / 3}], {'source_duration': 1}),
    ([{'start': 1e-9, 'end': 2e-9}], {}),
    ([{'start': '0', 'end': '2'}, {'start': '1', 'end': '3'}], {'source_duration': 4}),
    ([{'start': '0', 'end': '2'}, 'x'], {}),
    ([{'start': '0', 'end': '2'}, {'start': 'zz', 'end': '9'}], {}),
    ([{'start': 100, 'end': 200}], {'source_duration': 'abc'}),
    ([{'start': 100, 'end': 200}], {'source_duration': [3]}),
]


def _shot(fn, args, kwargs):
    '''Kết quả + thông báo lỗi + __cause__, để so cả câu báo lỗi bằng tiếng Việt.'''
    try:
        value = fn(*args, **kwargs)
        return ('ok', repr(value), type(value).__name__)
    except Exception as exc:                              # noqa: BLE001 - lỗi cũng là hành vi
        return ('err', type(exc).__name__, str(exc), repr(exc.__cause__))


def _compare(func, cases):
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    fn_ref, fn_rep = getattr(ref, func), getattr(rep, func)
    bad = []
    for args, kwargs in cases:
        a, b = _shot(fn_rep, args, kwargs), _shot(fn_ref, args, kwargs)
        if a != b:
            bad.append((args, kwargs, a, b))
    return bad


def test_parse_timecode_values():
    bad = same_result(DOTTED, 'parse_timecode', [((v,), {}) for v in TIMECODES])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_parse_timecode_default():
    bad = same_result(DOTTED, 'parse_timecode',
                      [((v,), {'default': 1.5}) for v in TIMECODES]
                      + [((None,), {'default': 0}), (('',), {'default': 0.0}),
                         (('',), {'default': None}), (('  ',), {'default': 3}),
                         (('abc',), {'default': 9.0}), ((-1,), {'default': 9.0})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_parse_timecode_messages():
    bad = _compare('parse_timecode', [((v,), {}) for v in TIMECODES])
    assert not bad, [(a, k, r, f) for a, k, r, f in bad]


def test_normalize_trim_segments_types():
    bad = same_result(DOTTED, 'normalize_trim_segments',
                      [((raw,), kwargs) for raw, kwargs in SEGMENTS])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_normalize_trim_segments_messages():
    bad = _compare('normalize_trim_segments', [(((raw,), kwargs)) for raw, kwargs in SEGMENTS])
    assert not bad, [(a, k, r, f) for a, k, r, f in bad]


def test_normalize_keeps_input_order_and_overlap():
    '''Thứ tự giữ nguyên, chồng lấn cho phép — đây là điểm dễ mất khi dịch ngược.'''
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    raw = [{'start': '5', 'end': '9'}, {'start': '0', 'end': '20'}, {'start': '8', 'end': '8.5'}]
    got, want = rep.normalize_trim_segments(raw, source_duration = 30), \
        ref.normalize_trim_segments(raw, source_duration = 30)
    assert got == want == [{'start': 5.0, 'end': 9.0, 'name': 'Đoạn 1'},
                           {'start': 0.0, 'end': 20.0, 'name': 'Đoạn 2'},
                           {'start': 8.0, 'end': 8.5, 'name': 'Đoạn 3'}], (got, want)


def test_normalize_does_not_mutate_input():
    rep = repo_module(DOTTED)
    raw = [{'start': '0:10', 'end': '0:20'}]
    rep.normalize_trim_segments(raw, source_duration = 30)
    assert raw == [{'start': '0:10', 'end': '0:20'}], raw


def test_normalize_name_survives():
    '''Bản dịch ngược cũ bỏ mất 'name', luôn ghi 'Đoạn n' — test này bắt lỗi đó.'''
    rep = repo_module(DOTTED)
    got = rep.normalize_trim_segments([{'start': 0, 'end': 2, 'name': 'Mở đầu'}])
    assert got[0]['name'] == 'Mở đầu', got

# -*- coding: utf-8 -*-
'''Test chính cái máy quét "hỏng im lặng".

Scanner là công cụ chốt của cả quy trình khôi phục: nếu nó dương tính giả thì người
ta tắt nó, nếu âm tính giả thì mã hỏng lọt qua. Cả hai đều phải có fixture giữ chân.
'''
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'tools'))

import check_source as cs                                    # noqa: E402

FIXTURE = '''
def f(text):
    if not text:
        text
    text = ''.replace('a', 'b')
    raw = None.read_text()
    candidate_dirs
    return text


def g(value):
    if not value:
        return 0
    return value
'''

# những dạng ĐÚNG nhưng dễ bị scanner hiểu nhầm
CLEAN = '''
def ok_comprehension(job):
    return [
        path
        for path in job.glob('tts/*.wav')
        if path.is_file()]


def ok_unpack(line):
    w, h = probe(line)
    return w


def ok_guard(text):
    if not text:
        if len(text) == 0:
            return ''
        return text
    return 'x'


def ok_call(target):
    if not target:
        raise ValueError('trống')
    return target.write('a')


def ok_multi_arg(a, b):
    return call(a,
                b)
'''


def _scan(source):
    tmp = REPO / 'output' / '_damage_fixture.py'
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(source, encoding='utf-8')
    try:
        found = cs.damage_scan([tmp.resolve()])
        # key là đường dẫn tương đối so với repo (dấu \ trên Windows), nên lấy value trực tiếp
        return next(iter(found.values()), [])
    finally:
        tmp.unlink(missing_ok=True)


def test_scanner_finds_every_damage_kind():
    hits = _scan(FIXTURE)
    labels = {h[1] for h in hits}
    assert len(hits) == 4, hits
    assert labels == {'nhánh if mất vế gán', 'gán từ chuỗi rỗng có phương thức',
                      'gán từ None.read/None attribute', 'câu chỉ gồm một tên biến'}, hits


def test_scanner_has_no_false_positives_on_valid_code():
    hits = _scan(CLEAN)
    assert not hits, hits


def test_restored_modules_are_clean_of_markers():
    '''Module đã khôi phục thì không được còn dòng cảnh báo của Decompyle++.'''
    import glob
    for path in glob.glob(str(REPO / 'app' / 'services' / 'srt_utils.py')):
        assert 'Decompyle' not in Path(path).read_text(encoding='utf-8')

# -*- coding: utf-8 -*-
'''Đối chiếu app.services.job_workspace với bản đã phát hành.

Module này chọn nơi mọi dữ liệu trung gian của một lần render được ghi xuống, nên
tên thư mục và hậu tố chống trùng phải giống hệt.

Hai bản được nạp vào cùng một tiến trình nên dùng chung ``JOBS_ROOT`` vì
``WINTERBOY_PROJECT_ROOT`` được ghim ở đầu file.  Vì vậy mỗi lần gọi
``create_job_workspace`` đều dọn kho job trước, rồi mới so tên thật.
'''
from __future__ import annotations

import os
import shutil
import tempfile
import types
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.job_workspace'

# Pin hai bản vào cùng một PROJECT_ROOT tạm, nếu không mỗi bên viết một chỗ khác nhau
_TMP = Path(tempfile.mkdtemp())
os.environ['WINTERBOY_PROJECT_ROOT'] = str(_TMP)

FIXED_STAMP = '20250101_000000'
CHILDREN = ['mp4', 'srt', 'stt', 'translated', 'tts']

NAMES = [
    'demo.mp4', 'Xin Chào.mp4', '  khoảng trắng  ', '...', '---', 'a/b/c',
    'C:\\video\\test.mp4', 'dấu tiếng việt ăêôư', '🎞 phim.mp4', 'x' * 60,
    '123', '_leading', 'trailing_', 'a\tb', 'video-final_v2.1.mp4',
    '***', '<<<>>>', 'réf. #42', '', '   ', '。、！',
]


def _clean_jobs(mod):
    for child in mod.JOBS_ROOT.iterdir():
        shutil.rmtree(child, ignore_errors=True)


def test_safe_name():
    cases = [((v,), {}) for v in NAMES]
    cases += [((v,), {'fallback': 'kind'}) for v in NAMES]
    cases += [(('',), {'fallback': ''}), ((None,), {}), ((123,), {}), ((0,), {})]
    bad = same_result(DOTTED, '_safe_name', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    rep = repo_module(DOTTED)
    assert len(rep._safe_name('x' * 200)) == 24
    assert rep._safe_name('demo.mp4') == 'demo.mp4'


def test_module_roots_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in ('OUTPUT_ROOT', 'JOBS_ROOT', 'DEFAULT_VIDEO_OUTPUT', 'STORY_PROJECTS_ROOT'):
        assert getattr(rep, name) == getattr(ref, name), name
    assert str(rep.JOBS_ROOT) == str((_TMP / 'output' / 'jobs').resolve())
    assert rep.JOBS_ROOT.is_dir(), 'import phải tạo sẵn kho job'
    assert rep.DEFAULT_VIDEO_OUTPUT.is_dir() and rep.STORY_PROJECTS_ROOT.is_dir()
    assert (rep.OUTPUT_ROOT / 'voice_library').is_dir()


def test_create_job_workspace_name_is_identical():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for kind, source in (('stt', 'demo.mp4'), ('render', 'phim_final.mp4'),
                         ('tts', None), ('dịch', 'Xin Chào.mp4'), ('stt', '...'),
                         ('srt', 12345), ('x', 'C:\\a\\b\\phim.mkv'),
                         ('stt', 'a' * 80), ('job', 'khong-co-đuôi')):
        rows = {}
        for tag, mod in (('rep', rep), ('ref', ref)):
            _clean_jobs(mod)
            frozen = mod.time
            mod.time = types.SimpleNamespace(strftime=lambda fmt: FIXED_STAMP)
            try:
                got = mod.create_job_workspace(kind, source)
                rows[tag] = (got.name, sorted(p.name for p in got.iterdir()),
                             got.parent == mod.JOBS_ROOT, got.is_dir())
            finally:
                mod.time = frozen
        assert rows['rep'] == rows['ref'], (kind, source, rows)
        assert rows['rep'][0].startswith(FIXED_STAMP + '_'), rows['rep']
        assert rows['rep'][1] == CHILDREN, rows['rep']
    # digest phụ thuộc nguồn: đổi đuôi file cũng đổi tên
    name_a = _name_of(rep, 'stt', 'demo.mp4')
    name_b = _name_of(rep, 'stt', 'demo.mkv')
    assert name_a.split('_')[-1] != name_b.split('_')[-1]


def _name_of(mod, kind, source):
    _clean_jobs(mod)
    frozen = mod.time
    mod.time = types.SimpleNamespace(strftime=lambda fmt: FIXED_STAMP)
    try:
        return mod.create_job_workspace(kind, source).name
    finally:
        mod.time = frozen


def test_create_job_workspace_avoids_collisions():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    rows = {}
    for tag, mod in (('rep', rep), ('ref', ref)):
        _clean_jobs(mod)
        frozen = mod.time
        mod.time = types.SimpleNamespace(strftime=lambda fmt: FIXED_STAMP)
        try:
            first = mod.create_job_workspace('stt', 'demo.mp4')
            for n in ('2', '3'):
                (mod.JOBS_ROOT / f'{first.name}_{n}').mkdir()
            nxt = mod.create_job_workspace('stt', 'demo.mp4')
            later = mod.create_job_workspace('dịch', 'demo.mp4')
            rows[tag] = (first.name, nxt.name, later.name,
                         sorted(p.name for p in nxt.iterdir()), nxt.is_dir(), later.is_dir())
        finally:
            mod.time = frozen
    assert rows['rep'] == rows['ref'], rows
    first, nxt, later = rows['rep'][:3]
    assert nxt == f'{first}_4', rows['rep']
    assert later.split('_')[2] == 'dịch' and later.endswith(first.split('_')[-1])
    assert rows['rep'][3] == CHILDREN


def test_is_managed_job_path():
    rep = repo_module(DOTTED)
    inside = _dir_of(rep, 'stt', 'demo.mp4')
    cases = [((str(inside),), {}), ((str(inside / 'a' / 'b'),), {}),
             ((str(rep.JOBS_ROOT),), {}), ((str(_TMP),), {}), (('C:\\Windows',), {}),
             (('',), {}), ((None,), {}), ((123,), {}), ((str(_TMP / 'other'),), {})]
    bad = same_result(DOTTED, 'is_managed_job_path', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    assert rep.is_managed_job_path(inside) is True
    assert rep.is_managed_job_path(_TMP) is False


def _dir_of(mod, kind, source):
    _clean_jobs(mod)
    return mod.create_job_workspace(kind, source)

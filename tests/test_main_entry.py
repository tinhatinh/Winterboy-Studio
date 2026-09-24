# -*- coding: utf-8 -*-
'''Đối chiếu main.py với bản đã phát hành.

Chỉ kiểm phần an toàn để chạy trong tiến trình test: _SafeStream. Mấy hàm chạm
stdio toàn cục / logging / mutex Win32 phải chạy ở tiến trình riêng để không làm
hỏng stdout của chính bộ test.
'''
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from _parity import REPO, RefMissing, ref_module, repo_module  # noqa: F401

DOTTED = 'main'


def _both():
    return repo_module(DOTTED), ref_module(DOTTED)


def _outcome(fn, *a):
    try:
        return ('ok', fn(*a))
    except Exception as exc:                              # noqa: BLE001
        return ('err', type(exc).__name__)


def test_safestream_matches_reference():
    rep, ref = _both()
    for target in (io.StringIO(), io.StringIO(), None):
        a = rep._SafeStream(target)
        b = ref._SafeStream(target)
        for s in ('xin', '', None, 'a' * 100, 'tiếng Việt ă â', 0, 12):
            ra, rb = _outcome(a.write, s), _outcome(b.write, s)
            assert ra == rb, (s, ra, rb)
        assert _outcome(a.writelines, ['x', 'y']) == _outcome(b.writelines, ['x', 'y'])
        assert _outcome(a.flush) == _outcome(b.flush)
    # cờ giao diện stream
    a, b = rep._SafeStream(), ref._SafeStream()
    for attr in ('encoding', 'errors'):
        assert getattr(a, attr) == getattr(b, attr), attr
    for meth in ('isatty', 'readable', 'writable', 'seekable'):
        assert getattr(a, meth)() == getattr(b, meth)(), meth
    assert a.reconfigure(encoding='utf-8') == b.reconfigure(encoding='utf-8') == None


def test_safestream_writes_through():
    rep, ref = _both()
    buf_r, buf_f = io.StringIO(), io.StringIO()
    rep._SafeStream(buf_r).write('repo')
    ref._SafeStream(buf_f).write('ref')
    assert (buf_r.getvalue(), buf_f.getvalue()) == ('repo', 'ref')


def _run_child(code):
    return subprocess.run([sys.executable, '-c', code], cwd=str(REPO), capture_output=True,
                          text=True, encoding='utf-8', errors='replace', timeout=120)


def test_ensure_safe_stdio_in_subprocess():
    '''Không được đụng stdio của tiến trình test.

    Sau khi _ensure_safe_stdio() thay sys.stdout bằng _SafeStream không đích đến thì
    print() đi vào hư không, nên kết quả phải ghi ra file.
    '''
    marker = REPO / 'output' / 'stdio_probe.txt'
    marker.parent.mkdir(exist_ok=True)
    marker.unlink(missing_ok=True)
    out = _run_child(
        'import sys, pathlib; sys.stdin=None; sys.stdout=None; sys.stderr=None;'
        'import main; main._ensure_safe_stdio();'
        'pathlib.Path(r"' + str(marker) + '").write_text('
        'f"{type(sys.stdin).__name__} {type(sys.stdout).__name__} {type(sys.stderr).__name__}\\n"'
        'f"{sys.stderr._target is sys.stdout}", encoding="utf-8")')
    assert out.returncode == 0, out.stderr[-400:]
    assert marker.is_file(), 'con không ghi được kết quả'
    lines = marker.read_text(encoding='utf-8').split('\n')
    assert lines[0] == 'StringIO _SafeStream _SafeStream', lines[0]
    assert lines[1] == 'True', lines[1]


def test_setup_logging_in_subprocess():
    out = _run_child('import logging, main; main.setup_logging();'
                     'logging.getLogger("t").info("ok");'
                     'print(len(logging.getLogger().handlers))')
    assert out.returncode == 0, out.stderr[-400:]
    assert out.stdout.strip().splitlines()[-1] == '2', out.stdout[-300:]


def test_single_instance_mutex_is_stable():
    '''Lần gọi thứ hai trong cùng tiến trình phải báo "đã có instance khác".'''
    out = _run_child('import main;'
                     'r1 = main._activate_existing_instance();'
                     'r2 = main._activate_existing_instance();'
                     'print(r1, r2)')
    assert out.returncode == 0, out.stderr[-400:]
    first, second = out.stdout.split()[-2:]
    assert second == 'True', (first, second)
    # first là False trừ khi app thật đang chạy sẵn trên máy
    assert first in ('True', 'False'), first

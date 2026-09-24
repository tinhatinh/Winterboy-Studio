# -*- coding: utf-8 -*-
'''Đối chiếu app.services.log_cleaner với bản đã phát hành.

Hai hàm ở đây đều đụng filesystem nên test dựng cây thư mục giả rồi trỏ
APP_ROOT / REPO_ROOT của CẢ HAI bản vào đó. Không có mạng, không có GUI.
'''
from __future__ import annotations

import tempfile
from pathlib import Path

from _parity import ref_module, repo_module

DOTTED = 'app.services.log_cleaner'

ROTATED = 'a' * 4096
SMALL = 'ngắn'


def _pair():
    return ref_module(DOTTED), repo_module(DOTTED)


def _build():
    '''Cây thư mục giả theo bố cục repo: APP_ROOT=<repo>/app, REPO_ROOT=<repo>.

    Mỗi lần gọi trả về một cây mới để repo và ref không phá lẫn nhau.
    '''
    repo = Path(tempfile.mkdtemp())
    root = repo / 'app'
    root.mkdir()
    logs = root / 'logs'
    logs.mkdir()
    (logs / 'app.log').write_text(ROTATED, encoding='utf-8')
    (logs / 'tiny.log').write_text(SMALL, encoding='utf-8')
    (logs / 'old.log.old').write_text('x' * 20, encoding='utf-8')
    (logs / 'notes.txt').write_text('ghi chu', encoding='utf-8')
    (logs / 'rolled.LOG.1').write_text('q' * 30, encoding='utf-8')
    (logs / 'khong-phai-log.md').write_text('# heading', encoding='utf-8')
    nested = logs / 'npm' / 'sau'
    nested.mkdir(parents=True)
    (nested / 'deep.log').write_text('d' * 500, encoding='utf-8')

    data_logs = repo / 'data' / 'logs'
    data_logs.mkdir(parents=True)
    (data_logs / 'repo.log').write_text('r' * 40, encoding='utf-8')

    temp = root / 'temp'
    temp.mkdir()
    (temp / 'one.wav').write_bytes(b'w' * 123)
    (temp / 'keepme.txt').write_text('gi lai', encoding='utf-8')
    sub = temp / 'mot-thu-muc'
    sub.mkdir()
    (sub / 'a.bin').write_bytes(b'a' * 10)
    (sub / 'b.bin').write_bytes(b'b' * 20)
    (sub / 'trung-gian').mkdir()

    cache = root / 'src' / '__pycache__'
    cache.mkdir(parents=True)
    (cache / 'x.cpython-312.pyc').write_bytes(b'pyc')
    return repo, root


def _point_at(mod, repo, root):
    mod.APP_ROOT = root
    mod.REPO_ROOT = repo


def _snapshot(root: Path):
    return sorted((str(p.relative_to(root)).replace('\\', '/'),
                   p.stat().st_size if p.is_file() else -1)
                  for p in root.rglob('*'))


def test_module_level_constants():
    '''APP_ROOT / REPO_ROOT phải là global cấp module để test trỏ được.'''
    ref, rep = _pair()
    assert isinstance(rep.APP_ROOT, type(ref.APP_ROOT))
    assert isinstance(rep.REPO_ROOT, type(ref.REPO_ROOT))
    assert rep.REPO_ROOT == rep.APP_ROOT.parent.parent, rep.REPO_ROOT
    assert ref.REPO_ROOT == ref.APP_ROOT.parent.parent, ref.REPO_ROOT


def test_clear_logs_flags_matrix():
    flags = [
        dict(), dict(clear_log_files=True, clear_temp=True, clear_pycache=True),
        dict(clear_log_files=False, clear_temp=False, clear_pycache=False),
        dict(clear_log_files=True, clear_temp=False, clear_pycache=False),
        dict(clear_log_files=False, clear_temp=True, clear_pycache=False),
        dict(clear_log_files=False, clear_temp=False, clear_pycache=True),
        dict(clear_log_files=False, clear_temp=True, clear_pycache=True)]
    ref, rep = _pair()
    for kw in flags:
        out = {}
        for label, mod in (('repo', rep), ('ref', ref)):
            repo, root = _build()
            _point_at(mod, repo, root)
            res = mod.clear_logs(**kw)
            out[label] = (res['log_files'], res['temp_dirs'], res['temp_bytes'],
                          sorted(str(e) for e in res['errors']), _snapshot(root),
                          _snapshot(repo / 'data'), sorted(res.keys()))
        assert out['repo'] == out['ref'], (kw, out['repo'], out['ref'])


def test_clear_logs_truncates_only_known_suffixes():
    ref, _ = _pair()
    repo, root = _build()
    _point_at(ref, repo, root)
    res = ref.clear_logs(clear_log_files=True, clear_temp=False, clear_pycache=False)
    logs = root / 'logs'
    for name in ('app.log', 'tiny.log', 'notes.txt', 'old.log.old'):
        assert (logs / name).read_text(encoding='utf-8') == '', name
    # suffix('.log.1').lower() == '.1' -> phần '.log.1' trong danh mục không bao giờ khớp
    assert (logs / 'rolled.LOG.1').read_text(encoding='utf-8') == 'q' * 30
    assert (logs / 'npm' / 'sau' / 'deep.log').read_text(encoding='utf-8') == ''
    assert (logs / 'khong-phai-log.md').read_text(encoding='utf-8') == '# heading'
    # rglob('*') có đệ quy, nên cả log của repo lẫn log lồng nhau đều bị cắt
    assert (repo / 'data' / 'logs' / 'repo.log').read_text(encoding='utf-8') == ''
    assert res['log_files'] == 6, res
    assert res['temp_bytes'] == 0 and res['temp_dirs'] == 0, res
    assert (root / 'temp' / 'one.wav').is_file()
    assert (root / 'src' / '__pycache__').is_dir()


def test_clear_logs_counts_temp_bytes():
    ref, _ = _pair()
    repo, root = _build()
    _point_at(ref, repo, root)
    res = ref.clear_logs(clear_log_files=False, clear_temp=True, clear_pycache=False)
    # one.wav 123 + keepme.txt 7 + mot-thu-muc(a=10 + b=20 + thư mục rỗng)
    assert res['temp_bytes'] == 123 + len('gi lai') + 30, res
    assert res['temp_dirs'] == 1, res
    assert res['log_files'] == 0, res
    assert res['errors'] == [], res
    assert not (root / 'temp' / 'mot-thu-muc').exists()
    assert not (root / 'temp' / 'one.wav').exists()
    assert (root / 'logs' / 'app.log').read_text(encoding='utf-8') == ROTATED
    assert (root / 'src' / '__pycache__').is_dir()


def test_clear_logs_pycache_flag():
    ref, _ = _pair()
    repo, root = _build()
    _point_at(ref, repo, root)
    res = ref.clear_logs(clear_log_files=False, clear_temp=False, clear_pycache=True)
    assert not (root / 'src' / '__pycache__').exists()
    assert (root / 'temp' / 'one.wav').is_file()
    assert (res['log_files'], res['temp_dirs'], res['temp_bytes'], res['errors']) == \
        (0, 0, 0, []), res


def test_clear_logs_survives_missing_roots():
    ref, rep = _pair()
    for label, mod in (('repo', rep), ('ref', ref)):
        base = Path(tempfile.mkdtemp())
        _point_at(mod, base / 'repo', base / 'app')
        res = mod.clear_logs(clear_log_files=True, clear_temp=True, clear_pycache=True)
        assert (res['log_files'], res['temp_dirs'], res['temp_bytes'], res['errors']) == \
               (0, 0, 0, []), (label, res)


def test_rotate_large_logs():
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        repo, root = _build()
        _point_at(mod, repo, root)
        logs = root / 'logs'
        before = (logs / 'app.log').read_text(encoding='utf-8')
        assert mod.rotate_large_logs(max_bytes=1000) is None
        out[label] = (before,
                      (logs / 'app.log').read_text(encoding='utf-8'),
                      (logs / 'app.log.old').is_file(),
                      (logs / 'app.log.old').read_text(encoding='utf-8'),
                      (logs / 'tiny.log').read_text(encoding='utf-8'),
                      (logs / 'tiny.log.old').is_file(),
                      (logs / 'npm' / 'sau' / 'deep.log').read_text(encoding='utf-8'),
                      (logs / 'old.log.old').read_text(encoding='utf-8'),
                      _snapshot(root))
    assert out['repo'] == out['ref'], out
    assert out['ref'][1] == '', out['ref']
    assert out['ref'][2] and out['ref'][3] == ROTATED, out['ref']
    assert out['ref'][4] == SMALL and not out['ref'][5], out['ref']
    # glob('*.log') không đệ quy -> log ở thư mục con không bị xoay
    assert out['ref'][6] == 'd' * 500, out['ref']
    assert out['ref'][7] == 'x' * 20, out['ref']


def test_rotate_replaces_existing_backup():
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        repo, root = _build()
        _point_at(mod, repo, root)
        logs = root / 'logs'
        (logs / 'app.log').write_text('n' * 3000, encoding='utf-8')
        (logs / 'app.log.old').write_text('cu', encoding='utf-8')
        mod.rotate_large_logs(max_bytes=1000)
        first = (logs / 'app.log.old').read_text(encoding='utf-8')
        second = (logs / 'app.log').read_text(encoding='utf-8')
        mod.rotate_large_logs(max_bytes=1000)
        out[label] = (first, second,
                      (logs / 'app.log.old').read_text(encoding='utf-8'),
                      (logs / 'app.log').read_text(encoding='utf-8'))
    assert out['repo'] == out['ref'], out
    assert out['ref'][0] == 'n' * 3000 and out['ref'][1] == '', out['ref']
    # lần hai: app.log đã rỗng nên không tới ngưỡng, backup giữ nguyên nội dung cũ
    assert out['ref'][2] == 'n' * 3000, out['ref']


def test_rotate_ignores_non_files():
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        repo, root = _build()
        _point_at(mod, repo, root)
        logs = root / 'logs'
        (logs / 'daimoi.log').mkdir()                 # *.log là thư mục -> bỏ qua
        assert mod.rotate_large_logs(max_bytes=10) is None
        assert (logs / 'daimoi.log').is_dir()
        out[label] = _snapshot(root)
    assert out['repo'] == out['ref'], out
    # rotate_large_logs không bao giờ đụng tới temp / __pycache__
    assert any(p.endswith('__pycache__') for p, _ in out['ref']), out['ref']

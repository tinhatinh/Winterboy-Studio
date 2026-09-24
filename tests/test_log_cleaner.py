# -*- coding: utf-8 -*-
'''Đối chiếu app.services.log_cleaner với bản đã phát hành.

Hai hàm ở đây đều đụng filesystem nên test dựng cây thư mục giả rồi trỏ
APP_ROOT / REPO_ROOT của CẢ HAI bản vào đó. Không có mạng, không có GUI.
'''
from __future__ import annotations

import tempfile
import types
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
    (root / 'systmp').mkdir()               # thế chỗ %TEMP% thật, xem _point_at
    return repo, root


# ``clear_logs`` tự ``import tempfile`` bên trong nên vá ``mod.tempfile`` là vô
# nghĩa — phải vá chính hàm của stdlib. Nhưng vá thường trực thì hỏng cả
# ``tempfile.mkdtemp`` của những test khác (nó tự lấy gettempdir để dựng cây giả,
# thành ra lồng nhau rồi "path not found"), nên chỉ vá trong lúc gọi clear_logs.
_TEMP_TARGET: list = []


def _clear(mod, **kw):
    """Gọi ``mod.clear_logs`` với %TEMP% tạm trỏ vào cây giả của test hiện hành."""
    orig = tempfile.gettempdir
    if _TEMP_TARGET:
        target = str(_TEMP_TARGET[0])
        tempfile.gettempdir = lambda: target
    try:
        return mod.clear_logs(**kw)
    finally:
        tempfile.gettempdir = orig


def _point_at(mod, repo, root):
    """Trỏ module vào cây giả — kể cả THƯ MỤC TEMP HỆ THỐNG.

    ``clear_logs`` không chỉ quét ``APP_ROOT/temp`` mà còn cộng cả kích thước
    ``tempfile.gettempdir()/winterboy_preview_audio``. Không chặn chỗ đó thì
    ``temp_bytes`` phụ thuộc %TEMP% lúc ấy đang có gì: chạy lẻ một file test thì
    xanh, chạy cả bộ thì đỏ tuỳ thứ tự — kiểu hỏng khó chịu nhất. Đã tái hiện
    chắc chắn: ném 4KB vào ``%TEMP%/winterboy_preview_audio`` làm ``temp_bytes``
    nhảy từ 160 lên 4159.
    """
    mod.APP_ROOT = root
    mod.REPO_ROOT = repo
    _TEMP_TARGET.clear()
    _TEMP_TARGET.append(root / 'systmp')   # _build() đã tạo; ở đây KHÔNG tạo gì thêm


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


def _temp_bytes(mod, *, stray: bool):
    """Một cây giả mới tinh -> chạy clear_logs MỘT lần -> trả temp_bytes.

    Phải dựng lại từ đầu mỗi lần: clear_logs xoá sạch APP_ROOT/temp nên gọi lần hai
    trên cùng cây thì số đo chỉ còn phần của %TEMP%.
    """
    repo, root = _build()
    stray_dir = root / 'systmp' / 'winterboy_preview_audio'
    stray_dir.mkdir(parents=True)
    if stray:
        (stray_dir / 'leftover.wav').write_bytes(b'x' * 64)
    _point_at(mod, repo, root)
    res = _clear(mod, clear_log_files=False, clear_temp=True, clear_pycache=False)
    assert res['errors'] == [], res['errors']
    return res['temp_bytes']


def test_clear_logs_tinh_ca_audio_preview_o_temp_he_thong():
    """File preview rớt trong %TEMP% được CỘNG vào temp_bytes, đúng 64 byte.

    Đây chính là cơ chế khiến test đếm số tuyệt đối từng đỏ khi %TEMP% của máy
    đang bẩn — và là lý do _point_at phải chặn gettempdir.
    """
    ref, rep = _pair()
    for label, mod in (('repo', rep), ('ref', ref)):
        base = _temp_bytes(mod, stray=False)
        with_file = _temp_bytes(mod, stray=True)
        assert with_file - base == 64, (label, base, with_file)


def test_clear_logs_truncates_only_known_suffixes():
    ref, _ = _pair()
    repo, root = _build()
    _point_at(ref, repo, root)
    res = _clear(ref, clear_log_files=True, clear_temp=False, clear_pycache=False)
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
    res = _clear(ref, clear_log_files=False, clear_temp=True, clear_pycache=False)
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
    res = _clear(ref, clear_log_files=False, clear_temp=False, clear_pycache=True)
    assert not (root / 'src' / '__pycache__').exists()
    assert (root / 'temp' / 'one.wav').is_file()
    assert (res['log_files'], res['temp_dirs'], res['temp_bytes'], res['errors']) == \
        (0, 0, 0, []), res


def test_clear_logs_survives_missing_roots():
    ref, rep = _pair()
    for label, mod in (('repo', rep), ('ref', ref)):
        base = Path(tempfile.mkdtemp())
        _point_at(mod, base / 'repo', base / 'app')
        res = _clear(mod, clear_log_files=True, clear_temp=True, clear_pycache=True)
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

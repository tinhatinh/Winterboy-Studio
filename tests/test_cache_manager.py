# -*- coding: utf-8 -*-
'''Đối chiếu app.services.cache_manager với bản đã phát hành (.pyc trong _internal).

cache_manager xóa dữ liệu thật, nên mọi test filesystem đều trỏ các root được
quản lý vào thư mục tạm riêng trong output/, và mỗi bên (repo / bản đã cài) chạy
trên một cây tạm khác nhau rồi so kết quả đã chuẩn hóa đường dẫn.

Trước khi nạp module, test dựng "shim" cho gói ``app.services`` trỏ thẳng vào
_internal: module cha trong repo vẫn còn hỏng cú pháp nên không import theo kiểu
thường được, còn .pyc đã phát hành thì nạp sạch. Nhờ vậy phụ thuộc của cả hai bên
đều giống nhau — biến duy nhất còn lại là file đang kiểm tra.
'''
from __future__ import annotations

import dataclasses
import inspect
import os
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

from _parity import INTERNAL, REPO, describe, fingerprint, ref_module, repo_module, same_result

DOTTED = 'app.services.cache_manager'
SCRATCH = REPO / 'output' / '_restore' / 'cache_manager'


# --------------------------------------------------------------------------- #
#  môi trường import
# --------------------------------------------------------------------------- #
def install_pkg_shim():
    '''Đăng ký package cha rỗng để ``import app.services.x`` không chạy __init__.py.'''
    pkg = INTERNAL / 'app'
    for name, path in (('app', pkg), ('app.services', pkg / 'services')):
        mod = sys.modules.get(name)
        if mod is None or not getattr(mod, '__path__', None):
            stub = types.ModuleType(name)
            stub.__path__ = [str(path)]
            sys.modules[name] = stub
    sys.modules.pop('app.services.cache_manager', None)


install_pkg_shim()


# --------------------------------------------------------------------------- #
# patch global của module (cả hai bên cùng một lúc qua run_both)
# --------------------------------------------------------------------------- #
def per_module(fn):
    '''Đánh dấu giá trị cần tính theo từng module đang được vá.'''
    fn._per_module = True
    return fn


def fake_locations(builder):
    '''Thay ``managed_locations()`` bằng builder(mod) — mỗi module có CacheLocation riêng.'''
    return per_module(lambda mod: (lambda: tuple(builder(mod))))


class patched:
    '''Gán tạm global cho một module rồi khôi phục khi thoát.'''

    def __init__(self, *targets, **values):
        self.targets = targets
        self.values = values
        self.saved = []

    def __enter__(self):
        for mod in self.targets:
            row = {}
            for name, value in self.values.items():
                row[name] = getattr(mod, name, ...)
                if callable(value) and getattr(value, '_per_module', False):
                    value = value(mod)
                setattr(mod, name, value)
            self.saved.append((mod, row))
        return self

    def __exit__(self, *exc):
        for mod, row in self.saved:
            for name, old in row.items():
                if old is ...:
                    delattr(mod, name)
                else:
                    setattr(mod, name, old)
        return False


# --------------------------------------------------------------------------- #
# cây tạm + fixture
# --------------------------------------------------------------------------- #
def fresh_tree(tag):
    SCRATCH.mkdir(parents = True, exist_ok = True)
    return Path(tempfile.mkdtemp(prefix = f'{tag}_', dir = str(SCRATCH)))


def touch(path, size = 3, mtime = 1700000000):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_bytes(b'x' * size)
    os.utime(path, (mtime, mtime))
    return path


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(text, encoding = 'utf-8')
    os.utime(path, (1700000000, 1700000000))
    return path


def normalize(text, *roots):
    '''Thay mọi biến thể đường dẫn gốc (\\\\, \\\\\\\\, /) trong chuỗi bằng <ROOT>.'''
    text = str(text)
    for root in roots:
        if root is None:
            continue
        pattern = _root_pattern(root)
        if pattern:
            text = re.sub(pattern, '<ROOT>', text)
    return text.replace('\\', '/')


def _root_pattern(root):
    '''Regex khớp đường dẫn gốc bất kể số lần escape của ký tự phân cách.'''
    parts = [re.escape(p) for p in str(root).split(os.sep) if p]
    return (r'(?:\\+|/)').join(parts)


def relative_list(root):
    return sorted(normalize(str(p.relative_to(root)), root) for p in root.rglob('*'))


def run_both(build, call):
    '''Chạy ``call`` trên repo rồi trên bản gốc, mỗi bên một cây tạm riêng.'''
    out = []
    for tag, mod in (('repo', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
        root = fresh_tree(tag)
        build(root, mod)
        try:
            kind, res = 'ok', fingerprint(call(mod, root))
        except Exception as exc:                        # noqa: BLE001 - so lỗi cũng là hành vi
            kind, res = type(exc).__name__, repr(exc)
        out.append((kind, normalize(res, root)))
        shutil.rmtree(root, ignore_errors = True)
    return out


def assert_same(built, msg = ''):
    (a_kind, a), (b_kind, b) = built
    assert a_kind == b_kind, f'{msg}: repo={a_kind}({a}) ref={b_kind}({b})'
    assert a == b, f'{msg}\n  repo: {a}\n  ref : {b}'


def shape(mod_name, build, call):
    '''Chạy một kịch bản trên đúng một module để kiểm tra số học cụ thể.'''
    mod = ref_module(DOTTED) if mod_name == 'ref' else repo_module(DOTTED)
    root = fresh_tree(f'shape_{mod_name}')
    try:
        build(root, mod)
        return call(mod, root)
    finally:
        shutil.rmtree(root, ignore_errors = True)


# --------------------------------------------------------------------------- #
#  format_bytes / chữ ký
# --------------------------------------------------------------------------- #
def test_format_bytes():
    values = [-500, -1, 0, 1, 512, 999, 1000, 1023, 1024, 1025, 1536, 2048,
              1024 ** 2 - 1, 1024 ** 2, 1024 ** 2 + 4096, 5 * 1024 ** 2,
              1024 ** 3, 1536 * 1024 ** 2, 1024 ** 4, 3 * 1024 ** 4, 10 ** 15,
              1024 ** 5, True, False, 12.5, 1023.999]
    mism = same_result(DOTTED, 'format_bytes', [(v, {}) for v in values])
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    assert ref.format_bytes(0) == '0 B'
    assert ref.format_bytes(1023) == '1023 B'
    assert ref.format_bytes(1024) == '1.0 KB'
    assert ref.format_bytes(1024 ** 3) == '1.0 GB'
    assert ref.format_bytes(1024 ** 5) == '1024.0 TB'      # đơn vị cuối không chia tiếp


def test_surface_matches_bytecode():
    '''Không được thiếu/thừa hàm, sai chữ ký hay sai docstring so với .pyc.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    names = set()
    for name, obj in vars(ref).items():
        if name.startswith('__') or getattr(obj, '__module__', None) != ref.__name__:
            continue
        if inspect.isfunction(obj) or isinstance(obj, type):
            names.add(name)
    assert names == {'CacheLocation', 'managed_locations', 'safe_cache_locations', '_measure',
                     '_measure_story_cache', '_measure_story_projects', 'cache_summary',
                     '_is_exact_managed_root', '_clear_locations', 'clear_story_cache',
                     'clear_safe_cache', 'clear_story_projects', '_job_files', '_final_voices',
                     '_archive_and_verify_job_voices', 'clear_completed_jobs',
                     'clear_all_cache_and_jobs', 'format_bytes'}, sorted(names)
    for name in names:
        a, b = getattr(ref, name), getattr(rep, name, None)
        assert b is not None, f'thiếu {name}'
        assert str(inspect.signature(a)) == str(inspect.signature(b)), name
        assert inspect.getdoc(a) == inspect.getdoc(b), f'docstring {name} khác'


def test_cache_location_is_frozen_dataclass():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (rep, ref):
        cls = mod.CacheLocation
        a = cls('k', 'L', Path('x'))
        assert repr(a) == "CacheLocation(key='k', label='L', path=PosixPath('x'))".replace(
            'PosixPath', type(Path()).__name__), repr(a)
        assert a == cls('k', 'L', Path('x'))
        assert a != cls('k', 'L', Path('y'))
        assert hash(a) == hash(cls('k', 'L', Path('x')))
        assert [f.name for f in dataclasses.fields(cls)] == ['key', 'label', 'path']
        assert a.__dataclass_params__.frozen is True
        try:
            a.key = 'z'
        except Exception as exc:                        # noqa: BLE001
            assert type(exc).__name__ == 'FrozenInstanceError', type(exc).__name__
        else:
            raise AssertionError('CacheLocation không frozen')
    assert repr(rep.CacheLocation('k', 'L', Path('x'))) == repr(ref.CacheLocation('k', 'L', Path('x')))


# --------------------------------------------------------------------------- #
#  managed / safe locations
# --------------------------------------------------------------------------- #
def test_managed_locations_content():
    ref = ref_module(DOTTED)
    items = ref.managed_locations()
    assert isinstance(items, tuple) and len(items) == 13
    keys = [i.key for i in items]
    assert keys == ['tts', 'tts_capcut', 'tts_artifacts', 'resume', 'demucs', 'visual',
                    'preview', 'tts_voice_preview', 'translation', 'legacy', 'jobs',
                    'story_cache', 'story_projects'], keys
    assert len(set(keys)) == len(keys)
    temp = ref.tempfile.gettempdir().replace('\\', '/')
    by_key = {i.key: str(i.path).replace('\\', '/') for i in items}
    # bản decompile ghi nhầm tiền tố mumu_ -> bytecode gốc dùng winterboy_
    assert by_key['tts'] == f'{temp}/winterboy_tts_cache', by_key['tts']
    assert by_key['tts_artifacts'] == f'{temp}/winterboy_tts_artifacts'
    assert by_key['resume'] == f'{temp}/winterboy_tts_resume'
    assert by_key['demucs'] == f'{temp}/winterboy_demucs_cache'
    assert by_key['visual'] == f'{temp}/winterboy_ffmpeg_visual_cache'
    assert by_key['preview'] == f'{temp}/winterboy_preview_audio'
    assert by_key['tts_capcut'].endswith('.winterboy/tts_cache/capcut')
    assert by_key['legacy'] == str(ref.APP_ROOT).replace('\\', '/') + '/temp'
    assert by_key['jobs'] == str(ref.JOBS_ROOT).replace('\\', '/')
    assert by_key['story_cache'] == by_key['story_projects'] == str(ref.STORY_PROJECTS_ROOT).replace('\\', '/')
    assert by_key['translation'] == str(ref.TRANSLATION_CACHE_ROOT).replace('\\', '/')
    assert by_key['tts_voice_preview'] == str(ref.TTS_PREVIEW_CACHE_ROOT).replace('\\', '/')
    assert all(isinstance(i.path, Path) for i in items)


def _strip(r):
    return [(i.key, i.label, str(i.path)) for i in r]


def test_managed_and_safe_locations_match():
    for fn in ('managed_locations', 'safe_cache_locations'):
        mism = same_result(DOTTED, fn, [((), {})], attrs = _strip)
        assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    safe = ref.safe_cache_locations()
    assert isinstance(safe, tuple)
    assert [i.key for i in safe] == ['tts', 'tts_capcut', 'demucs', 'visual', 'preview',
                                      'tts_voice_preview', 'translation', 'legacy'], [i.key for i in safe]


# --------------------------------------------------------------------------- #
#  _measure
# --------------------------------------------------------------------------- #
def test_measure_direct():
    def build(root, mod):
        touch(root / 'a.txt', 10)
        touch(root / 'sub' / 'b.txt', 25)
        touch(root / 'sub' / 'deep' / 'c.bin', 1)
        (root / 'empty_dir').mkdir()

    def call(mod, root):
        return [mod._measure(root), mod._measure(root / 'a.txt'),
                mod._measure(root / 'sub'), mod._measure(root / 'khong-co'),
                mod._measure(root / 'empty_dir')]

    assert_same(run_both(build, call), '_measure')
    got = shape('ref', build, call)
    assert got[0] == (3, 36), got                       # cả cây
    assert got[1] == (1, 10), got                       # bản thân 1 file
    assert got[2] == (2, 26), got                       # chỉ thư mục con
    assert got[3] == (0, 0) and got[4] == (0, 0), got


def test_measure_odd_paths():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    root = fresh_tree('measure_edge')
    try:
        deep = root / 'x' / 'y'
        deep.mkdir(parents = True)
        for mod in (rep, ref):
            assert mod._measure(root / 'khong-co') == (0, 0)
            assert mod._measure(deep) == (0, 0)
            assert mod._measure(root) == mod._measure(root.resolve())
    finally:
        shutil.rmtree(root, ignore_errors = True)


def test_story_measures():
    def build(root, mod):
        touch(root / 'proj_one' / '.cache' / 'preview_draft.mp4', 100)
        touch(root / 'proj_one' / '.cache' / 'x.json', 20)
        touch(root / 'proj_one' / 'one.clip.json', 7)
        touch(root / 'proj_one' / 'story_project.json', 30)
        touch(root / 'proj_one' / 'media' / 'clip.mp4', 50)
        touch(root / 'proj_two' / 'two.clip.json', 3)
        (root / 'proj_two' / '.cache').mkdir(parents = True)
        write_text(root / 'not_a_dir.clip.json', 'x')
        touch(root / 'ro.raw', 5)
        os.utime(root, (1700000000, 1700000000))

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root):
            return {'story_cache': mod._measure_story_cache(),
                    'story_projects': mod._measure_story_projects()}

    assert_same(run_both(build, call), 'story measures')
    got = shape('ref', build, call)
    assert got['story_cache'] == (4, 120 + 7 + 3), got         # .cache + .clip.json
    assert got['story_projects'] == (3, 30 + 50 + 5), got          # phần còn lại, kể cả file rời


def test_story_measures_without_root():
    def build(root, mod):
        pass

    def call(mod, root):
        missing = root / 'khong-ton-tai'
        with patched(mod, STORY_PROJECTS_ROOT = missing):
            return (mod._measure_story_cache(), mod._measure_story_projects())

    assert_same(run_both(build, call), 'story measures khi thiếu root')
    assert call(ref_module(DOTTED), fresh_tree('na')) == ((0, 0), (0, 0))


# --------------------------------------------------------------------------- #
#  cache_summary
# --------------------------------------------------------------------------- #
def test_cache_summary_groups():
    def build(root, mod):
        touch(root / 'cache' / 'a.wav', 40)
        touch(root / 'cache' / 'nested' / 'b.wav', 60)
        touch(root / 'story' / 'p1' / '.cache' / 'preview_draft.mp4', 11)
        touch(root / 'story' / 'p1' / 'p1.clip.json', 13)
        touch(root / 'story' / 'p1' / 'story_project.json', 17)

    def locations(mod, root):
        C = mod.CacheLocation
        return (C('tts', 'TTS', root / 'cache'),
                C('story_cache', 'Cache Story', root / 'story'),
                C('story_projects', 'Project Story', root / 'story'),
                C('jobs', 'Job cũ', root / 'jobs'))

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root / 'story',
                     managed_locations = fake_locations(lambda m: locations(m, root))):
            return mod.cache_summary()

    assert_same(run_both(build, call), 'cache_summary')
    res = shape('ref', build, call)
    assert [g['key'] for g in res['groups']] == ['tts', 'story_cache', 'story_projects', 'jobs']
    assert [g['files'] for g in res['groups']] == [2, 2, 1, 0], res
    assert [g['bytes'] for g in res['groups']] == [100, 11 + 13, 17, 0], res
    assert (res['files'], res['bytes']) == (5, 141), res
    assert all(isinstance(g['path'], str) for g in res['groups'])
    assert all(g['label'] for g in res['groups'])


def test_cache_summary_all_missing():
    def build(root, mod):
        pass

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root / 'story',
                     managed_locations = fake_locations(lambda m: (
                         m.CacheLocation('tts', 'TTS', root / 'cache'),
                         m.CacheLocation('story_cache', 'Cache Story', root / 'story')))):
            return mod.cache_summary()

    assert_same(run_both(build, call), 'cache_summary khi chưa có gì')


# --------------------------------------------------------------------------- #
#  _is_exact_managed_root + _clear_locations
# --------------------------------------------------------------------------- #
def test_is_exact_managed_root():
    def build(root, mod):
        (root / 'managed').mkdir()
        (root / 'other').mkdir()
        touch(root / 'managed' / 'f.txt', 5)

    def call(mod, root):
        with patched(mod, managed_locations = fake_locations(lambda m: (
                m.CacheLocation('m', 'M', root / 'managed'),
                m.CacheLocation('l', 'L', root / 'managed' / 'f.txt')))):
            return [mod._is_exact_managed_root(root / 'managed'),
                    mod._is_exact_managed_root(root / 'managed' / '.'),
                    mod._is_exact_managed_root(root / 'other'),
                    mod._is_exact_managed_root(root / 'managed' / 'f.txt'),
                    mod._is_exact_managed_root(root / 'managed' / 'deep' / 'x'),
                    mod._is_exact_managed_root(root / 'khong-co' / 'x'),
                    mod._is_exact_managed_root(Path('')),
                    mod._is_exact_managed_root(Path('.')),
                    mod._is_exact_managed_root(root)]

    assert_same(run_both(build, call), '_is_exact_managed_root')
    got = shape('ref', build, call)
    assert got == [True, True, False, True, False, False, False, False, False], got


def test_clear_locations():
    def build(root, mod):
        for name in ('cache_a', 'cache_b'):
            touch(root / name / 'one.txt', 30)
            touch(root / name / 'sub' / 'two.txt', 45)
        touch(root / 'loose.txt', 12)
        (root / 'empty_root').mkdir()
        (root / 'outside').mkdir()
        touch(root / 'outside' / 'keep.txt', 99)

    def locs(m, root):
        C = m.CacheLocation
        return (C('a', 'A', root / 'cache_a'), C('b', 'B', root / 'cache_b'),
                C('e', 'E', root / 'empty_root'), C('n', 'N', root / 'khong-co'),
                C('x', 'X', root / 'outside'), C('f', 'F', root / 'loose.txt'))

    def managed(m, root):
        return tuple(l for l in locs(m, root) if l.key != 'x')

    def call(mod, root):
        with patched(mod, managed_locations = fake_locations(lambda m: managed(m, root))):
            res = mod._clear_locations(locs(mod, root))
        return (res, relative_list(root))

    assert_same(run_both(build, call), '_clear_locations')
    res, left = shape('ref', build, call)
    assert res['removed_entries'] == 4, res              # 2 file + 2 thư mục con
    assert res['freed_bytes'] == 2 * (30 + 45), res
    assert res['remaining_bytes'] == 99 + 12, res        # outside + loose.txt còn nguyên
    assert len(res['errors']) == 1, res                  # chỉ 'outside' là ngoài phạm vi
    assert 'cache_a/one.txt' not in left and 'cache_b' in left, left
    assert 'outside/keep.txt' in left and 'loose.txt' in left, left


def test_clear_locations_never_deletes_the_root():
    for mod_name in ('repo', 'ref'):
        mod = ref_module(DOTTED) if mod_name == 'ref' else repo_module(DOTTED)

        def build(root, m):
            touch(root / 'cache' / 'a.txt', 10)
            touch(root / 'cache' / 'sub' / 'b.txt', 20)
            touch(root / 'outside' / 'keep.txt', 30)

        def call(m, root):
            C = m.CacheLocation
            with patched(m, managed_locations = fake_locations(lambda x: (
                    C('cache', 'Cache', root / 'cache'),))):
                res = m._clear_locations((C('cache', 'Cache', root / 'cache'),
                                          C('out', 'Out', root / 'outside')))
            assert (root / 'cache').is_dir(), 'root được quản lý bị xóa mất'
            assert not (root / 'cache' / 'a.txt').exists()
            assert not (root / 'cache' / 'sub').exists()
            assert (root / 'outside' / 'keep.txt').is_file(), 'xóa nhầm ngoài phạm vi'
            return res

        res = shape(mod_name, build, call)
        assert res['removed_entries'] == 2, res
        assert res['freed_bytes'] == 30, res
        assert res['remaining_bytes'] == 30, res    # 'outside' vẫn được tính lại
        assert len(res['errors']) == 1, res
        assert res['errors'][0].startswith('Bỏ qua đường dẫn ngoài phạm vi: '), res
        assert 'Out' not in res['errors'][0]


def test_clear_locations_empty_and_missing():
    def build(root, mod):
        (root / 'trống').mkdir()

    def call(mod, root):
        C = mod.CacheLocation
        with patched(mod, managed_locations = fake_locations(lambda m: (
                C('t', 'T', root / 'trống'), C('m', 'M', root / 'khong-co')))):
            return [mod._clear_locations(()), mod._clear_locations(
                (C('t', 'T', root / 'trống'), C('m', 'M', root / 'khong-co'))),
                mod._clear_locations([C('t', 'T', root / 'trống')])]

    assert_same(run_both(build, call), '_clear_locations rỗng/thiếu')
    got = shape('ref', build, call)
    assert got[0] == {'freed_bytes': 0, 'removed_entries': 0, 'remaining_bytes': 0, 'errors': []}, got
    assert [g['removed_entries'] for g in got] == [0, 0, 0], got


# --------------------------------------------------------------------------- #
#  clear_story_cache / clear_safe_cache
# --------------------------------------------------------------------------- #
def test_clear_story_cache():
    def build(root, mod):
        for name in ('p1', 'p2'):
            touch(root / name / '.cache' / 'draft.mp4', 60)
            touch(root / name / f'{name}.clip.json', 8)
        touch(root / 'p1' / 'story_project.json', 20)
        (root / 'p3').mkdir()
        write_text(root / 'file.clip.json', '{}')
        touch(root / 'p2' / 'media' / 'x.mp4', 999)

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root):
            res = mod.clear_story_cache()
        return (res, relative_list(root))

    assert_same(run_both(build, call), 'clear_story_cache')
    res, left = shape('ref', build, call)
    assert res['removed_entries'] == 4, res               # 2 .cache + 2 .clip.json
    assert res['freed_bytes'] == 2 * 60 + 2 * 8, res
    assert res['remaining_bytes'] == 0, res
    assert res['errors'] == [], res
    assert (root_exists(left, 'p1/story_project.json')), left
    assert (root_exists(left, 'p2/media/x.mp4')), left
    assert (root_exists(left, 'file.clip.json')), left     # file rời ở gốc không bị đụng


def root_exists(left, name):
    return name in left


def test_clear_story_cache_no_root():
    def build(root, mod):
        pass

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root / 'khong-co'):
            return mod.clear_story_cache()

    assert_same(run_both(build, call), 'clear_story_cache thiếu root')


def test_clear_safe_cache_merges():
    def build(root, mod):
        touch(root / 'tts' / 'a.mp3', 500)
        touch(root / 'jobs' / 'j1' / 'keep.txt', 700)
        touch(root / 'story' / 'p' / '.cache' / 'c.mp4', 300)

    def call(mod, root):
        C = mod.CacheLocation
        with patched(mod, STORY_PROJECTS_ROOT = root / 'story',
                     managed_locations = fake_locations(lambda m: (
                         C('tts', 'TTS', root / 'tts'), C('jobs', 'Job', root / 'jobs')))):
            res = mod.clear_safe_cache()
        return (res, relative_list(root))

    assert_same(run_both(build, call), 'clear_safe_cache')
    res, left = shape('ref', build, call)
    assert res['freed_bytes'] == 800, res                  # 500 tts + 300 .cache
    assert res['removed_entries'] == 2, res
    assert res['remaining_bytes'] == 0, res
    assert res['errors'] == [], res
    assert 'jobs/j1/keep.txt' in left, left                 # jobs không nằm trong safe cache
    assert 'tts/a.mp3' not in left, left


# --------------------------------------------------------------------------- #
#  clear_story_projects
# --------------------------------------------------------------------------- #
def story_projects_fixture(root):
    (root / 'a_empty' / 'sub').mkdir(parents = True)
    write_text(root / 'b_scenes' / 'story_project.json', '{"scenes": [{"t": 1}]}')
    write_text(root / 'c_raw' / 'story_project.json', '{"scenes": [], "raw_script": "  xin chao  "}')
    write_text(root / 'd_blank' / 'story_project.json', '{"scenes": []}')
    write_text(root / 'e_broken' / 'story_project.json', '{khong phai json')
    write_text(root / 'f_list' / 'story_project.json', '[1, 2, 3]')
    write_text(root / 'g_null' / 'story_project.json', 'null')
    touch(root / 'h_cacheonly' / '.cache' / 'x.mp4', 40)
    touch(root / 'loose.txt', 5)
    write_text(root / 'not_a_dir.json', '{}')


def test_clear_story_projects():
    def build(root, mod):
        story_projects_fixture(root)

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root):
            half = mod.clear_story_projects()
            full = mod.clear_story_projects(delete_all = True)
            nothing = mod.clear_story_projects(delete_all = False)
        return (half, full, nothing, relative_list(root))

    assert_same(run_both(build, call), 'clear_story_projects')

    def shape_call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root):
            res = mod.clear_story_projects()
            assert (root / 'b_scenes').is_dir() and (root / 'c_raw').is_dir()
            assert (root / 'loose.txt').is_file(), 'file rời bị xóa khi chưa delete_all'
            res2 = mod.clear_story_projects(delete_all = True)
            res3 = mod.clear_story_projects(delete_all = False)
        return res, res2, res3, relative_list(root)

    res, res2, res3, left = shape('ref', build, shape_call)
    # rỗng: không có json / scenes+rỗng đều trống / json lỗi hoặc không phải dict
    assert res['deleted_projects'] == 6, res
    assert res['skipped_projects'] == 2, res               # b_scenes, c_raw
    assert res['errors'] == [], res
    assert res['freed_bytes'] > 0 and res2['freed_bytes'] > 0, (res, res2)
    assert res2['deleted_projects'] == 4, res2             # 2 project + 2 file rời
    assert res2['skipped_projects'] == 0, res2
    assert left == [], left
    assert res3 == {'freed_bytes': 0, 'deleted_projects': 0, 'skipped_projects': 0,
                    'errors': []}, res3


def test_clear_story_projects_missing_root():
    def build(root, mod):
        pass

    def call(mod, root):
        with patched(mod, STORY_PROJECTS_ROOT = root / 'khong-co'):
            return mod.clear_story_projects(delete_all = True)

    assert_same(run_both(build, call), 'clear_story_projects root missing')
    assert shape('ref', build, call) == {'freed_bytes': 0, 'deleted_projects': 0,
                                         'skipped_projects': 0, 'errors': []}


# --------------------------------------------------------------------------- #
#  job helpers
# --------------------------------------------------------------------------- #
def test_job_files_and_final_voices():
    def build(root, mod):
        touch(root / 'job' / 'srt' / 'a.srt', 20)
        touch(root / 'job' / 'tts' / 'a' / 'final_voice.mp3', 400)
        touch(root / 'job' / 'tts' / 'b' / 'final_voice.wav', 0)
        touch(root / 'job' / 'tts' / 'c' / 'other.mp3', 10)
        (root / 'job' / 'tts' / 'empty').mkdir(parents = True)
        write_text(root / 'job' / 'tts' / 'final_voice.mp3', 'trực tiếp')
        (root / 'rong').mkdir()

    def call(mod, root):
        def rel(paths):
            return sorted(normalize(str(p.relative_to(root)), root) for p in paths)
        return {'job': (rel(mod._job_files(root / 'job')), rel(mod._final_voices(root / 'job'))),
                'rong': (rel(mod._job_files(root / 'rong')), rel(mod._final_voices(root / 'rong'))),
                'missing': (rel(mod._job_files(root / 'khong-co')),
                            rel(mod._final_voices(root / 'khong-co'))),
                'la_file': (rel(mod._job_files(root / 'job' / 'srt' / 'a.srt')),
                            rel(mod._final_voices(root / 'job' / 'srt' / 'a.srt')))}

    assert_same(run_both(build, call), '_job_files/_final_voices')
    got = shape('ref', build, call)
    assert got['job'][1] == ['job/tts/a/final_voice.mp3'], got     # glob 1 cấp, bỏ file 0 byte
    assert len(got['job'][0]) == 5, got
    assert got['rong'] == ([], []), got
    assert got['missing'] == ([], []), got
    assert got['la_file'] == ([], []), got                          # path là file, không có con


# --------------------------------------------------------------------------- #
#  _archive_and_verify_job_voices + clear_completed_jobs
# --------------------------------------------------------------------------- #
def make_voice_stub(store):
    '''Module giả cho app.services.voice_history — cache_manager import nó trong hàm.'''
    mod = types.ModuleType('app.services.voice_history')
    mod._calls = []

    def parse_job_folder(name):
        return (None, 'job', f'label::{name}')

    def paired_srt(path):
        return None

    def archive_voice(source, srt_path = None, label = ''):
        mod._calls.append((str(source), str(srt_path), label))
        mode = store.get('mode', 'copy')
        if mode == 'raise':
            raise RuntimeError('đĩa hỏng')
        if mode == 'none':
            return None
        dest = Path(store['lib']) / Path(source).parents[2].name / Path(source).name
        dest.parent.mkdir(parents = True, exist_ok = True)
        data = Path(source).read_bytes()
        if mode == 'wrong_size':
            data += b'x'
        dest.write_bytes(data)
        return dest

    mod.parse_job_folder = parse_job_folder
    mod.paired_srt = paired_srt
    mod.archive_voice = archive_voice
    return mod


class stub_voice_history:
    def __init__(self, store):
        self.stub = make_voice_stub(store)

    def __enter__(self):
        self.saved = sys.modules.get('app.services.voice_history', False)
        sys.modules['app.services.voice_history'] = self.stub
        return self.stub

    def __exit__(self, *exc):
        if self.saved is False:
            sys.modules.pop('app.services.voice_history', None)
        else:
            sys.modules['app.services.voice_history'] = self.saved
        return False


def test_archive_and_verify_job_voices():
    def build(root, mod):
        for name in ('v1.mp3', 'v2.mp3'):
            touch(root / 'job_x' / 'tts' / 'srt_a' / name, 40)

    def voices(root):
        return sorted((root / 'job_x' / 'tts' / 'srt_a').glob('*.mp3'))

    def call(mod, root):
        store = {'lib': root / 'library', 'mode': 'copy'}
        with stub_voice_history(store) as stub:
            ok = mod._archive_and_verify_job_voices(root / 'job_x', voices(root))
            calls = list(stub._calls)
            store['mode'] = 'none'
            missed = mod._archive_and_verify_job_voices(root / 'job_x', voices(root))
            store['mode'] = 'wrong_size'
            wrong = mod._archive_and_verify_job_voices(root / 'job_x', voices(root))
            store['mode'] = 'raise'
            boom = mod._archive_and_verify_job_voices(root / 'job_x', voices(root))
            empty = mod._archive_and_verify_job_voices(root / 'job_x', [])
            missing = mod._archive_and_verify_job_voices(root / 'job_x',
                                                         [root / 'job_x' / 'khong-co.mp3'])
        return {'ok': ok, 'missed': missed, 'wrong': wrong, 'boom': boom, 'empty': empty,
                'missing': missing, 'srt': calls[0][1] if calls else None,
                'label': calls[0][2] if calls else None}

    assert_same(run_both(build, call), '_archive_and_verify_job_voices')

    def shape_call(mod, root):
        store = {'lib': root / 'library', 'mode': 'copy'}
        with stub_voice_history(store) as stub:
            res = mod._archive_and_verify_job_voices(root / 'job_x', voices(root))
            calls = list(stub._calls)
        assert res[0] == 2 and res[1] == [], res
        assert len(calls) == 2, calls
        assert [c[2] for c in calls] == ['label::job_x'] * 2, calls
        assert all(c[1] == 'None' for c in calls), calls
        assert (root / 'library' / 'job_x' / 'v1.mp3').is_file()
        return res

    shape('ref', build, shape_call)
    shape('repo', build, shape_call)


def jobs_fixture(root):
    (root / 'jobs' / 'empty_job').mkdir(parents = True)
    touch(root / 'jobs' / 'voiced_job' / 'tts' / 's' / 'final_voice.mp3', 64)
    touch(root / 'jobs' / 'busy_job' / 'stt' / 'raw.json', 33)
    touch(root / 'jobs' / 'bad_job' / 'tts' / 's' / 'final_voice.mp3', 12)
    touch(root / 'jobs' / 'stray.txt', 4)
    write_text(root / 'jobs' / 'not_a_dir', 'x')
    (root / 'story' / 'proj_rong').mkdir(parents = True)
    write_text(root / 'story' / 'proj_day' / 'story_project.json', '{"scenes": [1, 2]}')


def picky_archive(store):
    def archive_voice(source, srt_path = None, label = ''):
        job_name = Path(source).parents[2].name
        if job_name == 'bad_job':
            return None
        dest = Path(store['lib']) / job_name / Path(source).name
        dest.parent.mkdir(parents = True, exist_ok = True)
        dest.write_bytes(Path(source).read_bytes())
        return dest
    return archive_voice


def jobs_patch(mod, root):
    '''patched() cho clear_completed_jobs trỏ hết vào cây tạm.'''
    return patched(mod, JOBS_ROOT = root / 'jobs', STORY_PROJECTS_ROOT = root / 'story',
                   managed_locations = fake_locations(lambda m: (
                       m.CacheLocation('jobs', 'Job', root / 'jobs'),
                       m.CacheLocation('story', 'Story', root / 'story'))))


def test_clear_completed_jobs():
    def build(root, mod):
        jobs_fixture(root)

    def call(mod, root):
        store = {'lib': root / 'library', 'mode': 'copy'}
        with jobs_patch(mod, root), stub_voice_history(store) as stub:
            stub.archive_voice = picky_archive(store)
            plain = mod.clear_completed_jobs()
            both = mod.clear_completed_jobs(delete_story_projects = True)
        return {'plain': plain, 'both': both, 'left': relative_list(root)}

    assert_same(run_both(build, call), 'clear_completed_jobs')

    def shape_call(mod, root):
        store = {'lib': root / 'library', 'mode': 'copy'}
        with jobs_patch(mod, root), stub_voice_history(store) as stub:
            stub.archive_voice = picky_archive(store)
            res = mod.clear_completed_jobs()
        assert res['deleted_jobs'] == 2, res                 # empty_job + voiced_job
        assert res['skipped_jobs'] == 2, res                 # busy_job + bad_job
        assert res['preserved_voices'] == 1, res
        assert res['deleted_projects'] == 1, res
        assert res['freed_bytes'] == (64 + 12 + 33 + 4 + 1) - (12 + 33 + 4 + 1), res
        assert any('bad_job: ' in e and 'Không tạo được bản sao' in e for e in res['errors']), res
        assert (root / 'jobs' / 'busy_job').is_dir(), 'xóa nhầm job đang dở'
        assert (root / 'jobs' / 'bad_job').is_dir(), 'xóa nhầm job chưa sao lưu voice'
        assert (root / 'jobs' / 'stray.txt').is_file(), 'xóa nhầm file rời trong jobs'
        assert (root / 'story' / 'proj_day').is_dir(), 'xóa nhầm project có phân cảnh'
        assert not (root / 'story' / 'proj_rong').exists()
        assert (root / 'library' / 'voiced_job' / 'final_voice.mp3').is_file()
        return res

    for mod_name in ('repo', 'ref'):
        shape(mod_name, build, shape_call)


def test_clear_completed_jobs_refuses_outside_root():
    def build(root, mod):
        jobs_fixture(root)

    def call(mod, root):
        with patched(mod, JOBS_ROOT = root / 'khong_phai_managed',
                     STORY_PROJECTS_ROOT = root / 'story',
                     managed_locations = fake_locations(lambda m: (
                         m.CacheLocation('jobs', 'Job', root / 'jobs'),))):
            return mod.clear_completed_jobs()

    assert_same(run_both(build, call), 'clear_completed_jobs ngoài phạm vi')
    got = shape('ref', build, call)
    assert got['deleted_jobs'] == 0 and got['skipped_jobs'] == 0, got
    assert got['freed_bytes'] == 0, got
    assert len(got['errors']) == 1 and got['errors'][0].startswith('Bỏ qua đường dẫn'), got
    assert got['deleted_projects'] == 1, got                 # story vẫn được dọn bình thường


def test_clear_completed_jobs_without_jobs_dir():
    def build(root, mod):
        (root / 'story' / 'p_rong').mkdir(parents = True)
        touch(root / 'story' / 'p_day' / 'story_project.json', 30)
        write_text(root / 'story' / 'p_day' / 'story_project.json', '{"scenes": [1]}')

    def call(mod, root):
        with patched(mod, JOBS_ROOT = root / 'khong-co',
                     STORY_PROJECTS_ROOT = root / 'story',
                     managed_locations = fake_locations(lambda m: (
                         m.CacheLocation('jobs', 'Job', root / 'khong-co'),))):
            return mod.clear_completed_jobs(delete_story_projects = True)

    assert_same(run_both(build, call), 'clear_completed_jobs khi jobs chưa có')
    got = shape('ref', build, call)
    assert got['deleted_jobs'] == 0 and got['errors'] == [] and got['deleted_projects'] == 2, got


def test_clear_all_cache_and_jobs_merges():
    rows = [
        ({'freed_bytes': 10, 'removed_entries': 2, 'remaining_bytes': 5, 'errors': []},
         {'freed_bytes': 7, 'deleted_jobs': 1, 'skipped_jobs': 0, 'preserved_voices': 3,
          'errors': ['x']}),
        ({'freed_bytes': '3', 'removed_entries': '1', 'remaining_bytes': '0', 'errors': None},
         {'freed_bytes': '2', 'deleted_jobs': '0', 'skipped_jobs': '1', 'preserved_voices': '0',
          'errors': None}),
        ({'freed_bytes': 1, 'removed_entries': 1, 'remaining_bytes': 1, 'errors': ['a']},
         {'freed_bytes': 1, 'deleted_jobs': 1, 'skipped_jobs': 1, 'preserved_voices': 1,
          'errors': ['b', 'c']}),
        ({'freed_bytes': 1}, {}),
        ({}, {}),
        ({'freed_bytes': 0.5, 'removed_entries': 0, 'remaining_bytes': 0, 'errors': []},
         {'freed_bytes': 0, 'deleted_jobs': 0, 'skipped_jobs': 0, 'preserved_voices': 0,
          'errors': []}),
    ]

    def call_with(mod, cache_res, job_res):
        def fake_cache():
            return dict(cache_res)

        def fake_jobs():
            return dict(job_res)
        with patched(mod, clear_safe_cache = fake_cache, clear_completed_jobs = fake_jobs):
            try:
                return ('ok', mod.clear_all_cache_and_jobs())
            except Exception as exc:                        # noqa: BLE001
                return ('err', type(exc).__name__)

    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for cache_res, job_res in rows:
        a = call_with(rep, cache_res, job_res)
        b = call_with(ref, cache_res, job_res)
        assert fingerprint(a) == fingerprint(b), f'{(cache_res, job_res)}: {a!r} != {b!r}'
    res = call_with(ref, rows[0][0], rows[0][1])
    assert res[1] == {'freed_bytes': 17, 'removed_entries': 2, 'deleted_jobs': 1,
                      'skipped_jobs': 0, 'preserved_voices': 3, 'remaining_bytes': 5,
                      'errors': ['x']}, res
    assert call_with(ref, rows[1][0], rows[1][1])[1]['errors'] == [], 'errors None phải ra []'


def test_decompile_artifacts_gone():
    src = (REPO / 'app' / 'services' / 'cache_manager.py').read_text(encoding = 'utf-8')
    for junk in ('Decompyle incomplete', '<NODE:', 'None(', 'mumu_tts', 'None ='):
        assert junk not in src, f'còn artifact decompile: {junk}'

# -*- coding: utf-8 -*-
'''Đối chiếu app.services.demucs_separator với bản đã phát hành (.pyc trong _internal).

Ràng buộc: test KHÔNG chạy ffmpeg hay demucs.
  * ``_run_cancellable`` được thay bằng RunnerSpy ghi lại đúng command list mà module
    dựng ra, rồi mô phỏng file đầu ra — vẫn kiểm được toàn bộ logic dựng câu lệnh,
    đường dẫn cache, chứng từ artifact và thứ tự fallback CUDA -> CPU;
  * ``_run_cancellable`` chỉ thật sự chạy tiến trình với ``python -c`` vài dòng, để
    kiểm vòng poll / kill / timeout / cắt log;
  * torch và importlib.metadata được stub qua sys.modules nên demucs_runtime_status
    không nạp mô hình thật.

Package cha ``app.services`` trỏ vào _internal vì app/services/__init__.py trong repo
còn hỏng cú pháp; artifact_manifest dùng bản đã phát hành để hai bên cùng chuẩn
fingerprint.
'''
from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
from pathlib import Path

from _parity import INTERNAL, REPO, fingerprint, ref_module, repo_module, same_result

DOTTED = 'app.services.demucs_separator'
SCRATCH = REPO / 'output' / '_restore' / 'demucs'
HASH_RE = re.compile(r'[0-9a-f]{40,}')


# --------------------------------------------------------------------------- #
#  môi trường import
# --------------------------------------------------------------------------- #
def install_pkg_shim():
    pkg = INTERNAL / 'app'
    for name, path in (('app', pkg), ('app.services', pkg / 'services')):
        mod = sys.modules.get(name)
        if mod is None or not getattr(mod, '__path__', None):
            stub = types.ModuleType(name)
            stub.__path__ = [str(path)]
            sys.modules[name] = stub
    sys.modules.pop('app.services.demucs_separator', None)


install_pkg_shim()


class patched:
    def __init__(self, *targets, **values):
        self.targets = targets
        self.values = values
        self.saved = []

    def __enter__(self):
        for mod in self.targets:
            row = {}
            for name, value in self.values.items():
                row[name] = getattr(mod, name, ...)
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


class stub_modules:
    '''Đặt module giả vào sys.modules trong phạm vi with.'''

    def __init__(self, **mapping):
        self.mapping = mapping
        self.saved = {}

    def __enter__(self):
        for name, value in self.mapping.items():
            self.saved[name] = sys.modules.get(name, False)
            sys.modules[name] = value
        return self

    def __exit__(self, *exc):
        for name, old in self.saved.items():
            if old is False:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        return False


class PackageNotFoundErrorStub(Exception):
    pass


def make_torch(version = '2.4.0+test', cuda = False):
    mod = types.ModuleType('torch')
    mod.__version__ = version
    mod.cuda = types.SimpleNamespace(is_available = lambda: cuda)
    return mod


def make_metadata(demucs_version = '4.0.1'):
    mod = types.ModuleType('importlib.metadata')

    def version(name):
        if name == 'demucs':
            return demucs_version
        raise PackageNotFoundErrorStub(name)
    mod.version = version
    mod.PackageNotFoundError = PackageNotFoundErrorStub
    return mod


def make_importlib(spec_present = True):
    def find_spec(name):
        return object() if (name == 'demucs' and spec_present) else None
    mod = types.ModuleType('importlib')
    mod.util = types.SimpleNamespace(find_spec = find_spec)
    return mod


class FakePath:
    '''Giống Path nhưng is_file() ném OSError đúng vào những path đã đánh dấu.

    home() bị chặn thật: nếu test quên đặt ``_home`` thì ném lỗi ngay, thay vì để
    thư mục mục của máy chạy test (``C:\\Users\\...\\AppData\\Local``) lọt vào kết quả
    và làm assertions chỉ đúng trên một chiếc laptop.
    '''

    fail = set()
    _home = None

    def __init__(self, *parts):
        self.p = Path(*[str(x) for x in parts]) if parts else Path('.')

    def __truediv__(self, other):
        return FakePath(str(self.p / str(other)))

    def is_file(self):
        if str(self.p).casefold() in FakePath.fail:
            raise OSError('khong truy cap duoc')
        return self.p.is_file()

    def is_dir(self):
        return self.p.is_dir()

    def glob(self, pattern):
        return [FakePath(x) for x in self.p.glob(pattern)]

    # sorted(..., reverse=True) trong _find_executable cần so sánh được path,
    # nên FakePath phải mô phỏng cách Path so sánh: theo chuỗi đã chuẩn hoá.
    def __lt__(self, other):
        if not isinstance(other, FakePath):
            return NotImplemented
        return str(self.p).casefold() < str(other.p).casefold()

    def __eq__(self, other):
        if not isinstance(other, FakePath):
            return NotImplemented
        return str(self.p).casefold() == str(other.p).casefold()

    def __hash__(self):
        return hash(str(self.p).casefold())

    def __str__(self):
        return str(self.p)

    def __repr__(self):
        return f'FakePath({str(self.p)!r})'

    @classmethod
    def home(cls):
        if cls._home is None:
            raise AssertionError('FakePath._home chưa được đặt -> kết quả sẽ phụ thuộc máy')
        return FakePath(cls._home)


class fake_home:
    '''Đặt home giả cho FakePath trong phạm vi with, trả lại giá trị cũ khi ra.'''

    def __init__(self, path):
        self.path = path
        self.old = None

    def __enter__(self):
        self.old = FakePath._home
        FakePath._home = str(self.path)
        return self

    def __exit__(self, *exc):
        FakePath._home = self.old
        return False


class FakeTempfile:
    '''tempfile trỏ vào cây tạm của test, không đụng %TEMP% thật.'''

    def __init__(self, root):
        self.root = Path(root)

    def gettempdir(self):
        return str(self.root)

    def TemporaryDirectory(self, prefix = '', dir = None, **kw):
        # tôn trọng dir module gửi vào (cache_root) để giống hành vi thật
        return tempfile.TemporaryDirectory(prefix = prefix or 'stub_',
                                           dir = str(dir or self.root))


# --------------------------------------------------------------------------- #
#  cây tạm + chuẩn hóa
# --------------------------------------------------------------------------- #
def fresh_tree(tag):
    SCRATCH.mkdir(parents = True, exist_ok = True)
    return Path(tempfile.mkdtemp(prefix = f'{tag}_', dir = str(SCRATCH)))


def touch(path, size = 3, mtime = 1700000000.0):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_bytes(b'q' * size)
    os.utime(path, (mtime, mtime))
    return path


def normalize(text, *roots):
    '''Ẩn đường dẫn tạm (mọi biến thể escape), tên folder tạm và fingerprint.

    Giá trị ``None`` được trả nguyên vẹn: ``str(None)`` thành 'None' khiến assertion
    'is None' không bao giờ chạy được. Chuỗi '\\' của str(list) cũng nhân đôi dấu
    phân cách nên phải nén lại, nếu không '<ROOT>//demucs.exe' làm fail oan.
    '''
    if text is None:
        return None
    text = str(text)
    for root in roots:
        if root is None:
            continue
        parts = [re.escape(p) for p in str(root).split(os.sep) if p]
        if parts:
            text = re.sub(r'(?:\\+|/)'.join(parts), '<ROOT>', text)
    text = re.sub(r'winterboy_demucs_(?!cache)[A-Za-z0-9_]+', '<TMP>', text)
    text = HASH_RE.sub('<FP>', text)
    return re.sub(r'/+', '/', text.replace('\\', '/'))


def raises(fn):
    try:
        return ('ok', fn())
    except Exception as exc:                        # noqa: BLE001 - so lỗi cũng là hành vi
        return (type(exc).__name__, str(exc))


def run_both(build, call):
    out = []
    for tag, mod in (('repo', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
        root = fresh_tree(tag)
        build(root, mod)
        kind, res = raises(lambda: fingerprint(call(mod, root)))
        out.append((kind, normalize(res, root)))
        shutil.rmtree(root, ignore_errors = True)
    return out


def assert_same(built, msg = ''):
    (a_kind, a), (b_kind, b) = built
    assert a_kind == b_kind, f'{msg}: repo={a_kind}({a}) ref={b_kind}({b})'
    assert a == b, f'{msg}\n  repo: {a}\n  ref : {b}'


def shape(mod_name, build, call):
    mod = ref_module(DOTTED) if mod_name == 'ref' else repo_module(DOTTED)
    root = fresh_tree(f'shape_{mod_name}')
    try:
        build(root, mod)
        return call(mod, root)
    finally:
        shutil.rmtree(root, ignore_errors = True)


# --------------------------------------------------------------------------- #
#  surface
# --------------------------------------------------------------------------- #
def test_surface_matches_bytecode():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    names = {n for n, o in vars(ref).items()
             if not n.startswith('__') and getattr(o, '__module__', None) == ref.__name__
             and (inspect.isfunction(o) or isinstance(o, type))}
    assert names == {'_hidden_kwargs', '_find_executable', '_demucs_command',
                     'demucs_runtime_status', '_run_cancellable',
                     'separate_background'}, sorted(names)
    for name in names:
        a, b = getattr(ref, name), getattr(rep, name, None)
        assert b is not None, f'thiếu {name}'
        assert str(inspect.signature(a)) == str(inspect.signature(b)), name
        assert inspect.getdoc(a) == inspect.getdoc(b), f'docstring {name} khác'
    assert str(ref.ProgressCb) == str(rep.ProgressCb)
    src = (REPO / 'app' / 'services' / 'demucs_separator.py').read_text(encoding = 'utf-8')
    for junk in ('Decompyle incomplete', '<NODE:', 'None(', ' = None('):
        assert junk not in src, f'còn artifact decompile: {junk}'


# --------------------------------------------------------------------------- #
#  _hidden_kwargs
# --------------------------------------------------------------------------- #
def test_hidden_kwargs():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)

    def read(mod):
        kw = mod._hidden_kwargs()
        info = kw.get('startupinfo')
        return {'keys': sorted(kw), 'flags': kw.get('creationflags'),
                'dw': getattr(info, 'dwFlags', None), 'show': getattr(info, 'wShowWindow', None)}

    (a, b) = (read(rep), read(ref))
    assert a == b, (a, b)
    if sys.platform.startswith('win'):
        assert a['flags'] == getattr(subprocess, 'CREATE_NO_WINDOW', 134217728), a
        assert a['dw'] == getattr(subprocess, 'STARTF_USESHOWWINDOW', 1), a
        assert a['show'] == getattr(subprocess, 'SW_HIDE', 0), a
    not_win = types.SimpleNamespace(platform = types.SimpleNamespace(startswith = lambda p: False))
    win = types.SimpleNamespace(platform = types.SimpleNamespace(startswith = lambda p: True))
    for mod in (rep, ref):
        with patched(mod, sys = not_win):
            assert mod._hidden_kwargs() == {}
        with patched(mod, sys = win):
            assert sorted(mod._hidden_kwargs()) == ['creationflags', 'startupinfo']
        bare = types.SimpleNamespace(STARTUPINFO = subprocess.STARTUPINFO)
        with patched(mod, sys = win, subprocess = bare):
            kw = mod._hidden_kwargs()
            assert kw['creationflags'] == 134217728, kw
            assert kw['startupinfo'].dwFlags == 1 and kw['startupinfo'].wShowWindow == 0, kw


# --------------------------------------------------------------------------- #
#  _find_executable
# --------------------------------------------------------------------------- #
def finder_env(which_result):
    return types.SimpleNamespace(which = lambda name: which_result)


def test_find_executable_uses_path_first():
    def build(root, mod):
        pass

    def call(mod, root):
        out = []
        for name in (sys.executable, 'python', 'cmd.exe' if os.name == 'nt' else 'sh'):
            out.append(normalize(mod._find_executable(name), root))
        with patched(mod, shutil = finder_env('C:/doi/tay/bin.exe')):
            out.append(normalize(mod._find_executable('whatever'), root))
            out.append(normalize(mod._find_executable('whatever.exe'), root))
            out.append(normalize(mod._find_executable('WHATEVER.EXE'), root))
        with patched(mod, shutil = finder_env(None)):
            out.append(mod._find_executable('demucs-khong-co-trong-moi-truong'))
        return out

    assert_same(run_both(build, call), '_find_executable qua PATH')


def test_find_executable_fallback_roots():
    def build(root, mod):
        touch(root / 'local' / 'Microsoft' / 'WinGet' / 'Links' / 'ffmpeg.exe', 1)
        for ver in ('Python311', 'Python312', 'Python39'):
            touch(root / 'local' / 'Programs' / 'Python' / ver / 'Scripts' / 'demucs.exe', 1)
        touch(root / 'base' / 'Scripts' / 'khac.exe', 1)

    def call(mod, root):
        os_stub = types.SimpleNamespace(environ = {'LOCALAPPDATA': str(root / 'local')})
        fake_sys = types.SimpleNamespace(base_prefix = str(root / 'base'), platform = 'win32',
                                        executable = sys.executable, frozen = False)
        with patched(mod, shutil = finder_env(None), sys = fake_sys, os = os_stub):
            demucs = normalize(mod._find_executable('demucs'), root)
            ffmpeg = normalize(mod._find_executable('ffmpeg.exe'), root)
            none = mod._find_executable('khong-bao-gio-co')
            # ngoài Windows chỉ còn ứng viên sys.base_prefix/Scripts, tên luôn thêm .exe
            nix = types.SimpleNamespace(base_prefix = str(root / 'nix'), platform = 'linux',
                                       executable = sys.executable, frozen = False)
            with patched(mod, sys = nix):
                before = mod._find_executable('demucs')
                touch(root / 'nix' / 'Scripts' / 'demucs.exe', 1)
                after = normalize(mod._find_executable('demucs'), root)
        # LOCALAPPDATA trống -> suy ra từ Path.home()/AppData/Local. Phải chặn cả
        # Path.home() lẫn sys.base_prefix: thiếu một trong hai là thư mục thật của
        # máy chạy test lọt vào kết quả và assertion chỉ đúng trên laptop đó.
        home = root / 'home'
        only = root / 'only'
        touch(home / 'AppData' / 'Local' / 'Microsoft' / 'WinGet' / 'Links' / 'demucs.exe', 1)
        for ver in ('Python311', 'Python39'):
            touch(only / 'AppData' / 'Local' / 'Programs' / 'Python' / ver / 'Scripts'
                  / 'demucs.exe', 1)
        base_less = types.SimpleNamespace(base_prefix = str(root / 'empty'), platform = 'win32',
                                         executable = sys.executable, frozen = False)
        FakePath.fail = set()
        with patched(mod, shutil = finder_env(None), sys = base_less,
                     os = types.SimpleNamespace(environ = {}), Path = FakePath):
            with fake_home(home):
                from_home = normalize(mod._find_executable('demucs'), root)
            with fake_home(only):
                from_only_python = normalize(mod._find_executable('demucs'), root)
            # _home bị xoá sau when -> nếu module còn gọi Path.home() mà test quên đặt
            # giả thì nhận AssertionError thay vì âm thầm dùng home thật
            FakePath._home = None
            forgotten = raises(lambda: mod._find_executable('demucs'))
        return {'demucs': demucs, 'ffmpeg': ffmpeg, 'none': none, 'before': before,
                'after': after, 'from_home': from_home, 'from_only_python': from_only_python,
                'forgotten': forgotten}

    assert_same(run_both(build, call), '_find_executable với các ứng viên cục bộ')
    res = shape('ref', build, call)
    # Quirk CÓ THẬT của bản phát hành: candidates Python*/Scripts được sắp bằng
    # sorted(..., reverse=True) nên so theo TỰ ĐIỂN, 'Python39' > 'Python312' ->
    # bản cũ nhất thắng. Đây là lỗi sắp xếp trong app đã đóng băng bytecode,
    # không phải lỗi của test, nên test phải ghi lại đúng giá trị này.
    assert res['demucs'].endswith('Python39/Scripts/demucs.exe'), res
    assert res['from_only_python'].startswith('<ROOT>/only/'), res
    assert res['from_only_python'].endswith('Python39/Scripts/demucs.exe'), res

    assert res['ffmpeg'].endswith('WinGet/Links/ffmpeg.exe'), res
    assert res['none'] is None and res['before'] is None, res
    assert res['after'].endswith('nix/Scripts/demucs.exe'), res
    # không có đường dẫn của máy: mọi kết quả nằm trong cây tạm của test
    assert res['from_home'].startswith('<ROOT>/home/'), res
    assert res['from_home'].endswith('AppData/Local/Microsoft/WinGet/Links/demucs.exe'), res
    assert res['forgotten'][0] == 'AssertionError', res['forgotten']



def test_find_executable_swallows_oserror():
    def build(root, mod):
        touch(root / 'base' / 'Scripts' / 'demucs.exe', 1)
        touch(root / 'local' / 'Microsoft' / 'WinGet' / 'Links' / 'demucs.exe', 1)

    def call(mod, root):
        fake_sys = types.SimpleNamespace(base_prefix = str(root / 'base'), platform = 'win32',
                                       executable = sys.executable, frozen = False)
        os_stub = types.SimpleNamespace(environ = {'LOCALAPPDATA': str(root / 'local')})
        first_bad = {str(root / 'base' / 'Scripts' / 'demucs.exe').casefold()}
        both_bad = first_bad | {str(root / 'local' / 'Microsoft' / 'WinGet' / 'Links'
                                    / 'demucs.exe').casefold()}
        with patched(mod, shutil = finder_env(None), sys = fake_sys, os = os_stub, Path = FakePath):
            FakePath.fail = first_bad
            found = normalize(mod._find_executable('demucs'), root)      # nhảy sang ứng viên 2
            FakePath.fail = both_bad
            nothing = mod._find_executable('demucs')                     # hết ứng viên
            FakePath.fail = set()
            again = normalize(mod._find_executable('demucs'), root)      # ưu tiên số 1
        return {'found': found, 'nothing': nothing, 'again': again}

    assert_same(run_both(build, call), '_find_executable nuốt OSError')
    res = shape('ref', build, call)
    assert res['found'].endswith('WinGet/Links/demucs.exe'), res
    assert res['nothing'] is None, res
    assert res['again'].endswith('base/Scripts/demucs.exe'), res


# --------------------------------------------------------------------------- #
#  _demucs_command
# --------------------------------------------------------------------------- #
def test_demucs_command():
    def build(root, mod):
        pass

    def call(mod, root):
        out = []
        with patched(mod, _find_executable = lambda n: str(root / 'demucs.exe')):
            # chuẩn hoá từng phần tử: str(list) nhân đôi dấu '\\' của đường dẫn
            out.append([normalize(c, root) for c in mod._demucs_command()])
        fake_sys = types.SimpleNamespace(frozen = False, executable = 'C:/python.exe')
        with patched(mod, _find_executable = lambda n: None, importlib = make_importlib(True),
                    sys = fake_sys):
            out.append(mod._demucs_command())                            # import được demucs
        with patched(mod, _find_executable = lambda n: None, importlib = make_importlib(False),
                    sys = fake_sys):
            out.append(raises(mod._demucs_command))
        frozen = types.SimpleNamespace(frozen = True, executable = 'C:/app.exe')
        with patched(mod, _find_executable = lambda n: None, importlib = make_importlib(True),
                    sys = frozen):
            out.append(raises(mod._demucs_command))
        with patched(mod, _find_executable = lambda n: None, importlib = make_importlib(False),
                    sys = frozen):
            out.append(raises(mod._demucs_command))
        return out

    assert_same(run_both(build, call), '_demucs_command')
    res = shape('ref', build, call)
    # tìm được binary -> dùng thẳng, không hề thêm '-m demucs'
    assert res[0] == ['<ROOT>/demucs.exe'], res[0]
    # không có binary nhưng import được gói demucs và app chưa đóng gói
    # -> fallback đúng như tài liệu: [sys.executable, '-m', 'demucs']
    assert res[1] == ['C:/python.exe', '-m', 'demucs'], res[1]
    # ba nhánh còn lại đều NÉM RuntimeError (chứ không trả giá trị nào)
    assert res[2][0] == 'RuntimeError' and 'requirements.txt' in res[2][1], res[2]
    assert res[3] == res[2] and res[4] == res[2], res[3:]               # một thông báo lỗi duy nhất


def test_demucs_command_real_environment():
    '''Không đoán: chạy nguyên bản trong môi trường thật phải ra câu lệnh dùng được.'''
    ref = ref_module(DOTTED)
    kind, value = raises(ref._demucs_command)
    if kind == 'ok':
        assert isinstance(value, list) and value, value
        assert all(isinstance(c, str) for c in value), value
        assert value[0] == sys.executable or Path(value[0]).is_file(), value
    else:
        assert kind == 'RuntimeError' and 'Demucs' in value, value


# --------------------------------------------------------------------------- #
#  demucs_runtime_status
# --------------------------------------------------------------------------- #
def test_demucs_runtime_status():
    def build(root, mod):
        pass

    def call(mod, root):
        out = {}
        cmd = lambda: ['demucs.exe']
        boom = lambda: (_ for _ in ()).throw(RuntimeError('không thấy demucs'))
        with stub_modules(torch = make_torch('2.4.1+cu121', cuda = True),
                         **{'importlib.metadata': make_metadata('4.0.1')}):
            with patched(mod, _demucs_command = cmd):
                out['gpu'] = dict(mod.demucs_runtime_status())
        with stub_modules(torch = make_torch('2.4.1', cuda = False),
                         **{'importlib.metadata': make_metadata('4.0.1')}):
            with patched(mod, _demucs_command = cmd):
                out['cpu'] = dict(mod.demucs_runtime_status())
        with stub_modules(torch = make_torch(), **{'importlib.metadata': make_metadata()}):
            with patched(mod, _demucs_command = boom):
                out['no_cmd'] = dict(mod.demucs_runtime_status())
        bad_torch = types.SimpleNamespace(__version__ = '1.0', cuda = None)
        with stub_modules(torch = bad_torch, **{'importlib.metadata': make_metadata()}):
            with patched(mod, _demucs_command = cmd):
                out['no_cuda'] = dict(mod.demucs_runtime_status())
        with stub_modules(torch = make_torch(), **{'importlib.metadata': types.ModuleType('m')}):
            with patched(mod, _demucs_command = cmd):
                out['no_meta'] = dict(mod.demucs_runtime_status())
        return out

    assert_same(run_both(build, call), 'demucs_runtime_status')
    res = shape('ref', build, call)
    assert res['gpu']['available'] is True and res['gpu']['device'] == 'cuda', res['gpu']
    assert res['gpu']['demucs_version'] == '4.0.1' and res['gpu']['torch_version'] == '2.4.1+cu121'
    assert res['gpu']['command'] == ['demucs.exe'], res['gpu']
    assert 'error' not in res['gpu'], res['gpu']
    assert res['cpu']['available'] is True and res['cpu']['device'] == 'cpu', res['cpu']
    assert res['no_cmd']['available'] is False and res['no_cmd']['command'] is None, res['no_cmd']
    assert 'demucs' in res['no_cmd']['error'], res['no_cmd']
    assert res['no_cuda']['available'] is False and 'error' in res['no_cuda'], res['no_cuda']
    assert res['no_meta']['available'] is False, res['no_meta']
    for key in ('available', 'command', 'device', 'torch_version', 'demucs_version'):
        assert key in res['gpu'], key


def test_demucs_runtime_status_real_environment():
    ref = ref_module(DOTTED)
    st = ref.demucs_runtime_status()
    assert isinstance(st, dict) and 'available' in st and st['device'] in ('cpu', 'cuda'), st
    assert st['available'] is False or st['command'], st


# --------------------------------------------------------------------------- #
#  _run_cancellable (chỉ chạy `python -c` vài dòng)
# --------------------------------------------------------------------------- #
def py_cmd(code):
    return [sys.executable, '-c', code]


class FakeTime:
    '''Đồng hồ giả để vòng poll chạy hết ngay, không phải chờ giây thật.'''

    def __init__(self, step = 0.2):
        self.now = 0.0
        self.step = step
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += self.step


def fake_subprocess(exit_code):
    '''Tiến trình giả: poll() luôn trả ``exit_code`` (None = vẫn sống) và ghi lại kill().'''
    seen = {'killed': [], 'waited': [], 'command': None, 'kwargs': None}

    class Proc:
        returncode = exit_code

        def __init__(self, command, **kwargs):
            seen['command'] = [str(c) for c in command]
            seen['kwargs'] = sorted(kwargs)

        def poll(self):
            return exit_code

        def kill(self):
            seen['killed'].append('kill')

        def wait(self, timeout = None):
            seen['waited'].append(timeout)
            return exit_code

    fake = types.SimpleNamespace(
        Popen = Proc, STDOUT = -2, STARTUPINFO = subprocess.STARTUPINFO,
        CREATE_NO_WINDOW = 134217728, STARTF_USESHOWWINDOW = 1, SW_HIDE = 0)
    return fake, seen


def test_run_cancellable_ok():
    def build(root, mod):
        pass

    def call(mod, root):
        log = root / 'ok.log'
        mod._run_cancellable(py_cmd('print("xin chao")'), cancel_event = None, log_path = log)
        return {'rc': log.read_text(encoding = 'utf-8').strip(), 'exists': log.is_file(),
                'ret': mod._run_cancellable(py_cmd('pass'), cancel_event = None,
                                           log_path = root / 'p.log')}

    assert_same(run_both(build, call), '_run_cancellable thành công')
    res = shape('ref', build, call)
    assert res['rc'] == 'xin chao' and res['exists'] is True, res
    assert res['ret'] is None, res


def test_run_cancellable_cancel_and_timeout():
    def build(root, mod):
        pass

    def call(mod, root):
        out = {}
        ev = threading.Event()
        ev.set()
        # tiến trình thật vẫn sống khi cancel được bật -> module NÉM RuntimeError,
        # không có kiểu trả về 'đã dừng'
        out['cancel'] = raises(lambda: mod._run_cancellable(
            py_cmd('import time; time.sleep(30)'), cancel_event = ev, log_path = root / 'c.log'))
        out['timeout'] = raises(lambda: mod._run_cancellable(
            py_cmd('import time; time.sleep(30)'), cancel_event = None,
            log_path = root / 't.log', timeout_s = 0.5))
        # timeout_s <= 0 vẫn cho chạy: max(1.0, timeout_s)
        log3 = root / 'fast.log'
        mod._run_cancellable(py_cmd('print(1)'), cancel_event = None, log_path = log3,
                            timeout_s = 0)
        out['fast'] = log3.read_text(encoding = 'utf-8').strip()
        # hai nhánh dưới dùng tiến trình + đồng hồ giả để kết luận không phụ thuộc
        # tốc độ máy, và đo được cả kill()/wait(10)
        for key, event, tmo in (('stuck_cancel', ev, 7200.0), ('stuck_timeout', None, 0.5)):
            fake, seen = fake_subprocess(None)                   # poll() -> None mãi
            clock = FakeTime()
            with patched(mod, subprocess = fake, time = clock):
                out[key] = raises(lambda: mod._run_cancellable(
                    ['a'], cancel_event = event, log_path = root / (key + '.log'),
                    timeout_s = tmo))
                out[key + '_proc'] = (seen['killed'], seen['waited'], clock.slept)
        # poll() có mã ngay -> vòng lặp không chạy: cancel_event đã set cũng vô nghĩa
        done, seen2 = fake_subprocess(0)
        with patched(mod, subprocess = done, time = FakeTime()):
            out['exited'] = raises(lambda: mod._run_cancellable(
                ['a'], cancel_event = ev, log_path = root / 'd.log'))
            out['exited_proc'] = (seen2['killed'], seen2['command'])
        return out

    assert_same(run_both(build, call), '_run_cancellable dừng/hết giờ')
    res = shape('ref', build, call)
    assert res['cancel'] == ('RuntimeError', 'Đã dừng tách lời Demucs'), res['cancel']
    assert res['timeout'] == ('RuntimeError', 'Demucs quá thời gian chờ (0 giây)'), res['timeout']
    assert res['fast'] == '1', res
    assert res['stuck_cancel'] == ('RuntimeError', 'Đã dừng tách lời Demucs'), res['stuck_cancel']
    assert res['stuck_timeout'] == ('RuntimeError', 'Demucs quá thời gian chờ (0 giây)'), \
        res['stuck_timeout']
    # cả hai nhánh đều kill rồi wait(timeout=10) trước khi ném lỗi
    assert res['stuck_cancel_proc'] == (['kill'], [10], []), res['stuck_cancel_proc']
    # deadline = max(1.0, 0.5) nên 0.5 giây vẫn chờ đủ 5 nhịp poll 0.2 giây
    assert res['stuck_timeout_proc'] == (['kill'], [10], [0.2] * 5), res['stuck_timeout_proc']
    # Quirk của bản phát hành: cancel chỉ được xét GIỮA hai lần poll, nên tiến trình
    # đã kết thúc thì lệnh vẫn coi như thành công (không trả 'đã dừng').
    assert res['exited'] == ('ok', None), res['exited']
    assert res['exited_proc'] == ([], ['a']), res['exited_proc']


def test_run_cancellable_failure_and_log_tail():
    def build(root, mod):
        pass

    def call(mod, root):
        out = {}
        log = root / 'fail.log'
        out['code'] = raises(lambda: mod._run_cancellable(
            py_cmd('import sys; sys.stderr.write("loi xyz"); sys.exit(3)'),
            cancel_event = None, log_path = log))
        out['log'] = 'loi xyz' in log.read_text(encoding = 'utf-8')
        filler = ''.join(f'dong{i}\n' for i in range(400))
        big = root / 'big.log'
        kind, text = raises(lambda: mod._run_cancellable(
            py_cmd(f'import sys; sys.stdout.write({filler!r}); sys.stdout.flush(); sys.exit(2)'),
            cancel_event = None, log_path = big))
        out['tail'] = (kind, len(str(text)), str(text).endswith('dong399\n'),
                       'dong0' not in str(text))
        out['missing'] = raises(lambda: mod._run_cancellable(
            ['khong-co-binay-nay-dau.exe'], cancel_event = None, log_path = root / 'n.log'))
        return out

    assert_same(run_both(build, call), '_run_cancellable thất bại')
    res = shape('ref', build, call)
    assert res['code'][0] == 'RuntimeError', res['code']
    assert res['code'][1].startswith('Demucs lỗi (code=3): '), res['code']
    assert res['code'][1].endswith('loi xyz'), res['code']
    assert res['log'] is True, res
    assert res['tail'][0] == 'RuntimeError' and res['tail'][2] is True, res['tail']
    assert res['tail'][3] is True and res['tail'][1] < 1290, res['tail']  # chỉ giữ 1200 ký tự
    assert res['missing'][0] == 'FileNotFoundError', res['missing']


def test_run_cancellable_passes_hidden_window_kwargs():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (rep, ref):
        seen = {}

        class FakePopen:
            returncode = 0

            def __init__(self, command, **kwargs):
                seen['command'] = list(command)
                seen['kwargs'] = sorted(kwargs)
                seen['flags'] = kwargs.get('creationflags')

            def poll(self):
                return 0

        root = fresh_tree('kwargs')
        try:
            fake = types.SimpleNamespace(
                Popen = FakePopen, STDOUT = -2, STARTUPINFO = subprocess.STARTUPINFO,
                CREATE_NO_WINDOW = 134217728, STARTF_USESHOWWINDOW = 1, SW_HIDE = 0)
            with patched(mod, subprocess = fake):
                mod._run_cancellable(['a', 'b'], cancel_event = None, log_path = root / 'a.log')
            assert seen['command'] == ['a', 'b'], seen
            assert 'stdout' in seen['kwargs'] and 'stderr' in seen['kwargs'], seen
            assert 'text' in seen['kwargs'], seen
            if sys.platform.startswith('win'):
                assert seen['flags'] == 134217728, seen
        finally:
            shutil.rmtree(root, ignore_errors = True)


# --------------------------------------------------------------------------- #
#  separate_background: dựng câu lệnh + đường dẫn, không chạy tiến trình
# --------------------------------------------------------------------------- #
class RunnerSpy:
    '''Thay _run_cancellable: ghi lại command, mô phỏng sản phẩm của ffmpeg/demucs.'''

    def __init__(self, mode = 'ok'):
        self.mode = mode
        self.calls = []
        self.failed_once = False
        self.cancel_after = None                        # threading.Event, set sau mỗi lệnh
        self.cancel_stage = None                        # None | 'extract' | 'demucs'

    def _want_cancel(self, demucs_stage):
        return (self.cancel_after is not None
                and (self.cancel_stage is None
                     or self.cancel_stage == ('demucs' if demucs_stage else 'extract')))

    def __call__(self, command, *, cancel_event = None, log_path = None, timeout_s = None):
        cmd = [str(c) for c in command]
        self.calls.append({'cmd': cmd, 'timeout': timeout_s,
                           'log': Path(log_path).name if log_path else None})
        demucs_stage = any(c.startswith('--two-stems') for c in cmd)
        try:
            self._simulate(cmd, demucs_stage)
        finally:
            # đặt event SAU lệnh đang mô phỏng, kể cả khi lệnh ném lỗi -> người dùng
            # bấm dừng ngay trong giai đoạn đó
            if self._want_cancel(demucs_stage):
                self.cancel_after.set()

    def _simulate(self, cmd, demucs_stage):
        if not demucs_stage:                                                      # lệnh ffmpeg
            if self.mode == 'empty_extract':
                return
            if self.mode == 'tiny_extract':
                Path(cmd[-1]).parent.mkdir(parents = True, exist_ok = True)
                Path(cmd[-1]).write_bytes(b'x' * 10)
                return
            Path(cmd[-1]).parent.mkdir(parents = True, exist_ok = True)
            Path(cmd[-1]).write_bytes(b'w' * 5000)
        else:                                                         # lệnh demucs
            if self.mode == 'demucs_fail' and not self.failed_once:
                self.failed_once = True
                raise RuntimeError('Demucs loi (code=1): CUDA out of memory')
            if self.mode == 'no_output':
                return
            out_root = Path(cmd[cmd.index('-o') + 1])
            model = cmd[cmd.index('-n') + 1]
            stem = Path(cmd[-1]).stem
            folder = 'other' if self.mode == 'deep_output' else stem
            target = out_root / model / folder / 'no_vocals.wav'
            target.parent.mkdir(parents = True, exist_ok = True)
            target.write_bytes(b'v' * (10 if self.mode == 'tiny_output' else 8000))


def bg_fixture(root, mode = 'ok', device = 'cpu', runtime_ok = True):
    video = touch(root / 'media' / 'clip source.mp4', 4000)
    spy = RunnerSpy(mode)
    if runtime_ok:
        status = {'available': True, 'command': ['demucs.exe'], 'device': device,
                  'torch_version': '2.4.1', 'demucs_version': '4.0.1'}
    else:
        status = {'available': False, 'command': None, 'device': 'cpu', 'torch_version': '',
                  'demucs_version': '', 'error': 'No module named demucs'}
    return video, spy, status


def bg_patch(mod, root, spy, status):
    return patched(mod, _run_cancellable = spy, demucs_runtime_status = lambda: status,
                   _find_executable = lambda name: 'ffmpeg-test' if name == 'ffmpeg' else None,
                   _demucs_command = lambda: ['demucs.exe'], tempfile = FakeTempfile(root))


def test_separate_background_builds_expected_commands():
    def build(root, mod):
        pass

    def call(mod, root):
        video, spy, status = bg_fixture(root)
        events = []
        with bg_patch(mod, root, spy, status):
            out = mod.separate_background(video, progress = lambda v, m: events.append(
                (round(v, 2), m)))
        first, second = spy.calls
        cache_dir = root / 'winterboy_demucs_cache'
        return {'n_calls': len(spy.calls), 'out': normalize(out, root),
                'extract_head': [normalize(x, root) for x in first['cmd'][:8]],
                'extract_tail': [normalize(x, root) for x in first['cmd'][8:]],
                'extract_timeout': first['timeout'], 'extract_log': first['log'],
                'demucs': [normalize(x, root) for x in second['cmd']],
                'demucs_log': second['log'], 'demucs_timeout': second['timeout'],
                'events': events, 'size': out.stat().st_size,
                'files': sorted(normalize(str(p.relative_to(root)), root)
                               for p in cache_dir.rglob('*'))}

    assert_same(run_both(build, call), 'separate_background')
    res = shape('ref', build, call)
    assert res['n_calls'] == 2, res
    assert res['extract_head'] == ['ffmpeg-test', '-y', '-hide_banner', '-loglevel', 'error',
                                   '-i', '<ROOT>/media/clip source.mp4', '-vn'], res['extract_head']
    assert res['extract_tail'][:4] == ['-ac', '2', '-ar', '44100'], res['extract_tail']
    assert res['extract_tail'][-1].endswith('source_audio.wav'), res['extract_tail']
    assert res['extract_timeout'] == 3600 and res['extract_log'] == 'ffmpeg_extract.log', res
    assert res['demucs'][0] == 'demucs.exe', res['demucs']
    # 11 phần tử: binary + 10 tham số; '-o' đứng ở chỉ mục 8 nên thư mục 'separated'
    # nằm ở 9 và file audio ở 10
    assert len(res['demucs']) == 11, res['demucs']
    assert res['demucs'][1:8] == ['--two-stems=vocals', '-n', 'htdemucs', '-d', 'cpu', '-j', '1'], \
        res['demucs']
    assert res['demucs'][8] == '-o', res['demucs']
    assert res['demucs'][9].endswith('/separated'), res['demucs']
    assert res['demucs'][10].endswith('/source_audio.wav'), res['demucs']
    assert res['demucs_log'] == 'demucs.log' and res['demucs_timeout'] is None, res
    assert res['events'] == [(0.02, 'Demucs · chuẩn bị tách lời…'),
                             (0.12, 'Demucs · đang tách lời thoại gốc bằng CPU…'),
                             (1.0, 'Demucs · đã tách lời và lưu cache')], res['events']
    assert res['size'] == 8000 and res['out'].endswith('_no_vocals.wav'), res
    assert res['files'] == ['winterboy_demucs_cache/<FP>_no_vocals.wav',
                            'winterboy_demucs_cache/artifact_manifest.json'], res['files']


def test_separate_background_cache_hit_and_manifest():
    def build(root, mod):
        pass

    def call(mod, root):
        video, spy, status = bg_fixture(root)
        events = []
        cache_file = root / 'winterboy_demucs_cache' / 'artifact_manifest.json'
        with bg_patch(mod, root, spy, status):
            first = mod.separate_background(video, progress = lambda v, m: events.append(v))
            n_after_first = len(spy.calls)
            second = mod.separate_background(video, progress = lambda v, m: events.append(v))
            # manifest ngay sau lần HIT: chỉ có 1 chứng từ, HIT không ghi thêm
            mid = json.loads(cache_file.read_text(encoding = 'utf-8'))
            video.write_bytes(b'2' * 4000)                        # đổi nội dung -> MISS
            third = mod.separate_background(video)
            fourth = mod.separate_background(video, model = 'htdemucs_6s')
            same = mod.separate_background(video, model = 'htdemucs_6s')
            manifest = json.loads(cache_file.read_text(encoding = 'utf-8'))
        # kho chứng từ nằm ở mục 'artifacts' (còn 'version' + 'updated_at' ở cấp cao nhất)
        entries = manifest.get('artifacts') or {}
        keys = sorted(entries)
        records = [entries[k] for k in keys]
        # bỏ trường biến động (mtime của video, updated_at) chỉ giữ phần ổn định
        deps = sorted({tuple(sorted((d, v) for d, v in r['dependencies'].items() if d != 'source'))
                       for r in records})
        return {'same_first_second': str(first) == str(second), 'n_after_first': n_after_first,
                'n_calls': len(spy.calls), 'third_differs': str(third) != str(first),
                'fourth_differs': str(fourth) != str(third),
                'same_model': str(same) == str(fourth), 'n_keys': len(keys),
                'n_keys_after_hit': len(mid.get('artifacts') or {}),
                'top_keys': sorted(manifest),
                'key_prefix': sorted({k.split(':')[0] for k in keys}),
                'key_shape': sorted(len(k.split(':')[1]) for k in keys),
                'fp_is_key': sorted(r['fingerprint'] == k.split(':', 1)[1]
                                    for k, r in zip(keys, records)),
                'record_keys': sorted({tuple(sorted(r)) for r in records}),
                'meta_keys': sorted({tuple(sorted(r['metadata'])) for r in records}),
                'deps': deps,
                'outputs': sorted(normalize(Path(r['output']).name, root) for r in records),
                'exists': sorted(Path(r['output']).is_file() for r in records),
                'sizes': sorted(Path(r['output']).stat().st_size for r in records),
                'events': [round(e, 2) for e in events]}

    assert_same(run_both(build, call), 'separate_background cache')
    res = shape('ref', build, call)
    assert res['same_first_second'] is True and res['n_after_first'] == 2, res
    assert res['n_calls'] == 6, res                                   # ba lần MISS, một lần HIT
    assert res['third_differs'] is True and res['fourth_differs'] is True, res
    assert res['same_model'] is True, res
    assert res['n_keys'] == 3 and res['n_keys_after_hit'] == 1, res    # HIT không ghi chứng từ
    assert res['top_keys'] == ['artifacts', 'updated_at', 'version'], res['top_keys']
    assert res['key_prefix'] == ['demucs'], res['key_prefix']
    # id chứng từ = 'demucs:' + sha256 của dependencies -> 3 khóa khác nhau
    assert res['key_shape'] == [64, 64, 64], res['key_shape']
    assert res['fp_is_key'] == [True, True, True], res['fp_is_key']
    assert res['record_keys'] == [('dependencies', 'fingerprint', 'metadata', 'output',
                                   'updated_at')], res['record_keys']
    assert res['meta_keys'] == [('demucs_version', 'device', 'model', 'source', 'torch_version')], \
        res['meta_keys']
    # đúng 2 bộ tham số: model htdemucs và htdemucs_6s, sample rate luôn 44100
    assert res['deps'] == [(('demucs_version', '4.0.1'), ('model', 'htdemucs'),
                            ('sample_rate', 44100), ('stems', 'vocals'), ('version', 2)),
                           (('demucs_version', '4.0.1'), ('model', 'htdemucs_6s'),
                            ('sample_rate', 44100), ('stems', 'vocals'), ('version', 2))], res['deps']
    assert res['outputs'] == ['<FP>_no_vocals.wav'] * 3, res['outputs']
    assert res['exists'] == [True, True, True] and res['sizes'] == [8000, 8000, 8000], res
    assert res['events'] == [0.02, 0.12, 1.0, 1.0], res['events']     # lần 2 là cache HIT


def test_separate_background_cuda_fallback():
    def build(root, mod):
        pass

    def call(mod, root):
        video, spy, status = bg_fixture(root, mode = 'demucs_fail', device = 'cuda')
        events = []
        with bg_patch(mod, root, spy, status):
            res = raises(lambda: mod.separate_background(
                video, progress = lambda v, m: events.append(round(v, 2))))
        cmds = [c['cmd'] for c in spy.calls]
        # chỉ lệnh demucs mới có -d/-n/-o; lệnh ffmpeg trích audio thì không
        demucs_cmds = [c for c in cmds if any(x.startswith('--two-stems') for x in c)]
        return {'res': res, 'events': events, 'n_calls': len(spy.calls),
                'logs': [c['log'] for c in spy.calls],
                'devices': [c[c.index('-d') + 1] for c in demucs_cmds],
                'models': [c[c.index('-n') + 1] for c in demucs_cmds],
                'roots': [normalize(c[c.index('-o') + 1], root) for c in demucs_cmds],
                'inputs': [normalize(c[-1], root) for c in demucs_cmds],
                'n_args': [len(c) for c in cmds]}

    assert_same(run_both(build, call), 'separate_background fallback CUDA')
    res = shape('ref', build, call)
    assert res['res'][0] == 'ok', res['res']
    assert res['n_calls'] == 3, res
    assert res['logs'] == ['ffmpeg_extract.log', 'demucs.log', 'demucs_cpu.log'], res
    assert res['devices'] == ['cuda', 'cpu'], res['devices']          # đúng một lần thử lại
    # lần thử lại giữ nguyên model, thư mục -o và file vào, chỉ đổi -d
    assert res['models'] == ['htdemucs', 'htdemucs'], res['models']
    assert len(set(res['roots'])) == 1 and len(set(res['inputs'])) == 1, res
    # 13 tham số cho ffmpeg, 11 cho demucs (binary + 10 tham số)
    assert res['n_args'] == [13, 11, 11], res['n_args']
    assert res['events'] == [0.02, 0.12, 0.14, 1.0], res['events']


def test_separate_background_errors():
    def build(root, mod):
        pass

    def call(mod, root):
        out = {}
        for mode, key in (('empty_extract', 'no_audio'), ('tiny_extract', 'tiny_audio'),
                          ('no_output', 'no_out'), ('tiny_output', 'tiny_out')):
            video, spy, status = bg_fixture(root, mode = mode)
            with bg_patch(mod, root, spy, status):
                out[key] = raises(lambda: mod.separate_background(video))
        video, spy, status = bg_fixture(root, mode = 'demucs_fail', device = 'cpu')
        with bg_patch(mod, root, spy, status):
            out['cpu_fail'] = raises(lambda: mod.separate_background(video))
        out['cpu_fail_calls'] = (len(spy.calls), [c['log'] for c in spy.calls])
        # dừng NGAY TRONG giai đoạn demucs: module không thử lại bằng CPU mà ném tiếp
        # lỗi gốc (thông báo chứa 'cuda' nhưng cancel_event đã set)
        video, spy, status = bg_fixture(root, mode = 'demucs_fail', device = 'cuda')
        ev = threading.Event()
        spy.cancel_after = ev
        spy.cancel_stage = 'demucs'
        with bg_patch(mod, root, spy, status):
            out['cuda_cancel'] = raises(lambda: mod.separate_background(video, cancel_event = ev))
        out['cuda_cancel_calls'] = (len(spy.calls), [c['log'] for c in spy.calls])
        # người dùng bấm dừng từ trước: NÉM RuntimeError('Đã dừng tách lời Demucs')
        # ở nhịp kiểm tra giữa hai giai đoạn, chứ không trả về Path
        video, spy, status = bg_fixture(root)
        pre = threading.Event()
        pre.set()
        with bg_patch(mod, root, spy, status):
            out['cancel_before'] = raises(lambda: mod.separate_background(video,
                                                                           cancel_event = pre))
        out['cancel_before_calls'] = (len(spy.calls), [c['log'] for c in spy.calls])
        video, spy, status = bg_fixture(root)
        with patched(mod, _find_executable = lambda name: None):
            out['no_ffmpeg'] = raises(lambda: mod.separate_background(video))
        video, spy, status = bg_fixture(root, runtime_ok = False)
        with bg_patch(mod, root, spy, status):
            out['no_runtime'] = raises(lambda: mod.separate_background(video))
        with bg_patch(mod, root, spy, status):
            out['missing_src'] = raises(lambda: mod.separate_background(root / 'khong-co.mp4'))
        video, spy, status = bg_fixture(root, mode = 'deep_output')
        with bg_patch(mod, root, spy, status):
            deep = mod.separate_background(video)
        out['deep'] = [normalize(deep.name, root), deep.stat().st_size]
        return out

    assert_same(run_both(build, call), 'separate_background các nhánh lỗi')
    res = shape('ref', build, call)
    for key in ('no_audio', 'tiny_audio'):
        assert res[key] == ('RuntimeError', 'Không trích được audio hợp lệ cho Demucs'), (key, res)
    for key in ('no_out', 'tiny_out'):
        assert res[key][0] == 'RuntimeError' and 'no_vocals.wav' in res[key][1], res[key]
    # device='cpu' -> nhánh fallback CUDA bị chặn ngay từ điều kiện, lỗi gốc ném thẳng
    assert res['cpu_fail'][1] == 'Demucs loi (code=1): CUDA out of memory', res['cpu_fail']
    assert res['cpu_fail_calls'] == (2, ['ffmpeg_extract.log', 'demucs.log']), res['cpu_fail_calls']
    assert res['cuda_cancel'][1] == 'Demucs loi (code=1): CUDA out of memory', res['cuda_cancel']
    # đã bấm dừng thì KHÔNG chạy lần hai với CPU
    assert res['cuda_cancel_calls'] == (2, ['ffmpeg_extract.log', 'demucs.log']), \
        res['cuda_cancel_calls']
    assert res['cancel_before'] == ('RuntimeError', 'Đã dừng tách lời Demucs'), res['cancel_before']
    assert res['cancel_before_calls'] == (1, ['ffmpeg_extract.log']), res['cancel_before_calls']
    assert res['no_ffmpeg'][1] == 'Không tìm thấy ffmpeg để chuẩn bị audio cho Demucs', res
    assert res['no_runtime'][1] == 'No module named demucs', res
    assert res['missing_src'][0] == 'FileNotFoundError', res
    # Quirk của bản phát hành: thư mục con không trùng tên file vẫn được rglob chấp
    # nhận, nên 'deep_output' vẫn hoàn tất với đúng một lệnh demucs.
    assert res['deep'] == ['<FP>_no_vocals.wav', 8000], res['deep']



def test_separate_background_cancel_between_stages():
    def build(root, mod):
        pass

    def call(mod, root):
        video, spy, status = bg_fixture(root)
        ev = threading.Event()
        spy.cancel_after = ev                                  # bấm dừng khi ffmpeg đang chạy
        with bg_patch(mod, root, spy, status):
            res = raises(lambda: mod.separate_background(video, cancel_event = ev))
        cache_dir = root / 'winterboy_demucs_cache'
        return {'res': res, 'n_calls': len(spy.calls),
                'temp_left': sorted(normalize(p.name, root) for p in root.iterdir()),
                'cache_left': sorted(normalize(p.name, root) for p in cache_dir.iterdir())}

    assert_same(run_both(build, call), 'separate_background dừng giữa chừng')
    res = shape('ref', build, call)
    # cancel ở nhịp kiểm tra giữa hai giai đoạn -> NÉM RuntimeError, không trả Path
    assert res['res'] == ('RuntimeError', 'Đã dừng tách lời Demucs'), res
    assert res['n_calls'] == 1, res                                    # chưa kịp gọi demucs
    assert res['temp_left'] == ['media', 'winterboy_demucs_cache'], res   # folder tạm đã dọn
    # trong cache chỉ còn chỗ đựng log tạm đã bị xoá: chưa có sản phẩm, chưa có chứng từ
    assert res['cache_left'] == [], res['cache_left']



def test_separate_background_signature_defaults():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    sig_r, sig_p = inspect.signature(ref.separate_background), inspect.signature(
        rep.separate_background)
    assert str(sig_r) == str(sig_p)
    assert sig_r.parameters['model'].default == 'htdemucs'
    assert sig_r.parameters['cancel_event'].default is None
    assert sig_r.parameters['progress'].default is None
    assert sig_r.parameters['video_path'].annotation == 'str | Path'
    assert sig_r.return_annotation == 'Path'
    assert ref._run_cancellable.__kwdefaults__ == rep._run_cancellable.__kwdefaults__ == \
        {'timeout_s': 7200.0}
    assert ref.separate_background.__kwdefaults__ == \
        rep.separate_background.__kwdefaults__ == {'cancel_event': None, 'progress': None,
                                                   'model': 'htdemucs'}

# -*- coding: utf-8 -*-
'''Khung test đối chiếu: module trong repo phải cho kết quả như .pyc gốc.

Repo được dịch ngược từ bytecode nên "sửa được" chưa chắc "đúng". Mỗi hàm khôi phục
phải chạy qua đây: cùng một đầu vào, bản repo và bản đã phát hành phải trả kết quả
giống hệt nhau (hoặc cùng kiểu lỗi).

Dùng:
    from tests._parity import same_result, ref_module, repo_module
    same_result("format_ts", [(0,), (1.5,), (3661.5,)])

Tham số INTERNAL trỏ tới thư mục _internal của bản đã cài; không có thì test bỏ qua
(không fail) để người đóng góp từ máy khác vẫn chạy được.
'''
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERNAL = Path(os.environ.get('WINTERBOY_INTERNAL',
                               r"C:\Users\Administrator\MumuStudioPro\{app}\_internal"))


class RefMissing(Exception):
    pass


class block_modules:
    '''Chặn module để cả hai bên cùng đi qua một nhánh code.

    Bản đã cài có sẵn ``pysrt`` nên ``parse_srt_string`` đi nhánh fast path, trong khi
    máy chạy test thì không có -> phải chặn đi để so đúng phần logic thuần.
    '''

    def __init__(self, *names):
        self.names = names
        self.saved = {}

    def __enter__(self):
        for n in self.names:
            self.saved[n] = sys.modules.get(n, False)
            sys.modules[n] = None                       # import sẽ raise ImportError
        return self

    def __exit__(self, *exc):
        for n, v in self.saved.items():
            if v is False:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = v
        return False


def _purge_app_modules():
    for name in [n for n in sys.modules if n == 'app' or n.startswith('app.')]:
        del sys.modules[name]


def _load_from(root, dotted):
    '''Nạp module thẳng từ file, KHÔNG đi qua ``app/services/__init__.py``.

    __init__ của gói đó import cả loạt module (nhiều cái còn hỏng cú pháp), nên nếu
    import theo tên gói thì một module sạch cũng không nạp được. Nạp theo đường dẫn
    giúp test từng file độc lập, và hai bên cùng một cách nạp.
    '''
    rel = dotted.split('.')
    base = root.joinpath(*rel)
    path = base.with_suffix('.py')
    if not path.is_file():
        path = base.with_suffix('.pyc')
    if not path.is_file():
        raise FileNotFoundError(f'không thấy {dotted} trong {root}')
    name = f'parity_{path.stem}_{abs(hash(str(root))) % 99999}'
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def repo_module(dotted):
    '''Nạp app.x.y từ mã nguồn repo.'''
    return _load_from(REPO, dotted)


def ref_module(dotted):
    '''Nạp cùng tên từ bản đã cài đặt (.pyc).'''
    if not INTERNAL.is_dir():
        raise RefMissing(f'không có _internal ở {INTERNAL}')
    return _load_from(INTERNAL, dotted)


def _call(fn, args, kwargs):
    try:
        return ('ok', fn(*args, **kwargs))
    except Exception as exc:                              # noqa: BLE001 - so lỗi cũng là hành vi
        return ('err', type(exc).__name__)


def fingerprint(value):
    '''Biểu diễn kết quả ổn định để so 2 bên, không phụ thuộc đối tượng thừa.'''
    if isinstance(value, tuple) and len(value) == 2 and value[0] in ('ok', 'err'):
        kind, val = value
        return (kind, fingerprint(val))
    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return repr(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [fingerprint(v) for v in value]
        if isinstance(value, (set, frozenset)):
            items.sort()
        return (type(value).__name__, items)
    if isinstance(value, dict):
        return ('dict', sorted((k, fingerprint(v)) for k, v in value.items()))
    if hasattr(value, '__dataclass_fields__'):
        return (type(value).__name__,
                [(f.name, fingerprint(getattr(value, f.name, None)))
                 for f in value.__dataclass_fields__.values()])
    if isinstance(value, Path):
        return ('Path', str(value).replace('\\', '/'))
    return (type(value).__name__, repr(value))


def same_result(dotted, func, cases, *, attrs=None, block=()):
    '''Chạy ``func`` trên repo và bản gốc với từng bộ tham số, đòi kết quả khớp.

    cases: list[(args_tuple, kwargs_dict)]
    attrs: hàm biến đổi kết quả (vd chỉ lấy một field) nếu muốn so một phần.
    block: tên module giả vờ thiếu để hai bên cùng đi một nhánh code.
    Trả về list mâu thuẫn: [((args, kwargs), kết_quả_repo, kết_quả_gốc)].
    '''
    args_list = [(c if isinstance(c, tuple) and len(c) == 2 else (c, {})) for c in cases]
    bad = []
    with block_modules(*block):                      # import trong lúc gọi, phải chặn cả lúc gọi
        ref = ref_module(dotted)
        rep = repo_module(dotted)
        fn_ref = _resolve(ref, func)
        fn_rep = _resolve(rep, func)
        for args, kwargs in args_list:
            a = _call(fn_rep, args, kwargs)
            b = _call(fn_ref, args, kwargs)
            if attrs:
                a = ('ok', attrs(a[1])) if a[0] == 'ok' else a
                b = ('ok', attrs(b[1])) if b[0] == 'ok' else b
            if fingerprint(a) != fingerprint(b):
                bad.append(((args, kwargs), a, b))
    return bad


def _resolve(mod, dotted_func):
    obj = mod
    for part in dotted_func.split('.'):
        obj = getattr(obj, part)
    return obj


def describe(pair):
    kind, val = pair
    return f'{kind}: {val!r}'[:160]

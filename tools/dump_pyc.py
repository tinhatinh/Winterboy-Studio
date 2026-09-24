# -*- coding: utf-8 -*-
'''In "khung" của module đã biên dịch (.pyc) để khôi phục mã nguồn có căn cứ.

Repo này được sinh ra bằng Decompyle++ nên nhiều chỗ mất thân hàm hoặc ra mã
không hợp lệ (`SrtCue = <NODE:12>()`). Thay vì đoán, tool này nạp .pyc gốc từ bản
đã cài đặt và in ra thứ chắc chắn đúng: lớp, trường dataclass, chữ ký hàm,
docstring, hằng cấp module — kèm thân giải mã bytecode khi cần.

    python tools/dump_pyc.py app.services.srt_utils
    python tools/dump_pyc.py app.services.capcut_tts_engine --body parse_voice_key
    python tools/dump_pyc.py app.services.srt_utils --all-bodies

Muốn có chữ ký thật thì phải import được module, tức chạy trong môi trường có đủ
thư viện của app. Tool tự thêm thư mục _internal vào sys.path.
'''
from __future__ import annotations

import argparse
import dataclasses
import dis
import importlib
import inspect
import io
import sys
import types
from contextlib import redirect_stdout

INTERNAL = r"C:\Users\Administrator\MumuStudioPro\{app}\_internal"

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def _default_repr(obj):
    if obj is dataclasses.MISSING:
        return None
    return repr(obj)


def dump_class(cls, indent='', bodies=False):
    out = [f'{indent}class {cls.__name__}{_bases(cls)}:']
    doc = inspect.getdoc(cls)
    if doc:
        out.append(f'{indent}    """{doc}"""')
    if dataclasses.is_dataclass(cls):
        out.insert(0, f'{indent}@dataclass')
        for f in dataclasses.fields(cls):
            d = _default_repr(f.default)
            if d is None and f.default_factory is not dataclasses.MISSING:
                d = f'field(default_factory={f.default_factory.__name__})'
                out.append(f'{indent}    {f.name}: {f.type} = {d}')
            elif d is None:
                out.append(f'{indent}    {f.name}: {f.type}')
            else:
                out.append(f'{indent}    {f.name}: {f.type} = {d}')
    own = [n for n, o in vars(cls).items()
           if isinstance(o, (types.FunctionType, types.BuiltinFunctionType))
           and not n.startswith('__')]
    statics = [n for n, o in vars(cls).items() if isinstance(o, staticmethod)]
    classmethods = [n for n, o in vars(cls).items() if isinstance(o, classmethod)]
    props = [n for n, o in vars(cls).items() if isinstance(o, property)]
    for n in sorted(own):
        out.append(f'{indent}    def {n}{_sig(getattr(cls, n))}:{_ellipsis(doc)}')
    for n in sorted(statics):
        raw = vars(cls)[n]
        fn = raw.__func__ if isinstance(raw, staticmethod) else raw
        out.append(f'{indent}    @staticmethod\n{indent}    def {n}'
                   f'{_sig(fn)}:{_ellipsis(doc)}')
    for n in sorted(classmethods):
        raw = vars(cls)[n]
        fn = raw.__func__ if isinstance(raw, classmethod) else raw
        out.append(f'{indent}    @classmethod\n{indent}    def {n}'
                   f'{_sig(fn)}:{_ellipsis(doc)}')
    for n in sorted(props):
        out.append(f'{indent}    @property\n{indent}    def {n}(self):{_ellipsis(doc)}')
    if not own and not statics and not classmethods and not props \
            and not dataclasses.is_dataclass(cls):
        out.append(f'{indent}    ...')
    return '\n'.join(out)


def _ellipsis(indent=''):
    return f' {indent}pass' if False else ' ...'


def _bases(cls):
    bs = [b.__name__ for b in cls.__bases__ if b is not object]
    return f'({", ".join(bs)})' if bs else ''


def _sig(fn):
    try:
        return str(inspect.signature(fn))
    except (TypeError, ValueError):
        return '(...)'


def dump_body(fn):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            dis.dis(fn)
    except Exception as exc:
        return f'  <không giải mã được: {exc}>'
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module')
    ap.add_argument('--internal', default=INTERNAL)
    ap.add_argument('--body', action='append', default=[], help='in dis của hàm này (lặp được)')
    ap.add_argument('--all-bodies', action='store_true')
    ap.add_argument('--consts', action='store_true', help='liệt kê hằng chuỗi cấp module')
    args = ap.parse_args()

    sys.path.insert(0, args.internal)
    mod = importlib.import_module(args.module)
    head = mod.__name__
    print(f'# ===== {head} =====')
    doc = inspect.getdoc(mod)
    if doc:
        print('# docstring:\n' + '\n'.join(f'#   {l}' for l in doc.splitlines()))

    classes, funcs, others = [], [], []
    for name, obj in vars(mod).items():
        if name.startswith('__'):
            continue
        if isinstance(obj, type) and getattr(obj, '__module__', '') == head:
            classes.append((name, obj))
        elif isinstance(obj, types.FunctionType) and getattr(obj, '__module__', '') == head:
            funcs.append((name, obj))
        else:
            others.append((name, obj))

    for name, val in sorted(others):
        if isinstance(val, (str, int, float, bool, tuple, list, dict, set, types.NoneType)):
            r = repr(val)
            print(f'{name} = {r if len(r) <= 150 else r[:147] + "..."}')
    print()
    for name, cls in sorted(classes):
        print(dump_class(cls))
        print()
    for name, fn in sorted(funcs):
        print(f'def {name}{_sig(fn)}: ...')
    if args.consts:
        print('\n# --- chuỗi trong bytecode ---')
        seen = set()
        stack = [mod.__dict__]
        while stack:
            cur = stack.pop()
            vals = cur.values() if isinstance(cur, dict) else [cur]
            for v in vals:
                if isinstance(v, types.ModuleType):
                    continue
                if isinstance(v, (types.FunctionType, types.CodeType)):
                    code = v.co_code if isinstance(v, types.CodeType) else v.__code__
                    for c in code.co_consts:
                        if isinstance(c, str) and c not in seen:
                            seen.add(c)
                            print(f'  {c!r}')
                        elif hasattr(c, 'co_code'):
                            stack.append(c)
    targets = list(args.body)
    if args.all_bodies:
        targets = [n for n, _ in funcs]
    for t in targets:
        fn = getattr(mod, t, None)
        if fn is None:
            print(f'\n# không tìm thấy {t}')
            continue
        print(f'\n# ===== dis {head}.{t} =====')
        print(dump_body(fn))
    return 0


if __name__ == '__main__':
    sys.exit(main())

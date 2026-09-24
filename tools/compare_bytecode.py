# -*- coding: utf-8 -*-
'''So sánh bytecode: .py trong repo phải biên dịch ra ĐÚNG mã như .pyc đã phát hành.

Đây là cổng kiểm mạnh nhất mà không cần gọi mạng: nếu chuỗi lệnh (opname + arg, code
object lồng nhau quy về vân tay đệ quy) khớp từng instruction thì hành vi chắc chắn
giống bản đã build — kể cả mấy chỗ dịch ngược ra mã "hợp lệ nhưng sai" kiểu ``.items()``
thừa, ``audio[:,0]`` viết thành ``audio[0]``, hay ``try`` đặt sai cấp độ.

    python tools/compare_bytecode.py app/services/tts_preview.py
    python tools/compare_bytecode.py app/services/edge_tts_engine.py --names normalize_voice
    python tools/compare_bytecode.py --all      # đo cả repo, xếp theo số chỗ khác

Exit code: 0 = khớp tuyệt đối (hoặc --all), 1 = có chỗ khác.
'''
from __future__ import annotations

import argparse
import dis
import marshal
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERNAL = Path(os.environ.get('WINTERBOY_INTERNAL',
                               r"C:\Users\Administrator\MumuStudioPro\{app}\_internal"))
# CACHE/RESUME/NOP là padding của pipeline 3.11+, không mang hành vi
SKIP = {'CACHE', 'RESUME', 'NOP'}
# jump target tính bằng byte nên đổi theo khoảng cách dòng; so hình dạng lệnh, không so con số
JUMPS = {'FOR_ITER', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE', 'POP_JUMP_IF_NONE',
         'POP_JUMP_IF_NOT_NONE', 'JUMP_FORWARD', 'JUMP_BACKWARD', 'SEND',
         'JUMP_BACKWARD_NO_INTERRUPT', 'RETURN_GENERATOR'}
SHAPE = ('name', 'argcount', 'kwonly', 'posonly', 'nlocals', 'stack', 'flags',
         'varnames', 'cellvars', 'freevars', 'consts')


def _consts(code):
    '''Mọi hằng số của code object, gồm cả chuỗi.

    LOAD_CONST mang arg là CHỈ SỐ vào co_consts, nên đổi nội dung chuỗi thì lệnh
    vẫn y hệt và phép so lệnh không hề biết. Đây chính là lỗ hổng đã cho phép
    'Winterboy Studio' lọt qua trong khi bản phát hành ghi 'Winterboy studio'.
    Code object lồng nhau chỉ lấy tên: thân nó được so riêng ở vòng lặp khác.
    '''
    out = []
    for c in code.co_consts:
        if hasattr(c, 'co_name') and hasattr(c, 'co_code'):
            out.append(('CODE', c.co_qualname))
        else:
            out.append(norm_arg(c))
    return tuple(out)

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def load_ref(dotted):
    p = INTERNAL.joinpath(*dotted.split('.')).with_suffix('.pyc')
    if not p.is_file():
        raise FileNotFoundError(p)
    return marshal.loads(p.read_bytes()[16:])


def norm_arg(arg, opname=''):
    if opname in JUMPS:
        return None
    if hasattr(arg, 'co_name') and hasattr(arg, 'co_code'):
        return ('CODE',) + fingerprint(arg)
    if isinstance(arg, tuple):
        return tuple(norm_arg(a) for a in arg)
    if isinstance(arg, list):
        return tuple(norm_arg(a) for a in arg)
    if isinstance(arg, (set, frozenset)):
        return ('set', tuple(sorted(map(repr, arg))))
    if isinstance(arg, dict):
        return ('dict', tuple(sorted((repr(k), repr(norm_arg(v))) for k, v in arg.items())))
    if isinstance(arg, (str, bytes, int, float, complex, bool, type(None))):
        return arg
    return ('obj', repr(arg)[:80])


def fingerprint(code):
    '''Vân tay đệ quy: hình dạng code object + hằng số + chuỗi lệnh.'''
    ops = []
    for i in dis.get_instructions(code):
        if i.opname in SKIP:
            continue
        ops.append((i.opname, norm_arg(i.arg, i.opname)))
    head = (code.co_name, code.co_argcount, code.co_kwonlyargcount,
            code.co_posonlyargcount, code.co_nlocals, code.co_stacksize,
            code.co_flags, code.co_varnames, code.co_cellvars, code.co_freevars,
            _consts(code))
    return head + (tuple(ops),)


def index(code, out=None):
    '''Gom mọi code object lồng theo tên (giữ thứ tự xuất hiện).'''
    out = out if out is not None else {}
    for c in code.co_consts:
        if hasattr(c, 'co_name') and hasattr(c, 'co_code'):
            out.setdefault(c.co_name, []).append(c)
            index(c, out)
    return out


def _brief(value, limit=140):
    '''Rút gọn để in: vân tay code object lồng nhau dài hàng chục nghìn ký tự.'''
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + '…'


def diff_seq(a, b, path, bad):
    if a is None or b is None:
        bad.append((path, 'thiếu một bên'))
        return
    fa, fb = fingerprint(a), fingerprint(b)
    if fa == fb:
        return
    if fa[:len(SHAPE)] != fb[:len(SHAPE)]:
        for k, x, y in zip(SHAPE[1:], fa[1:len(SHAPE)], fb[1:len(SHAPE)]):
            if x != y:
                if k == 'flags':            # cờ code object (generator/async) đổi theo cú pháp
                    bad.append((path, f'flags repo={x} ref={y}'))
                elif k == 'consts':
                    sr = [c for c in x if isinstance(c, str)]
                    sf = [c for c in y if isinstance(c, str)]
                    only = 'repo ' + _brief([c for c in sr if c not in sf]) + \
                           ' | ref ' + _brief([c for c in sf if c not in sr])
                    bad.append((path, 'hằng số chuỗi lệch nhau: ' + only
                                if (len(sr) != len(sf) or set(sr) != set(sf))
                                else f'hình dạng consts: repo={_brief(x)} ref={_brief(y)}'))
                else:
                    bad.append((path, f'hình dạng {k}: repo={_brief(x)} ref={_brief(y)}'))
        return
    ia, ib = fa[-1], fb[-1]
    n = 0
    while n < min(len(ia), len(ib)) and ia[n] == ib[n]:
        n += 1
    if len(ia) != len(ib):
        bad.append((path, f'số lệnh: repo={len(ia)} ref={len(ib)}, phân kỳ từ #{n}: '
                          f'repo {_brief(ia[n:n + 2])} ref {_brief(ib[n:n + 2])}'))
    else:
        bad.append((path, f'lệnh #{n}: repo={_brief(ia[n])} ref={_brief(ib[n])}'))


def compare(src_path, names=None):
    src_path = Path(src_path)
    if not src_path.is_absolute():
        src_path = REPO / src_path
    rel = str(src_path.resolve().relative_to(REPO)).replace('\\', '/')
    dotted = rel[:-3].replace('/', '.')
    # dont_inherit: nếu không, compile() ăn luôn future flags của module ĐANG GỌI
    # (file này có `from __future__ import annotations`) -> mọi file không có dòng đó
    # bị báo lệch CO_FUTURE_ANNOTATIONS giả.
    rep = compile(src_path.read_text(encoding='utf-8'), str(src_path), 'exec', dont_inherit=True)
    ref = load_ref(dotted)
    bad = []
    diff_seq(rep, ref, '<module>', bad)
    ri, fi = index(rep), index(ref)
    for name in sorted(set(ri) | set(fi)):
        if names and name not in names:
            continue
        if len(ri.get(name, [])) != len(fi.get(name, [])):
            bad.append((name, f'số lần xuất hiện repo={len(ri.get(name, []))} '
                              f'ref={len(fi.get(name, []))}'))
            continue
        for k, (a, b) in enumerate(zip(ri.get(name, []), fi.get(name, []))):
            diff_seq(a, b, f'{name}#{k}', bad)
    return dotted, len(ri), bad


def _skip_dir(parts):
    top = parts[1:] if len(parts) > 1 else ()
    return ('__pycache__' in parts) or ('build' in top) or ('dist' in top) \
        or ('tools' in top) or ('tests' in top) or ('output' in top)


def run_all():
    rows = []
    for p in sorted(REPO.rglob('*.py')):
        parts = p.relative_to(REPO).parts
        if _skip_dir(tuple(parts)) or not parts:
            continue
        try:
            dotted, n, bad = compare(p)
        except FileNotFoundError:
            continue
        except Exception as exc:
            rows.append((str(p.relative_to(REPO)).replace('\\', '/'), -1, f'không đọc được: {exc}'[:60]))
            continue
        rows.append((dotted.replace('.', '/') + '.py', len(bad), ''))
    exact = [r for r in rows if r[1] == 0]
    print(f'{len(rows)} module có .pyc đối chiếu | {len(exact)} KHỚP TUYỆT ĐỐI bytecode | '
          f'{len([r for r in rows if r[1] > 0])} còn khác')
    for name, k, note in sorted(rows, key=lambda r: -r[1])[:25]:
        print(f'  {k:6} chỗ khác  {name} {note}')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?')
    ap.add_argument('--names', nargs='*', default=[])
    ap.add_argument('--internal', default=None, help='thư mục _internal của bản đã cài')
    ap.add_argument('--all', action='store_true', help='đo toàn repo')
    args = ap.parse_args()
    if args.internal:
        globals()['INTERNAL'] = Path(args.internal)
    if args.all:
        return run_all()
    if not args.file:
        ap.error('thiếu <file> hoặc --all')
    dotted, n, bad = compare(args.file, args.names)
    if not bad:
        print(f'KHỚP HOÀN HẢO: {args.file} ({n} code object, so với {dotted}.pyc)')
        return 0
    print(f'KHÁC BIỆT: {args.file} ({len(bad)} chỗ)')
    for p, m in bad:
        print(f'  ✗ {p}: {m}')
    return 1


if __name__ == '__main__':
    sys.exit(main())

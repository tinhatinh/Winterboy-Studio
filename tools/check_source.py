# -*- coding: utf-8 -*-
'''Kiểm tra sức khoẻ mã nguồn Winterboy Studio.

Repo này sinh ra từ bytecode (Decompyle++), nên "có vẻ là source" nhưng nhiều file
không phải Python hợp lệ. Tool này cho biết chính xác file nào hỏng và hỏng ở đâu,
chạy lại được sau mỗi lần sửa, dùng làm cổng kiểm trước khi commit.

    python tools/check_source.py              # tóm tắt + danh sách lỗi
    python tools/check_source.py --import     # thử import từng module (subprocess riêng)
    python tools/check_source.py --parity     # so hàm trong .py với .pyc gốc của bản đã build
    python tools/check_source.py --json       # xuất máy đọc được
    python tools/check_source.py --only app/services/ffmpeg_renderer.py

Exit code: 0 = sạch, 1 = còn lỗi.
'''
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_INTERNAL = Path(r"C:\Users\Administrator\MumuStudioPro\{app}\_internal")

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def py_files(only=None):
    out = []
    for p in sorted(REPO.rglob('*.py')):
        if '__pycache__' in p.parts or 'build' in p.parts or 'dist' in p.parts:
            continue
        if only:
            rel = str(p.relative_to(REPO)).replace('\\', '/')
            if not any(rel.startswith(o.replace('\\', '/').lstrip('./')) for o in only):
                continue
        out.append(p)
    return out


def check_syntax(paths):
    '''compile() chứ không chỉ ast.parse(): ast.parse bỏ qua lỗi đặt
    "from __future__" sai chỗ mà vẫn cho qua.'''
    bad = {}
    for p in paths:
        try:
            with warnings.catch_warnings():
                # decompile ra toàn `None(None, None)` -> SyntaxWarning nhiễu, bỏ qua
                warnings.simplefilter('ignore', SyntaxWarning)
                compile(p.read_text(encoding='utf-8'), str(p), 'exec')
        except SyntaxError as exc:
            bad[str(p.relative_to(REPO))] = {'line': exc.lineno, 'msg': exc.msg,
                                             'text': (exc.text or '').strip()[:80]}
        except Exception as exc:                                    # đọc/codec lỗi
            bad[str(p.relative_to(REPO))] = {'line': None, 'msg': repr(exc)[:80], 'text': ''}
    return bad


DAMAGE_PATTERNS = [
    ('gán từ lời gọi None(...)', r'^\s*\w[\w\.\[\]]*\s*=\s*None\('),
    ('gán từ chuỗi rỗng có phương thức', r'^\s*\w[\w\.\[\]]*\s*=\s*\'\'\.(?!join)'),
    ('gán từ None.read/None attribute', r'^\s*\w[\w\.\[\]]*\s*=\s*None\.'),
    ('nhánh if mất vế gán', r'^\s*if not [\w\.]+:\s*$'),
    ('câu chỉ gồm một tên biến', r'^\s{4,}[a-z_][\w\.]*\s*$'),
    ('lambda mất thân (lambda .0)', r'lambda\s+\.\d+:'),
    ('truy cập None[...] ', r'=\s*None\['),
    ('None(...) như câu lệnh', r'^\s*None\('),
    ('gán cho None', r'^\s*None\s*='),
    ('NODE chưa dịch được', r'<NODE:'),
    ('dấu vết "Decompyle incomplete"', r'Decompyle incomplete'),
]
DAMAGE_EXEMPT_IF_NOT_FOLLOWS = {
    'nhánh if mất vế gán': ''.join((
        r'^(return|raise|pass|continue|break|\.\.\.|assert|del|yield|await|async|if|elif',
        r'|else|try|finally|with|for|while|lambda|#)',
        r'|^\w[\w\.\[\]]*(\s*,\s*\w[\w\.\[\]]*)+\s*=',      # a, b = ...
        r'|^\w[\w\.\[\]]*\s*[=:(\[]')),
}
# dòng nối tiếp hợp lệ của một list-comprehension / lời gọi nhiều dòng
CONTINUATION_ENDINGS = ('[', '(', '{', ',', 'in', 'or', 'and', '=', '+', '*', ':', '|', 'not')


def _prev_code_line(lines, n):
    for follow in reversed(lines[:n - 1]):
        if follow.strip() and not follow.strip().startswith('#'):
            return follow.rstrip()
    return ''


def _next_code_line(lines, n):
    for follow in lines[n:]:
        if follow.strip() and not follow.strip().startswith('#'):
            return follow.strip()
    return ''


def damage_scan(paths):
    '''Đánh dấu chỗ mã ĐỌC có vẻ đúng nhưng đã hỏng sau decompile.

    Nguy hiểm hơn lỗi cú pháp: file vẫn import được, chạy được, nhưng trả kết quả
    sai (``text = ''.replace(...)`` làm rỗng chuỗi, ``raw = None.read_text()`` nổ
    AttributeError, ...). Mỗi lần sửa một module phải kéo số này về 0.
    '''
    out = {}
    for p in paths:
        try:
            lines = p.read_text(encoding='utf-8').splitlines()
        except Exception:
            continue
        hits = []
        for n, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            for label, pat in DAMAGE_PATTERNS:
                if not re.match(pat, line if label != 'câu chỉ gồm một tên biến' else line):
                    continue
                if label == 'nhánh if mất vế gán':
                    nxt = _next_code_line(lines, n)
                    if re.match(DAMAGE_EXEMPT_IF_NOT_FOLLOWS[label], nxt or 'x'):
                        continue
                if label == 'câu chỉ gồm một tên biến':
                    if stripped in ('pass', 'continue', 'break', 'return', 'raise'):
                        continue
                    prev = _prev_code_line(lines, n)
                    # phần tử của list-comprehension / argument nhiều dòng thì hợp lệ
                    if not prev or prev.rstrip().endswith(CONTINUATION_ENDINGS):
                        continue
                    if _next_code_line(lines, n).startswith(('for ', 'if ')) \
                            and prev.rstrip().endswith(('[', '(')):
                        continue
                hits.append((n, label, stripped[:70]))
                break
        if hits:
            out[str(p.relative_to(REPO))] = hits
    return out


def count_markers(paths):
    out = {}
    for p in paths:
        try:
            n = p.read_text(encoding='utf-8').count('Decompyle incomplete')
        except Exception:
            n = 0
        if n:
            out[str(p.relative_to(REPO))] = n
    return out


def _py_defs(p):
    try:
        tree = ast.parse(p.read_text(encoding='utf-8'))
    except Exception:
        return None
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _pyc_names(pyc):
    '''Đọc tên hàm từ code object của .pyc mà không cần import (tránh side effect).'''
    import marshal
    data = pyc.read_bytes()
    start = 16 if sys.version_info >= (3, 7) else 12
    try:
        code = marshal.loads(data[start:])
    except Exception:
        return None
    names = set()
    stack = [code]
    while stack:
        c = stack.pop()
        for const in c.co_consts:
            if hasattr(const, 'co_name'):
                names.add(const.co_name)
                stack.append(const)
    names.add(code.co_name)
    names.discard('<module>')
    return names


def check_parity(paths, internal):
    '''Thiếu hàm so với .pyc = bản trong repo không chạy được như bản đã phát hành.'''
    rows = []
    for p in paths:
        try:
            rel = p.relative_to(REPO)
        except ValueError:
            continue
        pyc = internal.joinpath(*rel.parts).with_suffix('.pyc')
        if not pyc.is_file():
            continue
        src, ref = _py_defs(p), _pyc_names(pyc)
        if src is None or ref is None:
            continue
        missing = sorted(ref - src)
        if missing:
            rows.append({'file': str(rel), 'have': len(src & ref), 'missing': len(missing),
                         'names': missing})
    return sorted(rows, key=lambda r: -r['missing'])


def check_imports(paths):
    '''Mỗi module một subprocess: import hỏng không được làm chết cả lượt kiểm.'''
    bad = {}
    for p in paths:
        rel = str(p.relative_to(REPO)).replace('\\', '/')
        if rel.startswith('tools/'):
            continue
        mod = rel[:-3].replace('/', '.')            # bo .py roi cham thanh ten module
        code = ('import importlib,sys;'
                f'importlib.import_module({mod!r});print("OK")')
        try:
            r = subprocess.run([sys.executable, '-c', code], cwd=str(REPO),
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=90)
            if 'OK' not in (r.stdout or ''):
                lines = (r.stderr or '').strip().splitlines()
                err = (lines[-1] if lines else 'không rõ')[:110]
                # thủ phạm thật thường là file khác (gói cha import cả loạt module hỏng)
                culprit = ''
                for ln in reversed(lines):
                    m = re.search(r'File "([^"]+)", line (\d+)', ln)
                    if m and not m.group(1).endswith('<string>'):
                        culprit = f' <- {Path(m.group(1)).name}:{m.group(2)}'
                        break
                bad[mod] = (err + culprit)[:150]
        except subprocess.TimeoutExpired:
            bad[mod] = 'timeout 90s'
        except Exception as exc:
            bad[mod] = repr(exc)[:120]
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kiểm tra mã nguồn repo.')
    ap.add_argument('--import', dest='do_import', action='store_true', help='thử import từng module')
    ap.add_argument('--parity', action='store_true', help='so hàm với .pyc gốc')
    ap.add_argument('--internal', default=str(DEFAULT_INTERNAL), help='đường dẫn _internal bản đã cài')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--only', nargs='*', help='chỉ kiểm mấy đường dẫn này')
    ap.add_argument('--damaged', action='store_true',
                    help='đánh dấu chỗ compile được nhưng đã hỏng sau decompile')
    args = ap.parse_args(argv)

    paths = py_files(args.only)
    syn = check_syntax(paths)
    mark = count_markers(paths)
    report = {'files': len(paths), 'syntax_errors': syn, 'incomplete_markers': mark}
    good = [p for p in paths if str(p.relative_to(REPO)) not in syn]
    if args.damaged:
        report['damaged'] = damage_scan(good)
    if args.parity:
        report['parity'] = check_parity(good, Path(args.internal))
    if args.do_import:
        report['import_errors'] = check_imports(good)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f'{len(paths)} file .py | lỗi cú pháp: {len(syn)} | '
              f'nơi decompile hỏng: {sum(mark.values())}')
        for f, e in sorted(syn.items()):
            print(f"  ✗ {f}:{e['line']}  {e['msg']}   | {e['text']}")
        if args.damaged:
            dm = report['damaged']
            print(f'\n  {sum(len(v) for v in dm.values())} chỗ "hỏng im lặng" '
                  f'(compile vẫn đạt) ở {len(dm)} file:')
            for f, hits in sorted(dm.items(), key=lambda kv: -len(kv[1]))[:20]:
                print(f'    {f:52} {len(hits):3} chỗ  '
                      f'dòng {", ".join(str(h[0]) for h in hits[:6])}')
        if args.parity:
            tot = sum(r['missing'] for r in report['parity'])
            print(f'\n  Thiếu {tot} hàm so với bản đã build, ở {len(report["parity"])} file:')
            for r in report['parity'][:15]:
                print(f"    {r['file']:52} thiếu {r['missing']:3} (có {r['have']})")
        if args.do_import:
            ie = report['import_errors']
            print(f'\n  Import lỗi: {len(ie)}')
            for m, e in sorted(ie.items()):
                print(f'    {m:52} {e}')
    ok = not syn and not report.get('import_errors')
    if args.parity and report.get('parity'):
        ok = ok and not any(r['missing'] for r in report['parity'] if r['have'])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

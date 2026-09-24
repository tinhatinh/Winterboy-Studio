# -*- coding: utf-8 -*-
'''In báo cáo trạng thái khôi phục mã nguồn, ghi ra docs/RESTORE_STATUS.md.

Mục đích: để người dùng biết chính xác còn những file nào chưa dịch ngược xong,
theo ba mức độ nguy hiểm khác nhau — không phải một con số "còn lỗi" chung chung.

    python tools/restore_status.py            # in ra màn hình
    python tools/restore_status.py --write    # ghi luôn vào docs/RESTORE_STATUS.md
'''
from __future__ import annotations

import argparse
import ast
import marshal
import sys
import time
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERNAL = Path(r'C:\Users\Administrator\MumuStudioPro\{app}\_internal')
sys.path.insert(0, str(REPO / 'tools'))
warnings.simplefilter('ignore', SyntaxWarning)

import check_source as cs                                       # noqa: E402
import compare_bytecode as cb                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def pyc_callables(pyc: Path):
    try:
        code = marshal.loads(pyc.read_bytes()[16:])
    except Exception:
        return None
    out = set()
    stack = [code]
    while stack:
        c = stack.pop()
        for k in c.co_consts:
            if hasattr(k, 'co_name'):
                out.add(k.co_name)
                stack.append(k)
    out.discard('<module>')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='ghi ra docs/RESTORE_STATUS.md')
    args = ap.parse_args()

    paths = [p for p in sorted(REPO.rglob('*.py'))
             if '__pycache__' not in p.parts and 'build' not in p.parts
             and 'dist' not in p.parts and p.relative_to(REPO).parts[0]
             not in ('tools', 'tests')]
    syn = cs.check_syntax(paths)
    dmg = cs.damage_scan([p for p in paths if str(p.relative_to(REPO)) not in syn])
    marks = cs.count_markers(paths)

    tier_a, tier_b, tier_c, done = [], [], [], []
    for p in paths:
        rel = str(p.relative_to(REPO)).replace('\\', '/')
        pyc = INTERNAL.joinpath(*p.relative_to(REPO).parts).with_suffix('.pyc')
        if not pyc.is_file():
            continue
        if rel in syn:
            tier_c.append((rel, syn[rel]['line'], syn[rel]['msg']))
            continue
        try:
            _d, _n, bad = cb.compare(p)
        except Exception as exc:
            tier_c.append((rel, '?', f'không đọc được: {exc}'))
            continue
        if not bad:
            done.append(rel)
            continue
        src = {n.name for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        ref = pyc_callables(pyc) or set()
        missing = len(ref - src)
        hits = len(dmg.get(rel, []))
        row = (rel, len(bad), missing, hits)
        if missing or hits:
            tier_b.append(row)
        else:
            tier_a.append(row)

    lines = []
    add = lines.append
    add('# Trạng thái khôi phục mã nguồn')
    add('')
    add(f'Cập nhật: {time.strftime("%Y-%m-%d %H:%M")} — sinh tự động bằng '
        f'`python tools/restore_status.py --write`, đừng sửa tay.')
    add('')
    add('Bốn mức, xếp theo mức độ tin dùng được của file:')
    add('')
    add(f'- **A. Khớp bytecode 100%** với bản đã phát hành → dùng y hệt: **{len(done)} file**')
    add(f'- **B. Parse được nhưng còn thiếu hàm / còn "hỏng im lặng"** → ĐỪNG tin: '
        f'**{len(tier_b)} file**')
    add(f'- **C. Parse được, đủ hàm, chỉ lệch cách viết** → cần đối chiếu thêm: '
        f'**{len(tier_a)} file**')
    add(f'- **D. Chưa phải Python hợp lệ** → không chạy được: **{len(tier_c)} file**')
    add('')
    add('Mức B là nguy hiểm nhất: file import bình thường, chạy bình thường, nhưng có '
        'hàm thân đã mất hoặc dịch ra mã sai (kiểu `text = \'\'.replace(...)` làm rỗng '
        'chuỗi). Bộ test `tests/` chỉ phủ được các file đã khôi phục có chủ đích.')
    add('')

    if tier_c:
        add(f'## D. Chưa parse được ({len(tier_c)})')
        add('')
        add('| file | dòng | lỗi |')
        add('|---|---|---|')
        for rel, ln, msg in sorted(tier_c):
            add(f'| `{rel}` | {ln} | {str(msg)[:60]} |')
        add('')
    if tier_b:
        add(f'## B. Parse được nhưng còn thiếu hàm hoặc hỏng im lặng ({len(tier_b)})')
        add('')
        add('| file | lệch bytecode | hàm thiếu | hỏng im lặng |')
        add('|---|---|---|---|')
        for rel, bad, missing, hits in sorted(tier_b, key=lambda r: -(r[2] + r[3])):
            add(f'| `{rel}` | {bad} | {missing} | {hits} |')
        add('')
    if tier_a:
        add(f'## C. Đủ hàm, lệch cách viết ({len(tier_a)})')
        add('')
        add('| file | lệch bytecode |')
        add('|---|---|')
        for rel, bad, _m, _h in sorted(tier_a, key=lambda r: r[1]):
            add(f'| `{rel}` | {bad} |')
        add('')
    add(f'## A. Đã khớp tuyệt đối ({len(done)})')
    add('')
    for rel in sorted(done):
        add(f'- `{rel}`')
    add('')
    add('Kiểm chứng lại: `python tools/compare_bytecode.py --all` và `python tests/run_tests.py`.')

    text = '\n'.join(lines) + '\n'
    if args.write:
        out = REPO / 'docs' / 'RESTORE_STATUS.md'
        out.parent.mkdir(exist_ok=True)
        out.write_text(text, encoding='utf-8')
        print(f'đã ghi {out.relative_to(REPO)}')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())

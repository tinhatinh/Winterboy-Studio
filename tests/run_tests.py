# -*- coding: utf-8 -*-
'''Chạy bộ test mà không cần cài pytest.

    python tests/run_tests.py                # chạy hết
    python tests/run_tests.py srt_utils      # chỉ file khớp tên
    python tests/run_tests.py --serial       # gộp chung một tiến trình (nhanh hơn, dễ nhiễu)

Mỗi file test chạy ở MỘT TIẾN TRÌNH RIÊNG. Lý do: mấy test đối chiếu phải giả lập
package cha (đăng ký ``sys.modules['app.services']`` trỏ vào bản đã cài) để nạp được
module đơn lẻ — làm vậy thì污染 các file chạy sau nếu chung tiến trình.
'''
from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')

MARKER = '@@RESULT@@'


def load(path):
    spec = importlib.util.spec_from_file_location(f'tests_{path.stem}', path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f'tests_{path.stem}'] = mod
    spec.loader.exec_module(mod)
    return mod


def run_in_process(files):
    '''Chạy thẳng trong tiến trình hiện tại, trả (passed, failed, skipped).'''
    from _parity import RefMissing
    passed = failed = skipped = 0
    for path in files:
        print(f'\n=== {path.name} ===')
        try:
            mod = load(path)
        except RefMissing as exc:
            print(f'  SKIP: {exc}')
            skipped += 1
            continue
        except BaseException:
            print('  FAIL (không nạp được module):')
            print(indent(traceback.format_exc()))
            failed += 1
            continue
        for name in sorted(dir(mod)):
            if not name.startswith('test_'):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            try:
                fn()
                print(f'  PASS  {name}')
                passed += 1
            except RefMissing as exc:
                print(f'  SKIP  {name}: {exc}')
                skipped += 1
            except SystemExit as exc:
                print(f'  FAIL  {name}: SystemExit({exc.code}) — test gọi sys.exit, '
                      f'phải chạy trong subprocess')
                failed += 1
            except BaseException:
                print(f'  FAIL  {name}')
                print(indent(traceback.format_exc()))
                failed += 1
    return passed, failed, skipped


def run_isolated(files):
    '''Mỗi file một tiến trình. Cha chỉ gom kết quả và in lại.'''
    total = [0, 0, 0]
    for path in files:
        print(f'\n=== {path.name} ===', flush=True)
        t0 = time.time()
        proc = subprocess.run([sys.executable, str(HERE / 'run_tests.py'),
                               '--one', str(path), '--quiet'],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=900)
        out = (proc.stdout or '') + (proc.stderr or '')
        counts = None
        for line in out.splitlines():
            if line.startswith(MARKER):
                p, f, s = line[len(MARKER):].split()
                counts = (int(p), int(f), int(s))
            elif not line.startswith('==='):
                print(line)
        if counts is None:
            print('  FAIL  (tiến trình con chết trước khi báo kết quả)')
            print(indent(out[-2000:]))
            counts = (0, 1, 0)
        p, f, s = counts
        total[0] += p
        total[1] += f
        total[2] += s
        note = f'  ({time.time() - t0:.1f}s)' if f == 0 else note_slow(p, f, s, time.time() - t0)
        print(f'  -> {p} pass / {f} fail / {s} skip{note}', flush=True)
    return tuple(total)


def note_slow(p, f, s, dt):
    return f'  ⚠ {f} FAIL, {s} skip, {dt:.1f}s'


def indent(text, pad='      '):
    return '\n'.join(pad + l for l in text.strip().splitlines())


def main(argv):
    argv = list(argv)
    if '--one' in argv:
        i = argv.index('--one')
        path = Path(argv[i + 1])
        quiet = '--quiet' in argv
        p, f, s = run_in_process([path])
        print(f'{MARKER} {p} {f} {s}')
        if not quiet:
            print(f'{p} pass | {f} fail | {s} skip')
        return 1 if f else 0

    serial = '--serial' in argv
    args = [a for a in argv if a not in ('--serial', '--quiet')]
    files = sorted(HERE.glob('test_*.py'))
    if args:
        files = [x for x in files if any(a in x.name for a in args)]
    if not files:
        print('không có test nào khớp')
        return 1
    t0 = time.time()
    print(f'{len(files)} file test | {"chung tiến trình" if serial else "mỗi file một tiến trình"}')
    passed, failed, skipped = (run_in_process(files) if serial else run_isolated(files))
    print(f'\n{passed} pass | {failed} fail | {skipped} skip  ({time.time() - t0:.1f}s)')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

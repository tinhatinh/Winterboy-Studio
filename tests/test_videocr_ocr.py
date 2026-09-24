# -*- coding: utf-8 -*-
'''Test app.services.videocr_ocr — KHÔNG gọi VideOCR thật.

Hai bẫy đã gặp khi viết file này, ghi lại để sau đừng lặp:
1. On Windows, Popen([script.py, ...]) nổ WinError 193 — CLI giả phải là .bat gọi
   python, vì videocr-cli thật cũng là một executable.
2. Máy dev có VideOCR cài sẵn, nên test "không tìm thấy CLI" sẽ âm thầm tìm ra bản
   thật và chạy OCR thật. Mọi test phải cô lập SEARCH_DIRS/env trước đã.
'''
from __future__ import annotations

import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.services import videocr_ocr as vo                      # noqa: E402
from app.services.videocr_ocr import (                          # noqa: E402
    OcrOptions, build_command, find_videocr_cli, parse_progress, run_ocr)

SCRATCH = REPO / 'output' / '_restore' / 'videocr'
ENV_KEYS = ('WINTERBOY_VIDEOCR', 'VIDEOOCR_CLI', 'VIDEOOCR_HOME')

FAKE_BODY = '''
import argparse, pathlib, sys
p = argparse.ArgumentParser()
for f in ('--video_path', '--output', '--lang', '--use_gpu', '--min_subtitle_duration',
          '--conf_threshold', '--sim_threshold', '--max_merge_gap', '--frames_to_skip',
          '--time_start', '--time_end', '--crop_x', '--crop_y', '--crop_width',
          '--crop_height', '--ssim_threshold'):
    p.add_argument(f)
a, _ = p.parse_known_args()
for i in (1, 2):
    print(f'Step 1/2: Processing video... Current: 00:00:0{i} / 00:00:02, Frame: {i*30}', flush=True)
for i in range(1, 5):
    print(f'Step 2/2: Performing OCR on image {i} of 4', flush=True)
print('Generating subtitles...', flush=True)
pathlib.Path(a.output).write_text(
    "1\\n00:00:00,000 --> 00:00:02,258\\nA\\n\\n2\\n00:00:02,258 --> 00:00:04,000\\nB\\n",
    encoding='utf-8')
'''


def _isolate(tmp_name='nowhere'):
    '''Chặn mọi đường tìm CLI thật; trả về (SEARCH_DIRS cũ, env cũ) để restore.'''
    old_dirs, old_env = vo.SEARCH_DIRS, {}
    vo.SEARCH_DIRS = (SCRATCH / tmp_name,)
    for k in ENV_KEYS:
        old_env[k] = __import__('os').environ.pop(k, None)
    import shutil
    old_which = vo.shutil.which
    vo.shutil.which = lambda name: None
    return (old_dirs, old_env, old_which)


def _restore(state):
    import os
    old_dirs, old_env, old_which = state
    vo.SEARCH_DIRS = old_dirs
    vo.shutil.which = old_which
    for k, v in old_env.items():
        if v is not None:
            os.environ[k] = v


def _scratch(name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / name
    p.unlink(missing_ok=True)
    return p


def _fake_cli(body=FAKE_BODY, name='fake_ok'):
    '''Trả về đường dẫn .bat (executable thật sự trên Windows) gọi script python.'''
    script = _scratch(name + '.py')
    script.write_text(body, encoding='utf-8')
    bat = _scratch(name + '.bat')
    bat.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding='utf-8')
    return bat


def _video(name='clip.mp4'):
    v = _scratch(name)
    v.write_bytes(b'\x00' * 64)
    return v


# ---------------------------------------------------------------- cô lập môi trường
def test_isolation_actually_blocks_real_cli():
    state = _isolate()
    try:
        assert find_videocr_cli() is None, 'vẫn tìm thấy CLI thật -> test sẽ gọi OCR thật!'
    finally:
        _restore(state)


def test_find_cli_prefers_explicit():
    p = _scratch('videocr-cli.exe')
    p.write_bytes(b'')
    assert find_videocr_cli(p) == p.resolve()


def test_find_cli_from_env_pointing_at_directory():
    import os
    d = SCRATCH / 'envdir'
    d.mkdir(parents=True, exist_ok=True)
    exe = d / 'videocr-cli.exe'
    exe.write_bytes(b'')
    state = _isolate()
    os.environ['WINTERBOY_VIDEOCR'] = str(d)
    try:
        assert find_videocr_cli() == exe.resolve()
    finally:
        _restore(state)


# ---------------------------------------------------------------- build_command
def test_build_command_defaults():
    cmd = build_command(r'C:\VideOCR\videocr-cli.exe', 'v.mp4', 'out.srt')
    assert cmd[0] == r'C:\VideOCR\videocr-cli.exe'
    assert cmd[1:3] == ['--video_path', 'v.mp4'] and cmd[3:5] == ['--output', 'out.srt']
    assert cmd[cmd.index('--lang') + 1] == 'ch'
    assert cmd[cmd.index('--use_gpu') + 1] == 'true'
    assert cmd[cmd.index('--min_subtitle_duration') + 1] == '0.3'


def test_build_command_gpu_off_and_floats():
    cmd = build_command('cli.exe', 'v', 'o',
                        OcrOptions(lang='vi', use_gpu=False, min_subtitle_duration=0.5,
                                   conf_threshold=0.82))
    assert cmd[cmd.index('--lang') + 1] == 'vi'
    assert cmd[cmd.index('--use_gpu') + 1] == 'false'
    assert cmd[cmd.index('--conf_threshold') + 1] == '0.82'
    assert '--sim_threshold' not in cmd


def test_build_command_crop_and_extra():
    cmd = build_command('cli', 'v', 'o', OcrOptions(crop=(0, 928, 1920, 152),
                                                    extra={'ssim_threshold': 0.98}))
    for flag, val in (('--crop_x', '0'), ('--crop_y', '928'), ('--crop_width', '1920'),
                      ('--crop_height', '152'), ('--ssim_threshold', '0.98')):
        assert cmd[cmd.index(flag) + 1] == val, flag


def test_build_command_distinguishes_none_from_zero():
    cmd = build_command('cli', 'v', 'o', OcrOptions(time_start=None, time_end='120.5',
                                                    frames_to_skip=0,
                                                    min_subtitle_duration=None))
    assert '--time_start' not in cmd and '--min_subtitle_duration' not in cmd
    assert cmd[cmd.index('--time_end') + 1] == '120.5'
    assert cmd[cmd.index('--frames_to_skip') + 1] == '0'


# ---------------------------------------------------------------- parse_progress
def test_parse_progress_known_lines():
    stage, frac, label = parse_progress('Step 1/2: Processing video... Current: 00:01:30 / 00:03:00, Frame: 900')
    assert stage == 'scan' and abs(frac - 0.15) < 1e-9 and '00:01:30' in label
    stage, frac, label = parse_progress('Step 2/2: Performing OCR on image 829 of 1658')
    assert stage == 'ocr' and abs(frac - (0.3 + 0.7 * 829 / 1658)) < 1e-9
    assert label.startswith('OCR ảnh 829')
    assert parse_progress('Generating subtitles...')[0] == 'write'


def test_parse_progress_is_monotonic_across_stages():
    a = parse_progress('Step 1/2: Processing video... Current: 00:02:30 / 00:02:30, Frame: 1')[1]
    b = parse_progress('Step 2/2: Performing OCR on image 1 of 100')[1]
    c = parse_progress('Step 2/2: Performing OCR on image 100 of 100')[1]
    assert a <= b <= c <= 1.0, (a, b, c)


def test_parse_progress_ignores_noise():
    for line in ('', '   ', 'Creating output directory...', 'Some Paddle warning'):
        assert parse_progress(line) is None, line
    zero = parse_progress('Step 2/2: Performing OCR on image 0 of 0')
    assert zero is None or zero[1] <= 0.31, zero       # chia 0 không được nổ


# ---------------------------------------------------------------- run_ocr
def test_run_ocr_missing_video():
    r = run_ocr(_scratch('khong-co.mp4'), _scratch('o.srt'), cli=_fake_cli())
    assert not r.ok and 'Không thấy video' in r.error


def test_run_ocr_reports_missing_cli():
    state = _isolate()
    try:
        r = run_ocr(_video(), _scratch('o.srt'))
        assert not r.ok and 'videocr-cli' in r.error
    finally:
        _restore(state)


def test_run_ocr_happy_path():
    out = _scratch('ok.srt')
    seen = []
    r = run_ocr(_video(), out, cli=_fake_cli(), progress=lambda f, l: seen.append((f, l)))
    assert r.ok, r.error
    assert r.n_cues == 2 and abs(r.duration_s - 4.0) < 1e-6
    assert [c.text for c in r.cues] == ['A', 'B']
    assert [c.index for c in r.cues] == [0, 1]
    assert seen and abs(seen[-1][0] - 1.0) < 1e-9
    assert any('OCR ảnh 4/4' in s[1] for s in seen)
    assert out.is_file()


def test_run_ocr_nonzero_exit_keeps_tail():
    cli = _fake_cli('import sys\nprint("boom: model not found", flush=True)\nsys.exit(3)\n',
                    'bad_exit')
    r = run_ocr(_video('c2.mp4'), _scratch('e1.srt'), cli=cli)
    assert not r.ok and 'mã lỗi 3' in r.error and 'boom' in r.error


def test_run_ocr_no_output_file():
    cli = _fake_cli('print("done", flush=True)\n', 'silent')
    r = run_ocr(_video('c3.mp4'), _scratch('never.srt'), cli=cli)
    assert not r.ok and 'không có file SRT' in r.error


def test_run_ocr_empty_srt_is_not_success():
    cli = _fake_cli('import argparse, pathlib\n'
                    'p=argparse.ArgumentParser();p.add_argument("--output")\n'
                    'a,_=p.parse_known_args()\n'
                    'pathlib.Path(a.output).write_text("", encoding="utf-8")\n', 'empty')
    r = run_ocr(_video('c4.mp4'), _scratch('empty.srt'), cli=cli)
    assert not r.ok and 'rỗng' in r.error


def test_run_ocr_cancel():
    cli = _fake_cli('import time\nprint("start", flush=True)\ntime.sleep(30)\n', 'slow')
    ev = threading.Event()
    threading.Timer(1.0, ev.set).start()
    r = run_ocr(_video('c5.mp4'), _scratch('cancel.srt'), cli=cli, cancel_event=ev)
    assert not r.ok and 'dừng' in r.error.lower()


def test_run_ocr_timeout():
    cli = _fake_cli('import time\nprint("x", flush=True)\ntime.sleep(30)\n', 'slow2')
    r = run_ocr(_video('c6.mp4'), _scratch('to.srt'), cli=cli, timeout_s=2.0)
    assert not r.ok and 'quá thời gian' in r.error

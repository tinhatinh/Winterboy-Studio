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
    OcrOptions, build_command, crop_from_drag, find_videocr_cli, parse_progress, run_ocr)

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
    # 120.5 đã được đổi sang dạng VideOCR thật sự nhận (xem test_build_command_normalizes_time_flags)
    assert cmd[cmd.index('--time_end') + 1] == '00:02:01'
    assert cmd[cmd.index('--frames_to_skip') + 1] == '0'


# ---------------------------------------------------------------- crop_from_drag
# Video dọc 1080x1920, ảnh preview hiển thị 216x384 -> đúng hệ số 5 lần thu.
SRC = (1080, 1920)
SHOWN = (216, 384)


def test_crop_drag_full_image_is_the_whole_frame():
    assert crop_from_drag(0, 0, 216, 384, shown = SHOWN, source = SRC) == (0, 0, 1080, 1920)


def test_crop_drag_scales_to_source_pixels():
    '''Dải phụ đề cuối khung 1080x1920 ở y=1600 cao 200px -> phải ra đúng số đó.'''
    got = crop_from_drag(0, 1600 / 5, 1080 / 5, 1800 / 5, shown = SHOWN, source = SRC)
    assert got == (0, 1600, 1080, 200), got


def test_crop_drag_accepts_reversed_direction():
    '''Kéo ngược (phải-dưới -> trái-trên) vẫn phải ra w/h dương.'''
    forward = crop_from_drag(20, 40, 120, 90, shown = SHOWN, source = SRC)
    backward = crop_from_drag(120, 90, 20, 40, shown = SHOWN, source = SRC)
    assert forward == backward and forward is not None
    x, y, w, h = forward
    assert w > 0 and h > 0


def test_crop_drag_clamps_outside_the_canvas():
    '''Chuột hay trượt ra ngoài mép ảnh thì vùng cũng không được vượt khung hình.'''
    x, y, w, h = crop_from_drag(-30, -30, 9999, 9999, shown = SHOWN, source = SRC)
    assert (x, y, w, h) == (0, 0, 1080, 1920)


def test_crop_drag_rejects_dot_and_missing_metrics():
    assert crop_from_drag(10, 10, 11, 11, shown = SHOWN, source = SRC) is None   # 1px trên canvas
    assert crop_from_drag(0, 0, 10, 10, shown = (0, 0), source = SRC) is None    # chưa có ảnh
    assert crop_from_drag(0, 0, 10, 10, shown = SHOWN, source = (0, 0)) is None  # chưa probe
    assert crop_from_drag(0, 0, 10, 10, shown = SHOWN, source = None) is None


def test_crop_drag_then_command_is_consistent():
    '''Chuỗi đầu ra phải khớp lệnh VideOCR thật đã dùng khi làm video Newton.'''
    crop = crop_from_drag(0, 320, 216, 360, shown = SHOWN, source = SRC)
    cmd = build_command('videocr-cli.exe', 'v.mp4', 'out.srt', OcrOptions(crop = crop))
    assert cmd[cmd.index('--crop_y') + 1] == '1600', crop
    assert cmd[cmd.index('--crop_height') + 1] == '200', crop
    assert '--crop_x' in cmd and '--crop_width' in cmd
    assert '--crop_x' not in build_command('c', 'v', 'o', OcrOptions())


# ---------------------------------------------------------------- normalize_time
def test_normalize_time_accepts_everything_a_user_would_type():
    '''VideOCR chỉ nhận MM:SS / HH:MM:SS, nên phải tự đổi các kiểu hay bị gõ ra.'''
    from app.services.videocr_ocr import normalize_time as nt

    assert nt(0) == '00:00:00'
    assert nt('0') == '00:00:00'
    assert nt('75') == '00:01:15'
    assert nt(75.5) == '00:01:16'          # làm tròn tới giây vì engine không nhận phẩy
    assert nt('120.5') == '00:02:01'       # round() thường cho 120 (banker's) - ở đây luôn nửa-up
    assert nt('130.5') == '00:02:11'
    assert nt('1:15') == '00:01:15'
    assert nt('00:01:15') == '00:01:15'
    assert nt(' 02:05:09 ') == '02:05:09'
    assert nt('90:00') == '01:30:00'       # phút tràn vẫn ra giờ đúng
    assert nt(None) is None and nt('') is None and nt('   ') is None
    assert nt(-5) == '00:00:00'


def test_normalize_time_leaves_nonsense_to_the_engine():
    from app.services.videocr_ocr import normalize_time as nt

    assert nt('abc') == 'abc'
    assert nt('1:2:3:4') == '1:2:3:4'
    assert nt('1::2') == '1::2'


def test_build_command_normalizes_time_flags():
    cmd = build_command('cli', 'v', 'o', OcrOptions(time_start=0, time_end='20'))
    assert cmd[cmd.index('--time_start') + 1] == '00:00:00', cmd
    assert cmd[cmd.index('--time_end') + 1] == '00:00:20', cmd


# ---------------------------------------------------------------- ngôn ngữ OCR
# Bảng này ĐO bằng cách gọi thật videocr-cli.exe --lang <x> trên clip 1 giây rồi
# xem nó có ném "Unsupported OCR language code" không (VideOCR bản đang cài).
LANG_OK = ('ch', 'chinese_cht', 'en', 'vi', 'japan', 'korean', 'th', 'id', 'ar', 'ru',
           'de', 'fr', 'es', 'pt', 'it', 'ta', 'te', 'ka', 'tr', 'fa', 'pl', 'nl', 'sv',
           'uk', 'hi', 'ms', 'tl', 'sw', 'ro', 'el', 'hu', 'cs', 'da', 'fi', 'no')
LANG_BAD = ('zh', 'ja', 'ko', 'jp', 'cht', 'arab', 'latin', 'cyrillic',
            'devanagari', 'urdu', 'he', 'chinese', 'ch en', 'ch,en', 'en,ch')


def test_resolve_lang_nhan_ca_ma_lan_nhan():
    from app.services.videocr_ocr import resolve_lang

    assert resolve_lang('ch') == 'ch'
    assert resolve_lang('Chinese & English') == 'ch'
    assert resolve_lang('  CHINESE & ENGLISH  ') == 'ch'      # hoa thường + thừa cách
    assert resolve_lang('japan') == 'japan'
    assert resolve_lang('Japanese') == 'japan'
    assert resolve_lang('Vietnamese') == 'vi'


def test_resolve_lang_bac_ma_khong_ton_tai():
    ''''zh' là cái bẫy: ai cũng gõ 'zh' nhưng VideOCR chỉ nhận 'ch'.

    Lưu ý 'hindi' không nằm ở đây: làm MÃ thì CLI từ chối, nhưng làm NHÃN thì hợp
    lệ vì bảng mình map 'Hindi' -> 'hi'.
    '''
    from app.services.videocr_ocr import resolve_lang

    for bad in LANG_BAD:
        assert resolve_lang(bad) is None, bad
    assert resolve_lang(None) is None and resolve_lang('') is None and resolve_lang('  ') is None


def test_bang_ngon_ngu_dung_duoc_va_khong_trung():
    from app.services.videocr_ocr import (DEFAULT_LANG, OCR_LANGUAGES, language_codes,
                                          language_labels, label_for)

    codes, labels = language_codes(), language_labels()
    assert len(set(codes)) == len(codes) == len(OCR_LANGUAGES)
    assert len(set(labels)) == len(labels)
    assert DEFAULT_LANG in codes
    assert label_for('ch') == 'Chinese & English'
    assert set(LANG_OK) == set(codes), (set(LANG_OK) - set(codes), set(codes) - set(LANG_OK))
    # nhãn phải là tên đầy đủ, không phải mã 2 chữ cái người dùng nhìn không ra
    assert all(len(l) > 3 and ' ' not in l[:2] for l in labels), labels


def test_build_command_gui_nhan_ma_khi_dua_nhan():
    cmd = build_command('cli', 'v', 'o', OcrOptions(lang='Chinese & English'))
    assert cmd[cmd.index('--lang') + 1] == 'ch', cmd
    cmd = build_command('cli', 'v', 'o', OcrOptions(lang='Korean'))
    assert cmd[cmd.index('--lang') + 1] == 'korean', cmd


def test_run_ocr_chong_ngon_ngu_sai_truoc_khi_spawn():
    '''Lỗi ngôn ngữ phải trả lời ngắn gọn, không để VideOCR dump cả bảng --help.'''
    state = _isolate()
    try:
        r = run_ocr(_video(), _scratch('badlang.srt'), cli=_fake_cli(),
                    opts=OcrOptions(lang='zh'))
        assert not r.ok and r.error
        assert "'zh'" in r.error and 'chinese_cht' in r.error
        assert not (SCRATCH / 'badlang.srt').is_file(), 'vẫn spawn engine dù ngôn ngữ sai'
    finally:
        _restore(state)


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


def test_run_ocr_resolves_relative_paths():
    '''Đường dẫn tương đối phải được phân giải TRƯỚC khi spawn VideOCR.

    Popen chạy với cwd = thư mục cài VideOCR, nên đưa `output/x.srt` vào là engine
    ghi file ở chỗ khác, còn code đi kiểm tra thì nhìn chỗ cũ -> "chạy xong nhưng
    không có file SRT". Lỗi này chỉ lộ khi gọi từ CLI, UI luôn đưa đường dẫn tuyệt
    đối nên không thấy gì.
    '''
    out = _scratch('rel.srt')
    rel = out.relative_to(REPO)
    assert not rel.is_absolute()
    r = run_ocr(_video(), rel, cli=_fake_cli())
    assert r.ok, r.error
    assert out.is_file(), 'file nằm ở chỗ khác chỗ đã báo'
    assert r.srt_path == out.resolve()


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

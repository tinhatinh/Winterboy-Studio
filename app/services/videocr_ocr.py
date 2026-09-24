# -*- coding: utf-8 -*-
'''Chạy VideOCR (PaddleOCR) để lấy phụ đề cứng trên video thành SRT.

Lý do có module này: nhận diện giọng nói (ASR) trên video Douyin hay nghe sai tên
riêng và thuật ngữ — 伯努利 thành 佛努力, 微积分之父 thành 微积分支付 — nên dịch ra
sai bét mà không phát hiện được. OCR thì đọc đúng nguyên văn chữ đang hiện trên
hình, kèm dấu câu, và cho mốc thời gian theo từng dòng hiển thị.

Engine là binary ngoài (``C:\\Program Files\\VideOCR\\videocr-cli.exe``), module này
chỉ lo: tìm binary, dựng lệnh, chạy, đọc tiến trình, bắt lỗi, và parse SRT đầu ra
bằng ``app.services.srt_utils`` (nên cùng một kiểu cue với phần còn lại của app).

Không có tham số nào của VideOCR được "đoán": tất cả lấy từ ``videocr-cli.exe --help``.
'''
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.services.srt_utils import SrtCue, load_srt

logger = logging.getLogger(__name__)

DEFAULT_LANG = 'ch'
MIN_VERSION_HINT = 'videocr-cli.exe'
SEARCH_DIRS = (
    Path(r'C:\Program Files\VideOCR'),
    Path(r'C:\Program Files (x86)\VideOCR'),
    Path(os.environ.get('LOCALAPPDATA', str(Path.home))) / 'Programs' / 'VideOCR',
)
ENV_KEYS = ('WINTERBOY_VIDEOCR', 'VIDEOOCR_CLI', 'VIDEOOCR_HOME')

# dòng tiến trình thật của VideOCR, lấy nguyên văn từ log mẫu
_RE_STEP1 = re.compile(r'Step\s+1/2:.*Current:\s*(\d+):(\d+):(\d+)\s*/\s*(\d+):(\d+):(\d+)', re.I)
_RE_STEP2 = re.compile(r'Step\s+2/2:.*image\s+(\d+)\s+of\s+(\d+)', re.I)
_RE_DONE = re.compile(r'Generating subtitles|Subtitles? (saved|written|generated)', re.I)


@dataclass
class OcrOptions:
    '''Cờ truyền cho videocr-cli. Mặc định lấy theo cấu hình đã kiểm chứng thực tế.'''
    lang: str = DEFAULT_LANG
    use_gpu: bool = True
    min_subtitle_duration: float = 0.3
    conf_threshold: float | None = None
    sim_threshold: float | None = None
    max_merge_gap: float | None = None
    frames_to_skip: int | None = None
    time_start: str | None = None
    time_end: str | None = None
    crop: tuple[int, int, int, int] | None = None      # x, y, w, h -> --crop_x/y/width/height
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OcrResult:
    ok: bool
    srt_path: Path | None = None
    cues: list[SrtCue] = field(default_factory=list)
    duration_s: float = 0.0
    error: str | None = None
    log_tail: list[str] = field(default_factory=list)

    @property
    def n_cues(self) -> int:
        return len(self.cues)


def crop_from_drag(x0: float, y0: float, x1: float, y1: float, *,
                   shown: 'tuple[int, int]', source: 'tuple[int, int]',
                   min_edge: int = 8) -> 'tuple[int, int, int, int] | None':
    '''Biến hình chữ nhật người dùng kéo trên ảnh preview thành crop cho VideOCR.

    Ảnh preview luôn nhỏ hơn video thật, nên toạ độ phải đổi sang pixel GỐC —
    ``--crop_x/y/width/height`` của VideOCR tính theo khung hình gốc. Trả về None
    khi thiếu số đo hoặc khi người dùng chỉ click nhầm (bé hơn ``min_edge``), để
    UI phân biệt "không chọn vùng" với "chọn sai".
    '''
    sw, sh = (int(source[0]), int(source[1])) if source and len(source) >= 2 else (0, 0)
    dw, dh = (int(shown[0]), int(shown[1])) if shown and len(shown) >= 2 else (0, 0)
    if not (dw and dh and sw and sh):
        return None

    def span(a, b, limit, total):
        lo, hi = sorted((float(a), float(b)))
        lo = min(max(lo, 0.0), limit)
        hi = min(max(hi, 0.0), limit)
        return int(round(lo * total / limit)), int(round(hi * total / limit))

    ax, bx = span(x0, x1, dw, sw)
    ay, by = span(y0, y1, dh, sh)
    if bx - ax < min_edge or by - ay < min_edge:
        return None
    return (ax, ay, bx - ax, by - ay)


def find_videocr_cli(explicit: 'str | Path | None' = None) -> 'Path | None':
    '''Tìm videocr-cli.exe: chỉ định > biến môi trường > thư mục cài đặt > PATH.'''
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    for key in ENV_KEYS:
        value = os.environ.get(key)
        if value:
            p = Path(value)
            candidates.append(p if p.suffix else p / MIN_VERSION_HINT)
    for d in SEARCH_DIRS:
        candidates.append(d / MIN_VERSION_HINT)
    on_path = shutil.which('videocr-cli') or shutil.which(MIN_VERSION_HINT)
    if on_path:
        candidates.append(Path(on_path))

    for cand in candidates:
        try:
            if cand.is_file():
                return cand.resolve()
        except OSError:
            continue
    return None


def normalize_time(value: 'str | float | int | None') -> 'str | None':
    '''Về dạng HH:MM:SS mà VideOCR chấp nhận.

    ``--time_start`` của engine chỉ nhận MM:SS hoặc HH:MM:SS — truyền ``0`` hay
    ``75`` (rất tự nhiên khi muốn cắt theo giây) thì argparse của nó báo lỗi nguyên
    văn cả bảng help, người dùng không hiểu gì. Ở đây nhận hết: ``75``, ``75.5``,
    ``1:15``, ``00:01:15`` -> ``00:01:15``.
    '''
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if ':' in text:
        parts = [p.strip() for p in text.split(':')]
        if not all(re.fullmatch(r'\d+(\.\d+)?', p) for p in parts) or len(parts) > 3:
            return text                                  # để engine tự báo lỗi, không đoán
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
    else:
        if not re.fullmatch(r'-?\d+(\.\d+)?', text):
            return text
        seconds = float(text)
    seconds = max(0.0, seconds)
    # round() của Python là banker's rounding (120.5 -> 120, 130.5 -> 130) nên tự làm
    # tròn lên nửa đơn vị: người gõ "90.5" phải luôn nhận 00:01:31, không phụ thuộc
    # chẵn lẻ của giây.
    h, rem = divmod(int(seconds + 0.5), 3600)
    m, s = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def build_command(cli: 'str | Path', video: 'str | Path', out_srt: 'str | Path',
                  opts: 'OcrOptions | None' = None) -> 'list[str]':
    '''Dựng dòng lệnh VideOCR. Hàm thuần, test được mà không cần chạy OCR.'''
    opts = opts or OcrOptions()
    cmd = [str(Path(cli)), '--video_path', str(video), '--output', str(out_srt),
           '--lang', str(opts.lang), '--use_gpu', 'true' if opts.use_gpu else 'false']
    if opts.min_subtitle_duration is not None:
        cmd += ['--min_subtitle_duration', f'{float(opts.min_subtitle_duration):g}']
    for attr, flag in (('conf_threshold', '--conf_threshold'), ('sim_threshold', '--sim_threshold'),
                       ('max_merge_gap', '--max_merge_gap'), ('frames_to_skip', '--frames_to_skip'),
                       ('time_start', '--time_start'), ('time_end', '--time_end')):
        value = getattr(opts, attr)
        if value is None:
            continue
        if attr in ('time_start', 'time_end'):
            cmd += [flag, normalize_time(value)]
        else:
            cmd += [flag, f'{value:g}' if isinstance(value, float) else str(value)]
    if opts.crop:
        x, y, w, h = (int(v) for v in opts.crop)
        cmd += ['--crop_x', str(x), '--crop_y', str(y),
                '--crop_width', str(w), '--crop_height', str(h)]
    for flag, value in (opts.extra or {}).items():
        cmd += [f'--{flag.lstrip("-")}', str(value)]
    return cmd


def parse_progress(line: 'str') -> 'tuple[str, float, str] | None':
    '''Dịch một dòng log của VideOCR thành (giai đoạn, tỉ lệ 0..1, nhãn cho UI).

    Trả về None với dòng không phải tiến trình. VideOCR in 2 bước: quét frame lấy
    ảnh khác biệt, rồi OCR từng ảnh — nên tỉ lệ gộp 30/70 để thanh tiến trình chạy
    một chiều, không nhảy lùi.
    '''
    text = (line or '').strip()
    if not text:
        return None
    m = _RE_STEP1.search(text)
    if m:
        cur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        tot = int(m.group(4)) * 3600 + int(m.group(5)) * 60 + int(m.group(6))
        frac = min(1.0, cur / tot) if tot else 0.0
        return ('scan', frac * 0.3, f'Quét frame {m.group(1)}:{m.group(2)}:{m.group(3)}/{m.group(4)}:{m.group(5)}:{m.group(6)}')
    m = _RE_STEP2.search(text)
    if m:
        done, total = int(m.group(1)), int(m.group(2))
        frac = min(1.0, done / total) if total else 0.0
        return ('ocr', 0.3 + frac * 0.7, f'OCR ảnh {done}/{total}')
    if _RE_DONE.search(text):
        return ('write', 1.0, 'Đang ghi file SRT')
    return None


def _popen_kwargs() -> 'dict[str, Any]':
    if os.name == 'nt':
        return {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)}
    return {}


def _kill_tree(proc: 'subprocess.Popen') -> None:
    '''Giết cả cây tiến trình.

    VideOCR là exe PyInstaller: bootloader spawn tiến trình con và đứa con giữ
    pipe stdout. ``proc.kill()`` chỉ hạ bootloader nên vòng đọc stdout treo mãi.
    '''
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                           capture_output=True, timeout=15, **_popen_kwargs())
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def run_ocr(video: 'str | Path', out_srt: 'str | Path', *,
            cli: 'str | Path | None' = None, opts: 'OcrOptions | None' = None,
            progress: 'Callable[[float, str], None] | None' = None,
            cancel_event: 'threading.Event | None' = None,
            timeout_s: 'float | None' = 1800.0) -> OcrResult:
    '''Chạy VideOCR trên một video, trả về cue đã parse.

    Không raise: mọi lỗi nằm trong ``OcrResult.error`` để UI hiển thị được.
    Hủy và timeout phải giết cả cây tiến trình, vì vòng đọc stdout block cho tới khi
    pipe đóng — nên không thể kiểm cờ trong lúc đọc.
    '''
    video = Path(video)
    out_srt = Path(out_srt)
    if not video.is_file():
        return OcrResult(False, error=f'Không thấy video: {video}')
    exe = find_videocr_cli(cli)
    if exe is None:
        return OcrResult(False, error='Không tìm thấy videocr-cli.exe. Cài VideOCR hoặc trỏ '
                                      'biến môi trường WINTERBOY_VIDEOCR tới thư mục cài.')

    # Popen chạy với cwd = thư mục của VideOCR, nên đường dẫn tương đối của người
    # dùng sẽ bị tính từ "C:\Program Files\VideOCR" — phải absolute hoá trước.
    try:
        video = video.resolve()
    except OSError:
        pass
    try:
        out_srt = out_srt.resolve()
    except OSError:
        pass
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(exe, video, out_srt, opts)
    logger.info('OCR: %s', ' '.join(cmd[:6]) + ' ...')
    tail: list[str] = []
    try:
        proc = subprocess.Popen(cmd, cwd=str(exe.parent), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                                errors='replace', bufsize=1, **_popen_kwargs())
    except OSError as exc:
        return OcrResult(False, error=f'Không khởi động được VideOCR: {exc}')

    aborted = {'reason': None}

    def _abort(reason: str) -> None:
        if aborted['reason'] is None:
            aborted['reason'] = reason
            _kill_tree(proc)

    watchdog = None
    if timeout_s:
        watchdog = threading.Timer(timeout_s, lambda: _abort(f'quá thời gian chờ ({timeout_s:g} giây)'))
        watchdog.daemon = True
        watchdog.start()

    poller = None
    if cancel_event is not None:
        def _watch_cancel():
            while proc.poll() is None:
                if cancel_event.is_set():
                    _abort('Đã dừng OCR')
                    return
                threading.Event().wait(0.25)
        poller = threading.Thread(target=_watch_cancel, daemon=True)
        poller.start()

    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if line:
                tail.append(line)
                if len(tail) > 400:
                    del tail[:len(tail) - 400]
            state = parse_progress(line)
            if state and progress:
                progress(state[1], state[2])
        code = proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        code = None
    finally:
        if watchdog is not None:
            watchdog.cancel()
        try:
            proc.stdout.close()                                    # type: ignore[union-attr]
        except Exception:
            pass

    if aborted['reason'] is not None:
        return OcrResult(False, error=aborted['reason'], log_tail=tail[-12:])
    if code is None:
        return OcrResult(False, error='VideOCR không thoát sau khi bị dừng', log_tail=tail[-12:])
    if code != 0:
        return OcrResult(False, error=f'VideOCR trả mã lỗi {code}: '
                                      f'{(tail[-1] if tail else "không có output")[:200]}',
                         log_tail=tail[-12:])
    if not out_srt.is_file():
        return OcrResult(False, error='VideOCR chạy xong nhưng không có file SRT', log_tail=tail[-12:])

    cues = load_srt(out_srt)
    duration = max((c.end_s for c in cues), default=0.0)
    if not cues:
        return OcrResult(False, srt_path=out_srt, error='File SRT rỗng — VideOCR không nhận '
                                                        'được dòng phụ đề nào trong video',
                         log_tail=tail[-12:])
    return OcrResult(True, srt_path=out_srt, cues=cues, duration_s=duration, log_tail=tail[-6:])

# Source Generated with Decompyle++
# File: srt_utils.pyc (Python 3.12)

'''SRT helpers dùng chung: parse, write, format timestamp, wrap sub.'''
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
SrtCue = <NODE:12>()

def wrap_subtitle_text(text = None, *, max_chars, max_lines):
    '''
    Xuống dòng sub VI dài để không tràn rìa trái/phải trong CapCut (9:16).

    Ưu tiên tách theo khoảng trắng; nếu 1 từ quá dài thì cắt cứng.
    '''
    if not text:
        text
    text = ''.replace('\r', '').strip()
    if not text:
        return ''
    text = re.sub('\\s+', ' ', text)
    if len(text) <= max_chars:
        return text
    words = None.split(' ')
    lines = []
    cur = ''
    for w in words:
        if not w:
            continue
        if len(w) > max_chars:
            chunk = w[:max_chars]
            w = w[max_chars:]
            if cur:
                lines.append(cur)
                cur = ''
            lines.append(chunk)
            if len(w) > max_chars:
                continue
        cand = f'''{cur} {w}'''.strip() if cur else w
        if len(cand) <= max_chars:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        head = lines[:max_lines - 1]
        tail = ' '.join(lines[max_lines - 1:])
        if len(tail) > max_chars * 2:
            tail = tail[:max_chars * 2 - 1].rstrip() + '…'
        lines = head + [
            tail]
    return '\n'.join(lines)


def format_ts(seconds = None):
    ms = int(round(max(0, seconds) * 1000))
    (h, ms) = divmod(ms, 3600000)
    (m, ms) = divmod(ms, 60000)
    (s, ms) = divmod(ms, 1000)
    return f'''{h:02d}:{m:02d}:{s:02d},{ms:03d}'''


def parse_ts(ts = None):
    ts = ts.strip().replace('.', ',')
    m = re.match('(\\d+):(\\d+):(\\d+)[,.](\\d+)', ts)
    if not m:
        return 0
    (h, mi, s, ms) = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def parse_srt_string(raw = None):
    if not raw:
        raw
    raw = ''.strip()
    if not raw:
        return []
    
    try:
        import pysrt
        subs = pysrt.SubRipFile.from_string(raw)
        out = []
        for i, item in enumerate(subs):
            start_s = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
            end_s = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
            if not item.text:
                item.text
            text = ''.replace('\n', ' ').strip()
            if not text:
                continue
            if end_s <= start_s:
                end_s = start_s + 0.3
            out.append(SrtCue(index = i, start_s = start_s, end_s = end_s, text = text))
        return out
    except Exception:
        pass

    blocks = re.split('\\n\\s*\\n', raw.strip())
    out = []
    idx = 0
    time_re = re.compile('(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})\\s*-->\\s*(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})')
# WARNING: Decompyle incomplete


def load_srt(path = None):
    path = Path(path)
    if not path.is_file():
        return []
    raw = None.read_text(encoding = 'utf-8-sig', errors = 'replace')
    return parse_srt_string(raw)


def write_srt(cues = None, path = None):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    lines = []
    for i, c in enumerate(cues, start = 1):
        lines.append(str(i))
        lines.append(f'''{format_ts(c.start_s)} --> {format_ts(c.end_s)}''')
        lines.append(c.text.strip())
        lines.append('')
    path.write_text('\n'.join(lines), encoding = 'utf-8')
    return path


def cues_to_plain_lines(cues = None):
    pass
# WARNING: Decompyle incomplete


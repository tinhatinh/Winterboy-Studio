'''SRT helpers dùng chung: parse, write, format timestamp, wrap sub.'''
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SrtCue:
    index: int
    start_s: float
    end_s: float
    text: str

    @property
    def duration_s(self) -> 'float':
        return max(0.05, self.end_s - self.start_s)


def wrap_subtitle_text(text: 'str', *, max_chars: 'int' = 22, max_lines: 'int' = 3) -> 'str':
    '''
    Xuống dòng sub VI dài để không tràn rìa trái/phải trong CapCut (9:16).

    Ưu tiên tách theo khoảng trắng; nếu 1 từ quá dài thì cắt cứng.
    '''
    text = (text or '').replace('\r', '').strip()
    if not text:
        return ''
    text = re.sub('\\s+', ' ', text)
    if len(text) <= max_chars:
        return text
    words = text.split(' ')
    lines = []
    cur = ''
    for w in words:
        if not w:
            continue
        if len(w) > max_chars:
            # từ dài hơn 1 dòng: cắt cứng thành nhiều chunk, phần dư xử lý tiếp
            while len(w) > max_chars:
                chunk = w[:max_chars]
                w = w[max_chars:]
                if cur:
                    lines.append(cur)
                    cur = ''
                lines.append(chunk)
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


def format_ts(seconds: 'float') -> 'str':
    ms = int(round(max(0, seconds) * 1000))
    (h, ms) = divmod(ms, 3600000)
    (m, ms) = divmod(ms, 60000)
    (s, ms) = divmod(ms, 1000)
    return f'''{h:02d}:{m:02d}:{s:02d},{ms:03d}'''


def parse_ts(ts: 'str') -> 'float':
    ts = ts.strip().replace('.', ',')
    m = re.match('(\\d+):(\\d+):(\\d+)[,.](\\d+)', ts)
    if not m:
        return 0.0
    (h, mi, s, ms) = map(int, m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def parse_srt_string(raw: 'str') -> 'list[SrtCue]':
    '''Đọc nội dung SRT thành cue. Dùng pysrt khi có, không có thì tự tách block.'''
    raw = (raw or '').strip()
    if not raw:
        return []

    try:
        import pysrt
        subs = pysrt.SubRipFile.from_string(raw)
        out = []
        for i, item in enumerate(subs):
            start_s = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
            end_s = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
            text = (item.text or '').replace('\n', ' ').strip()
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
    for block in blocks:
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        if len(lines) < 2:
            continue
        m = None
        text_lines = []
        for j, ln in enumerate(lines):
            m = time_re.search(ln)
            if not m:
                continue
            text_lines = lines[j + 1:]
            break
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        start_s = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end_s = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        text = ' '.join(text_lines).strip()
        if not text:
            continue
        out.append(SrtCue(index = idx, start_s = start_s, end_s = end_s, text = text))
        idx += 1
    return out


def load_srt(path: 'str | Path') -> 'list[SrtCue]':
    path = Path(path)
    if not path.is_file():
        return []
    raw = path.read_text(encoding = 'utf-8-sig', errors = 'replace')
    return parse_srt_string(raw)


def write_srt(cues: 'list[SrtCue]', path: 'str | Path') -> 'Path':
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


def cues_to_plain_lines(cues: 'list[SrtCue]') -> 'list[str]':
    return [c.text for c in cues]

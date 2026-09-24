'''Dịch SRT thủ công — ghép bản dịch dán từ ngoài vào đúng cue chưa dịch.

Luồng thực tế: user đem SRT nguồn sang ChatGPT/Google Dịch, chép kết quả về rồi
dán ngược vào tool.  Bản chép về mỗi nơi một kiểu, nên phần khó không phải là
dán mà là *đoán đúng định dạng* và *đặt đúng dòng*.

Toàn bộ phần suy luận nằm ở đây, tách khỏi giao diện để test được bằng dữ liệu
dựng sẵn (scripts/manual_translate_test.py) — không cần mở app, không tốn quota.
'''
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from app.services.srt_utils import SrtCue

_SCRIPTS: dict[str, tuple[tuple[int, int], ...]] = {
    'han': ((13312, 19903), (19968, 40959), (63744, 64255)),
    'kana': ((12352, 12447), (12448, 12543)),
    'hangul': ((4352, 4607), (12592, 12687), (44032, 55215)),
    'thai': ((3584, 3711),),
    'cyrillic': ((1024, 1279),),
    'arabic': ((1536, 1791),),
}

_TARGET_SCRIPT: dict[str, str] = {
    'Tiếng Việt': 'latin',
    'English': 'latin',
    'Español (Spanish)': 'latin',
    'Français (French)': 'latin',
    'Deutsch (German)': 'latin',
    '中文 (Chinese)': 'han',
    '日本語 (Japanese)': 'kana',
    '한국어 (Korean)': 'hangul',
    'ไทย (Thai)': 'thai',
}


def _script_of(char: str) -> str:
    code = ord(char)
    for name, ranges in _SCRIPTS.items():
        for lo, hi in ranges:
            if lo <= code <= hi:
                return name
    return 'latin' if char.isalpha() else ''


def scripts_in(text: str) -> set[str]:
    '''Các hệ chữ xuất hiện trong đoạn text (bỏ qua số, dấu câu, khoảng trắng).'''
    found = set()
    for char in text:
        name = _script_of(char)
        if not name:
            continue
        found.add(name)
    return found


def looks_untranslated(text: str, *, target_lang: str,
                       source_lang: str | None = None) -> bool:
    '''Cue này còn cần dịch không?
    
    Hỗ trợ chuẩn xác cả 9 ngôn ngữ:
    - Trung, Nhật, Hàn, Thái -> Tiếng Việt
    - Anh, Pháp, Đức, Tây Ban Nha -> Tiếng Việt
    - Tiếng Việt -> Anh / các tiếng khác
    '''
    from app.services.language_detector import is_untranslated_cue
    return is_untranslated_cue(text, target_lang=target_lang, source_lang=source_lang)


_TS = r'\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}'
_SRT_BLOCK = re.compile(
    rf'(?:^|\n)\s*(\d+)\s*\n\s*({_TS})\s*-->\s*({_TS})\s*\n(.+?)(?=\n\s*\n|\n\s*\d+\s*\n\s*{_TS}|$)',
    re.DOTALL)
_NUMBERED = re.compile(r'^\s*(\d{1,5})\s*(?:[.)\]:|\-–—]|\t)\s*(.+)$')


@dataclass
class PastedLine:
    '''Một dòng bản dịch đọc được, kèm số thứ tự nếu bản dán có ghi.'''

    text: str
    index: int | None = None


@dataclass
class PasteReading:
    lines: list[PastedLine]
    fmt: str
    note: str = ''

    @property
    def numbered(self) -> bool:
        return any(line.index is not None for line in self.lines)


def _clean(text: str) -> str:
    '''Gộp xuống dòng trong một cue thành một dòng, bỏ khoảng trắng thừa.'''
    text = unicodedata.normalize('NFC', text)
    return re.sub(r'\s+', ' ', text).strip()


def read_pasted(raw: str) -> PasteReading:
    '''Đoán định dạng của đoạn vừa dán và rút ra danh sách dòng dịch.

    Thứ tự thử đi từ dạng nhiều thông tin nhất xuống ít nhất, vì dạng nào đọc
    được thì dạng đó chắc chắn hơn: SRT đầy đủ > có đánh số > cách nhau dòng
    trống > mỗi dòng một cue.
    '''
    raw = (raw or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not raw:
        return PasteReading([], 'lines', 'Chưa có nội dung.')

    blocks = _SRT_BLOCK.findall(raw)
    if blocks:
        lines = [PastedLine(_clean(body), int(num))
                 for num, _s, _e, body in blocks
                 if _clean(body)]
        if lines:
            return PasteReading(lines, 'srt', f'Đọc dạng SRT — {len(lines)} cue.')

    rows = [ln for ln in raw.split('\n')]
    stripped = [ln.strip() for ln in rows if ln.strip()]
    hits = [_NUMBERED.match(ln) for ln in stripped]
    if stripped and sum(1 for h in hits if h) >= max(2, int(len(stripped) * 0.8)):
        lines = [
            PastedLine(_clean(h.group(2)), int(h.group(1)))
            for h in hits
            if h and _clean(h.group(2))
        ]
        if lines:
            return PasteReading(lines, 'numbered', f'Đọc dạng đánh số — {len(lines)} dòng.')

    if re.search(r'\n\s*\n', raw):
        chunks = [_clean(c) for c in re.split(r'\n\s*\n', raw)]
        chunks = [c for c in chunks if c]
        if len(chunks) >= 2:
            return PasteReading(
                [PastedLine(c) for c in chunks], 'blocks',
                f'Đọc dạng khối cách dòng trống — {len(chunks)} khối.')

    lines = [PastedLine(_clean(ln)) for ln in stripped if _clean(ln)]
    return PasteReading(lines, 'lines', f'Đọc mỗi dòng một cue — {len(lines)} dòng.')


@dataclass
class FillPlan:
    '''Dự định thay chữ, chưa áp dụng — giao diện xem trước rồi mới xác nhận.'''

    changes: dict[int, str] = field(default_factory=dict)
    matched_by: str = 'order'
    leftover: list[str] = field(default_factory=list)
    unfilled: list[int] = field(default_factory=list)
    note: str = ''


def plan_fill(cues: list[SrtCue], reading: PasteReading, *,
              targets: list[int] | None = None) -> FillPlan:
    '''Tính xem mỗi dòng dán sẽ vào cue nào.

    targets: vị trí (0-based) các cue được phép ghi đè.  None nghĩa là mọi cue.

    Hai cách ghép:
      - theo SỐ THỨ TỰ khi bản dán có đánh số và số đó khớp cue thật.  Dùng
        được cả khi bản dán chỉ chứa một phần rời rạc.
      - theo THỨ TỰ khi không có số: dòng thứ k vào ô trống thứ k.
    '''
    plan = FillPlan()
    if not reading.lines:
        plan.note = 'Chưa có nội dung để lấp.'
        return plan

    allowed = (list(range(len(cues))) if targets is None
               else [i for i in targets if 0 <= i < len(cues)])
    allowed_set = set(allowed)

    if reading.numbered:
        by_index = {
            line.index - 1: line.text
            for line in reading.lines
            if line.index is not None and 0 <= line.index - 1 < len(cues)
        }
        hit = sum(1 for pos in by_index if pos in allowed_set)
        aligned = hit / len(by_index) if by_index else 0.0
        covers_file = len(by_index) >= max(1, int(len(cues) * 0.9))
        if by_index and (aligned >= 0.9 or covers_file):
            plan.matched_by = 'index'
            for pos, text in by_index.items():
                if pos in allowed_set:
                    plan.changes[pos] = text
            plan.leftover = [
                line.text for line in reading.lines
                if line.index is None or line.index - 1 not in allowed_set
            ]
            plan.unfilled = [i for i in allowed if i not in plan.changes]
            plan.note = (f'Ghép theo số thứ tự — {len(plan.changes)}'
                         ' ô. Số trong bản dán được coi là số cue của SRT.')
            return plan

    plan.matched_by = 'order'
    texts = [line.text for line in reading.lines]
    pairs = min(len(texts), len(allowed))
    for k in range(pairs):
        plan.changes[allowed[k]] = texts[k]
    plan.leftover = texts[pairs:]
    plan.unfilled = allowed[pairs:]
    if len(texts) == len(allowed):
        plan.note = f'Ghép tuần tự — vừa khít {pairs} ô.'
    elif plan.leftover:
        plan.note = (
            f'Ghép tuần tự {pairs} ô — còn thừa {len(plan.leftover)} dòng chưa dùng.')
    else:
        plan.note = (
            f'Ghép tuần tự {pairs} ô — còn {len(plan.unfilled)} ô chưa được lấp.')
    return plan


def apply_plan(cues: list[SrtCue], plan: FillPlan) -> list[SrtCue]:
    '''Trả về danh sách cue mới; timestamp giữ nguyên tuyệt đối.'''
    out = []
    for i, cue in enumerate(cues):
        text = plan.changes.get(i, cue.text)
        out.append(SrtCue(cue.index, cue.start_s, cue.end_s, text))
    return out


def untranslated_positions(cues: list[SrtCue], *, target_lang: str) -> list[int]:
    return [i for i, c in enumerate(cues) if looks_untranslated(c.text, target_lang=target_lang)]


def build_external_ai_request(cues: list[SrtCue], positions: list[int], *,
                              target_lang: str) -> str:
    '''Tạo đoạn copy gọn để dịch ngoài app và dán ngược theo đúng số cue.'''
    valid = [pos for pos in positions if 0 <= pos < len(cues)]
    lines = [f'{cues[pos].index}|{_clean(cues[pos].text)}' for pos in valid]
    if not lines:
        return ''
    extra = (
        ' Không được để sót chữ Hán; tên riêng, chức danh và đại từ phải dịch hoặc phiên âm sang tiếng Việt nhất quán.'
        if target_lang in {'Tiếng Việt', 'Vietnamese'}
        else ' Không được để sót chữ của ngôn ngữ nguồn.')
    return (f'Hãy dịch các cue sau sang {target_lang}.{extra}\n'
            'Giữ nguyên số cue trước dấu |. Chỉ trả về đúng dạng SỐ|BẢN DỊCH, mỗi cue một dòng; '
            'không giải thích, không Markdown.\n\n'
            + '\n'.join(lines))

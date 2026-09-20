# Source Generated with Decompyle++
# File: manual_translate.pyc (Python 3.12)

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
_SCRIPTS: 'dict[str, tuple[tuple[int, int], ...]]' = {
    'han': ((13312, 19903), (19968, 40959), (63744, 64255)),
    'kana': ((12352, 12447), (12448, 12543)),
    'hangul': ((4352, 4607), (12592, 12687), (44032, 55215)),
    'thai': ((3584, 3711),),
    'cyrillic': ((1024, 1279),),
    'arabic': ((1536, 1791),) }
_TARGET_SCRIPT: 'dict[str, str]' = {
    'Tiếng Việt': 'latin',
    'English': 'latin',
    'Español (Spanish)': 'latin',
    'Français (French)': 'latin',
    'Deutsch (German)': 'latin',
    '中文 (Chinese)': 'han',
    '日本語 (Japanese)': 'kana',
    '한국어 (Korean)': 'hangul',
    'ไทย (Thai)': 'thai' }

def _script_of(char = None):
    code = ord(char)
    for name, ranges in _SCRIPTS.items():
        for lo, hi in ranges:
            if  <= lo, code:
                if not lo, code <= hi:
                    continue
                else:
                    ranges
                
                
                return _SCRIPTS.items(), ranges, name
        if char.isalpha():
            return 'latin'
        return _SCRIPTS.items()


def scripts_in(text = None):
    '''Các hệ chữ xuất hiện trong đoạn text (bỏ qua số, dấu câu, khoảng trắng).'''
    found = set()
    for char in text:
        name = _script_of(char)
        if not name:
            continue
        found.add(name)
    return found


def looks_untranslated(text = None, *, target_lang, source_lang):
    '''Cue này còn cần dịch không?
    
    Hỗ trợ chuẩn xác cả 9 ngôn ngữ:
    - Trung, Nhật, Hàn, Thái -> Tiếng Việt
    - Anh, Pháp, Đức, Tây Ban Nha -> Tiếng Việt
    - Tiếng Việt -> Anh / các tiếng khác
    '''
    is_untranslated_cue = is_untranslated_cue
    import app.services.language_detector
    return is_untranslated_cue(text, target_lang = target_lang, source_lang = source_lang)

_TS = '\\d{1,2}:\\d{2}:\\d{2}[,.]\\d{1,3}'
_SRT_BLOCK = re.compile(f'''(?:^|\\n)\\s*(\\d+)\\s*\\n\\s*({_TS})\\s*-->\\s*({_TS})\\s*\\n(.+?)(?=\\n\\s*\\n|\\n\\s*\\d+\\s*\\n\\s*{_TS}|$)''', re.DOTALL)
_NUMBERED = re.compile('^\\s*(\\d{1,5})\\s*(?:[.)\\]:|\\-–—]|\\t)\\s*(.+)$')
PastedLine = <NODE:12>()
PasteReading = <NODE:12>()

def _clean(text = None):
    '''Gộp xuống dòng trong một cue thành một dòng, bỏ khoảng trắng thừa.'''
    text = unicodedata.normalize('NFC', text)
    return re.sub('\\s+', ' ', text).strip()


def read_pasted(raw = None):
    '''Đoán định dạng của đoạn vừa dán và rút ra danh sách dòng dịch.

    Thứ tự thử đi từ dạng nhiều thông tin nhất xuống ít nhất, vì dạng nào đọc
    được thì dạng đó chắc chắn hơn: SRT đầy đủ > có đánh số > cách nhau dòng
    trống > mỗi dòng một cue.
    '''
    if not raw:
        raw
    raw = ''.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not raw:
        return PasteReading([], 'lines', 'Chưa có nội dung.')
    blocks = None.findall(raw)
# WARNING: Decompyle incomplete

FillPlan = <NODE:12>()

def plan_fill(cues = None, reading = None, *, targets):
    '''Tính xem mỗi dòng dán sẽ vào cue nào.

    targets: vị trí (0-based) các cue được phép ghi đè.  None nghĩa là mọi cue.

    Hai cách ghép:
      - theo SỐ THỨ TỰ khi bản dán có đánh số và số đó khớp cue thật.  Dùng
        được cả khi bản dán chỉ chứa một phần rời rạc.
      - theo THỨ TỰ khi không có số: dòng thứ k vào ô trống thứ k.
    '''
    pass
# WARNING: Decompyle incomplete


def apply_plan(cues = None, plan = None):
    '''Trả về danh sách cue mới; timestamp giữ nguyên tuyệt đối.'''
    out = []
    for i, cue in enumerate(cues):
        text = plan.changes.get(i, cue.text)
        out.append(SrtCue(cue.index, cue.start_s, cue.end_s, text))
    return out


def untranslated_positions(cues = None, *, target_lang):
    pass
# WARNING: Decompyle incomplete


def build_external_ai_request(cues = None, positions = None, *, target_lang):
    '''Tạo đoạn copy gọn để dịch ngoài app và dán ngược theo đúng số cue.'''
    pass
# WARNING: Decompyle incomplete


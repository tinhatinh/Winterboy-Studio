# Source Generated with Decompyle++
# File: vi_normalizer.pyc (Python 3.12)

'''Vietnamese text normalization for TTS input: rewrites the written forms the
model was never trained to voice (digits, dates, clock times, version strings,
fractions, acronyms) into the words a speaker would actually say.

    "Ngày 23/8/2024 lúc 15h30, giá 1.250.000 tăng 12,5"
        -> "Ngày hai mươi ba tháng tám năm hai nghìn không trăm hai mươi tư lúc
            mười lăm giờ ba mươi phút, giá một triệu hai trăm năm mươi nghìn
            tăng mười hai phẩy năm"

Provenance
──────────
The expansion rules (Vietnamese number chunking, the mười/lăm/mốt/tư sandhi,
the time/date/version/fraction shapes) and ``data/abbreviations.txt`` are
adapted from soe-vinorm (https://github.com/vinhdq842/soe-vinorm), MIT —
see data/LICENSE.soe-vinorm. What is NOT carried over is its machinery: that
project tags every token with a CRF (sklearn-crfsuite + a pickled model) and
disambiguates acronyms with an ONNX scorer, both downloaded from the Hub on
first use. Neither runs here — this module is pure stdlib regex, so the webui\'s
ONNX-only, no-torch-anywhere backend stays that way and startup stays instant.

Scope — the deliberately small set of cases this covers
──────────────────────────────────────────────────────
    date       23/8/2024, 23-8-2024, 23.8.2024, 8/2024, "ngày 23/8"
    time       15h30, 15h, 15:30, 9g45, 15:30:20
    version    v1.2, 1.2.3   (3+ dot-separated groups, or a v-prefix)
    fraction   3/4           (when it isn\'t a date)
    percent    25%, 12,5 %   -> "... phần trăm"
    at         @             -> "a còng" (never inside an email — those are protected)
    abbrev     TP.HCM, ATM, UBND  -> dictionary lookup, uppercase forms only
    number     1.250.000, 12,5, -7, +3, 2+3, 5 * 4, 2^10
                 (integer, decimal, sign, thousand separators, arithmetic ops)

Everything else soe-vinorm handles — money, measurement units, Roman numerals,
ranges, scores, quarters, URLs/emails, letter-by-letter spelling of unknown
sequences — is intentionally left alone: those either need
the CRF\'s context to tag safely or were out of scope for this integration.
URLs and emails are actively *protected* (matched and skipped) so a normalizer
pass can never mangle one.

Ambiguity, without a tagger to resolve it
─────────────────────────────────────────
A CRF decides "3/4" by context; regexes cannot, so the choices are fixed and
documented at each pattern below. The two that matter:

  - ``D/M`` is a date only after a date cue word (ngày, mùng, mồng, hôm,
    sáng, ...); otherwise it is read as a fraction. So "ngày 3/4" -> "ngày ba
    tháng tư" but a bare "3/4" -> "ba trên bốn".
  - ``M/YYYY`` (4-digit second group in 1000-2999) is a month-year. Unlike
    soe-vinorm this emits the word "tháng" itself unless the text already has
    it, since here no tagger guarantees the cue word is there.

An acronym is only expanded when written in uppercase (``ATM``, ``TP.HCM``) and
at least two letters long — a lowercase dictionary key like "ca" or "tư" is an
ordinary Vietnamese word far more often than an acronym, and single letters are
pure noise. When the dictionary holds several readings for one acronym (BCS =
"ban cán sự" / "bao cao su"), soe-vinorm picks with its ONNX likelihood scorer;
here the first listed reading wins.
'''
from __future__ import annotations
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
__all__ = [
    'normalize_vi_text',
    'expand_number',
    'load_abbreviations']
_DATA_DIR = Path(__file__).parent / 'data'
_DIGIT = {
    '0': 'không',
    '1': 'một',
    '2': 'hai',
    '3': 'ba',
    '4': 'bốn',
    '5': 'năm',
    '6': 'sáu',
    '7': 'bảy',
    '8': 'tám',
    '9': 'chín',
    ',': 'phẩy' }
_UNIT_SINGLE = [
    '',
    'mươi',
    'trăm']
_UNIT_TRIPLE = [
    '',
    'nghìn',
    'triệu',
    'tỷ',
    'nghìn tỷ',
    'triệu tỷ',
    'tỷ tỷ']
_OP_WORDS = str.maketrans({
    '+': 'cộng',
    '-': 'trừ',
    '*': 'nhân',
    '/': 'chia',
    '^': 'mũ' })

def _apply_sandhi(text = None):
    '''Vietnamese number-pronunciation rules: 15 is "mười lăm" not "mười năm",
    21 "hai mươi mốt" not "hai mươi một", 24 "hai mươi tư", 104 "một trăm linh
    tư".'''
    return text.replace('mười năm', 'mười lăm').replace('mươi năm', 'mươi lăm').replace('mươi bốn', 'mươi tư').replace('mươi một', 'mươi mốt').replace('linh bốn', 'linh tư')


def expand_digit(digits = None):
    '''Read a run of characters one symbol at a time ("2024" -> "hai không hai
    bốn"). Used for the decimal tail and as the number fallback.'''
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(digits.replace(' ', '')())


def _split_chunks(number = None):
    """Split a digit string into 3-digit chunks, most significant first, with a
    short leading chunk when the length isn't a multiple of 3."""
    pass
# WARNING: Decompyle incomplete


def _speak_chunk(chunk = None, scale_index = None):
    '''One 3-digit chunk plus its scale word ("250" at scale 1 -> "hai trăm năm
    mươi nghìn"). An all-zero chunk is silent.'''
    if chunk == '000':
        return ''
    result = ''
    pos = len(chunk) - 1
    if pos >= 0:
        if pos == len(chunk) - 1 and chunk[pos] == '0' and len(chunk) > 1:
            pass
        elif pos == len(chunk) - 2 and chunk[pos] in ('1', '0'):
            if pos == 0 and chunk[pos] == '0':
                pass
            elif chunk[pos] == '1':
                result = f'''mười {_DIGIT[chunk[pos + 1]]}''' if chunk[pos + 1] != '0' else 'mười'
            elif chunk[pos + 1] != '0':
                pass
            
            result = ''
        elif result:
            pass
        
        result = ' ' + result + ''
        pos -= 1
        if pos >= 0:
            continue
    if scale_index >= len(_UNIT_TRIPLE):
        raise IndexError('number is too large to speak')
    return ' '.join([
        result.strip(),
        _UNIT_TRIPLE[scale_index]]).strip()


def expand_number(number = None):
    '''Speak an integer, a decimal, or a small arithmetic expression.

    Handles the sign ("-7" -> "trừ bảy"), \'.\' as a thousands separator
    ("1.250.000"), \',\' as the Vietnamese decimal comma ("12,5" -> "mười hai
    phẩy năm"), \'.\' as a decimal point when at most two digits follow it
    ("3.14" -> "ba chấm một bốn"), and operators between numbers ("2+3" ->
    "hai cộng ba"). Leading zeros are dropped; a number too large for the
    scale table falls back to digit-by-digit reading.
    '''
    
    try:
        sign = ''
        if number[0] in ('-', '+'):
            sign = {
                '+': 'cộng',
                '-': 'trừ' }[number[0]]
            number = number[1:]
        if len(number) > 1 and number[0] == '0' and number[1].isdigit():
            number = number[1:]
            if len(number) > 1 and number[0] == '0' and number[1].isdigit():
                continue
                
                try:
                    number = number.strip()
                    matches = re.findall('[-+]?[0-9.,]+', number)
                    if (len(matches) > 1 or matches) and matches[0] != number:
                        return re.sub('\\s*([-+]?[0-9.,]+)\\s*', (lambda m: f''' {expand_number(m.group(1))} '''), number).strip().translate(_OP_WORDS)
                    number = None.sub('[^0-9.,]', '', number)
                    decimal_part = ''
                    if number.count(',') == 1:
                        number = number.replace('.', '')
                        decimal_part = f'''phẩy {expand_digit(number.split(',')[-1])}'''
                        number = ''.join(number.split(',')[:-1])
                    elif number.count('.') == 1 and len(number[number.index('.'):]) <= 3:
                        number = number.replace(',', '')
                        decimal_part = f'''chấm {expand_digit(number.split('.')[-1])}'''
                        number = ''.join(number.split('.')[:-1])
                    else:
                        number = number.replace('.', '')
                    chunks = _split_chunks(number)
                    parts = []
                    for i, chunk in enumerate(chunks):
                        spoken = _speak_chunk(chunk, len(chunks) - i - 1)
                        if not spoken:
                            continue
                            
                            try:
                                parts.append(spoken)
                                continue
                                return f'''{sign} {_apply_sandhi(' '.join(parts))} {decimal_part}'''.strip()
                            except IndexError:
                                return 





def _num(value = None):
    '''expand_number for a plain integer group inside a date/time/version.'''
    return expand_number(value)

_ROMAN = {
    'I': 'một',
    'II': 'hai',
    'III': 'ba',
    'IV': 'bốn',
    'V': 'năm',
    'VI': 'sáu',
    'VII': 'bảy',
    'VIII': 'tám',
    'IX': 'chín',
    'X': 'mười' }
_ROMAN_CUES = ('quý', 'thứ', 'khóa', 'kỳ', 'đợt', 'loại', 'chương', 'phần', 'thế kỷ')
_PREFIX_ABBR = ('TP', 'Q', 'P', 'H', 'TX', 'TT', 'KP')

def spell_letters(letters = None):
    '''Return a letter run as capitals, unchanged: "ab" -> "AB".

    Deliberately NOT spaced into single letters, and deliberately NOT a
    Vietnamese letter-name table. A capitalised run is already enough for the
    model to spell it; "A B" adds nothing, and a letter-name table is a second
    thing to get wrong — "W" alone is "vê kép", "đắp liu" or "vê đúp"
    depending on the speaker.
    '''
    return letters.upper()


def _month(value = None):
    '''Month name. The fourth month is "tháng tư", never "tháng bốn" — the one
    place this module knowingly departs from soe-vinorm, which runs months
    through the plain cardinal reader.'''
    if value.lstrip('0') == '4':
        return 'tư'
    return None(value)

load_abbreviations = (lambda : path = _DATA_DIR / 'abbreviations.txt'table = { }f = open(path, encoding = 'utf-8')for line in f:
line = line.strip()if line and line.startswith('#') or ':' not in line:
continue(abbr, readings) = line.split(':', 1)table.setdefault(abbr, []).extend(readings.split(','))None(None, None)tablewith None:
if not None:
passtable)()

def _expand_abbreviation(token = None):
    '''Dictionary reading for an uppercase acronym, or None to leave it alone.

    Tries the token as written, then with dots stripped ("TP.HCM" -> "TPHCM"),
    then splits on dots and expands each part when every part is known
    ("T.Ư" -> "trung ương" only if both halves resolve). Unknown acronyms come
    back None — soe-vinorm would spell them out letter by letter, which this
    module does not do.
    '''
    pass
# WARNING: Decompyle incomplete

_VN_UPPER = 'A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯẠ-Ỹ'
_VN_LOWER = 'a-zàáâãèéêìíòóôõùúýăđĩũơưạ-ỹ'

def split_camel_case(text = None):
    '''Insert a space at every internal case boundary of a mixed-case token.

    Case is tested with ``str.isupper()``/``str.islower()``, NOT a regex letter
    class: the precomposed Vietnamese letters live in Latin Extended Additional,
    where upper and lower case interleave, so a range like ``Ạ-Ỹ`` also matches
    "ế" and would split "Chiếc" into "Chi ếc".

    Only an ACRONYM is split off — an uppercase run of two or more. That is the
    difference between "Chat|GPT" and "MacBook": the first is a word glued to an
    acronym, the second is an ordinary CamelCase brand that is read as one word
    ("YouTube", "TikTok"), and splitting those makes the reading worse.

    A single leading lowercase letter does not open a boundary either, so
    "iPhone" and "eBay" survive intact.
    '''
    out = []
    for token in re.split('(\\s+)', text):
        if token or token.isspace():
            out.append(token)
            continue
        if not (lambda .0: pass# WARNING: Decompyle incomplete
)(token()) or (lambda .0: pass# WARNING: Decompyle incomplete
)(token()):
            out.append(token)
            continue
        lower_run = 0
        chars = []
        for i, c in enumerate(token):
            if c.isupper() and i > 0:
                nxt = token[i + 1] if i + 1 < len(token) else ''
                run = 0
                if i + run < len(token) and token[i + run].isupper():
                    run += 1
                    if i + run < len(token) and token[i + run].isupper():
                        continue
                if lower_run >= 2 and run >= 2:
                    chars.append(' ')
                elif token[i - 1].isupper() and nxt.islower():
                    chars.append(' ')
            lower_run = lower_run + 1 if c.islower() else 0
            chars.append(c)
        out.append(''.join(chars))
    return ''.join(out)

_DATE_CUES = 'ngày|mùng|mồng|hôm|sáng|trưa|chiều|tối|đêm|từ|đến|và|hoặc'
_PROTECTED_RE = re.compile('(?:(?:https?|ftp)://\\S+\n        |www\\.\\S+\n        |[\\w.+-]+@[\\w-]+(?:\\.[\\w-]+)+\n        |\\b[\\w-]+(?:\\.[\\w-]+)*\\.(?:com|net|org|vn|io|edu|gov|info|dev|ai)\\b(?:/\\S*)?\n        )', re.VERBOSE | re.IGNORECASE)
_SCANNER = re.compile(f'''\n    # ── time: HH:MM:SS / HHhMMmSS ────────────────────────────────────────────\n      (?<![\\d:])(?P<t_h>[01]?\\d|2[0-3])[:hg](?P<t_m>[0-5]?\\d)[:mp](?P<t_s>[0-5]?\\d)(?![\\d:])\n    # ── date: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY ─────────────────────────────\n    | (?<![\\d/.\\-])(?P<d_d>0?[1-9]|[12]\\d|3[01])(?P<d_sep>[/.\\-])(?P<d_m>0?[1-9]|1[0-2])(?P=d_sep)(?P<d_y>[12]\\d{{3}})(?![\\d/-])(?!\\.\\d)\n    # ── month-year: MM/YYYY, MM-YYYY ─────────────────────────────────────────\n    | (?<![\\d/.\\-])(?P<my_m>0?[1-9]|1[0-2])[/\\-](?P<my_y>1\\d{{3}}|20\\d{{2}}|21\\d{{2}})(?![\\d/-])(?!\\.\\d)\n    # ── day-month: DD/MM after a date cue word only (else it\'s a fraction) ───\n    | (?<=\\b)(?P<dm_cue>(?i:{_DATE_CUES}))(?P<dm_gap>\\s+)(?P<dm_d>0?[1-9]|[12]\\d|3[01])[/\\-](?P<dm_m>0?[1-9]|1[0-2])(?![\\d/-])(?!\\.\\d)\n    # ── time: HH:MM (2-digit minutes), HHhMM, HHgMM ──────────────────────────\n    | (?<![\\d:])(?P<hm_h>[01]?\\d|2[0-3]):(?P<hm_m>[0-5]\\d)(?![\\d:])\n    | (?<![\\d:])(?P<hg_h>[01]?\\d|2[0-3])[hg](?P<hg_m>[0-5]\\d)(?![\\dhg])\n    # ── time: HH h  ("15h", "9g") ────────────────────────────────────────────\n    | (?<![\\d:])(?P<h_h>[01]?\\d|2[0-3])[hg](?![\\w])\n    # ── version: v1.2 / V1.2.3, or a bare 3+ group dotted number ─────────────\n    | (?<![\\w.])(?P<vp>[vV])(?P<v_num>\\d+(?:\\.\\d+)+)(?!\\w|\\.\\d|,\\d)\n    | (?<![\\w.,])(?P<v_bare>\\d+(?:\\.\\d+){{2,}})(?!\\w|\\.\\d|,\\d)\n    # ── fraction: a/b (dates already claimed above) ──────────────────────────\n    | (?<![\\w/.,])(?P<f_a>\\d+)\\s*/\\s*(?P<f_b>\\d+)(?![\\w/,])(?!\\.\\d)\n    # ── degree: 38°C / 38 °C ─────────────────────────────────────────────────\n    | (?<![\\w.,])(?P<deg_n>-?\\d[\\d.,]*)\\s*°\\s*(?P<deg_u>[CF])?(?![{_VN_LOWER}])\n    # ── percent: 25%, 12,5 % — BEFORE the number branch, or that claims the\n    #    digits and leaves a bare \'%\' behind ───────────────────────────────────\n    | (?<![\\w.,])(?P<pct_num>[-+]?\\d[\\d.,]*?)\\s*%(?!\\w)\n    # ── number: integer / decimal / thousand-separated / signed / arithmetic ─\n    | (?<![\\w.,])(?P<n_num>[-+]?\\d[\\d.,]*(?:\\s*[*^+]\\s*[-+]?\\d[\\d.,]*|\\s+[-/]\\s+[-+]?\\d[\\d.,]*|[*^]\\s*[-+]?\\d[\\d.,]*)*)(?![.,]?\\d)\n    # ── prefix abbreviation + proper noun: "TP. HCM" — the dot belongs to the\n    #    abbreviation, so it is consumed here rather than left mid-sentence ────\n    | (?<![\\w.])(?P<pfx>TP|TX|TT|KP|[QPH])\\.(?=\\s+[{_VN_UPPER}])\n    # ── acronym pair over a slash: USD/VND, KM/H. Left verbatim — expanding\n    #    each side invents a reading ("đô la mỹ/việt nam đồng") worse than the\n    #    source, and the model says "USD/VND" correctly as written. Matched\n    #    only so the abbreviation branch below cannot claim one half. ─────────\n    | (?<![\\w/])(?P<ap>[{_VN_UPPER}]{{1,6}}/[{_VN_UPPER}]{{1,6}})(?![\\w/])\n    # ── alphanumeric code: AB-1234, VN-215, SE1 — an identifier, so letters\n    #    are spelled and digits read one by one, never as a quantity ──────────\n    | (?<![\\w-])(?P<code_a>[{_VN_UPPER}]{{1,4}})-?(?P<code_n>\\d{{1,6}})(?![\\w-])\n    # ── abbreviation: uppercase acronym, optionally dotted ───────────────────\n    | (?<![\\w.])(?P<abbr>[{_VN_UPPER}][{_VN_UPPER}\\d]+(?:\\.[{_VN_UPPER}][{_VN_UPPER}\\d]*)*)(?![{_VN_LOWER}\\d])\n    # ── at sign: read as a word. Email addresses never reach here — they are\n    #    matched by _PROTECTED_RE and skipped ─────────────────────────────────\n    | (?P<at>@)\n    ''', re.VERBOSE)
_THOUSANDS_RE = re.compile('^\\d{1,3}(?:\\.\\d{3})+$')
_NUM_TRAIL_RE = re.compile('[.,\\s]+$')

def _speak_time(h = None, m = None, s = None):
    out = f'''{_num(h)} giờ'''
# WARNING: Decompyle incomplete


def _replace(match = None):
    '''re.sub callback: expand the match, then keep it a separate word.

    A written form can sit flush against a unit or a letter ("1.250.000đ",
    "5G"); the spoken form must not ("một triệu ...đ"), or the tokenizer sees
    one impossible word. A space is inserted on whichever side abutted a
    letter/digit, and only when the match actually changed.'''
    expanded = _expand_match(match)
    if expanded == match.group(0):
        return expanded
    text = None.string
    before = text[match.start() - 1] if match.start() else ''
    after = text[match.end():match.end() + 1]
    if not before.isalnum() and expanded[:1].isspace():
        expanded = ' ' + expanded
    if not after.isalnum() and expanded[-1:].isspace():
        expanded = expanded + ' '
    return expanded


def _expand_match(match = None):
    pass
# WARNING: Decompyle incomplete


def normalize_vi_text(text = None):
    '''Expand the supported non-standard forms in `text` into spoken Vietnamese.

    Punctuation, casing and every unsupported form are preserved verbatim, and
    URLs/emails are skipped wholesale, so this is safe to run over text that
    has already been punctuation-normalized (webui/text_chunking.py) and over
    text that contains none of these forms at all — it is then a no-op beyond
    Unicode NFC normalization.
    '''
    if not text or text.strip():
        return text
    text = None.normalize('NFC', text)
    out = []
    last = 0
    for protected in _PROTECTED_RE.finditer(text):
        out.append(_SCANNER.sub(_replace, split_camel_case(text[last:protected.start()])))
        out.append(protected.group(0))
        last = protected.end()
    out.append(_SCANNER.sub(_replace, split_camel_case(text[last:])))
    return re.sub('[ \\t]{2,}', ' ', ''.join(out))

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(normalize_vi_text(' '.join(sys.argv[1:])))
        return None
    for sample in ('Ngày 23/8/2024 lúc 15h30, giá là 1.250.000 đồng, tăng 12,5 điểm.', 'Phiên bản v1.2.3 phát hành tháng 8/2024, còn 3/4 số máy chạy 1.2.3.', 'UBND TP.HCM và ATM của NHNN, gửi mail tới abc@gmail.com nhé.', 'Tính 2+3, rồi 10 - 4, rồi 2^10 và 6 * 7 = 42.'):
        print(f'''{sample}\n  -> {normalize_vi_text(sample)}\n''')
    return None

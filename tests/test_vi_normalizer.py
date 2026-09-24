# -*- coding: utf-8 -*-
'''Đối chiếu app.services.voice_engine.zerotts.text_norm.vi_normalizer.

Module này thuần regex + stdlib (không mạng, không model), nên so được từng hàm
với bản đã phát hành trên hàng trăm đầu vào. Đây là nền của việc đọc số/ngày giờ
trong phụ đề lồng tiếng.

Chú ý: ``data/abbreviations.txt`` KHÔNG có trong bản đã cài (tìm cả thư mục
``_internal`` không thấy), nên mọi nhánh tra viết tắt — ``load_abbreviations``,
``_expand_abbreviation`` và nhánh ``abbr``/``pfx`` của ``normalize_vi_text`` —
nổ ``FileNotFoundError`` ở CẢ HAI bên. Test vẫn ghi nhận hành vi đó, không sửa.
'''
from __future__ import annotations

from _parity import RefMissing, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.voice_engine.zerotts.text_norm.vi_normalizer'

NUMBERS = [
    '0', '1', '5', '10', '11', '15', '20', '21', '24', '25', '44', '99', '100',
    '101', '104', '105', '110', '115', '121', '250', '999', '1000', '1001',
    '1010', '1100', '1250', '2024', '9999', '10000', '100000', '1000000',
    '1.250.000', '1.000.000', '12,5', '0,5', '3.14', '2.718', '-7', '+3',
    '-0.5', '007', '0001234', '12,5', '999999999999', '2+3', '5 * 4', '2^10',
    '10 - 4', '1.2.3', '12345678901234567890', '1.000.000.000.000',
    '1.000.000.000.000.000', '1,234', '1.2,3', '', ' ', 'abc', '1a2',
    ',5', '.', '..', '1.', '-', '+', '1e5',
]

DIGITS = ['0', '2024', '12,5', '000', '1 2 3', '', 'abc', '9' * 12]

CHUNKS = [
    ('000', 0), ('001', 0), ('010', 0), ('100', 0), ('101', 0), ('110', 0),
    ('111', 0), ('250', 1), ('007', 2), ('999', 3), ('020', 0), ('021', 0),
    ('024', 0), ('025', 0), ('115', 0), ('100', 1), ('000', 4), ('050', 1),
    ('123', 7), ('123', 6),
]

SPLIT_INPUTS = ['0', '12', '123', '1234', '12345', '123456', '1234567', '',
                '0' * 21]

TIMES = [
    ('15',), ('0',), ('9', None, None), ('9', '0'), ('9', '00'), ('9', '45'),
    ('15', '30', '20'), ('0', '0', '0'), ('23', '59', '59'), ('5', '1'),
    ('15', None, '0'), ('00', '05', '05'),
]

TEXTS = [
    '', '   ', 'Không có số gì ở đây.', 'a', '0', '42',
    'Ngày 23/8/2024 lúc 15h30, giá 1.250.000 tăng 12,5',
    'Ngày 23-8-2024, ngày 23.8.2024, 8/2024, ngày 23/8',
    'mùng 5 Tết, hôm 1/6, sáng 12/3',
    'Phiên bản v1.2, V1.2.3, còn 1.2.3 và 1.2.3.4',
    '3/4 số máy, tỷ lệ 1/2, ngày 3/4, và 3/4, hoặc 3/4',
    'Tính 2+3, rồi 10 - 4, rồi 2^10 và 6 * 7 = 42.',
    '15:30, 15:30:20, 9g45, 15h, 15h30, 8h15p30',
    'Nhiệt độ 38°C và 38 F, 12,5 %, 25%',
    'gửi abc@gmail.com hoặc https://mumu.vn/a?b=1 và www.mumu.vn nhé',
    'Liên hệ user@example.com.vn giá 1.000đ',
    'iPhone 15, MacBook Pro, ChatGPT, YouTube, TikTok, ATP',
    'AB-1234, VN-215, SE1, GPT4, 5G, 4K',
    'quý I, quý II, thế kỷ XX, thứ III',
    'Năm 2024 có 1.000.000 ngày công, 12345678901234567890 số',
    '1.250.000đ, giá 1.250.000 đồng',
    '0, 00, 000, 0000',
    '23/8/2024 23/8/2024 23/8/2024',
    '1.2.3.4.5.6', '12 34 56', '1\t2', '   khoảng   trắng   ',
    'Số 07 và 007 và -0.5 và +3',
    'mm/2024, 13/2024, 0/2024', '23/8/2024.', '23/8/2024, và',
    '@home, a@b, m@', '1.000.000.000.000 và 1.000.000.000.000.000',
    'TP.HCM, UBND, ATM, NHNN',                       # nổ FileNotFoundError (xem docstring)
    '12,5 điểm, 12.5 điểm',
    '100% và 99,99 %',
    '23/08/2024 và 03/04/2024',
]

CAMEL = [
    '', '   ', 'abc', 'ABC', 'a', 'A', 'iPhone', 'eBay', 'MacBook', 'ChatGPT',
    'YouTube', 'TikTok', 'Chiếc', 'ATM', 'GPT4', 'ab12CD', 'aB', 'Ab',
    'OpenAI', 'aiAgent', 'AAa', 'aAA', 'HTTPServer', 'XInterface',
    'HàNội', 'Hà Nội', 'TPHCM', 'iP', 'IP', 'x' * 50, 'a bC dE',
    'abc\tDef', '  lead', 'trail  ',
]


def _cases(values):
    return [((v,), {}) for v in values]


def test_expand_number():
    bad = same_result(DOTTED, 'expand_number', _cases(NUMBERS))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_expand_digit():
    bad = same_result(DOTTED, 'expand_digit', _cases(DIGITS))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_split_chunks():
    bad = same_result(DOTTED, '_split_chunks', _cases(SPLIT_INPUTS))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_speak_chunk():
    bad = same_result(DOTTED, '_speak_chunk', [((a, b), {}) for a, b in CHUNKS])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_apply_sandhi():
    vals = ['mười năm', 'mươi năm', 'mươi bốn', 'mươi một', 'linh bốn',
            'một trăm linh tư', '', 'mười lăm', 'năm mươi lăm năm']
    bad = same_result(DOTTED, '_apply_sandhi', _cases(vals))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_month_and_num_and_letters():
    bad = same_result(DOTTED, '_month', _cases(
        ['1', '01', '4', '04', '10', '11', '12', '0', '00', '13', '']))
    assert not bad, [('_month', c, describe(a), describe(b)) for c, a, b in bad]
    bad = same_result(DOTTED, '_num', _cases(['0', '23', '2024', '8', '00']))
    assert not bad, [('_num', c, describe(a), describe(b)) for c, a, b in bad]
    bad = same_result(DOTTED, 'spell_letters', _cases(
        ['ab', 'ATM', '', 'àđỹ', 'x1', 'Hà Nội']))
    assert not bad, [('spell_letters', c, describe(a), describe(b))
                     for c, a, b in bad]


def test_speak_time():
    bad = same_result(DOTTED, '_speak_time',
                      [((t[0],), {}) if len(t) == 1 else ((t[0], t[1]), {})
                       if len(t) == 2 else ((t[0], t[1], t[2]), {})
                       for t in TIMES])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_split_camel_case():
    bad = same_result(DOTTED, 'split_camel_case', _cases(CAMEL))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_normalize_vi_text():
    bad = same_result(DOTTED, 'normalize_vi_text', _cases(TEXTS))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_abbreviation_data_missing():
    """Bản đã cài không kèm data/abbreviations.txt -> cả hai cùng thiếu file.

    Test ghi lại đúng hành vi đó (FileNotFoundError) thay vì đoán bảng viết tắt.
    """
    ref = ref_module(DOTTED)
    rep = repo_module(DOTTED)
    for fn in ('load_abbreviations', '_expand_abbreviation'):
        args = () if fn == 'load_abbreviations' else ('ATM',)
        try:
            getattr(ref, fn)(*args)
            raise AssertionError(f'bản gốc {fn} không nổ như mong đợi')
        except FileNotFoundError:
            pass
        try:
            getattr(rep, fn)(*args)
            raise AssertionError(f'repo {fn} không nổ FileNotFoundError')
        except FileNotFoundError:
            pass
    bad = same_result(DOTTED, '_expand_abbreviation', _cases(
        ['ATM', 'TP.HCM', 'TPHCM', 'T.Ư', 'UBND', 'XZQ', 'A', '']))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_module_tables_match():
    """Hằng số cấp module (bảng số, đơn vị, cue) phải khớp từng ký tự."""
    ref = ref_module(DOTTED)
    rep = repo_module(DOTTED)
    for name in ('_DIGIT', '_UNIT_SINGLE', '_UNIT_TRIPLE', '_OP_WORDS', '_ROMAN',
                 '_ROMAN_CUES', '_PREFIX_ABBR', '_DATE_CUES', '_VN_LOWER',
                 '_VN_UPPER', '__all__'):
        a, b = getattr(rep, name), getattr(ref, name)
        assert a == b, f'{name}: {a!r} != {b!r}'


def test_regex_patterns_match():
    ref = ref_module(DOTTED)
    rep = repo_module(DOTTED)
    for name in ('_PROTECTED_RE', '_SCANNER', '_THOUSANDS_RE', '_NUM_TRAIL_RE'):
        a, b = getattr(rep, name), getattr(ref, name)
        assert a.pattern == b.pattern, f'{name} pattern khác bản đã phát hành'
        assert a.flags == b.flags, f'{name} flags {a.flags} != {b.flags}'


def test_bytecode_identical():
    """Mọi code object trong .py phải trùng .pyc gốc — không còn chỗ đoán."""
    import marshal
    from pathlib import Path

    internal = Path(r'C:\Users\Administrator\MumuStudioPro\{app}\_internal')
    rel = DOTTED.replace('.', '/')
    pyc = internal / (rel + '.pyc')
    if not pyc.is_file():
        raise RefMissing(f'không có {pyc}')
    ref = marshal.loads(pyc.read_bytes()[16:])
    src = Path(__file__).resolve().parent.parent / (rel + '.py')
    mine = compile(src.read_text(encoding='utf-8'), str(src), 'exec')

    def flat(code, prefix='', out=None):
        out = {} if out is None else out
        key = f'{prefix}{code.co_name}'
        out[key] = (code.co_code, tuple(code.co_names), tuple(code.co_varnames),
                    code.co_argcount, code.co_flags,
                    tuple(_const(c) for c in code.co_consts))
        for c in code.co_consts:
            if hasattr(c, 'co_code'):
                flat(c, key + '.', out)
        return out

    a, b = flat(mine), flat(ref)
    assert set(a) == set(b), f'tập hàm khác nhau: {set(b) ^ set(a)}'
    for name in sorted(b):
        assert a[name] == b[name], f'{name} không trùng bytecode gốc'
    assert len(a) >= 20, len(a)


def _const(c):
    return ('code', c.co_name) if hasattr(c, 'co_code') else repr(c)

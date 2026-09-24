# -*- coding: utf-8 -*-
'''Đối chiếu app.services.translation_memory với bản đã phát hành.

Phần glossary/memory ở đây là logic thuần (chuẩn hoá văn bản, tách dòng ``a=b``,
khoá cache SHA-256) nên dùng same_result trực tiếp. Phần đọc/ghi file thì trỏ
GLOSSARY_PATH / TRANSLATION_MEMORY_PATH của cả hai bản vào thư mục tạm.
'''
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.translation_memory'

TEXT_EDGE = [
    '', '   ', 'a', 'hai\ncâu', 'thừa  khoảng   trắng\t', '\n\n', '  cắt  ',
    'không\ndown\nhàng', 'tab\tkèm\nxuống dòng', '  a  b  ',
    'dấu câu, chấm: phẩy;', 'tiếng Việt có dấu ệ ă ô', '‏unicode ẩn​',
    'a' * 500, '\r\nWindows newline\r\n', 'mixed \r\n của \n mọi', '   \\n   ']

GLOSSARY_TEXT = [
    '', '   ', '# chỉ comment', 'khong-co-separator', 'source=', '=target',
    'a=b', 'a => b', 'a=>b', '  k  =  v  ', '# comment\na=b',
    'a=b=c', 'a=>b=>c', 'lựu=apple\nhành=onion', 'a =b', 'a= b',
    'trùng=x1\ntrùng=x2', 'a=', '=', '=>', '==', '=a=b',
    'nguồn\nkhác dòng', 'a=b\n\n#c\nx=y', '\n', 'a= b ', 'x=1',
    'emoji=😀', 'viet=tiếng Việt', 'a=>', 'a = > b']

GLOSSARIES = [
    {}, {'a': 'b'}, {'a': 'b', 'c': 'd'}, {'z': '1', 'aa': '2'},
    {'rỗng': ''}, {'  spaced  ': '  value  '}, {'ab': 'X', 'a': 'Y'},
    {'một': 'hai', 'bốn': 'năm', 'sáu': 'bảy'},
    {'x': 'ä', 'y': 'ế'}, {'k': 'v'}, {'aa': 'A', 'a': 'B', 'aaa': 'C'}]

KEY_TEXTS = ['', 'a', 'hai\ndòng', '  thừa  trắng  ', 'tiếng Việt', 'mix\r\nnl']

KEY_LANGS = [('vi', 'en'), ('', ''), (None, None), (' auto ', ' Viet '),
             ('en', 'vi'), ('AUTO', 'VIETNAMESE')]


def _cases(values):
    return [((v,), {}) for v in values]


def test_normalize_source_text():
    bad = same_result(DOTTED, 'normalize_source_text', _cases(TEXT_EDGE))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref = ref_module(DOTTED)
    assert ref.normalize_source_text('  a   b\t\nc  ') == 'a b c'
    assert ref.normalize_source_text(None) == ''
    assert ref.normalize_source_text('') == ''


def test_parse_glossary_text():
    bad = same_result(DOTTED, 'parse_glossary_text', _cases(GLOSSARY_TEXT))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref = ref_module(DOTTED)
    assert ref.parse_glossary_text('a=b\nc => d\n#x=y\nrasad') == \
        {'a': 'b', 'c': 'd'}
    assert ref.parse_glossary_text('trùng=x1\ntrùng=x2') == {'trùng': 'x2'}
    assert ref.parse_glossary_text('a=b=c') == {'a': 'b=c'}
    assert ref.parse_glossary_text(None) == {}


def test_glossary_text_roundtrip():
    bad = same_result(DOTTED, 'glossary_to_text', [((g,), {}) for g in GLOSSARIES])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for g in GLOSSARIES:
        assert rep.parse_glossary_text(rep.glossary_to_text(g)) == \
            ref.parse_glossary_text(ref.glossary_to_text(g)), g
    assert rep.glossary_to_text({}) == ref.glossary_to_text({}) == ''
    assert ref.glossary_to_text({'a': 'b', 'c': 'd'}) == 'a=b\nc=d'


def test_apply_glossary():
    texts = TEXT_EDGE + ['thay a bằng b', 'aa và a và aaa', 'không khớp gì',
                         'tiếng Việt có dấu', 'lựu và hành', 'a=b']
    bad = []
    for g in GLOSSARIES:
        bad += same_result(DOTTED, 'apply_glossary',
                           [((t, g), {}) for t in texts])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref = ref_module(DOTTED)
    # từ dài nhất thắng: 'aa' phải thay trước 'a'
    assert ref.apply_glossary('aa', {'a': 'X', 'aa': 'Y'}) == 'Y'
    assert ref.apply_glossary(None, {'a': 'b'}) == ''
    assert ref.apply_glossary('abc', {}) == 'abc'


def test_glossary_fingerprint():
    bad = same_result(DOTTED, 'glossary_fingerprint', [((g,), {}) for g in GLOSSARIES])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref = ref_module(DOTTED)
    assert ref.glossary_fingerprint({'a': '1', 'b': '2'}) == \
        ref.glossary_fingerprint({'b': '2', 'a': '1'}), 'phải không phụ thuộc thứ tự'
    assert ref.glossary_fingerprint({'a': '1'}) != ref.glossary_fingerprint({'a': '2'})
    assert len(ref.glossary_fingerprint({})) == 64


def test_memory_key():
    bad = []
    for g in GLOSSARIES[:5]:
        for src, tgt in KEY_LANGS:
            for t in KEY_TEXTS:
                bad += same_result(DOTTED, 'memory_key',
                                   [((t,), {'source_lang': src, 'target_lang': tgt,
                                            'glossary': g})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    ref = ref_module(DOTTED)
    kw = dict(source_lang='vi', target_lang='en', glossary={'a': 'b'})
    assert ref.memory_key('hai   dòng', **kw) == ref.memory_key('hai dòng', **kw)
    assert ref.memory_key('a', **kw) != ref.memory_key('b', **kw)
    assert ref.memory_key('a', source_lang='vi', target_lang='en',
                          glossary={'a': 'b'}) == ref.memory_key(
        'a', source_lang='vi', target_lang='en', glossary={'a': 'b'})
    # key trống -> dùng mặc định auto-detect / Vietnamese
    assert ref.memory_key('a', source_lang='', target_lang='', glossary={}) == \
        ref.memory_key('a', source_lang='auto-detect', target_lang='Vietnamese',
                       glossary={})


def test_glossary_file_roundtrip():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        home = Path(tempfile.mkdtemp())
        mod.GLOSSARY_PATH = home / 'translation_glossary.json'
        assert mod.load_glossary() == {}, 'chưa có file phải trả {}'
        mod.save_glossary({'a': 'b', '  ': 'x', 'c': '  ', ' d ': ' e '})
        written = json.loads(mod.GLOSSARY_PATH.read_text(encoding='utf-8'))
        out[label] = (written['version'], sorted(written['pairs'].items()),
                      mod.load_glossary())
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert out['ref'][0] == 1, out['ref']
    # key/value đều được strip; cặp có vế rỗng bị loại hẳn
    assert out['ref'][1] == [('a', 'b'), ('d', 'e')], out['ref']
    assert out['ref'][2] == {'a': 'b', 'd': 'e'}, out['ref']


def test_glossary_loader_accepts_legacy_shapes():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    shapes = [
        {'pairs': {'a': 'b'}},
        {'a': 'b'},
        {'pairs': [{'x': 1}]},
        {'pairs': 'chuoi'},
        [],
        'chuoi',
        5,
        {'pairs': {'a': 'b', 'c': ' ', ' d': 'e'}},
        {}]
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        home = Path(tempfile.mkdtemp())
        mod.GLOSSARY_PATH = home / 'g.json'
        rows = []
        for shape in shapes:
            mod.GLOSSARY_PATH.write_text(json.dumps(shape, ensure_ascii=False),
                                         encoding='utf-8')
            try:
                rows.append(('ok', mod.load_glossary()))
            except Exception as exc:
                rows.append(('err', type(exc).__name__))
        mod.GLOSSARY_PATH.write_text('{khong phai json', encoding='utf-8')
        try:
            rows.append(('ok', mod.load_glossary()))
        except Exception as exc:
            rows.append(('err', type(exc).__name__))
        mod.GLOSSARY_PATH = home / 'khong-co' / 'g.json'
        try:
            rows.append(('ok', mod.load_glossary()))
        except Exception as exc:
            rows.append(('err', type(exc).__name__))
        out[label] = rows
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert out['ref'][0] == ('ok', {'a': 'b'}), out['ref']
    assert out['ref'][1] == ('ok', {'a': 'b'}), out['ref']
    assert out['ref'][-2] == ('ok', {}), out['ref']       # JSON hỏng -> {}
    assert out['ref'][-1] == ('ok', {}), out['ref']       # không có file -> {}


def test_translation_memory_roundtrip_and_trim():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        home = Path(tempfile.mkdtemp())
        mod.TRANSLATION_CACHE_ROOT = home / 'translation_cache'
        mod.TRANSLATION_MEMORY_PATH = mod.TRANSLATION_CACHE_ROOT / 'memory.json'
        assert mod.load_translation_memory() == {}
        entries = {str(i): f'dich {i}' for i in range(5)}
        mod.save_translation_memory(entries)
        rows = [sorted(mod.load_translation_memory().items()),
                sorted(json.loads(mod.TRANSLATION_MEMORY_PATH.read_text(
                    encoding='utf-8')).keys())]
        # bộ nhớ phải được cắt còn _MAX_MEMORY_ENTRIES phần tử cuối
        big = {str(i): 'x' for i in range(mod._MAX_MEMORY_ENTRIES + 3)}
        mod.save_translation_memory(big)
        rows.append(len(mod.load_translation_memory()))
        rows.append(sorted(mod.load_translation_memory(), key=int)[:1] +
                    sorted(mod.load_translation_memory(), key=int)[-1:])
        shapes = ([], 'chuoi', {'entries': 'x'}, {'entries': {'a': ' ', 'b': 'c'}},
                  {'a': 'b'}, {})
        for shape in shapes:
            mod.TRANSLATION_MEMORY_PATH.write_text(json.dumps(shape, ensure_ascii=False),
                                                   encoding='utf-8')
            rows.append(sorted(mod.load_translation_memory().items()))
        mod.TRANSLATION_MEMORY_PATH.write_text('rong', encoding='utf-8')
        rows.append(sorted(mod.load_translation_memory().items()))
        out[label] = rows
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert out['ref'][1] == ['entries', 'version'], out['ref'][1]
    assert out['ref'][2] == ref._MAX_MEMORY_ENTRIES, out['ref'][2]
    assert out['ref'][3] == ['3', '20002'], out['ref'][3]
    # 6 hình dạng payload: list/str -> {}, value rỗng bị loại, thiếu 'entries' -> {}
    assert out['ref'][4] == [] and out['ref'][5] == [] and out['ref'][6] == [], \
        out['ref'][4:7]
    assert out['ref'][7] == [('b', 'c')], out['ref'][7]
    assert out['ref'][8] == [] and out['ref'][9] == [], out['ref'][8:10]
    assert out['ref'][10] == [], 'file không phải JSON phải trả {}'


def test_save_translation_memory_order_is_insertion():
    '''trimmed lấy N phần tử CUỐI theo thứ tự chèn -> thứ tự key có ý nghĩa.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    rows = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        home = Path(tempfile.mkdtemp())
        mod.TRANSLATION_CACHE_ROOT = home
        mod.TRANSLATION_MEMORY_PATH = home / 'memory.json'
        mod._MAX_MEMORY_ENTRIES = 2
        mod.save_translation_memory({'a': '1', 'b': '2', 'c': '3'})
        rows[label] = sorted(mod.load_translation_memory().items())
    assert rows['repo'] == rows['ref'] == [('b', '2'), ('c', '3')], rows

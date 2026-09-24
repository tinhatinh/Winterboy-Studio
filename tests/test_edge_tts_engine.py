# -*- coding: utf-8 -*-
'''Đối chiếu app.services.edge_tts_engine với bản đã phát hành.

Không có bất kỳ gói tin mạng nào: mọi lời gọi Edge TTS đều đi qua module ``edge_tts``
giả trong sys.modules (``Communicate`` tự ghi file, ``list_voices`` trả dữ liệu cố định).
Nhờ vậy vẫn so được cả *chuỗi tham số* mà repo và bản phát hành truyền cho nhà cung cấp.

Tầng 1: ``test_bytecode_matches_pyc`` — bytecode repo phải trùng 100% .pyc gốc.
Tầng 2: ``same_result`` cho hàm thuần + ``_both`` cho hàm tổng hợp (offline).
'''
from __future__ import annotations

import contextlib
import dis
import marshal
import os
import sys
import tempfile
import types
from pathlib import Path

from _parity import INTERNAL, REPO, RefMissing, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.edge_tts_engine'
SRC = REPO / 'app' / 'services' / 'edge_tts_engine.py'
PYC = INTERNAL / 'app' / 'services' / 'edge_tts_engine.pyc'

_IGNORED_OPS = {'CACHE', 'RESUME', 'NOP'}
_JUMPS = {'FOR_ITER', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE', 'POP_JUMP_IF_NONE',
          'POP_JUMP_IF_NOT_NONE', 'JUMP_FORWARD', 'JUMP_BACKWARD', 'SEND',
          'JUMP_BACKWARD_NO_INTERRUPT'}


# ---------------------------------------------------------------- bytecode ---
def _fp(code):
    ops = []
    for i in dis.get_instructions(code):
        if i.opname in _IGNORED_OPS:
            continue
        a = i.arg
        if hasattr(a, 'co_code'):
            a = ('CODE', ) + _fp(a)
        elif isinstance(a, tuple):
            a = tuple(('CODE', ) + _fp(x) if hasattr(x, 'co_code') else x for x in a)
        elif isinstance(a, (set, frozenset)):
            a = ('set', tuple(sorted(map(repr, a))))
        ops.append((i.opname, None if i.opname in _JUMPS else a))
    return (code.co_name, code.co_argcount, code.co_kwonlyargcount,
            code.co_posonlyargcount, code.co_nlocals, code.co_stacksize, code.co_flags,
            code.co_varnames, code.co_cellvars, code.co_freevars, tuple(ops))


def _all_codes(code, out=None):
    out = out if out is not None else {}
    for c in code.co_consts:
        if hasattr(c, 'co_code'):
            out.setdefault(c.co_name, []).append(c)
            _all_codes(c, out)
    return out


def _first_diff(xa, xb):
    n = 0
    while n < min(len(xa), len(xb)) and xa[n] == xb[n]:
        n += 1
    return n, xa[n:n + 2], xb[n:n + 2]


def test_bytecode_matches_pyc():
    '''Mỗi hàm trong repo phải sinh bytecode giống hệt .pyc đã phát hành.'''
    if not PYC.is_file():
        raise RefMissing(f'không có {PYC}')
    ref = marshal.loads(PYC.read_bytes()[16:])
    rep = compile(SRC.read_text(encoding='utf-8'), str(SRC), 'exec')
    fi, ri = _all_codes(ref), _all_codes(rep)
    bad = []
    if _fp(ref) != _fp(rep):
        bad.append(('<module>', _first_diff(_fp(rep)[-1], _fp(ref)[-1])))
    for name in sorted(set(fi) | set(ri)):
        if len(fi.get(name, [])) != len(ri.get(name, [])):
            bad.append((name, f'số lần xuất hiện repo={len(ri.get(name, []))} '
                              f'ref={len(fi.get(name, []))}'))
            continue
        for k, (a, b) in enumerate(zip(ri.get(name, []), fi.get(name, []))):
            if _fp(a) != _fp(b):
                bad.append((f'{name}#{k}', _first_diff(_fp(a)[-1], _fp(b)[-1])))
    assert not bad, bad


# ------------------------------------------------------------- module data ---
def test_module_constants_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in ('DEFAULT_VOICE', 'VI_VOICES', 'VOICE_LABELS', 'EDGE_ALL_VOICES',
                 'EDGE_CURATED_LABELS', '_RATE_RE'):
        a, b = getattr(rep, name), getattr(ref, name)
        if name == '_RATE_RE':
            assert (a.pattern, a.flags) == (b.pattern, b.flags), name
        else:
            assert a == b, f'{name}: {a!r} != {b!r}'
    assert len(ref.EDGE_ALL_VOICES) == len(ref.EDGE_CURATED_LABELS) == len(ref.VOICE_LABELS)
    assert ref.EDGE_CURATED_LABELS[0] == 'vi-VN-HoaiMyNeural|Nữ - Hoài My (Tiếng Việt)'


# ------------------------------------------------------------------ helpers ---
@contextlib.contextmanager
def fake_edge_tts(save_side_effect=None, voices=None, fail_first=0):
    '''edge_tts giả: gọi được mà không phát gói tin nào.'''
    calls = []
    state = {'left': fail_first}

    class Communicate:
        def __init__(self, text, voice, rate=None, pitch=None):
            self.rec = (text, voice, rate, pitch)

        async def save(self, path):
            calls.append(self.rec)
            if state['left'] > 0:
                state['left'] -= 1
                raise RuntimeError('NoAudioReceived')
            if save_side_effect:
                raise save_side_effect
            Path(path).write_bytes(b'ID3' + b'\x00' * 300)

    async def list_voices():
        return list(voices or [])

    mod = types.ModuleType('edge_tts')
    mod.Communicate = Communicate
    mod.list_voices = list_voices
    old = sys.modules.get('edge_tts', False)
    sys.modules['edge_tts'] = mod
    try:
        yield calls
    finally:
        if old is False:
            sys.modules.pop('edge_tts', None)
        else:
            sys.modules['edge_tts'] = old


@contextlib.contextmanager
def fake_capcut(speakable=True):
    made = []

    def _make(path, duration_s=0.2):
        made.append((str(path), duration_s))
        Path(path).write_bytes(b'RIFF' + b'\x00' * 200)
        return Path(path)

    mod = types.SimpleNamespace(is_speakable_text=lambda t: speakable,
                                _make_silence_audio=_make)
    old = sys.modules.get('app.services.capcut_tts_engine', False)
    sys.modules['app.services.capcut_tts_engine'] = mod
    try:
        yield made
    finally:
        if old is False:
            sys.modules.pop('app.services.capcut_tts_engine', None)
        else:
            sys.modules['app.services.capcut_tts_engine'] = old


@contextlib.contextmanager
def tmp_cwd():
    tmp = Path(tempfile.mkdtemp(prefix='edge_', dir=str(REPO / 'output')))
    cwd = os.getcwd()
    os.chdir(tmp)
    try:
        yield tmp
    finally:
        os.chdir(cwd)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def _both(dotted, fn, *args, **kwargs):
    '''Gọi cùng một hàm trên repo và bản phát hành, trả (kết_quả, log_lệnh_gọi).'''
    out = {}
    for tag, mod in (('repo', repo_module(dotted)), ('ref', ref_module(dotted))):
        try:
            res = getattr(mod, fn)(*args, **kwargs)
            out[tag] = ('ok', repr(res))
        except Exception as exc:
            out[tag] = ('err', type(exc).__name__, str(exc))
    return out


# ---------------------------------------------------------------- pure fns ---
VOICE_INPUTS = [
    None, '', '   ', 'vi-VN-HoaiMyNeural', 'vi-VN-NamMinhNeural',
    'vi-VN-HoaiMyNeural|Nữ - Hoài My (Tiếng Việt)', '  vi-VN-NamMinhNeural |x  ',
    'Nữ - Hoài My', 'hoaimy', 'Hoài My', 'HOẠT NGÔN', 'hoat ngon',
    'Nam - Minh', 'namminh', 'Tự Tin', 'tu tin', 'en-US-AriaNeural',
    'zh-CN-XiaoxiaoNeural', 'fr-FR-DeniseNeural', 'xx-YY-TestNeural',
    'Some-Voice', 'plainword', 'Neural', 'neural', 'a-neural-b',
    'en-US-AndrewMultilingualNeural|Nam - Andrew', 'MAICHI', 'maichi',
    'Hiếu', 'Nữ - Cô Gái Hoạt Ngôn', '|', 'a|b|c', 'vi-VN-HoaiMyNeural|',
]

SPEED_INPUTS = [
    None, '', 0, 1, 1.0, 0.8, 1.2, 0.5, 0.49, 2.0, 2.5, -1, 0.999, 1.005, 1.004,
    '0.8', '1.2', '1', '2', 'abc', '0.05', '1e0', 1.15, 1.151, 1.149, 0.51,
    1.999, float('nan'), True, [1], {}, 1.0 / 3, 3.0, 1.05, 0.95,
]

TEXT_INPUTS = [
    None, '', '   ', 'Xin chào các bạn.',
    'Một\rđoạn\ncó\tnhiều dòng',
    '<speak>Xin chào <break time="500ms"/></speak>',
    '{tho} {day} là placeholder',
    'Quá nhiều dấu chấm..............',
    'Héllo\u200bworld\ufeff!",' + '\u200d',
    '!!!???。。。！？',
    'a' * 500,
    '  khoảng trắng thừa   ở   giữa  ',
    '<b>đậm</b> và <i>nghiêng</i>',
    '{{nest}}{x}',
    '...</i>',
    '\n\n\n',
    '\t\t  \r\r  ',
    'Trộn <tag> với {ph} và ... hết',
    'tiếng việt có dấu, có số 123 và ký tự !@#$%^&*()',
    'emoji 😀 vẫn còn',
    '<a><b>closed</b></a>',
    '{} {} {}',
    'no-separator-here',
    'Một đoạn văn rất dài để kiểm tra xem có bị cắt hay thay đổi khoảng trắng không nhé.',
]


def test_normalize_voice():
    bad = same_result(DOTTED, 'normalize_voice', [((v,), {}) for v in VOICE_INPUTS])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_speed_to_edge_rate():
    cases = [((v,), {}) for v in SPEED_INPUTS]
    bad = same_result(DOTTED, 'speed_to_edge_rate', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_sanitize_edge_text():
    cases = [((v,), {}) for v in TEXT_INPUTS]
    cases += [((t * 3,), {}) for t in ('abc.', '<i>x</i>', '{a}')]
    bad = same_result(DOTTED, 'sanitize_edge_text', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_list_vietnamese_voices():
    bad = same_result(DOTTED, 'list_vietnamese_voices', [((), {})])
    assert not bad
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    rep.list_vietnamese_voices().append('x')
    assert 'x' not in rep.VI_VOICES, 'phải trả bản sao'
    assert ref.list_vietnamese_voices() == ref.VI_VOICES


def test_edge_tts_available_blocked():
    with contextlib.ExitStack() as st:
        st.enter_context(_block('edge_tts'))
        bad = same_result(DOTTED, 'edge_tts_available', [((), {})])
    assert not bad, bad
    assert repo_module(DOTTED).edge_tts_available() is False


def test_edge_tts_available_with_fake():
    with fake_edge_tts():
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        assert rep.edge_tts_available() is True
        assert ref.edge_tts_available() is True


@contextlib.contextmanager
def _block(*names):
    saved = {n: sys.modules.get(n, False) for n in names}
    for n in names:
        sys.modules[n] = None
    try:
        yield
    finally:
        for n, v in saved.items():
            if v is False:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = v


def test_list_edge_tts_options_and_all_voices():
    '''Cache file nằm trong cwd tạm -> cả hai bên đọc đúng một dữ liệu.'''
    import json
    with tmp_cwd() as tmp:
        cache_file = tmp / 'output' / 'edge_voices_cache.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        def write_cache(payload):
            cache_file.write_text(json.dumps(payload), encoding='utf-8')

        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        assert rep.list_edge_tts_options() == ref.list_edge_tts_options()
        assert rep.list_edge_tts_options() == rep.EDGE_CURATED_LABELS
        assert rep.list_all_edge_voices() == ref.list_all_edge_voices()
        assert rep.list_all_edge_voices()[0] == ('vi-VN-HoaiMyNeural',
                                                 'Nữ - Hoài My (Tiếng Việt)')
        # cache ngắn hơn danh mục tuyển chọn -> vẫn phải dùng tuyển chọn
        write_cache(['a|A'])
        assert rep.list_edge_tts_options() == ref.list_edge_tts_options()
        assert rep.list_edge_tts_options() == rep.EDGE_CURATED_LABELS
        # cache dài hơn -> được ưu tiên
        big = ['zz-ZZ-Voice|Zz'] * (len(rep.EDGE_CURATED_LABELS) + 1)
        write_cache(big)
        assert rep.list_edge_tts_options() == ref.list_edge_tts_options() == big
        assert rep.list_all_edge_voices() == ref.list_all_edge_voices()
        assert rep.list_all_edge_voices()[0] == ('zz-ZZ-Voice', 'Zz')
        # cache rác (không phải list) -> fallback
        cache_file.write_text('{"k": 1}', encoding='utf-8')
        assert rep.list_edge_tts_options() == rep.EDGE_CURATED_LABELS
        # option không có '|' -> nhân đôi thành (opt, opt)
        n = len(rep.EDGE_CURATED_LABELS) + 1
        write_cache(['  SoloVoice  '] * n)
        assert rep.list_all_edge_voices() == ref.list_all_edge_voices()
        assert rep.list_all_edge_voices() == [('SoloVoice', 'SoloVoice')] * n


def test_fetch_all_edge_voices_online_offline():
    '''Dùng edge_tts giả: vẫn chạy hết phần định dạng nhãn + ghi cache, không mạng.'''
    voices = [
        {'ShortName': 'vi-VN-NamMinhNeural', 'Locale': 'vi-VN', 'Gender': 'Male',
         'FriendlyName': 'Nam Minh'},
        {'ShortName': 'vi-VN-HoaiMyNeural', 'Locale': 'vi-VN', 'Gender': 'Female',
         'FriendlyName': 'Hoai My'},
        {'ShortName': 'en-US-AriaNeural', 'Locale': 'en-US', 'Gender': 'Female',
         'FriendlyName': 'Aria Multi'},
        {'ShortName': 'zh-CN-XiaoxiaoNeural', 'Locale': 'zh-CN', 'Gender': 'Female',
         'FriendlyName': 'Xiaoxiao'},
        {'ShortName': 'ja-JP-NanamiNeural', 'Locale': 'ja-JP', 'Gender': 'Female',
         'FriendlyName': 'Nanami'},
        {'ShortName': 'ko-KR-SunHiNeural', 'Locale': 'ko-KR', 'Gender': 'Female',
         'FriendlyName': 'SunHi'},
        {'ShortName': 'th-TH-NiwatNeural', 'Locale': 'th-TH', 'Gender': 'Male',
         'FriendlyName': 'Niwat'},
        {'ShortName': 'fr-CA-EveNeural', 'Locale': 'fr-CA', 'Gender': 'Female',
         'FriendlyName': 'Eve'},
        {'ShortName': '', 'Locale': 'xx', 'Gender': 'Female', 'FriendlyName': 'rỗng'},
        {'Locale': 'de-DE', 'Gender': 'Male', 'FriendlyName': 'khong co ShortName'},
        {'ShortName': 'de-DE-KlausNeural', 'Locale': 'de-DE', 'Gender': 'Male',
         'FriendlyName': 'Klaus'},
    ]
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        with fake_edge_tts(voices=voices):
            a = rep.fetch_all_edge_voices_online()
            b = ref.fetch_all_edge_voices_online()
        assert a == b, (a, b)
        assert a[0].startswith('vi-VN-'), a[:3]
        assert 'de-DE-KlausNeural|Nam - Klaus (fr-CA)' not in a
        assert any(x == 'de-DE-KlausNeural|Nam - Klaus (Deutschland)' or
                   x.startswith('de-DE-KlausNeural|Nam - Klaus (') for x in a), a
        assert not any('|' in x and x.split('|')[0] == '' for x in a)
        assert (tmp / 'output' / 'edge_voices_cache.json').is_file()
        # đọc lại: cache chỉ có vài mục (< len(EDGE_ALL_VOICES)) -> cả hai cùng fallback
        with fake_edge_tts(voices=[]):
            assert rep.fetch_all_edge_voices_online() == ref.fetch_all_edge_voices_online()
        # force_refresh -> gọi lại provider
        with fake_edge_tts(voices=voices):
            assert rep.fetch_all_edge_voices_online(True) == \
                   ref.fetch_all_edge_voices_online(True)
        # voices rỗng -> fallback curated
        empty = tmp / 'output' / 'edge_voices_cache.json'
        empty.unlink()
        with fake_edge_tts(voices=[]):
            assert rep.fetch_all_edge_voices_online() == rep.EDGE_CURATED_LABELS
        # provider nổ -> fallback curated, không tung lỗi ra ngoài
        cache = tmp / 'output' / 'edge_voices_cache.json'
        if cache.is_file():
            cache.unlink()
        with fake_edge_tts(voices=voices):
            for tag, mod in (('repo', rep), ('ref', ref)):
                old = mod._run_coro
                mod._run_coro = lambda coro: (_ for _ in ()).throw(RuntimeError('boom'))
                try:
                    assert mod.fetch_all_edge_voices_online(True) == mod.EDGE_CURATED_LABELS
                finally:
                    mod._run_coro = old
        # edge_tts không cài sẵn -> ModuleNotFoundError (đúng như bản phát hành,
        # vì 'import edge_tts' nằm ngoài mọi try)
        with _block('edge_tts'):
            for mod in (rep, ref):
                try:
                    mod.fetch_all_edge_voices_online()
                except ModuleNotFoundError:
                    pass
                else:
                    raise AssertionError('phải lỗi ModuleNotFoundError')


def test_make_tts_func_offline():
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        import inspect
        assert str(inspect.signature(rep.make_tts_func)) == str(inspect.signature(ref.make_tts_func))
        fn_r = rep.make_tts_func('Hoài My', 1.2)
        fn_f = ref.make_tts_func('Hoài My', 1.2)
        assert callable(fn_r) and callable(fn_f)
        with fake_edge_tts() as calls, fake_capcut() as made:
            out_r = fn_r('Xin chào.', tmp / 'r.mp3')
            rec_r = list(calls); calls.clear()
            out_f = fn_f('Xin chào.', tmp / 'f.mp3')
            rec_f = list(calls)
        assert rec_r == rec_f, (rec_r, rec_f)
        assert rec_r[0][1] == 'vi-VN-HoaiMyNeural' and rec_r[0][2] == '+20%'
        assert Path(out_r).name == 'r.mp3'


def test_edge_tts_generate_rate_and_voice():
    '''Chuỗi (text, voice, rate, pitch) gửi nhà cung cấp phải giống hệt bản phát hành.'''
    cases = [
        ('Xin chào các bạn.', 'vi-VN-HoaiMyNeural', '+0%'),
        ('Xin chào các bạn.', 'Hoài My', 1.2),
        ('Xin chào các bạn.', 'Nam Minh', 0.8),
        ('Xin chào các bạn.', 'en-US-AriaNeural', '1'),
        ('Xin chào các bạn.', 'zh-CN-XiaoxiaoNeural', '0.75'),
        ('Xin chào các bạn.', None, None),
        ('Xin chào các bạn.', '', ''),
        ('Xin chào các bạn.', 'xx-YY', '+15%'),
        ('Xin chào các bạn.', 'xx-YY', 2.5),
        ('Xin chào các bạn.', 'xx-YY', 0.1),
        ('Xin chào các bạn.', 'xx-YY', 'abc'),
        ('Xin chào các bạn.', 'xx-YY', 1.005),
    ]
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        for k, (text, voice, rate) in enumerate(cases):
            with fake_edge_tts() as calls, fake_capcut() as made:
                out_r = rep.edge_tts_generate(text, tmp / f'r{k}.mp3', voice=voice, rate=rate)
                rec_r = list(calls); calls.clear()
                out_f = ref.edge_tts_generate(text, tmp / f'f{k}.mp3', voice=voice, rate=rate)
                rec_f = list(calls)
            assert rec_r == rec_f, (voice, rate, rec_r, rec_f)
            assert Path(out_r).name == f'r{k}.mp3'
        # text không phát âm được -> im lặng, không gọi provider
        with fake_edge_tts() as calls, fake_capcut(speakable=False) as made:
            out_r = rep.edge_tts_generate('...', tmp / 'silence.mp3')
            n_r = len(made), len(calls)
            made.clear()
            out_f = ref.edge_tts_generate('...', tmp / 'silence2.mp3')
            assert n_r == (len(made), len(calls)), (n_r, made, calls)
        assert calls == []


def test_synthesize_async_validation_offline():
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        import asyncio
        for mod, tag in ((rep, 'repo'), (ref, 'ref')):
            pass
        cases = [('',), ('   ',), ('\u200b\ufeff',), ('<i></i>',), ('{a}{b}',)]
        for (t,) in cases:
            r = _both(DOTTED, '_noop')  # placeholder giữ cấu trúc, gọi trực tiếp bên dưới
            with fake_edge_tts(), fake_capcut():
                got = {}
                for tag, mod in (('repo', rep), ('ref', ref)):
                    try:
                        got[tag] = ('ok', str(asyncio.run(
                            mod._synthesize_async(t, tmp / f'{tag}.mp3',
                                                  voice='vi-VN-HoaiMyNeural', rate='+0%'))))
                    except Exception as exc:
                        got[tag] = ('err', type(exc).__name__, str(exc))
                assert got['repo'] == got['ref'], (t, got)


def test_synthesize_async_retry_and_failure_offline():
    with tmp_cwd() as tmp:
        import asyncio
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        # lần 1 hỏng, lần 2 thành công -> phải retry đúng số lần và cùng tham số
        results = {}
        for tag, mod in (('repo', rep), ('ref', ref)):
            with fake_edge_tts(fail_first=1) as calls, fake_capcut():
                got = asyncio.run(mod._synthesize_async(
                    'Xin chào.', tmp / f'{tag}.mp3', voice='vi-VN-NamMinhNeural',
                    rate='+30%', max_retries=3))
                results[tag] = (str(got).replace(tag, 'X'), list(calls))
        assert results['repo'][1] == results['ref'][1], results
        assert len(results['repo'][1]) == 2
        assert results['repo'][1][0][:3] == ('Xin chào.', 'vi-VN-NamMinhNeural', '+30%')
        assert results['repo'][1][1][2] == '+0%', 'lần thử 2 phải hạ rate về +0%'
        # thất bại hoàn toàn -> RuntimeError cùng thông báo
        errs = {}
        for tag, mod in (('repo', rep), ('ref', ref)):
            with fake_edge_tts(fail_first=5) as calls, fake_capcut():
                try:
                    asyncio.run(mod._synthesize_async(
                        'Xin chào.', tmp / f'{tag}2.mp3', voice='vi-VN-NamMinhNeural',
                        rate='+0%', max_retries=1))
                    errs[tag] = 'no-raise'
                except Exception as exc:
                    errs[tag] = (type(exc).__name__, str(exc), len(exc.args))
        assert errs['repo'] == errs['ref'], errs
        assert errs['repo'][0] == 'RuntimeError'
        assert 'Edge-TTS thất bại sau 1 lần' in errs['repo'][1]
        assert 'NoAudioReceived' in errs['repo'][1]


def test_synthesize_async_missing_package():
    with tmp_cwd() as tmp:
        import asyncio
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        with _block('edge_tts'):
            got = {}
            for tag, mod in (('repo', rep), ('ref', ref)):
                try:
                    asyncio.run(mod._synthesize_async('abc', tmp / f'{tag}.mp3',
                                                      voice='x', rate='+0%'))
                    got[tag] = 'no-raise'
                except Exception as exc:
                    got[tag] = (type(exc).__name__, str(exc))
            assert got['repo'] == got['ref'], got
        assert got['repo'] == ('RuntimeError', 'Chưa cài edge-tts. Chạy: pip install edge-tts')


def test_mp3_to_wav_without_ffmpeg():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    got = {}
    for tag, mod in (('repo', rep), ('ref', ref)):
        old = mod.shutil.which
        mod.shutil.which = lambda name: None
        try:
            mod._mp3_to_wav(Path('a.mp3'), Path('a.wav'))
            got[tag] = 'no-raise'
        except Exception as exc:
            got[tag] = (type(exc).__name__, str(exc))
        finally:
            mod.shutil.which = old
    assert got['repo'] == got['ref'], got
    assert got['repo'][1] == 'Cần ffmpeg để convert Edge-TTS mp3 → wav'


def test_run_coro_from_sync_context():
    import asyncio
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)

    async def val():
        await asyncio.sleep(0)
        return 42

    assert rep._run_coro(val()) == ref._run_coro(val()) == 42

    async def boom():
        raise KeyError('lost')

    for mod in (rep, ref):
        try:
            mod._run_coro(boom())
        except KeyError as exc:
            assert str(exc) == "'lost'"
        else:
            raise AssertionError('phải nổi KeyError')

    async def outer():
        return rep._run_coro(val())

    assert asyncio.run(outer()) == 42, 'đang có loop thì phải đẩy sang thread khác'

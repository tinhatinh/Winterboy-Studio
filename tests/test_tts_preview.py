# -*- coding: utf-8 -*-
'''Đối chiếu app.services.tts_preview với bản đã phát hành.

Hai tầng kiểm chứng:
1. ``test_bytecode_matches_pyc`` — source repo phải biên dịch ra ĐÚNG chuỗi lệnh của
   .pyc gốc. Đây là cách duy nhất bắt được kiểu dịch ngược ra "mã hợp lệ nhưng sai"
   (``.items()`` thừa, ``and``/``or`` bị đảo, thiếu tham số ``split('—', 1)``…).
2. Test hành vi qua ``_parity.same_result`` cho từng hàm thuần.

KHÔNG có cuộc gọi mạng: mọi nhánh tổng hợp đều bị chặn ở cổng ValueError, trả kết quả
từ cache, hoặc trỏ thư mục cache/asset vào output/ tạm.
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

DOTTED = 'app.services.tts_preview'
SRC = REPO / 'app' / 'services' / 'tts_preview.py'
PYC = INTERNAL / 'app' / 'services' / 'tts_preview.pyc'

_IGNORED_OPS = {'CACHE', 'RESUME', 'NOP'}      # NOP chỉ là padding dòng

EDGE_STUB = types.SimpleNamespace(normalize_voice=lambda v: 'edge:' + (v or ''))
CAPCUT_STUB = types.SimpleNamespace(list_capcut_voices=lambda: [
    ('Nữ - A|aaa', 'aaa'), ('Nam - B|bbb', 'bbb'), ('Có |_pipe| trong', 'pipe-key')])


@contextlib.contextmanager
def _seeded():
    '''Đặt module giả để ``from app.services.x import y`` không chạy package init (hỏng).'''
    names = {'app.services.edge_tts_engine': EDGE_STUB,
             'app.services.capcut_tts_engine': CAPCUT_STUB}
    saved = {k: sys.modules.get(k, False) for k in names}
    sys.modules.update(names)
    try:
        yield
    finally:
        for k, prev in saved.items():
            if prev is False:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = prev


# ---------------------------------------------------------------- bytecode ---
def _fp(code):
    '''Vân tay đệ quy của code object: hình dạng + chuỗi lệnh.'''
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
        ops.append((i.opname, a))
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


# ------------------------------------------------------------------- hành vi ---
VOICE_INPUTS = [
    '', '   ', None, 'vi-VN-HoaiMyNeural', 'vi-VN-NamMinhNeural',
    'en-US-AndrewMultilingualNeural', 'en-US-AvaMultilingualNeural',
    'fr-FR-VivienneMultilingualNeural', 'zh-CN-XiaoxiaoNeural', 'ja-JP-NanamiNeural',
    'ko-KR-InJoonNeural', 'th-TH-PremwadeeNeural', 'pt-BR-ThalitaMultilingualNeural',
    'de-DE-KatjaNeural', 'ru-RU-SvetlanaNeural', 'id-ID-GadisNeural',
    'ar-XA-SalmaB', 'hi-IN-SwaraNeural', 'tr-TR-AhmetNeural', 'es-ES-ElviraNeural',
    'Adam', 'Rachel', 'Bella', 'Charlotte', 'Josh', 'Elli', 'Antoni',
    'Female 1', 'Male 2', 'US Aria', 'UK Sonia', 'british voice', 'american guy',
    'Mandarin Voice', 'Cantonese', 'chinese classic', 'Japanese storyboard',
    'Korean anchor', 'english multilingual', 'Tiếng Việt - Hoài My',
    'tieng viet nam minh', 'Nữ - Hoài My (Tiếng Việt)', 'MAICHI',
    'Mai Chi (Nữ - Kể chuyện nhẹ nhàng)', 'vi-VN-HoaiMyNeural|Nữ - Hoài My',
    'en-', 'zh)', '(ja', 'ko-kr', 'VIETNAMESE', 'multilingual', '(vi', '(en',
]

MODEL_IDS = [None, '', 'eleven_multilingual_v2', 'eleven_turbo_v2_5',
             'eleven_flash v2 — Nhanh nhất', 'comic—x', '—', '  spaced  — label',
             'mr', 'eleven_english_sts_mc', 'multilingual — Đa ngôn ngữ',
             'turbo', '— turbo', 'a——b', 'flash-v2.5', 'en_us — Automatic',
             'xi — ', ' eleven_multilingual_v2 ', 'é—ê', '—-—', 'a—b—c']

PROVIDERS = ['Edge TTS', 'CapCut', 'ElevenLabs', 'Google Cloud TTS', 'ZeroTTS',
             'VieNeu', '', None, 'zerotts']


def _run(func, cases, **kw):
    bad = same_result(DOTTED, func, cases, **kw)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_normalize_eleven_model():
    _run('normalize_eleven_model', [((v,), {}) for v in MODEL_IDS])


def test_get_sample_text_for_voice():
    cases = [((v,), {}) for v in VOICE_INPUTS]
    cases += [((v,), {'default': 'MAC-DINH'}) for v in VOICE_INPUTS[:24]]
    cases += [((v,), {'default': ''}) for v in ['zzz', 'không rõ', None]]
    _run('get_sample_text_for_voice', cases)


def test_stable_voice_key():
    voices = ['vi-VN-HoaiMyNeural', 'vi-VN-HoaiMyNeural|Nữ - Hoài My', 'Nữ - A',
              'aaa', 'bbb', 'abc|def', 'abc|  def  ', 'Có |pipe| trong', '', '   ',
              None, 'zh-CN|xy', 'solo']
    args = [((p, v), {}) for p in PROVIDERS for v in voices]
    with _seeded():
        _run('_stable_voice_key', args)


def test_cache_path():
    combos = [(p, v, s, m, t)
              for p in ['Edge TTS', 'CapCut', 'ElevenLabs', 'ZeroTTS']
              for v in ['vi-VN-HoaiMyNeural', 'maichi', 'Nữ - A', 'abc|def', '']
              for s in ['1.0', '0.8', 1.2, '', None, 'official-preview']
              for m in ['eleven_multilingual_v2', 'x—label', '']
              for t in ['Xin chào', '', 'héllo—wörld']]
    step = max(1, len(combos) // 72)
    cases = [((), {'provider': p, 'voice': v, 'speed': s, 'model_id': m, 'text': t})
             for p, v, s, m, t in combos[::step]]
    with _seeded():
        _run('_cache_path', cases)


def test_bundled_sample_path():
    def only_tail(res):
        '''Bỏ phần gốc thư mục assets — repo và bản cài đặt đặt nó ở chỗ khác nhau.'''
        s = str(res).replace('\\', '/')
        if 'tts_samples/' in s:
            return s.split('tts_samples/', 1)[1]
        return s
    cases = [((p, v), {}) for p in PROVIDERS
             for v in ['vi-VN-HoaiMyNeural', 'maichi', 'abc|def', '', None, 'Nữ - A']]
    with _seeded():
        _run('bundled_sample_path', cases, attrs=only_tail)


def test_preview_result_is_frozen_dataclass():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a = rep.TtsPreviewResult(Path('x.mp3'), True)
    b = ref.TtsPreviewResult(Path('x.mp3'), True)
    assert repr(a) == repr(b), (repr(a), repr(b))
    assert [vars(x) for x in (a, b)][0] == [vars(x) for x in (a, b)][1], (a, b)
    assert a.bundled is False and b.bundled is False
    for mod in (rep, ref):
        try:
            mod.TtsPreviewResult(Path('y'), True).path = Path('z')
        except Exception as exc:
            assert type(exc).__name__ == 'FrozenInstanceError', type(exc).__name__
        else:
            raise AssertionError('TtsPreviewResult phải frozen')


def _target(mod, c):
    """Tính ra đường dẫn cache mà is_tts_preview_cached/generate sẽ dùng cho ``c``."""
    provider = (c['provider'] or 'Edge TTS').strip()
    voice = (c['voice'] or '').strip()
    text = (c.get('text') or mod.PREVIEW_TEXT).strip()
    if text == mod.PREVIEW_TEXT:
        text = mod.get_sample_text_for_voice(voice, default=mod.PREVIEW_TEXT)
    return mod._cache_path(provider=provider, voice=voice,
                           speed=c.get('speed', '1.0'),
                           model_id=c.get('model_id', 'eleven_multilingual_v2'),
                           text=text)


# Các bộ tham số đi tới tận cùng hàm mà không gọi provider nào.
HIT_CASES = [
    {'provider': 'Edge TTS', 'voice': 'vi-VN-HoaiMyNeural'},
    {'provider': '', 'voice': 'abc'},
    {'provider': 'ElevenLabs', 'voice': 'xyz'},
    {'provider': 'ZeroTTS', 'voice': 'maichi'},
    {'provider': 'VieNeu', 'voice': 'clone-a'},
    {'provider': 'CapCut', 'voice': 'lbl|key'},
    {'provider': 'Edge TTS', 'voice': 'abc|def', 'speed': '0.9'},
]


def test_is_tts_preview_cached_offline():
    '''Trỏ cache/asset vào output/ tạm: cùng file trên đĩa -> cùng kết quả.'''
    tmp = Path(tempfile.mkdtemp(prefix='tp_', dir=str(REPO / 'output')))
    cwd = os.getcwd()
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    os.chdir(tmp)
    try:
        with _seeded():
            for mod in (ref, rep):
                mod.TTS_PREVIEW_CACHE_ROOT = tmp / 'cache'
                mod.BUNDLED_TTS_PREVIEW_ROOT = tmp / 'bundled'
                # hàm dò thêm Path(__file__).parents[1]/parents[2] -> dẫn hết về tmp
                mod.__file__ = str(tmp / 'pkgx' / 'svcs' / 'tts_preview.py')
            # 1) chưa có file nào -> None cả hai bên
            for c in HIT_CASES:
                a = rep.is_tts_preview_cached(**c)
                b = ref.is_tts_preview_cached(**c)
                assert a == b, (c, a, b)
                assert a is None, (c, a)
            # 2) dựng file cache với hai mức dung lượng để kiểm ngưỡng 128 byte
            for size, expect in ((200, True), (50, False)):
                for c in HIT_CASES:
                    p = _target(rep, c)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(b'a' * size)
                    a = rep.is_tts_preview_cached(**c)
                    b = ref.is_tts_preview_cached(**c)
                    assert a == b, (c, size, a, b)
                    assert ((a is not None) == expect), (c, size, a)
                    p.unlink()
            # 3) bundled sample (edge / capcut)
            for prov in ('Edge TTS', 'CapCut'):
                key = rep.bundled_sample_path(prov, 'vi-VN-HoaiMyNeural')
                key.parent.mkdir(parents=True, exist_ok=True)
                key.write_bytes(b'b' * 300)
                a = rep.is_tts_preview_cached(provider=prov, voice='vi-VN-HoaiMyNeural')
                b = ref.is_tts_preview_cached(provider=prov, voice='vi-VN-HoaiMyNeural')
                assert a == b and a is not None, (a, b)
                key.unlink()
            # 4) mẫu zerotts/vieneu đặt trong preview/ (= parents[2] của __file__ giả)
            for sub, minsize in (('zerotts', 2000), ('vieneu', 200000)):
                d = tmp / 'preview' / sub
                d.mkdir(parents=True, exist_ok=True)
                (d / 'maichi.wav').write_bytes(b'c' * minsize)
                prov = 'ZeroTTS' if sub == 'zerotts' else 'VieNeu'
                a = rep.is_tts_preview_cached(provider=prov, voice='maichi')
                b = ref.is_tts_preview_cached(provider=prov, voice='maichi')
                assert a == b, (sub, a, b)
            # 5) voice không hợp lệ -> None
            for bad in ('', '   ', 'Chưa tải giọng (hãy clone thêm)', None):
                a = rep.is_tts_preview_cached(provider='Edge TTS', voice=bad)
                b = ref.is_tts_preview_cached(provider='Edge TTS', voice=bad)
                assert a is None and b is None, (bad, a, b)
    finally:
        os.chdir(cwd)


def test_generate_tts_preview_guards():
    '''Chỉ đi các nhánh chặn trước khi chạm mạng.'''
    cases = [((), c) for c in [
        {'provider': 'Edge TTS', 'voice': ''},
        {'provider': None, 'voice': None},
        {'provider': 'ElevenLabs', 'voice': '   '},
        {'provider': 'CapCut', 'voice': 'Chưa tải giọng (hãy clone)'},
        {'provider': 'ZeroTTS', 'voice': 'Chưa tải giọng'},
        {'provider': 'VieNeu', 'voice': ''},
        {'provider': 'Nhà Rong', 'voice': 'ai-do'},
        {'provider': 'google cloud tts', 'voice': 'x|y'},
    ]]
    with _seeded():
        _run('generate_tts_preview', cases)


def test_generate_tts_preview_cache_and_bundled_hits():
    '''Trả file có sẵn mà không gọi provider nào cả.'''
    tmp = Path(tempfile.mkdtemp(prefix='tg_', dir=str(REPO / 'output')))
    cwd = os.getcwd()
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    os.chdir(tmp)
    try:
        with _seeded():
            for mod in (ref, rep):
                mod.TTS_PREVIEW_CACHE_ROOT = tmp / 'cache'
                mod.BUNDLED_TTS_PREVIEW_ROOT = tmp / 'bundled'
                mod.__file__ = str(tmp / 'pkgx' / 'svcs' / 'tts_preview.py')
            bp = rep.bundled_sample_path('Edge TTS', 'vi-VN-HoaiMyNeural')
            bp.parent.mkdir(parents=True, exist_ok=True)
            bp.write_bytes(b'x' * 400)
            ra = rep.generate_tts_preview(provider='Edge TTS', voice='vi-VN-HoaiMyNeural')
            rb = ref.generate_tts_preview(provider='Edge TTS', voice='vi-VN-HoaiMyNeural')
            assert (ra.path, ra.cache_hit, ra.bundled) == (rb.path, rb.cache_hit, rb.bundled)
            assert ra.cache_hit and ra.bundled
            bp.unlink()

            c = {'provider': 'CapCut', 'voice': 'lbl|key', 'speed': '1.1'}
            p = _target(rep, c)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'y' * 256)
            ra = rep.generate_tts_preview(**c)
            rb = ref.generate_tts_preview(**c)
            assert (ra.path, ra.cache_hit, ra.bundled) == (rb.path, rb.cache_hit, rb.bundled)
            assert ra.cache_hit and not ra.bundled
            p.unlink()

            z = tmp / 'bundled' / 'zerotts'
            z.mkdir(parents=True, exist_ok=True)
            # resolve_voice_name có thể trả 'maichi' hoặc (khi import fail) 'Mai Chi'
            for nm in ('maichi', 'Mai Chi'):
                (z / f'{nm}.wav').write_bytes(b'z' * 4096)
            ra = rep.generate_tts_preview(provider='ZeroTTS', voice='Mai Chi')
            rb = ref.generate_tts_preview(provider='ZeroTTS', voice='Mai Chi')
            assert (ra.path, ra.cache_hit, ra.bundled) == (rb.path, rb.cache_hit, rb.bundled)
            assert ra.cache_hit and ra.bundled
    finally:
        os.chdir(cwd)


def test_prewarm_offline():
    '''Chữ ký phải khớp; không được khởi động worker thật.'''
    import inspect
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    assert str(inspect.signature(rep.prewarm_tts_samples_async)) == \
        str(inspect.signature(ref.prewarm_tts_samples_async))
    old = sys.modules.get('threading', False)
    sys.modules['threading'] = None               # import trong hàm sẽ raise
    try:
        for mod in (rep, ref):
            try:
                mod.prewarm_tts_samples_async('Edge TTS', 'vi-VN-HoaiMyNeural')
            except ImportError:
                pass
            else:
                raise AssertionError('phải lỗi khi không có threading')
    finally:
        if old is False:
            sys.modules.pop('threading', None)
        else:
            sys.modules['threading'] = old

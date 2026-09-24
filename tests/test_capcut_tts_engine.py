# -*- coding: utf-8 -*-
'''Đối chiếu app.services.capcut_tts_engine với bản đã phát hành (.pyc gốc).

Chỉ chạy phần logic thuần. Mọi hàm gọi HTTP hoặc spawn process (submit_tts,
query_*, poll_*, _http_post, _get_bytes, _mp3_to_wav, _make_silence_audio,
capcut_tts_generate, make_capcut_tts_func, upload_media_for_stt,
capcut_transcribe_to_srt, _FixSharkBatchRunner._execute) đều KHÔNG được gọi ở
đây — test không bao giờ được chạm mạng hay mở file thực thi.
'''
from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path

from _parity import (REPO, block_modules, describe, fingerprint, ref_module,
                     repo_module, same_result)

DOTTED = 'app.services.capcut_tts_engine'

B64 = ('SUKUyW3Z0sW1V2T3x4ZmN0R0FmSGpLbE1uT3BRc1R1V3eFl6QWJjRGVmR2hKaWtMbU5v'
       'A' * 4)                                    # >= 200 ký tự base64 hợp lệ
URL_MP3 = 'https://v16-capcut-sign.byteimg.com/ae-music/tos-cn-a-a/audio/x.mp3?a=1'

TEXTS = [
    '', '   ', 'Xin chào', 'Héllo wörld', 'Xin chào! Cảm ơn bạn.',
    '<b>đậm</b> thường', '{placeholder} còn lại', '<i>a</i>{b}c',
    '123', '!!!', '…', '—–', 'à á ã ạ ơ ư', 'Xin   chào\tthế giới',
    'dòng 1\ndòng 2', 'dòng 1\r\nvà 3', '<b>', '</b>', '{}', '{ }',
    'a' * 200, '🙂 emoji', '中文 普通话', '   ', '\n\n\n',
    '<script>alert(1)</script>nội dung', '{0} {name} trộn <u>gạch</u>',
    'tab\tvà\ncả xuống dòng', None, 0, 12345, ['a'], {'a': 1}, True,
]

RATES = [
    None, '', ' ', '1', 1, 1.0, '1.0', '1.00', '0.5', 0.5, '2', 2.0, '3', 99,
    -1, 0, -0.0, '1.25', '1.999', 1.005, '0.4999', '  1.5  ', 'abc', [], [1],
    {}, True, False, 1.049999, '2.5', 'nan', '1e-3', float('inf'), '-inf']

URLS = [
    '', '   ', 'http://', 'https://', 'https://a', 'http://x/y z', 'HTTP://UPPER',
    'https://a.b/c?d=1', 'ftp://x', 'data:audio/mp3;base64,AAAA', 'not a url',
    'https://' + ('a' * 300), '//nohost.com/x', 'https:/slash', 'http:///nohost',
    'https://[bad', 'http://ok.com/x.mp3', '  https://trim.me/x  ', 'http:',
    'https://x\nhttp://y', URL_MP3, B64, None, 5, 0.5, ['http://x'], {'a': 1},
]

B64_VALUES = [
    '', '   ', 'data:audio/mpeg;base64,AAAA', 'data:audio/mp3;' + 'x' * 300,
    B64, B64[:199], B64 + '\n\r\n', 'A' * 200, 'A' * 201, '!!!!' * 60,
    'a-_=' * 60, URL_MP3, 'https://x.com/' + 'A' * 300, '  ' + B64 + '  ',
    B64[:80] + ' ' * 200, 'short', None, 5, ['A' * 300], {'a': 1},
]

B64_BAD = ['', 'a', '====', '!!!!', 'AAA=', 'aGVsbG8=', '  aGVsbG8=  ',
           'data:text/plain;base64,YQ==', 'data:audio/mp3;base64,YQ==',
           'SGVsbG8gV29ybGQ=', '-_8=', 'aGVsbG8', 'aGVsbG8', 'YQ', 'YQ==',
           'AAAA' * 60, 'W5pbCU=', 'AAA\nA=', None, 5, b'aGVsbG8=', ['a'], {}]

DEVICES = [
    {}, {'ret': 0}, {'ret': '0'}, {'ret': 0.0}, {'code': 200}, {'code': 0},
    {'ret': 'ok'}, {'ret': 'success'}, {'ret': ''}, {'ret': None},
    {'ret': 'x', 'errmsg': 'boom'}, {'ret': '-6'}, {'ret': -6},
    {'ret': '-6', 'errmsg': 'shark block only'}, {'errmsg': 'Shark Block'},
    {'ret': '1014', 'message': 'system busy'}, {'ret': '5', 'msg': 'khác'},
    {'ret': '1', 'errmsg': '', 'message': '', 'msg': ''},
    {'code': None, 'ret': None}, {'ret': True}, {'ret': [1]},
]

TASKS = [
    {}, {'data': None}, {'data': {}}, {'data': {'tasks': []}}, {'tasks': []},
    {'tasks': None}, {'tasks': 'abc'}, {'data': 'abc'}, {'data': 5},
    {'data': {'tasks': [{'task_id': '1'}]}}, {'data': {'tasks': ['x']}},
    {'data': {'tasks': [{'a': 1}, {'b': 2}], 'failed_tasks': ['f']}},
    {'tasks': [{'x': 1}]}, {'tasks': [{'x': 1}], 'data': {'tasks': [{'y': 2}]}},
    {'data': {'tasks': [None]}}, {'data': {'tasks': {}}},
    {'data': {'failed_tasks': ['bad']}}, {'data': {'tasks': [1, 'a']}},
    {'payload': 'x'}, {'data': {'tasks': [[]]}},
]

PAYLOADS = [
    {}, {'payload': None}, {'payload': '{}'}, {'payload': '{"a":1}'},
    {'payload': 'not json'}, {'payload': ''}, {'payload': '[]'},
    {'payload': 'null'}, {'payload': {'audio_url': URL_MP3}},
    {'payload': [1, 2]}, {'payload': 5}, {'payload': {'url': 'ftp://x'}},
    {'payload': '{"audio_url":'}, {'payload': {'data': {'audio_url': URL_MP3}}},
    {'payload': {'utterances': [{'text': 'a', 'start_ms': 1, 'end_ms': 2}]}},
    {'payload': {'audio_data': B64}}, {'payload': b'raw'}, {'payload': True},
    {'payload': {'audio_list': [{'url': URL_MP3}]}},
    {'payload': {'a': {'b': {'c': {'url': URL_MP3}}}}},
]

AUDIO_REFS = [
    {}, { }, {'audio_url': URL_MP3}, {'url': 'http://a/b'}, {'url': 'ftp://x'},
    {'url': '  https://spaced.me/x  '}, {'audio': {'url': URL_MP3}},
    {'audio_data': B64}, {'data': B64[:150]}, {'audio_data': 'short'},
    {'audio_list': [{'url': URL_MP3}]}, {'audio_list': 'nope'},
    {'audios': [{'audio_base64': B64}, {'url': URL_MP3}]},
    {'results': [{'utterances': [{'text': 'x'}]}]},
    {'utterances': [{'text': 'a', 'start_ms': 0}]},
    {'other': URL_MP3}, {'other': 'https://example.com/plain'},
    {'weird': b'x' * 100}, {'weird': bytearray(b'y' * 10)},
    {'weird': b'z' * 10}, [URL_MP3], [B64], ['không gì cả'],
    URL_MP3, B64, 'data:audio/mp3;base64,' + B64, 'plain string', 5, None, [],
    {'audio_url': None, 'url': 5, 'download_url': {'x': URL_MP3}},
    {'a': {'b': [{'c': {'play_url': URL_MP3}}]}},
]

STT_PAYLOADS = [
    {'utterances': [{'text': 'Xin chào', 'start_time': 200, 'end_time': 1200}]},
    {'utterances': [{'text': 'a', 'start_ms': 0, 'end_ms': 900},
                    {'text': 'b', 'start_ms': 900, 'end_ms': 1800}]},
    {'captions': [{'content': 'nội dung', 'start': 1.0, 'end': 2.0}]},
    {'segments': [{'text': 'dài hơn chút', 'start': 1500, 'end': 2600}]},
    {'sentences': [{'sentence': 'không end', 'start_time': 500}]},
    {'items': [{'attribute_text': 'chỉ có attribute_text', 'begin': 3}]},
    {'data': {'utterances': [{'text': 'lồng', 'start_ms': 10, 'end_ms': 20}]}},
    {'utterances': [{'text': 'giảm dần', 'start_ms': 900, 'end_ms': 1000},
                    {'text': 'lộn xộn', 'start_ms': 100, 'end_ms': 300}]},
    {'utterances': [{'text': '  ', 'start_ms': 0, 'end_ms': 1}]},
    {'utterances': [{'text': 'bằng nhau', 'start_ms': 500, 'end_ms': 500}]},
    {'utterances': 'not a list'}, {'utterances': []}, {'utterances': [1, 2]},
    {'other': 1}, 'not json', '{}', '{"utterances": [{"text": "json"}]}',
    [], None, 5, {'payload': 'x'}, json.dumps({'utterances': [
        {'text': 'micro', 'start_time': 21600001, 'end_time': 22000000}]}),
    {'utterances': [{'text': 'float', 'start': '0.5', 'end': '1.5'}]},
    {'utterances': [{'start_ms': 0, 'end_ms': 1}]},
]

LANGS = [
    None, '', ' ', 'auto', 'AUTO', 'Auto ', ' detect', 'detect', 'none', 'NONE',
    'vi', 'vi-VN', 'vi-vn', 'VI-VN', 'zh', 'zh-CN', 'zh-cn', 'en', 'en-US',
    'English', 'Vietnamese', 'Tiếng Việt', 'th', 'ja', 'ko', 'id', 'pt', 'es',
    'fr', 'de', 'x', 'xx', 'y', '中文', 'vi-VN (Vietnamese)',
    'Portuguese (Brazil)', 'ru', 'hi', 'zh_CN', 'en-us', 'a', 'ab', 'abcdefg',
    'abcdefghij', '(vi)', 'vi(VN)', '  vi  ',
]

MS = [None, 0, -5, 0.0, 1, 200, 999, 1000, 1001, 1500, '2000', 'abc',
      21600000, 21600001, 36000000, 3.6e9, True, False, [], {}, '1e3',
      ' 2000 ', 1e6, 1e7, 0.4, [1], 1e12, '1000000000000', 21600000.0]

ERRS = [
    '', 'shark', 'SHARK BLOCK ONLY', 'ret=-6', 'ret=1014', 'System Busy here',
    'chặn request', 'http 429', 'HTTP 500', 'khuôn mẫu bình thường',
    RuntimeError('shark block only'), ValueError('ret=-6'), Exception(''),
    'CapCut TTS thất bại: xyz', 'CapCut TTS timeout', 'CAPCUT TTS hết thời gian',
    'CapCut tts queued', 'Connection reset by peer', 'Read timed out',
    'WinError 10054', 'temporary failure', 'Name resolution failed',
    'Network is unreachable', 'http://x', 0, None, ['a'], {'a': 1}, 5,
]

VOICE_KEYS = [
    None, '', 'BV074_streaming', 'bv074_streaming', 'Nam Chính', 'Cô Gái Hoạt Ngôn',
    'voice_a:7102355709945188865', 'BV075_streaming:123',
    'Tên hiển thị | BV074_streaming:7102355709945188865', 'x | y:1',
    'a:b:c', ':', 'a:', ':b', ' male ', 'MAN_', 'thanh niên', 'nữ', 'em bé',
    'bv070', 'bv107', 'bv075', 'namminh', 'hoaimy', 'https://x/y', 5, ['a'],
]

UTTERS = [
    {}, [], None, 'x', {'utterances': [{'text': 'a'}]},
    {'utterances': [{'start_ms': 1}]}, {'utterances': [{'foo': 1}]},
    {'captions': [{'content': 'a'}]}, {'segments': [{'text': 'x'}]},
    {'data': {'results': [{'utterances': [{'sentence': 'y'}]}]}},
    {'deep': {'deeper': {'x': [{'text': 'a'}]}}}, [
        {'text': 'a', 'start': 1}], [[{'content': 'b'}]], {'items': [{'start_ms': 1}]},
    {'utterances': 'x'}, {'utterances': []}, {'utterances': [1, 2]},
    {'a': {'captions': [{'start': 0}]}}, {'x': 5}, 5, ('tuple',),
    {'utterances': [{'text': 'vi-VN', 'start_ms': 0, 'end_ms': 1}, {'text': 2}]},
]


def _seed_srt_utils():
    '''Cho ``from app.services.srt_utils import SrtCue`` chạy được.

    ``app/services/__init__.py`` trong repo vẫn còn lỗi decompile nên import theo
    gói sẽ chết; nạp sẵn module theo đường dẫn làm cả hai bên cùng dùng một SrtCue.
    '''
    if 'app.services.srt_utils' in sys.modules:
        return
    srt = repo_module('app.services.srt_utils')
    pkg = sys.modules.get('app') or types.ModuleType('app')
    pkg.__path__ = [str(REPO / 'app')]
    sub = sys.modules.get('app.services') or types.ModuleType('app.services')
    sub.__path__ = [str(REPO / 'app' / 'services')]
    sys.modules['app'] = pkg
    sys.modules['app.services'] = sub
    sys.modules['app.services.srt_utils'] = srt


def _check(func, cases, *, block=(), attrs=None):
    bad = same_result(DOTTED, func, [((c,), {}) for c in cases], block=block, attrs=attrs)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def _check2(func, cases, *, block=(), attrs=None):
    '''Như _check nhưng mỗi case là (args, kwargs).'''
    bad = same_result(DOTTED, func, cases, block=block, attrs=attrs)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def _messages(func, cases):
    '''So cả tên lẫn thông báo exception — same_result chỉ thấy tên.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    fr, fp = getattr(ref, func), getattr(rep, func)
    bad = []

    def shot(fn, args, kwargs):
        try:
            return ('ok', repr(fn(*args, **kwargs)), )
        except Exception as exc:
            return ('err', type(exc).__name__, str(exc))

    for args, kwargs in cases:
        a, b = shot(fp, args, kwargs), shot(fr, args, kwargs)
        if a != b:
            bad.append((args, kwargs, a, b))
    return bad


def _assert_no_diff(func, cases):
    bad = _messages(func, cases)
    assert not bad, bad[:6]


# ---------------------------------------------------------------- constants


def test_module_constants_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in ('DEFAULT_VOICE_TYPE', 'DEFAULT_RESOURCE_ID', 'DEFAULT_VOICE_LABEL',
                 '_SUCCESS', '_FAILED', '_PENDING', '_URL_KEYS', '_B64_KEYS',
                 '_STT_LANG_MAP', '_CURL_IMPERSONATE', '_MIN_SUBMIT_INTERVAL_S',
                 '_FIX_SHARK_EVERY_CUES', '_FIX_SHARK_STALL_S',
                 '_FIX_SHARK_MIN_INTERVAL_S', '_edge_fallback_active',
                 '_edge_fallback_reason', '_last_submit_mono', '_device_cache_stamp',
                 '_device_cache_value'):
        a, b = getattr(rep, name), getattr(ref, name)
        assert repr(a) == repr(b), (name, a, b)


def test_callables_present():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    missing = [n for n in dir(ref) if not hasattr(rep, n) and not n.startswith('__')]
    assert not missing, missing


# ---------------------------------------------------------------- text logic


def test_normalize_rate():
    _check('normalize_rate', RATES)


def test_normalize_cache_text():
    _check('normalize_cache_text', TEXTS)


def test_is_speakable_text():
    _check('is_speakable_text', TEXTS)


def test_map_stt_language():
    _check('map_stt_language', LANGS)


def test_ms_to_s():
    _check('_ms_to_s', MS)


def test_looks_like_url():
    _check('_looks_like_url', URLS)


def test_looks_like_b64_audio():
    _check('_looks_like_b64_audio', B64_VALUES)
    _check('_looks_like_b64_audio', URLS)


def test_decode_b64():
    _check('_decode_b64', B64_BAD)
    bad = _messages('_decode_b64', [((v,), {}) for v in B64_BAD])
    assert not bad, bad[:6]


def test_edge_voice_for_capcut():
    _check('_edge_voice_for_capcut', VOICE_KEYS)


def test_is_shark_or_busy():
    _check('_is_shark_or_busy', ERRS)


def test_is_retryable_strict_tts_error():
    _check('_is_retryable_strict_tts_error', ERRS)


# ---------------------------------------------------------------- payloads


def _nested(depth):
    '''Dict lồng ``depth`` tầng, mỗi tầng một key thường để ép đệ quy đi hết cỡ.'''
    root = cur = {}
    for _ in range(depth):
        nxt = {}
        cur['k'] = nxt
        cur = nxt
    cur['audio_url'] = URL_MP3
    return root


def test_find_audio_ref():
    _check('_find_audio_ref', AUDIO_REFS)
    _check('_find_audio_ref', [_nested(d) for d in (0, 1, 5, 10, 11, 12, 13, 20)])
    _check2('_find_audio_ref', [({'url': URL_MP3}, 12), ({'url': URL_MP3}, 13),
                                ({'url': URL_MP3}, 0),
                                ({'audio_list': [{'url': URL_MP3}]}, 11)])


def test_find_audio_ref_messages():
    _assert_no_diff('_find_audio_ref', [((v,), {}) for v in AUDIO_REFS])


def test_first_task():
    _check('_first_task', DEVICES)
    _check('_first_task', TASKS)


def test_first_task_messages():
    _assert_no_diff('_first_task', [((v,), {}) for v in DEVICES + TASKS])


def test_check_api_ret():
    cases = [((d, 'tts-new'), {}) for d in DEVICES] + [((d, 'query'), {}) for d in DEVICES]
    _check2('_check_api_ret', cases)
    _assert_no_diff('_check_api_ret', cases)


def test_parse_task_payload():
    _check('_parse_task_payload', PAYLOADS)


def test_payload_has_audio():
    _check('_payload_has_audio', PAYLOADS)


def test_payload_has_utterances():
    _check('_payload_has_utterances', PAYLOADS)


def test_extract_audio_bytes_rejects_bad_payload():
    # chỉ chạy nhánh lỗi (không có URL/base64 hợp lệ) -> không đụng mạng
    bad = [p for p in PAYLOADS if p.get('payload') in (None, 'not json', 5, b'raw', True)]
    _check('extract_audio_bytes', bad)


# ---------------------------------------------------------------- cues


def test_utterances_to_cues():
    _seed_srt_utils()
    _check('utterances_to_cues', STT_PAYLOADS)


def test_utterances_to_cues_messages():
    _seed_srt_utils()
    _assert_no_diff('utterances_to_cues', [((p,), {}) for p in STT_PAYLOADS])


def test_extract_stt_cues():
    _seed_srt_utils()
    _check('extract_stt_cues', [{'payload': p} for p in STT_PAYLOADS] + PAYLOADS)


def test_find_utterances():
    _check('_find_utterances', UTTERS)
    _check2('_find_utterances', [((v, 14), {}) for v in UTTERS]
            + [((v, 15), {}) for v in UTTERS])


# ---------------------------------------------------------------- device files


def _both(call):
    '''Chạy call(mod, home) trên repo + bản gốc, mỗi bên một thư mục tạm.

    Hai module trỏ vào ``~/.winterboy`` thật -> phải ghi đè đường dẫn cấp module
    thì test mới không đụng tới hồ sơ device của người dùng.
    '''
    out = []
    for loader in (repo_module, ref_module):
        mod = loader(DOTTED)
        home = Path(tempfile.mkdtemp())
        try:
            out.append(('ok', call(mod, home)))
        except Exception as exc:
            out.append(('err', type(exc).__name__, str(exc)))
    return out


def _write(home, name, text):
    p = home / name
    p.write_text(text, encoding='utf-8-sig' if name.endswith('.bom') else 'utf-8')
    return p


def test_config_paths_are_stable():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for func in ('device_config_path', 'device_source_config_path'):
        assert getattr(rep, func)() == getattr(ref, func)()
    for name in ('_DEVICE_PATH', '_DEVICE_SOURCE_PATH', 'CAPCUT_TTS_CACHE_ROOT'):
        assert getattr(rep, name) == getattr(ref, name), name
    assert rep.CAPCUT_TTS_CACHE_ROOT.parent.name == 'tts_cache'


def test_bundled_fix_paths():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a, b = rep.get_bundled_capcut_fix_paths(), ref.get_bundled_capcut_fix_paths()
    assert [p.name for p in a] == [p.name for p in b] == ['fix_shark.bat', 'device.json']
    assert a[0].parent == a[1].parent


def test_resolve_paths():
    home = Path(tempfile.mkdtemp())
    real_bat = _write(home, 'fix_shark.bat', '@echo off\r\n')
    real_json = _write(home, 'device.json', '{}')

    def name_of(p):
        return p.name

    _check2('resolve_capcut_device_path', [((None,), {}), (('',), {}),
                                           ((home / 'khong-ton-tai.json',), {}),
                                           (('~/nothing.json',), {}),
                                           ((5,), {})], attrs=name_of)
    # candidate tồn tại -> trả đúng file đó (so đường dẫn đầy đủ)
    _check2('resolve_capcut_device_path', [((real_json,), {}), ((str(real_json),), {})],
            attrs=lambda p: str(p).replace('\\', '/'))
    _check2('resolve_capcut_fix_bat_path', [((None,), {}), (('',), {}),
                                            ((real_bat,), {}), ((real_json,), {}),
                                            ((home / 'missing.bat',), {}),
                                            (([1],), {})],
            attrs=lambda p: (p.name, p == real_bat or p == real_json))


def test_file_stamp():
    home = Path(tempfile.mkdtemp())
    good = _write(home, 'device.json', '{"device_id": "1"}')
    _check2('_file_stamp', [((home,), {}), ((good,), {}), ((home / 'nope.json',), {}),
                            ((Path('C:/'),), {}), ((Path('C:/khong/co/gi.do'),), {}),
                            (('',), {}), ((5,), {}), ((None,), {})])


def test_active_device_stamp():
    def call(mod, home):
        return fingerprint(mod._active_device_stamp())

    a, b = _both(call)
    assert a == b, (a, b)


def test_save_device_overrides():
    def call(mod, home):
        mod._DEVICE_PATH = home / 'capcut_device.json'
        for data in ({}, {'device_id': '9' * 19}, {'_note': 'x', 'comment': 'c',
                                                   'source': 's', 'iid': '7'},
                     {'tdid': 5, 'ok': True}, {'mô tả': 'dấu tiếng Việt'},
                     {'nested': {'a': [1, 2]}}, {'ret': None}):
            mod.save_device_overrides(data)
        written = mod._DEVICE_PATH.read_text(encoding='utf-8')
        mod.save_device_overrides({'a': 1})
        tail = mod._DEVICE_PATH.read_text(encoding='utf-8')
        base = mod.save_device_overrides({}).name
        try:
            mod.save_device_overrides(None)
            err = None
        except Exception as exc:
            err = type(exc).__name__
        return (written, tail, base, err)

    a, b = _both(call)
    assert a == b, (a, b)
    assert a[0] == 'ok', a


def test_save_device_overrides_bytes_exact():
    '''File device.json phải giống nhau từng byte (ensure_ascii/indent/key lọc).'''
    payload = {'device_id': '9' * 19, 'comment': 'ghi chú', 'source': 'auto',
               '_hidden': 1, 'unicode': 'Cô Gái Hoạt Ngôn', 'flag': False}

    def call(mod, home):
        mod._DEVICE_PATH = home / 'sub' / 'capcut_device.json'
        mod.save_device_overrides(payload)
        return mod._DEVICE_PATH.read_bytes()

    a, b = _both(call)
    assert a == b and a[0] == 'ok', (a, b)
    assert json.loads(a[1].decode('utf-8')) == {
        'device_id': '9' * 19, 'unicode': 'Cô Gái Hoạt Ngôn', 'flag': False}


def test_load_selected_device_overrides():
    def call(mod, home):
        mod._DEVICE_PATH = _write(home, 'capcut_device.json',
                                  '{"device_id": "111", "source": "auto"}')
        mod._DEVICE_SOURCE_PATH = home / 'capcut_device_source.json'
        out = [('main', fingerprint(mod.load_selected_device_overrides()))]

        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True,
                           'backup_path': str(_write(home, 'backup.json',
                                                     '{"iid": "222"}'))}))
        out.append(('backup', fingerprint(mod.load_selected_device_overrides())))

        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True, 'backup_path': ''}))
        mod.resolve_capcut_device_path = lambda c: home / 'missing.json'
        try:
            mod.load_selected_device_overrides()
            out.append(('missing', None))
        except Exception as exc:
            out.append(('missing', f'{type(exc).__name__}: {exc}'.replace(str(home), 'H')))

        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True,
                           'backup_path': str(_write(home, 'list.json', '[1, 2]'))}))
        try:
            mod.load_selected_device_overrides()
            out.append(('notdict', None))
        except Exception as exc:
            out.append(('notdict', str(exc)))

        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True,
                           'backup_path': str(_write(home, 'bad.json', '{sai'))}))
        try:
            mod.load_selected_device_overrides()
            out.append(('bad', None))
        except Exception as exc:
            out.append(('bad', f'{type(exc).__name__}: {exc}'.replace(str(home), 'H')))
        return out

    a, b = _both(call)
    assert a == b, (a, b)
    assert a[0] == 'ok', a


def test_load_selected_device_restores_path():
    '''Đường dẫn backup hỏng nhưng có file khác hợp lệ -> tự ghi lại lựa chọn.'''
    def call(mod, home):
        good = _write(home, 'ok.json', '{"tdid": "333"}')
        mod._DEVICE_PATH = home / 'capcut_device.json'
        mod._DEVICE_SOURCE_PATH = home / 'capcut_device_source.json'
        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True, 'backup_path': str(home / 'no.json')}))
        mod.resolve_capcut_device_path = lambda c: good
        data = mod.load_selected_device_overrides()
        saved = json.loads(mod._DEVICE_SOURCE_PATH.read_text(encoding='utf-8'))
        return (fingerprint(data), saved['use_backup'], Path(saved['backup_path']).name)

    a, b = _both(call)
    assert a == b and a[0] == 'ok', (a, b)
    assert a[1][1] is True and a[1][2] == 'ok.json', a


def test_edge_fallback_state():
    def call(mod, home):
        log = [mod.is_edge_fallback_active(), mod._edge_fallback_reason]
        mod._activate_edge_fallback('lý do shark 1')
        log += [mod.is_edge_fallback_active(), mod._edge_fallback_reason]
        mod._activate_edge_fallback('lý do khác')
        log += [mod.is_edge_fallback_active(), mod._edge_fallback_reason]
        mod.reset_edge_fallback()
        log += [mod.is_edge_fallback_active(), mod._edge_fallback_reason]
        return log

    a, b = _both(call)
    assert a == b, (a, b)


def test_capcut_tts_available_without_requests():
    _check2('capcut_tts_available', [((), {})], block=('requests',))


# ---------------------------------------------------------------- fix-shark


def test_runner_init_defaults():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)

    def attrs(inst):
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(inst).items()
                if k != '_lock'}

    for kwargs in ({'enabled': False, 'path': ''},
                   {'enabled': True, 'path': 'C:/x/fix_shark.bat'},
                   {'enabled': 1, 'path': '  ', 'device_path': '  '},
                   {'enabled': True, 'path': '~/a.bat', 'device_path': '~/d.json',
                    'every_cues': 0, 'stall_s': -1, 'min_interval_s': -5},
                   {'enabled': True, 'path': Path('out/fix.bat'), 'every_cues': '7',
                    'stall_s': '0.5', 'min_interval_s': None},
                   {'enabled': 'x', 'path': None, 'device_path': None},
                   {'enabled': True, 'path': '~/d.bat', 'every_cues': 90.9}):
        out = []
        for mod in (rep, ref):
            try:
                out.append(('ok', attrs(mod._FixSharkBatchRunner(**kwargs))))
            except Exception as exc:
                out.append(('err', type(exc).__name__))
        assert out[0] == out[1], (kwargs, out)


def test_valid_device_ids():
    _check('_FixSharkBatchRunner._valid_device_ids', [
        None, (), ('9' * 19,), ('9' * 20,), ('9' * 18,), ('9' * 21,),
        ('9' * 19, '8' * 19, '7' * 20), ('9' * 19, '', '7' * 19),
        ('a' * 19, '9' * 19, '9' * 19), (' 9' * 1 + '9' * 18,), ('9' * 9 + '-' + '9' * 10,),
        ('9' * 19, '9' * 19, '9' * 19, '9' * 19), (5,), ('9' * 19, 5), '9' * 19,
        [], [1], True, 0, {'a': 1}])


def test_profile_snapshot():
    home = Path(tempfile.mkdtemp())
    good = _write(home, 'device.json', json.dumps(
        {'device_id': '9' * 19, 'iid': '8' * 19, 'tdid': '7' * 19}))
    partial = _write(home, 'partial.json', '{"device_id": 12345, "iid": null}')
    _check2('_FixSharkBatchRunner._profile_snapshot', [
        ((good,), {}), ((partial,), {}), ((home / 'nope.json',), {}), ((home,), {}),
        ((_write(home, 'arr.json', '[1,2]'),), {}),
        ((_write(home, 'bad.json', '{sai'),), {}),
        ((_write(home, 'empty.json', ''),), {}),
        ((_write(home, 'num.json', '5'),), {}),
        ((_write(home, 'null.json', 'null'),), {}),
        ((Path('C:/khong/co'),), {}), ((None,), {})])


def test_batch_device_json_paths():
    home = Path(tempfile.mkdtemp())
    simple = _write(home, 'simple.bat', '@echo off\r\nset DEV=C:\\x\\device.json\r\n')
    quoted = _write(home, 'quoted.bat', 'set "DEV={0}\\q.json"\r\n'.format(home))
    var = _write(home, 'var.bat', 'set BASE={0}\r\nset DEV=%BASE%\\sub.json\r\n'.format(home))
    rel = _write(home, 'rel.bat', 'set DEV=device_rel.json\r\n')
    dup = _write(home, 'dup.bat',
                 'set A={0}\\d.json\r\nset B={0}\\d.json\r\n'.format(home))
    otherext = _write(home, 'other.bat', 'set DEV={0}\\x.txt\r\n'.format(home))
    env = _write(home, 'env.bat', 'set DEV=%USERPROFILE%\\capcut_device.json\r\n')
    arith = _write(home, 'arith.bat', 'set /a N=1\r\nset DEV={0}\\a.json\r\n'.format(home))
    cases = [((simple,), {}), ((quoted,), {}), ((var,), {}), ((rel,), {}),
             ((dup,), {}), ((otherext,), {}), ((env,), {}), ((arith,), {}),
             ((home / 'missing.bat',), {}), ((home,), {}),
             ((_write(home, 'empty.bat', ''),), {}),
             ((_write(home, 'noclose.bat', 'set DEV=' + str(home) + '\\z.json'),), {}),
             ((_write(home, 'lower.bat', 'SET dev={0}\\low.json\r\n'.format(home)),), {})]
    _check2('_FixSharkBatchRunner._batch_device_json_paths', cases,
            attrs=lambda ps: [p.relative_to(home).as_posix() if p.is_relative_to(home)
                              else str(p) for p in ps])


def test_active_profile_snapshot():
    def call(mod, home):
        mod._DEVICE_PATH = _write(home, 'capcut_device.json',
                                  '{"device_id": "%s"}' % ('9' * 19))
        mod._DEVICE_SOURCE_PATH = home / 'capcut_device_source.json'

        def brief(snap):
            (path, ids, _mtime) = snap
            return (path.name, ids)

        out = [brief(mod._FixSharkBatchRunner._active_profile_snapshot())]
        backup = _write(home, 'backup.json',
                        '{"device_id": "%s", "iid": "%s"}' % ('9' * 19, '8' * 19))
        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True, 'backup_path': str(backup)}))
        out.append(brief(mod._FixSharkBatchRunner._active_profile_snapshot()))
        missing = home / 'khong-co.json'
        _write(home, 'capcut_device_source.json',
               json.dumps({'use_backup': True, 'backup_path': str(missing)}))
        out.append(brief(mod._FixSharkBatchRunner._active_profile_snapshot()))
        return out

    a, b = _both(call)
    assert a == b, (a, b)
    assert a[0] == 'ok', a
    assert a[1][0] == ('capcut_device.json', ('9' * 19, '', '')), a


def test_run_once_cached_and_rate_limited():
    '''Chỉ hai nhánh không spawn process: cache hit và chặn theo chu kỳ.'''
    import time

    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (rep, ref):
        r = mod._FixSharkBatchRunner(enabled = True, path = '')
        r._results['k'] = True
        assert r._run_once('k', 'reason') is True, mod.__name__

        r2 = mod._FixSharkBatchRunner(enabled = True, path = '', min_interval_s = 60)
        r2._last_run_mono = time.monotonic()
        assert r2._run_once('khac', 'reason') is False
        assert r2._results.get('khac') is False

        r3 = mod._FixSharkBatchRunner(enabled = False, path = '')
        assert r3._run_once('bat', 'reason') is False
        assert 'bat' not in r3._results

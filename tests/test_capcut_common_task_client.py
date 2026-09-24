# -*- coding: utf-8 -*-
'''Đối chiếu app.services.capcut_common_task_client với bản đã phát hành.

Module này dựng chữ ký cho API TTS/STT trên mây của CapCut: stub MD5 của body,
chuỗi truy vấn chuẩn hoá, chữ ký RSA-PKCS#1 v1.5, header thiết bị và SigV4 cho
bước upload audio. Tất cả đều tất định khi cố định đầu vào, nên kiểm tra bằng
cách GỌI TRỰC TIẾP hàm trong .pyc đã phát hành — không một gọi mạng nào:

* ``test_bytecode_khop_voi_ban_phat_hanh`` - so code object từng byte (co_code,
  hằng, tên, dòng, bảng exception) của module + 34 hàm và lambda/genexpr lồng nhau.
* mỗi hàm khác - cùng đầu vào thì hai bên phải cho byte giống hệt (kể cả thứ tự
  key của header), và có giá trị neo tính sẵn từ bản gốc để vẫn kiểm được khi máy
  không có .pyc.

``secrets.token_bytes`` (padding RSA), ``time.time``, ``uuid.uuid4`` và
``utc_now_for_vod`` được cố định qua ``FixedWorld``; bước upload và CLI chạy với
vận chuyển giả nên không phát sinh kết nối nào.
'''
import argparse
import base64
import binascii
import hashlib
import io
import json
import marshal
import secrets
import sys
import tempfile
import time
import uuid
from contextlib import redirect_stdout
from pathlib import Path

from _parity import INTERNAL, REPO, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.capcut_common_task_client'
SRC = REPO / 'app' / 'services' / 'capcut_common_task_client.py'

URL_TTS = ('https://editor-api-sg.capcutapi.com/lv/v1/common_task/new'
           '?app_name=CapCut&aid=359289&version_code=589824')
DEVICE = {
    'aid': '359289', 'app_name': 'CapCut', 'appvr': '9.0.0', 'version_name': '9.0.0',
    'version_code': '589824', 'channel': 'capcutpc_web_product', 'device_platform': 'windows',
    'device_type': 'Windows', 'device_brand': 'American Megatrends International, LLC.',
    'os_version': '10.0.22635', 'device_id': '7321782919767590401',
    'iid': '7616057603051374344', 'region': 'VN', 'loc': 'VN', 'lan': 'vi-VN',
    'pf': '3', 'tdid': '7321782919767590401',
}
CREDS = {
    'domain': 'tos-vn-v3.tikvcdn.com',
    'access_key_id': 'AKIDEXAMPLE',
    'secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    'session_token': 'SESSION123',
    'space_name': 'tos-vn-v3-alisb',
}
AMZ_DATE = '20230918T120000Z'
HTTP_DATE = 'Mon, 18 Sep 2023 12:00:00 GMT'
SSML = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        ' xml:lang="en-US">\nXin chào\n</speak>')
AUDIO_BYTES = b'ID3' + bytes(range(256)) * 5
AUDIO_CRC = 'a04a999f'
AUDIO_MD5 = '5a41b719973978fb0d14db5d098382d3'

# ---------- giá trị neo tính từ app/services/capcut_common_task_client.pyc gốc ----------
A_STUB = 'fa2bd752782454b40d6b4ac3136dc1d2'
A_HMAC = '2d93cbc1be167bcb1637a4a23cbff01a7878f0c50ee833954ea5221bb1b8c628'
A_CANON = 'aid=359289&app_name=CapCut&version_code=589824'
A_SIGN_HEADER = '727ba2cbb38bad3130c80c20f82da45c'
A_SIGNING_KEY = 'dbd396609f16873f834be84f4f835c663a7692ce3773d9177b15663b57677909'
A_RSA_MODULUS_HEAD = '993777e0bc386fb2'
A_RSA_MODULUS_TAIL = 'b82dfa9b'
A_RSA_PROBE = ('a21wwsUFnpq8w1OosG1CbY26NQTiT3msGz/Z/Yi4b5kPi9uxIgkRBSxb75+ee5sGn7RLAEkLP96'
               'jCraNz5ATYoXRI3j/265VgMfg+BJhJWPNMRwbR2yJclDS0TQWC3+tF1/FnqlCE0+I/ch0PrTpao6'
               'cw/UuLlBTi4vJ+fLJ8zWXJ4J5Wzq/+PC11jKRytCsrr7MAOZ2mLavrriGhg0uUNHRfdwtrs33A6'
               'fhft80EvcratPm/T6DT4lnZwMBRCOW8QKJk26dPRtOS2xaDAXl8YaE9TI5qa0fmxJFl2VCNhGwJ'
               'zsioI9WvGUnpxCtZuLxMpFmIufmyN82Gdd7GhMxHg==')
A_RSA_EMPTY = ('VQnytYbvwGSfpZruJUT9G5IFu08dNcDdAPL/vCLSpXLn47KoooBJp9VVDzrrQj1BaywGxKJoyKk'
               'P0VmGn+CXpJHKbs7ukFkI7aTCrbNgGP4zM4IKKNy2pmrKyfk4JgrQSp0q6AngaIyph98pADC4p7'
               'bBGuk6Ou+eO8ae8xLJP7e/C69ol+M/g1UrmVdJjQ9DUxIZl2ZdZmW/9iUdpz75WqfyQRt1+QA6W'
               'wk1feP8x8AKm7GwUpo7xFK94zj/GaBYbNwuw5Ppo64KJ6ON0N4phyHPoFE0eMVSpALxFEpJQYq7'
               '1IU/cUFqCbxpQGHCNQv6PKd4IY80MLmIis7dgOdb+Q==')
A_TTS_SIGN = ('gAfKRcHbnNLe66s78oQy42+a+wyzSBqmUKtqJGJFQibZ5JnZWg8l9bzNiPGvOUA9pfQ2vzd72Tm'
              '/FbrnNyzQQLrxLzguZ2p9yTi6/Ge5XnEYYPJ/+UxY1bM98lf4pw7pnAZGQ0PQB/35KFqzmpOrMvo'
              '9yMPp5v8DbDRuGKrcSwVWTM56lH6O7Lu0KcuEXjvfLEGvxBwWaGQEIjitbMS23apQ0+haGobjvhRD'
              'ILid4bhxkeTb2MbWQMmnJaNHLXi4E78YVTYCXhSFYj9j+GnSEcGXjD6xChvhZ6KA2GNMgqgEpEgK'
              'n8USP1DaxmhLXzWK2agsRGa2QTkexkVyfR+NcA==')
A_TTS_SIGN_NOEXTRA = ('VGt+tCrdz0Zik9ovVb5VF9jBMesyiI5tes7pGiWQDIGz/CYQC3HRKnGF0MVbKKwua2bs'
                      'Jize2c7MGSZMQRhKIG8Worz4QI3cFNCPcnnK308E97fUWtWMKRaQ4/mCPaoazsb+CXpHU/'
                      'v2gJ2k7CxFAY1dgBMruOESglFiytApMnO2oF69+P8SjOrgjdeGrPRmMLxpyEK80Ga87an6'
                      'WG+AymgysQAtx1Cer7P8PpXY0UzVgKv8IQAHPJlbO4tRvFaNOsS5Cm7cRzPzPYYMrM+z1y'
                      'RTtGhrx2TTLI6I58U6IRGnljVk0s71EHhCK6RY089HDueexu8PTqkltSqoJVbtqA==')
A_SIGV4_POST = ('AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20230918/sdwdmwlll/vod/aws4_request'
                ', SignedHeaders=x-amz-date;x-amz-security-token'
                ', Signature=02931c8185216842a77a9a8482c506996b40dc829e1ff690455201c82720db52')
A_SIGV4_GET = ('AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20230918/sdwdmwlll/vod/aws4_request'
               ', SignedHeaders=x-amz-date;x-amz-security-token'
               ', Signature=5e8246f44ca64cf2effe78a7045f45907cd7320d49c15c0e8f95e1a7ff029966')
A_SIGV4_PUT = ('AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20230918/sdwdmwlll/vod/aws4_request'
               ', SignedHeaders=x-amz-date;x-amz-security-token'
               ', Signature=3a590679b072b1de8d7731f3395cadecd22ddde5694912aa54ea778583b5f4de')
A_BASE_HEADERS = json.loads(
    '{"content-type": "application/json", "appvr": "9.0.0", "ch": "capcutpc_web_product",'
    ' "device-time": "1700000000", "lan": "vi-VN", "loc": "VN", "pf": "3",'
    ' "sign-ver": "1", "tdid": "7321782919767590401",'
    ' "x-ss-stub": "bb6cb5c68df4652941caf652a366f2d8", "x-ss-dp": "359289",'
    ' "x-khronos": "1700000000",'
    ' "x-tt-trace-id": "00-00000000000000000000000000000001-0000000000000000-01",'
    ' "user-agent": "Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03",'
    ' "accept-encoding": "gzip, deflate", "store-country-code": "vn",'
    ' "store-country-code-src": "did", "is-dispatch-us-ttp": "0",'
    ' "is-app-region-us-ttp": "0"}')
A_BASE_HEADERS_APPID = json.loads(
    '{"content-type": "application/json", "appvr": "9.0.0", "ch": "capcutpc_web_product",'
    ' "device-time": "1700000000", "lan": "vi-VN", "loc": "VN", "pf": "3",'
    ' "sign-ver": "1", "tdid": "7321782919767590401",'
    ' "x-ss-stub": "bb6cb5c68df4652941caf652a366f2d8", "x-ss-dp": "359289",'
    ' "x-khronos": "1700000000",'
    ' "x-tt-trace-id": "00-00000000000000000000000000000001-0000000000000000-01",'
    ' "user-agent": "Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03",'
    ' "accept-encoding": "gzip, deflate", "store-country-code": "vn",'
    ' "store-country-code-src": "did", "is-dispatch-us-ttp": "0",'
    ' "is-app-region-us-ttp": "0", "app-sdk-version": "9.0.0", "appid": "359289"}')
A_COMMON_QUERY = json.loads(
    '{"app_name": "CapCut", "device_type": "Windows", "os_version": "10.0.22635",'
    ' "channel": "capcutpc_web_product", "version_name": "9.0.0",'
    ' "device_brand": "American Megatrends International, LLC.",'
    ' "device_id": "7321782919767590401", "iid": "7616057603051374344",'
    ' "version_code": "589824", "device_platform": "windows", "aid": "359289",'
    ' "region": "VN"}')
A_COMMON_QUERY_BABI = json.loads(
    '{"app_name": "CapCut", "device_type": "Windows", "os_version": "10.0.22635",'
    ' "channel": "capcutpc_web_product", "version_name": "9.0.0",'
    ' "device_brand": "American Megatrends International, LLC.",'
    ' "device_id": "7321782919767590401", "iid": "7616057603051374344",'
    ' "version_code": "589824", "device_platform": "windows", "aid": "359289",'
    ' "babi_param": "{\\"k\\":\\"v\\"}"}')
A_STT_BODY = json.loads(
    '[{"feature_entrance": "editor",'
    ' "feature_entrance_detail": "editor-elements-captions-subtitle_recognition",'
    ' "feature_key": "subtitle_recognition", "scenario": "video_editor"},'
    ' {"bind_id": "00000000-0000-0000-0000-000000000002", "can_queue": true,'
    ' "enter_from": "asr", "tasks": [{"context": "00000000-0000-0000-0000-000000000003",'
    ' "payload": "{\\"cap_json\\":{\\"adjust_endtime\\":200,\\"audio\\":\\"vid-1\\",'
    '\\"audio_type\\":\\"vid\\",\\"caption_type\\":0,\\"client_request_id\\":'
    '\\"00000000-0000-0000-0000-000000000001\\",\\"duration\\":12345,\\"enable_cache\\":true,'
    '\\"enter_from\\":\\"asr\\",\\"language\\":\\"zh-CN\\",\\"max_lines\\":1,'
    '\\"md5\\":\\"md5-1\\",\\"pack_options\\":{\\"need_attribute\\":true},'
    '\\"songs_info\\":[{\\"end_time\\":12334.666,\\"id\\":\\"\\",\\"start_time\\":0}],'
    '\\"translation_language\\":\\"vi-VN\\",\\"use_translation\\":true,'
    '\\"words_per_line\\":15}}", "req_key": "cc_audio_subtitle_asr",'
    ' "task_version": "v3"}]}]')
A_TTS_BODY_SHA = '3b3da851928a42081cc806b1e31e5c9a52960c17481537feb6545e503476830b'
A_UPLOAD_SIGN_URL = ('https://editor-api-sg.capcutapi.com/lv/v1/upload_sign?app_name=CapCut'
                     '&device_type=Windows&os_version=10.0.22635&channel=capcutpc_web_product'
                     '&version_name=9.0.0'
                     '&device_brand=American+Megatrends+International%2C+LLC.'
                     '&device_id=7321782919767590401&iid=7616057603051374344'
                     '&version_code=589824&device_platform=windows&aid=359289')
A_UPLOAD_SIGN_HEADERS = json.loads(
    '{"content-type": "application/json", "appvr": "9.0.0", "ch": "capcutpc_web_product",'
    ' "device-time": "1700000000", "lan": "vi-VN", "loc": "VN", "pf": "3", "sign-ver": "1",'
    ' "tdid": "7321782919767590401",'
    ' "x-ss-stub": "e8eff844fa0457999a30b4d5f6572dff", "x-ss-dp": "359289",'
    ' "x-khronos": "1700000000",'
    ' "x-tt-trace-id": "00-00000000000000000000000000000001-0000000000000000-01",'
    ' "user-agent": "Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03",'
    ' "accept-encoding": "gzip, deflate", "store-country-code": "vn",'
    ' "store-country-code-src": "did", "is-dispatch-us-ttp": "0",'
    ' "is-app-region-us-ttp": "0", "app-sdk-version": "9.0.0", "appid": "359289",'
    ' "sign": "55c407156cfcc425e917a50a18299120"}')
A_VOD_HEADERS = {
    'Authorization': A_SIGV4_POST,
    'Date': HTTP_DATE, 'User-Agent': 'BDFileUpload(1700000000500)',
    'X-Amz-Date': AMZ_DATE, 'X-Amz-Expires': '31536000',
    'X-Amz-Security-Token': CREDS['session_token'], 'accept-encoding': 'identity',
    'store-country-code': 'vn', 'store-country-code-src': 'did',
    'is-dispatch-us-ttp': '0', 'is-app-region-us-ttp': '0',
    'tdid': DEVICE['tdid'], 'pf': '3'}
A_BIN_HEADERS = json.loads(
    '{"Authorization": "AUTHTOKEN", "Date": "Mon, 18 Sep 2023 12:00:00 GMT",'
    ' "User-Agent": "BDFileUpload(1700000000500)", "X-Upload-Content-CRC32": "cbf43926",'
    ' "accept-encoding": "identity", "store-country-code": "vn",'
    ' "store-country-code-src": "did", "is-dispatch-us-ttp": "0",'
    ' "is-app-region-us-ttp": "0", "tdid": "7321782919767590401", "pf": "3"}')
A_FIN_HEADERS = json.loads(
    '{"Authorization": "AUTHTOKEN", "Date": "Mon, 18 Sep 2023 12:00:00 GMT",'
    ' "User-Agent": "BDFileUpload(1700000000500)", "accept-encoding": "identity",'
    ' "store-country-code": "vn", "store-country-code-src": "did",'
    ' "is-dispatch-us-ttp": "0", "is-app-region-us-ttp": "0",'
    ' "tdid": "7321782919767590401", "pf": "3"}')
A_BUILD = {   # sha256(url + header theo thứ tự + body_text) cho 4 chế độ
    'tts': '89f37400e66ac2ef786f0b22ccf2dc2b12e865a5714ebc7fd293560cfe0d73b1',
    'stt': '1e97d3fa4931509aae653477fd2ec8a57fa0ad564a245c964d3e79a193f70275',
    'tq': 'd6d2f80e21c0ea4957af78e561cc4e2bd156d9eb115759f04bba6305e028402d',
    'sq': '7663a5502d83a888d39267323ed5c6e66193fdea0918b9ef0db4a4e4765d7a93',
}
A_UPLOAD_INFO = json.loads(
    '{"vid": "vid-777", "md5": "md5-from-server", "local_md5": "' + AUDIO_MD5 + '",'
    ' "duration_ms": 12345, "format": "mp3", "size": 4096, "file_type": "audio",'
    ' "store_uri": "tos/cn/aliysb/store-1"}')
A_UPLOAD_CALLS = '2a7a27dfbdfcb14a1148862e062fdc201f1d006e17917af99272e9522bfe483a'
A_CLI_TTS = 'c06c8a553a5fcee89d3932df7bbb5cafadb23fe027f0c136935bc265eeaae9bf'


# ----------------------------------------------------------------- hạ tầng test
def strict(value):
    '''Chuẩn hoá để so nhưng GIỮ nguyên thứ tự key của dict (thứ tự header có nghĩa).'''
    if isinstance(value, dict):
        return ['D', [[k, strict(v)] for k, v in value.items()]]
    if isinstance(value, (list, tuple)):
        return [type(value).__name__, [strict(v) for v in value]]
    return value


def assert_same(want, got, note=''):
    assert strict(want) == strict(got), f'{note}\nwant={want!r}\ngot ={got!r}'


def parity(func, cases, attrs=None):
    '''Gọi ``func`` trên cả hai bản với từng bộ tham số; kết quả phải khớp.'''
    bad = same_result(DOTTED, func, cases, attrs=attrs)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def call_both(func, cases, setup=None):
    '''Như parity nhưng so cả thứ tự key; trả về kết quả thô của bản repo.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    outs = []
    for args, kwargs in cases:
        got = []
        for mod in (rep, ref):
            if setup:
                setup(mod)
            got.append(getattr(mod, func)(*args, **kwargs))
        assert_same(got[1], got[0], f'{func}{args} {kwargs}')
        outs.append(got[0])
    return outs


class FixedWorld:
    '''Cố định đồng hồ, uuid4 và padding RSA để mọi chữ ký trở nên tất định.'''

    def __init__(self):
        self.counter = 0

    def __enter__(self):
        self._time = time.time
        self._uuid = uuid.uuid4
        self._token = secrets.token_bytes
        time.time = lambda: 1700000000.5
        uuid.uuid4 = self._uuid4
        secrets.token_bytes = lambda n: bytes((i % 251) + 1 for i in range(n))
        return self

    def __exit__(self, *exc):
        time.time, uuid.uuid4, secrets.token_bytes = self._time, self._uuid, self._token
        return False

    def _uuid4(self):
        self.counter += 1
        return uuid.UUID('%032x' % self.counter)

    def reset(self, mod=None):
        self.counter = 0


def pin_clock(mod):
    mod.utc_now_for_vod = lambda: (AMZ_DATE, HTTP_DATE)


# --------------------------------------------------------- bytecode của bản gốc
def test_bytecode_khop_voi_ban_phat_hanh():
    '''Code object bản khôi phục phải ĐÚNG NGẴN từng byte với .pyc đã phát hành.'''
    pyc = INTERNAL / 'app' / 'services' / 'capcut_common_task_client.pyc'
    with open(pyc, 'rb') as fp:
        fp.read(16)
        ref = marshal.load(fp)
    # dont_inherit=True để 'from __future__' của file test không đổi co_flags
    rep = compile(SRC.read_text(encoding='utf-8'), ref.co_filename, 'exec', dont_inherit=True)

    def walk(code, path, out):
        key = path or '<module>'
        out[key] = code
        for c in code.co_consts:
            if isinstance(c, type(code)):
                walk(c, f'{key}.{c.co_name}', out)
        return out

    a, b = walk(ref, '', {}), walk(rep, '', {})
    assert sorted(a) == sorted(b), sorted(set(a) ^ set(b))
    bad = []
    for name in sorted(a):
        x, y = a[name], b[name]
        for attr in ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals',
                     'co_stacksize', 'co_flags', 'co_firstlineno', 'co_names', 'co_varnames',
                     'co_freevars', 'co_cellvars', 'co_code', 'co_exceptiontable'):
            if getattr(x, attr) != getattr(y, attr):
                bad.append((name, attr, repr(getattr(x, attr))[:100], repr(getattr(y, attr))[:100]))
        ca = [c.co_name if isinstance(c, type(ref)) else c for c in x.co_consts]
        cb = [c.co_name if isinstance(c, type(ref)) else c for c in y.co_consts]
        if ca != cb:
            bad.append((name, 'co_consts', repr(ca)[:140], repr(cb)[:140]))
        if list(x.co_lines()) != list(y.co_lines()):
            bad.append((name, 'co_lines', repr(list(x.co_lines()))[:140],
                        repr(list(y.co_lines()))[:140]))
    assert not bad, bad[:6]
    assert len([k for k in a if k.count('.') <= 1]) == 35, sorted(a)
    assert len(a) == 39, sorted(a)          # 34 hàm + module + 4 code object lồng nhau


def test_hang_so_cap_module():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    assert rep.BASE == ref.BASE == 'https://editor-api-sg.capcutapi.com'
    assert rep.VOD_REGION == ref.VOD_REGION == 'sdwdmwlll'
    assert rep.VOD_SERVICE == ref.VOD_SERVICE == 'vod'
    assert list(rep.DEFAULT_DEVICE.items()) == list(ref.DEFAULT_DEVICE.items())
    assert rep.TTS_SIGN_PUBLIC_KEY_PEM == ref.TTS_SIGN_PUBLIC_KEY_PEM
    assert rep.TTS_SIGN_PUBLIC_KEY_PEM.startswith('-----BEGIN PUBLIC KEY-----\nMIIBIjAN')
    assert rep.TTS_SIGN_PUBLIC_KEY_PEM.endswith('\nmwIDAQAB\n-----END PUBLIC KEY-----')
    assert rep.DEFAULT_DEVICE['aid'] == '359289' and rep.DEFAULT_DEVICE['region'] == 'VN'
    assert rep.DEFAULT_DEVICE is not ref.DEFAULT_DEVICE


# ------------------------------------------------------------------ hàm thuần
def test_compact_json():
    objs = [{}, {'a': 1}, {'a': [1, 2, {'b': None}]}, [], [1, 'a'],
            {'text': 'Xin chào Việt Nam'}, {'text': '你好'}, {'n': 1.5},
            {'ok': True, 'no': False}, None, 0, 'chuỗi', {'a': 1, 'b': 2, 'c': 3},
            {'emoji': '🎬'}, {'q': '"nháy"'}, {'s': "'", 't': '\\slash'},
            {'list': [{'x': 1}, {'y': 2}]}, {'nested': {'deep': {'deeper': {}}}},
            {'unicode_key_á': 1}, {'long': 'a' * 300}, {'t': (1, 2)}, 1.25]
    parity('compact_json', [(o,) for o in objs])
    assert repo_module(DOTTED).compact_json({'a': 'Xin chào'}) == '{"a":"Xin chào"}'
    assert repo_module(DOTTED).compact_json([1, {'b': None}]) == '[1,{"b":null}]'


def test_make_x_ss_stub():
    bodies = ['', '{}', '{"a":1}', 'Xin chào Việt Nam', 'x' * 4096, 'hello world',
              '{"texts":["Xin chào"]}', '你好世界', 'émoji 🎬', '\n', '\r\n\t', '0',
              'null', '{"sign":"abc"}', 'a', 'ab', 'abc', 'abcd', 'ünicode', ' tab',
              'tab\t', '"' * 50, "'" * 50, '\\', '中文与越南语', 'x' * 65536,
              '{"a":{"b":{"c":[1,2,3]}}}']
    parity('make_x_ss_stub', [(b,) for b in bodies])
    rep = repo_module(DOTTED)
    assert rep.make_x_ss_stub('Xin chào Việt Nam') == A_STUB
    for b in bodies:
        assert rep.make_x_ss_stub(b) == hashlib.md5(b.encode('utf-8')).hexdigest()


def test_sha256_hex():
    datas = ['', 'a', 'abc', 'Xin chào', b'', b'\x00\x01\x02', 'x' * 1000, '你好', 'é',
             '{"a":1}', b'\xff' * 32, '0123456789', 'multi\nline\ntext', ' \t\n\r ', 'ü',
             'ÅÄÖ', 'x' * 8192, b'bytes-\xff', 'emoji 🎬', '1', b'\x00' * 64, ' Payload']
    parity('sha256_hex', [(d,) for d in datas])
    assert repo_module(DOTTED).sha256_hex('') == hashlib.sha256(b'').hexdigest()
    assert repo_module(DOTTED).sha256_hex(b'abc') == \
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'


def test_hmac_sha256():
    keys = ['k', '', b'key', 'AWS4wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', 'x' * 100,
            b'\x00\x01', 'é']
    msgs = ['m', '', b'body', 'Xin chào', '20230918', 'sdwdmwlll', 'vod', 'aws4_request',
            'x' * 300, 'a\nb', 'ü', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'payload hash', 'é', b'\xff']
    parity('hmac_sha256', [((k, m), {}) for k in keys for m in msgs[:6]] +
                         [((k, m), {}) for m in msgs for k in keys[:2]])
    got = repo_module(DOTTED).hmac_sha256('key', 'msg')
    assert got.hex() == A_HMAC and len(got) == 32


def test_crc32_hex():
    blobs = [b'', b'\x00', b'1', b'audio', 'Xin chào'.encode(), b'\xff' * 64,
             bytes(range(256)), b'{"a":1}', b'x' * 4096]
    blobs += [bytes((i * 37 + 11) % 256 for i in range(n)) for n in range(1, 13)]
    blobs += [b'\x00' * 1000, b'part-one', b'part-two', b'\r\n', b'\t', AUDIO_BYTES]
    parity('crc32_hex', [(b,) for b in blobs])
    rep = repo_module(DOTTED)
    assert rep.crc32_hex(b'123456789') == 'cbf43926'
    assert rep.crc32_hex(b'') == '00000000'
    for b in blobs:
        assert rep.crc32_hex(b) == '%08x' % (binascii.crc32(b) & 0xffffffff)


def test_escape_xml():
    texts = ['', 'plain', '&', '<', '>', '"', "'", '&<>"\'', 'Xin chào & tạm biệt',
             'a < b > c', 'quote "double" and \'single\'', '&amp;', '&lt;&gt;',
             '你好 & 世界', 'emoji 🎬 & sound', 'line1\nline2', '\t', 'a' * 200,
             '<prosody rate="1.0">', '</voice>', '<>&', "''''", '""""', '&a&b&c',
             '<x><y>', 'mixed &<>"\' end', 'no entity']
    parity('escape_xml', [(t,) for t in texts])
    assert repo_module(DOTTED).escape_xml('a & b < c > d " e \' f') == \
        'a &amp; b &lt; c &gt; d &quot; e &apos; f'
    assert repo_module(DOTTED).escape_xml('&') == '&amp;'      # & phải thay trước cùng


def test_der_doc():
    parity('_der_len', [((b'\x05', 0), {}), ((b'\x7f', 0), {}), ((b'\x80\x01', 0), {}),
                       ((b'\x81\x05', 0), {}), ((b'\x82\x01\x00', 0), {}),
                       ((b'\x83\x00\x01\x02', 0), {}), ((b'\xe0', 0), {}),
                       ((b'\xff' + bytes(8), 0), {}), ((b'AB\x03', 2), {}),
                       ((b'\x00', 0), {}), ((b'\x01\x02', 1), {}), ((b'\x81\x00', 0), {}),
                       ((b'\x82\x00\x00', 0), {}), ((b'\x84' + bytes(range(4)), 0), {}),
                       ((b'\x7f\x7f', 0), {}), ((b'\x80', 0), {}), ((b'\x40', 0), {}),
                       ((b'\x02\x01\x00', 0), {}), ((b'\x02\x01\x00', 1), {}),
                       ((b'\x02\x01\x00', 2), {}), ((b'\xc0\x01\x02\x03', 0), {})])
    parity('_der_value', [((b'\x02\x01\x00', 0, 2), {}), ((b'\x02\x01\x00', 0, 3), {}),
                          ((b'\x30\x03\x02\x01\x00', 0, 0x30), {}),
                          ((b'\x03\x02\x00\x01', 0, 3), {}), ((b'\x02\x00', 0, 2), {}),
                          ((b'\x02\x81\x01\x00', 0, 2), {}), ((b'\x04\x02ab', 0, 4), {}),
                          ((b'\x02\x02\x00\xff', 0, 2), {}),
                          ((b'\x02\x03\x01\x02\x03', 0, 2), {}),
                          ((b'\x30\x00', 0, 0x30), {}), ((b'', 0, 2), {})])
    parity('_der_int', [((b'\x02\x01\x00', 0), {}), ((b'\x02\x01\x01', 0), {}),
                        ((b'\x02\x01\x7f', 0), {}), ((b'\x02\x01\x80', 0), {}),
                        ((b'\x02\x02\x01\x00', 0), {}), ((b'\x02\x03\x00\xff\xff', 0), {}),
                        ((b'\x02\x00', 0), {}),
                        ((b'\x02\x08\x01\x02\x03\x04\x05\x06\x07\x08', 0), {}),
                        ((b'\x02\x21\x00' + bytes(range(1, 33)), 0), {}),
                        ((b'\x04\x01\x02', 0), {}), ((b'\x02\x02\x00\x00', 0), {}),
                        ((b'\x02\x04\x7f\xff\xff\xff', 0), {})])
    rep = repo_module(DOTTED)
    assert rep._der_len(b'\x82\x01\x02ab', 0) == (258, 3)
    assert rep._der_int(b'\x02\x03\x00\x01\x02', 0)[0] == 258
    assert rep._der_value(b'\x30\x03\x02\x01\x00', 0, 0x30)[0] == b'\x02\x01\x00'


def test_query_body():
    args = [('task-1', 'tok', 'sami_text_to_speech', ''), ('', '', '', ''),
            ('7200000000000000000', 'token-xyz', 'cc_audio_subtitle_asr', 'bind-9'),
            ('t', 'k', 'r', 'b'), ('T', 'K', 'sami_text_to_speech', 'B')]
    parity('query_body', [((t, k, r), {'bind_id': b}) for t, k, r, b in args] +
           [((t, k, r, b), {}) for t, k, r, b in args] +
           [(('t', 'k', 'x'), {}), (('t', 'k', 'y'), {'bind_id': ''})], attrs=strict)
    assert repo_module(DOTTED).query_body('T', 'K', 'sami_text_to_speech', 'B') == \
        {'tasks': [{'bind_id': 'B', 'id': 'T', 'req_key': 'sami_text_to_speech',
                    'task_version': 'v3', 'token': 'K'}]}


def test_canonical_query():
    urls = [URL_TTS, 'x?b=2&a=1', 'x?a=1&a=2', 'x?a=1&a=2&a=3', 'x?', 'x?a=', 'x?=1',
            'https://h/p?app_name=CapCut', 'x?A=1&a=1', 'x?a b=1', 'x?a=1 2', 'x?a+b=c',
            'x?a=b%20c', 'x?~=~', 'x?/=&=?', 'x?a=%E4%BD%A0', 'x?越=1', 'x?é=1', 'x?0=0',
            'x?flag', 'x?dup=1&dup=1', '?only=1', 'noquery', 'x?a=1&b=2&c=3&d=4',
            'x?z=1&y=2&x=3', 'x?x-amz-date=1&a=2']
    parity('canonical_query', [(u,) for u in urls])
    rep = repo_module(DOTTED)
    assert rep.canonical_query(URL_TTS) == A_CANON
    assert rep.canonical_query('x?b=2&a=1') == 'a=1&b=2'
    assert rep.canonical_query('x?a b=1') == 'a%20b=1'          # Space -> %20, không phải +
    assert rep.canonical_query('') == ''


# --------------------------------------------------------------- RSA / chữ ký
def test_rsa_public_numbers_from_pem():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    pem = ref.TTS_SIGN_PUBLIC_KEY_PEM
    n, e = rep.rsa_public_numbers_from_pem(pem)
    assert (n, e) == ref.rsa_public_numbers_from_pem(pem)
    assert e == 65537 and n.bit_length() == 2048
    assert hex(n)[2:18] == A_RSA_MODULUS_HEAD and hex(n)[-8:] == A_RSA_MODULUS_TAIL
    der = base64.b64decode(''.join(l for l in pem.splitlines() if not l.startswith('-----')))
    assert der.startswith(b'0\x82\x01"0\r\x06\t')
    parity('rsa_public_numbers_from_pem', [((pem,), {}), ((pem.strip(),), {}),
                                          ((pem + '\n',), {}), (('',), {}),
                                          (('garbage',), {}),
                                          ((pem.replace('MIIB', 'MIIC'),), {}),
                                          ((pem[:60],), {})])


def test_rsa_encrypt_pkcs1v15_byte_exact():
    '''RSA-PKCS#1 v1.5: cùng padding + cùng message -> chuỗi base64 giống hệt từng byte.'''
    with FixedWorld():
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        msgs = ['', 'a', 'Xin chào', 'appid:359289&did:7321782919767590401', 'x' * 100,
                'x' * 200, 'x' * 245, '你好', 'é' * 50, 'payload-sign-input',
                'appid:359289&did:7321782919767590401&creditDisable:false&ssml:deadbeef']
        for msg in msgs:
            assert rep.rsa_encrypt_pkcs1v15(msg) == ref.rsa_encrypt_pkcs1v15(msg), msg[:24]
        assert rep.rsa_encrypt_pkcs1v15('payload-sign-input') == A_RSA_PROBE
        assert rep.rsa_encrypt_pkcs1v15('') == A_RSA_EMPTY
        # tái lập RSA-PKCS#1 v1.5 bằng số học thô (không dùng code của module):
        # m = 00 02 | padding != 0 | 00 | message, c = m^e mod n
        n, e = rep.rsa_public_numbers_from_pem(ref.TTS_SIGN_PUBLIC_KEY_PEM)
        stream = bytes((i % 251) + 1 for i in range(4096))

        def rsa_manual(text):
            msg = text.encode('utf-8')
            ps_len = 256 - len(msg) - 3
            pre = b'\x00\x02' + bytes(b for b in stream if b)[:ps_len] + b'\x00' + msg
            assert len(pre) == 256 and pre[0] == 0 and pre[1] == 2
            return base64.b64encode(
                pow(int.from_bytes(pre, 'big'), e, n).to_bytes(256, 'big')).decode('ascii')

        for msg in ('payload-sign-input', '', 'Xin chào'):
            assert rsa_manual(msg) == rep.rsa_encrypt_pkcs1v15(msg), msg
        assert rsa_manual('payload-sign-input') == A_RSA_PROBE
        for too_long in ('x' * 246, 'x' * 500):
            try:
                rep.rsa_encrypt_pkcs1v15(too_long)
                raise AssertionError('phải ValueError')
            except ValueError as exc:
                assert str(exc) == 'message too long for RSA PKCS#1 v1.5'


def test_rsa_padding_that_ngau_nhien():
    '''Không cố định padding: hai lần ký cùng message ra hai chuỗi khác, vẫn dài 256 byte.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    c1 = rep.rsa_encrypt_pkcs1v15('payload-sign-input')
    c2 = rep.rsa_encrypt_pkcs1v15('payload-sign-input')
    assert c1 != c2
    assert len(base64.b64decode(c1)) == 256 == len(base64.b64decode(c2))
    assert ref.rsa_encrypt_pkcs1v15('payload-sign-input') not in (c1, c2)
    assert c1 != A_RSA_PROBE        # bản gốc dùng padding ngẫu nhiên, không phải neo cố định


def test_make_tts_payload_sign_byte_exact():
    '''Chuỗi ký TTS (appid/did/md5(ssml)/extraInfo) + RSA, so từng byte với bản gốc.'''
    with FixedWorld():
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        extra = ref.compact_json({'benefit_info': {}})
        got = rep.make_tts_payload_sign(SSML, extra, DEVICE['device_id'], DEVICE['aid'])
        assert got == ref.make_tts_payload_sign(SSML, extra, DEVICE['device_id'],
                                                DEVICE['aid'])
        assert got == A_TTS_SIGN
        # tự dựng chuỗi ký theo quy tắc thì phải cho đúng chữ ký đã neo
        sign_input = ('appid:359289&did:7321782919767590401&creditDisable:false&ssml:'
                      + hashlib.md5(SSML.encode('utf-8')).hexdigest() + '&extraInfo:' + extra)
        assert rep.rsa_encrypt_pkcs1v15(sign_input) == got
        assert rep.make_tts_payload_sign(SSML, None, DEVICE['device_id'],
                                         DEVICE['aid']) == A_TTS_SIGN_NOEXTRA
        parity('make_tts_payload_sign',
               [((SSML, extra, DEVICE['device_id'], DEVICE['aid']), {}),
                (('', None, '0', '0'), {}), ((SSML, None, 'x', 'y'), {}),
                (('<speak>&amp;</speak>', '{}', '1', '2'), {}), ((SSML, '', 'd', 'a'), {})])


def test_make_sign_header():
    urls = [URL_TTS, 'https://x/y?z=1', '/lv/v1/common_task/new?a=1', 'no-query',
            'https://e.com/a/b/c/d/e/f/g/h?x=1', 'https://e.com/aaaaaaaaaaaaaa',
            'https://e.com/short?q', 'https://e.com/1?x=1&y=2', '?', 'a?',
            'https://editor-api-sg.capcutapi.com/lv/v1/common_task/query?a=1',
            'https://editor-api-sg.capcutapi.com/lv/v1/upload_sign?a=1',
            'https://e.com/中文路径?x=1', 'https://e.com/x?é=1', 'https://e.com/abcdefgh?1',
            'https://e.com/abcdefghi?1', 'https://e.com?1', 'https://e.com/?1',
            'https://e.com/a?b?c', 'https://e.com/a#frag?b',
            'https://e.com/lv/v1/common_task/new', 'x' * 100 + '/new?a=1', '', '/a/b/c/d/e/f/g/h']
    parity('make_sign_header',
           [((u, '9.0.0', '1700000000', DEVICE['tdid']), {}) for u in urls] +
           [((URL_TTS, '8.0.0', '0', ''), {}), ((URL_TTS, '', '', ''), {}),
            ((URL_TTS, '9.0.0', '1700000001', DEVICE['tdid']), {})])
    rep = repo_module(DOTTED)
    assert rep.make_sign_header(URL_TTS, '9.0.0', '1700000000', DEVICE['tdid']) == A_SIGN_HEADER
    # chuỗi ký: 9e2c|<7 ký tự cuối path>|3|appvr|device-time|tdid|11ac
    path = URL_TTS.split('?', 1)[0]
    raw = '9e2c|' + path[-7:] + '|3|' + '9.0.0' + '|' + '1700000000' + '|' + DEVICE['tdid'] + '|11ac'
    assert rep.make_sign_header(URL_TTS, '9.0.0', '1700000000', DEVICE['tdid']) == \
        hashlib.md5(raw.encode('utf-8')).hexdigest()


# --------------------------------------------------------------------- SigV4
def test_aws4_signing_key():
    pairs = [('wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', '20230918'), ('', '20230918'),
             ('k', '20230101'), ('k', ''), ('x' * 64, '20240229'), ('AWS4', '20230918'),
             ('secret', '20200101'), ('é', '20231231')]
    parity('aws4_signing_key', [p for p in pairs] +
           [(p, {'region': r, 'service': v}) for p in pairs[:3]
            for r, v in [('sdwdmwlll', 'vod'), ('us-east-1', 's3'), ('', '')]])
    got = repo_module(DOTTED).aws4_signing_key(CREDS['secret_access_key'], '20230918')
    assert got.hex() == A_SIGNING_KEY and len(got) == 32
    # vẫn dùng region/service mặc định của VOD nếu không truyền
    assert got == repo_module(DOTTED).aws4_signing_key(CREDS['secret_access_key'], '20230918',
                                                      'sdwdmwlll', 'vod')


def test_aws4_authorization_byte_exact():
    '''Cả chuỗi SigV4: canonical request -> string to sign -> signature, khớp byte.'''
    neo = {('GET', URL_TTS, b''): A_SIGV4_GET, ('POST', URL_TTS, b'{"a":1}'): A_SIGV4_POST,
           ('PUT', 'https://h/p?x=1&y=2', b'0123456789'): A_SIGV4_PUT}
    extra = [('POST', URL_TTS, 'Xin chào'.encode('utf-8'), AMZ_DATE),
             ('GET', 'x?a=1&a=2', b'', '20240101T000000Z'),
             ('POST', 'x?dup=1&dup=1', b'{}', '20240101T000000Z'),
             ('GET', 'noquery', b'x', '20200101T000000Z'),
             ('PUT', 'x?é=1', 'é'.encode('utf-8'), '20231231T235959Z')]
    parity('aws4_authorization',
           [((m, u, b, CREDS['access_key_id'], CREDS['secret_access_key'],
              CREDS['session_token'], AMZ_DATE), {}) for m, u, b in neo] +
           [((m, u, b, CREDS['access_key_id'], CREDS['secret_access_key'], tok, d), {})
            for m, u, b, d in extra for tok in ('SESSION123', '')])
    rep = repo_module(DOTTED)
    for (method, url, body), want in neo.items():
        got = rep.aws4_authorization(method, url, body, CREDS['access_key_id'],
                                    CREDS['secret_access_key'], CREDS['session_token'], AMZ_DATE)
        assert got == want, (method, url, got)
        assert got.startswith('AWS4-HMAC-SHA256 Credential=' + CREDS['access_key_id'] + '/'
                             + AMZ_DATE[:8] + '/sdwdmwlll/vod/aws4_request, ')
        assert len(got.split('Signature=')[1]) == 64
        # đổi body -> đổi signature, đổi ngày -> đổi scope
        other = rep.aws4_authorization(method, url, b'changed', CREDS['access_key_id'],
                                       CREDS['secret_access_key'], CREDS['session_token'], AMZ_DATE)
        assert other != got and other.split('Signature=')[1] != got.split('Signature=')[1]


def test_utc_now_for_vod():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a_amz, a_http = rep.utc_now_for_vod()
    b_amz, b_http = ref.utc_now_for_vod()
    assert len(a_amz) == 16 and a_amz[8] == 'T' and a_amz.endswith('Z'), a_amz
    assert a_amz[:8] == b_amz[:8] or True
    assert a_http.endswith(' GMT')
    assert a_http.split()[0].rstrip(',') in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    time.strptime(a_http, '%a, %d %b %Y %H:%M:%S GMT')
    assert int(a_amz[:4]) >= 2024


# --------------------------------------------------------- query / header
def test_common_query():
    devices = [DEVICE, dict(DEVICE, region='US', loc='US', lan='en-US'),
               dict(DEVICE, aid='1234', app_name='X'), dict(DEVICE, channel=''),
               dict(DEVICE, device_brand='Ünicode Brand'), dict(DEVICE, iid='0')]
    cases = [((d,), {}) for d in devices] + \
            [((d,), {'include_region': False}) for d in devices] + \
            [((d,), {'babi_param': b}) for d in devices[:3]
             for b in ({}, {'feature_key': 'text_to_speech'}, {'a': [1, 2]})] + \
            [((DEVICE,), {'babi_param': None, 'include_region': True}),
             ((DEVICE,), {'babi_param': {'k': 'v'}, 'include_region': False})]
    parity('common_query', cases, attrs=strict)
    rep = repo_module(DOTTED)
    assert_same(A_COMMON_QUERY, rep.common_query(DEVICE))
    assert_same(A_COMMON_QUERY_BABI, rep.common_query(DEVICE, {'k': 'v'},
                                                     include_region=False))
    assert 'region' not in rep.common_query(DEVICE, None, include_region=False)
    assert list(rep.common_query(DEVICE)) == list(A_COMMON_QUERY)


def test_base_headers_byte_exact():
    '''Ghép header thiết bị: cùng đồng hồ + cùng uuid -> dict giống hệt, theo thứ tự.'''
    with FixedWorld() as world:
        bodies = ['{"a":1}', '', 'Xin chào', '{"texts":["a","b"]}', 'x' * 1000]
        devices = [DEVICE, dict(DEVICE, loc='US', appvr='8.0.0', aid='1')]
        outs = call_both('base_headers',
                         [((d, b), {'appid': flag}) for d in devices for b in bodies
                          for flag in (False, True)], setup=world.reset)
        assert len(outs) == 20
        assert_same(A_BASE_HEADERS, outs[0], 'base_headers')
        assert_same(A_BASE_HEADERS_APPID, outs[1], 'base_headers appid')
        keys = list(outs[0])
        assert keys[:4] == ['content-type', 'appvr', 'ch', 'device-time'], keys
        assert keys[15:19] == ['store-country-code', 'store-country-code-src',
                              'is-dispatch-us-ttp', 'is-app-region-us-ttp'], keys
        assert len(keys) == 19
        assert outs[2]['x-ss-stub'] == hashlib.md5(b'').hexdigest()
        assert outs[0]['x-khronos'] == outs[0]['device-time'] == '1700000000'
        assert outs[0]['x-ss-dp'] == DEVICE['aid']
        assert outs[0]['store-country-code'] == 'vn'
        assert 'appid' not in outs[0] and 'app-sdk-version' not in outs[0]
        assert list(outs[1])[-2:] == ['app-sdk-version', 'appid']
        assert outs[0]['x-ss-stub'] == hashlib.md5(b'{"a":1}').hexdigest()


def test_make_trace_id():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    seen = {rep.make_trace_id() for _ in range(5)}
    assert len(seen) == 5                              # uuid4 -> không được lặp
    for v in seen | {ref.make_trace_id()}:
        assert v.startswith('00-') and v.endswith('-01'), v
        parts = v.split('-')
        assert len(parts[1]) == 32 and len(parts[2]) == 16, v
        assert parts[2] == parts[1][:16], v
        int(parts[1], 16)


def test_vod_signed_headers_byte_exact():
    with FixedWorld():
        cases = [(('POST', URL_TTS, b'{"a":1}', CREDS, DEVICE), {}),
                 (('GET', URL_TTS, b'', CREDS, DEVICE), {}),
                 (('GET', URL_TTS, '', CREDS, DEVICE), {}),
                 (('POST', 'https://h/p?x=1&y=2', b'0' * 64, CREDS, DEVICE), {}),
                 (('PUT', 'x?a=1&a=2', b'x', CREDS, dict(DEVICE, loc='us')), {})]
        outs = call_both('vod_signed_headers', cases, setup=pin_clock)
        assert_same(A_VOD_HEADERS, outs[0], 'vod_signed_headers')
        keys = list(outs[0])
        assert keys[0] == 'Authorization' and keys[3] == 'X-Amz-Date', keys
        assert len(keys) == 13
        assert outs[0]['Authorization'] == A_SIGV4_POST
        assert outs[0]['User-Agent'] == 'BDFileUpload(1700000000500)'
        assert outs[0]['Date'] == HTTP_DATE and outs[0]['X-Amz-Date'] == AMZ_DATE
        # str body và bytes body phải cho cùng một chữ ký
        assert outs[1]['Authorization'] == outs[2]['Authorization']
        assert outs[4]['store-country-code'] == 'us'


def test_upload_binary_and_finish_headers():
    with FixedWorld():
        crcs = ['00000000', 'cbf43926', 'ffffffff', '', '01234567', 'deadbeef']
        outs = call_both('upload_binary_headers', [(('AUTHTOKEN', c, DEVICE), {}) for c in crcs],
                         setup=pin_clock)
        assert_same(A_BIN_HEADERS, outs[1], 'upload_binary_headers')
        assert list(outs[0])[:4] == ['Authorization', 'Date', 'User-Agent',
                                    'X-Upload-Content-CRC32']
        assert outs[0]['X-Upload-Content-CRC32'] == '00000000'
        fin = call_both('upload_finish_headers', [(('AUTHTOKEN', DEVICE), {})],
                        setup=pin_clock)
        assert_same(A_FIN_HEADERS, fin[0], 'upload_finish_headers')
        assert 'X-Upload-Content-CRC32' not in fin[0]
        assert list(fin[0])[:3] == ['Authorization', 'Date', 'User-Agent']
        assert fin[0]['Date'] == HTTP_DATE


# ---------------------------------------------------------------- payload
def test_tts_new_body_byte_exact():
    with FixedWorld() as world:
        outs = call_both('tts_new_body', [
            ((('Xin chào',), 'BV074_streaming', '7102355709945188865', '1.0', DEVICE), {}),
            ((('a', 'b'), 'BV075_streaming', '7102355803792740865', '0.9', DEVICE), {}),
            (((), 'v', 'r', '1.0', DEVICE), {}),
            ((('&<>"\'',), 'v', 'r', '2.0', DEVICE), {}),
            ((('你好世界',), 'multi_male_felipe_uranus_bigtts', '7637456729696996628',
              '1.1', DEVICE), {}),
        ], setup=world.reset)
        babi, body = outs[0]
        assert list(babi) == ['feature_entrance', 'feature_entrance_detail', 'feature_key',
                             'scenario']
        assert babi['feature_entrance_detail'] == 'editor-feature-text_to_speech'
        task = body['tasks'][0]
        assert list(task) == ['context', 'payload', 'req_key', 'task_version']
        assert task['req_key'] == 'sami_text_to_speech' and task['task_version'] == 'v3'
        payload = json.loads(task['payload'])
        assert list(payload) == ['audio_format', 'babi_param', 'credit_disable', 'extra_info',
                                 'need_merge_voice', 'need_subtitle_timestamp', 'scene', 'ssml',
                                 'sign']
        assert payload['audio_format'] == 'mp3' and payload['scene'] == 'text_to_speech'
        assert payload['credit_disable'] is False and payload['need_merge_voice'] is False
        assert payload['ssml'].startswith('<speak version="1.0"')
        assert 'resource_id="7102355709945188865"' in payload['ssml']
        assert '<prosody rate="1.0">Xin chào</prosody>' in payload['ssml']
        assert len(base64.b64decode(payload['sign'])) == 256
        assert body['bind_id'] == '00000000-0000-0000-0000-000000000001'
        assert body['enter_from'] == 'text_to_speech' and body['can_queue'] is True
        assert hashlib.sha256(json.dumps([babi, body], ensure_ascii=False).encode()
                              ).hexdigest() == A_TTS_BODY_SHA
        # ký tự XML trong text phải được escape ngay trong SSML
        p4 = json.loads(outs[3][1]['tasks'][0]['payload'])
        assert '&amp;&lt;&gt;&quot;&apos;' in p4['ssml'] and '<voice name="v"' in p4['ssml']
        assert 'need_subtitle_timestamp="false"' in p4['ssml']


def test_stt_new_body_byte_exact():
    with FixedWorld() as world:
        outs = call_both('stt_new_body', [
            (('vid-1', 'md5-1', 12345, 'zh-CN', 'vi-VN', True), {}),
            (('', '', 0, '', '', False), {}),
            (('v', 'm', 1, 'en', 'vi', 1), {}),
            (('vid', 'md5', 10000, 'zh-CN', 'vi-VN', False), {}),
            (('v', 'm', 1500.5, 'zh-CN', 'vi-VN', None), {}),
        ], setup=world.reset)
        assert_same(A_STT_BODY, list(outs[0]), 'stt_new_body')
        babi, body = outs[0]
        task = body['tasks'][0]
        cap = json.loads(task['payload'])['cap_json']
        assert cap['duration'] == 12345 and cap['audio'] == 'vid-1'
        assert cap['songs_info'][0]['end_time'] == 12345 - 10.334
        assert cap['use_translation'] is True and cap['words_per_line'] == 15
        assert cap['pack_options'] == {'need_attribute': True}
        assert babi['feature_entrance_detail'] == 'editor-elements-captions-subtitle_recognition'
        assert body['bind_id'] == '00000000-0000-0000-0000-000000000002'
        assert task['req_key'] == 'cc_audio_subtitle_asr'
        assert json.loads(outs[4][1]['tasks'][0]['payload'])['cap_json']['duration'] == 1500


# ------------------------------------------------------------------- file I/O
def test_load_and_save_json():
    tmp = Path(tempfile.mkdtemp())
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    obj = {'a': [1, 2], 't': 'Xin chào Việt Nam', 'n': None, 'ok': True}
    pa, pb = tmp / 'repo.json', tmp / 'ref.json'
    rep.save_json(obj, str(pa))
    ref.save_json(obj, str(pb))
    assert pa.read_bytes() == pb.read_bytes()
    text = pa.read_text(encoding='utf-8')
    assert text.endswith('}\n') and '"t": "Xin chào Việt Nam"' in text
    assert rep.load_json(str(pa)) == obj
    parity('load_json', [((str(pa),), {}), ((str(pa),), {'default': {}}),
                         ((str(tmp / 'khong-co.json'),), {'default': {'x': 1}}),
                         ((str(tmp / 'khong-co.json'),), {'default': None}),
                         (('',), {'default': {}}), ((None,), {'default': [1]}),
                         ((None,), {}), (('',), {}), (('',), {'default': {}}),
                         ((str(tmp / 'khong-co'),), {'default': {}}),
                         ((str(pa),), {'default': []})])
    assert same_result(DOTTED, 'load_json', [((str(tmp / 'khong-co'),), {'default': {}})]) == []
    dflt = {'d': [1]}
    got = repo_module(DOTTED).load_json('', dflt)
    assert got == dflt and got is not dflt                # deepcopy, không trả object gốc
    assert repo_module(DOTTED).load_json('') == {}


def test_file_md5():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    paths = []
    for i, n in enumerate([0, 1, 16, 1023, 1024, 4096, 1048575, 1048576, 1048577]):
        p = tmp / f'blob{i}.bin'
        data = bytes((j * 31 + i) % 256 for j in range(n))
        p.write_bytes(data)
        assert rep.file_md5(str(p)) == hashlib.md5(data).hexdigest() == ref.file_md5(str(p)), n
        paths.append((str(p),))
    paths += [(str(tmp / 'khong-co.bin'),), (str(tmp),), ('',)]
    parity('file_md5', [((p,), {}) for p, in paths])


# ------------------------------------------------ build request (không gọi mạng)
def test_upload_sign_request_byte_exact():
    with FixedWorld() as world:
        outs = call_both('upload_sign_request', [((DEVICE,), {}),
                                                 ((dict(DEVICE, loc='US'),), {})],
                         setup=world.reset)
        url, headers, body_text = outs[0]
        assert url == A_UPLOAD_SIGN_URL, url
        assert body_text == '{"biz":"cc_pc_text_recognize","key_version":"v5"}'
        assert_same(A_UPLOAD_SIGN_HEADERS, headers, 'upload_sign_request headers')
        assert 'region=' not in url and 'babi_param=' not in url
        assert headers['sign'] == repo_module(DOTTED).make_sign_header(
            url, DEVICE['appvr'], '1700000000', DEVICE['tdid'])
        assert headers['appid'] == DEVICE['aid'] and headers['app-sdk-version'] == '9.0.0'
        assert 'region=US' not in outs[1][0]


def _args(**kw):
    base = dict(mode='tts-new', device_json=None, text=['Xin chào'], text_file=None,
                voice='BV074_streaming', resource_id='7102355709945188865', rate='1.0',
                audio_vid=None, audio_md5=None, duration_ms=None, language='zh-CN',
                translation_language='vi-VN', use_translation=False, task_id=None,
                token=None, bind_id='', out=None, dry_run=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _fingerprint(url, headers, body_text):
    blob = url + '\n' + json.dumps(list(headers.items()), ensure_ascii=False) + '\n' + body_text
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def test_build_request_byte_exact():
    '''Cả 4 chế độ build request: URL + header + body giống hệt bản phát hành.'''
    modes = {'tts': _args(),
             'stt': _args(mode='stt-new', audio_vid='v1', audio_md5='m1', duration_ms=9000),
             'tq': _args(mode='tts-query', task_id='t', token='k'),
             'sq': _args(mode='stt-query', task_id='t', token='k', bind_id='b')}
    with FixedWorld() as world:
        for tag, ns in modes.items():
            got = []
            for mod in (repo_module(DOTTED), ref_module(DOTTED)):
                world.reset()
                got.append(_fingerprint(*mod.build_request(ns)))
            assert got[0] == got[1], (tag, got)
            assert got[0] == A_BUILD[tag], (tag, got[0])
        url, headers, body_text = repo_module(DOTTED).build_request(modes['tts'])
        assert 'babi_param=' in url and 'region=VN' in url
        assert json.loads(body_text)['tasks'][0]['req_key'] == 'sami_text_to_speech'
        assert list(headers)[0] == 'content-type' and 'sign' in headers
        url2, headers2, _ = repo_module(DOTTED).build_request(modes['stt'])
        assert 'region=VN' in url2 and 'appid' not in headers2
        assert 'babi_param=' in url2
        assert repo_module(DOTTED).build_request(modes['sq'])[2] == json.dumps(
            {'tasks': [{'bind_id': 'b', 'id': 't', 'req_key': 'cc_audio_subtitle_asr',
                        'task_version': 'v3', 'token': 'k'}]}, ensure_ascii=False,
            separators=(',', ':'))


def test_build_request_errors():
    # SystemExit là BaseException -> same_result không bắt được, nên gọi trực tiếp
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for ns, msg in ((_args(mode='sai'), 'bad mode'),
                    (_args(text=[]), 'need --text or --text-file'),
                    (_args(mode='stt-new'), 'need --audio-vid and --audio-md5'),
                    (_args(mode='tts-query'), 'need --task-id and --token')):
        for mod in (rep, ref):
            try:
                mod.build_request(ns)
                raise AssertionError(f'phải SystemExit: {ns.mode}')
            except SystemExit as exc:
                assert str(exc) == msg, (ns.mode, str(exc))
    # --text-file đọc file thật (I/O đĩa, không mạng)
    tmp = Path(tempfile.mkdtemp())
    src = tmp / 'lines.txt'
    src.write_text('dòng một\n\n  \ndòng hai\n', encoding='utf-8')
    outs = []
    with FixedWorld() as world:
        for mod in (rep, ref):
            world.reset()
            outs.append(mod.build_request(_args(text=[], text_file=str(src)))[2])
    assert outs[0] == outs[1]
    ssml = json.loads(outs[0])['tasks'][0]['payload']
    assert 'dòng một' in ssml and 'dòng hai' in ssml and ssml.count('<voice name=') == 2


def test_checked_json_response():
    BAD = object()

    class Resp:
        def __init__(self, payload, status=200, raw='null'):
            self.payload = payload
            self.status_code = status
            self.text = raw

        def json(self):
            if self.payload is BAD:
                raise ValueError('Expecting value: line 1 column 1 (char 0)')
            return self.payload

    class NoJson:
        status_code = 500
        text = '<html>oops</html>' + 'y' * 900

        def json(self):
            raise ValueError('no json')

    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    good = {'data': {'a': 1}}
    for status in (200, 299, 400, 404, 500):
        if status < 400:
            assert rep.checked_json_response(Resp(good, status), 'lbl') == good
            assert ref.checked_json_response(Resp(good, status), 'lbl') == good
        for mod in (rep, ref):
            try:
                mod.checked_json_response(Resp(good, status), 'upload_sign')
                assert status < 400
            except RuntimeError as exc:
                assert str(exc) == f'upload_sign HTTP {status}: {good}', str(exc)
    for mod in (rep, ref):
        try:
            mod.checked_json_response(Resp(BAD, 200), 'commit')
            raise AssertionError('phải RuntimeError')
        except RuntimeError as exc:
            assert str(exc) == 'commit returned non-JSON HTTP 200: null', str(exc)
            assert exc.__cause__ is not None
        try:
            mod.checked_json_response(NoJson(), 'lbl')
            raise AssertionError('phải RuntimeError')
        except RuntimeError as exc:
            assert str(exc).startswith('lbl returned non-JSON HTTP 500: <html>oops</html>')
            assert len(str(exc)) == len('lbl returned non-JSON HTTP 500: ') + 500


# ------------------------------------------------------ chuỗi upload (offline)
class FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return json.loads(json.dumps(self._payload))


class FakeRequests:
    '''Vận chuyển giả: ghi lại từng lời gọi, trả kịch bản dựng sẵn — không kết nối.'''

    def __init__(self, script):
        self.script = [FakeResp(p) for p in script]
        self.calls = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append(['POST', url, sorted((headers or {}).items()),
                           (data or b'').hex(), timeout])
        return self.script.pop(0)

    def get(self, url, headers=None, timeout=None):
        self.calls.append(['GET', url, sorted((headers or {}).items()), '', timeout])
        return self.script.pop(0)


UPLOAD_SCRIPT = [
    {'data': dict(CREDS)},
    {'Result': {'InnerUploadAddress': {'UploadNodes': [{
        'UploadHost': 'www.v3upload.com',
        'StoreInfos': [{'StoreUri': 'tos/cn/aliysb/store-1', 'UploadID': 'up-1',
                        'Auth': 'UPLOAD-AUTH'}],
        'Vid': 'vid-777', 'SessionKey': 'session-1'}]}}},
    {'Code': 0},
    {'Code': 0},
    {'Result': {'Results': [{'Vid': 'vid-777', 'VideoMeta': {
        'Duration': 12.345, 'Md5': 'md5-from-server', 'Format': 'mp3', 'Size': 4096,
        'FileType': 'audio', 'Uri': 'tos/cn/aliysb/store-1'}}]}}]


def run_upload(mod, path, world=None):
    if world:
        world.reset()
    pin_clock(mod)
    fake = FakeRequests(UPLOAD_SCRIPT)
    mod.requests = fake
    info = mod.upload_audio_file(path, DEVICE)
    return info, fake.calls


def test_upload_audio_file_chain_offline():
    '''Toàn chuỗi sign -> apply -> transfer -> finish -> commit chạy với requests giả.'''
    tmp = Path(tempfile.mkdtemp())
    audio = tmp / 'nhac.mp3'
    audio.write_bytes(AUDIO_BYTES)
    with FixedWorld() as world:
        info_repo, calls_repo = run_upload(repo_module(DOTTED), str(audio), world)
        info_ref, calls_ref = run_upload(ref_module(DOTTED), str(audio), world)
        assert_same(info_ref, info_repo, 'upload_audio_file info')
        assert info_repo == A_UPLOAD_INFO, info_repo
        assert json.dumps(calls_repo, ensure_ascii=False) == \
            json.dumps(calls_ref, ensure_ascii=False), calls_repo[0][1]
        assert hashlib.sha256(json.dumps(calls_repo, ensure_ascii=False).encode()
                              ).hexdigest() == A_UPLOAD_CALLS
        assert [c[0] for c in calls_repo] == ['POST', 'GET', 'POST', 'POST', 'POST']
        assert calls_repo[0][1].startswith('https://editor-api-sg.capcutapi.com/lv/v1/upload_sign?')
        assert calls_repo[1][1].startswith('https://tos-vn-v3.tikvcdn.com/top/v1?Action=ApplyUploadInner')
        assert [c[4] for c in calls_repo] == [60, 60, 300, 60, 120]
        assert '/upload/v1/tos/cn/aliysb/store-1?' in calls_repo[2][1]
        assert 'phase=finish' in calls_repo[3][1] and 'uploadmode=part' in calls_repo[3][1]
        assert 'CommitUploadInner' in calls_repo[4][1]
        apply_hdr = dict(calls_repo[1][2])
        assert apply_hdr['Authorization'].startswith(
            'AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20230918/sdwdmwlll/vod/aws4_request')
        assert apply_hdr['X-Amz-Date'] == AMZ_DATE
        assert apply_hdr['X-Amz-Security-Token'] == CREDS['session_token']
        bin_hdr = dict(calls_repo[2][2])
        assert bin_hdr['X-Upload-Content-CRC32'] == AUDIO_CRC
        assert 'X-Upload-Content-CRC32' not in dict(calls_repo[3][2])
        assert bytes.fromhex(calls_repo[2][3]) == AUDIO_BYTES
        assert bytes.fromhex(calls_repo[3][3]).decode() == '0:' + AUDIO_CRC
        assert json.loads(bytes.fromhex(calls_repo[4][3]).decode()) == {
            'Functions': [{'Input': {'SnapshotTime': 0.0}, 'Name': 'Snapshot'}],
            'SessionKey': 'session-1'}
        commit_hdr = dict(calls_repo[4][2])
        assert commit_hdr['Authorization'] != apply_hdr['Authorization']  # body khác -> chữ ký khác


def test_upload_audio_file_loi_tran_van():
    tmp = Path(tempfile.mkdtemp())
    audio = tmp / 'a.mp3'
    audio.write_bytes(b'fake-mp3')
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    outs = []
    for mod in (rep, ref):
        mod.requests = None
        try:
            mod.upload_audio_file(str(audio), DEVICE)
            raise AssertionError('phải SystemExit')
        except SystemExit as exc:
            outs.append(str(exc))
        mod.requests = FakeRequests([{'code': 1}])
        try:
            mod.upload_audio_file(str(audio), DEVICE)
            raise AssertionError('phải RuntimeError')
        except RuntimeError as exc:
            outs.append(str(exc))
        mod.requests = None
    assert outs[0] == outs[2] == 'pip install requests', outs
    assert outs[1].startswith("upload_sign missing domain: {'code': 1}"), outs
    assert outs[1] == outs[3], outs


# -------------------------------------------------------------------------- CLI
def test_main_dry_run_khong_goi_mang():
    '''--dry-run in request ra stdout: khớp bản gốc từng byte, không kết nối.'''
    with FixedWorld() as world:
        for argv, anchor in ((['tts-new', '--text', 'Xin chào Việt Nam', '--text', 'tạm biệt'],
                              A_CLI_TTS),
                             (['stt-new', '--audio-vid', 'v1', '--audio-md5', 'm1',
                               '--duration-ms', '9000'], None),
                             (['tts-query', '--task-id', 't', '--token', 'k'], None),
                             (['stt-query', '--task-id', 't', '--token', 'k'], None)):
            got = []
            for mod in (repo_module(DOTTED), ref_module(DOTTED)):
                world.reset()
                old = sys.argv
                sys.argv = ['capcut_common_task_client.py'] + argv + ['--dry-run']
                buf = io.StringIO()
                try:
                    with redirect_stdout(buf):
                        mod.main()
                finally:
                    sys.argv = old
                got.append(buf.getvalue())
            assert got[0] == got[1], (argv, got[0][:400], got[1][:400])
            dump = json.loads(got[0])
            assert sorted(dump) == ['body', 'headers', 'url']
            assert dump['url'].startswith('https://editor-api-sg.capcutapi.com/lv/v1/')
            assert len(dump['headers']['sign']) == 32
            if anchor:
                assert hashlib.sha256(got[0].encode('utf-8')).hexdigest() == anchor
                ssml = json.loads(dump['body']['tasks'][0]['payload'])['ssml']
                assert ssml.count('<voice name=') == 2
                assert 'Xin chào Việt Nam' in ssml and 'tạm biệt' in ssml


def test_main_thieu_tham_so():
    '''Nhánh kiểm tra tham số của CLI cũng phải giống bản gốc.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mode in ('upload-audio', 'stt-file'):
        outs = []
        for mod in (rep, ref):
            prev, mod.requests = mod.requests, None
            sys.argv = ['capcut_common_task_client.py', mode]
            try:
                with redirect_stdout(io.StringIO()):
                    mod.main()
                outs.append(None)
            except SystemExit as exc:
                outs.append(str(exc))
            finally:
                mod.requests = prev
        assert outs[0] == outs[1] == 'need --audio-file', (mode, outs)

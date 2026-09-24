# -*- coding: utf-8 -*-
import argparse
import base64
import binascii
import datetime as dt
import hashlib
import hmac
import json
import secrets
import time
import uuid
from copy import deepcopy
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

try:
    import requests
except ImportError:
    requests = None

# Endpoint + hồ sơ device "chuẩn" của CapCut PC 9.0.0 (region VN) — khớp bản đã phát hành.
BASE = 'https://editor-api-sg.capcutapi.com'
VOD_REGION = 'sdwdmwlll'
VOD_SERVICE = 'vod'


# Device fallback: chỉ dùng khi máy chưa có capcut_device.json của người dùng.
DEFAULT_DEVICE = {
    'aid': '359289',
    'app_name': 'CapCut',
    'appvr': '9.0.0',
    'version_name': '9.0.0',
    'version_code': '589824',
    'channel': 'capcutpc_web_product',
    'device_platform': 'windows',
    'device_type': 'Windows',
    'device_brand': 'American Megatrends International, LLC.',
    'os_version': '10.0.22635',
    'device_id': '7321782919767590401',
    'iid': '7616057603051374344',
    'region': 'VN',
    'loc': 'VN',
    'lan': 'vi-VN',
    # pf = mã platform của CapCut bản desktop
    'pf': '3',
    'tdid': '7321782919767590401',
}

TTS_SIGN_PUBLIC_KEY_PEM = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmTd34Lw4b7IuldSXh/zY
CMla+ITdGG5TeWz6ad+OySd4r+IrY45AoqrYUxhQ2dl+7z+i7r/5vEa8rr39BYfB
8AGMQLmZA8HmgpWBsqrn/V6daUALkKnkLb70Fn32CJigIuGXAYqxUdGuI340aC+0
v5Es3puJsHyzf01/AelE4Cdc6bZhQrASJLBh8R3BQToYClmDVSDUQk28o8sl/guA
Z4n303Vj+6Siv1HayPCdV6kpVVnMBAG4+umUbwGmn132N3fgpzLarFF3XyWmS1zh
D/J07iM/rP8GDO9IskHNHd2phrO0G6KzrcFAnTBHjVv+hCBEfzN/no3FNA9AuC36
mwIDAQAB
-----END PUBLIC KEY-----'''


def compact_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def load_json(path, default=None):
    if not path:
        return deepcopy(default) if default is not None else {}
    with open(path, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def save_json(obj, path):
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump(obj, fp, ensure_ascii=False, indent=2)
        fp.write('\n')


def make_x_ss_stub(body_text):
    return hashlib.md5(body_text.encode('utf-8')).hexdigest()

def _der_len(data, pos):
    first = data[pos]
    pos += 1
    if first < 128:
        return first, pos
    nbytes = first & 127
    return int.from_bytes(data[pos:pos + nbytes], 'big'), pos + nbytes

def _der_value(data, pos, tag):
    if data[pos] != tag:
        raise ValueError(f'bad DER tag: expected 0x{tag:02x}, got 0x{data[pos]:02x}')
    length, pos = _der_len(data, pos + 1)
    return data[pos:pos + length], pos + length

def _der_int(data, pos):
    raw, pos = _der_value(data, pos, 0x02)
    return int.from_bytes(raw.lstrip(b'\x00'), 'big'), pos

def rsa_public_numbers_from_pem(pem):
    b64 = ''.join(line for line in pem.splitlines() if not line.startswith('-----'))
    der = base64.b64decode(b64)
    outer, pos = _der_value(der, 0, 48)
    if pos != len(der):
        raise ValueError('trailing data in public key')
    _, pos = _der_value(outer, 0, 48)
    bit_string, pos = _der_value(outer, pos, 3)
    if pos != len(outer) or not bit_string or bit_string[0] != 0:
        raise ValueError('bad subjectPublicKeyInfo')
    rsa_seq, pos = _der_value(bit_string[1:], 0, 48)
    if pos != len(bit_string[1:]):
        raise ValueError('trailing data in RSA public key')
    modulus, pos = _der_int(rsa_seq, 0)
    exponent, pos = _der_int(rsa_seq, pos)
    if pos != len(rsa_seq):
        raise ValueError('trailing integer data in RSA public key')
    return modulus, exponent

def rsa_encrypt_pkcs1v15(message, pem=TTS_SIGN_PUBLIC_KEY_PEM):
    modulus, exponent = rsa_public_numbers_from_pem(pem)
    key_len = (modulus.bit_length() + 7) // 8
    msg = message.encode('utf-8') if isinstance(message, str) else bytes(message)
    if len(msg) > key_len - 11:
        raise ValueError('message too long for RSA PKCS#1 v1.5')
    ps_len = key_len - len(msg) - 3
    ps = bytearray()
    while len(ps) < ps_len:
        chunk = secrets.token_bytes(ps_len - len(ps))
        ps.extend(b for b in chunk if b != 0)
    encoded = b'\x00\x02' + bytes(ps[:ps_len]) + b'\x00' + msg
    encrypted = pow(int.from_bytes(encoded, 'big'), exponent, modulus).to_bytes(key_len, 'big')
    return base64.b64encode(encrypted).decode('ascii')

def make_tts_payload_sign(ssml, extra_info, device_id, app_id):
    ssml_md5 = hashlib.md5(ssml.encode('utf-8')).hexdigest()
    sign_input = f'appid:{app_id}&did:{device_id}&creditDisable:false&ssml:{ssml_md5}'
    if extra_info is not None:
        sign_input += f'&extraInfo:{extra_info}'
    return rsa_encrypt_pkcs1v15(sign_input)

def make_sign_header(url, appvr, device_time, tdid):
    path = url.split('?', 1)[0]
    sign_str = f'9e2c|{path[-7:]}|3|{appvr}|{device_time}|{tdid}|11ac'
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

def sha256_hex(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def hmac_sha256(key, msg):
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).digest()

def aws4_signing_key(secret_access_key, date_stamp, region=VOD_REGION, service=VOD_SERVICE):
    k_date = hmac_sha256('AWS4' + secret_access_key, date_stamp)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    return hmac_sha256(k_service, 'aws4_request')

def canonical_query(url):
    pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    return '&'.join(
        quote(str(k), safe='-_.~') + '=' + quote(str(v), safe='-_.~') for k, v in sorted(pairs))


def aws4_authorization(method, url, body, access_key_id, secret_access_key, session_token, amz_date):
    date_stamp = amz_date[:8]
    scope = f'{date_stamp}/{VOD_REGION}/{VOD_SERVICE}/aws4_request'
    signed_headers = 'x-amz-date;x-amz-security-token'
    canonical_headers = f'x-amz-date:{amz_date}\nx-amz-security-token:{session_token}\n'
    canonical_request = '\n'.join(
        [method, urlsplit(url).path, canonical_query(url), canonical_headers, signed_headers, sha256_hex(body)]
    )
    string_to_sign = '\n'.join(
        ['AWS4-HMAC-SHA256', amz_date, scope, sha256_hex(canonical_request)]
    )
    signature = hmac.new(
        aws4_signing_key(secret_access_key, date_stamp), string_to_sign.encode('utf-8'), hashlib.sha256
    ).hexdigest()
    return f'AWS4-HMAC-SHA256 Credential={access_key_id}/{scope}, SignedHeaders={signed_headers}, Signature={signature}'

def utc_now_for_vod():
    now = dt.datetime.now(dt.timezone.utc)
    return now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%a, %d %b %Y %H:%M:%S GMT')

def file_md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def crc32_hex(data):
    return f'{binascii.crc32(data) & 0xffffffff:08x}'


def common_query(device, babi_param=None, include_region=True):
    q = {
        'app_name': device['app_name'],
        'device_type': device['device_type'],
        'os_version': device['os_version'],
        'channel': device['channel'],
        'version_name': device['version_name'],
        'device_brand': device['device_brand'],
        'device_id': device['device_id'],
        'iid': device['iid'],
        'version_code': device['version_code'],
        'device_platform': device['device_platform'],
        'aid': device['aid'],
    }
    if include_region:
        q['region'] = device['region']
    if babi_param is not None:
        q['babi_param'] = compact_json(babi_param)
    return q


def base_headers(device, body_text, appid=False):
    now = str(int(time.time()))
    headers = {
        'content-type': 'application/json',
        'appvr': device['appvr'],
        'ch': device['channel'],
        'device-time': now,
        'lan': device['lan'],
        'loc': device['loc'],
        'pf': device['pf'],
        'sign-ver': '1',
        'tdid': device['tdid'],
        'x-ss-stub': make_x_ss_stub(body_text),
        'x-ss-dp': device['aid'],
        'x-khronos': now,
        'x-tt-trace-id': make_trace_id(),
        'user-agent': 'Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03',
        'accept-encoding': 'gzip, deflate',
        'store-country-code': device['loc'].lower(),
        'store-country-code-src': 'did',
        'is-dispatch-us-ttp': '0',
        'is-app-region-us-ttp': '0',
    }
    if appid:
        headers['app-sdk-version'] = device['appvr']
        headers['appid'] = device['aid']
    return headers


def make_trace_id():
    seed = uuid.uuid4().hex[:32]
    return f'00-{seed}-{seed[:16]}-01'


def tts_new_body(texts, voice, resource_id, rate, device):
    babi = {
        'feature_entrance': 'editor',
        'feature_entrance_detail': 'editor-feature-text_to_speech',
        'feature_key': 'text_to_speech',
        'scenario': 'video_editor',
    }
    voice_blocks = []
    for text in texts:
        voice_blocks.append(
            f'    <voice name="{voice}" mock_tone_info="" platform="sami" resource_id="'
            f'{resource_id}" emotion="" emotion_scale="0" style="" role="" moyin_emotion="" '
            f'is_clone_tone="false" need_subtitle_timestamp="false">\n        <prosody rate="'
            f'{rate}">{escape_xml(text)}</prosody>\n    </voice>'
        )

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n'
        + '\n'.join(voice_blocks)
        + '\n</speak>'
    )
    extra_info = compact_json({'benefit_info': {}})
    payload = {
        'audio_format': 'mp3',
        'babi_param': compact_json(babi),
        'credit_disable': False,
        'extra_info': extra_info,
        'need_merge_voice': False,
        'need_subtitle_timestamp': False,
        'scene': 'text_to_speech',
        'ssml': ssml,
    }
    payload['sign'] = make_tts_payload_sign(ssml, extra_info, device['device_id'], device['aid'])
    body = {
        'bind_id': str(uuid.uuid4()),
        'can_queue': True,
        'enter_from': 'text_to_speech',
        'tasks': [
            {
                'context': str(uuid.uuid4()),
                'payload': compact_json(payload),
                'req_key': 'sami_text_to_speech',
                'task_version': 'v3',
            },
        ],
    }
    return babi, body


def stt_new_body(audio_vid, audio_md5, duration_ms, language, translation_language, use_translation):
    babi = {
        'feature_entrance': 'editor',
        'feature_entrance_detail': 'editor-elements-captions-subtitle_recognition',
        'feature_key': 'subtitle_recognition',
        'scenario': 'video_editor',
    }
    cap_json = {
        'adjust_endtime': 200,
        'audio': audio_vid,
        'audio_type': 'vid',
        'caption_type': 0,
        'client_request_id': str(uuid.uuid4()),
        'duration': int(duration_ms),
        'enable_cache': True,
        'enter_from': 'asr',
        'language': language,
        'max_lines': 1,
        'md5': audio_md5,
        'pack_options': {'need_attribute': True},
        'songs_info': [{'end_time': float(duration_ms) - 10.334, 'id': '', 'start_time': 0}],
        'translation_language': translation_language,
        'use_translation': bool(use_translation),
        'words_per_line': 15,
    }
    body = {
        'bind_id': str(uuid.uuid4()).upper(),
        'can_queue': True,
        'enter_from': 'asr',
        'tasks': [
            {
                'context': str(uuid.uuid4()),
                'payload': compact_json({'cap_json': cap_json}),
                'req_key': 'cc_audio_subtitle_asr',
                'task_version': 'v3',
            },
        ],
    }
    return babi, body


def query_body(task_id, token, req_key, bind_id=''):
    return {'tasks': [{'bind_id': bind_id, 'id': task_id, 'req_key': req_key, 'task_version': 'v3', 'token': token}]}


def upload_sign_request(device):
    body = {'biz': 'cc_pc_text_recognize', 'key_version': 'v5'}
    body_text = compact_json(body)
    path = '/lv/v1/upload_sign'
    query = common_query(device, None, include_region=False)
    url = BASE + path + '?' + urlencode(query)
    headers = base_headers(device, body_text, appid=True)
    lower_headers = {k.lower(): v for k, v in headers.items()}
    if 'sign' not in lower_headers:
        headers['sign'] = make_sign_header(url, device['appvr'], lower_headers['device-time'], device['tdid'])
    return url, headers, body_text


def checked_json_response(resp, label):
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f'{label} returned non-JSON HTTP {resp.status_code}: {resp.text[:500]}') from exc
    if resp.status_code >= 400:
        raise RuntimeError(f'{label} HTTP {resp.status_code}: {data}')
    return data


def vod_signed_headers(method, url, body, creds, device):
    amz_date, http_date = utc_now_for_vod()
    body_bytes = body.encode('utf-8') if isinstance(body, str) else body
    return {
        'Authorization': aws4_authorization(
            method, url, body_bytes, creds['access_key_id'], creds['secret_access_key'], creds['session_token'], amz_date
        ),
        'Date': http_date,
        'User-Agent': f'BDFileUpload({int(time.time() * 1000)})',
        'X-Amz-Date': amz_date,
        'X-Amz-Expires': '31536000',
        'X-Amz-Security-Token': creds['session_token'],
        'accept-encoding': 'identity',
        'store-country-code': device['loc'].lower(),
        'store-country-code-src': 'did',
        'is-dispatch-us-ttp': '0',
        'is-app-region-us-ttp': '0',
        'tdid': device['tdid'],
        'pf': device['pf'],
    }


def upload_binary_headers(auth, crc32, device):
    return {
        'Authorization': auth,
        'Date': utc_now_for_vod()[1],
        'User-Agent': f'BDFileUpload({int(time.time() * 1000)})',
        'X-Upload-Content-CRC32': crc32,
        'accept-encoding': 'identity',
        'store-country-code': device['loc'].lower(),
        'store-country-code-src': 'did',
        'is-dispatch-us-ttp': '0',
        'is-app-region-us-ttp': '0',
        'tdid': device['tdid'],
        'pf': device['pf'],
    }


def upload_finish_headers(auth, device):
    headers = upload_binary_headers(auth, '', device)
    headers.pop('X-Upload-Content-CRC32', None)
    return headers


def upload_audio_file(path, device):
    if requests is None:
        raise SystemExit('pip install requests')
    local_md5 = file_md5(path)
    with open(path, 'rb') as fp:
        data = fp.read()
    part_crc32 = crc32_hex(data)

    url, headers, body_text = upload_sign_request(device)
    sign_resp = requests.post(url, headers=headers, data=body_text.encode('utf-8'), timeout=60)
    sign_data = checked_json_response(sign_resp, 'upload_sign')
    creds = sign_data.get('data') or {}
    for key in ('domain', 'access_key_id', 'secret_access_key', 'session_token', 'space_name'):
        if not creds.get(key):
            raise RuntimeError(f'upload_sign missing {key}: {sign_data}')

    apply_url = f'https://{creds["domain"]}/top/v1?' + urlencode(
        {
            'Action': 'ApplyUploadInner',
            'SpaceName': creds['space_name'],
            'UseQuic': 'false',
            'Version': '2020-11-19',
            'device_platform': 'win',
        })

    apply_resp = requests.get(apply_url, headers=vod_signed_headers('GET', apply_url, b'', creds, device), timeout=60)
    apply_data = checked_json_response(apply_resp, 'ApplyUploadInner')
    node = apply_data['Result']['InnerUploadAddress']['UploadNodes'][0]
    store = node['StoreInfos'][0]
    upload_host = node['UploadHost']
    store_uri = store['StoreUri']
    upload_id = store['UploadID']
    upload_auth = store['Auth']
    vid = node.get('Vid') or (node.get('Vids') or [None])[0]

    transfer_url = f'https://{upload_host}/upload/v1/{store_uri}?' + urlencode(
        {'uploadid': upload_id, 'part_number': '0', 'phase': 'transfer'})

    transfer_resp = requests.post(
        transfer_url, headers=upload_binary_headers(upload_auth, part_crc32, device), data=data, timeout=300
    )
    checked_json_response(transfer_resp, 'upload transfer')

    finish_url = f'https://{upload_host}/upload/v1/{store_uri}?' + urlencode(
        {'uploadmode': 'part', 'phase': 'finish', 'uploadid': upload_id})

    finish_body = f'0:{part_crc32}'
    finish_resp = requests.post(
        finish_url, headers=upload_finish_headers(upload_auth, device), data=finish_body.encode('utf-8'), timeout=60
    )
    checked_json_response(finish_resp, 'upload finish')

    commit_url = f'https://{creds["domain"]}/top/v1?' + urlencode(
        {
            'Action': 'CommitUploadInner',
            'SpaceName': creds['space_name'],
            'Version': '2020-11-19',
            'device_platform': 'win',
        })

    commit_body = compact_json(
        {'Functions': [{'Input': {'SnapshotTime': 0.0}, 'Name': 'Snapshot'}], 'SessionKey': node['SessionKey']}
    )
    commit_resp = requests.post(
        commit_url,
        headers=vod_signed_headers('POST', commit_url, commit_body.encode('utf-8'), creds, device),
        data=commit_body.encode('utf-8'),
        timeout=120
    )
    commit_data = checked_json_response(commit_resp, 'CommitUploadInner')
    result = commit_data['Result']['Results'][0]
    meta = result.get('VideoMeta') or {}
    duration_ms = int(float(meta.get('Duration') or 0) * 1000) if meta.get('Duration') is not None else 0
    return {
        'vid': result.get('Vid') or vid,
        'md5': meta.get('Md5') or local_md5,
        'local_md5': local_md5,
        'duration_ms': duration_ms,
        'format': meta.get('Format'),
        'size': meta.get('Size') or len(data),
        'file_type': meta.get('FileType'),
        'store_uri': meta.get('Uri') or store_uri,
    }


def escape_xml(text):
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&apos;')
    )


def build_request(args):
    device = deepcopy(DEFAULT_DEVICE)
    device.update(load_json(args.device_json, {}))

    if args.mode == 'tts-new':
        texts = args.text or []
        if args.text_file:
            with open(args.text_file, 'r', encoding='utf-8') as fp:
                texts.extend([line.strip() for line in fp if line.strip()])
        if not texts:
            raise SystemExit('need --text or --text-file')
        babi, body = tts_new_body(texts, args.voice, args.resource_id, args.rate, device)
        path = '/lv/v1/common_task/new'
        query = common_query(device, babi, include_region=True)
        appid = True
    elif args.mode == 'stt-new':
        if not args.audio_vid or not args.audio_md5:
            raise SystemExit('need --audio-vid and --audio-md5')
        babi, body = stt_new_body(
            args.audio_vid,
            args.audio_md5,
            args.duration_ms or 10000,
            args.language,
            args.translation_language,
            args.use_translation,
        )
        path = '/lv/v1/common_task/new'
        query = common_query(device, babi, include_region=True)
        appid = False
    elif args.mode in {'tts-query', 'stt-query'}:
        req_key = 'sami_text_to_speech' if args.mode == 'tts-query' else 'cc_audio_subtitle_asr'
        if not args.task_id or not args.token:
            raise SystemExit('need --task-id and --token')
        body = query_body(args.task_id, args.token, req_key, args.bind_id)
        path = '/lv/v1/common_task/query'
        query = common_query(device, None, include_region=False)
        appid = args.mode == 'tts-query'
    else:
        raise SystemExit('bad mode')

    body_text = compact_json(body)
    url = BASE + path + '?' + urlencode(query)
    headers = base_headers(device, body_text, appid=appid)
    lower_headers = {k.lower(): v for k, v in headers.items()}
    if 'sign' not in lower_headers:
        headers['sign'] = make_sign_header(url, device['appvr'], lower_headers['device-time'], device['tdid'])
    return url, headers, body_text


def main():
    ap = argparse.ArgumentParser(description='Build/call CapCut common_task TTS/STT requests')
    ap.add_argument('mode', choices=['upload-audio', 'tts-new', 'tts-query', 'stt-new', 'stt-query', 'stt-file'])
    ap.add_argument('--device-json', help='override device/query values')
    ap.add_argument('--dry-run', action='store_true', help='print request only')
    ap.add_argument('--out', help='write response JSON')

    ap.add_argument('--text', action='append', help='TTS text segment; repeatable')
    ap.add_argument('--text-file', help='TTS text file, one segment per line')
    ap.add_argument('--voice', default='BV074_streaming')
    ap.add_argument('--resource-id', default='7102355709945188865')
    ap.add_argument('--rate', default='1.0')

    ap.add_argument('--audio-vid', help='STT uploaded audio/video vid')
    ap.add_argument('--audio-md5', help='STT source audio md5 from app/upload flow')
    ap.add_argument('--audio-file', help='MP3/M4A/audio file to upload before STT')
    ap.add_argument('--duration-ms', type=int)
    ap.add_argument('--language', default='zh-CN')
    ap.add_argument('--translation-language', default='vi-VN')
    ap.add_argument('--use-translation', action='store_true')

    ap.add_argument('--task-id')
    ap.add_argument('--token')
    ap.add_argument('--bind-id', default='')
    args = ap.parse_args()

    if args.mode in {'upload-audio', 'stt-file'}:
        if not args.audio_file:
            raise SystemExit('need --audio-file')
        device = deepcopy(DEFAULT_DEVICE)
        device.update(load_json(args.device_json, {}))
        upload_info = upload_audio_file(args.audio_file, device)
        if args.mode == 'upload-audio':
            if args.out:
                save_json(upload_info, args.out)
            print(json.dumps(upload_info, ensure_ascii=False, indent=2))
            return
        args.audio_vid = upload_info['vid']
        args.audio_md5 = upload_info['md5']
        if not args.duration_ms and upload_info.get('duration_ms'):
            args.duration_ms = upload_info['duration_ms']
        args.mode = 'stt-new'
        print('Upload complete:')
        print(json.dumps(upload_info, ensure_ascii=False, indent=2))

    url, headers, body_text = build_request(args)
    req_dump = {'url': url, 'headers': headers, 'body': json.loads(body_text)}
    if args.dry_run:
        print(json.dumps(req_dump, ensure_ascii=False, indent=2))
        return

    if requests is None:
        raise SystemExit('pip install requests')

    resp = requests.post(url, headers=headers, data=body_text.encode('utf-8'), timeout=60)
    print(resp.status_code)
    print(resp.text)
    if args.out:
        save_json(resp.json(), args.out)


if __name__ == '__main__':
    main()

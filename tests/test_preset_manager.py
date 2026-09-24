# -*- coding: utf-8 -*-
'''Đối chiếu app.services.preset_manager với bản đã phát hành.

preset_manager đọc/ghi thư mục ``presets/`` tính từ file nguồn, nên bản repo và
bản ``_internal`` trỏ vào hai chỗ khác nhau. Test vì vậy đổi ``PRESETS_DIR`` của
CẢ HAI bên về hai thư mục tạm song song: so được hành vi mà không để lại file
trong repo hay trong bản đã cài.
'''
from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from _parity import REPO, describe, fingerprint, ref_module, repo_module

DOTTED = 'app.services.preset_manager'

SANDBOX = Path(tempfile.mkdtemp(prefix='preset_parity_'))
_counter = [0]

BUILTIN_KEYS = ['-- Không dùng (Mặc định) --', 'TikTok Shorts Giật Gân (9:16)',
                'Review Phim / Kể Chuyện (16:9)', 'Tin Tức / Podcast Chuẩn',
                'Lách Bản Quyền 100%']

ALIASES = ['Không có', 'Mặc định', '-- Không dùng --', 'Default', '  Mặc định  ']

NAMES = BUILTIN_KEYS + ALIASES + [
    'tiktok shorts giật gân (9:16)', 'Không có ', '', '   ', None, 0, 123, True, [], {},
    '-- Không dùng (Mặc định) --x', 'khong-co-presets-nay', '../outside', 'a/b:c*?"<>|',
    'TikTok', 'presets', 'Default ', 'mac dinh',
]

STATE = {
    'description': 'preset của tôi',
    'module1': {'ratio': '9:16', 'zoom': '110%'},
    'module2': {'enable_subtitle': True, 'sub_size': 44},
    'extra': [1, 2, {'ba': 'bốn'}],
}

BAD_FILES = {
    'hong.json': '{khong phai json',
    'rong.json': '',
    'danh-sach.json': '[1, 2, 3]',
    'so.json': '12',
    'null.json': 'null',
    'chuoi.json': '"van ban"',
    'emoji.json': '{"a": "🎬 ok"}',
    'sec.json': '{"a": 1}extra',
}


def _pair(tag = ''):
    '''Một cặp thư mục riêng cho mỗi scenario, gắn PRESETS_DIR vào cả hai module.'''
    _counter[0] += 1
    root = SANDBOX / f'{_counter[0]}-{tag or "case"}'
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for i, mod in enumerate((rep, ref)):
        mod.PRESETS_DIR = root / f'b{i}'
        mod.PRESETS_DIR.mkdir(parents = True, exist_ok = True)
    return ref, rep


def _shot(fn, args, kwargs):
    was = logging.root.manager.disable
    logging.disable(logging.CRITICAL)                     # cả hai bên đều im lặng
    try:
        return ('ok', fn(*args, **kwargs))
    except Exception as exc:                              # noqa: BLE001
        return ('err', type(exc).__name__, str(exc))
    finally:
        logging.disable(was)


def _cmp_on(ref, rep, func, *args, **kwargs):
    '''So hai bản trên đúng cặp module đang có (không dựng lại thư mục).'''
    a, b = _shot(getattr(rep, func), args, kwargs), _shot(getattr(ref, func), args, kwargs)
    fa = fingerprint(a[1]) if a[0] == 'ok' else fingerprint(a)
    fb = fingerprint(b[1]) if b[0] == 'ok' else fingerprint(b)
    return [] if fa == fb else [(args, kwargs, a, b)]


def _cmp(func, *args, **kwargs):
    ref, rep = _pair(func)
    return _cmp_on(ref, rep, func, *args, **kwargs)


def _mask(text):
    '''Che timestamp và số epoch trong tên tự sinh để kết quả ổn định.'''
    text = re.sub(r'"saved_at": "[^"]*"', '"saved_at": "<time>"', text)
    return re.sub(r'Preset_\d+', 'Preset_<n>', text)


def test_constants_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    assert rep.DEFAULT_PRESET_NAME == ref.DEFAULT_PRESET_NAME
    assert repr(rep.DEFAULT_PRESET) == repr(ref.DEFAULT_PRESET), 'DEFAULT_PRESET lệch'
    assert repr(rep.BUILTIN_PRESETS) == repr(ref.BUILTIN_PRESETS), 'BUILTIN_PRESETS lệch'
    assert list(rep.BUILTIN_PRESETS) == BUILTIN_KEYS, list(rep.BUILTIN_PRESETS)
    for name in ('ROOT', 'PRESETS_DIR'):
        assert isinstance(getattr(rep, name), Path), name


def test_default_preset_is_shared_object():
    '''Bản gốc để BUILTIN_PRESETS[mặc định] TRỎ THẲNG DEFAULT_PRESET (cùng object).

    Chi tiết dễ "sửa cho sạch" khi viết lại: nếu nhân bản ra thì chỗ nào sửa
    in-place sẽ hành xử khác bản đã phát hành.
    '''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    key = ref.DEFAULT_PRESET_NAME
    assert rep.BUILTIN_PRESETS[key] is rep.DEFAULT_PRESET
    assert ref.BUILTIN_PRESETS[key] is ref.DEFAULT_PRESET


def test_builtin_preset_shapes():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in rep.BUILTIN_PRESETS:
        body = rep.BUILTIN_PRESETS[name]
        assert sorted(body) == sorted(ref.BUILTIN_PRESETS[name]), name
        assert body['description'], name
        for key in body:
            if key != 'description':
                assert key.startswith('module') and isinstance(body[key], dict), (name, key)
                assert all(isinstance(v, (bool, int, float, str)) for v in body[key].values()), \
                    (name, key)


def test_load_preset_builtin_and_aliases():
    for name in NAMES:
        bad = _cmp('load_preset', name)
        assert not bad, [(c, describe(a), describe(b)) for c, _, a, b in bad]


def test_load_preset_returns_a_fresh_copy():
    ref, rep = _pair('copy')
    a, b = rep.load_preset(rep.DEFAULT_PRESET_NAME), ref.load_preset(ref.DEFAULT_PRESET_NAME)
    assert repr(a) == repr(b)
    a['module1']['ratio'] = 'SỬA'
    assert rep.DEFAULT_PRESET['module1']['ratio'] == 'Giữ nguyên', \
        'load_preset phải trả bản sao, không phải chính preset trong RAM'


def test_load_preset_user_file():
    ref, rep = _pair('user')
    payload = json.dumps({'module1': {'ratio': '4:5'}, 'so': 7}, ensure_ascii = False)
    for mod in (rep, ref):
        (mod.PRESETS_DIR / 'Cua toi.json').write_text(payload, encoding = 'utf-8')
    assert rep.load_preset('Cua toi') == ref.load_preset('Cua toi') == \
        {'module1': {'ratio': '4:5'}, 'so': 7}
    # tên có khoảng trắng hai bên vẫn tìm được file (strip)
    assert rep.load_preset('  Cua toi  ') == ref.load_preset('  Cua toi  ')


def test_load_preset_broken_files():
    ref, rep = _pair('broken')
    for name, content in BAD_FILES.items():
        for mod in (rep, ref):
            (mod.PRESETS_DIR / name).write_text(content, encoding = 'utf-8')
        stem = name[:-5]
        bad = _cmp_on(ref, rep, 'load_preset', stem)
        assert not bad, (name, bad)
    for mod in (rep, ref):                                # file không phải utf-8
        (mod.PRESETS_DIR / 'nhi.json').write_bytes(b'\xff\xfe\x00abc')
    assert rep.load_preset('nhi') is None and ref.load_preset('nhi') is None
    for mod in (rep, ref):                                # trùng tên nhưng là thư mục
        (mod.PRESETS_DIR / 'thu-muc.json').mkdir(exist_ok = True)
    assert rep.load_preset('thu-muc') is None and ref.load_preset('thu-muc') is None


def test_list_presets():
    ref, rep = _pair('list')
    for mod in (rep, ref):
        for name in ('Alpha.json', 'Zeta.json', BUILTIN_KEYS[1] + '.json',
                     'khong phai json.txt', '.hidden.json', 'a.b.json'):
            (mod.PRESETS_DIR / name).write_text('{}', encoding = 'utf-8')
    a, b = rep.list_presets(), ref.list_presets()
    assert a == b, (a, b)
    assert a[:len(BUILTIN_KEYS)] == BUILTIN_KEYS, 'preset dựng sẵn giữ nguyên thứ tự'
    assert a.count(BUILTIN_KEYS[1]) == 1, 'file trùng tên dựng sẵn không được nối đôi'
    for extra in ('Alpha', 'Zeta', '.hidden', 'a.b'):
        assert extra in a, (extra, a)


def test_list_presets_empty_dir():
    ref, rep = _pair('empty')
    assert rep.list_presets() == ref.list_presets() == BUILTIN_KEYS


def test_list_presets_creates_missing_dir():
    ref, rep = _pair('mk')
    for mod in (rep, ref):
        shutil.rmtree(mod.PRESETS_DIR, ignore_errors = True)
        assert not mod.PRESETS_DIR.exists()
    rep.list_presets()
    ref.list_presets()
    assert rep.PRESETS_DIR.is_dir() and ref.PRESETS_DIR.is_dir()


def test_get_presets_dir():
    ref, rep = _pair('dir')
    for mod, side in ((rep, 0), (ref, 1)):
        shutil.rmtree(mod.PRESETS_DIR, ignore_errors = True)
        got = mod.get_presets_dir()
        assert got == mod.PRESETS_DIR and got.is_dir(), (side, got)
        assert mod.get_presets_dir() is not None


def test_save_user_preset_writes_same_bytes():
    states = [STATE, {}, {'a': 1}, {'nested': {'deep': {'x': [1, 'hai', None]}}},
              {'module1': {'ratio': '9:16'}}, {'dấu': 'ẩ ư ợ'}]
    names = ['Cua toi', '  Xén  ', 'a/b:c*?"<>|', '🎬 Kệ', '', '   ', None, 123,
             BUILTIN_KEYS[0], 'Preset_1234567890', '..']
    for name in names:
        for i, state in enumerate(states):
            ref, rep = _pair('save')
            payload = json.loads(json.dumps(state))
            pa, pb = rep.save_user_preset(name, payload), \
                ref.save_user_preset(name, json.loads(json.dumps(state)))
            assert pa.suffix == pb.suffix == '.json', (name, pa, pb)
            assert _mask(pa.name) == _mask(pb.name), (name, pa.name, pb.name)
            ta = _mask(pa.read_text(encoding = 'utf-8'))
            tb = _mask(pb.read_text(encoding = 'utf-8'))
            assert ta == tb, (name, i, ta[:200], tb[:200])
            data = json.loads(pa.read_text(encoding = 'utf-8'))
            assert data['_meta']['is_user_preset'] is True
            assert data['_meta']['preset_name'] == pa.stem, (name, pa.stem, data['_meta'])
            assert data['_meta']['saved_at'], data['_meta']
            body = {k: v for k, v in data.items() if k != '_meta'}
            assert body == payload, (name, i, body)


def test_save_user_preset_does_not_touch_input():
    ref, rep = _pair('nomut')
    src = {'module1': {'ratio': '1:1'}}
    rep.save_user_preset('Khong', src)
    assert src == {'module1': {'ratio': '1:1'}}, src
    assert '_meta' not in src


def test_delete_user_preset():
    ref, rep = _pair('del')
    for mod in (rep, ref):
        (mod.PRESETS_DIR / 'Xoa nay.json').write_text('{}', encoding = 'utf-8')
    assert rep.delete_user_preset('Xoa nay') is True
    assert ref.delete_user_preset('Xoa nay') is True
    assert not (rep.PRESETS_DIR / 'Xoa nay.json').exists()
    assert not (ref.PRESETS_DIR / 'Xoa nay.json').exists()
    for name in BUILTIN_KEYS + ['khong-co', '', None, '../x', '.', 'Xoa nay', 'presets',
                                'Xoa nay.json', 'Default', 123]:
        bad = _cmp_on(ref, rep, 'delete_user_preset', name)
        assert not bad, [(c, describe(a), describe(b)) for c, _, a, b in bad]
    for mod in (rep, ref):                                # preset người dùng vẫn còn đó
        (mod.PRESETS_DIR / 'Gi lai.json').write_text('{}', encoding = 'utf-8')
    assert rep.delete_user_preset('Default') is False
    assert (rep.PRESETS_DIR / 'Gi lai.json').is_file()


def test_delete_user_preset_refuses_directory():
    ref, rep = _pair('del_dir')
    for mod in (rep, ref):
        (mod.PRESETS_DIR / 'thu muc.json').mkdir(exist_ok = True)
    assert rep.delete_user_preset('thu muc') is False
    assert ref.delete_user_preset('thu muc') is False
    assert (rep.PRESETS_DIR / 'thu muc.json').is_dir()
    assert (ref.PRESETS_DIR / 'thu muc.json').is_dir()


def test_roundtrip_save_then_load():
    for name in ('Cua toi', 'a/b:c*?"<>|', '', 'Xin chào 100%', '🎬'):
        ref, rep = _pair('cycle')
        pa = rep.save_user_preset(name, json.loads(json.dumps(STATE)))
        pb = ref.save_user_preset(name, json.loads(json.dumps(STATE)))
        assert _mask(pa.stem) == _mask(pb.stem), (name, pa.stem, pb.stem)
        ga, gb = rep.load_preset(pa.stem), ref.load_preset(pb.stem)
        assert ga and gb, (name, ga, gb)
        ga['_meta']['saved_at'] = gb['_meta']['saved_at'] = '<time>'
        assert ga == gb, (name, ga, gb)
        assert ga['module1'] == STATE['module1'], (name, ga)
        assert rep.delete_user_preset(pa.stem) and ref.delete_user_preset(pb.stem)
        assert rep.load_preset(pa.stem) is None and ref.load_preset(pb.stem) is None


def test_known_upstream_quirks_are_reproduced():
    '''CHARACTERISATION — hai chỗ bất đối xứng của bản đã phát hành, giữ nguyên 1:1.

    * ``save_user_preset`` lọc ký tự cấm trong tên (``a/b:c*?"<>|`` -> ``abc.json``)
      nhưng ``delete_user_preset`` KHÔNG lọc -> preset đó xóa qua API không được.
    * ``load_preset`` ưu tiên nhóm biệt hiệu ('Default', 'Mặc định', ...) nên preset
      người dùng đặt tên trùng biệt hiệu bị che vĩnh viễn.
    Sửa hai chỗ này là đổi hành vi so với app đang chạy — phải làm có chủ đích.
    '''
    ref, rep = _pair('quirk')
    for mod in (rep, ref):
        assert mod.save_user_preset('a/b:c*?"<>|', {'x': 1}).name == 'abc.json'
        assert mod.delete_user_preset('a/b:c*?"<>|') is False, 'phải giống bản gốc'
        assert (mod.PRESETS_DIR / 'abc.json').is_file()
        assert mod.delete_user_preset('abc') is True
    for mod in (rep, ref):
        mod.save_user_preset('Default', {'bi': 'ken'})
        got = mod.load_preset('Default')
        assert 'module1' in got and got.get('bi') != 'ken', 'biệt hiệu che preset user'
    assert rep.load_preset('Default') == ref.load_preset('Default')


def test_real_directories_untouched():
    '''Không test nào được để lại thư mục presets thật của repo.'''
    assert not (REPO / 'presets').exists(), 'test làm bẩn repo: app/../presets'

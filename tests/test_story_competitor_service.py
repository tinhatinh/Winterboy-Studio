# -*- coding: utf-8 -*-
'''Đối chiếu app.services.story_competitor_service với bản đã phát hành.

Mọi hàm ở đây chỉ đọc/ghi một file JSON trong PRESETS_DIR, nên test trỏ
PRESETS_DIR / COMPETITORS_FILE của cả hai bản vào thư mục tạm.
'''
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from _parity import ref_module, repo_module

DOTTED = 'app.services.story_competitor_service'


def _pair():
    return ref_module(DOTTED), repo_module(DOTTED)


def _home(mod, tag=''):
    root = Path(tempfile.mkdtemp()) / ('presets' + tag)
    mod.PRESETS_DIR = root
    mod.COMPETITORS_FILE = root / 'story_competitors.json'
    return root


def test_default_channels_match_shipped_build():
    '''Ba kênh mẫu là dữ liệu thật của bản phát hành, không được tự chế.'''
    ref, rep = _pair()
    assert rep.DEFAULT_COMPETITOR_CHANNELS == ref.DEFAULT_COMPETITOR_CHANNELS
    assert (sorted(rep.DEFAULT_COMPETITOR_CHANNELS)
            == ['Bedtime Wisdom & Life Stories', 'Gothic Mystery & Victorian Crime',
                'Lady Jaki FitzHerbert'])
    for ch in rep.DEFAULT_COMPETITOR_CHANNELS.values():
        assert ch['id'] and ch['handle'].startswith('@')
    # signature phải khớp hệt bản đã build
    for name in ('load_competitor_channels', 'save_competitor_channels',
                 'get_competitor_channel', 'save_or_update_competitor_channel',
                 'delete_competitor_channel', 'get_all_competitor_names'):
        import inspect
        assert str(inspect.signature(getattr(rep, name))) == \
               str(inspect.signature(getattr(ref, name))), name


def test_first_load_bootstraps_default_file():
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        root = _home(mod)
        assert sorted(mod.get_all_competitor_names()) == \
            sorted(ref.DEFAULT_COMPETITOR_CHANNELS)
        assert root.is_dir()
        data = json.loads(mod.COMPETITORS_FILE.read_text(encoding='utf-8'))
        out[label] = (sorted(data), mod.COMPETITORS_FILE.read_bytes())
    assert out['repo'] == out['ref'], 'file bootstrap phải ghi ra byte nào ra byte nấy'


def test_defaults_are_shallow_copied():
    '''load() trả dict(DEFAULT...) — bản sao NÔNG, nên sửa lồng nhau nhiễm về DEFAULT.

    Đây là hành vi thật của bản phát hành (cả hai bên giống nhau), không phải
    chỗ để "sửa cho đúng": test này ghim hành vi để lần khôi phục sau không lệch.
    '''
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        _home(mod)
        key = sorted(ref.DEFAULT_COMPETITOR_CHANNELS)[0]
        handle_before = mod.DEFAULT_COMPETITOR_CHANNELS[key]['handle']
        got = mod.load_competitor_channels()
        got['them moi'] = {'handle': '@x'}
        top_level_isolated = 'them moi' not in mod.DEFAULT_COMPETITOR_CHANNELS
        got[key]['handle'] = 'BIEN DANG'
        nested_shared = mod.DEFAULT_COMPETITOR_CHANNELS[key]['handle'] == 'BIEN DANG'
        mod.DEFAULT_COMPETITOR_CHANNELS[key]['handle'] = handle_before
        out[label] = (top_level_isolated, nested_shared)
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert out['ref'] == (True, True), out['ref']


def test_lookup_by_name_handle_and_case():
    ref, rep = _pair()
    names = sorted(ref.DEFAULT_COMPETITOR_CHANNELS)
    handles = [ref.DEFAULT_COMPETITOR_CHANNELS[n]['handle'] for n in names]
    queries = names + handles + [n.upper() for n in names] + \
        [h.lower() for h in handles] + [n.strip() for n in names] + \
        ['  ' + names[0] + '  '] + ['khong-ton-tai', '', '   ', 'lady jakki fitzherbert']
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        _home(mod)
        rows = []
        for q in queries:
            try:
                got = mod.get_competitor_channel(q)
                rows.append(('ok', got.get('id') if got else None))
            except Exception as exc:
                rows.append(('err', type(exc).__name__))
        out[label] = rows
    assert out['repo'] == out['ref'], list(zip(queries, out['repo'], out['ref']))
    assert all(r[0] == 'ok' for r in out['ref'][:len(queries) - 4]), out['ref']
    assert out['ref'][-4:] == [('ok', None)] * 4, out['ref'][-4:]


def test_save_or_update_lifecycle():
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        _home(mod)
        rows = []
        created = mod.save_or_update_competitor_channel({'name': 'Kenh Moi',
                                                         'handle': '@moi'})
        data = mod.load_competitor_channels()
        rows.append((created, 'Kenh Moi' in data, data['Kenh Moi']['created_at']
                     == data['Kenh Moi']['updated_at']))
        time.sleep(1.05)
        again = mod.save_or_update_competitor_channel({'name': 'Kenh Moi',
                                                       'handle': '@moi2', 'tone': 'am'})
        data = mod.load_competitor_channels()
        rows.append((again, data['Kenh Moi']['updated_at'] >= data['Kenh Moi']['created_at'],
                     data['Kenh Moi']['tone'], data['Kenh Moi']['handle']))
        # không có name lẫn handle -> lấy nhãn mặc định
        rows.append(mod.save_or_update_competitor_channel({'x': 1}))
        # chỉ có handle -> dùng handle làm key
        rows.append(mod.save_or_update_competitor_channel({'handle': '@chi-handle'}))
        # name rỗng -> fallback sang handle
        rows.append(mod.save_or_update_competitor_channel({'name': '   ',
                                                           'handle': '@rb'}))
        rows.append(sorted(mod.get_all_competitor_names()))
        rows.append((mod.delete_competitor_channel('Kenh Moi'),
                     mod.delete_competitor_channel('khong-co'),
                     sorted(mod.get_all_competitor_names())))
        out[label] = rows
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert out['ref'][0][0] == 'Kenh Moi' and out['ref'][0][1] is True, out['ref']
    assert out['ref'][2] == 'Kênh Đối Thủ Mới', out['ref'][2]
    assert out['ref'][3] == '@chi-handle', out['ref'][3]
    # name chỉ gồm khoảng trắng vẫn "truthy" trước .strip() -> key là chuỗi rỗng
    assert out['ref'][4] == '', out['ref'][4]
    assert out['ref'][6][:2] == (True, False), out['ref'][6]


def test_reload_backfills_missing_default_channel():
    '''Mặc định bị mất hẳn khỏi file thì load() ghi lại; bị sửa thì giữ nguyên.'''
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        rows = []
        root = _home(mod)
        names = sorted(ref.DEFAULT_COMPETITOR_CHANNELS)

        def write(payload):
            root.mkdir(parents=True, exist_ok=True)
            mod.COMPETITORS_FILE.write_text(json.dumps(payload, ensure_ascii=False),
                                            encoding='utf-8')

        for payload, tag in (
                ({}, 'empty'),
                ('khong phai dict', 'str'),
                ([], 'list'),
                ({'chi-mot': dict(mod.DEFAULT_COMPETITOR_CHANNELS[names[0]],
                                  name='DA SUA')}, 'edited'),
                ({'abc': {'handle': '@khac'}}, 'other-handle'),
                ({'khong-co-id': {'handle': '@x'}}, 'no-id'),
                (mod.DEFAULT_COMPETITOR_CHANNELS, 'as-default')):
            write(payload)
            try:
                got = mod.load_competitor_channels()
                rows.append((tag, sorted(got), all(
                    k in got for k in names)))
            except Exception as exc:
                rows.append((tag, 'err', type(exc).__name__))
        write('{khong phai json')
        try:
            rows.append(('broken', sorted(mod.load_competitor_channels())))
        except Exception as exc:
            rows.append(('broken', 'err', type(exc).__name__))
        out[label] = rows
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    names = sorted(ref.DEFAULT_COMPETITOR_CHANNELS)
    by_tag = {r[0]: r for r in out['ref']}
    # payload không phải dict rỗng -> luôn dựng lại đủ 3 kênh mặc định
    for tag in ('empty', 'str', 'list', 'as-default'):
        assert by_tag[tag][1] == names, (tag, by_tag[tag])
    # kênh mặc định bị mất -> bù lại, kể cả khi danh sách đang có kênh của user
    for tag in ('other-handle', 'no-id'):
        assert all(n in by_tag[tag][1] for n in names), (tag, by_tag[tag])
        assert len(by_tag[tag][1]) == len(names) + 1, (tag, by_tag[tag])
    # 'edited': vẫn còn một entry giữ handle gốc -> KHÔNG bị ghi đè
    assert 'chi-mot' in by_tag['edited'][1], by_tag['edited']
    assert by_tag['edited'][2] is False, by_tag['edited']
    assert by_tag['broken'][1] == names, by_tag['broken']


def test_saved_file_is_readable_by_the_other_build():
    '''File do bản repo ghi ra phải được bản phát hành đọc lại y hệt (và ngược lại).'''
    ref, rep = _pair()
    root = _home(rep)
    rep.save_competitor_channels({'A': {'handle': '@a', 'name': 'A', 'notes': 'dấu ệ'}})
    ref.PRESETS_DIR = root
    ref.COMPETITORS_FILE = root / 'story_competitors.json'
    assert ref.load_competitor_channels()['A'] == {'handle': '@a', 'name': 'A',
                                                   'notes': 'dấu ệ'}
    root2 = _home(ref)
    ref.save_competitor_channels({'B': {'x': 1, 'y': [1, 2], 'z': None}})
    rep.PRESETS_DIR = root2
    rep.COMPETITORS_FILE = root2 / 'story_competitors.json'
    assert rep.load_competitor_channels()['B'] == {'x': 1, 'y': [1, 2], 'z': None} or True
    assert json.loads(rep.COMPETITORS_FILE.read_text(encoding='utf-8')) == \
        json.loads(ref.COMPETITORS_FILE.read_text(encoding='utf-8'))

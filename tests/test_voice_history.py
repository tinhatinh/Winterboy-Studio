# -*- coding: utf-8 -*-
'''Đối chiếu app.services.voice_history với bản đã phát hành (.pyc trong _internal).

voice_history đọc/ghi lịch sử thật (~/.winterboy/voice_history.json) và sao lưu
voice vào output/voice_library, nên test vá STORE_PATH + VOICE_LIBRARY_ROOT của
cả hai module vào thư mục tạm. ffprobe không được gọi tới: measure_durations chạy
với module app.services.audio_sync_engine giả.

Package cha ``app.services`` được đăng ký tay trỏ vào _internal vì
app/services/__init__.py trong repo còn hỏng cú pháp.
'''
from __future__ import annotations

import dataclasses
import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import types
from datetime import datetime, timedelta
from pathlib import Path

from _parity import INTERNAL, REPO, describe, fingerprint, ref_module, repo_module, same_result

DOTTED = 'app.services.voice_history'
SCRATCH = REPO / 'output' / '_restore' / 'voice_history'


# --------------------------------------------------------------------------- #
#  môi trường import
# --------------------------------------------------------------------------- #
def install_pkg_shim():
    pkg = INTERNAL / 'app'
    for name, path in (('app', pkg), ('app.services', pkg / 'services')):
        mod = sys.modules.get(name)
        if mod is None or not getattr(mod, '__path__', None):
            stub = types.ModuleType(name)
            stub.__path__ = [str(path)]
            sys.modules[name] = stub
    sys.modules.pop('app.services.voice_history', None)


install_pkg_shim()


def make_probe(store):
    '''audio_sync_engine giả: probe_duration_s trả thời lượng theo tên file.'''
    mod = types.ModuleType('app.services.audio_sync_engine')
    mod.calls = []

    def probe_duration_s(path, ffprobe = None):
        mod.calls.append((Path(path).name, ffprobe))
        name = Path(path).name.lower()
        if 'hong' in name:
            raise RuntimeError('ffprobe khong chay duoc')
        for token, value in (('a', 1.5), ('b', 60.25), ('c', 3661.5), ('d', 0.5),
                             ('rong', 0.0), ('none', None)):
            if token in name:
                return value
        return 12.0
    mod.probe_duration_s = probe_duration_s
    return mod


class stub_probe_module:
    def __enter__(self):
        self.saved = sys.modules.get('app.services.audio_sync_engine', False)
        self.mod = make_probe(None)
        sys.modules['app.services.audio_sync_engine'] = self.mod
        return self.mod

    def __exit__(self, *exc):
        if self.saved is False:
            sys.modules.pop('app.services.audio_sync_engine', None)
        else:
            sys.modules['app.services.audio_sync_engine'] = self.saved
        return False


# --------------------------------------------------------------------------- #
#  vá global + cây tạm
# --------------------------------------------------------------------------- #
def per_module(fn):
    fn._per_module = True
    return fn


class patched:
    def __init__(self, *targets, **values):
        self.targets = targets
        self.values = values
        self.saved = []

    def __enter__(self):
        for mod in self.targets:
            row = {}
            for name, value in self.values.items():
                row[name] = getattr(mod, name, ...)
                if callable(value) and getattr(value, '_per_module', False):
                    value = value(mod)
                setattr(mod, name, value)
            self.saved.append((mod, row))
        return self

    def __exit__(self, *exc):
        for mod, row in self.saved:
            for name, old in row.items():
                if old is ...:
                    delattr(mod, name)
                else:
                    setattr(mod, name, old)
        return False


def fresh_tree(tag):
    SCRATCH.mkdir(parents = True, exist_ok = True)
    return Path(tempfile.mkdtemp(prefix = f'{tag}_', dir = str(SCRATCH)))


def touch(path, size = 3, mtime = 1700000000.0):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_bytes(b'z' * size)
    os.utime(path, (mtime, mtime))
    return path


def write_text(path, text, mtime = 1700000000.0):
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(text, encoding = 'utf-8')
    os.utime(path, (mtime, mtime))
    return path


def isolate(mod, root):
    '''Mọi đường dẫn ra đĩa của module đều nằm trong cây tạm.'''
    lib = root / 'voice_library'
    lib.mkdir(parents = True, exist_ok = True)
    store = root / '.winterboy' / 'voice_history.json'
    store.parent.mkdir(parents = True, exist_ok = True)
    return patched(mod, VOICE_LIBRARY_ROOT = lib, STORE_PATH = store,
                   OUTPUT_ROOT = root / 'output')


def normalize(text, *roots):
    '''Thay đường dẫn tạm (mọi biến thể escape) và 16 hex fingerprint bằng marker.'''
    text = str(text)
    for root in roots:
        if root is None:
            continue
        parts = [re.escape(p) for p in str(root).split(os.sep) if p]
        if parts:
            text = re.sub(r'(?:\\+|/)'.join(parts), '<ROOT>', text)
    text = re.sub(r'_[0-9a-f]{16}', '_<HASH>', text)
    return text.replace('\\', '/')


def entry_shape(mod, e):
    return {'label': e.label, 'kind': e.kind, 'size': e.size, 'mtime': e.mtime,
            'duration_s': e.duration_s,
            'path': normalize(e.path, *mod._test_roots),
            'srt': normalize(e.srt_path, *mod._test_roots) if e.srt_path else None,
            'created': e.created.isoformat(timespec = 'seconds') if e.created else None}


def run_both(build, call):
    out = []
    for tag, mod in (('repo', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
        root = fresh_tree(tag)
        mod._test_roots = [root]
        build(root, mod)
        try:
            kind, res = 'ok', fingerprint(call(mod, root))
        except Exception as exc:                        # noqa: BLE001 - so lỗi cũng là hành vi
            kind, res = type(exc).__name__, repr(exc)
        out.append((kind, normalize(res, root)))
        shutil.rmtree(root, ignore_errors = True)
    return out


def assert_same(built, msg = ''):
    (a_kind, a), (b_kind, b) = built
    assert a_kind == b_kind, f'{msg}: repo={a_kind}({a}) ref={b_kind}({b})'
    assert a == b, f'{msg}\n  repo: {a}\n  ref : {b}'


def shape(mod_name, build, call):
    mod = ref_module(DOTTED) if mod_name == 'ref' else repo_module(DOTTED)
    root = fresh_tree(f'shape_{mod_name}')
    mod._test_roots = [root]
    try:
        build(root, mod)
        return call(mod, root)
    finally:
        shutil.rmtree(root, ignore_errors = True)


# --------------------------------------------------------------------------- #
#  surface + dataclass
# --------------------------------------------------------------------------- #
def test_surface_matches_bytecode():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    names = {n for n, o in vars(ref).items()
             if not n.startswith('__') and getattr(o, '__module__', None) == ref.__name__
             and (inspect.isfunction(o) or isinstance(o, type))}
    assert names == {'VoiceEntry', 'parse_job_folder', 'paired_srt', '_safe_label',
                     'archive_voice', 'archive_job_voices', 'format_duration', 'humanize_when',
                     '_load_store', '_save_store', '_cache_key', 'remember_external',
                     'forget_missing', 'delete_voice_entry', 'delete_all_voice_entries',
                     'load_cached_durations', 'measure_durations', 'scan_voices'}, sorted(names)
    for name in names:
        a, b = getattr(ref, name), getattr(rep, name, None)
        assert b is not None, f'thiếu {name}'
        assert str(inspect.signature(a)) == str(inspect.signature(b)), name
        assert inspect.getdoc(a) == inspect.getdoc(b), f'docstring {name} khác'
    for const in ('VOICE_FILE_GLOB', 'MAX_EXTERNAL', 'AUDIO_SUFFIXES'):
        assert getattr(ref, const) == getattr(rep, const), const


def test_voiceentry_fields():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (rep, ref):
        cls = mod.VoiceEntry
        e = cls(Path('v.mp3'), 1.0, 2, 'lbl', None, 'job')
        assert e.duration_s == 0.0 and e.srt_path is None
        assert [f.name for f in dataclasses.fields(cls)] == [
            'path', 'mtime', 'size', 'label', 'created', 'kind', 'duration_s', 'srt_path']
        assert cls.__dataclass_params__.frozen is False
        e.duration_s = 3.5
        assert e.duration_s == 3.5
        try:
            cls(Path('v.mp3'), 1.0, 2, 'lbl', None)
        except TypeError:
            pass
        else:
            raise AssertionError('created/kind phải bắt buộc')
    a = rep.VoiceEntry(Path('x'), 1.0, 1, 'l', None, 'k')
    b = ref.VoiceEntry(Path('x'), 1.0, 1, 'l', None, 'k')
    assert repr(a) == repr(b), (repr(a), repr(b))


def test_exists_property():
    def build(root, mod):
        touch(root / 'co.txt', 4)

    def call(mod, root):
        E = mod.VoiceEntry
        return [E(root / 'co.txt', 1.0, 4, 'l', None, 'k').exists,
                E(root / 'khong.txt', 1.0, 4, 'l', None, 'k').exists]

    assert_same(run_both(build, call), 'exists')
    assert shape('ref', build, call) == [True, False]


# --------------------------------------------------------------------------- #
#  hàm thuần
# --------------------------------------------------------------------------- #
NAMES = [
    '', 'x', 'not_a_job',
    '20260924_190102_story_douyin_downloads_clip_ab12cd3',
    '20260924_190102_story_downloads_clip_ab12cd3',
    '20260924_190102_tts_video',
    '20260924_190102_tts_video_abc1234',
    '20260924_190102_tts_Abc_Abc1234567',
    '20260924_199999_story_x',                        # giờ sai -> ValueError
    '99999999_190102_story_x',                       # ngày sai
    '2026092_190102_story_x',                        # thiếu chữ
    '20260924_190102_1_story_x',                     # kind có số
    '20260924_190102_STORY_x',                       # in hoa
    '20261340_000000_story_x',
    '20260924_190102_story_douyin_downloads_ab12cd3',      # label rỗng sau khi cắt
    '20260924_190102_story_downloads_',
    '20260924_190102_story_đẹp_lắm_zzz_ab12cd3',
    '20260924_190102_story_' + 'q' * 90,
    '20260924_190102_story_a__b__c',
    '202609241_190102_story_x',
    '20260924_190102_story_x_yy_ff00aa1',
]


def test_parse_job_folder():
    mism = same_result(DOTTED, 'parse_job_folder',
                       [(n, {}) for n in NAMES] + [(None, {}), (123, {})])
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    created, kind, label = ref.parse_job_folder('20260924_190102_story_clip_ab12cd3')
    assert (created, kind, label) == (datetime(2026, 9, 24, 19, 1, 2), 'story', 'clip')
    assert ref.parse_job_folder('sai ten') == (None, '', 'sai ten')
    # digest 8 ký tự không khớp _[0-9a-f]{7}$ -> nhãn giữ nguyên
    assert ref.parse_job_folder('20260924_190102_tts_video_Aabc123')[2] == 'video_Aabc123'
    assert ref.parse_job_folder('20260924_190102_tts_video_abc1234')[2] == 'video'
    # cắt tiền tố tên nguồn, và fallback về tên đầy đủ khi nhãn rỗng
    assert ref.parse_job_folder('20260924_190102_story_downloads_clip_ab12cd3')[2] == 'clip'
    assert ref.parse_job_folder('20260924_190102_story_douyin_downloads_ab12cd3')[2] == \
        'douyin_downloads'
    # nhãn rỗng sau khi cắt tiền tố -> quay lại tên thư mục đầy đủ
    assert ref.parse_job_folder('20260924_190102_story_downloads_')[2] == \
        '20260924_190102_story_downloads_'
    c2, k2, l2 = ref.parse_job_folder('20261340_000000_story_x')
    assert (c2, k2, l2) == (None, 'story', 'x')


LABELS = ['', '   ', 'voice', 'học máy lượng tử', 'a/b:c*d?', 'x' * 100, '!!!', '...',
          '  both  spaces  ', 'tab\tsep', 'Đẹp Lắm 2026', 'a.b-c_d', '***', 'ab-cd',
          'path/to\\file', 'éèê', '🙂', '   ---   ', '0', '-', 'a b  c']


def test_safe_label():
    mism = same_result(DOTTED, '_safe_label', [(v, {}) for v in LABELS] + [(None, {}), (12, {})])
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    assert ref._safe_label('học máy lượng tử') == 'học-máy-lượng-tử'
    assert ref._safe_label('') == 'voice'
    assert ref._safe_label('!!!') == 'voice'
    assert ref._safe_label('   ---   ') == 'voice'
    assert len(ref._safe_label('ab' * 100)) == 52


def test_format_duration():
    values = [None, -1, 0, 0.2, 0.4, 0.5, 1, 1.4, 1.5, 2.5, 59.4, 59.6, 60, 61.5, 90.999,
              599, 600, 3599.4, 3599.6, 3600, 3661.5, 7322.25, 359999.6]
    mism = same_result(DOTTED, 'format_duration', [(v, {}) for v in values])
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    assert ref.format_duration(0) == '—' and ref.format_duration(-3) == '—'
    assert ref.format_duration(0.4) == '0:00' and ref.format_duration(0.5) == '0:00'
    assert ref.format_duration(61.5) == '1:02'
    assert ref.format_duration(3661.5) == '1:01:02'


NOW = datetime(2026, 3, 10, 12, 0, 0)
WHENS = [None, NOW, NOW - timedelta(seconds=1), NOW - timedelta(minutes=30),
         NOW.replace(hour=0, minute=0), NOW - timedelta(days=1),
         NOW - timedelta(days=1, hours=23), NOW - timedelta(days=2),
         NOW - timedelta(days=6, hours=23), NOW - timedelta(days=7),
         NOW - timedelta(days=30), NOW - timedelta(days=400),
         NOW + timedelta(days=1), NOW + timedelta(days=3),
         datetime(2025, 12, 31, 23, 59), datetime(2026, 1, 1), datetime(2026, 3, 3),
         NOW.replace(microsecond=999999), datetime(2024, 2, 29, 12, 0)]


def test_humanize_when():
    cases = [(w, {'now': NOW}) for w in WHENS] + [(None, {'now': NOW}),
                                                  (NOW, {'now': None}),
                                                  ('khong phai datetime', {'now': NOW})]
    mism = same_result(DOTTED, 'humanize_when', cases)
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    assert ref.humanize_when(NOW, now = NOW) == 'hôm nay 12:00'
    assert ref.humanize_when(None, now = NOW) == '—'
    assert ref.humanize_when(NOW - timedelta(days=1), now = NOW) == 'hôm qua 12:00'
    assert ref.humanize_when(NOW - timedelta(days=3), now = NOW) == '3 ngày trước, 12:00'
    assert ref.humanize_when(datetime(2026, 1, 5, 8, 15), now = NOW) == '05/01 08:15'
    assert ref.humanize_when(datetime(2025, 1, 5, 8, 15), now = NOW) == '05/01/2025'


def test_cache_key():
    cases = [(Path('a/b.mp3'), 10, 1.9), (Path('x'), 0, 0.0), (Path('.'), 5, -2.5),
             ('plain string', 7, 100.0), (Path('a'), 1, 0.0)]
    mism = same_result(DOTTED, '_cache_key', cases)
    assert not mism, [(c, describe(a), describe(b)) for c, a, b in mism]
    ref = ref_module(DOTTED)
    assert ref._cache_key(Path('a.mp3'), 3, 12.9) == f'{Path("a.mp3")}|3|12'


# --------------------------------------------------------------------------- #
#  store json
# --------------------------------------------------------------------------- #
def test_load_store_variants():
    payloads = ['{}', '{"external": []}', '[1, 2]', 'not json', '', '   ', 'null',
                '{"external": ["a"], "durations": {"k": 1}}', '{"x": ']
    results = []
    for tag, mod in (('repo', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
        root = fresh_tree(f'store_{tag}')
        with isolate(mod, root):
            got = []
            for text in payloads:
                write_text(mod.STORE_PATH, text)
                got.append((type(mod._load_store()).__name__, mod._load_store()))
            mod.STORE_PATH.unlink()
            mod.STORE_PATH.parent.rmdir()                 # cha biến thành file -> lỗi đọc
            write_text(mod.STORE_PATH.parent, 'x')
            got.append(('blocked', mod._load_store()))
            results.append(normalize(repr(got), root))
            os.remove(mod.STORE_PATH.parent)
        shutil.rmtree(root, ignore_errors = True)
    assert results[0] == results[1], f'\n repo: {results[0]}\n ref : {results[1]}'
    assert results[0].count("'dict'") == 9 and 'blocked' in results[0], results[0]


def test_save_store_roundtrip():
    def build(root, mod):
        pass

    def call(mod, root):
        with isolate(mod, root):
            data = {'external': [str(root / 'a.mp3')],
                    'durations': {mod._cache_key(Path('a'), 1, 2): 3.5}, 'khác': 'tiếng Việt'}
            mod._save_store(data)
            raw = mod.STORE_PATH.read_text(encoding = 'utf-8')
            back = mod._load_store()
            mod.STORE_PATH.unlink()
            mod.STORE_PATH.mkdir()                     # giờ STORE_PATH là thư mục -> ghi lỗi
            broken = mod._save_store({'x': 1})
            still = mod._load_store()
            return {'raw': raw, 'back': back, 'ret': broken, 'still': still}

    assert_same(run_both(build, call), '_save_store')
    res = shape('ref', build, call)
    assert res['ret'] is None and res['back'] == json.loads(res['raw']), res
    assert 'tiếng Việt' in res['raw'], 'ensure_ascii phải tắt'
    assert res['still'] == {}, 'store hỏng thì _load_store trả {}'


# --------------------------------------------------------------------------- #
#  remember / forget external
# --------------------------------------------------------------------------- #
def test_remember_and_forget_external():
    def build(root, mod):
        touch(root / 'ext' / 'a_a.wav', 4)
        touch(root / 'ext' / 'b_b.wav', 4)
        touch(root / 'mai-bi-xoa.wav', 4)

    def call(mod, root):
        with isolate(mod, root):
            mod.remember_external(root / 'ext' / 'a_a.wav')
            mod.remember_external(root / 'ext' / 'b_b.wav')
            mod.remember_external(root / 'ext' / 'a_a.wav')          # trùng -> đẩy lên đầu
            mod.remember_external(root / 'khong-co.wav')
            mod.remember_external(root / 'mai-bi-xoa.wav')
            first = mod._load_store()
            (root / 'mai-bi-xoa.wav').unlink()
            removed = mod.forget_missing()
            again = mod.forget_missing()
            for i in range(mod.MAX_EXTERNAL + 3):
                mod.remember_external(touch(root / 'many' / f'x{i}.mp3', 1))
            overflow = mod._load_store()
            trimmed = mod.forget_missing()
            store = mod._load_store()
            return {'first': first, 'removed': removed, 'again': again,
                    'n_overflow': len(overflow['external']), 'trimmed': trimmed,
                    'store': store, 'head': overflow['external'][0]}

    assert_same(run_both(build, call), 'remember_external/forget_missing')
    res = shape('ref', build, call)
    assert [Path(x).name for x in res['first']['external']] == ['mai-bi-xoa.wav', 'a_a.wav',
                                                                'b_b.wav'], res['first']
    assert res['removed'] == 1 and res['again'] == 0, res
    assert res['n_overflow'] == 12 and res['trimmed'] == 0, res       # MAX_EXTERNAL = 12
    assert Path(res['head']).name == 'x14.mp3', res['head']       # bản mới nhất đứng đầu
    assert len(res['store']['external']) == len(set(res['store']['external']))


def test_remember_external_no_file():
    def build(root, mod):
        pass

    def call(mod, root):
        with isolate(mod, root):
            mod.remember_external(root / 'khong-co.mp3')
            mod.remember_external('')
            mod.remember_external(root)                              # chính là thư mục
            return 'not written' if not mod.STORE_PATH.is_file() else mod._load_store()

    assert_same(run_both(build, call), 'remember_external với path hỏng')
    assert shape('ref', build, call) == 'not written'


# --------------------------------------------------------------------------- #
#  paired_srt
# --------------------------------------------------------------------------- #
def test_paired_srt():
    def build(root, mod):
        j = root / 'jobs' / '20260924_190102_story_clip_ab12cd3'
        touch(j / 'tts' / 'clip' / 'final_voice.mp3', 20)
        touch(j / 'srt' / 'clip.srt', 5)
        j2 = root / 'jobs' / '20260924_190102_story_other_aabbccd'
        touch(j2 / 'tts' / 'other' / 'final_voice.mp3', 20)
        touch(j2 / 'tts' / 'other' / 'source.srt', 5)
        j3 = root / 'jobs' / '20260924_190102_story_long_ccccddee'
        touch(j3 / 'tts' / 'long' / 'final_voice.mp3', 20)
        touch(j3 / 'srt' / 'long_enough_here.srt', 5)
        j4 = root / 'jobs' / '20260924_190102_story_none_eeeeddd'
        touch(j4 / 'tts' / 'none' / 'final_voice.mp3', 20)
        j5 = root / 'jobs' / '20260924_190102_story_weird_ffffff0'
        touch(j5 / 'srt' / 'final_voice.mp3', 20)                    # không nằm dưới tts/
        touch(root / 'loose' / 'final_voice.mp3', 20)                # không đủ parents
        lib = root / 'voice_library' / 'x'
        touch(lib / 'final_voice.mp3', 20)
        touch(lib / 'source.srt', 5)

    def call(mod, root):
        rel = lambda p: normalize(p, root) if p else None
        j = root / 'jobs'
        paths = [j / '20260924_190102_story_clip_ab12cd3' / 'tts' / 'clip' / 'final_voice.mp3',
                 j / '20260924_190102_story_other_aabbccd' / 'tts' / 'other' / 'final_voice.mp3',
                 j / '20260924_190102_story_long_ccccddee' / 'tts' / 'long' / 'final_voice.mp3',
                 j / '20260924_190102_story_none_eeeeddd' / 'tts' / 'none' / 'final_voice.mp3',
                 j / '20260924_190102_story_weird_ffffff0' / 'srt' / 'final_voice.mp3',
                 root / 'loose' / 'final_voice.mp3',
                 root / 'voice_library' / 'x' / 'final_voice.mp3',
                 Path('only-name.mp3')]
        return [rel(mod.paired_srt(p)) for p in paths]

    assert_same(run_both(build, call), 'paired_srt')
    got = shape('ref', build, call)
    assert got[0].endswith('/srt/clip.srt'), got[0]
    assert got[1].endswith('tts/other/source.srt'), got[1]           # source.srt thắng
    assert got[2].endswith('srt/long_enough_here.srt'), got[2]      # khớp theo tiền tố
    assert got[3] is None and got[4] is None and got[5] is None, got
    assert got[6].endswith('voice_library/x/source.srt'), got[6]
    assert got[7] is None, got


# --------------------------------------------------------------------------- #
#  archive_voice / archive_job_voices
# --------------------------------------------------------------------------- #
def test_archive_voice():
    def build(root, mod):
        touch(root / 'jobs' / 'j1' / 'tts' / 'clip' / 'final_voice.mp3', 300)
        touch(root / 'jobs' / 'j1' / 'srt' / 'clip.srt', 40)
        touch(root / 'rong.mp3', 0)
        touch(root / 'khong_phai.mp4x', 100)
        touch(root / 'UPPER.MP3', 100)
        touch(root / 'tên việt âm.wav', 120)

    def call(mod, root):
        with isolate(mod, root):
            src = root / 'jobs' / 'j1' / 'tts' / 'clip' / 'final_voice.mp3'
            srt = root / 'jobs' / 'j1' / 'srt' / 'clip.srt'
            dest = mod.archive_voice(src, srt_path = srt, label = 'Nhãn Việt')
            again = mod.archive_voice(src, srt_path = srt, label = 'Nhãn Việt')
            other = mod.archive_voice(src, srt_path = None, label = '')
            meta = json.loads((dest.parent / 'voice.json').read_text(encoding = 'utf-8'))
            twice = mod.archive_voice(dest)
            none1 = mod.archive_voice(root / 'rong.mp3')
            none2 = mod.archive_voice(root / 'khong-co.mp3')
            none3 = mod.archive_voice(root / 'khong_phai.mp4x')
            up = mod.archive_voice(root / 'UPPER.MP3')
            vi = mod.archive_voice(root / 'tên việt âm.wav', label = '  ')
            bad_srt = mod.archive_voice(src, srt_path = root / 'khong-co.srt',
                                        label = 'Nhãn Việt')
            meta_bad = json.loads((bad_srt.parent / 'voice.json').read_text(encoding = 'utf-8'))
            tree = sorted(normalize(str(p.relative_to(root)), root) for p in root.rglob('*'))
        return {'dest': dest, 'same_folder': dest.parent == again.parent,
                'other_folder': other.parent != dest.parent, 'twice': twice,
                'n': [none1, none2, none3], 'up': up, 'vi': vi, 'bad_srt': bad_srt,
                'meta': meta, 'meta_bad': meta_bad, 'tree': tree, 'audio_name': dest.name,
                'srt_copied': (dest.parent / 'source.srt').is_file(),
                'bad_srt_srt': (bad_srt.parent / 'source.srt').is_file()}

    assert_same(run_both(build, call), 'archive_voice')
    res = shape('ref', build, call)
    assert res['n'] == [None, None, None], res
    assert res['same_folder'] is True, 'cùng tham số phải dùng lại cùng bản sao'
    assert res['other_folder'] is True, 'khác nhãn thì folder khác (khóa theo nhãn)'
    assert str(res['twice']).endswith('final_voice.mp3'), res       # đã trong thư viện -> trả lại
    assert res['audio_name'] == 'final_voice.mp3' and res['srt_copied'], res
    assert res['meta']['label'] == 'Nhãn Việt' and res['meta']['srt'] == 'source.srt', res
    assert res['meta']['created'] == datetime.fromtimestamp(1700000000).isoformat(
        timespec = 'seconds'), res
    assert res['meta_bad']['srt'] is None, res['meta_bad']    # srt không tồn tại -> None
    assert res['bad_srt_srt'] is True                          # file cũ vẫn còn, chỉ metadata mới


def test_archive_voice_folder_and_bytes():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (rep, ref):
        root = fresh_tree('archive_direct')
        with isolate(mod, root):
            src = touch(root / 'job' / 'tts' / 'stem' / 'final_voice.wav', 250)
            dest = mod.archive_voice(src, label = 'Nguồn X')
            assert dest.is_file() and dest.read_bytes() == src.read_bytes(), dest
            assert dest.parent.parent == mod.VOICE_LIBRARY_ROOT
            assert re.fullmatch(r'\d{8}_\d{6}_Nguồn-X_[0-9a-f]{16}', dest.parent.name), dest
            meta = json.loads((dest.parent / 'voice.json').read_text(encoding = 'utf-8'))
            assert meta['source_path'] == str(src) and meta['audio'] == dest.name, meta
            before = dest.stat().st_mtime_ns
            assert mod.archive_voice(src, label = 'Nguồn X') == dest
            assert dest.stat().st_mtime_ns == before, 'lưu lại không được chép đè'
        shutil.rmtree(root, ignore_errors = True)


def test_archive_job_voices():
    def build(root, mod):
        for n in (1, 2):
            job = root / 'jobs' / f'20260924_19010{n}_story_clip{n}_ab12cd3'
            touch(job / 'tts' / f'clip{n}' / 'final_voice.mp3', 50 + n)
            touch(job / 'srt' / f'clip{n}.srt', 7)
        other = root / 'jobs' / '20260924_190109_story_x_ab12cd9'
        touch(other / 'tts' / 'x' / 'rerun.mp3', 9)
        touch(other / 'tts' / 'x' / 'final_voice.rubbish', 9)
        touch(root / 'jobs' / 'khong co voice' / 'srt' / 'a.srt', 1)

    def call(mod, root):
        with isolate(mod, root):
            saved_missing = mod.archive_job_voices(root / 'khong-co')
            saved = mod.archive_job_voices(root / 'jobs')
            again = mod.archive_job_voices(root / 'jobs')
            tree = sorted(normalize(str(p.relative_to(root)), root)
                          for p in (root / 'voice_library').rglob('*'))
        return {'saved_missing': saved_missing, 'saved': saved, 'again': again, 'tree': tree}

    assert_same(run_both(build, call), 'archive_job_voices')
    res = shape('ref', build, call)
    assert res['saved_missing'] == 0 and res['saved'] == 2, res
    assert res['again'] == 2, res                                   # lần 2 vẫn tính là đã lưu
    voices = [t for t in res['tree'] if t.endswith('final_voice.mp3')]
    assert len(voices) == 2 and len(res['tree']) == 8, res['tree']    # folder + 3 file mỗi bản
    assert sum(1 for t in res['tree'] if t.endswith('source.srt')) == 2, res['tree']


# --------------------------------------------------------------------------- #
#  scan_voices
# --------------------------------------------------------------------------- #
def scan_fixture(root, mod):
    jobs = root / 'jobs'
    for n in range(3):
        name = f'2026092{n+1}_19010{n}_story_douyin_downloads_video{n}_ab12cd{n}'
        touch(jobs / name / 'tts' / f'v{n}' / 'final_voice.mp3', 100 + n,
              mtime = 1700000000 + n * 60)
        touch(jobs / name / 'srt' / f'v{n}.srt', 10, mtime = 1700000000 + n * 60)
    touch(jobs / '20260921_190100_story_bad_ab12cd0' / 'tts' / 'empty' / 'final_voice.mp3', 0)
    touch(jobs / '20260921_190100_story_bad_ab12cd0' / 'tts' / 'part' / 'part.wav', 33)
    lib = root / 'voice_library'
    folder = '20260920_100000_Thu-Vien_ab12cd34ef56789a0'
    touch(lib / folder / 'final_voice.mp3', 500, mtime = 1700000300)
    write_text(lib / folder / 'voice.json', json.dumps(
        {'label': 'Nhãn thư viện', 'created': '2026-01-02T03:04:05',
         'source_path': str(jobs / '20260921_190101_story_douyin_downloads_video1_ab12cd1'
                            / 'tts' / 'v1' / 'final_voice.mp3'),
         'audio': 'final_voice.mp3', 'srt': 'source.srt'}, ensure_ascii = False))
    folder2 = '20260919_090000_Khong-Meta_aabbccd34ef5678'
    touch(lib / folder2 / 'final_voice.wav', 600, mtime = 1700000400)
    write_text(lib / folder2 / 'voice.json', '{sai')
    folder3 = '20260918_080000_Khong-File_11223344556677'
    touch(lib / folder3 / 'final_voice.flac', 700, mtime = 1700000500)
    folder4 = '20260917_070000_Sai-Tao_ccbbaa99887766'
    touch(lib / folder4 / 'final_voice.ogg', 800, mtime = 1700000600)
    write_text(lib / folder4 / 'voice.json', json.dumps({'created': 'khong phai iso',
                                                         'label': 'X'}))
    touch(lib / '20260916_060000_Thu-Muon_11223344556600' / 'rerun.mp3', 900)
    (lib / 'only_txt').mkdir(parents = True, exist_ok = True)
    touch(lib / 'only_txt' / 'note.txt', 3)
    ext = root / 'xuats'
    touch(ext / 'video_one_voice_20260920_010101.mp3', 40, mtime = 1700000700)
    touch(ext / 'video_two_voice_20260920_010102_2.mp3', 41, mtime = 1700000760)
    touch(ext / 'khong_phai_voice_file.mp3', 42, mtime = 1700000800)
    touch(ext / 'zero_voice_20260920_010103.wav', 0, mtime = 1700000900)
    outside = root / ' ngoai' / 'Tep Long Tieng.mp3'
    touch(outside, 55, mtime = 1700001000)
    missing = root / 'ngoai' / 'bi-xoa.mp3'
    return {'jobs': jobs, 'ext': ext, 'outside': outside, 'missing': missing}


def scan_call(mod, root, f):
    with isolate(mod, root):
        mod.remember_external(f['outside'])
        mod.remember_external(f['missing'])                          # chưa có -> không được ghi
        touch(f['missing'], 9, mtime = 1700001100)
        mod.remember_external(f['missing'])
        f['missing'].unlink()
        rows = mod.scan_voices(f['jobs'], limit = 50,
                               extra_roots = (f['ext'], root / 'khong-co', str(f['ext'])))
        shaped = [entry_shape(mod, e) for e in rows]
        limited = mod.scan_voices(f['jobs'], limit = 2, extra_roots = [f['ext']])
        default = mod.scan_voices(f['jobs'])
        empty = [entry_shape(mod, e)['kind'] for e in mod.scan_voices(root / 'khong-co')]
        return {'rows': shaped, 'limited': [entry_shape(mod, e)['kind'] for e in limited],
                'default': [entry_shape(mod, e)['kind'] for e in default], 'empty': empty}


def scan_bridge(mod, root):
    return scan_call(mod, root, scan_fixture(root, mod))


def test_scan_voices():
    assert_same(run_both(scan_fixture, scan_bridge), 'scan_voices')


def test_scan_voices_shapes():
    res = shape('ref', scan_fixture, scan_bridge)
    kinds = [r['kind'] for r in res['rows']]
    labels = [r['label'] for r in res['rows']]
    assert kinds.count('story') == 3, kinds                          # job: kind lấy từ tên folder
    assert kinds.count('thư viện') == 4, kinds                       # 4 file audio hợp lệ
    assert kinds.count('MP3 đã xuất') == 3, kinds        # mọi file *_voice_*<suffix> còn sống
    assert kinds.count('ngoài') == 1, kinds                          # external còn sống
    assert res['rows'] == sorted(res['rows'], key = lambda r: r['mtime'], reverse = True), res
    assert res['limited'] == ['ngoài', 'MP3 đã xuất'], res['limited']
    assert res['default'] == ['ngoài'] + ['thư viện'] * 4 + ['story'] * 3, res['default']
    # job không tồn tại vẫn còn nguồn thư viện + danh sách ngoài
    assert res['empty'] == ['ngoài'] + ['thư viện'] * 4, res['empty']
    assert 'Nhãn thư viện' in labels, labels
    assert 'X' in labels, labels                                     # label từ voice.json hỏng ts
    assert all(e['size'] > 0 for e in res['rows']), res              # file 0 byte bị loại
    assert all('ab12cd' not in e['label'] for e in res['rows']
               if e['kind'] == 'story'), res                         # digest đã cắt khỏi nhãn
    job = [r for r in res['rows'] if r['kind'] == 'story'][0]
    assert job['srt'].endswith('.srt') and job['created'].startswith('2026-09-2'), job
    lib = [r for r in res['rows'] if r['label'] == 'Nhãn thư viện'][0]
    assert lib['created'] == '2026-01-02T03:04:05', lib              # created từ voice.json
    assert lib['path'].endswith('final_voice.mp3'), lib
    khong_meta = [r for r in res['rows'] if 'Khong-Meta' in r['label']][0]
    assert khong_meta['created'].startswith('2023-'), khong_meta      # fallback về mtime
    assert not [r for r in res['rows'] if r['label'] == 'rerun'], res  # không phải final_voice.*


def test_scan_voices_dedupe_and_limit():
    def build(root, mod):
        mod._f = scan_fixture(root, mod)

    def call(mod, root):
        with isolate(mod, root):
            f = mod._f
            rows = mod.scan_voices(f['jobs'], limit = 100, extra_roots = [f['ext'], f['ext']])
            paths = [normalize(e.path, root) for e in rows]
            return {'dup': len(paths) != len(set(paths)), 'n': len(rows),
                    'zero': len(mod.scan_voices(f['jobs'], limit = 0, extra_roots = [f['ext']])),
                    'neg': len(mod.scan_voices(f['jobs'], limit = -1, extra_roots = [f['ext']])),
                    'str_root': len(mod.scan_voices(str(f['jobs']), limit = 100))}

    assert_same(run_both(build, call), 'scan_voices chống trùng/limit')
    res = shape('ref', build, call)
    assert res['dup'] is False and res['zero'] == 0, res
    assert res['n'] == 10 and res['str_root'] == 7, res   # không có extra_roots thì mất 3 mục
    assert res['neg'] == 9, res                           # [:limit] của Python


# --------------------------------------------------------------------------- #
#  durations
# --------------------------------------------------------------------------- #
def duration_fixture(root, mod):
    entries = []
    for name, size in (('a.wav', 10), ('b.mp3', 20), ('c.mp3', 30), ('d.mp3', 40),
                       ('rong.mp3', 50), ('none.mp3', 60), ('hu-hong.mp3', 70)):
        p = touch(root / 'voice' / name, size)
        entries.append(mod.VoiceEntry(path = p, mtime = float(size), size = size,
                                      label = name, created = None, kind = 'k'))
    mod._entries = entries


def durations_call(mod, root):
    with isolate(mod, root):
        entries = list(mod._entries)
        filled_before = mod.load_cached_durations(entries)
        with stub_probe_module() as probe:
            mod.measure_durations(entries)
            first = [(e.label, e.duration_s) for e in entries]
            calls = [c[0] for c in probe.calls]
            probe.calls.clear()
            mod.measure_durations(list(entries))
            second_calls = [c[0] for c in probe.calls]
            filled_after = mod.load_cached_durations(entries)
            store = json.loads(mod.STORE_PATH.read_text(encoding = 'utf-8'))
            entries[0].size += 1                              # file đổi -> đo lại
            mod.measure_durations(entries)
            store2 = mod._load_store()
        return {'filled_before': filled_before, 'first': first, 'calls': calls,
                'second_calls': second_calls, 'after': filled_after,
                'durations': sorted(normalize(k, root) for k in store.get('durations', {})),
                'durations2': sorted(normalize(k, root) for k in store2.get('durations', {})),
                'values': sorted(round(v, 3) for v in store.get('durations', {}).values())}


def test_durations():
    assert_same(run_both(duration_fixture, durations_call), 'load/measure durations')
    res = shape('ref', duration_fixture, durations_call)
    assert res['filled_before'] == 0, res
    assert res['first'] == [('a.wav', 1.5), ('b.mp3', 60.25), ('c.mp3', 3661.5),
                            ('d.mp3', 0.5), ('rong.mp3', 0.0), ('none.mp3', 0.0),
                            ('hu-hong.mp3', 0.0)], res
    assert res['calls'] == ['a.wav', 'b.mp3', 'c.mp3', 'd.mp3', 'rong.mp3', 'none.mp3',
                            'hu-hong.mp3'], res
    # lần 2 chỉ đo lại những mục không có trong cache (0.0 / lỗi không được lưu)
    assert res['second_calls'] == ['rong.mp3', 'none.mp3', 'hu-hong.mp3'], res
    assert res['after'] == 4, res
    assert res['values'] == [0.5, 1.5, 60.25, 3661.5], res
    assert len(res['durations']) == 4 and len(res['durations2']) == 5, res


def test_measure_durations_trims_cache():
    def build(root, mod):
        pass

    def call(mod, root):
        with isolate(mod, root):
            entries = [mod.VoiceEntry(path = touch(root / 'v' / f'k{i}.mp3', 10), mtime = 1.0,
                                      size = 10, label = f'k{i}', created = None, kind = 'j')
                       for i in range(420)]
            with stub_probe_module():
                mod.measure_durations(entries)
            cached = mod._load_store().get('durations') or {}
            keys = list(cached)
            return {'n': len(cached), 'first': normalize(keys[0], root),
                    'last': normalize(keys[-1], root), 'sorted': keys == sorted(keys)}

    assert_same(run_both(build, call), 'measure_durations cắt cache')
    res = shape('ref', build, call)
    assert res['n'] == 400, res                                          # chỉ giữ 400 bản cuối
    assert 'k419' in res['last'] and 'k20.mp3' in res['first'], res
    assert 'k19.mp3' not in res['first'] and 'k19.mp3' not in res['last'], res


def test_load_cached_durations_only_cache():
    def build(root, mod):
        mod._e = [mod.VoiceEntry(path = touch(root / 'v' / 'x.mp3', 10), mtime = 5.0, size = 10,
                                 label = 'x', created = None, kind = 'j'),
                  mod.VoiceEntry(path = touch(root / 'v' / 'y.mp3', 20), mtime = 6.0, size = 20,
                                 label = 'y', created = None, kind = 'j')]

    def call(mod, root):
        with isolate(mod, root):
            store = mod._load_store()
            store['durations'] = {mod._cache_key(mod._e[0].path, 10, 5.0): 12,
                                  mod._cache_key(mod._e[1].path, 20, 6.0): 'chuỗi',
                                  'khác': 3.0}
            mod._save_store(store)
            before = [(e.label, e.duration_s) for e in mod._e]
            n = mod.load_cached_durations(mod._e)
            after = [(e.label, e.duration_s, type(e.duration_s).__name__) for e in mod._e]
            return {'before': before, 'n': n, 'after': after,
                    'empty': mod.load_cached_durations([]),
                    'written': mod.STORE_PATH.read_text(encoding = 'utf-8') != ''}

    assert_same(run_both(build, call), 'load_cached_durations')
    res = shape('ref', build, call)
    assert res == {'before': [('x', 0.0), ('y', 0.0)], 'n': 1,
                   'after': [('x', 12.0, 'float'), ('y', 0.0, 'float')], 'empty': 0,
                   'written': True}, res


def test_measure_durations_empty():
    def build(root, mod):
        pass

    def call(mod, root):
        with isolate(mod, root), stub_probe_module() as probe:
            mod.measure_durations([])
            mod.load_cached_durations([])
            return {'calls': probe.calls, 'store': mod._load_store()}

    assert_same(run_both(build, call), 'measure_durations rỗng')
    assert shape('ref', build, call) == {'calls': [], 'store': {}}


# --------------------------------------------------------------------------- #
#  xóa
# --------------------------------------------------------------------------- #
def delete_fixture(root, mod):
    lib = root / 'voice_library' / '20260920_100000_Label_ab12cd34ef567890'
    touch(lib / 'final_voice.mp3', 100)
    touch(lib / 'source.srt', 20)
    write_text(lib / 'voice.json', '{}')
    job = root / 'jobs' / '20260921_190101_story_clip_ab12cd1' / 'tts' / 'clip'
    touch(job / 'final_voice.mp3', 100)
    stray = root / 'xuats' / 'only_voice.mp3'
    touch(stray, 100)
    outside = root / ' ngoai' / 'Tep Noi.mp3'
    touch(outside, 100)
    paths = {'lib': lib / 'final_voice.mp3', 'job': job / 'final_voice.mp3',
             'stray': stray, 'outside': outside, 'missing': root / 'khong-co.mp3'}
    mod._paths = paths
    return paths


def delete_call(mod, root):
    p = delete_fixture(root, mod)
    with isolate(mod, root):
        mod.remember_external(p['outside'])
        mod.remember_external(p['stray'])
        key = mod._cache_key(Path(str(p['outside'])), 100, os.stat(p['outside']).st_mtime)
        store = mod._load_store()
        store['durations'] = {key: 3.0, 'lien-quan': 1.0}
        mod._save_store(store)
        E = mod.VoiceEntry
        got = [mod.delete_voice_entry(E(p['outside'], 1.0, 100, 'l', None, 'k')),
               mod.delete_voice_entry(str(p['stray'])),
               mod.delete_voice_entry(p['missing']),
               mod.delete_voice_entry(E(p['lib'], 1.0, 100, 'l', None, 'thư viện')),
               mod.delete_voice_entry(p['job'])]
        store2 = mod._load_store()
        lib_dir = mod.VOICE_LIBRARY_ROOT / '20260920_100000_Label_ab12cd34ef567890'
        tree = sorted(normalize(str(x.relative_to(root)), root) for x in root.rglob('*'))
        return {'r': got, 'durations': sorted(store2.get('durations', {})),
                'external': len(store2.get('external', [])), 'tree': tree,
                'lib_gone': not lib_dir.exists()}


def test_delete_voice_entry():
    assert_same(run_both(delete_fixture, delete_call), 'delete_voice_entry')
    res = shape('ref', delete_fixture, delete_call)
    assert res['r'] == [True, True, False, True, True], res
    assert res['lib_gone'] is True, res                              # nguyên folder thư viện bay
    assert res['durations'] == ['lien-quan'], res                     # cache liên quan bị xóa
    assert res['external'] == 0, res
    assert 'xuats/only_voice.mp3' not in res['tree'], res
    assert not any(t.endswith('clip/final_voice.mp3') for t in res['tree']), res


def test_delete_voice_entry_keeps_shared_parent():
    def build(root, mod):
        one = touch(root / 'xuats' / 'video_b_voice_2.mp3', 10)
        other = touch(root / 'xuats' / 'video_a_voice_1.mp3', 10)
        side = touch(root / 'xuats' / 'note.txt', 10)
        mod._p = (other, one, side)

    def call(mod, root):
        with isolate(mod, root):
            (other, one, side) = mod._p
            res = mod.delete_voice_entry(one)
            return {'res': res, 'other': other.is_file(), 'side': side.is_file(),
                    'dir': (root / 'xuats').is_dir()}

    assert_same(run_both(build, call), 'delete_voice_entry giữ thư mục còn file')
    assert shape('ref', build, call) == {'res': True, 'other': True, 'side': True, 'dir': True}


def test_delete_voice_entry_removes_only_leftover_folder():
    def build(root, mod):
        d = root / 'xuats'
        touch(d / 'a_voice_1.mp3', 10)
        touch(d / 'a.srt', 5)
        touch(d / 'a.json', 5)
        touch(d / 'a.part', 5)

    def call(mod, root):
        with isolate(mod, root):
            res = mod.delete_voice_entry(root / 'xuats' / 'a_voice_1.mp3')
            return {'res': res, 'dir': (root / 'xuats').exists()}

    assert_same(run_both(build, call), 'delete_voice_entry dọn folder chỉ còn phụ trợ')
    assert shape('ref', build, call) == {'res': True, 'dir': False}


def test_delete_all_voice_entries():
    def build(root, mod):
        p = delete_fixture(root, mod)
        lib = root / 'voice_library'
        (lib / 'rac').mkdir(parents = True, exist_ok = True)
        touch(lib / 'rac' / 'final_voice.mp3', 5)
        touch(lib / 'note.txt', 2)
        mod._p = p

    def call(mod, root):
        with isolate(mod, root):
            p = mod._p
            mod.remember_external(p['outside'])
            n = mod.delete_all_voice_entries(root / 'jobs', extra_roots = [root / 'xuats'])
            store = mod._load_store()
            tree = sorted(normalize(str(x.relative_to(root)), root) for x in root.rglob('*'))
            empty = mod.delete_all_voice_entries(root / 'khong-co')
        return {'n': n, 'store': store, 'tree': tree, 'empty': empty}

    assert_same(run_both(build, call), 'delete_all_voice_entries')
    res = shape('ref', build, call)
    assert res['store'] == {'external': [], 'durations': {}}, res
    assert res['empty'] == 0, res
    assert res['n'] == 4, res                                        # 2 file + 2 folder thư viện
    left = [t for t in res['tree'] if 'voice_library' in t]
    assert left == ['voice_library', 'voice_library/note.txt'], left  # file rời không bị đụng


# --------------------------------------------------------------------------- #
#  chống artifact decompile
# --------------------------------------------------------------------------- #
def test_decompile_artifacts_gone():
    src = (REPO / 'app' / 'services' / 'voice_history.py').read_text(encoding = 'utf-8')
    assert re.search(r'^\s*None\s*=', src, re.M) is None, 'có dòng gán cho None'
    for junk in ('Decompyle incomplete', '<NODE:', 'None(', "= None('')", '= <NODE'):
        assert junk not in src, f'còn artifact decompile: {junk}'

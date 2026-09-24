# -*- coding: utf-8 -*-
'''Đối chiếu app.services.voice_engine.zerotts_engine với bản đã phát hành.

ZeroTTS normally loads a 202M-parameter ONNX model.  Đây là module đã được
PyInstaller đông đặc nên import là nạp cả numpy/soundfile — vì vậy toàn bộ test
chỉ đi qua các nhánh **không** đụng model: gói ``zerotts`` giả, ``subprocess``
giả và thư mục tạm.  Không có mạng, không có suy luận ONNX.

Tầng 1: ``test_bytecode_matches_pyc`` — bytecode phải trùng 100% .pyc gốc.
Tầng 2: ``same_result`` / ``_each`` đối chiếu hành vi từng hàm.
'''
from __future__ import annotations

import contextlib
import dis
import marshal
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

import numpy as np

from _parity import INTERNAL, REPO, RefMissing, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.voice_engine.zerotts_engine'
SRC = REPO / 'app' / 'services' / 'voice_engine' / 'zerotts_engine.py'
PYC = INTERNAL / 'app' / 'services' / 'voice_engine' / 'zerotts_engine.pyc'

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


# ------------------------------------------------------------------ helpers ---
@contextlib.contextmanager
def fake_zerotts(normalize=None, punct=None, from_pretrained=None):
    '''Package ``zerotts`` giả — đủ để đi hết nhánh chuẩn hoá text và nạp model.'''
    log = []
    text_norm = types.ModuleType('zerotts.text_norm')
    text_norm.normalize_vi_text = normalize or (lambda t: 'VI(' + t + ')')
    chunking = types.ModuleType('zerotts.chunking')
    chunking.normalize_punctuation = punct or (lambda t: 'P(' + t + ')')
    root = types.ModuleType('zerotts')
    root.text_norm = text_norm
    root.chunking = chunking

    class ZeroTTS:
        @classmethod
        def from_pretrained(cls, target, providers=None, warmup=None):
            log.append(('from_pretrained', str(target), tuple(providers or []), warmup))
            return make_tts() if from_pretrained is None else from_pretrained(target, log)

    root.ZeroTTS = ZeroTTS

    def make_tts():
        def synthesize(text, voice, cfg_scale=None):
            log.append(('synthesize', text, voice, cfg_scale))
            return np.array([0.01, -0.02, 0.03], dtype=np.float32)

        def save_audio(audio, path):
            log.append(('save_audio', path))
            Path(path).write_bytes(b'RIFF' + b'\x00' * 200)

        return types.SimpleNamespace(synthesize=synthesize, save_audio=save_audio)

    names = {'zerotts': root, 'zerotts.text_norm': text_norm, 'zerotts.chunking': chunking}
    saved = {k: sys.modules.get(k, False) for k in names}
    sys.modules.update(names)
    try:
        yield log
    finally:
        for k, v in saved.items():
            if v is False:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


@contextlib.contextmanager
def fake_subprocess():
    '''Thay ``subprocess`` trong module để kiểm tra câu lệnh ffmpeg mà không chạy ffmpeg.'''
    log = []
    mod = types.SimpleNamespace(
        run=lambda cmd, **kw: (log.append((list(cmd), dict(kw))), None)[0],
        CREATE_NO_WINDOW=0x08000000)
    old = sys.modules.get('app.services.voice_engine.audio_merger', False)
    sys.modules['app.services.voice_engine.audio_merger'] = types.SimpleNamespace(
        find_ffmpeg_bin=lambda: '/fake/ffmpeg')
    yield log, mod
    if old is False:
        sys.modules.pop('app.services.voice_engine.audio_merger', None)
    else:
        sys.modules['app.services.voice_engine.audio_merger'] = old


def _each(fn, apply):
    '''Chạy ``apply(mod)`` trên repo và bản phát hành, đòi kết quả giống nhau.'''
    a = apply(repo_module(DOTTED))
    b = apply(ref_module(DOTTED))
    assert a == b, f'{fn}: repo={a!r} ref={b!r}'
    return a


@contextlib.contextmanager
def tmp_cwd(sub=None):
    tmp = Path(tempfile.mkdtemp(prefix='ztt_', dir=str(REPO / 'output')))
    cwd = os.getcwd()
    os.chdir(tmp if sub is None else tmp / sub)
    try:
        yield tmp
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)


def _relocate(mod, tmp):
    '''Dọn mọi đường dẫn ``Path(__file__).parents[k]`` về thư mục tạm đã kiểm soát.'''
    mod.__file__ = str(tmp / 'pkgx' / 'aa' / 'bb' / 'zerotts_engine.py')


# -------------------------------------------------------------- module data ---
def test_module_constants_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in ('SAMPLE_RATE', 'AUDIO_EXTENSIONS', 'ZEROTTS_PRESET_VOICES',
                 'VOICE_NAMES', 'VOICE_LABELS', 'VOICE_MAP', '_v'):
        assert getattr(rep, name) == getattr(ref, name), name
    assert len(ref.VOICE_NAMES) == 8
    assert len(ref.ZEROTTS_PRESET_VOICES) == 8
    # VOICE_MAP khoá đã lowercase, giá trị là id chuẩn
    assert ref.VOICE_MAP['mai chi'] == 'maichi'
    assert ref.VOICE_MAP['quang minh (nam - tin tức dứt khoát) | quangminh'] == 'quangminh'
    assert set(ref.VOICE_MAP) == {k.lower() for k in ref.VOICE_MAP}


VOICE_QUERY = [
    None, '', '   ', 'maichi', 'baotrang', 'kimoanh', 'hamy', 'giahuy', 'huuduc',
    'quangminh', 'tiendat', 'MAICHI', 'Mai Chi', 'mai chi', 'Mai Chi (Nữ - Kể chuyện nhẹ nhàng)',
    'Mai Chi (Nữ - Kể chuyện nhẹ nhàng) | maichi', 'lbl | maichi', 'abc|quangminh',
    'abc|khong-co', 'Quang Minh', 'TIẾN ĐẠT', 'tiến đạt', 'Hữu Đức (Nam - Điềm đạm lớn tuổi)',
    '  hamy  ', 'Gia Huy | giahuy', 'khong ton tai', 'zh-CN-XiaoxiaoNeural',
    'nam - kể chuyện trầm ấm', 'giahuy-extra', 'label: Kim Oanh (Nữ - Truyền cảm ấm áp)',
    'TIENDAT', 'Bao Trang', 'bảo trang', 'Ha My', 'baotrang|baotrang', '|hamy',
    '0', '1', 'true', 'mai',
]


def test_resolve_voice_name():
    bad = same_result(DOTTED, 'resolve_voice_name', [((v,), {}) for v in VOICE_QUERY])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


# ------------------------------------------------------------------ methods ---
def test_preset_voice_listing():
    def snap(mod):
        eng = mod.ZeroTTSEngine()
        eng._initialized = False
        eng.__init__()
        voices = [dict(v) for v in eng.list_preset_voices()]
        tuples = list(eng.list_voice_tuples())
        return (len(voices) == 8, voices[0]['id'], tuples[0], tuples[-1],
                eng.is_model_loaded())
    out = _each('list_preset_voices', snap)
    assert out[0] is True, out
    assert out[1] == 'maichi', out
    assert out[2] == ('Mai Chi (Nữ - Kể chuyện nhẹ nhàng) | maichi', 'maichi'), out
    assert out[3] == ('Tiến Đạt (Nam - Sôi nổi năng lượng) | tiendat', 'tiendat'), out
    assert out[4] is False, out


def test_singleton_identity():
    def snap(mod):
        a = mod.ZeroTTSEngine()
        b = mod.ZeroTTSEngine('y')
        return (a is b, a.model_id, getattr(a, '_initialized', None))
    _each('singleton', snap)
    # instance dùng chung toàn tiến trình -> kiểm tra không tạo对象 mới
    rep = repo_module(DOTTED)
    assert rep.ZeroTTSEngine() is rep.ZeroTTSEngine()


def test_preview_audio_path_offline():
    def snap(mod, tmp):
        _relocate(mod, tmp)
        eng = mod.ZeroTTSEngine()
        eng._initialized = False
        eng.__init__()
        got = eng.get_preview_audio_path('Mai Chi')
        return None if got is None else str(got).replace('\\', '/')
    with tmp_cwd() as tmp:
        _each('get_preview_audio_path', lambda m: snap(m, tmp))
        # đặt file mẫu đúng ngưỡng > 1000 byte thì hai bên phải trả cùng đường dẫn
        d = tmp / 'pkgx' / 'assets' / 'tts_samples' / 'zerotts'
        d.mkdir(parents=True, exist_ok=True)
        (d / 'maichi.wav').write_bytes(b'w' * 2000)
        got = _each('get_preview_audio_path hit', lambda m: snap(m, tmp))
        assert got and got.endswith('maichi.wav'), got
        # quá nhỏ -> bỏ qua
        (d / 'maichi.wav').write_bytes(b'w' * 100)
        _each('get_preview_audio_path too small', lambda m: snap(m, tmp))
        assert snap(repo_module(DOTTED), tmp) is None


def test_normalize_text_offline():
    texts = ['', '   ', 'Xin chào các bạn.', '1,5 triệu đồng', 'Hà Nội, ngày 2/9/2024',
             'Nhiều     khoảng trắng', 'Tiếp tục…', 'In hoa ALL CAPS', 'a' * 400,
             'Có {placeholder} ở đây', 'Hết!!??', 'Số 42 và 3.14', 'TP.HCM', 'Ngày 1/1',
             '\n nhiều dòng \n', 'emoji 😀', 'rồi thì', 'Khoan đã…', '100%', 'A — B']
    cases = [((t,), {}) for t in texts]
    with fake_zerotts():
        bad = same_result(DOTTED, 'ZeroTTSEngine.normalize_text', cases)
        assert not bad, bad
    # zerotts không có ở cả hai nguồn -> trả nguyên văn bản đã strip
    pkg = types.ModuleType('app.services.voice_engine')
    with _seed({'zerotts': None, 'app.services.voice_engine': pkg}):
        bad = same_result(DOTTED, 'ZeroTTSEngine.normalize_text', cases)
        assert not bad, bad
        for mod in (repo_module(DOTTED), ref_module(DOTTED)):
            assert mod.ZeroTTSEngine().normalize_text('  Xin chào  ') == 'Xin chào'


def test_normalize_text_provider_error():
    '''Nhà cung cấp nổ -> phải log rồi trả text gốc, không được làm chết luồng.'''
    def boom(t):
        raise RuntimeError('text_norm hỏng')
    cases = [((t,), {}) for t in ['Xin chào', 'a b c', '123']]
    with fake_zerotts(normalize=boom):
        bad = same_result(DOTTED, 'ZeroTTSEngine.normalize_text', cases)
        assert not bad, bad
        assert repo_module(DOTTED).ZeroTTSEngine().normalize_text('Xin chào') == 'Xin chào'


def test_load_zerotts_module_offline():
    with fake_zerotts() as log:
        got = _each('_load_zerotts_module', lambda m: m._load_zerotts_module() is not None)
        assert got is True
    with _block('zerotts'):
        # Nhánh hai import `from app.services.voice_engine import zerotts` — kết quả
        # tuỳ package của repo đã sửa được tới đâu, nên chỉ đòi HAI BÊN GIỐNG NHAU.
        got = _each('_load_zerotts_module missing', lambda m: _call(m._load_zerotts_module))
        assert got[0] in ('ok', 'err'), got


def _call(fn):
    try:
        return ('ok', fn())
    except Exception as exc:
        return ('err', type(exc).__name__)


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


def test_resolve_local_cached_model_path():
    with tmp_cwd() as tmp:
        d = tmp / 'model'
        d.mkdir()
        (d / 'onnx').mkdir()

        def snap(mod):
            return [mod._resolve_local_cached_model_path(v) for v in
                    [None, '', '   ', str(d), str(tmp / 'khong-co'),
                     'zeroweight-ai/ZeroTTS', './model']]
        a = snap(repo_module(DOTTED))
        b = snap(ref_module(DOTTED))
        assert a[0] is None and a[1] == ''
        assert str(d) in a[3], a
        assert a == b, (a, b)
        # cache Hugging Face giả lập: có config.json + 2 file kia -> trả thư mục
        fake_dir = tmp / 'hf' / 'snapshots' / 'rev'
        (fake_dir / 'onnx').mkdir(parents=True)
        for f in ('config.json', 'null_voice_emb.npy', 'onnx/text_encoder.onnx'):
            (fake_dir / f).write_text('{}', encoding='utf-8')
        found = {'cached_file': str(fake_dir / 'config.json')}
        hub = types.ModuleType('huggingface_hub')
        hub.try_to_load_from_cache = lambda repo, filename: found['cached_file']
        with _seed({'huggingface_hub': hub}):
            got = _each('_resolve_local_cached_model_path cache',
                        lambda m: str(Path(m._resolve_local_cached_model_path('some/repo'))
                                      .name))
            assert got == 'rev', got
            other = tmp / 'hf' / 'snapshots' / 'rev2'
            other.mkdir()
            found['cached_file'] = str(other / 'config.json')
            got2 = _each('_resolve_local_cached_model_path partial',
                         lambda m: m._resolve_local_cached_model_path('some/repo'))
            assert got2 == 'some/repo', got2


@contextlib.contextmanager
def _seed(mapping):
    saved = {k: sys.modules.get(k, False) for k in mapping}
    sys.modules.update(mapping)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is False:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def test_get_tts_lazy_load_offline():
    '''Nạp model được giả lập hoàn toàn: chỉ đo tham số gửi vào from_pretrained.'''
    with tmp_cwd() as tmp:
        d = tmp / 'model'
        d.mkdir()
        results = {}
        logs = {}
        for tag, mod in (('repo', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
            with fake_zerotts() as log:
                eng = mod.ZeroTTSEngine()
                eng._initialized = False
                eng.__init__(str(d))
                before = eng.is_model_loaded()
                tts = eng._get_tts()
                results[tag] = (before, tts is not None, eng.is_model_loaded(),
                                eng._is_loading)
                logs[tag] = list(log)
        assert results['repo'] == results['ref'], results
        assert results['repo'] == (False, True, True, False)
        assert logs['repo'] == logs['ref'], (logs['repo'], logs['ref'])
        assert logs['repo'][0][1] == str(d), logs['repo']
        assert logs['repo'][0][2] == ('CPUExecutionProvider',)
        assert logs['repo'][0][3] is True


def test_get_tts_without_package():
    def snap(mod):
        eng = mod.ZeroTTSEngine('khong-co/Model')
        eng._initialized = False
        eng.__init__()
        try:
            eng._get_tts()
        except Exception as exc:
            return (type(exc).__name__, str(exc))
        return 'no-raise'
    def boom_build(target, blog):
        raise RuntimeError('onnx thiếu')

    with fake_zerotts(from_pretrained=boom_build):
        got = _each('_get_tts model error', snap)
        assert got[0] == 'RuntimeError', got
        assert got[1].startswith('Không thể khởi tạo ZeroTTS: '), got
    with _block('zerotts'):
        got = _each('_get_tts no package', snap)
        assert got[0] in ('RuntimeError', 'SyntaxError'), got


def test_process_audio_output_commands():
    cases = [(0.5, False), (1.0, False), (1.2, False), (2.5, False), (0.2, True),
             (1.0, True), (1.001, False), (0.96, False), (0.94, False), (3.0, True),
             (0.5, True), (2.0, False), (1.34, True), (0.75, False), (1.05, False)]
    with fake_subprocess() as (log, fake):
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        for speed, mp3 in cases:
            got = {}
            for tag, mod in (('repo', rep), ('ref', ref)):
                log.clear()
                old = mod.subprocess
                mod.subprocess = fake
                try:
                    eng = mod.ZeroTTSEngine()
                    eng._initialized = False
                    eng.__init__()
                    eng._process_audio_output('/in.wav', '/out.wav',
                                              speed=speed, is_mp3=mp3)
                    got[tag] = list(log)
                finally:
                    mod.subprocess = old
            assert got['repo'] == got['ref'], (speed, mp3, got)
            cmd, kw = got['repo'][0]
            assert cmd[0] == '/fake/ffmpeg' and '-y' in cmd and '-i' in cmd
            assert (kw.get('check') is True) and (kw.get('capture_output') is True)
            if abs(max(0.5, min(2.0, speed)) - 1.0) > 0.05:
                assert any(x.startswith('atempo=') for x in cmd), cmd
            assert ('libmp3lame' in cmd) is mp3
            assert '-ar' in cmd and '48000' in cmd


def test_synthesize_value_error():
    cases = [((), {'text': t}) for t in ['', '   ', None, '\n\t ', '\u200b']]
    bad = same_result(DOTTED, 'ZeroTTSEngine.synthesize', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]
    got = None
    try:
        repo_module(DOTTED).ZeroTTSEngine().synthesize('   ')
    except ValueError as exc:
        got = str(exc)
    assert got == 'Văn bản rỗng, không thể tổng hợp giọng đọc.', got


def test_synthesize_offline_with_fake_tts():
    '''numpy -> WAV qua soundfile, hoặc fallback save_audio của provider.'''
    arr1 = np.array([0.1, -0.2, 0.3, 0.4], dtype=np.float32)
    arr2 = np.array([[0.1, 0.2], [-0.3, 0.4], [0.5, -0.6]], dtype=np.float32)
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        outcomes = {}
        for kind, audio in (('mono', arr1), ('stereo', arr2), ('raw', object())):
            got = {}
            for tag, mod in (('repo', rep), ('ref', ref)):
                log = []

                def synth(text, voice, cfg_scale=None):
                    log.append(('synthesize', text, voice, cfg_scale))
                    return audio

                def save(a, path):
                    log.append(('save_audio', Path(path).name))
                    Path(path).write_bytes(b'RIFF' + b'\x00' * 400)

                def build(target, blog):
                    return types.SimpleNamespace(synthesize=synth, save_audio=save)

                with fake_zerotts(from_pretrained=build), fake_subprocess() as (slog, fake):
                    old = mod.subprocess
                    mod.subprocess = fake
                    try:
                        eng = mod.ZeroTTSEngine(str(tmp / 'model'))
                        eng._initialized = False
                        eng.__init__()
                        eng._tts = None
                        out = tmp / tag / f'{kind}.wav'
                        out.parent.mkdir(exist_ok=True)
                        path = eng.synthesize('Xin chào các bạn', voice='Mai Chi',
                                              out_path=str(out))
                        got[tag] = (list(log), Path(path).name, out.is_file(),
                                    out.stat().st_size if out.is_file() else -1,
                    )
                    finally:
                        mod.subprocess = old
            a, b = got['repo'], got['ref']
            assert a == b, (kind, a, b)
            outcomes[kind] = a
        # text đi qua normalize_text của provider giả (VI/P) rồi mới tới synthesize
        assert outcomes['mono'][0][0] == ('synthesize', 'P(VI(Xin chào các bạn))',
                                          'maichi', 1.0), outcomes['mono']
        assert outcomes['raw'][0][1][0] == 'save_audio', outcomes['raw']
        assert outcomes['mono'][2] is True and outcomes['mono'][3] > 0
        assert outcomes['stereo'][2] is True


def test_synthesize_speed_and_mp3_paths():
    '''Tốc độ != 1.0 hoặc .mp3 phải sinh đúng câu lệnh ffmpeg.'''
    with tmp_cwd() as tmp:
        ref, rep = ref_module(DOTTED), repo_module(DOTTED)
        for speed, ext in ((1.2, '.wav'), (0.8, '.wav'), (1.0, '.mp3'),
                           (2.0, '.mp3'), (1.0, '.wav')):
            cmds = {}
            for tag, mod in (('repo', rep), ('ref', ref)):
                audio = np.array([0.1, 0.2], dtype=np.float32)

                def synth(text, voice, cfg_scale=None):
                    return audio

                def build(target, blog):
                    return types.SimpleNamespace(synthesize=synth, save_audio=lambda *a: None)

                with fake_zerotts(from_pretrained=build), fake_subprocess() as (slog, fake):
                    old = mod.subprocess
                    mod.subprocess = fake
                    try:
                        eng = mod.ZeroTTSEngine(str(tmp / 'model'))
                        eng._initialized = False
                        eng.__init__()
                        eng._tts = None
                        out = tmp / f'{tag}-{speed}{ext}'
                        eng.synthesize('Xin chào', out_path=str(out), speed=speed)
                        cmds[tag] = [[x.replace(tag, 'X') for x in c] for c, _ in slog]
                    finally:
                        mod.subprocess = old
            assert cmds['repo'] == cmds['ref'], (speed, ext, cmds)
            if speed == 1.0 and ext == '.wav':
                assert cmds['repo'] == [], cmds
            else:
                assert any('atempo=' in x or 'libmp3lame' in x for x in cmds['repo'][0]), cmds


def test_signatures_match():
    import inspect
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in ('resolve_voice_name', '_ensure_safe_environment',
                 '_resolve_local_cached_model_path', '_load_zerotts_module'):
        assert str(inspect.signature(getattr(rep, name))) == \
            str(inspect.signature(getattr(ref, name))), name
    for name in ('is_model_loaded', '_get_tts', 'list_preset_voices', 'list_voice_tuples',
                 'get_preview_audio_path', 'normalize_text', 'synthesize',
                 '_process_audio_output', '__init__', '__new__'):
        a = str(inspect.signature(getattr(rep.ZeroTTSEngine, name)))
        b = str(inspect.signature(getattr(ref.ZeroTTSEngine, name)))
        assert a == b, (name, a, b)

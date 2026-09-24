# -*- coding: utf-8 -*-
'''Đối chiếu app.services.audio_sync_engine với bản đã phát hành.

AudioSyncEngine quyết định mỗi câu giọng nằm ở đâu trên timeline, nên phần tính
toán thuần (fit atempo/pad, khoá cache, manifest, duration meta) phải khớp từng
chữ. Phần phải chạy FFmpeg KHÔNG được thực thi ở đây — chỉ so mã lệnh qua
``_run`` đã chặn sẵn (xem test_build_atempo_command_uses_shared_filter_chain).
'''
from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.audio_sync_engine'

SPEAKABLE_EDGE = [
    '', '   ', None, '…', '—', '»»', '<b>x</b>', '{tag}', '<b>文字</b>',
    '123', '…1', '(!@#)', 'xin chào', '\n\t ', '́', '{a}{b}', '<>',
    '«»', 'ok.', '。。。', '①②③', 'emoji \U0001f600',
]

RATE_EDGE = [0.0001, 0.5, 0.999, 1.0, 1.02, 1.5, 2.0, 2.0001, 3.7, 4.0, 8.0, 9.5,
             100.0, 0.25, 0.1, 0.02, 1e-9, 1.35, 1.85, 1e6]


def test_dataclass_fields_match_reference():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for cls_name, args in (
            ('SubBlock', (1, 0.0, 2.5, 'a')),
            ('SegmentReport', (1, 'a', 2.5, 2.0, 'pad')),
            ('SyncResult', (True, None, 3))):
        a = getattr(rep, cls_name)(*args)
        b = getattr(ref, cls_name)(*args)
        assert repr(a) == repr(b), f'{cls_name}: {a!r} != {b!r}'
    blk = rep.SubBlock(1, 1.0, 4.25, 'x')
    assert blk.duration_s == ref.SubBlock(1, 1.0, 4.25, 'x').duration_s == 3.25
    assert rep.SubBlock(1, 5.0, 1.0, 'x').duration_s == 0.0


def test_is_speakable_text():
    bad = same_result(DOTTED, 'is_speakable_text', [((v,), {}) for v in SPEAKABLE_EDGE])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_build_atempo_filters():
    cases = [((v,), {}) for v in RATE_EDGE]
    cases += [((v,), {}) for v in (0, -1, -0.5)]
    bad = same_result(DOTTED, 'build_atempo_filters', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_build_atempo_filters_rejects_non_numeric():
    bad = same_result(DOTTED, 'build_atempo_filters', [(('1.5',), {}), ((None,), {})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_which_resolves_from_path():
    bad = same_result(DOTTED, '_which', [(('python',), {}), (('khong-co-bin-nay',), {})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_load_srt_blocks_without_pysrt_fails_identically():
    # bản đã cài có pysrt trong _internal nhưng không nằm trên sys.path của test
    tmp = Path(tempfile.mkdtemp())
    srt = tmp / 'a.srt'
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nA\n", encoding='utf-8')
    bad = same_result(DOTTED, 'load_srt_blocks', [((srt,), {})], block=('pysrt',))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def _fake_tts(normalize=None, parallel=None):
    def tts(text, out_path):
        return Path(out_path)

    if normalize is not None:
        tts.normalize_cache_text = normalize
    if parallel is not None:
        tts.parallel_allowed = parallel
    return tts


def _engines(**kw):
    '''Dựng engine giống hệt trên hai bản, mỗi bản một thư mục temp riêng.'''
    tmp = Path(tempfile.mkdtemp())
    out = {}
    for tag, mod in (('rep', repo_module(DOTTED)), ('ref', ref_module(DOTTED))):
        out[tag] = mod.AudioSyncEngine(tmp / tag, tts_func=kw.pop('tts_func', _fake_tts()), **kw)
        out[tag + '_mod'] = mod
    out['tmp'] = tmp
    return out


def test_resume_identity_stable_and_mode_sensitive():
    tmp = Path(tempfile.mkdtemp())
    srt = tmp / 'src.srt'
    srt.write_bytes('1\n00:00:01,000 --> 00:00:02,000\nA\n'.encode('utf-8'))
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for kwargs in ({}, {'voice_signature': 'abc'}, {'natural_voice_sync': True},
                   {'soft_timing_enabled': True},
                   {'soft_timing_enabled': True, 'natural_voice_sync': True},
                   {'sample_rate': 24000, 'max_speed_rate': 2.0, 'soft_max_atempo': 1.4}):
        a = rep.AudioSyncEngine(tmp / 'r', tts_func=_fake_tts(), **kwargs)
        b = ref.AudioSyncEngine(tmp / 'f', tts_func=_fake_tts(), **kwargs)
        assert a._resume_identity(srt) == b._resume_identity(srt), kwargs
    # các chế độ khác nhau phải cho khoá khác nhau
    plain = rep.AudioSyncEngine(tmp / 'p', tts_func=_fake_tts(), voice_signature='v')
    nat = rep.AudioSyncEngine(tmp / 'n', tts_func=_fake_tts(), voice_signature='v',
                              natural_voice_sync=True)
    assert plain._resume_identity(srt)[0] != nat._resume_identity(srt)[0]


def test_cue_dependencies():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for kwargs in ({}, {'voice_signature': 'sig', 'sample_rate': 48000},
                   {'soft_timing_enabled': True, 'soft_max_atempo': 1.4},
                   {'natural_voice_sync': True, 'max_speed_rate': 2.0}):
        a = rep.AudioSyncEngine(tmp / 'r', tts_func=_fake_tts(), **kwargs)
        b = ref.AudioSyncEngine(tmp / 'f', tts_func=_fake_tts(), **kwargs)
        rep_blk = rep.SubBlock(1, 0.0, 2.3456789, 'Xin chào')
        ref_blk = ref.SubBlock(1, 0.0, 2.3456789, 'Xin chào')
        got, want = a._cue_dependencies(rep_blk, 2.3456789), b._cue_dependencies(ref_blk, 2.3456789)
        assert got == want, (kwargs, got, want)
        assert got['duration_s'] == 2.345679, got['duration_s']


def test_normalised_tts_text():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    cases = [
        (_fake_tts(), ['thường', '', None, '  a  ']),
        (_fake_tts(normalize=lambda t: '[' + str(t).strip().lower() + ']'),
         ['Mixed CASE', '', None]),
        (_fake_tts(normalize=lambda t: 1 / 0), ['dự phòng khi normalizer nổ']),
    ]
    for factory, texts in cases:
        a = rep.AudioSyncEngine(tmp / 'r', tts_func=factory)
        b = ref.AudioSyncEngine(tmp / 'f', tts_func=factory)
        for text in texts:
            assert a._normalised_tts_text(text) == b._normalised_tts_text(text), (text, factory)


def test_raw_cache_lock_is_per_key():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for mod in (rep, ref):
        lock = mod._raw_cache_lock('key-a')
        assert isinstance(lock, type(threading.Lock())), type(lock)
        assert mod._raw_cache_lock('key-a') is lock
        assert mod._raw_cache_lock('key-b') is not lock


def test_resume_manifest_roundtrip_and_mismatch():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for tag, mod in (('rep', rep), ('ref', ref)):
        path = tmp / tag / 'manifest.json'
        payload = {'version': 1, 'job_key': 'job', 'completed': {'1': {'segment_path': 'x'}}}
        mod.AudioSyncEngine._write_resume_manifest(path, payload)
        assert mod.AudioSyncEngine._read_resume_manifest(path, 'job') == payload
        empty = mod.AudioSyncEngine._read_resume_manifest(path, 'khac')
        assert empty == {'version': 1, 'job_key': 'khac', 'completed': {}}, empty
        missing = mod.AudioSyncEngine._read_resume_manifest(tmp / tag / 'none.json', 'job')
        assert missing == {'version': 1, 'job_key': 'job', 'completed': {}}
        # manifest hỏng: không nổ, trả rỗng
        broken = tmp / tag / 'hung.json'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text('{không phải json', encoding='utf-8')
        assert mod.AudioSyncEngine._read_resume_manifest(broken, 'job')['completed'] == {}
        # không ghi được thì cũng không nổ
        mod.AudioSyncEngine._write_resume_manifest(tmp / tag / 'a' / 'b' / 'c.json', payload)
    a = json.loads((tmp / 'rep' / 'manifest.json').read_text(encoding='utf-8'))
    b = json.loads((tmp / 'ref' / 'manifest.json').read_text(encoding='utf-8'))
    assert a == b
    assert (tmp / 'rep' / 'manifest.json').read_text(encoding='utf-8') == \
        (tmp / 'ref' / 'manifest.json').read_text(encoding='utf-8')


def test_duration_meta_cache():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for tag, mod in (('rep', rep), ('ref', ref)):
        root = tmp / tag
        root.mkdir(parents=True, exist_ok=True)
        audio = root / 'a.wav'
        audio.write_bytes(b'x' * 500)
        meta = root / 'a.json'
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 0.0
        mod.AudioSyncEngine._write_duration_meta(meta, audio, 3.14159)
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 3.14159
        # file audio đổi kích thước → cache hết hiệu lực
        audio.write_bytes(b'y' * 400)
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 0.0
        # duration_s <= 0: không ghi gì thêm
        before = sorted(p.name for p in root.iterdir())
        mod.AudioSyncEngine._write_duration_meta(root / 'empty.json', audio, 0.0)
        assert sorted(p.name for p in root.iterdir()) == before
        mod.AudioSyncEngine._write_duration_meta(root / 'fail.json', audio, 1.0)
        assert (root / 'fail.json').is_file()
        meta.write_text('rác', encoding='utf-8')
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 0.0
        meta.write_text('[1, 2]', encoding='utf-8')
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 0.0
        meta.write_text('{"audio_size": 400, "duration_s": "2.5"}', encoding='utf-8')
        assert mod.AudioSyncEngine._read_duration_meta(meta, audio) == 2.5
    assert (tmp / 'rep' / 'a.json').read_text(encoding='utf-8') == \
        (tmp / 'ref' / 'a.json').read_text(encoding='utf-8')


def test_copy_atomic_and_quality_report():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    payload = {'a': 1, 'text': 'Xin chào', 'nested': {'b': [1, 2]}}
    for tag, mod in (('rep', rep), ('ref', ref)):
        src = tmp / f'{tag}-src.bin'
        src.write_bytes(b'12345')
        dst = tmp / tag / 'deep' / 'out.bin'
        mod.AudioSyncEngine._copy_atomic(src, dst)
        assert dst.read_bytes() == b'12345'
        assert not list(dst.parent.glob('*.tmp'))
        got = mod.AudioSyncEngine._write_quality_report(
            tmp / tag / 'report.json', payload)
        assert got.name == 'report.json'
    assert (tmp / 'rep' / 'report.json').read_text(encoding='utf-8') == \
        (tmp / 'ref' / 'report.json').read_text(encoding='utf-8')


def test_engine_defaults_match_reference():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    tmp = Path(tempfile.mkdtemp())
    a = rep.AudioSyncEngine(tmp / 'rep', tts_func=_fake_tts())
    b = ref.AudioSyncEngine(tmp / 'ref', tts_func=_fake_tts())
    assert a.ffmpeg == b.ffmpeg and a.ffprobe == b.ffprobe
    assert a.sample_rate == b.sample_rate == 44100
    assert a.max_speed_rate == b.max_speed_rate == 1.85
    assert a.min_segment_s == b.min_segment_s == 0.08
    assert (a.soft_max_drift_s, a.soft_min_gap_s, a.soft_max_atempo) == \
        (b.soft_max_drift_s, b.soft_min_gap_s, b.soft_max_atempo) == (1.5, 0.12, 1.1)
    assert a.fast_tts_workers == b.fast_tts_workers == 1
    assert a.resume_job_key == b.resume_job_key == ''


def _capture(mod, tmp, durations=(), **kw):
    '''Chặn ``_run`` + ``probe_duration_s``: lấy đúng lệnh FFmpeg, không chạy FFmpeg.'''
    eng = mod.AudioSyncEngine(tmp, tts_func=kw.pop('tts_func', _fake_tts()), **kw)
    cmds = []
    seq = list(durations)
    orig_run, orig_probe = mod._run, mod.probe_duration_s
    mod._run = lambda cmd, timeout=600: cmds.append([str(c) for c in cmd])
    mod.probe_duration_s = lambda path, ffprobe_bin=None: seq.pop(0)
    return eng, cmds, (orig_run, orig_probe)


def _release(mod, saved):
    mod._run, mod.probe_duration_s = saved


def _norm(rows, tag):
    return [[c.replace('\\', '/').replace(f'/{tag}/', '/') for c in row] for row in rows]


def test_ffmpeg_command_construction():
    '''Chuỗi lệnh FFmpeg của từng bước fit phải giống hệt bản đã phát hành.'''
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    src, dst = tmp / 'src.wav', tmp / 'dst.wav'
    for rate, exact in ((1.0, None), (1.35, 2.0), (3.0, 1.5), (0.4, None), (1.0, 0.0)):
        collected = {}
        for tag, mod in (('rep', rep), ('ref', ref)):
            eng, cmds, saved = _capture(mod, tmp / tag, durations=[])
            try:
                eng._apply_atempo(src, dst, rate, exact_duration=exact)
                eng._pad_silence_end(src, dst, 0.25, exact_duration=exact)
                eng._copy_audio(src, dst, exact_duration=exact)
                eng._make_silence(dst, 1.234)
                # _force_exact_duration đề up file temp -> cho temp tồn tại sẵn
                (tmp / tag / 'x.wav').write_bytes(b'1')
                (tmp / tag / 'x.exact.wav').write_bytes(b'2')
                eng._force_exact_duration(tmp / tag / 'x.wav', 2.5)
            finally:
                _release(mod, saved)
            collected[tag] = _norm(cmds, tag)
        assert collected['rep'] == collected['ref'], (rate, exact, collected)


def test_timeline_mix_and_concat_commands():
    '''Lệnh trộn timeline (adelay/amix) và concat — dựng graph thật, không chạy FFmpeg.'''
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    collected = {}
    for tag, mod in (('rep', rep), ('ref', ref)):
        eng, cmds, saved = _capture(mod, tmp / tag, durations=[])
        try:
            a1, a2 = tmp / tag / 'a1.wav', tmp / tag / 'a2.wav'
            eng._mix_timeline_batch([(a1, 0.0), (a2, 1.5)], tmp / tag / 'mix.wav', origin_s=0.5)
            eng._mix_timeline_batch([(a1, 0.0)], tmp / tag / 'mix.mp3', origin_s=0.0)
            parts = [a1, a2]
            eng._concat_sequential(parts, tmp / tag / 'seq.wav')
            blocks = [mod.SubBlock(0, 0.0, 1.0, 'a'), mod.SubBlock(1, 2.0, 3.5, 'b')]
            eng._concat_with_timeline_gaps(blocks, parts, tmp / tag / 'gap.wav')
            eng._mix_with_timeline_overlap(blocks, parts, tmp / tag / 'nat.wav')
        finally:
            _release(mod, saved)
        collected[tag] = (_norm(cmds, tag), str(eng.work_dir / 'concat_list.txt'))
    assert collected['rep'][0] == collected['ref'][0], collected


def test_ffmpeg_concat_list_falls_back_to_mp3():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    out = {}
    for tag, mod in (('rep', rep), ('ref', ref)):
        rows = []
        orig_run = mod._run

        def fake_run(cmd, timeout=600, rows=rows):
            rows.append([str(c) for c in cmd])
            if 'copy' in rows[-1]:                    # giả lập FFmpeg chê stream copy
                raise RuntimeError('codec không hợp lệ')
        mod._run = fake_run
        try:
            eng = mod.AudioSyncEngine(tmp / tag, tts_func=_fake_tts())
            lst = eng.work_dir / 'list.txt'
            got = eng._ffmpeg_concat_list(lst, tmp / tag / 'a.wav')
            got2 = eng._ffmpeg_concat_list(lst, tmp / tag / 'b.mp3')
        finally:
            mod._run = orig_run
        out[tag] = ([p.name for p in (got, got2)], _norm(rows, tag))
    assert out['rep'][0] == out['ref'][0] == ['a.mp3', 'b.mp3'], out
    assert out['rep'][1] == out['ref'][1], out


def test_process_one_block_decision_table():
    '''Bảng quyết định atempo / pad / skip — trái tim của chống đè giọng.'''
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    cases = [
        (2.0, 2.0, {}),
        (2.0, 1.0, {}),                                  # phải ép tốc độ 2.0x
        (2.0, 1.0, {'max_speed_rate': 1.35}),            # chạm trần → giữ đuôi
        (1.0, 2.0, {}),                                  # pad
        (1.0, 2.0, {'soft_timing_enabled': True}),       # soft: copy nguyên
        (2.0, 1.0, {'natural_voice_sync': True}),
        (2.0, 1.0, {'natural_voice_sync': True, 'max_speed_rate': 1.2}),
        (1.0, 1.0, {}),                                  # trong dung sai eps
        (0.5, 0.5, {}),
        (10.0, 0.2, {}),                                 # tốc độ cực đại, chuỗi atempo dài
        (0.05, 3.0, {}),                                 # pad rất dài
    ]
    for d_voice, d_sub, kw in cases:
        rows = {}
        for tag, mod in (('rep', rep), ('ref', ref)):
            eng, cmds, saved = _capture(mod, tmp / tag, durations=[d_voice], **kw)
            blk = mod.SubBlock(3, 0.0, d_sub, 'câu test')
            raw = tmp / tag / 'raw.wav'
            raw.write_bytes(b'123456789')
            try:
                _path, report = eng._process_one_block(blk, d_sub, prepared_raw=(raw, d_voice))
            finally:
                _release(mod, saved)
            rows[tag] = ((report.mode, report.speed_rate, report.pad_s, report.d_sub,
                          report.d_voice, report.index, Path(report.segment_path).name),
                         _norm(cmds, tag))
        assert rows['rep'] == rows['ref'], (d_voice, d_sub, kw, rows)


def test_process_one_block_unspeakable_and_error_paths():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    for text in ('…', '   ', '<b></b>', 'xin chào'):
        rows = {}
        for tag, mod in (('rep', rep), ('ref', ref)):
            eng, cmds, saved = _capture(mod, tmp / tag, durations=[])
            blk = mod.SubBlock(1, 0.0, 1.5, text)
            try:
                _path, report = eng._process_one_block(blk, 1.5)
            finally:
                _release(mod, saved)
            rows[tag] = ((report.mode, report.d_voice, report.pad_s,
                          Path(report.segment_path).name), _norm(cmds, tag))
        assert rows['rep'] == rows['ref'], (text, rows)

    # TTS nổ → độn silence, trừ khi provider đánh dấu no_silence_on_error
    for flag in (False, True):
        def boom(text, out_path, _flag=flag):
            raise RuntimeError('provider shark ret=-6')
        boom.no_silence_on_error = flag
        rows = {}
        for tag, mod in (('rep', rep), ('ref', ref)):
            eng, cmds, saved = _capture(mod, tmp / tag, durations=[], tts_func=boom)
            blk = mod.SubBlock(2, 0.0, 1.0, 'câu chữ')
            try:
                _path, report = eng._process_one_block(blk, 1.0)
                outcome = ('ok', report.mode, report.error)
            except Exception as exc:
                outcome = ('err', type(exc).__name__, str(exc))
            finally:
                _release(mod, saved)
            rows[tag] = (outcome, len(cmds))
        assert rows['rep'] == rows['ref'], (flag, rows)



def test_constructor_normalises_options():
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    hexkey = 'a' * 64
    for kwargs in ({'resume_job_key': '  ' + hexkey.upper() + '  '},
                   {'resume_job_key': 'ngắn'},
                   {'resume_job_key': hexkey + 'z'},
                   {'fast_tts_workers': 5}, {'fast_tts_workers': 0},
                   {'soft_max_drift_s': -3, 'soft_min_gap_s': -1, 'soft_max_atempo': 0.2},
                   {'resume_metadata': None}, {'resume_metadata': {'k': 1}}):
        a = rep.AudioSyncEngine(tmp / 'r', tts_func=_fake_tts(), **kwargs)
        b = ref.AudioSyncEngine(tmp / 'f', tts_func=_fake_tts(), **kwargs)
        skip = ('work_dir', 'seg_dir', 'tts_func')
        got = {k: v for k, v in vars(a).items() if k not in skip}
        want = {k: v for k, v in vars(b).items() if k not in skip}
        assert got == want, (kwargs, got, want)
    for mod in (rep, ref):
        try:
            mod.AudioSyncEngine(tmp / 'x')
        except ValueError as exc:
            assert 'tts_func' in str(exc)
        else:
            raise AssertionError('thiếu tts_func phải nổ ValueError')


def test_soft_timing_plan_is_pure_arithmetic():
    '''_apply_soft_timing_plan đọc duration từng file → cho ffprobe giả, so hai bản.

    Hai bản được feed cùng một dãy duration nên phần còn lại (đẩy/trễ/giới hạn
    drift) thuần là số học.  Không có nhánh nào được phép chạm FFmpeg ở đầu vào
    này (mọi ``atempo`` đều bị ``available`` chặn lại).
    '''
    tmp = Path(tempfile.mkdtemp())
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    # Mọi kịch bản dưới đây được chọn để ``available`` luôn đủ dài: nhánh atempo
    # (phải chạy FFmpeg) không bao giờ kích hoạt.
    scenarios = [
        ([1.0, 1.0, 1.0], 1.5, 0.12),
        ([0.4, 0.4, 0.4], 1.5, 0.12),
        ([0.2, 0.2, 0.2], 0.0, 0.0),
        ([2.0, 2.0], 5.0, 0.0),
        ([1.5, 1.5], 10.0, 0.2),
        ([0.2, 0.2, 0.2], 0.0, 5.0),
        ([0.0], 1.5, 0.12),
    ]
    probe_rep, probe_ref = rep.probe_duration_s, ref.probe_duration_s
    for durations_in, drift, gap in scenarios:
        a = rep.AudioSyncEngine(tmp / 'r', tts_func=_fake_tts(), soft_timing_enabled=True,
                                soft_max_drift_s=drift, soft_min_gap_s=gap,
                                soft_max_atempo=1.1, sample_rate=44100)
        b = ref.AudioSyncEngine(tmp / 'f', tts_func=_fake_tts(), soft_timing_enabled=True,
                                soft_max_drift_s=drift, soft_min_gap_s=gap,
                                soft_max_atempo=1.1, sample_rate=44100)
        seq_a, seq_b = list(durations_in), list(durations_in)
        rep.probe_duration_s = lambda path, ffprobe_bin=None: seq_a.pop(0)
        ref.probe_duration_s = lambda path, ffprobe_bin=None: seq_b.pop(0)
        try:
            blocks_a = [rep.SubBlock(i, i * 1.0, i * 1.0 + 0.4, f'câu {i}')
                        for i in range(len(durations_in))]
            blocks_b = [ref.SubBlock(i, i * 1.0, i * 1.0 + 0.4, f'câu {i}')
                        for i in range(len(durations_in))]
            fitted_a = [tmp / 'r' / f'f{i}.wav' for i in range(len(durations_in))]
            fitted_b = [tmp / 'f' / f'f{i}.wav' for i in range(len(durations_in))]
            reports_a = [rep.SegmentReport(i, blocks_a[i].text, 0.4, durations_in[i], 'soft')
                         for i in range(len(durations_in))]
            reports_b = [ref.SegmentReport(i, blocks_b[i].text, 0.4, durations_in[i], 'soft')
                         for i in range(len(durations_in))]
            out_a = a._apply_soft_timing_plan(blocks_a, fitted_a, reports_a)
            out_b = b._apply_soft_timing_plan(blocks_b, fitted_b, reports_b)
        finally:
            rep.probe_duration_s, ref.probe_duration_s = probe_rep, probe_ref
        got = ([(x.index, x.start_s, x.end_s, x.text) for x in out_a[0]],
               [str(p).replace('\\', '/').replace('/r/', '/') for p in out_a[1]],
               out_a[2], [(r.mode, r.effective_start_s, r.shift_s, r.overlap_s,
                           r.speed_rate, Path(r.segment_path).name) for r in reports_a])
        want = ([(x.index, x.start_s, x.end_s, x.text) for x in out_b[0]],
                [str(p).replace('\\', '/').replace('/f/', '/') for p in out_b[1]],
                out_b[2], [(r.mode, r.effective_start_s, r.shift_s, r.overlap_s,
                            r.speed_rate, Path(r.segment_path).name) for r in reports_b])
        assert got == want, (durations_in, drift, gap, got, want)
        assert not (tmp / 'r' / 'segments').exists() or \
            not list((tmp / 'r' / 'segments').glob('tts_soft_*')), 'FFmpeg bị gọi'

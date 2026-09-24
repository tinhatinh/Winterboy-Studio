# -*- coding: utf-8 -*-
'''Đối chiếu app.services.tts_projects với bản đã phát hành.

Phần lớn hàm ở đây là logic thuần (parse voice signature, dựng lại khoá resume cũ,
đếm câu đã xong) nên so trực tiếp. Phần quét đĩa thì trỏ TTS_RESUME_ROOT / JOBS_ROOT
của cả hai bản vào thư mục tạm dựng giống hệt nhau.
'''
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
from pathlib import Path

from _parity import ref_module, repo_module

DOTTED = 'app.services.tts_projects'


def _stub_dependencies():
    '''job_workspace vẫn còn hỏng cú pháp -> tạm cung cấp JOBS_ROOT để nạp được module.'''
    try:
        import app.services.job_workspace                                    # noqa: F401
    except Exception:
        holder = types.ModuleType('app.services.job_workspace')
        holder.JOBS_ROOT = Path(tempfile.gettempdir()) / 'mumu_stub_jobs'
        sys.modules['app.services.job_workspace'] = holder


_stub_dependencies()


def _pair():
    return ref_module(DOTTED), repo_module(DOTTED)


def _cmp(func, cases, *, attrs=None):
    '''Gọi cùng một hàm trên 2 bản, trả về list mâu thuẫn [(case, repo, ref)].'''
    ref, rep = _pair()
    fn_ref, fn_rep = getattr(ref, func), getattr(rep, func)
    bad = []
    for args, kwargs in cases:
        try:
            a = ('ok', fn_rep(*args, **kwargs))
        except Exception as exc:
            a = ('err', type(exc).__name__)
        try:
            b = ('ok', fn_ref(*args, **kwargs))
        except Exception as exc:
            b = ('err', type(exc).__name__)
        if attrs:
            a = ('ok', attrs(a[1])) if a[0] == 'ok' else a
            b = ('ok', attrs(b[1])) if b[0] == 'ok' else b
        if repr(a) != repr(b):
            bad.append(((args, kwargs), a, b))
    return bad


def _tupel(value):
    return tuple(value)


def test_sha256_matches_hashlib():
    tmp = Path(tempfile.mkdtemp())
    small = tmp / 'small.bin'
    small.write_bytes(b'')
    big = tmp / 'big.bin'
    big.write_bytes(bytes(range(256)) * 9000)                      # > 1 chunk 1 MiB
    missing = tmp / 'khong-co.bin'
    want = {str(small): hashlib.sha256(b'').hexdigest(),
            str(big): hashlib.sha256(bytes(range(256)) * 9000).hexdigest()}
    bad = _cmp('_sha256', [((small,), {}), ((big,), {}), ((missing,), {}),
                           ((tmp,), {}), ((None,), {})])
    assert not bad, bad
    ref, _ = _pair()
    assert ref._sha256(small) == want[str(small)]
    assert ref._sha256(big) == want[str(big)], 'phải cộng dồn nhiều chunk'


def test_legacy_voice_parts():
    sigs = ['', None, 'khong-co-dau', '|', 'a|', '|b', 'CapCut|voice-1',
            'edge-tts|vi-VN-NamMinhNeural|1.25', 'ElevenLabs/turbo|v123',
            'ElevenLabs/|v123', 'ElevenLabs/multilingual/v2|v123',
            'Google Cloud TTS|vi-VN-Standard-A', 'Google Cloud TTS/us|vi-VN',
            'Google Cloud TTS/|vi-VN', 'unknown-engine|voice',
            'x|voice|', 'x|voice|0.5', 'x||1.5', 'CapCut|v|', 'ZeroTTS|z|2',
            'edge-tts|a|b|c|1.5']
    bad = _cmp('_legacy_voice_parts', [((s,), {}) for s in sigs])
    assert not bad, bad
    ref, _ = _pair()
    assert ref._legacy_voice_parts('edge-tts|vi-VN-NamMinhNeural|1.25') == \
        ('Edge TTS', '', 'vi-VN-NamMinhNeural', '1.25')
    assert ref._legacy_voice_parts('ElevenLabs/turbo|v123') == \
        ('ElevenLabs', 'turbo', 'v123', '1.0')
    assert ref._legacy_voice_parts('khong-co-dau') == ('', '', '', '1.0')
    assert ref._legacy_voice_parts('x|voice|') == ('x', '', 'voice', '1.0')


def _identity(stable):
    return hashlib.sha256(stable.encode('utf-8')).hexdigest()


def _resume_key(srt_hash, signature, max_speed_rate, natural, soft):
    identity = {'version': 1, 'srt_sha256': srt_hash, 'voice_signature': signature,
                'sample_rate': 44100, 'max_speed_rate': max_speed_rate,
                'min_segment_s': 0.08, 'natural_voice_sync': natural,
                'soft_timing_enabled': soft, 'soft_max_drift_s': 1.5,
                'soft_min_gap_s': 0.12, 'soft_max_atempo': 1.1}
    if natural:
        identity['natural_sync_policy'] = 'overlap_v1'
    if soft:
        identity['soft_timing_policy'] = 'shift_compress_report_v1'
    return _identity(json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                separators=(',', ':')))


def test_legacy_sync_modes():
    h = 'a' * 64
    cases = [
        ({'natural_voice_sync': True, 'soft_timing_enabled': False,
          'voice_signature': 'x|y'}, {'srt_hash': h, 'resume_key': 'deadbeef'}),
        ({'natural_voice_sync': 0, 'soft_timing_enabled': 1},
         {'srt_hash': h, 'resume_key': ''}),
        ({'soft_timing_enabled': None}, {'srt_hash': h, 'resume_key': ''}),
        ({'voice_signature': 'CapCut|v'}, {'srt_hash': h, 'resume_key': 'sai'}),
        ({}, {'srt_hash': h, 'resume_key': 'sai'}),
        ({'voice_signature': None}, {'srt_hash': '', 'resume_key': ''}),
        ({'natural_voice_sync': 'x', 'other': object()},
         {'srt_hash': h, 'resume_key': 'z'}),
    ]
    # 4 tổ hợp mode lịch sử phải được nhận ra đúng qua chính khoá resume cũ
    for sig in ('', 'CapCut|v', 'edge-tts|a|1.2'):
        for rate, natural, soft in ((1.35, True, False), (3.0, False, True),
                                    (3.0, False, False), (1.85, False, False)):
            key = _resume_key(h, sig, rate, natural, soft)
            cases.append(({'voice_signature': sig}, {'srt_hash': h, 'resume_key': key}))
    bad = _cmp('_legacy_sync_modes', cases)
    assert not bad, bad
    ref, _ = _pair()
    key = _resume_key(h, '', 1.35, True, False)
    assert ref._legacy_sync_modes({'voice_signature': ''}, srt_hash=h,
                                  resume_key=key) == (True, False)
    assert ref._legacy_sync_modes({'voice_signature': ''}, srt_hash=h,
                                  resume_key='sai') == (False, False)
    assert ref._legacy_sync_modes({}, srt_hash=h, resume_key=key) == (True, False)


def test_valid_completed_count():
    tmp = Path(tempfile.mkdtemp())
    good = tmp / 'c001.wav'
    good.write_bytes(b'x' * 500)
    tiny = tmp / 'c002.wav'
    tiny.write_bytes(b'x' * 50)
    cases = [
        ({},), ({'completed': None},), ({'completed': []},), ({'completed': {}},),
        ({'completed': {'1': good}},),
        ({'completed': {'1': {'segment_path': str(good)}}},),
        ({'completed': {'1': {'segment_path': str(tiny)}}},),
        ({'completed': {'1': {'segment_path': str(tmp)}}},),
        ({'completed': {'1': {'segment_path': ''}}},),
        ({'completed': {'1': {}}},),
        ({'completed': {'1': {'segment_path': str(good),
                              'report': {'mode': 'skip'}}}},),
        ({'completed': {'1': {'segment_path': str(good),
                              'report': {'mode': 'SKIP'}}}},),
        ({'completed': {'1': {'segment_path': str(good), 'report': {'mode': 'fit'}}}},),
        ({'completed': {'1': {'segment_path': str(good), 'report': {}}}},),
        ({'completed': {'1': {'segment_path': str(good), 'report': 'abc'}}},),
        ({'completed': {'1': {'segment_path': str(good)},
                        '2': {'segment_path': str(good)},
                        '3': {'segment_path': str(tiny)},
                        '4': 'khong phai dict'}},),
        ({'completed': {'1': {'segment_path': str(tmp / 'khong-co.wav')}}},),
        ({'completed': {'1': 5}},),
    ]
    bad = _cmp('_valid_completed_count', [(c, {}) for c in cases])
    assert not bad, bad
    ref, _ = _pair()
    assert ref._valid_completed_count(
        {'completed': {'1': {'segment_path': str(good)},
                       '2': {'segment_path': str(tiny)},
                       '3': {'segment_path': str(good), 'report': {'mode': 'skip'}}}}) == 1


def test_resolve_srt():
    tmp = Path(tempfile.mkdtemp())
    srt = tmp / 'a.srt'
    srt.write_text('1\n00:00:01,000 --> 00:00:02,000\nA\n', encoding='utf-8')
    digest = hashlib.sha256(srt.read_bytes()).hexdigest()
    cases = [
        ({}, {'x': tmp}),
        ({'source_srt': str(srt)}, {}),
        ({'source_srt': str(srt), 'srt_sha256': digest}, {}),
        ({'source_srt': str(srt), 'srt_sha256': digest.upper()}, {}),
        ({'source_srt': str(srt), 'srt_sha256': 'be' * 32}, {}),
        ({'source_srt': str(srt), 'srt_sha256': '  ' + digest + '  '}, {}),
        ({'source_srt': str(tmp / 'khong-co.srt')}, {}),
        ({'source_srt': '   '}, {'': tmp}),
        ({'srt_sha256': digest}, {digest: srt}),
        ({'srt_sha256': digest}, {digest.upper(): srt}),
        ({'srt_sha256': '  ' + digest.upper() + ' '}, {digest: srt}),
        ({'source_srt': str(srt), 'srt_sha256': digest}, {digest: tmp}),
        ({'source_srt': '~/khong-co.srt'}, {}),
        ({'source_srt': str(srt), 'srt_sha256': None}, {}),
        ({'source_srt': 5}, {}),
    ]
    bad = _cmp('_resolve_srt', [(a, b) for a, b in cases],
               attrs=lambda r: str(r) if r is not None else None)
    assert not bad, bad
    ref, _ = _pair()
    assert ref._resolve_srt({'source_srt': str(srt), 'srt_sha256': 'sai'}, {}) is None
    # không có srt_sha256 thì expected = '' -> tra legacy bằng khoá rỗng, không phải digest
    assert ref._resolve_srt({}, {digest: srt}) is None
    assert ref._resolve_srt({'srt_sha256': digest}, {digest: srt}) == srt
    assert ref._resolve_srt({'srt_sha256': '  ' + digest.upper() + ' '}, {digest: srt}) == srt
    assert ref._resolve_srt({'source_srt': str(srt)}, {}) == srt
    assert ref._resolve_srt({}, {'': tmp}) == tmp


def test_legacy_srt_lookup():
    ref, rep = _pair()
    tmp = Path(tempfile.mkdtemp())
    a, b = tmp / 'a.srt', tmp / 'b.srt'
    a.write_text('AAA', encoding='utf-8')
    b.write_text('BBB', encoding='utf-8')
    (tmp / 'c.txt').write_text('CCC', encoding='utf-8')
    sub = tmp / 'sub'
    sub.mkdir()
    (sub / 'd.srt').write_text('DDD', encoding='utf-8')
    hashes = {hashlib.sha256(p.read_bytes()).hexdigest(): p
              for p in (a, b, sub / 'd.srt')}
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        mod.JOBS_ROOT = tmp
        got = mod._legacy_srt_lookup(set(hashes))
        out[label] = sorted((k, str(v.relative_to(tmp)).replace('\\', '/'))
                            for k, v in got.items())
        mod.JOBS_ROOT = tmp / 'khong-ton-tai'
        assert mod._legacy_srt_lookup(set(hashes)) == {}
        mod.JOBS_ROOT = tmp
        assert mod._legacy_srt_lookup(set()) == {}
        assert mod._legacy_srt_lookup({'deadbeef'}) == {}
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    assert len(out['ref']) == 3, out['ref']


def test_legacy_srt_lookup_stops_when_satisfied():
    ref, _ = _pair()
    tmp = Path(tempfile.mkdtemp())
    keep = []
    for name in 'abcdefgh':
        p = tmp / (name + '.srt')
        p.write_text(name * 4000, encoding='utf-8')
        keep.append(p)
    ref.JOBS_ROOT = tmp
    wanted = {hashlib.sha256(keep[7].read_bytes()).hexdigest()}
    got = ref._legacy_srt_lookup(wanted)
    assert set(got) == wanted, got
    assert list(got.values()) == [keep[7]]


def test_tts_project_properties():
    ref, rep = _pair()
    fields = ('resume_dir', 'manifest_path', 'srt_path', 'source_video', 'target',
              'provider', 'voice_id', 'tts_speed', 'model_id', 'voice_signature',
              'total_cues', 'completed_cues', 'remaining_cues', 'status', 'updated_at',
              'updated_epoch', 'natural_voice_sync', 'soft_timing_enabled',
              'capcut_strict', 'capcut_fast_mode')
    a = [f.name for f in rep.TtsProject.__dataclass_fields__.values()]
    b = [f.name for f in ref.TtsProject.__dataclass_fields__.values()]
    assert a == b == list(fields), (a, b)
    c = [f.name for f in rep.TtsCheckpointCleanup.__dataclass_fields__.values()]
    assert c == ['kept', 'removed_projects', 'removed_files', 'reclaimed_bytes'], c

    def build(mod, srt, status):
        args = [mod.Path(srt), mod.Path('m.json'), mod.Path(srt), None, 'mp4', 'p', 'v',
                '1.0', 'mo', 'sig', 3, 2, 1, status, '2026', 1.0, True, False, None, None]
        return mod.TtsProject(*args)

    labels = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        labels[label] = [build(mod, 'C:/jobs/j1/work/a.srt', 'complete').label,
                         build(mod, 'C:/a.srt', 'complete').label,
                         build(mod, 'C:/x/a.srt', 'x').label]
        for st, want in (('complete', True), ('tts_ready', False),
                         ('needs_repair', False), ('', False)):
            assert build(mod, 'C:/a/b.srt', st).is_complete is want, (label, st)
    assert labels['repo'] == labels['ref'], labels
    # parents[1] hợp lệ -> tên job; IndexError -> fallback stem của SRT (ở đây là 'a')
    assert labels['ref'] == ['j1', 'a', 'a'], labels['ref']

    texts = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        texts[label] = [build(mod, 'C:/a/b.srt', st).status_label for st in
                        ('complete', 'tts_ready', 'needs_repair', 'not_started',
                         'in_progress', '', 'COMPLETE')]
    assert texts['repo'] == texts['ref'], texts
    assert texts['ref'][:4] == ['Đã hoàn thành', 'Đã đủ câu · chờ hoàn tất',
                                'Thiếu file · cần khôi phục',
                                'Chưa tạo câu nào'], texts['ref']
    assert texts['ref'][4:] == ['Đang thực hiện'] * 3, texts['ref']


def _write_project(root: Path, name: str, *, srt_text='1\n00:00:01,000 --> 00:00:02,000\nA\n',
                   payload=None, srt_name='a.srt'):
    d = root / name
    d.mkdir(parents=True)
    srt = d / srt_name
    digest = ''
    if srt_text is not None:
        srt.write_text(srt_text, encoding='utf-8')
        digest = hashlib.sha256(srt.read_bytes()).hexdigest()
    body = {'completed': {}, 'source_srt': str(srt) if srt_text is not None else '',
            'total_cues': 1, 'srt_sha256': digest}
    body.update(payload or {})
    (d / 'manifest.json').write_text(json.dumps(body, ensure_ascii=False), encoding='utf-8')
    return d


def test_list_tts_projects_matches_reference():
    ref, rep = _pair()
    specs = 'shared'

    def build(root):
        _write_project(root, 'ok', payload={'status': 'complete', 'total_cues': 2,
                                            'resume_metadata': {'target': 'mov',
                                                                'provider': 'Edge TTS',
                                                                'voice_id': 'v1',
                                                                'tts_speed': '1.25',
                                                                'natural_voice_sync': True,
                                                                'soft_timing_enabled': True}})
        _write_project(root, 'legacy-sig', payload={
            'voice_signature': 'edge-tts|vi-VN-NamMinhNeural|1.25', 'total_cues': 4,
            'status': 'running'})
        _write_project(root, 'no-srt', srt_text=None)
        _write_project(root, 'done', payload={'status': 'complete', 'total_cues': 1,
                                              'completed': {'1': {}}})
        _write_project(root, 'broken', payload={'updated_at': 'khong-phai-so'})
        (root / 'damaged').mkdir()
        (root / 'damaged' / 'manifest.json').write_text('{khong phai json',
                                                        encoding='utf-8')
        (root / 'nocompleted').mkdir()
        (root / 'nocompleted' / 'manifest.json').write_text(json.dumps(
            {'source_srt': 'x', 'total_cues': 1}), encoding='utf-8')
        _write_project(root, 'meta-v2', payload={
            'total_cues': 1, 'resume_metadata_version': '2',
            'resume_metadata': {'capcut_strict': True, 'capcut_fast_mode': False}})
        _write_project(root, 'meta-v1', payload={
            'total_cues': 1, 'resume_metadata_version': '1',
            'resume_metadata': {'capcut_strict': True}})
        _write_project(root, 'hash-only', srt_name='src.srt', payload={
            'source_srt': '', 'total_cues': 1})
        _write_project(root, 'empty-srt', srt_text='', payload={'total_cues': 2})

    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        root = Path(tempfile.mkdtemp())
        build(root)
        mod.TTS_RESUME_ROOT = root
        mod.JOBS_ROOT = root / 'khong-co'
        rows = [(p.srt_path.name, p.source_video, p.target, p.provider, p.voice_id,
                 p.tts_speed, p.model_id, p.voice_signature, p.total_cues,
                 p.completed_cues, p.remaining_cues, p.status, p.status_label,
                 p.natural_voice_sync, p.soft_timing_enabled, p.capcut_strict,
                 p.capcut_fast_mode,
                 # label suy ra từ tên thư mục tạm, 2 bản dùng 2 thư mục khác nhau
                 p.label.replace(root.name, '<root>'),
                 type(p.updated_epoch).__name__)
                for p in mod.list_tts_projects()]
        out[label] = rows
        assert mod.list_unfinished_tts_projects() == [
            p for p in mod.list_tts_projects() if not p.is_complete]
    assert out['repo'] == out['ref'], (out['repo'], out['ref'])
    statuses = {r[11] for r in out['ref']}
    assert {'complete', 'needs_repair', 'tts_ready', 'not_started'} & statuses, statuses


def test_total_cues_falls_back_to_load_srt_blocks():
    '''Thiếu total_cues -> gọi audio_sync_engine.load_srt_blocks (cần pysrt).

    Máy chạy test không cài pysrt, nên chỉ so được rằng HAI bản cùng đi tới cùng
    một chỗ và cùng nổ một kiểu — không được im lặng trả kết quả khác nhau.
    '''
    ref, rep = _pair()
    errs = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        root = Path(tempfile.mkdtemp())
        _write_project(root, 'no-total', payload={'total_cues': 0})
        mod.TTS_RESUME_ROOT = root
        mod.JOBS_ROOT = root / 'khong-co'
        try:
            errs[label] = ('ok', [p.total_cues for p in mod.list_tts_projects()])
        except Exception as exc:
            errs[label] = ('err', type(exc).__name__)
    assert errs['repo'] == errs['ref'], errs


def test_list_tts_projects_limit_and_empty():
    ref, rep = _pair()
    for mod in (ref, rep):
        mod.TTS_RESUME_ROOT = Path(tempfile.mkdtemp()) / 'khong-co'
        assert mod.list_tts_projects() == []
        assert mod.list_unfinished_tts_projects() == []
        assert mod.cleanup_old_tts_checkpoints(keep=1).kept == 0
    root = Path(tempfile.mkdtemp())
    for i in range(3):
        _write_project(root, f'p{i}', payload={'total_cues': 1,
                                               'updated_at': 1000.0 + i})
    rows = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        mod.TTS_RESUME_ROOT = root
        rows[label] = [(p.label, p.updated_epoch) for p in
                       mod.list_tts_projects(limit=2)]
    assert rows['repo'] == rows['ref'], rows
    assert len(rows['ref']) == 2, rows
    for label, mod in (('repo', rep), ('ref', ref)):
        mod.TTS_RESUME_ROOT = root
        assert len(mod.list_tts_projects(limit=0)) == 1
        assert len(mod.list_unfinished_tts_projects(limit='x' if False else 1)) == 1


def test_cleanup_old_tts_checkpoints():
    ref, rep = _pair()

    def build(root):
        for i in range(3):
            d = _write_project(root, f'p{i}', payload={'total_cues': 1,
                                                       'updated_at': 1000.0 + i})
            (d / 'seg001.wav').write_bytes(b'x' * (100 * (i + 1)))

    results = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        per_keep = []
        for keep in (1, 2, 5):
            root = Path(tempfile.mkdtemp())
            build(root)
            mod.TTS_RESUME_ROOT = root
            res = mod.cleanup_old_tts_checkpoints(keep=keep)
            per_keep.append((res.kept, res.removed_projects, res.removed_files,
                             res.reclaimed_bytes,
                             sorted(p.name for p in root.rglob('*'))))
        results[label] = per_keep
    assert results['repo'] == results['ref'], results
    assert results['ref'][0][0] == 1, results['ref'][0]
    assert results['ref'][0][1] == 2, results['ref'][0]
    assert results['ref'][0][3] > 300, results['ref'][0]   # 2 project cũ nhất
    assert results['ref'][2][:4] == (3, 0, 0, 0), results['ref'][2]
    # project giữ lại vẫn còn đủ manifest + segment
    assert 'manifest.json' in results['ref'][0][4], results['ref'][0][4]


def test_cleanup_refuses_to_delete_resume_root_itself():
    '''resume_dir phải nằm ngay trong TTS_RESUME_ROOT; sâu hơn hoặc trùng root là bỏ.'''
    ref, rep = _pair()
    for label, mod in (('repo', rep), ('ref', ref)):
        root = Path(tempfile.mkdtemp())
        outer = _write_project(root, 'binh-thuong', payload={'total_cues': 1,
                                                             'updated_at': 5.0})
        (outer / 'seg.wav').write_bytes(b'y' * 50)
        deep = root / 'cap-sau' / 'con'
        deep.mkdir(parents=True)
        (deep / 'manifest.json').write_text(json.dumps(
            {'completed': {}, 'source_srt': str(deep / 'a.srt'), 'total_cues': 1,
             'srt_sha256': 'x'}), encoding='utf-8')
        (deep / 'a.srt').write_text('1\n', encoding='utf-8')
        (deep / 'seg.wav').write_bytes(b'y' * 50)
        mod.TTS_RESUME_ROOT = root
        res = mod.cleanup_old_tts_checkpoints(keep=1)
        assert deep.is_dir(), (label, 'thư mục lồng sâu không được xoá')
        assert res.removed_projects <= 1, (label, res)

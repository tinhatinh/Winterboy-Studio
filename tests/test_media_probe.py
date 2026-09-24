# -*- coding: utf-8 -*-
'''Đối chiếu app.services.media_probe với bản đã phát hành.

media_probe gọi ffprobe qua subprocess. Test KHÔNG chạy ffprobe thật:
``subprocess.run`` và ``shutil.which`` được giả lập trong một phạm vi hẹp, vừa để
không sinh tiến trình, vừa để quan sát chính xác command line mà hàm dựng ra —
đây là phần hành vi cần khớp (danh sách tham số, encoding, creationflags, timeout)
cũng như cách hàm đọc stdout và ghi cache.
'''
from __future__ import annotations

import contextlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.media_probe'

TMP = Path(tempfile.mkdtemp())
VIDEO = TMP / 'clip.mp4'
VIDEO.write_bytes(b'fake-video-bytes')
AUDIO = TMP / 'nhac.mp3'
AUDIO.write_bytes(b'x' * 10)
NOTHING = TMP / 'khong-ton-tai.mp4'

FAKE_FFPROBE = r'C:\fake\bin\ffprobe.exe'


@contextlib.contextmanager
def fake_ffprobe(which = FAKE_FFPROBE, results = None, exc = None):
    '''Chặn shutil.which + subprocess.run; ghi lại mọi lệnh đáng lẽ đã chạy.

    results: list giá trị trả về cho run (lấy lần lượt); hết phần tử thì dùng
    phần tử cuối. exc: exception ném ra thay vì trả kết quả.
    '''
    log = []
    queue = list(results or [])
    real_which, real_run = shutil.which, subprocess.run

    def _which(cmd, *a, **k):
        if cmd == 'ffprobe':
            return which
        return real_which(cmd, *a, **k)

    def _run(cmd, *a, **k):
        log.append(([str(c) for c in cmd], sorted(k), tuple(sorted(
            (key, repr(v)) for key, v in k.items()))))
        if exc is not None:
            raise exc
        if not queue:
            return subprocess.CompletedProcess(cmd, 0, '', '')
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, BaseException):
            raise item
        return item

    def _ok(stdout, code = 0):
        return subprocess.CompletedProcess(['ffprobe'], code, stdout, '')

    prev_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)             # hai bên đều im lặng như nhau
    shutil.which, subprocess.run = _which, _run
    try:
        yield log, _ok
    finally:
        shutil.which, subprocess.run = real_which, real_run
        logging.disable(prev_disable)


def _caches(mod):
    return {name: {repr(k): v for k, v in getattr(mod, name).items()}
            for name in ('_CACHE_SIZE', '_CACHE_DURATION', '_CACHE_DETAILS')}


def _clear_all():
    for mod in (ref_module(DOTTED), repo_module(DOTTED)):
        mod.clear_probe_cache()


def _run_both(func, arg, *, which = FAKE_FFPROBE, results = None, exc = None):
    '''Gọi func trên cả hai bản với cùng một ffprobe giả -> so ba thứ:
    kết quả, command line đã dựng, và nội dung cache sau lời gọi.'''
    out = []
    for mod in (repo_module(DOTTED), ref_module(DOTTED)):
        mod.clear_probe_cache()
        with fake_ffprobe(which = which, results = results, exc = exc) as (log, _ok):
            try:
                res = ('ok', getattr(mod, func)(arg))
            except Exception as exc2:                         # noqa: BLE001
                res = ('err', type(exc2).__name__, str(exc2))
        out.append((res, log, _caches(mod)))
    return out


def _cmp(func, arg, **kw):
    a, b = _run_both(func, arg, **kw)
    problems = []
    if describe_shape(a[0]) != describe_shape(b[0]):
        problems.append(('result', a[0], b[0]))
    if a[1] != b[1]:
        problems.append(('argv', a[1], b[1]))
    if repr(a[2]) != repr(b[2]):
        problems.append(('cache', a[2], b[2]))
    return problems


def describe_shape(res):
    kind = res[0]
    if kind == 'err':
        return 'err ' + ' '.join(map(str, res[1:]))
    val = res[1]
    return 'ok ' + repr(sorted(val.items()) if isinstance(val, dict) else val)


# ---------------------------------------------------------------- ffprobe giả
SIZE_OUT = ['1920x1080\n', '1920x1080', '1080x1920', '0x0', '-5x-9', '1x1',
            '1920x1080x2', '1920x1080\n720x480\n', 'abc', '', ' ', None,
            '1920X1080', ' 1920x1080 ', '1920 x 1080', 'x', 'x1080', '1920x',
            '99999x99999', '3840x2160', '0x1080', '1080x0', '1080.5x1920.5',
            'truexfalse', '1e3x2e3', '0x0\n']

DETAIL_JSON = [
    '{"format":{"duration":"12.5","size":"1024","bit_rate":"900000","format_name":"mp4"},'
    '"streams":[{"codec_type":"video","codec_name":"h264","width":1080,"height":1920,'
    '"avg_frame_rate":"30000/1001","r_frame_rate":"30000/1001"},'
    '{"codec_type":"audio","codec_name":"aac"}]}',
    '{"format":{},"streams":[]}',
    '{}',
    '',
    'not json at all',
    '{"format":{"duration":"N/A","size":"0","bit_rate":"N/A"},"streams":[]}',
    '{"format":{"duration":-3,"bit_rate":"12.7","size":"55"},"streams":[]}',
    '{"streams":[{"codec_type":"video","width":0,"height":0,"avg_frame_rate":"0/0"}]}',
    '{"streams":[{"codec_type":"video","width":720,"height":1280,"avg_frame_rate":"0/0"}]}',
    '{"streams":[{"codec_type":"video","width":720,"height":1280,"r_frame_rate":"25/1"}]}',
    '{"streams":[{"codec_type":"video","width":720,"height":1280}]}',
    '{"streams":[{"codec_type":"video","width":720,"height":1280,"avg_frame_rate":29.97}]}',
    '{"streams":[{"codec_type":"video","width":720,"height":1280,"avg_frame_rate":"abc"}]}',
    '{"streams":[{"codec_type":"video","width":"9","height":"9","avg_frame_rate":"9/2"}]}',
    '{"streams":[{"codec_type":"audio","codec_name":"pcm_s16le"},'
    '{"codec_type":"audio","codec_name":"ignored"},{"codec_type":"video",'
    '"width":100,"height":200,"avg_frame_rate":"1/3"}]}',
    '{"streams":[{"codec_type":"subtitle"},{"codec_type":"data"}]}',
    '{"streams":[null]}',
    '{"streams":"không phải list"}',
    '{"format":{"duration":"1.5"},"streams":{"codec_type":"video"}}',
    '{"format":{"duration":"1e3","size":"2e3","bit_rate":"3e3"},"streams":[]}',
]


def test_get_file_stat_key_paths():
    bad = same_result(DOTTED, '_get_file_stat_key',
                      [(str(VIDEO),), (str(AUDIO),), (str(NOTHING),), (str(TMP),),
                       ('',), (None,), ('x' * 600,), (b'bytes',), (123,),
                       (str(VIDEO) + '/*',), (VIDEO,), (TMP,), (['list'],),
                       ('C:/Windows/System32/config',), ('\\\\.\\NUL',),
                       (str(TMP / '..' / VIDEO.name),), (':',), ('nul',), (0,), (False,)]
                      + [((TMP / f'f{i}'),) for i in range(3)])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_clear_probe_cache_empties_everything():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod in (ref, rep):
        mod.clear_probe_cache()
        mod._CACHE_SIZE[('k', 1.0, 2)] = (1, 2)
        mod._CACHE_DURATION[('k', 1.0, 2)] = 3.0
        mod._CACHE_DETAILS[('k', 1.0, 2)] = {'a': 1}
        assert mod.clear_probe_cache() is None
        assert _caches(mod) == {'_CACHE_SIZE': {}, '_CACHE_DURATION': {},
                                '_CACHE_DETAILS': {}}, _caches(mod)


def test_probe_video_size_no_ffprobe():
    bad = _cmp('probe_video_size', str(VIDEO), which = None)
    assert not bad, bad
    assert _run_both('probe_video_size', str(VIDEO), which = None)[0][0] == \
        ('ok', (1080, 1920))


def test_probe_video_size_missing_file():
    for which in (None, FAKE_FFPROBE):
        bad = _cmp('probe_video_size', str(NOTHING), which = which)
        assert not bad, (which, bad)


def test_probe_video_size_parses_stdout():
    for out in SIZE_OUT:
        for code in (0, 1):
            bad = _cmp('probe_video_size', str(VIDEO),
                       results = [subprocess.CompletedProcess(['x'], code, out, 'err')])
            assert not bad, (out, code, bad)


def test_probe_video_size_survives_errors():
    for exc in (subprocess.TimeoutExpired(['x'], 30), OSError('dead'),
                RuntimeError('boom'), ValueError('nope')):
        bad = _cmp('probe_video_size', str(VIDEO), results = [exc])
        assert not bad, (exc, bad)


def test_probe_video_duration_no_ffprobe_and_missing_file():
    for which in (None, FAKE_FFPROBE):
        assert not _cmp('probe_video_duration_s', str(VIDEO), which = which)
        assert not _cmp('probe_video_duration_s', str(NOTHING), which = which)
    assert _run_both('probe_video_duration_s', str(VIDEO), which = None)[0][0] == ('ok', 0.0)


def test_probe_video_duration_values():
    for out in ['12.5', '12,5', '', '   ', '0', '-4', 'abc', None, '1e3', 'nan', 'inf',
                '999999999999999999999', '1\n2\n', '.5', '5.', '0x10', ' 7.25 ',
                '12345678901234567890.5']:
        for code in (0, 1, -1):
            bad = _cmp('probe_video_duration_s', str(VIDEO),
                       results = [subprocess.CompletedProcess(['x'], code, out, '')])
            assert not bad, (out, code, bad)


def test_probe_video_details_branches():
    for text in DETAIL_JSON:
        for code in (0, 1):
            for which in (FAKE_FFPROBE, None):
                bad = _cmp('probe_video_details', str(VIDEO), which = which,
                           results = [subprocess.CompletedProcess(['x'], code, text, '')])
                assert not bad, (text[:40], code, which, bad)


def test_probe_video_details_missing_file_short_circuits():
    for which in (FAKE_FFPROBE, None):
        bad = _cmp('probe_video_details', str(NOTHING), which = which,
                   results = [subprocess.CompletedProcess(['x'], 0, '{}', '')])
        assert not bad, (which, bad)
        got = _run_both('probe_video_details', str(NOTHING), which = which,
                        results = [subprocess.CompletedProcess(['x'], 0, '{}', '')])[0]
        assert got[0][0] == 'ok' and got[0][1]['exists'] is False, got[0]
        assert got[1] == [], ('không được gọi ffprobe cho file không tồn tại', got[1])


def test_probe_video_details_errors():
    for exc in (subprocess.TimeoutExpired(['x'], 30), OSError('boom'), ValueError('x'),
                TypeError('y'), ZeroDivisionError('z')):
        bad = _cmp('probe_video_details', str(VIDEO), results = [exc])
        assert not bad, (exc, bad)


def test_ffprobe_command_line_is_what_the_shipped_build_runs():
    '''Không chạy thật, nhưng phải dựng đúng argv: không được đổi tham số ffprobe.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    rep.clear_probe_cache()
    with fake_ffprobe() as (log, _ok):
        rep.probe_video_size(str(VIDEO))
        repo_argv = list(log)
    ref.clear_probe_cache()
    with fake_ffprobe() as (log, _ok):
        ref.probe_video_size(str(VIDEO))
        ref_argv = list(log)
    assert repo_argv == ref_argv, (repo_argv, ref_argv)
    cmd, keys, kw = repo_argv[0]
    assert cmd[0] == FAKE_FFPROBE and cmd[-1] == str(VIDEO), cmd
    assert '-select_streams' in cmd and 'v:0' in cmd and 'csv=p=0:s=x' in cmd, cmd
    assert keys == ['capture_output', 'creationflags', 'encoding', 'errors', 'text',
                    'timeout'], keys
    assert ('timeout', '30') in kw and ('encoding', "'utf-8'") in kw, kw


def test_caches_are_shared_and_reused():
    '''Lời gọi thứ hai phải ăn cache, không dựng thêm lệnh ffprobe — và cache của
    bản repo phải giống hệt bản đã phát hành (kể cả key).'''
    payload = subprocess.CompletedProcess(['x'], 0, DETAIL_JSON[0], '')
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    snapshots = []
    for mod in (rep, ref):
        mod.clear_probe_cache()
        with fake_ffprobe(results = [payload]) as (log, _ok):
            mod.probe_video_details(str(VIDEO))
            first = len(log)
            mod.probe_video_size(str(VIDEO))
            mod.probe_video_duration_s(str(VIDEO))
            second = len(log)
        snapshots.append((first, second, _caches(mod)))
    assert snapshots[0][0] == 1, snapshots[0]
    assert snapshots[0][1] == snapshots[0][0], 'cache details phải nuôi cache size/duration'
    assert repr(snapshots[0][2]) == repr(snapshots[1][2]), snapshots


def test_probe_result_shape():
    rep = repo_module(DOTTED)
    payload = subprocess.CompletedProcess(['x'], 0, DETAIL_JSON[0], '')
    rep.clear_probe_cache()
    with fake_ffprobe(results = [payload]):
        info = rep.probe_video_details(str(VIDEO))
    assert sorted(info) == sorted(
        ['name', 'path', 'exists', 'width', 'height', 'fps', 'duration_s', 'size_bytes',
         'video_codec', 'audio_codec', 'bitrate', 'format']), info
    assert (info['width'], info['height'], info['video_codec']) == (1080, 1920, 'h264'), info
    assert abs(info['fps'] - 30000 / 1001) < 1e-9, info
    assert info['duration_s'] == 12.5 and info['bitrate'] == 900000, info

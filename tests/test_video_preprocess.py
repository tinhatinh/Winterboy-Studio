# -*- coding: utf-8 -*-
'''Đối chiếu app.services.video_preprocess với bản đã phát hành.

Ba hàm quyết định CÓ bake hiệu ứng hay không và chuỗi filter ra sao đều là logic
thuần nên so trực tiếp.  ``preprocess_main_video`` chạy FFmpeg thật -> test chỉ
kiểm tra các nhánh bỏ qua (không cho phép FFmpeg được khởi động).
'''
from __future__ import annotations

import tempfile
from pathlib import Path

from _parity import describe, ref_module, repo_module, same_result

DOTTED = 'app.services.video_preprocess'

OPTION_SETS = [
    None, {}, {'brightness': 0}, {'brightness': 0.2}, {'brightness': -0.2},
    {'brightness': '0.2'}, {'brightness': 'rác'}, {'brightness': None},
    {'contrast': 1.2}, {'contrast': 0.8}, {'contrast': 'rác'},
    {'saturation': 1.2}, {'saturation': 0.5}, {'saturation': 'rác'},
    {'brightness': 0.005}, {'contrast': 1.005}, {'saturation': 0.995},
    {'brightness': 0.011}, {'brightness': ''},
    {'brightness': 0, 'contrast': 1, 'saturation': 1},
    {'bypass_noise': True}, {'bypass_noise': False}, {'bypass_colorspace': 1},
    {'bypass_zoompan': '0'}, {'bypass_gop': True}, {'bypass_ultimate': True},
    {'bypass_ultimate': True, 'brightness': 0},
    {'brightness': [], 'contrast': {}, 'saturation': ()},
    {'brightness': True}, {'contrast': True}, {'saturation': False},
    {'brightness': 1e9}, {'contrast': -1e9}, {'saturation': float('nan')},
    {'vocal_filter': True}, {'vocal_filter': 'generic'},
    {'bypass_tempo': True}, {'bypass_tempo': True, 'vocal_filter': True},
    {'bypass_ultimate': True, 'vocal_filter': True},
    {'bypass_tempo': False, 'bypass_ultimate': False, 'vocal_filter': False},
]


def _check(func):
    bad = same_result(DOTTED, func, [((v,), {}) for v in OPTION_SETS])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_needs_video_preprocess():
    _check('needs_video_preprocess')


def test_needs_audio_fx():
    _check('needs_audio_fx')


def test_audio_filter_chain():
    _check('audio_filter_chain')
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    assert rep.audio_filter_chain({'vocal_filter': 1, 'bypass_tempo': 1}) == \
        ref.audio_filter_chain({'vocal_filter': 1, 'bypass_tempo': 1})


def test_ffmpeg_lookup_matches():
    bad = same_result(DOTTED, '_ffmpeg', [((), {}), ((), {})])
    assert not bad, bad
    rep = repo_module(DOTTED)
    got = rep._ffmpeg()
    assert got is None or Path(got).name.lower().startswith('ffmpeg'), got


def test_preprocess_never_starts_ffmpeg():
    '''Mọi ca dưới đây phải thoát trước lệnh FFmpeg; ``subprocess.run`` bị chặn.'''
    rep = repo_module(DOTTED)
    tmp = Path(tempfile.mkdtemp())
    dest = tmp / 'out.mp4'
    calls = []
    real_run = rep.subprocess.run
    rep.subprocess.run = lambda *a, **k: calls.append(a)
    try:
        assert rep.preprocess_main_video(tmp / 'khong-co.mp4', dest, {'brightness': 0.5}) is None
        assert rep.preprocess_main_video(__file__, dest, {}) is None
        assert rep.preprocess_main_video(__file__, dest, {'brightness': 0}) is None
        assert rep.preprocess_main_video(__file__, dest, None) is None
        real_which = rep.shutil.which
        rep.shutil.which = lambda name: None
        try:
            assert rep.preprocess_main_video(__file__, dest, {'bypass_noise': True}) is None
        finally:
            rep.shutil.which = real_which
    finally:
        rep.subprocess.run = real_run
    assert calls == [], 'preprocess_main_video đã khởi động subprocess'
    assert not dest.exists()

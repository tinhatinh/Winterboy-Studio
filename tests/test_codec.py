# -*- coding: utf-8 -*-
'''Đối chiếu app.services.voice_engine.zerotts.codec với bản đã phát hành.

Không chạm tới model ONNX nào cả: mọi session đều là stub bằng Python thuần, nên
đo được đúng phần số học khung mã (transpose BKT->BTK, int32, thêm trục batch,
cắt theo audio_lengths, trung bình hai kênh, cập nhật KV cache) mà không nạp
weight. Đây là chỗ dễ sai nhất của bản dịch ngược — decompile ra
`codes[(None, :, :)]` và `audio[(:, :, :n)]`.
'''
from __future__ import annotations

import tempfile

import numpy as np

from _parity import ref_module, repo_module

DOTTED = 'app.services.voice_engine.zerotts.codec'


class _Out:
    '''Giống NodeArg của onnxruntime: chỉ cần .name.'''

    def __init__(self, name):
        self.name = name


class _StubSession:
    '''Session giả: ghi lại feeds của lần run cuối, trả đúng mảng dựng sẵn.'''

    def __init__(self, output_names, results):
        self._names = list(output_names)
        self._results = results
        self.feeds = None
        self.calls = 0

    def get_outputs(self):
        return [_Out(n) for n in self._names]

    def run(self, _want, feeds):
        self.calls += 1
        self.feeds = feeds
        return [self._results[n] for n in self._names]


META = {
    'codec_config': {'sample_rate': 48000, 'channels': 2,
                     'downsample_rate': 600, 'num_quantizers': 16},
    'streaming_decode': {
        'transformer_offsets': [
            {'input_name': 'past_h.0', 'output_name': 'present_h.0',
             'shape': [1, 16, 0, 64]},
            {'input_name': 'past_h.1', 'output_name': 'present_h.1',
             'shape': [1, 16, 0, 64]},
        ],
        'attention_caches': [
            {'offset_input_name': 'off.0', 'offset_output_name': 'off_out.0',
             'offset_shape': [1],
             'cached_keys_input_name': 'k.0', 'cached_keys_output_name': 'k_out.0',
             'cached_values_input_name': 'v.0', 'cached_values_output_name': 'v_out.0',
             'cached_positions_input_name': 'p.0',
             'cached_positions_output_name': 'p_out.0',
             'cache_shape': [1, 8, 0, 64], 'positions_shape': [1, 8, 0]},
        ],
    },
}


def _same(label, a, b):
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        assert type(a) is type(b), f'{label}: kiểu {type(a)} != {type(b)}'
        assert a.dtype == b.dtype, f'{label}: dtype {a.dtype} != {b.dtype}'
        assert a.shape == b.shape, f'{label}: shape {a.shape} != {b.shape}'
        assert np.array_equal(a, b), f'{label}: {a!r} != {b!r}'
        return
    assert a == b, f'{label}: {a!r} != {b!r}'


def _decoder(mod, audio, lengths):
    d = object.__new__(mod.MossCodecDecoder)
    d._decode_full_sess = _StubSession(['audio', 'audio_lengths'],
                                       {'audio': audio, 'audio_lengths': lengths})
    return d


STREAM_OUTS = ['audio', 'audio_lengths', 'present_h.0', 'present_h.1',
               'off_out.0', 'k_out.0', 'v_out.0', 'p_out.0']


def _streaming(mod, results):
    codec = object.__new__(mod.MossCodecDecoder)
    codec._meta = META
    codec._decode_step_sess = _StubSession(STREAM_OUTS, results)
    return mod.MossStreamingDecoder(codec)


def _stream_results(n_frames):
    """Kết quả run() dựng sẵn cho luồng streaming, với n_frames khung audio."""
    return {
        'audio': np.zeros((1, 2, n_frames + 2), dtype=np.float32),
        'audio_lengths': np.array([[n_frames]], dtype=np.int32),
        'present_h.0': np.full((1, 16, n_frames, 64), 1, dtype=np.int32),
        'present_h.1': np.full((1, 16, n_frames, 64), 2, dtype=np.int32),
        'off_out.0': np.array([n_frames], dtype=np.int32),
        'k_out.0': np.zeros((1, 8, n_frames, 64), dtype=np.float32),
        'v_out.0': np.zeros((1, 8, n_frames, 64), dtype=np.float32),
        'p_out.0': np.full((1, 8, n_frames), n_frames, dtype=np.int32),
    }


def test_decode_transposes_and_mixes():
    """(B,K,T) -> transpose (B,T,K) int32, lengths = T, mono = trung bình kênh."""
    codes = np.arange(2 * 3 * 4, dtype=np.int64).reshape(2, 3, 4)
    audio = np.zeros((2, 2, 5), dtype=np.float64)      # (B, kênh, mẫu)
    audio[:, 0, :] = 2.0
    audio[:, 1, :] = 4.0
    lengths = np.array([[5], [5]], dtype=np.int32)

    got = _decoder(repo_module(DOTTED), audio, lengths).decode(codes)
    want = _decoder(ref_module(DOTTED), audio, lengths).decode(codes)
    _same('decode()', got, want)
    assert got.shape == (2, 5) and got.dtype == np.float32, (got.shape, got.dtype)
    _same('decode giá trị', got, np.full((2, 5), 3.0, dtype=np.float32))


def test_decode_adds_batch_axis_for_2d():
    codes = np.arange(6, dtype=np.int64).reshape(2, 3)          # (K, T) không batch
    audio = np.zeros((1, 2, 3), dtype=np.float32)
    lengths = np.array([[3]], dtype=np.int32)
    feeds = []

    def build(mod):
        d = _decoder(mod, audio, lengths)
        out = d.decode(codes)
        feeds.append(d._decode_full_sess.feeds)
        return out

    a = build(repo_module(DOTTED))
    b = build(ref_module(DOTTED))
    _same('decode 2D', a, b)
    fa, fb = feeds
    _same('keys', sorted(fa), sorted(fb))
    _same('audio_codes', fa['audio_codes'], fb['audio_codes'])
    _same('audio_code_lengths', fa['audio_code_lengths'], fb['audio_code_lengths'])
    assert list(sorted(fa)) == ['audio_code_lengths', 'audio_codes'], sorted(fa)
    assert fa['audio_codes'].shape == (1, 3, 2), fa['audio_codes'].shape   # (B,T,K)
    assert fa['audio_codes'].dtype == np.int32, fa['audio_codes'].dtype
    assert fa['audio_code_lengths'].tolist() == [3], fa['audio_code_lengths']
    # chuyển vị thật sự: hàng của BTK chính là cột của BKT
    _same('nội dung transpose', fa['audio_codes'][0],
          np.array([[0, 3], [1, 4], [2, 5]], dtype=np.int32))


def test_decode_trims_to_reported_length():
    """audio dài hơn audio_lengths -> cắt [:, :, :n] trước khi trung bình kênh."""
    codes = np.zeros((1, 2, 3), dtype=np.int32)
    audio = np.zeros((1, 2, 9), dtype=np.float32)
    audio[:, :, 3:] = 100.0                      # phần dư phải bị bỏ
    lengths = np.array([[3]], dtype=np.int32)
    got = _decoder(repo_module(DOTTED), audio, lengths).decode(codes)
    want = _decoder(ref_module(DOTTED), audio, lengths).decode(codes)
    _same('decode cắt ngắn', got, want)
    _same('decode cắt ngắn giá trị', got, np.zeros((1, 3), dtype=np.float32))


def test_streaming_state_bootstrap():
    def build(mod):
        s = _streaming(mod, _stream_results(2))
        return (list(s._output_names),
                {k: (tuple(v.shape), str(v.dtype)) for k, v in s._state.items()})

    a, b = build(repo_module(DOTTED)), build(ref_module(DOTTED))
    _same('output names', a[0], b[0])
    _same('state', a[1], b[1])
    assert a[0] == STREAM_OUTS, a[0]
    # buffer cache khởi tạo rỗng (trục độ dài = 0), riêng hàng đợi vị trí đầy -1
    state = a[1]
    assert state['p.0'] == ((1, 8, 0), 'int32'), state['p.0']
    assert state['k.0'] == ((1, 8, 0, 64), 'float32'), state['k.0']
    assert state['off.0'] == ((1,), 'int32'), state['off.0']
    st = _streaming(repo_module(DOTTED), _stream_results(2))._state
    assert st['p.0'].shape == (1, 8, 0) and (st['p.0'] == -1).all()


def test_streaming_chunk_updates_state():
    codes = np.arange(2 * 3, dtype=np.int64).reshape(2, 3)      # (K=2, n=3)

    def run(mod):
        s = _streaming(mod, _stream_results(3))
        out = s.decode_chunk(codes)
        feeds = s._session.feeds
        return (out, np.asarray(feeds['audio_codes']),
                np.asarray(feeds['audio_code_lengths']), sorted(feeds),
                {k: tuple(v.shape) for k, v in s._state.items()})

    a, b = run(repo_module(DOTTED)), run(ref_module(DOTTED))
    for i, label in enumerate(['chunk', 'codes', 'lengths', 'feeds', 'state']):
        _same(label, a[i], b[i])
    assert a[2].tolist() == [3], a[2]
    assert 'audio_codes' in a[3] and 'past_h.0' in a[3], a[3]
    assert a[4]['past_h.0'] == (1, 16, 3, 64), a[4]           # KV đã nhận output mới
    assert a[4]['p.0'] == (1, 8, 3), a[4]


def test_streaming_close_resets_state():
    codes = np.arange(6, dtype=np.int64).reshape(2, 3)

    def snap(mod):
        s = _streaming(mod, _stream_results(3))
        s.decode_chunk(codes)
        after = {k: v.shape for k, v in s._state.items()}
        s.close()
        return after, {k: v.shape for k, v in s._state.items()}

    a, b = snap(repo_module(DOTTED)), snap(ref_module(DOTTED))
    _same('close()', a, b)
    assert a[0]['k.0'] == (1, 8, 3, 64), a[0]   # sau khi decode: cache 3 khung
    assert a[1]['k.0'] == (1, 8, 0, 64), a[1]   # close(): về buffer rỗng


def test_two_chunks_are_sequential():
    """Hai liên tiếp: chunk 2 phải mang state của chunk 1 sang feeds."""
    codes = np.arange(6, dtype=np.int64).reshape(2, 3)

    def twice(mod):
        s = _streaming(mod, _stream_results(3))
        first = s.decode_chunk(codes)
        second = s.decode_chunk(codes)
        seen = np.asarray(s._session.feeds['past_h.0']).shape
        return first.shape, second.shape, seen, s._session.calls

    a, b = twice(repo_module(DOTTED)), twice(ref_module(DOTTED))
    _same('hai chunk', a, b)
    assert a[2] == (1, 16, 3, 64) and a[3] == 2, a


def test_missing_meta_directory_raises():
    """Thư mục không có codec_browser_onnx_meta.json -> FileNotFoundError cả hai bên."""
    empty = tempfile.mkdtemp()
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for mod, tag in ((rep, 'repo'), (ref, 'ref')):
        try:
            mod.MossCodecDecoder(empty)
        except FileNotFoundError as exc:
            assert 'codec_browser_onnx_meta.json' in str(exc), (tag, str(exc))
            continue
        raise AssertionError(f'{tag}: MossCodecDecoder không nổ FileNotFoundError')

# Source Generated with Decompyle++
# File: codec.pyc (Python 3.12)

'''onnxruntime-only MOSS-Audio-Tokenizer-Nano **decoder** — codes -> waveform.

Vendored, not downloaded. The decoder graphs ship inside the ZeroTTS weights
repo (``onnx/codec/``) so a ZeroTTS install has no runtime dependency on any
third-party model repo staying up or unchanged.

Decoder only. The upstream export also has an encoder graph (waveform -> codes),
used solely to turn reference audio into voice latents. That is voice cloning,
which this release does not do (see zerotts.voices), so the encoder is neither
shipped nor wrapped — it would be ~45MB of weights nothing here can call.

Conventions worth knowing before touching this:
  * native sample rate 48 kHz; the codec is stereo internally, the public
    interface is mono (decode averages the two channels).
  * this export uses (batch, T, K) — TIME-major, codebook-LAST — for
    ``audio_codes``. ZeroTTS\'s AR loop produces (B, K, T), so decode transposes.
  * every integer tensor here is **int32**, not int64. This is verified against
    the graphs; do not "fix" it to int64 out of PyTorch habit.

Credit: MOSS-Audio-Tokenizer-Nano by the OpenMOSS team, Apache-2.0. See
https://github.com/OpenMOSS/MOSS-Audio-Tokenizer and the NOTICE file.
'''
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

class MossCodecDecoder:
    '''Args:
        codec_dir: directory holding the decoder graphs and
            ``codec_browser_onnx_meta.json``.
        providers: onnxruntime execution providers.
        intra_op_num_threads: per-session thread count.
    '''
    
    def __init__(self = None, codec_dir = None, providers = None, intra_op_num_threads = (None, 4)):
        pass
    # WARNING: Decompyle incomplete

    
    def decode(self = None, codes_bkt = None):
        '''(B, K, T) int codes -> (B, T_audio) float32 mono at sample_rate.'''
        codes = np.asarray(codes_bkt)
        if codes.ndim == 2:
            codes = codes[(None, :, :)]
        codes_btk = codes.transpose(0, 2, 1).astype(np.int32)
        lengths = np.array([
            codes_btk.shape[1]], dtype = np.int32)
        (audio, audio_lengths) = self._decode_full_sess.run(None, {
            'audio_codes': codes_btk,
            'audio_code_lengths': lengths })
        n = int(audio_lengths.reshape(-1)[0])
        return audio[(:, :, :n)].mean(axis = 1).astype(np.float32)

    
    def streaming_decoder(self = None):
        '''Open a stateful streaming decoder (keeps the causal decoder KV cache
        across chunks). Call decode_chunk per chunk, then close.'''
        return MossStreamingDecoder(self)



class MossStreamingDecoder:
    '''KV-cached streaming decode over decode_step.onnx, driven by the state
    layout ``codec_browser_onnx_meta.json``\'s "streaming_decode" section
    describes: per-decoder transformer offsets plus per-layer attention caches
    (key/value/position ring buffers). Use via
    ``MossCodecDecoder.streaming_decoder()``.'''
    
    def __init__(self = None, codec = None):
        self._codec = codec
        self._session = codec._decode_step_sess
        streaming = codec._meta.get('streaming_decode', { })
        self._transformer_specs = list(streaming.get('transformer_offsets', []))
        self._attention_specs = list(streaming.get('attention_caches', []))
    # WARNING: Decompyle incomplete

    
    def _reset_state(self = None):
        self._state = { }
        for spec in self._transformer_specs:
            self._state[str(spec['input_name'])] = np.zeros(tuple(spec['shape']), dtype = np.int32)
        for spec in self._attention_specs:
            self._state[str(spec['offset_input_name'])] = np.zeros(tuple(spec['offset_shape']), dtype = np.int32)
            self._state[str(spec['cached_keys_input_name'])] = np.zeros(tuple(spec['cache_shape']), dtype = np.float32)
            self._state[str(spec['cached_values_input_name'])] = np.zeros(tuple(spec['cache_shape']), dtype = np.float32)
            self._state[str(spec['cached_positions_input_name'])] = np.full(tuple(spec['positions_shape']), -1, dtype = np.int32)

    
    def decode_chunk(self = None, codes_bkt = None):
        '''(1, K, n) int codes -> (1, chunk_samples) float32 mono.'''
        codes = np.asarray(codes_bkt)
        if codes.ndim == 2:
            codes = codes[(None, :, :)]
        codes_btk = codes.transpose(0, 2, 1).astype(np.int32)
    # WARNING: Decompyle incomplete

    
    def close(self = None):
        self._reset_state()



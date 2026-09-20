# Source Generated with Decompyle++
# File: synthesizer.pyc (Python 3.12)

"""ZeroTTS inference — onnxruntime + numpy, no PyTorch anywhere.

Three ONNX graphs and a two-level autoregressive loop:

  1. ``text_encoder.onnx`` — the text ids become encoder states, once per
     utterance. Also returns the ``<soa>`` control embedding.
  2. ``prefix_step.onnx`` — advances the global (time-axis) transformer. Called
     once to build the ``[voice | soa]`` prefix from an empty KV cache, then once
     per generated frame with T=1. Same graph, same session, different shapes.
  3. ``local_frame_decode.onnx`` — decodes one whole frame: the control channel
     (continue vs. stop) plus all K codebooks, with the embeddings, CFG mixing,
     and sampling fused into the graph.

So two onnxruntime calls per audio frame. Frames come out at 12.5 Hz and are
decoded to a waveform by the vendored MOSS codec decoder (see zerotts.codec).

Speaker conditioning
────────────────────
A voice is ``n_voice_queries`` latents prepended to the sequence, and that is
all of it: no reference transcript, no in-context audio prompt, no teacher-forced
frames. The latents come from a precomputed voice pack (zerotts.voices) or,
with no voice at all, from the model's learned unconditional prefix
(``null_voice_emb.npy``) — which is also the branch CFG guides away from.

This release cannot *create* a voice from audio; the voice encoder is not part
of it. See zerotts.voices.

Sampling
────────
Temperature / top-k / top-p and a per-codebook repetition penalty all happen
*inside* ``local_frame_decode.onnx``, not out here. This runtime feeds it fresh
random draws and a ``seen_mask`` — a dense (1, K, codebook_size) bool array
standing in for a per-codebook history set, since a graph cannot carry
variable-length state between calls — and mutates that mask in place after each
sampled frame.
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
from  import hub
from  import voices as _voices
from audio import save_wav
from codec import MossCodecDecoder
from tokenizer import load_tokenizer
DEFAULT_MAX_FRAMES = 1500

class ZeroTTS:
    '''ZeroTTS synthesizer.

    Prefer :meth:`from_pretrained`. The constructor takes an already-resolved
    local directory.
    '''
    
    def __init__(self, model_dir = None, providers = None, intra_op_num_threads = None, codec_intra_op_num_threads = (None, 4, None, True), warmup = ('model_dir', 'str | Path', 'providers', 'list[str] | None', 'intra_op_num_threads', 'int', 'codec_intra_op_num_threads', 'int | None', 'warmup', 'bool')):
        pass
    # WARNING: Decompyle incomplete

    from_pretrained = (lambda cls = None, model_id = None, revision = classmethod, cache_dir = (hub.DEFAULT_REPO_ID, None, None, False), local_files_only = ('model_id', 'str | Path', 'revision', 'str | None', 'cache_dir', 'str | None', 'local_files_only', 'bool', 'return', 'ZeroTTS'): model_dir = hub.resolve_model_dir(model_id, revision = revision, cache_dir = cache_dir, local_files_only = local_files_only)# WARNING: Decompyle incomplete
)()
    
    def warmup(self = None):
        """Push one dummy request through every session on the hot path, so lazy
        allocator and thread-pool setup lands here instead of skewing the first
        real call's time-to-first-audio. The text encoder is included because it
        is on the critical path for TTFA even though it runs once per utterance."""
        text_ids = np.zeros((1, 1), dtype = np.int64)
        txt_lengths = np.ones(1, dtype = np.int64)
        (h, packed_kv, full_valid, cross_kv, text_valid) = self._prefix_step_init(text_ids, txt_lengths, self.null_voice_emb)
        seen = np.zeros((1, self.num_codebooks, self.codebook_size), dtype = bool)
        (_ctrl, codes) = self._local_decode_frame(h, forbid_eoa = True, text_temperature = 1, text_topk = 50, audio_temperature = 0.8, audio_topk = 25, audio_topp = 0.95, audio_repetition_penalty = 1.2, seen_mask = seen, cfg_scale = 1)
        self._prefix_step_frame(codes[(:, None, :)], np.array([
            0], dtype = np.int64), packed_kv, full_valid, n_voice = self.null_voice_emb.shape[1], cross_kv = cross_kv, text_valid = text_valid)

    
    def list_voices(self = None):
        '''Names of the voice packs bundled with these weights.'''
        return _voices.list_voices(self.voices_root)

    
    def load_voice(self = None, name = None):
        return _voices.load_voice(self.voices_root, name, expect_queries = self.n_voice_queries)

    
    def resolve_voice(self = None, voice = None):
        '''Latents to condition on, from a name, a Voice, a raw array, or None.

        None means the learned unconditional prefix — the model then picks a
        voice itself, and it will not be stable across calls.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _prefix_step_init(self = None, text_ids = None, txt_lengths = None, voice_emb = ('text_ids', 'np.ndarray', 'txt_lengths', 'np.ndarray', 'voice_emb', 'np.ndarray')):
        '''Cold start: build the [voice | soa] prefix from an empty KV cache.

        ``voice_emb`` (B, V, d) sets the batch — B=1 normally, B=2 for CFG
        ([conditional; unconditional]). text_ids is broadcast to match, since
        only the voice differs between guidance branches.

        Returns (h (B, d) predicting frame 0, packed_kv, full_valid,
        cross_kv, text_valid).
        '''
        B = voice_emb.shape[0]
        V = voice_emb.shape[1]
        L = text_ids.shape[1]
        if text_ids.shape[0] != B:
            text_ids = np.broadcast_to(text_ids, (B, L))
            txt_lengths = np.broadcast_to(txt_lengths, (B,))
        (_text_states, text_valid, soa_embed, cross_kv) = self.text_encoder_sess.run(None, {
            'text_ids': np.ascontiguousarray(text_ids),
            'txt_lengths': np.ascontiguousarray(txt_lengths) })
        external_embed = np.concatenate([
            voice_emb.astype(np.float32),
            soa_embed.astype(np.float32)], axis = 1)
        T = V + 1
        (hidden, packed_kv, full_valid) = self.prefix_step_sess.run(None, {
            'external_embed': external_embed,
            'use_external_embed': np.ones((B, T), dtype = bool),
            'frame_codes': np.zeros((B, T, self.num_codebooks), dtype = np.int64),
            'new_pos': np.tile(np.arange(T, dtype = np.int64), (B, 1)),
            'new_valid': np.ones((B, T), dtype = bool),
            'packed_kv': np.zeros((self.n_layers, 2, B, self.n_heads, 0, self.d_head), dtype = np.float32),
            'new_bidirectional': np.concatenate([
                np.ones((B, V), dtype = bool),
                np.zeros((B, 1), dtype = bool)], axis = 1),
            'past_valid': np.zeros((B, 0), dtype = bool),
            'cross_kv': cross_kv,
            'text_valid': text_valid })
        return (hidden[(:, -1, :)], packed_kv, full_valid, cross_kv, text_valid)

    
    def _prefix_step_frame(self, frame_codes, frame_index, packed_kv = None, full_valid = None, n_voice = None, cross_kv = (0, None, None), text_valid = ('frame_codes', 'np.ndarray', 'frame_index', 'np.ndarray', 'packed_kv', 'np.ndarray', 'full_valid', 'np.ndarray', 'n_voice', 'int')):
        '''Advance the global transformer by one frame (T=1, S_past = cache len).

        ``n_voice`` shifts the position id: the voice block occupies logical
        positions 0..V-1, so audio frame t sits at V + 1 + t. Getting this wrong
        does not raise — it silently offsets every RoPE position.

        The frame is tiled across the guidance batch: one sampled frame is the
        history BOTH branches continue from.
        '''
        B = packed_kv.shape[2]
        if frame_codes.shape[0] != B:
            frame_codes = np.broadcast_to(frame_codes, (B,) + frame_codes.shape[1:])
        new_pos = (n_voice + 1 + frame_index).astype(np.int64)
        new_pos = np.tile(new_pos.reshape(1, 1), (B, 1))
        (hidden, new_packed_kv, new_full_valid) = self.prefix_step_sess.run(None, {
            'external_embed': np.zeros((B, 1, self.d_model), dtype = np.float32),
            'use_external_embed': np.zeros((B, 1), dtype = bool),
            'frame_codes': np.ascontiguousarray(frame_codes),
            'new_pos': new_pos,
            'new_valid': np.ones((B, 1), dtype = bool),
            'packed_kv': packed_kv,
            'past_valid': full_valid,
            'cross_kv': cross_kv,
            'new_bidirectional': np.zeros((B, 1), dtype = bool),
            'text_valid': text_valid })
        return (hidden[(:, -1, :)], new_packed_kv, new_full_valid)

    
    def _local_decode_frame(self, h, forbid_eoa, text_temperature, text_topk, audio_temperature, audio_topk, audio_topp, audio_repetition_penalty, seen_mask, cfg_scale = (1,)):
        """Decode one frame from the global hidden — one call to the fused graph.

        h is (1, d) with no guidance, (2, d) = [conditional; unconditional] with
        it; the graph samples once either way, so seen_mask, the random draws,
        and the outputs all stay batch 1.

        Returns (ctrl_id, codes (1, K)). ``codes`` comes back even when the
        control channel said <eoa>: those codes were sampled from the same global
        hidden and are the model's own trailing frame, which the caller may keep.
        """
        K = self.num_codebooks
        (is_eoa, codes) = self.local_frame_decode_sess.run(None, {
            'global_hidden': h.astype(np.float32, copy = False),
            'forbid_eoa': np.array([
                bool(forbid_eoa)], dtype = bool),
            'text_temperature': np.array([
                text_temperature], dtype = np.float32),
            'text_topk': np.array([
                text_topk if text_topk and text_topk > 0 else self.codebook_size], dtype = np.int64),
            'audio_temperature': np.array([
                audio_temperature], dtype = np.float32),
            'audio_topk': np.array([
                audio_topk if audio_topk and audio_topk > 0 else self.codebook_size], dtype = np.int64),
            'audio_topp': np.array([
                audio_topp], dtype = np.float32),
            'audio_repetition_penalty': np.array([
                audio_repetition_penalty], dtype = np.float32),
            'seen_mask': seen_mask,
            'ctrl_random_u': np.random.random(1).astype(np.float32),
            'audio_random_u': np.random.random((1, K)).astype(np.float32),
            'cfg_scale': np.array([
                cfg_scale], dtype = np.float32) })
        codes = codes.astype(np.int64)
        for c in range(K):
            seen_mask[(0, c, codes[(0, c)])] = True
        if bool(is_eoa.reshape(-1)[0]):
            return (self.eoa_id, codes)
        return (None.slot_id, codes)

    
    def _generate_frames(self, text, min_frames, max_frames, voice_emb, cfg_scale, text_temperature, text_topk, audio_temperature, audio_topk, audio_topp, audio_repetition_penalty, eoa_extra_frames, timing = (None, 1, 1, 50, 0.8, 25, 0.95, 1.2, 1, None)):
        """Generator yielding one (1, num_codebooks) int64 frame at a time.

        ``eoa_extra_frames``: how many frames sampled at and after <eoa> to KEEP.
        The control channel and the audio channels are decoded from the same
        global hidden, so when <eoa> fires that frame's codes already exist — and
        they are the model's own trailing silence. Discarding them cuts the
        waveform the instant the last phone ends, clipping its release and
        butting it against whatever comes next. <eoa> is forbidden for those tail
        frames so they are real audio rather than an immediate re-stop.
        """
        pass
    # WARNING: Decompyle incomplete

    
    def synthesize(self, text, voice, cfg_scale, text_temperature, text_topk, audio_temperature, audio_topk, audio_topp, audio_repetition_penalty = None, min_frames = None, max_frames = None, eoa_extra_frames = (None, 1, 1, 50, 0.8, 25, 0.95, 1.2, 4, DEFAULT_MAX_FRAMES, 1, None), timing = ('text', 'str', 'cfg_scale', 'float', 'text_temperature', 'float', 'text_topk', 'int', 'audio_temperature', 'float', 'audio_topk', 'int', 'audio_topp', 'float', 'audio_repetition_penalty', 'float', 'min_frames', 'int', 'max_frames', 'int', 'eoa_extra_frames', 'int', 'timing', 'dict | None', 'return', 'np.ndarray')):
        """Synthesize ``text``. Returns (1, T) float32 at ``self.sample_rate``.

        voice: a voice name, a :class:`~zerotts.voices.Voice`, a latent array, or
            None for the model's unconditional voice.
        cfg_scale: >1 doubles the per-frame cost and pushes the output toward the
            voice's identity. 1.0 (default) computes no unconditional branch.
        audio_repetition_penalty: 1.2 is the benchmarked default; 1.0 measurably
            raises WER and leaves more dead air.
        """
        voice_emb = self.resolve_voice(voice)
        frames = list(self._generate_frames(text, min_frames, max_frames, voice_emb = voice_emb, cfg_scale = cfg_scale, text_temperature = text_temperature, text_topk = text_topk, audio_temperature = audio_temperature, audio_topk = audio_topk, audio_topp = audio_topp, audio_repetition_penalty = audio_repetition_penalty, eoa_extra_frames = eoa_extra_frames, timing = timing))
        if not frames:
            return np.zeros((1, 0), dtype = np.float32)
        codes_out = None.stack(frames, axis = 1)[0].transpose(1, 0)
        return self.codec.decode(codes_out[(None, :, :)])

    
    def synthesize_stream(self, text, voice, cfg_scale, text_temperature, text_topk, audio_temperature, audio_topk, audio_topp, audio_repetition_penalty, min_frames = None, max_frames = None, eoa_extra_frames = None, first_chunk_frames = (None, 1, 1, 50, 0.8, 25, 0.95, 1.2, 4, DEFAULT_MAX_FRAMES, 1, 1, 16), max_chunk_frames = ('text', 'str', 'cfg_scale', 'float', 'text_temperature', 'float', 'text_topk', 'int', 'audio_temperature', 'float', 'audio_topk', 'int', 'audio_topp', 'float', 'audio_repetition_penalty', 'float', 'min_frames', 'int', 'max_frames', 'int', 'eoa_extra_frames', 'int', 'first_chunk_frames', 'int', 'max_chunk_frames', 'int')):
        '''Streaming synthesis — yields (1, chunk_samples) float32 chunks.

        The chunk schedule ramps: the first chunk is ``first_chunk_frames`` (low
        time-to-first-audio), then each chunk doubles up to ``max_chunk_frames``,
        so the per-call codec overhead — the main CPU cost of streaming — is
        amortized once a playback buffer exists.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def save_audio(self = None, audio = None, path = None):
        save_wav(audio, path, self.sample_rate)



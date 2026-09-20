# Source Generated with Decompyle++
# File: cli.pyc (Python 3.12)

'''Command-line interface: ``zerotts say`` / ``zerotts voices`` / ``zerotts bench``.'''
from __future__ import annotations
import argparse
import sys
import time
import numpy as np
from  import hub
from audio import concat_with_silence
from chunking import chunk_text, clean_segment_punctuation, normalize_punctuation
from synthesizer import ZeroTTS
from text_norm import normalize_vi_text

def _add_model_args(p = None):
    p.add_argument('--model', default = hub.DEFAULT_REPO_ID, help = 'HF repo id or local model directory.')
    p.add_argument('--revision', default = None, help = 'HF revision to pin.')
    p.add_argument('--threads', type = int, default = 4, help = 'onnxruntime intra-op threads.')


def _add_sampling_args(p = None):
    p.add_argument('--cfg_scale', type = float, default = 1, help = '>1 guides toward the voice, at 2x the per-frame cost.')
    p.add_argument('--audio_temperature', type = float, default = 0.8)
    p.add_argument('--audio_topk', type = int, default = 25)
    p.add_argument('--audio_topp', type = float, default = 0.95)
    p.add_argument('--audio_repetition_penalty', type = float, default = 1.2, help = '1.2 is the benchmarked default; 1.0 raises WER.')
    p.add_argument('--seed', type = int, default = None, help = 'Seed the sampler.')


def _sampling_kwargs(a = None):
    return {
        'cfg_scale': a.cfg_scale,
        'audio_temperature': a.audio_temperature,
        'audio_topk': a.audio_topk,
        'audio_topp': a.audio_topp,
        'audio_repetition_penalty': a.audio_repetition_penalty }


def cmd_say(a = None):
    pass
# WARNING: Decompyle incomplete


def cmd_voices(a = None):
    tts = ZeroTTS.from_pretrained(a.model, revision = a.revision, warmup = False)
    names = tts.list_voices()
    if not names:
        print('No voice packs in this model directory.')
        print('This build cannot create voices from audio — see the README (voice cloning).')
        return 1
    for name in names:
        v = tts.load_voice(name)
        desc = f'''  {v.description}''' if v.description else ''
        print(f'''{name:20s} {v.language:4s} {v.n_voice_queries} queries{desc}''')
    return 0


def cmd_bench(a = None):
    pass
# WARNING: Decompyle incomplete


def main(argv = None):
    p = argparse.ArgumentParser(prog = 'zerotts', description = 'ZeroTTS command line.')
    sub = p.add_subparsers(dest = 'cmd', required = True)
    say = sub.add_parser('say', help = 'Synthesize text to a wav file.')
    say.add_argument('text', help = "Text to speak, or '-' to read stdin.")
    say.add_argument('-o', '--out', default = 'out.wav')
    say.add_argument('-v', '--voice', default = None, help = "Voice name. Omit for the model's unconditional voice.")
    say.add_argument('--chunk', action = 'store_true', help = 'Split long text into segments and join the audio.')
    say.add_argument('--max_chunk_sec', type = float, default = 15)
    say.add_argument('--gap_sec', type = float, default = 0.15, help = 'Silence inserted between chunks.')
    say.add_argument('--no_text_norm', action = 'store_true', help = 'Skip Vietnamese normalization of dates/times/numbers. Use for non-Vietnamese text — the expansions are Vietnamese words.')
    _add_model_args(say)
    _add_sampling_args(say)
    say.set_defaults(func = cmd_say)
    voices = sub.add_parser('voices', help = 'List available voices.')
    _add_model_args(voices)
    voices.set_defaults(func = cmd_voices)
    bench = sub.add_parser('bench', help = 'Measure realtime factor and TTFF.')
    bench.add_argument('--text', default = 'Xin chào, đây là một bài kiểm tra tốc độ tổng hợp giọng nói.')
    bench.add_argument('-v', '--voice', default = None)
    bench.add_argument('--runs', type = int, default = 3)
    _add_model_args(bench)
    _add_sampling_args(bench)
    bench.set_defaults(func = cmd_bench)
    a = p.parse_args(argv)
    return a.func(a)

if __name__ == '__main__':
    raise SystemExit(main())

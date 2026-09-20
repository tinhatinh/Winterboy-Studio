# Source Generated with Decompyle++
# File: hub.pyc (Python 3.12)

'''Resolving a ZeroTTS model directory — local path or Hugging Face repo.

Published layout (hf.co/zeroweight-ai/ZeroTTS):

    config.json
    tokenizer.json
    null_voice_emb.npy
    onnx/{text_encoder,prefix_step,local_frame_decode}.onnx
    onnx/codec/...            # vendored MOSS decoder, Apache-2.0
    voices/index.json
    voices/<name>/{voice.npz,voice.bin,preview.wav,meta.json}

``voice.bin`` exists only for the browser demo (raw f32, no zip parser needed),
so the Python download skips it — it is a byte-for-byte duplicate of what
``voice.npz`` already carries.
'''
from __future__ import annotations
import json
import os
from pathlib import Path
DEFAULT_REPO_ID = 'zeroweight-ai/ZeroTTS'
DEFAULT_REVISION = '8a0c3c29f6f047011f5cae02d0b14475a690be86'
_ALLOW_PATTERNS = [
    'config.json',
    'tokenizer.json',
    'null_voice_emb.npy',
    'silence_frame.npy',
    'onnx/*',
    'onnx/codec/*',
    'voices/index.json',
    'voices/*/voice.npz',
    'voices/*/meta.json',
    'voices/*/preview.wav']
REQUIRED_FILES = ('config.json', 'null_voice_emb.npy', 'onnx/text_encoder.onnx', 'onnx/prefix_step.onnx', 'onnx/local_frame_decode.onnx')

def resolve_model_dir(model_id = None, revision = None, cache_dir = None, local_files_only = (DEFAULT_REPO_ID, None, None, False)):
    '''A local directory containing the model, downloading it if needed.

    ``model_id`` is either an existing local directory (used as-is, nothing is
    fetched) or a Hugging Face repo id.

    ``revision`` defaults to DEFAULT_REVISION — but only for DEFAULT_REPO_ID.
    Any other repo id resolves its own default branch, because this pin is a
    commit in one specific repository and forcing it on a fork or a mirror would
    fail to resolve rather than fall back.
    '''
    pass
# WARNING: Decompyle incomplete


def load_config(model_dir = None):
    '''Read and validate ``config.json``, checking the graphs are actually there.'''
    model_dir = Path(model_dir)
    config_path = model_dir / 'config.json'
    if not config_path.exists():
        raise FileNotFoundError(f'''{model_dir} has no config.json — it is not a ZeroTTS model directory.''')
# WARNING: Decompyle incomplete


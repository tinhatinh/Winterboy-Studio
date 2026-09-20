# Source Generated with Decompyle++
# File: voices.pyc (Python 3.12)

'''Precomputed voice packs.

A "voice" in ZeroTTS is a small array of speaker latents — shape
``(1, n_voice_queries, d_model)`` float32 — that gets prepended to the sequence.
That array is the *entire* speaker conditioning; there is no reference audio, no
transcript, and no prompt frames involved at generation time.

Those latents are produced by a voice encoder that reads a reference clip. **The
encoder is not part of this release**, so this package cannot create a voice
from a wav — it can only load ones that already exist. See the README, or
zeroweight.ai, for how to obtain latents for your own speaker.

That boundary is narrower than it sounds: a voice pack is just a .npz, so
latents obtained elsewhere drop into ``voices/<name>/voice.npz`` and work with
no code change.

Layout of a voice pack directory:

    voices/
      index.json                 # optional manifest: name, display_name, tags...
      <name>/
        voice.npz                # required: {n_voice_queries: int64, voice_emb: (1,Q,D) f32}
        voice.bin                # optional: raw f32 of voice_emb, for the JS demo
        preview.wav              # optional
        meta.json                # optional: display_name, gender, tags, description...
'''
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np
Voice = <NODE:12>()

def _voice_dirs(voices_root = None):
    if not voices_root.is_dir():
        return []
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(voices_root.iterdir()())


def list_voices(voices_root = None):
    '''Voice names available under ``voices_root``, sorted.'''
    pass
# WARNING: Decompyle incomplete


def load_voice(voices_root = None, name = None, expect_queries = None):
    """Load one voice pack by name.

    ``expect_queries`` is the model's ``n_voice_queries``. A mismatch is fatal
    and says so: latents built for a different model would still be the right
    dtype and rank, so they would feed the graph cleanly and produce confident
    nonsense.
    """
    root = Path(voices_root)
    vdir = root / name
    npz = vdir / 'voice.npz'
    if not npz.exists():
        available = list_voices(root)
        if not available:
            available
        raise FileNotFoundError(f'''no voice {name!r} in {root} (available: {'none'})''')
    data = np.load(npz)
    emb = np.asarray(data['voice_emb'], dtype = np.float32)
    if emb.ndim == 2:
        emb = emb[(None, :, :)]
    stored_q = int(data['n_voice_queries']) if 'n_voice_queries' in data else int(emb.shape[1])
    if stored_q != emb.shape[1]:
        raise ValueError(f'''voice {name!r} is inconsistent: n_voice_queries={stored_q} but voice_emb has {emb.shape[1]} queries.''')
# WARNING: Decompyle incomplete


def load_index(voices_root = None):
    '''The ``index.json`` manifest, or a minimal one synthesized from the dirs.'''
    root = Path(voices_root)
    index_path = root / 'index.json'
    if index_path.exists():
        return json.loads(index_path.read_text())
# WARNING: Decompyle incomplete


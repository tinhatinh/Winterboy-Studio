# Source Generated with Decompyle++
# File: tokenizer.pyc (Python 3.12)

"""BPE text encoding for ZeroTTS — numpy only, no torch.

Port of the training-side tokenizer with the training-only parts removed: BPE
dropout is gone (inference is always dropout=0.0) and ids come back as
``np.ndarray`` instead of ``torch.Tensor``. Everything that affects *which ids a
string produces* is byte-identical to the training tokenizer; that is the whole
contract of this file.

``normalize_text`` in particular must not drift. It is NFC + whitespace collapse:

  * NFC matters most for Vietnamese — decomposed input ('e' + combining marks)
    tokenizes into different pieces than the precomposed 'ệ' the vocab was
    trained on, scattering the tone across tokens.
  * Whitespace runs collapse to a single space because whitespace is carried as
    its OWN token: a tab or newline has no token of its own, so it would encode
    as <unk> and silently delete the word boundary it stands for.

A divergence here does not raise — it just makes the model sound worse on input
that looks fine, which is why it gets a docstring instead of a comment.
"""
from __future__ import annotations
import re
from pathlib import Path
from unicodedata import normalize
import numpy as np
SPECIAL_TOKENS: 'dict[str, int]' = {
    '<pad>': 0,
    '<bos>': 1,
    '<eot>': 2,
    '<soa>': 3,
    '<slot>': 4,
    '<eoa>': 5,
    '<en>': 6,
    '<vi>': 7 }
UNK_TOKEN = '<unk>'
_WS_RUN = re.compile('\\s+')

def normalize_text(text = None):
    '''NFC + whitespace collapse. Case and punctuation preserved verbatim.'''
    return _WS_RUN.sub(' ', normalize('NFC', text))


class BPEProcessor:
    '''Args:
        tokenizer: a tokenizers JSON path, the JSON string itself, or an
            already-built ``tokenizers.Tokenizer``.
    '''
    
    def __init__(self, tokenizer):
        Tokenizer = Tokenizer
        import tokenizers
    # WARNING: Decompyle incomplete

    vocab_size = (lambda self = None: self._vocab_size)()
    
    def to_str(self = None):
        return self._tok.to_str()

    
    def encode_body(self = None, text = None):
        '''NFC + whitespace-collapse -> BPE ids, no BOS/EOT.'''
        return self._tok.encode(normalize_text(text)).ids

    
    def decode(self = None, ids = None):
        '''Ids back to text, skipping the reserved specials (0-7).'''
        pass
    # WARNING: Decompyle incomplete

    
    def wrap_ids(self = None, body_ids = None, max_length = None):
        '''[BOS | body | EOT] as int32, body truncated to ``max_length``.'''
        pass
    # WARNING: Decompyle incomplete

    
    def __call__(self = None, text = None, max_length = None):
        return self.wrap_ids(self.encode_body(text), max_length)



def load_tokenizer(config = None, model_dir = None):
    '''Build the tokenizer described by a model ``config.json``.

    Accepts either an inline ``bpe_tokenizer`` JSON string (how the private
    export embeds it) or a ``tokenizer.json`` sitting next to the config (how
    the published repo lays it out).

    Char-tokenizer exports are refused rather than silently mis-encoded: the
    published model is BPE and nothing here can encode for a char vocab.
    '''
    fmt = str(config.get('text_format', 'bpe'))
    if fmt != 'bpe':
        raise ValueError(f'''text_format={fmt!r} is not supported — this package ships BPE only. A char-vocab export needs a different tokenizer than the one here.''')
    inline = config.get('bpe_tokenizer')
    if inline:
        return BPEProcessor(str(inline))
# WARNING: Decompyle incomplete


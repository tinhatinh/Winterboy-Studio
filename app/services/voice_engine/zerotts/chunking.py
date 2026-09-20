# Source Generated with Decompyle++
# File: chunking.pyc (Python 3.12)

'''Punctuation normalization + sentence segmentation/chunking for long-form
text-to-speech input.

No sentence-boundary-detection library is a project dependency (no nltk/
spacy/pysbd), so this uses a regex-based splitter, then greedily packs
sentences into chunks bounded by an estimated speaking duration.

Splitting falls back through a hierarchy so no single chunk ever exceeds
the character budget, however the user punctuates (or doesn\'t):
    1. sentence-ending punctuation (. ! ? …)
    2. commas, if a "sentence" is still too long
    3. word boundaries, if a comma-separated piece is still too long
    4. raw character slicing, as a last resort (e.g. one giant run-on word)
'''
from __future__ import annotations
import re
_SENTENCE_END_RE = re.compile('(?<=[.!?…])\\s+')
_COMMA_RE = re.compile('(?<=,)\\s+')
_CHARS_PER_SEC = 15
_PAUSE_PUNCT_RE = re.compile('[;]')
_NEWLINE_RE = re.compile('(.?)[ \\t]*(?:\\r?\\n[ \\t]*)+')
_EXISTING_PUNCT = set('.!?…,;:—–-"\')]}')

def normalize_punctuation(text = None):
    """Rewrite written-only punctuation into the breaks the model can voice.

        ';' -> ','
        newline -> '. ' when the line does not already end in punctuation,
                   otherwise just a space.

    Semicolons are converted FIRST, so a line ending in one counts as
    already-punctuated when the newline rule runs (it ends in ',' by then)
    and does not also collect a '.'. ':' is untouched by this step, but is
    already in _EXISTING_PUNCT so a line ending in one is also treated as
    already-punctuated.
    """
    if not text:
        return text
    text = None.sub(',', text)
    
    def _repl(m = None):
        prev = m.group(1)
        if not prev:
            return ''
        if prev in _EXISTING_PUNCT:
            return f'''{prev} '''
        return f'''{None}. '''

    text = _NEWLINE_RE.sub(_repl, text)
    return text.strip()


def split_sentences(text = None):
    text = text.strip()
    if not text:
        return []
    sentences = None
    for para in re.split('\\n\\s*\\n', text):
        para = para.strip()
        if not para:
            continue
        for sent in _SENTENCE_END_RE.split(para):
            sent = sent.strip()
            if not sent:
                continue
            sentences.append(sent)
    return sentences


def _pack_pieces(pieces = None, max_chars = None):
    '''Greedily join `pieces` (each already <= max_chars) with a single
    space, filling each output chunk as close to max_chars as possible
    without exceeding it.'''
    chunks = []
    current = []
    current_len = 0
    for piece in pieces:
        piece_len = len(piece) + 1 if current else 0
        if current and current_len + piece_len > max_chars:
            chunks.append(' '.join(current))
            current_len = 0
            current = []
            piece_len = len(piece)
        current.append(piece)
        current_len += piece_len
    if current:
        chunks.append(' '.join(current))
    return chunks


def _split_by_chars(text = None, max_chars = None):
    pass
# WARNING: Decompyle incomplete


def _split_by_words(text = None, max_chars = None):
    words = text.split()
    pieces = _pack_pieces(words, max_chars)
    out = []
    for piece in pieces:
        if len(piece) <= max_chars:
            out.append(piece)
            continue
        out.extend(_split_by_chars(piece, max_chars))
    return out


def _atomize(text = None, max_chars = None):
    '''Break `text` down until every returned piece is <= max_chars,
    preferring the least disruptive split available (comma > word >
    character).'''
    text = text.strip()
    if not text:
        return []
    if None(text) <= max_chars:
        return [
            text]
# WARNING: Decompyle incomplete


def chunk_text(text = None, max_chunk_sec = None):
    """Split `text` into speakable chunks whose estimated duration stays
    near `max_chunk_sec`, preferring to break on sentence-ending
    punctuation, then commas, then words, then raw characters as a last
    resort — so a single chunk never balloons past the budget no matter how
    the input is (or isn't) punctuated.
    """
    max_chars = max(1, int(max_chunk_sec * _CHARS_PER_SEC))
    sentences = split_sentences(text)
    atoms = []
    for sent in sentences:
        atoms.extend(_atomize(sent, max_chars))
    return _pack_pieces(atoms, max_chars)

_TRAILING_RE = re.compile('[^\\w]+$', re.UNICODE)
_MID_PUNCT_RE = re.compile('[^\\w\\s\\-/.,:?@!\\"\'%]', re.UNICODE)
_REPEAT_COMMA_RE = re.compile('\\s*(?:,\\s*)+')
_END_PUNCT = {
    '!',
    '.',
    '?'}

def clean_segment_punctuation(text = None):
    '''Normalize a single chunked segment\'s punctuation for TTS:

        1. every mid-segment punctuation mark other than
           \'-\', \'/\', \'.\', \':\', \'?\', \'!\', \'"\', "\'", \'%\' becomes a \',\' pause
        2. terminal mark: kept as-is if it\'s \'.\', \'!\', or \'?\', otherwise
           whatever trails (comma, dash, stray symbol, nothing) -> \'.\'
    '''
    text = text.strip()
    if not text:
        return text
    m = None.search(text)
    core = text[:m.start()] if m else text
    trailing = text[m.start():].rstrip() if m else ''
    end_punct = trailing[-1] if trailing and trailing[-1] in _END_PUNCT else '.'
    core = _MID_PUNCT_RE.sub(',', core)
    core = _REPEAT_COMMA_RE.sub(', ', core).strip(' ,')
    if not core:
        return ''
    return core + end_punct


def load_text_samples(path = None):
    '''Parse a "### name" delimited sample-text file (see webui/test_samples.txt\'s
    header for the format) into {name: text}. Missing file -> {}.'''
    pass
# WARNING: Decompyle incomplete


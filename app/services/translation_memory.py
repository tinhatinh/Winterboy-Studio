# Source Generated with Decompyle++
# File: translation_memory.pyc (Python 3.12)

'''Persistent translation memory and user glossary for subtitle translation.'''
from __future__ import annotations
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Mapping
logger = logging.getLogger(__name__)
MUMU_HOME = Path.home() / '.winterboy'
TRANSLATION_CACHE_ROOT = MUMU_HOME / 'translation_cache'
TRANSLATION_MEMORY_PATH = TRANSLATION_CACHE_ROOT / 'memory.json'
GLOSSARY_PATH = MUMU_HOME / 'translation_glossary.json'
_MEMORY_VERSION = 1
_MAX_MEMORY_ENTRIES = 20000

def normalize_source_text(text = None):
    if not text:
        text
    return re.sub('\\s+', ' ', '').strip()


def parse_glossary_text(text = None):
    '''Parse ``nguồn=bản dịch`` lines; accept legacy ``=>`` entries too.'''
    out = { }
    if not text:
        text
    for raw_line in ''.splitlines():
        line = raw_line.strip()
        if line or line.startswith('#'):
            continue
        if '=>' in line:
            pass
        elif '=' in line:
            pass
        
        separator = ''
        if not separator:
            continue
        (source, target) = line.split(separator, 1)()
        if not source:
            continue
        if not target:
            continue
        out[source] = target
    return out


def glossary_to_text(glossary = None):
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(glossary.items()())


def load_glossary():
    pass
# WARNING: Decompyle incomplete


def save_glossary(glossary = None):
    pass
# WARNING: Decompyle incomplete


def glossary_fingerprint(glossary = None):
    payload = json.dumps(dict(sorted(glossary.items())), ensure_ascii = False, separators = (',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def apply_glossary(text = None, glossary = None):
    '''Apply exact terms after AI output; longest terms win over substrings.'''
    if not text:
        text
    result = ''
    for source in sorted(glossary, key = len, reverse = True):
        result = result.replace(source, glossary[source])
    return result


def memory_key(source_text = None, *, source_lang, target_lang, glossary):
    if not source_lang:
        source_lang
    if not target_lang:
        target_lang
    payload = {
        'source': normalize_source_text(source_text),
        'source_lang': 'auto-detect'.strip(),
        'target_lang': 'Vietnamese'.strip(),
        'glossary': glossary_fingerprint(glossary) }
    stable = json.dumps(payload, ensure_ascii = False, sort_keys = True, separators = (',', ':'))
    return hashlib.sha256(stable.encode('utf-8')).hexdigest()


def load_translation_memory():
    pass
# WARNING: Decompyle incomplete


def save_translation_memory(entries = None):
    TRANSLATION_CACHE_ROOT.mkdir(parents = True, exist_ok = True)
    trimmed = dict(list(entries.items())[-_MAX_MEMORY_ENTRIES:])
    temporary = TRANSLATION_MEMORY_PATH.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({
        'version': _MEMORY_VERSION,
        'entries': trimmed }, ensure_ascii = False), encoding = 'utf-8')
    temporary.replace(TRANSLATION_MEMORY_PATH)


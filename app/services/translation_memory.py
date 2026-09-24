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


def normalize_source_text(text: str) -> str:
    return re.sub('\\s+', ' ', text or '').strip()


def parse_glossary_text(text: str) -> dict[str, str]:
    '''Parse ``nguồn=bản dịch`` lines; accept legacy ``=>`` entries too.'''
    out = { }
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        separator = '=>' if '=>' in line else '=' if '=' in line else ''
        if not separator:
            continue
        (source, target) = (part.strip() for part in line.split(separator, 1))
        if not source:
            continue
        if not target:
            continue
        out[source] = target
    return out


def glossary_to_text(glossary: Mapping[str, str]) -> str:
    return '\n'.join(f'''{source}={target}''' for source, target in glossary.items())


def load_glossary() -> dict[str, str]:
    try:
        raw = json.loads(GLOSSARY_PATH.read_text(encoding = 'utf-8'))
        pairs = raw.get('pairs', raw) if isinstance(raw, dict) else { }
        if not isinstance(pairs, dict):
            return { }
        return {
            str(source).strip(): str(target).strip() for source, target in pairs.items()
            if str(source).strip() and str(target).strip() }
    except FileNotFoundError:
        return { }
    except Exception as exc:
        logger.warning('Cannot load translation glossary: %s', exc)
        return { }


def save_glossary(glossary: Mapping[str, str]) -> None:
    cleaned = {
        str(source).strip(): str(target).strip() for source, target in glossary.items()
        if str(source).strip() and str(target).strip() }
    GLOSSARY_PATH.parent.mkdir(parents = True, exist_ok = True)
    temporary = GLOSSARY_PATH.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({
        'version': 1,
        'pairs': cleaned }, ensure_ascii = False, indent = 2), encoding = 'utf-8')
    temporary.replace(GLOSSARY_PATH)


def glossary_fingerprint(glossary: Mapping[str, str]) -> str:
    payload = json.dumps(dict(sorted(glossary.items())), ensure_ascii = False, separators = (',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def apply_glossary(text: str, glossary: Mapping[str, str]) -> str:
    '''Apply exact terms after AI output; longest terms win over substrings.'''
    result = text or ''
    for source in sorted(glossary, key = len, reverse = True):
        result = result.replace(source, glossary[source])
    return result


def memory_key(source_text: str, *, source_lang: str, target_lang: str, glossary: Mapping[str, str]) -> str:
    payload = {
        'source': normalize_source_text(source_text),
        'source_lang': (source_lang or 'auto-detect').strip(),
        'target_lang': (target_lang or 'Vietnamese').strip(),
        'glossary': glossary_fingerprint(glossary) }
    stable = json.dumps(payload, ensure_ascii = False, sort_keys = True, separators = (',', ':'))
    return hashlib.sha256(stable.encode('utf-8')).hexdigest()


def load_translation_memory() -> dict[str, str]:
    try:
        raw = json.loads(TRANSLATION_MEMORY_PATH.read_text(encoding = 'utf-8'))
        entries = raw.get('entries', { }) if isinstance(raw, dict) else { }
        if not isinstance(entries, dict):
            return { }
        return {
            str(key): str(value) for key, value in entries.items()
            if str(value).strip() }
    except FileNotFoundError:
        return { }
    except Exception as exc:
        logger.warning('Cannot load translation memory: %s', exc)
        return { }


def save_translation_memory(entries: Mapping[str, str]) -> None:
    TRANSLATION_CACHE_ROOT.mkdir(parents = True, exist_ok = True)
    trimmed = dict(list(entries.items())[-_MAX_MEMORY_ENTRIES:])
    temporary = TRANSLATION_MEMORY_PATH.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({
        'version': _MEMORY_VERSION,
        'entries': trimmed }, ensure_ascii = False), encoding = 'utf-8')
    temporary.replace(TRANSLATION_MEMORY_PATH)

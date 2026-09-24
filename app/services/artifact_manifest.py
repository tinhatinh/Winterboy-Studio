# Source Generated with Decompyle++
# File: artifact_manifest.pyc (Python 3.12)

'''Dependency-aware artifact records used by resumable render stages.

The manifest never decides that an output is reusable merely because the file
exists.  A record is valid only when the stable fingerprint of all inputs and
settings still matches and the output is still present.
'''
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any


def stable_fingerprint(value: 'Any') -> 'str':
    payload = json.dumps(value, ensure_ascii = False, sort_keys = True, separators = (',', ':'), default = str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def file_dependency(path: 'str | Path | None', *, content: 'bool' = False) -> 'dict[str, Any] | None':
    if not path:
        return None
    item = Path(path)
    if not item.is_file():
        return {
            'path': str(item),
            'missing': True }
    stat = item.stat()
    result = {
        'path': str(item.resolve()),
        'size': stat.st_size,
        'mtime_ns': stat.st_mtime_ns }
    if content:
        digest = hashlib.sha256()
        with item.open('rb') as stream:
            for block in iter((lambda :stream.read(1048576)), b''):
                digest.update(block)
        result['sha256'] = digest.hexdigest()
    return result


class DependencyManifest:
    '''Small atomic JSON manifest for one render/cache workspace.'''
    VERSION = 1

    def __init__(self, path: 'str | Path'):
        self.path = Path(path)
        self.data = {
            'version': self.VERSION,
            'artifacts': { } }
        self._load()

    def _load(self) -> 'None':
        
        try:
            loaded = json.loads(self.path.read_text(encoding = 'utf-8'))
            if not isinstance(loaded, dict):
                return None
            if isinstance(loaded.get('artifacts'), dict):
                self.data = loaded
                return None
            return None
        except (OSError, ValueError, TypeError):
            return None

    def _save(self) -> 'None':
        self.path.parent.mkdir(parents = True, exist_ok = True)
        temp = self.path.with_suffix(self.path.suffix + '.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        temp.replace(self.path)

    def valid(self, name: 'str', dependencies: 'Any', *, output: 'str | Path | None' = None,
            min_size: 'int' = 1) -> 'bool':
        record = (self.data.get('artifacts') or { }).get(name)
        if not isinstance(record, dict):
            return False
        if record.get('fingerprint') != stable_fingerprint(dependencies):
            return False
        if not output:
            output = record.get('output') or ''
        candidate = Path(output)
        
        try:
            if not candidate.is_file():
                return False
            return candidate.stat().st_size >= min_size
        except OSError:
            return False

    def record(self, name: 'str', output: 'str | Path', dependencies: 'Any', *,
               metadata: 'dict[str, Any] | None' = None, save: 'bool' = True) -> 'None':
        artifacts = self.data.setdefault('artifacts', { })
        artifacts[name] = {
            'output': str(Path(output)),
            'fingerprint': stable_fingerprint(dependencies),
            'dependencies': dependencies,
            'metadata': dict(metadata or { }),
            'updated_at': time.time() }
        self.data['updated_at'] = time.time()
        if save:
            self._save()
            return None

    def save(self) -> 'None':
        '''Persist records added with ``save=False`` in one atomic write.'''
        self._save()

    def invalidate(self, name: 'str', *, save: 'bool' = True) -> 'None':
        artifacts = self.data.setdefault('artifacts', { })
        if name in artifacts:
            artifacts.pop(name, None)
            if save:
                self._save()
                return None
            return None

    def get(self, name: 'str') -> 'dict[str, Any] | None':
        record = (self.data.get('artifacts') or { }).get(name)
        if isinstance(record, dict):
            return dict(record)
        return None

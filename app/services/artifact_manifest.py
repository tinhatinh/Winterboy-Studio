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

def stable_fingerprint(value = None):
    payload = json.dumps(value, ensure_ascii = False, sort_keys = True, separators = (',', ':'), default = str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def file_dependency(path = None, *, content):
    pass
# WARNING: Decompyle incomplete


class DependencyManifest:
    '''Small atomic JSON manifest for one render/cache workspace.'''
    VERSION = 1
    
    def __init__(self = None, path = None):
        self.path = Path(path)
        self.data = {
            'version': self.VERSION,
            'artifacts': { } }
        self._load()

    
    def _load(self = None):
        
        try:
            loaded = json.loads(self.path.read_text(encoding = 'utf-8'))
            if isinstance(loaded, dict):
                if isinstance(loaded.get('artifacts'), dict):
                    self.data = loaded
                    return None
                return None
            return None
        except (OSError, ValueError, TypeError):
            return None


    
    def _save(self = None):
        self.path.parent.mkdir(parents = True, exist_ok = True)
        temp = self.path.with_suffix(self.path.suffix + '.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        temp.replace(self.path)

    
    def valid(self = None, name = None, dependencies = None, *, output, min_size):
        if not self.data.get('artifacts'):
            self.data.get('artifacts')
        record = { }.get(name)
        if not isinstance(record, dict):
            return False
        if record.get('fingerprint') != stable_fingerprint(dependencies):
            return False
        if not output:
            output
            if not record.get('output'):
                record.get('output')
        candidate = Path('')
        
        try:
            if candidate.is_file():
                candidate.is_file()
            return candidate.stat().st_size >= min_size
        except OSError:
            return False


    
    def record(self = None, name = None, output = None, dependencies = None, *, metadata, save):
        artifacts = self.data.setdefault('artifacts', { })
        if not metadata:
            metadata
        artifacts[name] = {
            'output': str(Path(output)),
            'fingerprint': stable_fingerprint(dependencies),
            'dependencies': dependencies,
            'metadata': dict({ }),
            'updated_at': time.time() }
        self.data['updated_at'] = time.time()
        if save:
            self._save()
            return None

    
    def save(self = None):
        '''Persist records added with ``save=False`` in one atomic write.'''
        self._save()

    
    def invalidate(self = None, name = None, *, save):
        artifacts = self.data.setdefault('artifacts', { })
        if name in artifacts:
            artifacts.pop(name, None)
            if save:
                self._save()
                return None
            return None

    
    def get(self = None, name = None):
        if not self.data.get('artifacts'):
            self.data.get('artifacts')
        record = { }.get(name)
        if isinstance(record, dict):
            return dict(record)



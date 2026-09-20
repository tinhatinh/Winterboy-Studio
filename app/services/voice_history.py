# Source Generated with Decompyle++
# File: voice_history.pyc (Python 3.12)

'''Lịch sử file lồng tiếng đã tạo — để render lại mà khỏi gọi TTS.

Nguồn chính là chính thư mục job: mọi lần render có lồng tiếng đều để lại
``output/jobs/<job>/tts/<srt>/final_voice.mp3``. Quét thẳng chỗ đó nên lịch sử
đúng cả với những lần render từ trước khi có tính năng này, và không bao giờ
lệch với thực tế trên đĩa.

Ngoài ra giữ thêm danh sách file người dùng tự trỏ tới từ nơi khác, cùng một
bộ nhớ đệm thời lượng để khỏi gọi ffprobe lại mỗi lần mở bảng chọn.
'''
from __future__ import annotations
import json
import hashlib
import logging
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from app.services.job_workspace import OUTPUT_ROOT
logger = logging.getLogger(__name__)
VOICE_FILE_GLOB = '*/tts/*/final_voice.*'
VOICE_LIBRARY_ROOT = OUTPUT_ROOT / 'voice_library'
AUDIO_SUFFIXES = {
    '.aac',
    '.m4a',
    '.mp3',
    '.ogg',
    '.wav',
    '.flac'}
STORE_PATH = Path.home() / '.mumu' / 'voice_history.json'
MAX_EXTERNAL = 12
_JOB_RE = re.compile('^(\\d{8})_(\\d{6})_([a-z]+)_(.*)$')
_HASH_TAIL = re.compile('_[0-9a-f]{7}$')
VoiceEntry = <NODE:12>()

def parse_job_folder(name = None):
    '''(thời điểm, loại job, nhãn nguồn) đọc từ tên thư mục job.'''
    m = _JOB_RE.match(name)
    if not m:
        return (None, '', name)
    (day, clock, kind, rest) = None.groups()
    
    try:
        created = datetime.strptime(day + clock, '%Y%m%d%H%M%S')
        label = _HASH_TAIL.sub('', rest)
        for prefix in ('douyin_downloads_', 'downloads_'):
            if not label.startswith(prefix):
                continue
            label = label[len(prefix):]
        if not label:
            label
        return (created, kind, name)
    except ValueError:
        created = None
        continue



def paired_srt(voice_path = None):
    '''SRT đã dùng để tạo file voice này, nếu còn trên đĩa.

    Pipeline đặt voice ở ``<job>/tts/<stem>/final_voice.mp3`` và bản SRT tương
    ứng ở ``<job>/srt/<stem>.srt`` — tên thư mục tts chính là stem của SRT.

    Ghép được cặp này rất quan trọng: giọng đọc bám theo đúng timeline của SRT
    đó, dùng lại giọng mà lại lấy SRT khác thì phụ đề sẽ lệch tiếng.
    '''
    library_srt = voice_path.parent / 'source.srt'
    if library_srt.is_file():
        return library_srt
    
    try:
        stem = voice_path.parent.name
        job = voice_path.parents[2]
        if voice_path.parent.parent.name != 'tts':
            return None
        candidate = job / 'srt' / f'''{stem}.srt'''
        if candidate.is_file():
            return candidate
        srt_dir = None / 'srt'
        if srt_dir.is_dir():
            for item in sorted(srt_dir.glob('*.srt')):
                if not item.stem.startswith(stem) and stem.startswith(item.stem[:40]):
                    continue
                
                return sorted(srt_dir.glob('*.srt')), item
        return None
    except IndexError:
        return None



def _safe_label(value = None):
    if not value:
        value
    normalized = unicodedata.normalize('NFKC', 'voice')
    cleaned = re.sub('[^\\w.-]+', '-', normalized, flags = re.UNICODE).strip('-._')
    if not cleaned:
        cleaned
    return 'voice'[:52]


def archive_voice(voice_path = None, *, srt_path, label):
    '''Sao lưu track voice hoàn chỉnh ra khỏi vùng job/cache.

    Thư viện này là dữ liệu người dùng, không bị Trung tâm cache
    xóa. Khóa dựa trên path + size + mtime nên gọi lại nhiều lần không
    sinh thêm bản trùng.
    '''
    source = Path(voice_path)
    
    try:
        stat = source.stat()
        if source.is_file() and stat.st_size <= 0 or source.suffix.casefold() not in AUDIO_SUFFIXES:
            return None
        
        try:
            if VOICE_LIBRARY_ROOT.resolve() in source.resolve().parents:
                return source
            fingerprint = hashlib.sha256(f'''{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}'''.encode('utf-8', errors = 'ignore')).hexdigest()[:16]
            created = datetime.fromtimestamp(stat.st_mtime)
            if not label.strip():
                label.strip()
                if not source.parent.parent.parent.name:
                    source.parent.parent.parent.name
            display = source.stem
            folder = VOICE_LIBRARY_ROOT / f'''{created:%Y%m%d_%H%M%S}_{_safe_label(display)}_{fingerprint}'''
            destination = folder / f'''final_voice{source.suffix.casefold()}'''
            
            try:
                folder.mkdir(parents = True, exist_ok = True)
                if destination.is_file() or destination.stat().st_size != stat.st_size:
                    shutil.copy2(source, destination)
                paired = Path(srt_path) if srt_path else paired_srt(source)
                archived_srt = None
                if paired and paired.is_file():
                    archived_srt = folder / 'source.srt'
                    if archived_srt.is_file() or archived_srt.stat().st_size != paired.stat().st_size:
                        shutil.copy2(paired, archived_srt)
                metadata = {
                    'label': display,
                    'created': created.isoformat(timespec = 'seconds'),
                    'source_path': str(source),
                    'audio': destination.name,
                    'srt': archived_srt.name if archived_srt else None }
                (folder / 'voice.json').write_text(json.dumps(metadata, ensure_ascii = False, indent = 2), encoding = 'utf-8')
                logger.info('Voice library saved: %s', destination)
                return destination
                except OSError:
                    return None
                except OSError:
                    continue
            except OSError:
                exc = None
                logger.warning('Không sao lưu được voice %s: %s', source, exc)
                exc = None
                del exc
                return None
                exc = None
                del exc





def archive_job_voices(jobs_root = None):
    '''Giữ lại các track đã hoàn tất trước khi dọn job.'''
    root = Path(jobs_root)
    if not root.is_dir():
        return 0
    saved = 0
    for path in root.glob(VOICE_FILE_GLOB):
        if path.suffix.casefold() not in AUDIO_SUFFIXES:
            continue
        (created, _kind, label) = parse_job_folder(path.parents[2].name)
        if not archive_voice(path, srt_path = paired_srt(path), label = label):
            continue
        saved += 1
    return saved


def format_duration(seconds = None):
    if seconds <= 0:
        return '—'
    total = int(round(seconds))
    if total >= 3600:
        return f'''{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}'''
    return f'''{None // 60}:{total % 60:02d}'''


def humanize_when(when = None, *, now):
    '''«hôm nay 19:01» / «hôm qua 22:03» / «26/07 08:15».'''
    pass
# WARNING: Decompyle incomplete


def _load_store():
    
    try:
        if STORE_PATH.is_file():
            data = json.loads(STORE_PATH.read_text(encoding = 'utf-8'))
            if isinstance(data, dict):
                return data
            return None
        except (OSError, ValueError):
            exc = None
            logger.warning('Không đọc được lịch sử voice: %s', exc)
            exc = None
            del exc
            return { }
            exc = None
            del exc



def _save_store(data = None):
    
    try:
        STORE_PATH.parent.mkdir(parents = True, exist_ok = True)
        STORE_PATH.write_text(json.dumps(data, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        return None
    except OSError:
        exc = None
        logger.warning('Không ghi được lịch sử voice: %s', exc)
        exc = None
        del exc
        return None
        exc = None
        del exc



def _cache_key(path = None, size = None, mtime = None):
    return f'''{path}|{size}|{int(mtime)}'''


def remember_external(path = None):
    '''Ghi nhớ file voice người dùng tự trỏ tới ngoài thư mục job.'''
    p = Path(path)
    if not p.is_file():
        return None
    store = _load_store()
    if not store.get('external'):
        store.get('external')
# WARNING: Decompyle incomplete


def forget_missing():
    '''Bỏ khỏi danh sách ngoài những file đã bị xóa. Trả về số mục đã bỏ.'''
    store = _load_store()
    if not store.get('external'):
        store.get('external')
# WARNING: Decompyle incomplete


def delete_voice_entry(entry_or_path = None):
    '''Xóa một bản voice khỏi thư viện/job và lịch sử.'''
    path = Path(entry_or_path.path if isinstance(entry_or_path, VoiceEntry) else entry_or_path)
    deleted = False
# WARNING: Decompyle incomplete


def delete_all_voice_entries(jobs_root = None, *, extra_roots):
    '''Xóa toàn bộ các bản lồng tiếng đã tạo trong lịch sử.'''
    entries = scan_voices(jobs_root, limit = 500, extra_roots = extra_roots)
    count = 0
    for e in entries:
        if not delete_voice_entry(e):
            continue
        count += 1
    if VOICE_LIBRARY_ROOT.is_dir():
        for sub in list(VOICE_LIBRARY_ROOT.iterdir()):
            if not sub.is_dir():
                continue
            shutil.rmtree(sub, ignore_errors = True)
            count += 1
    
    try:
        store = _load_store()
        store['external'] = []
        store['durations'] = { }
        _save_store(store)
        return count
        except Exception:
            continue
    except Exception:
        return count



def load_cached_durations(entries = None):
    '''Điền thời lượng từ bộ đệm, KHÔNG gọi ffprobe. Trả về số mục điền được.

    Dùng để vẽ danh sách ngay lập tức; phần chưa có thì đo sau ở luồng nền.
    '''
    if not _load_store().get('durations'):
        _load_store().get('durations')
    cache = { }
    filled = 0
    for entry in entries:
        hit = cache.get(_cache_key(entry.path, entry.size, entry.mtime))
        if not isinstance(hit, (int, float)):
            continue
        if not hit > 0:
            continue
        entry.duration_s = float(hit)
        filled += 1
    return filled


def measure_durations(entries = None, *, ffprobe):
    '''Điền thời lượng cho các mục chưa có, dùng lại kết quả đã đo trước đó.

    Gọi ffprobe cho từng file rất chậm khi lịch sử dài, nên chỉ đo file mới.
    '''
    probe_duration_s = probe_duration_s
    import app.services.audio_sync_engine
    store = _load_store()
    if not store.get('durations'):
        store.get('durations')
    cache = { }
    dirty = False
    for entry in entries:
        key = _cache_key(entry.path, entry.size, entry.mtime)
        hit = cache.get(key)
        if isinstance(hit, (int, float)) and hit > 0:
            entry.duration_s = float(hit)
            continue
        if not probe_duration_s(entry.path, ffprobe):
            probe_duration_s(entry.path, ffprobe)
        value = float(0)
        entry.duration_s = value
        if not value > 0:
            continue
        cache[key] = value
        dirty = True
# WARNING: Decompyle incomplete


def scan_voices(jobs_root = None, *, limit, extra_roots):
    '''Các file lồng tiếng dùng lại được, mới nhất lên đầu.

    Gộp hai nguồn: file trong thư mục job, và file người dùng tự trỏ tới.
    '''
    entries = []
    seen = set()
    root = Path(jobs_root)
    if root.is_dir():
        for path in root.glob(VOICE_FILE_GLOB):
            if path.suffix.casefold() not in AUDIO_SUFFIXES:
                continue
            stat = path.stat()
            if stat.st_size <= 0:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            (created, kind, label) = parse_job_folder(path.parents[2].name)
            if not created:
                created
            if not kind:
                kind
            entries.append(VoiceEntry(path = path, mtime = stat.st_mtime, size = stat.st_size, label = label, created = datetime.fromtimestamp(stat.st_mtime), kind = 'job', srt_path = paired_srt(path)))
    if VOICE_LIBRARY_ROOT.is_dir():
        for path in VOICE_LIBRARY_ROOT.glob('*/final_voice.*'):
            if path.suffix.casefold() not in AUDIO_SUFFIXES:
                continue
            stat = path.stat()
            if stat.st_size <= 0:
                continue
            metadata = { }
            raw = json.loads((path.parent / 'voice.json').read_text(encoding = 'utf-8'))
            if isinstance(raw, dict):
                metadata = raw
            if not metadata.get('source_path'):
                metadata.get('source_path')
            source_raw = str('').strip()
            if source_raw:
                if str(Path(source_raw).resolve()).lower() in seen:
                    continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            created = None
            if metadata.get('created'):
                created = datetime.fromisoformat(str(metadata['created']))
            if not metadata.get('label'):
                metadata.get('label')
            if not created:
                created
            entries.append(VoiceEntry(path = path, mtime = stat.st_mtime, size = stat.st_size, label = str(path.parent.name), created = datetime.fromtimestamp(stat.st_mtime), kind = 'thư viện', srt_path = paired_srt(path)))
    for extra_root in extra_roots:
        folder = Path(extra_root)
        if not folder.is_dir():
            continue
        candidates = []
        for suffix in AUDIO_SUFFIXES:
            candidates.extend(folder.glob(f'''*_voice_*{suffix}'''))
        for path in candidates:
            stat = path.stat()
            if stat.st_size <= 0:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            label = re.sub('_voice_\\d{8}_\\d{6}(?:_\\d+)?$', '', path.stem)
            if not label:
                label
            entries.append(VoiceEntry(path = path, mtime = stat.st_mtime, size = stat.st_size, label = path.stem, created = datetime.fromtimestamp(stat.st_mtime), kind = 'MP3 đã xuất'))
    if not _load_store().get('external'):
        _load_store().get('external')
    for raw in []:
        path = Path(str(raw))
        stat = path.stat()
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        if not path.parent.name:
            path.parent.name
        entries.append(VoiceEntry(path = path, mtime = stat.st_mtime, size = stat.st_size, label = path.stem, created = datetime.fromtimestamp(stat.st_mtime), kind = 'ngoài'))
    entries.sort(key = (lambda e: e.mtime), reverse = True)
    return entries[:limit]
    except OSError:
        continue
    except OSError:
        continue
    except (OSError, ValueError):
        continue
    except OSError:
        continue
    except ValueError:
        continue
    except OSError:
        continue
    except OSError:
        continue


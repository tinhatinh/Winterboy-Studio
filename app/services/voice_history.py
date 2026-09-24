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

# các vị trí cần quét trong thư mục job
VOICE_FILE_GLOB = '*/tts/*/final_voice.*'
VOICE_LIBRARY_ROOT = OUTPUT_ROOT / 'voice_library'
AUDIO_SUFFIXES = {'.wav', '.aac', '.ogg', '.flac', '.m4a', '.mp3'}
STORE_PATH = Path.home() / '.winterboy' / 'voice_history.json'
MAX_EXTERNAL = 12

# 20260924_190102_story_<nguồn>_<hash>
_JOB_RE = re.compile('^(\\d{8})_(\\d{6})_([a-z]+)_(.*)$')
_HASH_TAIL = re.compile('_[0-9a-f]{7}$')


@dataclass
class VoiceEntry:
    '''Một file lồng tiếng dùng lại được.'''

    path: Path
    mtime: float
    size: int
    label: str
    created: datetime | None
    kind: str
    duration_s: float = 0.0
    srt_path: Path | None = None

    @property
    def exists(self) -> bool:
        return self.path.is_file()


def parse_job_folder(name: str) -> tuple[datetime | None, str, str]:
    '''(thời điểm, loại job, nhãn nguồn) đọc từ tên thư mục job.'''
    m = _JOB_RE.match(name)
    if not m:
        return (None, '', name)
    (day, clock, kind, rest) = m.groups()
    try:
        created = datetime.strptime(day + clock, '%Y%m%d%H%M%S')
    except ValueError:
        created = None
    label = _HASH_TAIL.sub('', rest)
    # bỏ bớt tiền tố tên video gốc cho gọn nhãn hiển thị
    for prefix in ('douyin_downloads_', 'downloads_'):
        if not label.startswith(prefix): continue
        label = label[len(prefix):]
    return (created, kind, label or name)


def paired_srt(voice_path: Path) -> Path | None:
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
    except IndexError:
        return None
    if voice_path.parent.parent.name != 'tts':
        return None
    candidate = job / 'srt' / f'''{stem}.srt'''
    if candidate.is_file():
        return candidate
    # stem có thể bị rút ngắn khi tạo job, nên thử so theo phần đầu
    srt_dir = job / 'srt'
    if srt_dir.is_dir():
        for item in sorted(srt_dir.glob('*.srt')):
            if item.stem.startswith(stem) or stem.startswith(item.stem[:40]):
                return item
    return None


def _safe_label(value: str) -> str:
    normalized = unicodedata.normalize('NFKC', value or 'voice')
    cleaned = re.sub('[^\\w.-]+', '-', normalized, flags = re.UNICODE).strip('-._')
    return (cleaned or 'voice')[:52]


def archive_voice(
    voice_path: str | Path,
    *,
    srt_path: str | Path | None = None,
    label: str = '',
) -> Path | None:
    '''Sao lưu track voice hoàn chỉnh ra khỏi vùng job/cache.

    Thư viện này là dữ liệu người dùng, không bị Trung tâm cache
    xóa. Khóa dựa trên path + size + mtime nên gọi lại nhiều lần không
    sinh thêm bản trùng.
    '''
    source = Path(voice_path)
    try:
        stat = source.stat()
    except OSError:
        return None
    if not source.is_file() or stat.st_size <= 0 or source.suffix.casefold() not in AUDIO_SUFFIXES:
        return None
    try:
        # đã nằm trong thư viện rồi thì không copy thêm
        if VOICE_LIBRARY_ROOT.resolve() in source.resolve().parents:
            return source
    except OSError:
        pass
    fingerprint = hashlib.sha256(
        f'''{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}'''.encode('utf-8', errors = 'ignore')).hexdigest()[:16]
    created = datetime.fromtimestamp(stat.st_mtime)
    display = label.strip() or source.parent.parent.parent.name or source.stem
    folder = VOICE_LIBRARY_ROOT / \
        f'''{created:%Y%m%d_%H%M%S}_{_safe_label(display)}_{fingerprint}'''
    destination = folder / f'''final_voice{source.suffix.casefold()}'''
    try:
        folder.mkdir(parents = True, exist_ok = True)
        if not destination.is_file() or destination.stat().st_size != stat.st_size:
            shutil.copy2(source, destination)
        paired = Path(srt_path) if srt_path else paired_srt(source)
        archived_srt = None
        if paired and paired.is_file():
            archived_srt = folder / 'source.srt'
            if not archived_srt.is_file() or archived_srt.stat().st_size != paired.stat().st_size:
                shutil.copy2(paired, archived_srt)
        metadata = {
            'label': display,
            'created': created.isoformat(timespec = 'seconds'),
            'source_path': str(source),
            'audio': destination.name,
            'srt': archived_srt.name if archived_srt else None}
        (folder / 'voice.json').write_text(
            json.dumps(metadata, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        logger.info('Voice library saved: %s', destination)
        return destination
    except OSError as exc:
        logger.warning('Không sao lưu được voice %s: %s', source, exc)
        return None


def archive_job_voices(jobs_root: str | Path) -> int:
    '''Giữ lại các track đã hoàn tất trước khi dọn job.'''
    root = Path(jobs_root)
    if not root.is_dir():
        return 0
    saved = 0
    for path in root.glob(VOICE_FILE_GLOB):
        if path.suffix.casefold() not in AUDIO_SUFFIXES:
            continue
        (created, _kind, label) = parse_job_folder(path.parents[2].name)
        if archive_voice(path, srt_path = paired_srt(path), label = label):
            saved += 1
    return saved


def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return '—'
    total = int(round(seconds))
    if total >= 3600:
        return f'''{total // 3600}:{(total % 3600) // 60:02d}:{total % 60:02d}'''
    return f'''{total // 60}:{total % 60:02d}'''


def humanize_when(when: datetime | None, *, now: datetime) -> str:
    '''«hôm nay 19:01» / «hôm qua 22:03» / «26/07 08:15».'''
    if when is None:
        return '—'
    days = (now.date() - when.date()).days
    if days == 0:
        return f'''hôm nay {when:%H:%M}'''
    if days == 1:
        return f'''hôm qua {when:%H:%M}'''
    if days < 7:
        return f'''{days} ngày trước, {when:%H:%M}'''
    if when.year == now.year:
        return f'''{when:%d/%m %H:%M}'''
    return f'''{when:%d/%m/%Y}'''


def _load_store() -> dict:
    try:
        if STORE_PATH.is_file():
            data = json.loads(STORE_PATH.read_text(encoding = 'utf-8'))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError) as exc:
        logger.warning('Không đọc được lịch sử voice: %s', exc)
    return {}


def _save_store(data: dict) -> None:
    try:
        STORE_PATH.parent.mkdir(parents = True, exist_ok = True)
        STORE_PATH.write_text(
            json.dumps(data, ensure_ascii = False, indent = 2),
            encoding = 'utf-8')
    except OSError as exc:
        logger.warning('Không ghi được lịch sử voice: %s', exc)


def _cache_key(path: Path, size: int, mtime: float) -> str:
    # thời lượng chỉ đáng nhớ khi đúng cả file lẫn bản sửa đổi
    return f'''{path}|{size}|{int(mtime)}'''


def remember_external(path: str | Path) -> None:
    '''Ghi nhớ file voice người dùng tự trỏ tới ngoài thư mục job.'''
    p = Path(path)
    if not p.is_file():
        return
    store = _load_store()
    items = [str(x) for x in (store.get('external') or []) if str(x) != str(p)]
    store['external'] = [str(p), *items][:MAX_EXTERNAL]
    _save_store(store)


def forget_missing() -> int:
    '''Bỏ khỏi danh sách ngoài những file đã bị xóa. Trả về số mục đã bỏ.'''
    store = _load_store()
    items = [str(x) for x in (store.get('external') or [])]
    alive = [x for x in items if Path(x).is_file()]
    if len(alive) != len(items):
        store['external'] = alive
        _save_store(store)
    return len(items) - len(alive)


def delete_voice_entry(entry_or_path: VoiceEntry | str | Path) -> bool:
    '''Xóa một bản voice khỏi thư viện/job và lịch sử.'''
    path = Path(entry_or_path.path if isinstance(entry_or_path, VoiceEntry) else entry_or_path)
    deleted = False
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    # bản trong thư viện: xóa nguyên thư mục hồ sơ của nó
    try:
        if VOICE_LIBRARY_ROOT.is_dir() and VOICE_LIBRARY_ROOT.resolve() in resolved.parents:
            folder = path.parent
            if folder.is_dir() and folder.resolve() != VOICE_LIBRARY_ROOT.resolve():
                shutil.rmtree(folder, ignore_errors = True)
                deleted = True
    except Exception as exc:
        logger.warning('Không xóa được thư mục voice library %s: %s', path, exc)
    if path.is_file():
        try:
            path.unlink()
            deleted = True
        except OSError as exc:
            logger.warning('Không xóa được file audio %s: %s', path, exc)
    # thư mục job/thoát ra đã trống thì dọn luôn, nhưng không đụng thư mục gốc
    try:
        parent = path.parent
        if parent.is_dir() and parent.name not in ('jobs', 'output', 'voice_library'):
            leftover = list(parent.iterdir())
            if not leftover or all(f.suffix.casefold() in ('.srt', '.json', '.part') for f in leftover):
                shutil.rmtree(parent, ignore_errors = True)
                deleted = True
    except Exception:
        pass
    try:
        store = _load_store()
        dirty = False
        externals = [str(x) for x in store.get('external') or []]
        path_str = str(path).casefold()
        new_ext = [x for x in externals if str(Path(x)).casefold() != path_str]
        if len(new_ext) != len(externals):
            store['external'] = new_ext
            dirty = True
        cache = store.get('durations') or {}
        new_cache = {k: v for k, v in cache.items() if not k.casefold().startswith(path_str)}
        if len(new_cache) != len(cache):
            store['durations'] = new_cache
            dirty = True
        if dirty:
            _save_store(store)
    except Exception as exc:
        logger.warning('Lỗi dọn cache voice history: %s', exc)
    return deleted


def delete_all_voice_entries(jobs_root: str | Path, *,
                             extra_roots: tuple[str | Path, ...] | list[str | Path] = (
                             )) -> int:
    '''Xóa toàn bộ các bản lồng tiếng đã tạo trong lịch sử.'''
    entries = scan_voices(jobs_root, limit = 500, extra_roots = extra_roots)
    count = 0
    for e in entries:
        if delete_voice_entry(e):
            count += 1
    # thư viện vẫn còn mục nào sót (bị xóa khỏi đĩa) thì dọn cả folder
    if VOICE_LIBRARY_ROOT.is_dir():
        for sub in list(VOICE_LIBRARY_ROOT.iterdir()):
            if not sub.is_dir(): continue
            try:
                shutil.rmtree(sub, ignore_errors = True)
                count += 1
            except Exception:
                continue
    try:
        store = _load_store()
        store['external'] = []
        store['durations'] = {}
        _save_store(store)
    except Exception:
        pass
    return count


def load_cached_durations(entries: list[VoiceEntry]) -> int:
    '''Điền thời lượng từ bộ đệm, KHÔNG gọi ffprobe. Trả về số mục điền được.

    Dùng để vẽ danh sách ngay lập tức; phần chưa có thì đo sau ở luồng nền.
    '''
    cache = _load_store().get('durations') or {}
    filled = 0
    for entry in entries:
        hit = cache.get(_cache_key(entry.path, entry.size, entry.mtime))
        if isinstance(hit, (int, float)) and hit > 0:
            entry.duration_s = float(hit)
            filled += 1
    return filled


def measure_durations(entries: list[VoiceEntry], *, ffprobe: str | None = None) -> None:
    '''Điền thời lượng cho các mục chưa có, dùng lại kết quả đã đo trước đó.

    Gọi ffprobe cho từng file rất chậm khi lịch sử dài, nên chỉ đo file mới.
    '''
    from app.services.audio_sync_engine import probe_duration_s
    store = _load_store()
    cache = store.get('durations') or {}
    dirty = False
    for entry in entries:
        key = _cache_key(entry.path, entry.size, entry.mtime)
        hit = cache.get(key)
        if isinstance(hit, (int, float)) and hit > 0:
            entry.duration_s = float(hit)
            continue
        try:
            value = float(probe_duration_s(entry.path, ffprobe) or 0.0)
        except Exception:
            value = 0.0
        entry.duration_s = value
        if value > 0:
            cache[key] = value
            dirty = True
    if dirty:
        # giữ 400 bản đo gần nhất để file lịch sử không phình vô hạn
        keys = list(cache)[-400:]
        store['durations'] = {k: cache[k] for k in keys}
        _save_store(store)


def scan_voices(
    jobs_root: str | Path,
    *,
    limit: int = 25,
    extra_roots: tuple[str | Path, ...] | list[str | Path] = ()) -> list[VoiceEntry]:
    '''Các file lồng tiếng dùng lại được, mới nhất lên đầu.

    Gộp hai nguồn: file trong thư mục job, và file người dùng tự trỏ tới.
    '''
    entries = []
    seen = set()
    # 1) các track nằm trong thư mục job
    root = Path(jobs_root)
    if root.is_dir():
        for path in root.glob(VOICE_FILE_GLOB):
            if path.suffix.casefold() not in AUDIO_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size <= 0:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            (created, kind, label) = parse_job_folder(path.parents[2].name)
            entries.append(
                VoiceEntry(
                    path = path,
                    mtime = stat.st_mtime,
                    size = stat.st_size,
                    label = label,
                    created = created or datetime.fromtimestamp(stat.st_mtime),
                    kind = kind or 'job',
                    srt_path = paired_srt(path)))
    # 2) thư viện voice đã được sao lưu vĩnh viễn
    if VOICE_LIBRARY_ROOT.is_dir():
        for path in VOICE_LIBRARY_ROOT.glob('*/final_voice.*'):
            if path.suffix.casefold() not in AUDIO_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            metadata = {}
            try:
                raw = json.loads((path.parent / 'voice.json').read_text(encoding = 'utf-8'))
                if isinstance(raw, dict):
                    metadata = raw
            except (OSError, ValueError):
                pass
            # bản đã lưu trong thư viện thì nguồn gốc không còn, chỉ chống trùng
            source_raw = str(metadata.get('source_path') or '').strip()
            if source_raw:
                try:
                    if str(Path(source_raw).resolve()).lower() in seen:
                        continue
                except OSError:
                    pass
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            created = None
            try:
                if metadata.get('created'):
                    created = datetime.fromisoformat(str(metadata['created']))
            except ValueError:
                pass
            entries.append(
                VoiceEntry(
                    path = path,
                    mtime = stat.st_mtime,
                    size = stat.st_size,
                    label = str(metadata.get('label') or path.parent.name),
                    created = created or datetime.fromtimestamp(stat.st_mtime),
                    kind = 'thư viện',
                    srt_path = paired_srt(path)))
    # 3) mp3 xuất thẳng ra thư mục khác (video_<ts>_<job>/..._voice_*.mp3)
    for extra_root in extra_roots:
        folder = Path(extra_root)
        if not folder.is_dir():
            continue
        candidates = []
        for suffix in AUDIO_SUFFIXES:
            candidates.extend(folder.glob(f'''*_voice_*{suffix}'''))
        for path in candidates:
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size <= 0:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            label = re.sub('_voice_\\d{8}_\\d{6}(?:_\\d+)?$', '', path.stem)
            entries.append(
                VoiceEntry(
                    path = path,
                    mtime = stat.st_mtime,
                    size = stat.st_size,
                    label = label or path.stem,
                    created = datetime.fromtimestamp(stat.st_mtime),
                    kind = 'MP3 đã xuất'))
    # 4) file người dùng tự trỏ tới
    for raw in _load_store().get('external') or []:
        path = Path(str(raw))
        try:
            stat = path.stat()
        except OSError:
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            VoiceEntry(
                path = path,
                mtime = stat.st_mtime,
                size = stat.st_size,
                label = path.parent.name or path.stem,
                created = datetime.fromtimestamp(stat.st_mtime),
                kind = 'ngoài'))
    entries.sort(key = (lambda e: e.mtime), reverse = True)
    return entries[:limit]

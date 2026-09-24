'''Thống kê và dọn dữ liệu tạm do Winterboy studio quản lý.

Chỉ những thư mục được liệt kê rõ trong :func:`managed_locations` mới được
đụng tới. Video thành phẩm, cấu hình, device và log không thuộc phạm vi này.
'''

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.services.job_workspace import APP_ROOT, JOBS_ROOT, STORY_PROJECTS_ROOT
from app.services.translation_memory import TRANSLATION_CACHE_ROOT
from app.services.tts_preview import TTS_PREVIEW_CACHE_ROOT

logger = logging.getLogger(__name__)


@dataclass(frozen = True)
class CacheLocation:
    key: str
    label: str
    path: Path


def managed_locations() -> tuple[CacheLocation, ...]:
    '''Danh sách đóng các vùng cache/job mà nút dọn dẹp được phép xóa.'''
    system_temp = Path(tempfile.gettempdir())
    return (
        CacheLocation('tts', 'TTS', system_temp / 'winterboy_tts_cache'),
        CacheLocation('tts_capcut', 'TTS CapCut (MP3 + thời lượng)', Path.home() / '.winterboy' / 'tts_cache' / 'capcut'),
        CacheLocation('tts_artifacts', 'Artifact TTS', system_temp / 'winterboy_tts_artifacts'),
        CacheLocation('resume', 'Resume', system_temp / 'winterboy_tts_resume'),
        CacheLocation('demucs', 'Demucs', system_temp / 'winterboy_demucs_cache'),
        CacheLocation('visual', 'Video nền', system_temp / 'winterboy_ffmpeg_visual_cache'),
        CacheLocation('preview', 'Preview', system_temp / 'winterboy_preview_audio'),
        CacheLocation('tts_voice_preview', 'Nghe thử giọng', TTS_PREVIEW_CACHE_ROOT),
        CacheLocation('translation', 'Bộ nhớ dịch', TRANSLATION_CACHE_ROOT),
        CacheLocation('legacy', 'Temp cũ', APP_ROOT / 'temp'),
        CacheLocation('jobs', 'Job cũ', JOBS_ROOT),
        CacheLocation('story_cache', 'Cache Story', STORY_PROJECTS_ROOT),
        CacheLocation('story_projects', 'Project Story', STORY_PROJECTS_ROOT))


def safe_cache_locations() -> tuple[CacheLocation, ...]:
    '''Cache có thể xóa mà không làm mất job/checkpoint TTS đang dở.'''
    protected = {'jobs', 'tts_artifacts', 'story_cache', 'story_projects', 'resume'}
    return tuple(item for item in managed_locations() if item.key not in protected)


def _measure(path: Path) -> tuple[int, int]:
    files = 0
    size = 0
    if not path.exists():
        return (files, size)
    try:
        entries = path.rglob('*') if path.is_dir() else (path,)
        for entry in entries:
            try:
                if entry.is_file():
                    files += 1
                    size += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return (files, size)
    return (files, size)


def _measure_story_cache() -> tuple[int, int]:
    '''Đo dung lượng cache xem trước (.cache/preview_draft.mp4) và clip cache của Dựng Truyện.'''
    files = 0
    size = 0
    if not STORY_PROJECTS_ROOT.is_dir():
        return (files, size)
    try:
        for p in STORY_PROJECTS_ROOT.iterdir():
            if not p.is_dir(): continue
            c_dir = p / '.cache'
            if c_dir.is_dir():
                (f_cnt, b_cnt) = _measure(c_dir)
                files += f_cnt
                size += b_cnt
            for clip_json in p.glob('*.clip.json'):
                if not clip_json.is_file(): continue
                files += 1
                try:
                    size += clip_json.stat().st_size
                except OSError:
                    continue
    except OSError:
        return (files, size)
    return (files, size)


def _measure_story_projects() -> tuple[int, int]:
    '''Đo dung lượng các dự án Dựng Truyện (loại trừ các file .cache).'''
    files = 0
    size = 0
    if not STORY_PROJECTS_ROOT.is_dir():
        return (files, size)
    try:
        for entry in STORY_PROJECTS_ROOT.rglob('*'):
            if '.cache' in entry.parts or entry.name.endswith('.clip.json'):
                continue
            if not entry.is_file(): continue
            files += 1
            try:
                size += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return (files, size)
    return (files, size)


def cache_summary() -> dict[str, object]:
    '''Trả về dung lượng/số file theo nhóm, không thay đổi filesystem.'''
    groups = []
    total_files = 0
    total_bytes = 0
    for location in managed_locations():
        if location.key == 'story_cache':
            (files, size) = _measure_story_cache()
        elif location.key == 'story_projects':
            (files, size) = _measure_story_projects()
        else:
            (files, size) = _measure(location.path)
        groups.append({
            'key': location.key,
            'label': location.label,
            'path': str(location.path),
            'files': files,
            'bytes': size})
        total_files += files
        total_bytes += size
    return {
        'groups': groups,
        'files': total_files,
        'bytes': total_bytes}


def _is_exact_managed_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
        return any(resolved == item.path.resolve() for item in managed_locations())
    except OSError:
        return False


def _clear_locations(locations: Iterable[CacheLocation]) -> dict[str, object]:
    '''Xóa nội dung các root đã khai báo, không xóa chính root.'''
    locations = tuple(locations)
    before_bytes = sum(_measure(item.path)[1] for item in locations)
    removed_files = 0
    errors = []
    for location in locations:
        root = location.path
        if not _is_exact_managed_root(root):
            errors.append(f'''Bỏ qua đường dẫn ngoài phạm vi: {root}''')
            continue
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError as exc:
            errors.append(f'''{root}: {exc}''')
            continue
        for child in children:
            try:
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed_files += 1
            except OSError as exc:
                errors.append(f'''{child}: {exc}''')
                logger.warning('Không thể dọn cache %s: %s', child, exc)
    after_bytes = sum(_measure(item.path)[1] for item in locations)
    return {
        'freed_bytes': max(0, before_bytes - after_bytes),
        'removed_entries': removed_files,
        'remaining_bytes': after_bytes,
        'errors': errors}


def clear_story_cache() -> dict[str, object]:
    '''Xóa toàn bộ thư mục .cache và các file .clip.json trong tất cả Story Projects.'''
    (before_files, before_bytes) = _measure_story_cache()
    removed_files = 0
    errors = []
    if STORY_PROJECTS_ROOT.is_dir():
        try:
            for p in list(STORY_PROJECTS_ROOT.iterdir()):
                if not p.is_dir(): continue
                c_dir = p / '.cache'
                if c_dir.is_dir():
                    try:
                        shutil.rmtree(c_dir)
                        removed_files += 1
                    except OSError as exc:
                        errors.append(f'''{c_dir}: {exc}''')
                for clip_json in list(p.glob('*.clip.json')):
                    try:
                        clip_json.unlink()
                        removed_files += 1
                    except OSError as exc:
                        errors.append(f'''{clip_json}: {exc}''')
        except OSError as exc:
            errors.append(f'''{STORY_PROJECTS_ROOT}: {exc}''')
    (after_files, after_bytes) = _measure_story_cache()
    return {
        'freed_bytes': max(0, before_bytes - after_bytes),
        'removed_entries': removed_files,
        'remaining_bytes': after_bytes,
        'errors': errors}


def clear_safe_cache() -> dict[str, object]:
    '''Dọn cache tạm; giữ nguyên jobs, resume và cue artifacts.
    Đồng thời tự động dọn sạch toàn bộ cache review nháp (.cache) của Dựng Truyện.'''
    base_result = _clear_locations(safe_cache_locations())
    story_result = clear_story_cache()
    return {
        'freed_bytes': int(base_result.get('freed_bytes', 0)) + int(story_result.get('freed_bytes', 0)),
        'removed_entries': int(base_result.get('removed_entries', 0)) + int(story_result.get('removed_entries', 0)),
        'remaining_bytes': int(base_result.get('remaining_bytes', 0)) + int(story_result.get('remaining_bytes', 0)),
        'errors': [*(base_result.get('errors') or []), *(story_result.get('errors') or [])]}


def clear_story_projects(delete_all: bool = False) -> dict[str, object]:
    '''Dọn dẹp các dự án Dựng Truyện trong output/projects/.

    - delete_all=False: Chỉ xóa các project rỗng (chưa có phân cảnh nào).
    - delete_all=True: Xóa toàn bộ dự án Dựng Truyện.
    '''
    import json
    (before_files, before_bytes) = _measure_story_projects()
    deleted_projects = 0
    skipped_projects = 0
    errors = []
    if not STORY_PROJECTS_ROOT.is_dir():
        return {
            'freed_bytes': 0,
            'deleted_projects': 0,
            'skipped_projects': 0,
            'errors': []}
    # chỉ đụng tới những thư mục nằm thẳng trong output/projects
    try:
        children = list(STORY_PROJECTS_ROOT.iterdir())
    except OSError as exc:
        return {
            'freed_bytes': 0,
            'deleted_projects': 0,
            'skipped_projects': 0,
            'errors': [f'''{STORY_PROJECTS_ROOT}: {exc}''']}
    # project "rỗng" là chưa có phân cảnh và chưa có kịch bản thô
    for item in children:
        if item.is_dir() and not item.is_symlink():
            is_empty = False
            json_file = item / 'story_project.json'
            if not json_file.is_file():
                is_empty = True
            else:
                try:
                    data = json.loads(json_file.read_text(encoding = 'utf-8'))
                    scenes = data.get('scenes') or []
                    raw = (data.get('raw_script') or '').strip()
                    if not scenes and not raw:
                        is_empty = True
                except Exception:
                    is_empty = True
            if not delete_all and not is_empty:
                skipped_projects += 1
                continue
            try:
                shutil.rmtree(item)
                deleted_projects += 1
            except OSError as exc:
                errors.append(f'''{item}: {exc}''')
        elif item.is_file() and delete_all:
            # file rời rác phía ngoài project cũng chỉ bị xóa khi xóa tất cả
            try:
                item.unlink()
                deleted_projects += 1
            except OSError as exc:
                errors.append(f'''{item}: {exc}''')
    (after_files, after_bytes) = _measure_story_projects()
    return {
        'freed_bytes': max(0, before_bytes - after_bytes),
        'deleted_projects': deleted_projects,
        'skipped_projects': skipped_projects,
        'errors': errors}


def _job_files(job: Path) -> list[Path]:
    try:
        return [path for path in job.rglob('*') if path.is_file()]
    except OSError:
        return []


def _final_voices(job: Path) -> list[Path]:
    try:
        return [
            path
            for path in job.glob('tts/*/final_voice.*')
            if path.is_file() and path.stat().st_size > 0]
        # file rỗng chưa tính là voice đã hoàn tất
    except OSError:
        return []


def _archive_and_verify_job_voices(job: Path, voices: list[Path]) -> tuple[int, list[str]]:
    '''Sao lưu từng voice; mọi lỗi đều chặn việc xóa toàn bộ job.'''
    from app.services.voice_history import archive_voice, paired_srt, parse_job_folder
    (_created, _kind, label) = parse_job_folder(job.name)
    saved = 0
    errors = []
    for source in voices:
        try:
            source_size = source.stat().st_size
            destination = archive_voice(source, srt_path = paired_srt(source), label = label)
            if destination is None or not destination.is_file():
                errors.append(f'''Không tạo được bản sao: {source}''')
                continue
            if destination.stat().st_size != source_size:
                errors.append(f'''Bản sao sai dung lượng: {source}''')
                continue
            saved += 1
        except Exception as exc:
            errors.append(f'''Không sao lưu được {source.name}: {exc}''')
            logger.warning('Không sao lưu được voice của job %s', job, exc_info = True)
    return (saved, errors)


def clear_completed_jobs(delete_story_projects: bool = False) -> dict[str, object]:
    '''Chỉ xóa job rỗng hoặc job có voice đã sao lưu và xác minh.
    Đồng thời dọn dẹp các dự án Dựng Truyện (story projects).
    - delete_story_projects=False: Chỉ dọn các dự án Dựng Truyện rỗng.
    - delete_story_projects=True: Xóa toàn bộ dự án Dựng Truyện.
    '''
    root = JOBS_ROOT
    if not _is_exact_managed_root(root):
        story_res = clear_story_projects(delete_all = delete_story_projects)
        return {
            'freed_bytes': int(story_res.get('freed_bytes', 0)),
            'deleted_jobs': 0,
            'deleted_projects': int(story_res.get('deleted_projects', 0)),
            'skipped_jobs': 0,
            'preserved_voices': 0,
            'errors': [f'''Bỏ qua đường dẫn ngoài phạm vi: {root}'''] + (story_res.get('errors') or [])}
    if not root.is_dir():
        story_res = clear_story_projects(delete_all = delete_story_projects)
        return {
            'freed_bytes': int(story_res.get('freed_bytes', 0)),
            'deleted_jobs': 0,
            'deleted_projects': int(story_res.get('deleted_projects', 0)),
            'skipped_jobs': 0,
            'preserved_voices': 0,
            'errors': story_res.get('errors') or []}
    # job còn file nhưng chưa có voice final thì giữ lại để chạy tiếp được
    before_bytes = _measure(root)[1]
    deleted_jobs = 0
    skipped_jobs = 0
    preserved_voices = 0
    errors = []
    try:
        jobs = [item for item in root.iterdir() if item.is_dir() and not item.is_symlink()]
    except OSError as exc:
        story_res = clear_story_projects(delete_all = delete_story_projects)
        return {
            'freed_bytes': int(story_res.get('freed_bytes', 0)),
            'deleted_jobs': 0,
            'deleted_projects': int(story_res.get('deleted_projects', 0)),
            'skipped_jobs': 0,
            'preserved_voices': 0,
            'errors': [f'''{root}: {exc}'''] + (story_res.get('errors') or [])}
    # voice phải nằm trong thư viện trước khi job bị xóa
    for job in jobs:
        files = _job_files(job)
        voices = _final_voices(job)
        if files and not voices:
            skipped_jobs += 1
            logger.info('Giữ job chưa hoàn tất/resume: %s', job)
            continue
        if voices:
            (saved, archive_errors) = _archive_and_verify_job_voices(job, voices)
            if archive_errors or saved != len(voices):
                skipped_jobs += 1
                errors.extend(f'''{job.name}: {message}''' for message in archive_errors)
                logger.warning('Giữ job vì voice chưa sao lưu an toàn: %s', job)
                continue
            preserved_voices += saved
        try:
            shutil.rmtree(job)
            deleted_jobs += 1
        except OSError as exc:
            errors.append(f'''{job}: {exc}''')
            logger.warning('Không thể xóa job %s: %s', job, exc)
    job_freed = max(0, before_bytes - _measure(root)[1])
    story_res = clear_story_projects(delete_all = delete_story_projects)
    return {
        'freed_bytes': job_freed + int(story_res.get('freed_bytes', 0)),
        'deleted_jobs': deleted_jobs,
        'deleted_projects': int(story_res.get('deleted_projects', 0)),
        'skipped_jobs': skipped_jobs,
        'preserved_voices': preserved_voices,
        'errors': errors + (story_res.get('errors') or [])}


def clear_all_cache_and_jobs() -> dict[str, object]:
    '''Tương thích caller cũ nhưng dùng chính sách dọn an toàn mới.'''
    cache_result = clear_safe_cache()
    job_result = clear_completed_jobs()
    return {
        'freed_bytes': int(cache_result['freed_bytes']) + int(job_result['freed_bytes']),
        'removed_entries': int(cache_result['removed_entries']),
        'deleted_jobs': int(job_result['deleted_jobs']),
        'skipped_jobs': int(job_result['skipped_jobs']),
        'preserved_voices': int(job_result['preserved_voices']),
        'remaining_bytes': int(cache_result['remaining_bytes']),
        'errors': [*(cache_result['errors'] or []), *(job_result['errors'] or [])]}


def format_bytes(value: int) -> str:
    size = float(max(0, value))
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f'''{size:.0f} {unit}''' if unit == 'B' else f'''{size:.1f} {unit}'''
        size /= 1024.0
    return '0 B'

# Source Generated with Decompyle++
# File: cache_manager.pyc (Python 3.12)

'''Thống kê và dọn dữ liệu tạm do Winterboy Studio quản lý.

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
CacheLocation = <NODE:12>()

def managed_locations():
    '''Danh sách đóng các vùng cache/job mà nút dọn dẹp được phép xóa.'''
    system_temp = Path(tempfile.gettempdir())
    return (CacheLocation('tts', 'TTS', system_temp / 'mumu_tts_cache'), CacheLocation('tts_capcut', 'TTS CapCut (MP3 + thời lượng)', Path.home() / '.winterboy' / 'tts_cache' / 'capcut'), CacheLocation('tts_artifacts', 'Artifact TTS', system_temp / 'mumu_tts_artifacts'), CacheLocation('resume', 'Resume', system_temp / 'mumu_tts_resume'), CacheLocation('demucs', 'Demucs', system_temp / 'mumu_demucs_cache'), CacheLocation('visual', 'Video nền', system_temp / 'mumu_ffmpeg_visual_cache'), CacheLocation('preview', 'Preview', system_temp / 'mumu_preview_audio'), CacheLocation('tts_voice_preview', 'Nghe thử giọng', TTS_PREVIEW_CACHE_ROOT), CacheLocation('translation', 'Bộ nhớ dịch', TRANSLATION_CACHE_ROOT), CacheLocation('legacy', 'Temp cũ', APP_ROOT / 'temp'), CacheLocation('jobs', 'Job cũ', JOBS_ROOT), CacheLocation('story_cache', 'Cache Story', STORY_PROJECTS_ROOT), CacheLocation('story_projects', 'Project Story', STORY_PROJECTS_ROOT))


def safe_cache_locations():
    '''Cache có thể xóa mà không làm mất job/checkpoint TTS đang dở.'''
    pass
# WARNING: Decompyle incomplete


def _measure(path = None):
    files = 0
    size = 0
    if not path.exists():
        return (files, size)
    
    try:
        entries = path.rglob('*') if path.is_dir() else (path,)
        for entry in entries:
            if entry.is_file():
                files += 1
                size += entry.stat().st_size
                
                try:
                    continue
                    return (files, size)
                    except OSError:
                        
                        try:
                            continue
                            
                            try:
                                pass
                            except OSError:
                                return (files, size)






def _measure_story_cache():
    '''Đo dung lượng cache xem trước (.cache/preview_draft.mp4) và clip cache của Dựng Truyện.'''
    files = 0
    size = 0
    if not STORY_PROJECTS_ROOT.is_dir():
        return (files, size)
    
    try:
        for p in STORY_PROJECTS_ROOT.iterdir():
            if not p.is_dir():
                continue
                
                try:
                    c_dir = p / '.cache'
                    if c_dir.is_dir():
                        (f_cnt, b_cnt) = _measure(c_dir)
                        files += f_cnt
                        size += b_cnt
                    for clip_json in p.glob('*.clip.json'):
                        if not clip_json.is_file():
                            continue
                            
                            try:
                                files += 1
                                size += clip_json.stat().st_size
                                
                                try:
                                    continue
                                    continue
                                    return (files, size)
                                    except OSError:
                                        
                                        try:
                                            continue
                                            
                                            try:
                                                pass
                                            except OSError:
                                                return (files, size)








def _measure_story_projects():
    '''Đo dung lượng các dự án Dựng Truyện (loại trừ các file .cache).'''
    files = 0
    size = 0
    if not STORY_PROJECTS_ROOT.is_dir():
        return (files, size)
    
    try:
        for entry in STORY_PROJECTS_ROOT.rglob('*'):
            if '.cache' in entry.parts or entry.name.endswith('.clip.json'):
                continue
            if not entry.is_file():
                continue
                
                try:
                    files += 1
                    size += entry.stat().st_size
                    
                    try:
                        continue
                        return (files, size)
                        except OSError:
                            
                            try:
                                continue
                                
                                try:
                                    pass
                                except OSError:
                                    return (files, size)







def cache_summary():
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
            'bytes': size })
        total_files += files
        total_bytes += size
    return {
        'groups': groups,
        'files': total_files,
        'bytes': total_bytes }


def _is_exact_managed_root(path = None):
    pass
# WARNING: Decompyle incomplete


def _clear_locations(locations = None):
    '''Xóa nội dung các root đã khai báo, không xóa chính root.'''
    locations = tuple(locations)
    before_bytes = (lambda .0: pass# WARNING: Decompyle incomplete
)(locations())
    removed_files = 0
    errors = []
    for location in locations:
        root = location.path
        if not _is_exact_managed_root(root):
            errors.append(f'''Bỏ qua đường dẫn ngoài phạm vi: {root}''')
            continue
        if not root.is_dir():
            continue
        children = list(root.iterdir())
        for child in children:
            removed_files += 1
    after_bytes = (lambda .0: pass# WARNING: Decompyle incomplete
)(locations())
    return {
        'freed_bytes': max(0, before_bytes - after_bytes),
        'removed_entries': removed_files,
        'remaining_bytes': after_bytes,
        'errors': errors }
    except OSError:
        exc = None
        errors.append(f'''{root}: {exc}''')
        exc = None
        del exc
        continue
        exc = None
        del exc
    except OSError:
        exc = None
        errors.append(f'''{child}: {exc}''')
        logger.warning('Không thể dọn cache %s: %s', child, exc)
        exc = None
        del exc
        continue
        exc = None
        del exc


def clear_story_cache():
    '''Xóa toàn bộ thư mục .cache và các file .clip.json trong tất cả Story Projects.'''
    (before_files, before_bytes) = _measure_story_cache()
    removed_files = 0
    errors = []
    if STORY_PROJECTS_ROOT.is_dir():
        
        try:
            for p in list(STORY_PROJECTS_ROOT.iterdir()):
                if not p.is_dir():
                    continue
                    
                    try:
                        c_dir = p / '.cache'
                        if c_dir.is_dir():
                            shutil.rmtree(c_dir)
                            removed_files += 1
                            
                            try:
                                for clip_json in list(p.glob('*.clip.json')):
                                    clip_json.unlink()
                                    removed_files += 1
                                    
                                    try:
                                        continue
                                        continue
                                        (after_files, after_bytes) = _measure_story_cache()
                                        return {
                                            'freed_bytes': max(0, before_bytes - after_bytes),
                                            'removed_entries': removed_files,
                                            'remaining_bytes': after_bytes,
                                            'errors': errors }
                                        except OSError:
                                            exc = None
                                            errors.append(f'''{c_dir}: {exc}''')
                                            
                                            try:
                                                exc = None
                                                del exc
                                                continue
                                                exc = None
                                                del exc
                                                
                                                try:
                                                    except OSError:
                                                        exc = None
                                                        errors.append(f'''{clip_json}: {exc}''')
                                                        
                                                        try:
                                                            exc = None
                                                            del exc
                                                            continue
                                                            exc = None
                                                            del exc
                                                            
                                                            try:
                                                                pass
                                                            except OSError:
                                                                exc = None
                                                                errors.append(f'''{STORY_PROJECTS_ROOT}: {exc}''')
                                                                exc = None
                                                                del exc
                                                                continue
                                                                exc = None
                                                                del exc










def clear_safe_cache():

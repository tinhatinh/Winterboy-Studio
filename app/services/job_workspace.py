# Source Generated with Decompyle++
# File: job_workspace.pyc (Python 3.12)

'''Quản lý workspace bền vững cho từng tác vụ của Winterboy Studio.

Không dùng ``temp`` cho dữ liệu người dùng.  Mỗi lần STT, dịch hoặc render
đều có một thư mục mẹ riêng trong ``output/jobs`` để dễ kiểm tra và không ghi
đè lên tác vụ khác.
'''
from __future__ import annotations
import hashlib
import re
import time
import unicodedata
from pathlib import Path
import os
import sys
APP_ROOT = Path(__file__).resolve().parents[2]
if os.environ.get('WINTERBOY_PROJECT_ROOT'):
    PROJECT_ROOT = Path(os.environ['WINTERBOY_PROJECT_ROOT']).resolve()
elif getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
elif (APP_ROOT / 'config.json').is_file():
    PROJECT_ROOT = APP_ROOT
elif (APP_ROOT.parent.parent / 'config.json').is_file():
    PROJECT_ROOT = APP_ROOT.parent.parent
else:
    PROJECT_ROOT = APP_ROOT
OUTPUT_ROOT = PROJECT_ROOT / 'output'
JOBS_ROOT = OUTPUT_ROOT / 'jobs'
DEFAULT_VIDEO_OUTPUT = OUTPUT_ROOT / 'videos'
STORY_PROJECTS_ROOT = OUTPUT_ROOT / 'projects'
JOBS_ROOT.mkdir(parents = True, exist_ok = True)
DEFAULT_VIDEO_OUTPUT.mkdir(parents = True, exist_ok = True)
(OUTPUT_ROOT / 'voice_library').mkdir(parents = True, exist_ok = True)
STORY_PROJECTS_ROOT.mkdir(parents = True, exist_ok = True)

def _safe_name(value = None, *, fallback):
    '''Tên thư mục ngắn, đọc được và an toàn trên Windows.'''
    normalized = unicodedata.normalize('NFKC', value)
    cleaned = re.sub('[^\\w.-]+', '-', normalized, flags = re.UNICODE).strip('-._')
    if not cleaned:
        cleaned
    return fallback[:24]


def create_job_workspace(kind = None, source = None):
    '''Tạo workspace duy nhất: ``output/jobs/<time>_<kind>_<video>_<id>``.'''
    if not source:
        source
    source_value = str(kind)
    source_name = Path(source_value).stem if source else kind
    stamp = time.strftime('%Y%m%d_%H%M%S')
    digest = hashlib.sha1(source_value.encode('utf-8', errors = 'ignore')).hexdigest()[:7]
    base = f'''{stamp}_{_safe_name(kind)}_{_safe_name(source_name)}_{digest}'''
    candidate = JOBS_ROOT / base
    suffix = 2
    if candidate.exists():
        candidate = JOBS_ROOT / f'''{base}_{suffix}'''
        suffix += 1
        if candidate.exists():
            continue
    candidate.mkdir(parents = True, exist_ok = False)
    for child in ('srt', 'stt', 'translated', 'tts', 'mp4'):
        (candidate / child).mkdir(exist_ok = True)
    return candidate


def is_managed_job_path(path = None):
    '''Cho biết path có nằm trong kho job của ứng dụng không.'''
    
    try:
        return JOBS_ROOT.resolve() in Path(path).resolve().parents
    except OSError:
        return False



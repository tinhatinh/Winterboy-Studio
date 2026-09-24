'''Xóa log + temp của Auto Render / Winterboy studio.'''
from __future__ import annotations
import logging
import shutil
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
APP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APP_ROOT.parent.parent
# đặt lại một lần nữa cho rõ: APP_ROOT là thư mục chứa app, không phải repo
APP_ROOT = Path(__file__).resolve().parents[2]


def clear_logs(*, clear_log_files: bool = True, clear_temp: bool = True, clear_pycache: bool = False) -> dict[str, Any]:
    '''
    Xóa / truncate log files và cache legacy trong ``temp``.
    Xóa / truncate log files và cache trong ``temp`` cũng như preview audio tạm.

    Các job đã tạo trong ``output/jobs`` và video trong thư mục xuất tuyệt đối
    không bị nút này đụng tới.

    Returns:
      log_files, temp_dirs, temp_bytes, errors
    '''
    import tempfile
    stats = {
        'log_files': 0,
        'temp_dirs': 0,
        'temp_bytes': 0,
        'errors': [] }
    log_dirs = [
        APP_ROOT / 'logs',
        REPO_ROOT / 'data' / 'logs']
    if clear_log_files:
        for ld in log_dirs:
            if not ld.is_dir():
                continue
            for f in ld.rglob('*'):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in {'.log', '.old', '.txt', '.log.1'}:
                    continue
                try:
                    # truncate chứ không unlink: logger đang giữ handle mở trên file
                    f.write_text('', encoding = 'utf-8')
                    stats['log_files'] += 1
                    logger.info('Cleared log: %s', f)
                except Exception as e:
                    stats['errors'].append(f'''{f}: {e}''')
    if clear_temp:
        temp_roots = [APP_ROOT / 'temp']
        temp_roots = [
            APP_ROOT / 'temp',
            Path(tempfile.gettempdir()) / 'winterboy_preview_audio']
        for td in temp_roots:
            if not td.is_dir():
                continue
            for child in list(td.iterdir()):
                try:
                    if child.is_file():
                        stats['temp_bytes'] += child.stat().st_size
                        child.unlink()
                    elif child.is_dir():
                        for f in child.rglob('*'):
                            if not f.is_file():
                                continue
                            try:
                                stats['temp_bytes'] += f.stat().st_size
                            except OSError:
                                continue
                        shutil.rmtree(child, ignore_errors = True)
                        stats['temp_dirs'] += 1
                    logger.info('Removed temp: %s', child)
                except Exception as e:
                    stats['errors'].append(f'''{child}: {e}''')
    if clear_pycache:
        for pyc in APP_ROOT.rglob('__pycache__'):
            if not pyc.is_dir():
                continue
            try:
                shutil.rmtree(pyc, ignore_errors = True)
            except Exception:
                continue
    return stats


def rotate_large_logs(max_bytes: int = 5000000) -> None:
    '''Xoay vòng cắt bớt file log nếu vượt quá 5 MB khi được gọi.'''
    log_dirs = [
        APP_ROOT / 'logs']
    for ld in log_dirs:
        if not ld.is_dir():
            continue
        for f in ld.glob('*.log'):
            try:
                if f.is_file() and f.stat().st_size > max_bytes:
                    backup = f.with_suffix('.log.old')
                    if backup.is_file():
                        try:
                            backup.unlink()
                        except Exception:
                            pass
                    f.rename(backup)
                    f.write_text('', encoding = 'utf-8')
                    logger.info('Rotated log file: %s -> %s', f, backup)
            except Exception as e:
                logger.debug('Log rotation skip %s: %s', f, e)
    return None

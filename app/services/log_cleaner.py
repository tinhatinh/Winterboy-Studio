# Source Generated with Decompyle++
# File: log_cleaner.pyc (Python 3.12)

'''Xóa log + temp của Auto Render / Winterboy Studio.'''
from __future__ import annotations
import logging
import shutil
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
APP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APP_ROOT.parent.parent
APP_ROOT = Path(__file__).resolve().parents[2]

def clear_logs(*, clear_log_files, clear_temp, clear_pycache):
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
                if f.suffix.lower() not in frozenset({'.log', '.old', '.txt', '.log.1'}):
                    continue
                f.write_text('', encoding = 'utf-8')
                logger.info('Cleared log: %s', f)
    if clear_temp:
        [
            APP_ROOT / 'temp'] = None
        temp_roots = [
            APP_ROOT / 'temp',
            Path(tempfile.gettempdir()) / 'mumu_preview_audio']
        for td in temp_roots:
            if not td.is_dir():
                continue
            for child in list(td.iterdir()):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    for None in child.rglob('*'):
                        if not f.is_file():
                            continue
                    shutil.rmtree(child, ignore_errors = True)
                logger.info('Removed temp: %s', child)
    if clear_pycache:
        for None in APP_ROOT.rglob('__pycache__'):
            if not pyc.is_dir():
                continue
            shutil.rmtree(pyc, ignore_errors = True)
    return stats
    except Exception:
        e = None
        stats['errors'].append(f'''{f}: {e}''')
        e = None
        del e
        continue
        e = None
        del e
    except OSError:
        continue
    except Exception:
        e = None
        stats['errors'].append(f'''{child}: {e}''')
        e = None
        del e
        continue
        e = None
        del e
    except Exception:
        continue


def rotate_large_logs(max_bytes = None):
    '''Xoay vòng cắt bớt file log nếu vượt quá 5 MB khi được gọi.'''
    log_dirs = [
        APP_ROOT / 'logs']
    for ld in log_dirs:
        if not ld.is_dir():
            continue
        for f in ld.glob('*.log'):
            if f.is_file() and f.stat().st_size > max_bytes:
                backup = f.with_suffix('.log.old')
                if backup.is_file():
                    backup.unlink()
                f.rename(backup)
                f.write_text('', encoding = 'utf-8')
                logger.info('Rotated log file: %s -> %s', f, backup)
    continue
    return None
    except Exception:
        continue
    except Exception:
        e = None
        logger.debug('Log rotation skip %s: %s', f, e)
        e = None
        del e
        continue
        e = None
        del e


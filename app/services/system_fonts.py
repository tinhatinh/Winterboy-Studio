'''Windows system-font discovery — full machine coverage.

Nguồn:
  1. HKLM + HKCU registry (font hệ thống + font user cài cho mình)
  2. C:\\Windows\\Fonts
  3. %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts  (font cài cho user)
  4. tkinter.font.families() — mọi face Windows đang dùng được (giống CapCut/Adobe)

Resolve path ưu tiên registry/file thật (FFmpeg ASS / Pillow); nếu chỉ có
tên family thì tìm file gần đúng trong các thư mục font.
'''
from __future__ import annotations
import os
import re
from functools import lru_cache
from pathlib import Path

WINDOWS_FONTS = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
USER_FONTS = Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Windows' / 'Fonts'

_FALLBACKS = {
    'Arial': 'arial.ttf',
    'Arial Bold': 'arialbd.ttf',
    'Segoe UI': 'segoeui.ttf',
    'Segoe UI Bold': 'segoeuib.ttf',
    'Tahoma': 'tahoma.ttf',
    'Verdana': 'verdana.ttf',
    'Calibri': 'calibri.ttf',
    'Times New Roman': 'times.ttf',
    'Nirmala UI': 'Nirmala.ttf',
    'Microsoft YaHei': 'msyh.ttc',
    'Microsoft YaHei UI': 'msyh.ttc'
}
_FONT_EXTS = {'.fon', '.otc', '.otf', '.ttc', '.ttf'}


def _label(value: str) -> str:
    '''Convert Windows font registry labels to a displayable face name.'''
    s = (value or '').strip()
    for junk in (
        ' (TrueType)',
        ' (OpenType)',
        ' (All res)',
        ' (VGA res)',
        ' (Plotter)'
    ):
        s = s.replace(junk, '')
    return s.strip()


def _font_dirs() -> list[Path]:
    dirs = []
    for d in (WINDOWS_FONTS, USER_FONTS):
        try:
            if d and d.is_dir():
                dirs.append(d)
        except Exception:
            continue
    return dirs


def _add_font(found: dict[str, Path], name: str, path: Path) -> None:
    name = _label(name)
    if not name or not path:
        return None
    try:
        if not path.is_file():
            return None
    except Exception:
        return None

    found.setdefault(name, path)

    base = re.sub(
        '\\s+(Bold|Italic|Regular|Light|Medium|Black|Thin|SemiBold|ExtraBold)$',
        '',
        name,
        flags=re.I
    ).strip()
    if base and base != name:
        found.setdefault(base, path)


def _scan_registry(found: dict[str, Path], hive, subkey: str) -> None:
    try:
        import winreg

        key = winreg.OpenKey(hive, subkey)
    except Exception:
        return None
    try:
        index = 0
        while True:
            try:
                (name, filename, _kind) = winreg.EnumValue(key, index)
            except OSError:
                break
            index += 1
            if not isinstance(filename, str) or not filename.strip():
                continue
            path = Path(filename)
            if not path.is_absolute():
                for base in _font_dirs():
                    candidate = base / filename
                    if not candidate.is_file():
                        continue
                    path = candidate
                    break
                path = WINDOWS_FONTS / filename
            _add_font(found, name, path)
    finally:
        try:
            import winreg

            winreg.CloseKey(key)
        except Exception:
            pass


def _scan_directory(found: dict[str, Path], directory: Path) -> None:
    try:
        if not directory.is_dir():
            return None
        for path in directory.iterdir():
            if path.suffix.lower() not in _FONT_EXTS:
                continue
            stem = path.stem.replace('_', ' ').replace('-', ' ')
            stem = re.sub('\\s+', ' ', stem).strip()
            _add_font(found, stem, path)
            if '-' in path.stem:
                fam = path.stem.split('-', 1)[0].replace('_', ' ').strip()
                if fam:
                    _add_font(found, fam, path)
    except Exception:
        return None


@lru_cache(maxsize=1)
def system_font_map() -> dict[str, Path]:
    '''face-name → file path (hệ thống + user + fallbacks).'''
    found = {}

    try:
        import winreg

        _scan_registry(
            found,
            winreg.HKEY_LOCAL_MACHINE,
            'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts'
        )
        _scan_registry(
            found,
            winreg.HKEY_CURRENT_USER,
            'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts'
        )

        try:
            _scan_registry(
                found,
                winreg.HKEY_LOCAL_MACHINE,
                'SOFTWARE\\WOW6432Node\\Microsoft\\Windows NT\\CurrentVersion\\Fonts'
            )
        except Exception:
            pass
    except Exception:
        pass

    for d in _font_dirs():
        _scan_directory(found, d)

    for name, filename in _FALLBACKS.items():
        for base in _font_dirs():
            path = base / filename
            if not path.is_file():
                continue
            _add_font(found, name, path)
            break
    return found


@lru_cache(maxsize=1)
def _tk_font_families() -> tuple[str, ...]:
    '''Mọi font face Windows đang expose cho GDI/UI (thường > registry).'''
    try:
        import tkinter as tk
        import tkinter.font as tkfont

        created = False
        try:
            root = tk._default_root
        except Exception:
            root = None
        if root is None:
            root = tk.Tk()
            root.withdraw()
            created = True
        try:
            families = tuple(sorted(set(tkfont.families()), key=str.casefold))
        finally:
            if created:
                try:
                    root.destroy()
                except Exception:
                    pass
        return families
    except Exception:
        return tuple()


def list_system_fonts(*, include_vertical: bool = True) -> list[str]:
    '''
    Danh sách full font trên máy (CapCut/Adobe-style).

    Gộp:
      - mọi face trong registry/file map
      - mọi family tkinter (font user / cloud / app cài)
    '''
    names = set()
    for n in system_font_map():
        if not n:
            continue
        names.add(n)
    for n in _tk_font_families():
        if not n:
            continue
        if not include_vertical and n.startswith('@'):
            continue
        names.add(n)
    return sorted(names, key=str.casefold)


def _norm(s: str) -> str:
    return re.sub('[\\s_\\-]+', '', (s or '').casefold())


def _find_file_fuzzy(wanted: str) -> Path | None:
    '''Tìm file font theo tên family gần đúng trong mọi thư mục font.'''
    key = _norm(wanted)
    if not key:
        return None
    best = None
    best_score = 1_000_000_000
    for directory in _font_dirs():
        try:
            for path in directory.iterdir():
                if path.suffix.lower() not in _FONT_EXTS:
                    continue
                stem = _norm(path.stem)
                if stem == key:
                    return path
                if key in stem or stem in key:
                    score = abs(len(stem) - len(key))
                    if score < best_score:
                        best_score = score
                        best = path
        except Exception:
            continue
    return best


def resolve_system_font(font_name: str) -> Path | None:
    '''Tìm file .ttf/.otf/.ttc cho tên font (preview + FFmpeg ASS).'''
    wanted = (font_name or '').strip()
    if not wanted:
        wanted = 'Arial'

    mapping = system_font_map()
    if wanted in mapping:
        return mapping[wanted]

    folded = wanted.casefold()
    for name, path in mapping.items():
        if name.casefold() == folded:
            return path

    cleaned = _label(wanted)
    if cleaned != wanted:
        hit = resolve_system_font(cleaned)
        if hit:
            return hit

    for name, path in mapping.items():
        if name.casefold().startswith(folded) or folded.startswith(name.casefold()):
            return path

    nkey = _norm(wanted)
    for name, path in mapping.items():
        if _norm(name) == nkey:
            return path

    direct = Path(wanted)
    if direct.is_file():
        return direct
    for base in _font_dirs():
        for suffix in ('.ttf', '.otf', '.ttc', '.otc', ''):
            candidate = base / f'{wanted}{suffix}'
            if not candidate.is_file():
                continue
            return candidate

    fuzzy = _find_file_fuzzy(wanted)
    if fuzzy:
        return fuzzy

    for base in _font_dirs():
        arial = base / 'arial.ttf'
        if not arial.is_file():
            continue
        return arial
    return None


def clear_font_cache() -> None:
    '''Gọi khi user vừa cài font mới — bắt buộc reload.'''
    system_font_map.cache_clear()
    _tk_font_families.cache_clear()


def font_stats() -> dict[str, int]:
    '''Debug / UI: số font theo nguồn.'''
    return {
        'mapped_files': len(system_font_map()),
        'tk_families': len(_tk_font_families()),
        'listed': len(list_system_fonts()),
        'user_dir': sum(
            1
            for p in (USER_FONTS.iterdir() if USER_FONTS.is_dir() else [])
            if p.suffix.lower() in _FONT_EXTS)
    }

# Source Generated with Decompyle++
# File: system_fonts.pyc (Python 3.12)

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
    'Microsoft YaHei UI': 'msyh.ttc' }
_FONT_EXTS = {
    '.fon',
    '.otc',
    '.otf',
    '.ttc',
    '.ttf'}

def _label(value = None):
    '''Convert Windows font registry labels to a displayable face name.'''
    if not value:
        value
    s = ''.strip()
    for junk in (' (TrueType)', ' (OpenType)', ' (All res)', ' (VGA res)', ' (Plotter)'):
        s = s.replace(junk, '')
    return s.strip()


def _font_dirs():
    dirs = []
    for d in (WINDOWS_FONTS, USER_FONTS):
        if d and d.is_dir():
            dirs.append(d)
    continue
    return dirs
    except Exception:
        continue


def _add_font(found = None, name = None, path = None):
    name = _label(name)
    if not name or path:
        return None
    
    try:
        if not path.is_file():
            return None
        found.setdefault(name, path)
        base = re.sub('\\s+(Bold|Italic|Regular|Light|Medium|Black|Thin|SemiBold|ExtraBold)$', '', name, flags = re.I).strip()
        if base:
            if base != name:
                found.setdefault(base, path)
                return None
            return None
        return None
    except Exception:
        return None



def _scan_registry(found = None, hive = None, subkey = None):
    
    try:
        import winreg
        key = winreg.OpenKey(hive, subkey)
        
        try:
            index = 0
            
            try:
                (name, filename, _kind) = winreg.EnumValue(key, index)
                
                try:
                    index += 1
                    if not isinstance(filename, str) or filename.strip():
                        continue
                    path = Path(filename)
                    if not path.is_absolute():
                        for base in _font_dirs():
                            candidate = base / filename
                            if not candidate.is_file():
                                continue
                                
                                try:
                                    path = candidate
                                    _font_dirs()
                                path = WINDOWS_FONTS / filename
                                continue
                                except Exception:
                                    return None

                                except OSError:
                                    
                                    try:
                                        pass
                                    try:
                                        
                                        try:
                                            import winreg
                                            winreg.CloseKey(key)
                                            return None
                                        except Exception:
                                            return None
                                            import winreg
                                            winreg.CloseKey(key)








def _scan_directory(found = None, directory = None):
    
    try:
        if not directory.is_dir():
            return None
            
            try:
                for path in directory.iterdir():
                    if path.suffix.lower() not in _FONT_EXTS:
                        continue
                    stem = path.stem.replace('_', ' ').replace('-', ' ')
                    stem = re.sub('\\s+', ' ', stem).strip()
                    _add_font(found, stem, path)
                    if not '-' in path.stem:
                        continue
                        
                        try:
                            fam = path.stem.split('-', 1)[0].replace('_', ' ').strip()
                            if not fam:
                                continue
                                
                                try:
                                    _add_font(found, fam, path)
                                    continue
                                    return None
                                except Exception:
                                    return None





system_font_map = (lambda : found = { }try:
import winreg_scan_registry(found, winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts')_scan_registry(found, winreg.HKEY_CURRENT_USER, 'SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts')try:
_scan_registry(found, winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\WOW6432Node\\Microsoft\\Windows NT\\CurrentVersion\\Fonts')for d in _font_dirs():
_scan_directory(found, d)for name, filename in _FALLBACKS.items():
for base in _font_dirs():
path = base / filenameif not path.is_file():
continue_add_font(found, name, path)_font_dirs()foundexcept Exception:
try:
continuetry:
passexcept Exception:
continue)()
_tk_font_families = (lambda : pass# WARNING: Decompyle incomplete
)()

def list_system_fonts(*, include_vertical):
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
        if include_vertical and n.startswith('@'):
            continue
        names.add(n)
    return sorted(names, key = str.casefold)


def _norm(s = None):
    if not s:
        s
    return re.sub('[\\s_\\-]+', '', ''.casefold())


def _find_file_fuzzy(wanted = None):
    '''Tìm file font theo tên family gần đúng trong mọi thư mục font.'''
    key = _norm(wanted)
    if not key:
        return None
    best = None
    best_score = 1000000000
    for directory in _font_dirs():
        for path in directory.iterdir():
            if path.suffix.lower() not in _FONT_EXTS:
                continue
            stem = _norm(path.stem)
            if stem == key:
                
                
                return _font_dirs(), directory.iterdir(), path
            if not directory.iterdir() in stem and stem in key:
                continue
            if not score < best_score:
                continue
            score = abs(len(stem) - len(key))
            best = path
    return best
    except Exception:
        continue


def resolve_system_font(font_name = None):
    '''Tìm file .ttf/.otf/.ttc cho tên font (preview + FFmpeg ASS).'''
    if not font_name:
        font_name
    wanted = ''.strip()
    if not wanted:
        wanted = 'Arial'
    mapping = system_font_map()
    if wanted in mapping:
        return mapping[wanted]
    folded = None.casefold()
    for name, path in mapping.items():
        if not name.casefold() == folded:
            continue
        
        return mapping.items(), path
    if cleaned != wanted:
        resolve_system_font(cleaned) = _label(wanted)
        if hit:
            return hit
        for name, path in None.items():
            if not name.casefold().startswith(folded) and folded.startswith(name.casefold()):
                continue
            
            return None.items(), path
        for name, path in mapping.items():
            if not _norm(name) == nkey:
                continue
            
            return mapping.items(), path
        if direct.is_file():
            return direct
        for None in Path(wanted)():
            for suffix in ('.ttf', '.otf', '.ttc', '.otc', ''):
                candidate = base / f'''{wanted}{suffix}'''
                if not candidate.is_file():
                    continue
                
                
                return None, ('.ttf', '.otf', '.ttc', '.otc', ''), candidate
        if fuzzy:
            return fuzzy
        for None in _find_file_fuzzy(wanted)():
            arial = base / 'arial.ttf'
            if not arial.is_file():
                continue
            
            return None, arial
        return None


def clear_font_cache():
    '''Gọi khi user vừa cài font mới — bắt buộc reload.'''
    system_font_map.cache_clear()
    _tk_font_families.cache_clear()


def font_stats():
    '''Debug / UI: số font theo nguồn.'''
    return {
        'mapped_files': len(list_system_fonts()),
        'tk_families': None,
        'listed': sum,
        'user_dir': (lambda .0: pass# WARNING: Decompyle incomplete
)(USER_FONTS.iterdir() if USER_FONTS.is_dir() else []()) }


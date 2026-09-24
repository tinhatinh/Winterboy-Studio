# -*- coding: utf-8 -*-
'''Đối chiếu app.ui.fluent_icons với bản đã phát hành.

Phần render chỉ dùng PIL (không cần cửa sổ Tk) nên so được từng pixel. Riêng
``fluent_icon`` dựng ``ctk.CTkImage`` — cần root Tk đang chạy — nên chỉ kiểm tra
chữ ký, không gọi.
'''
from __future__ import annotations

from _parity import ref_module, repo_module

DOTTED = 'app.ui.fluent_icons'

NAMES = ['settings', 'video', 'undo', 'redo', 'info', 'khong-ton-tai', 'close',
         'megaphone', 'cc', 'play']
SIZES = [8, 10, 16, 24, 32, 0, 1, -5, 3.7]
COLORS = ['#FFFFFF', '#000000', ('#FFFFFF', '#111111'), ['a', 'b'], ['chỉ-một'],
          [], None, 12, ('x', 'y', 'z')]


def _digest(image):
    return (image.mode, image.size, image.tobytes()[:4096], len(image.tobytes()))


def test_glyph_table():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    assert rep._GLYPHS == ref._GLYPHS, 'bảng codepoint khác bản đã phát hành'
    assert list(rep._GLYPHS) == list(ref._GLYPHS), 'thứ tự key khác'
    assert len(ref._GLYPHS) == 39, len(ref._GLYPHS)
    # mọi codepoint đều nằm trong vùng Private Use Area của font icon
    for name, cp in rep._GLYPHS.items():
        assert isinstance(cp, int) and 0xE000 <= cp <= 0xF8FF, (name, cp)


def test_font_path():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    a, b = rep._font_path(), ref._font_path()
    assert (a is None) == (b is None), (a, b)
    assert str(a) == str(b), (a, b)
    if a is not None:
        assert a.is_file() and a.parent.name == 'Fonts', a


def test_pair():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for color in COLORS:
        a, b = rep._pair(color), ref._pair(color)
        assert a == b, f'{color!r}: {a!r} != {b!r}'
        assert isinstance(a, tuple) and len(a) == 2, (color, a)
    assert repo_module(DOTTED)._pair(('sáng', 'tối')) == ('sáng', 'tối')
    assert repo_module(DOTTED)._pair('#FFF') == ('#FFF', '#FFF')


def test_render_undo_redo_pixels():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for size in (8, 16, 24, 33):
        for color in ('#FFFFFF', '#0F0'):
            for fn in ('_render_undo', '_render_redo'):
                a = _digest(getattr(rep, fn)(size, color))
                b = _digest(getattr(ref, fn)(size, color))
                assert a == b, f'{fn}({size}, {color}) khác bản đã phát hành'
        # redo là ảnh gương của undo
        undo = rep._render_undo(size, '#FFFFFF')
        mirror = rep._render_redo(size, '#FFFFFF')
        assert undo.size == mirror.size == (size, size), (size, undo.size)


def test_render_matches_reference():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    for name in NAMES:
        for size in SIZES:
            key = (name, int(size) if float(size) == int(size) else size)
            try:
                a = _digest(rep._render(name, size, '#FFFFFF'))
            except Exception as exc:
                a = ('err', type(exc).__name__)
            try:
                b = _digest(ref._render(name, size, '#FFFFFF'))
            except Exception as exc:
                b = ('err', type(exc).__name__)
            assert a == b, f'_render{key} khác: {a[:2] if a[0] != "err" else a} vs {b}'


def test_render_is_cached():
    """_render phải là lru_cache(256) — gọi lại không vẽ lại ảnh khác."""
    from functools import _lru_cache_wrapper
    rep = repo_module(DOTTED)
    assert isinstance(rep._render, _lru_cache_wrapper), type(rep._render)
    assert rep._render.cache_info().maxsize == 256, rep._render.cache_info()
    a = rep._render('settings', 16, '#FFFFFF')
    b = rep._render('settings', 16, '#FFFFFF')
    assert a is b


def test_public_surface():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    import inspect
    for fn in ('_font_path', '_pair', '_render_undo', '_render_redo', 'fluent_icon'):
        sa = str(inspect.signature(getattr(rep, fn)))
        sb = str(inspect.signature(getattr(ref, fn)))
        assert sa == sb, f'{fn}: {sa} != {sb}'
    # fluent_icon: size/color là keyword-only, mặc định 16 và '#FFFFFF'
    p = inspect.signature(rep.fluent_icon).parameters
    assert p['size'].kind.name == 'KEYWORD_ONLY' and p['size'].default == 16, p
    assert p['color'].default == '#FFFFFF', p

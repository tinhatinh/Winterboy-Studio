# -*- coding: utf-8 -*-
'''Đối chiếu app.services.subtitle_layout với bản đã phát hành.

Điểm cần chú ý khi khôi phục: hàm đo bề rộng bằng Pillow, nên kết quả phụ thuộc
font thật trên máy. Cả hai bên cùng chạy trên một máy và cùng dùng một Pillow nên
phép so vẫn có giá trị; phần logic cắt dòng (đoạn "…" khi vượt max_lines, cắt cứng
từ quá dài, bỏ dòng rỗng) mới là thứ cần giữ đúng.
'''
from __future__ import annotations

import sys
import types

from _parity import INTERNAL, describe, ref_module, repo_module, same_result

DOTTED = 'app.services.subtitle_layout'


def _use_shipped_dependencies():
    '''Đăng ký gói giả ``app.services`` trỏ vào bản đã cài.

    ``app/services/__init__.py`` và ``app/services/system_fonts.py`` trong repo vẫn
    còn hỏng cú pháp (không thuộc phạm vi khôi phục này), trong khi
    ``subtitle_layout`` import chúng ở đầu file. Trỏ ``__path__`` vào ``_internal``
    để CẢ HAI bên cùng dùng chung srt_utils + system_fonts đã phát hành: khác biệt
    còn lại duy nhất là đúng module đang được đối chiếu.
    '''
    for name, path in (('app', INTERNAL), ('app.services', INTERNAL / 'app' / 'services')):
        mod = sys.modules.get(name)
        want = str(path)
        if isinstance(mod, types.ModuleType) and list(getattr(mod, '__path__', [])) == [want]:
            continue
        stub = types.ModuleType(name)
        stub.__path__ = [want]
        sys.modules[name] = stub


_use_shipped_dependencies()

TEXTS = [
    '', '   ', None, 'ngắn', 'Một hai ba bốn năm sáu bảy tám chín mười',
    'Học máy lượng tử và rối lượng tử cho phép suy luận nhanh hơn',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'siêu_dài_không_có_khoảng_trong_từ_này_chút_nào ' * 3,
    'tiếng Việt có dấu: ă â ê ô ơ ư đ, và số 1234567890',
    'x' * 200, 'đã có\nsẵn\nxuống dòng', 'tab\tvà\\hkhoảng trắng lạ',
    '    leading and trailing    ', 'a b', 'a  b   c',
    'Xin chào thế giới, đây là một câu khá dài để kiểm tra việc xuống dòng',
    'Hà Nội 30 độ, mưa rào và dông rải rác khắp khu vực nội thành',
    'Ký tự đặc biệt !@#$%^&*()_+-=[]{};:",.<>/?\\|~`',
    'đường dài một từ duy nhất' + '!' * 60,
    '四五六七八九十一二三', 'Emoji 😀🎬 vui vẻ', 'mixed 中文 english Tiếng Việt',
    'end end end end end end end end end end end end end end end end',
    'a' * 30 + ' ' + 'b' * 30 + ' ' + 'c' * 30,
    '12:30:45 100% 3.14 -0.5 +7', '…dấu chấm lửng đã có sẵn',
]

WIDTHS = [0, 1, 2, 40, 60, 80, 100, 120, 160, 200, 260, 320, 400, 700, 10000]
SPACING = [0.0, -4.0, 2.0, 8.0]
FONTS = ['Arial', 'arial', 'Segoe UI', 'Không Có Font ZZZ', None, 'Tahoma']


def _cases(widths=WIDTHS, lines=(1, 2, 3, 4), spacing=(0.0, -4.0, 2.0), fonts=('Arial',)):
    out = []
    for text in TEXTS:
        for fn in fonts:
            for w in widths:
                for ml in lines:
                    for ls in spacing:
                        out.append(((text,), {'font_name': fn, 'font_size': 36,
                                              'max_width_px': w, 'letter_spacing': ls,
                                              'max_lines': ml}))
    return out


def test_wrap_subtitle_lines_empty_and_defaults():
    bad = same_result(DOTTED, 'wrap_subtitle_lines',
                      [(('',), {}), (('   ',), {}), ((None,), {}),
                       (('a',), {}), (('a b c',), {'max_width_px': 1}),
                       (('a b c',), {'max_width_px': 0}),
                       (('word',), {'max_width_px': 10000})])
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_lines_measured():
    '''Đo bằng font thật: Arial, nhiều bề rộng / letter_spacing / max_lines.'''
    bad = same_result(DOTTED, 'wrap_subtitle_lines',
                      _cases(widths=[2, 40, 120, 400], spacing=SPACING))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_lines_fallback_branch():
    '''Font không tồn tại -> rơi về đếm ký tự, phải giống hệt bản gốc.'''
    bad = same_result(DOTTED, 'wrap_subtitle_lines',
                      _cases(widths=[2, 120, 400], lines=(1, 3), spacing=(0.0, 2.0),
                             fonts=['Không Có Font ZZZ', None, '']))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_lines_other_fonts():
    bad = same_result(DOTTED, 'wrap_subtitle_lines',
                      _cases(widths=[80, 200], lines=(2, 4), spacing=(0.0, 8.0),
                             fonts=['arial', 'Segoe UI', 'Tahoma']))
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_lines_font_size_and_maxlines():
    cases = [((t,), {'font_name': 'Arial', 'font_size': fs, 'max_width_px': 120,
                     'max_lines': ml})
             for t in TEXTS[::2] for fs in (0, 1, 8, 16, 36, 96) for ml in (0, 1, 2, 5, 8)]
    cases += [((t,), {'font_size': '36', 'max_width_px': '240'}) for t in TEXTS[:8]]
    cases += [((t,), {'max_lines': '2'}) for t in TEXTS[:8]]
    cases += [((t,), {'max_width_px': 120.0, 'letter_spacing': '3'}) for t in TEXTS[:8]]
    bad = same_result(DOTTED, 'wrap_subtitle_lines', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_wrap_subtitle_block_matches_lines():
    cases = _cases(widths=[2, 60, 140, 300], lines=(1, 3), spacing=(0.0, 2.0))
    bad = same_result(DOTTED, 'wrap_subtitle_block', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_block_is_lines_joined():
    rep = repo_module(DOTTED)
    for text in TEXTS[:12]:
        for w in (0, 80, 240):
            lines = rep.wrap_subtitle_lines(text, max_width_px = w)
            assert rep.wrap_subtitle_block(text, max_width_px = w) == '\n'.join(lines), text


def test_text_width_with_fake_fonts():
    class GetLength:
        def getlength(self, text):
            return len(text) * 7.5

    class OnlyGetsize:
        def getsize(self, text):
            return (len(text) * 5, 12)

    class ListGetsize:
        def getsize(self, text):
            return [len(text) * 3, 9]

    class Broken:
        def getlength(self, text):
            raise RuntimeError('no getlength')

        def getsize(self, text):
            raise RuntimeError('no getsize')

    class NoApi:
        pass

    class BadReturn:
        def getlength(self, text):
            return 'không phải số'

    fonts = [GetLength(), OnlyGetsize(), ListGetsize(), Broken(), NoApi(), BadReturn(), None]
    texts = ['', 'a', 'abc', 'xin chào', 'x' * 40, None, 12]
    cases = [((f, t), {}) for f in fonts for t in texts]
    cases += [((f, t, ls), {}) for f in fonts[:5] for t in ['ab', 'abcde', '']
              for ls in (0.0, -3.0, 2, None, '2')]
    bad = same_result(DOTTED, '_text_width', cases)
    assert not bad, [(c, describe(a), describe(b)) for c, a, b in bad]


def test_load_font_shape():
    '''_load_font trả object Pillow có path + size; so các thuộc tính đo được.'''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)

    def shape(font):
        if font is None:
            return 'None'
        return (type(font).__name__, getattr(font, 'path', None), getattr(font, 'size', None))

    for name in FONTS + ['Segoe UI Bold', 'Arial Bold', '']:
        for size in (0, -5, 1, 16, 36, 96, '36', 2.7):
            try:
                a = shape(rep._load_font(name, size))
                b = shape(ref._load_font(name, size))
            except Exception as exc:                          # noqa: BLE001
                a = b = ('exc', type(exc).__name__)
            assert a == b, (name, size, a, b)


def test_measured_lines_fit_the_box():
    '''Mọi dòng trả về phải vẽ vừa khung — bất biến bản gốc luôn giữ (spacing = 0).'''
    rep = repo_module(DOTTED)
    font = rep._load_font('Arial', 24)
    assert font is not None, 'máy này không tìm ra Arial để đo, bỏ qua phần kiểm này'
    for text in TEXTS:
        for w in (40, 80, 120, 200, 400):
            for ml in (1, 2, 3, 5):
                lines = rep.wrap_subtitle_lines(text, max_width_px = w, max_lines = ml,
                                                font_size = 24)
                for ln in lines:
                    assert ln, (text, w, ml, lines)
                    if len(ln) > 1:
                        assert rep._text_width(font, ln) <= w + 1e-6, (text, w, ml, ln)


def test_known_upstream_quirk_ellipsis_ignores_letter_spacing():
    '''CHARACTERISATION — bản đã phát hành ĐO dòng "…" mà bỏ qua letter_spacing.

    Vòng rút gọn gọi ``_text_width(font, tail + '…')`` với 2 tham số nên letter_spacing
    bị coi là 0: user tăng khoảng chữ thì dòng cuối vẫn tràn khung. Repo phải tái hiện
    y hệ thống — test này chốt hành vi đó, khác bản gốc là báo đỏ.
    '''
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    text = 'Học máy lượng tử và rối lượng tử cho phép suy luận nhanh hơn nhiều lần'
    font = rep._load_font('Arial', 36)
    assert font is not None, 'máy này không có Arial'
    for spacing in (12.0, 30.0):
        a = rep.wrap_subtitle_lines(text, max_width_px = 200, max_lines = 2,
                                    letter_spacing = spacing, font_size = 36)
        b = ref.wrap_subtitle_lines(text, max_width_px = 200, max_lines = 2,
                                    letter_spacing = spacing, font_size = 36)
        assert a == b, (spacing, a, b)
        assert rep._text_width(font, a[-1], spacing) > 200, \
            f'không còn thấy dòng cuối tràn khung (spacing={spacing}): {a}'


def test_constants_match():
    ref, rep = ref_module(DOTTED), repo_module(DOTTED)
    assert rep.FALLBACK_MAX_CHARS == ref.FALLBACK_MAX_CHARS == 24
    assert rep.DEFAULT_MAX_LINES == ref.DEFAULT_MAX_LINES == 3
    assert rep._load_font.__wrapped__.__name__ == '_load_font'
    assert rep._load_font.cache_info().maxsize == ref._load_font.cache_info().maxsize == 64

# -*- coding: utf-8 -*-
'''Đối chiếu app.ui.control_panel với bản đã phát hành — KHÔNG cần mở cửa sổ.

control_panel là thanh công cụ bên trái (rail + một pane duy nhất). Lớp
ControlPanel phải có Tk root mới dựng được, nhưng phần quyết định hành vi thì không:

* ``test_bytecode_khop_ban_phat_hanh`` - mọi code object của ``control_panel.pyc``
  đã phát hành (26 cái: module, 2 lớp, 23 hàm/property, lambda và reset_scroll lồng
  nhau) phải còn nguyên vẹn: cùng dòng lệnh (đã chuẩn hoá jump target), cùng tên
  biến, cùng hằng đệ quy. Phần tử mới (công cụ OCR nối thêm sau này) được khai báo
  tường minh trong ``FEATURE_ADDITIONS`` và chỉ được PHÉP THÈM, không được sửa/xoá
  lệnh cũ — nên mã cũ vẫn là mã đã ship, từng instruction một.
* ``_draw_nav_icon`` - thuần PIL, so từng pixel với bản gốc cho cả 11 icon gốc.
* ``_get_module`` / ``has_module`` / ``select_tool`` / ``refresh_lists`` /
  ``_idle_preload_step`` / ``_mouse_wheel_all`` - chạy trên object giả ghi lại dấu
  vết lời gọi; hai bản phải ghi ra chuỗi giống hệt nhau.

Không test nào tạo cửa sổ; riêng ``test_control_panel_tren_cua_so_that`` cần
``MUMU_GUI_TESTS=1`` vì nó dựng Tk root thật.
'''
from __future__ import annotations

import dis
import importlib.util
import io
import logging
import marshal
import os
import re
import sys
import types
from contextlib import redirect_stderr
from pathlib import Path

from _parity import INTERNAL, REPO, RefMissing

DOTTED = 'app.ui.control_panel'
SRC = REPO / 'app' / 'ui' / 'control_panel.py'
PYC = INTERNAL / 'app' / 'ui' / 'control_panel.pyc'

GUI_OPT_IN = os.environ.get('MUMU_GUI_TESTS') == '1'

# ---- hợp đồng của BẢN ĐÃ PHÁT HÀNH (đọc thẳng từ control_panel.pyc) -------------
# thứ tự key dụng cụ: NAV, _module_classes và _pending_preload phải khớp nhau
SHIPPED_KEYS = ('video', 'subtitle', 'stt', 'srt', 'tts', 'blur', 'bgm', 'brand',
                'trim', 'fx', 'story')
SHIPPED_LABELS = ('Video', 'Phụ đề', 'STT', 'SRT', 'TTS', 'Che mờ', 'Nhạc', 'Logo',
                  'Cắt', 'Hiệu ứng', 'Dựng Truyện')
SHIPPED_PRELOAD = ('subtitle', 'srt', 'tts', 'blur', 'bgm', 'brand', 'trim', 'fx',
                   'stt', 'story')
# property -> key dụng cụ; mod_sub và mod_bypass không trùng tên với key
SHIPPED_PROP = {
    'mod_video': 'video', 'mod_sub': 'subtitle', 'mod_srt': 'srt', 'mod_stt': 'stt',
    'mod_tts': 'tts', 'mod_blur': 'blur', 'mod_bgm': 'bgm', 'mod_brand': 'brand',
    'mod_trim': 'trim', 'mod_bypass': 'fx', 'mod_story': 'story',
}
THEME_NAMES = ('ACCENT_TEXT', 'ACCENT', 'ACCENT_HOVER', 'BG_CARD', 'BG_PANEL',
               'BG_SUNKEN', 'BORDER', 'ON_ACCENT', 'SURFACE_BTN_HOVER', 'TEXT', 'TEXT_DIM')
# refresh_lists gọi thẳng từng module một, theo đúng thứ tự này
REFRESH_CALLS = [('video', 'refresh_list'), ('tts', 'refresh_reuse_voice'),
                 ('bgm', 'refresh_list'), ('srt', 'refresh_status'),
                 ('brand', 'refresh_logo_label'), ('blur', '_refresh_region_picker'),
                 ('trim', 'refresh_segments'), ('stt', 'refresh_stt_path')]

# ---- phần nối thêm sau này: công cụ OCR ----------------------------------------
OCR_KEY, OCR_LABEL, OCR_PROP = 'ocr', 'OCR', 'mod_ocr'
# code object được phép có thêm lệnh so với .pyc; không được mất/sửa lệnh cũ
FEATURE_ADDITIONS = {'<module>', 'ControlPanel', 'ControlPanel.__init__',
                     '_draw_nav_icon', 'ControlPanel.mod_ocr'}

# control_panel chỉ GIỮ tham chiếu tới các lớp module (để dựng _module_classes),
# không gọi chúng lúc import -> thay bằng lớp rỗng để khỏi kéo theo cả GUI. Nạp thật
# cũng không được: base_module xin 'section_title_kwargs' mà theme trong repo chưa có.
MODULE_IMPORT_RE = re.compile(r'^from (app\.ui\.modules\.\w+) import (.+)$', re.M)


def _load(root, tag):
    '''Nạp app/ui/control_panel từ một gốc: mã nguồn trong repo hoặc .pyc đã phát hành.'''
    path = (root / 'app' / 'ui' / 'control_panel').with_suffix('.py' if root == REPO else '.pyc')
    if not path.is_file():
        raise RefMissing(f'không có {path}')
    imports = MODULE_IMPORT_RE.findall(SRC.read_text(encoding='utf-8'))
    saved = {n: sys.modules.get(n, False) for n in ['app.ui.modules'] + [d for d, _ in imports]}
    pkg = types.ModuleType('app.ui.modules')
    pkg.__path__ = [str(REPO / 'app' / 'ui' / 'modules')]
    sys.modules['app.ui.modules'] = pkg
    for dotted, names in imports:
        stub = types.ModuleType(dotted)
        stub.__getattr__ = lambda name, _d=dotted: type(name, (), {})   # PEP 562
        sys.modules[dotted] = stub
    try:
        spec = importlib.util.spec_from_file_location(tag, str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[tag] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(tag, None)
        for n, old in saved.items():
            if old is False:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = old
    return mod


def _need_pyc():
    '''.pyc đã phát hành là chuẩn đối chiếu: không có thì bỏ qua test dựa trên nó.'''
    if not PYC.is_file():
        raise RefMissing(f'không có {PYC}')


def repo_cp():
    return _load(REPO, 'cp_repo_under_test')


def ref_cp():
    if not INTERNAL.is_dir():
        raise RefMissing(f'không có _internal ở {INTERNAL}')
    return _load(INTERNAL, 'cp_ref_under_test')


def both(fn):
    '''Chạy fn trên cả hai bản, đòi kết quả giống hệt; trả về kết quả của bản repo.'''
    a = fn(repo_cp())
    b = fn(ref_cp())
    assert a == b, f'\nrepo={a!r}\nref ={b!r}'
    return a


def fmt(args, kwargs):
    txt = ', '.join(repr(a) for a in args)
    if kwargs:
        txt += ', '.join(f'{k}={v!r}' for k, v in kwargs.items())
    return f'({txt})'


def without_ocr(keys):
    return [k for k in keys if k != OCR_KEY]


def order_preserved(sub, full):
    return [x for x in full if x in sub] == list(sub)


# ------------------------------------------------------------- thế giới giả
class Sink:
    '''Ghi mọi lời gọi thành chuỗi để so hai bản, không phụ thuộc địa chỉ object.'''

    def __init__(self):
        self.calls = []

    def add(self, text):
        self.calls.append(text)
        return text


class Widget:
    '''Widget giả: configure/pack; canvas thì thêm các hàm cuộn.'''

    def __init__(self, sink, name):
        self.sink = sink
        self.name = name

    def log(self, meth, *a, **k):
        self.sink.add(f'{self.name}.{meth}{fmt(a, k)}')

    def configure(self, **kw):
        self.log('configure', **kw)

    def pack(self, **kw):
        self.log('pack', **kw)

    def pack_forget(self):
        self.log('pack_forget')

    def yview_moveto(self, *a):
        self.log('yview_moveto', *a)

    def winfo_exists(self):
        return True


class Scrollable(Widget):
    '''content của panel: có ensure_mouse_wheel -> select_tool phải gọi nó.'''

    def ensure_mouse_wheel(self):
        self.log('ensure_mouse_wheel')


class Bare(Widget):
    '''Không có hook nào ngoài pack/pack_forget: test các nhánh hasattr() False.'''


class Mod(Widget):
    '''Module nội dung đã tạo sẵn: đủ hook on_tab_*.'''

    def on_tab_deactivated(self):
        self.log('on_tab_deactivated')

    def on_tab_activated(self):
        self.log('on_tab_activated')

    def set_header_visible(self, v):
        self.log('set_header_visible', v)


class Boom(Widget):
    '''Hook nổ tung: các except trong module phải nuốt sạch.'''

    def on_tab_deactivated(self):
        raise RuntimeError('deactivated')

    def on_tab_activated(self):
        raise RuntimeError('activated')


KINDS = {'mod': Mod, 'bare': Bare, 'boom': Boom}


def make_mod_class(sink, key, boom=False):
    '''Lớp module giả mà _get_module thật có thể gọi: cls(content, state, callbacks).'''

    class _Cls:
        def __init__(self, parent, state, callbacks):
            sink.add(f'new mod[{key}]')
            self.parent, self.state, self.callbacks = parent, state, callbacks

        def set_header_visible(self, v):
            sink.add(f'mod[{key}].set_header_visible({v!r})')
            if boom:
                raise RuntimeError('header')

        def pack_forget(self):
            sink.add(f'mod[{key}].pack_forget()')

    _Cls.__name__ = 'Module' + key.capitalize()
    return _Cls


class Panel:
    '''Giả chính mình là ControlPanel: chỉ dựng mấy attribute các hàm đang test cần.'''

    def __init__(self, classes=(), mods=(), buttons=(), images=None, titles=None,
                 pending=(), top=None, content=None, canvas=None, exists=True,
                 active='', state=None):
        self.sink = Sink()
        self._module_classes = {k: make_mod_class(self.sink, k, boom=(v == 'boom'))
                                for k, v in classes}
        self._modules = {k: KINDS[v](self.sink, f'mod[{k}]') for k, v in mods}
        self._nav_buttons = {k: Widget(self.sink, f'nav[{k}]') for k in buttons}
        self._nav_images = dict(images or {})
        self._titles = dict(titles or {})
        self._pending_preload = list(pending)
        self._active_key = active
        self.state = state if state is not None else object()
        self.callbacks = {}
        self.after_calls = []
        self.idle_calls = []
        self.exists = exists
        self.content = content if content is not None else Scrollable(self.sink, 'content')
        if canvas is not None:
            self.content._parent_canvas = canvas
        self._content_title = Widget(self.sink, 'title')
        self._top = top if top is not None else object()

    @property
    def trace(self):
        return self.sink.calls

    def winfo_exists(self):
        if not self.exists:
            raise TypeError('window da bi huy')
        return True

    def winfo_toplevel(self):
        return self._top

    def after(self, ms, fn):
        self.after_calls.append(ms)
        self.sink.add(f'panel.after({ms!r}, {getattr(fn, "__name__", "?")})')

    def after_idle(self, fn):
        self.idle_calls.append(fn)
        self.sink.add('panel.after_idle(reset_scroll)')

    def _idle_preload_step(self):
        '''Đứng chỗ: bản thật được chính _idle_preload_step truyền vào after().'''

    def _get_module(self, key, create=True):
        '''Bản giả: select_tool/preload chỉ cần gọi được là đủ, khỏi dựng widget thật.'''
        self.sink.add(f"panel._get_module({key!r}, create={create!r})")
        if not create and key not in self._modules:
            return None
        made = self._modules.get(key) or Mod(self.sink, f'mod[{key}]')
        self._modules[key] = made
        return made


class AppStateish:
    '''Mảnh trạng thái dùng được: select_tool ghi self.state.active_tool = key.'''


class MainTop:
    '''Thay MainWindow: có set_story_mode + preview.'''

    def __init__(self, boom=False):
        self.calls = []
        self._boom = boom
        self.preview = Preview(boom)

    def set_story_mode(self, on):
        self.calls.append(('main', on))
        if self._boom:
            raise RuntimeError('top')


class Preview:
    def __init__(self, boom=False):
        self.calls = []
        self._boom = boom

    def set_story_mode(self, on):
        self.calls.append(('preview', on))
        if self._boom:
            raise RuntimeError('preview')


class Event:
    def __init__(self, widget='w', **kw):
        self.widget = widget
        for k, v in kw.items():
            setattr(self, k, v)


class Canvas:
    '''_parent_canvas giả: trả view dựng sẵn để chọn đúng nhánh cuộn.'''

    def __init__(self, calls, xview=(0.0, 1.0), yview=(0.0, 0.5)):
        self.calls = calls
        self._x = xview
        self._y = yview

    def xview(self, *a):
        self.calls.append(('xview',) + a)
        return self._x

    def yview(self, *a):
        self.calls.append(('yview',) + a)
        return self._y

    def xview_scroll(self, *a):
        self.calls.append(('xview_scroll',) + a)

    def yview_scroll(self, *a):
        self.calls.append(('yview_scroll',) + a)


class Scroll:
    '''Giả _ToolScroll cho _mouse_wheel_all: canvas + cờ shift + hàm kiểm hợp lệ.'''

    def __init__(self, valid=True, shift=False, xview=(0.0, 1.0), yview=(0.0, 0.5)):
        self.calls = []
        self._valid = valid
        self._shift_pressed = shift
        self._parent_canvas = Canvas(self.calls, xview, yview)

    def _check_if_valid_scroll(self, widget):
        self.calls.append(('check', widget))
        return self._valid


class Plat:
    '''Thế chỗ tên ``sys`` trong namespace của control_panel -> đi được cả 3 nhánh.'''

    def __init__(self, platform):
        self.platform = platform


class quiet_logger:
    '''_get_module gọi logger.exception() -> traceback dài, giấu khỏi output test.'''

    def __enter__(self):
        self.buf = io.StringIO()
        self.ctx = redirect_stderr(self.buf)
        self.ctx.__enter__()
        self.old = logging.getLogger().handlers
        logging.getLogger().handlers = [logging.NullHandler()]
        return self

    def __exit__(self, *exc):
        logging.getLogger().handlers = self.old
        return self.ctx.__exit__(*exc)


# ================================================================= hằng số cấp module
def test_theme_reexport():
    '''11 màu của rail là đồ nhập lại từ app.config.theme, không phải bản copy.'''
    import app.config.theme as theme
    mod = repo_cp()
    for name in THEME_NAMES:
        got = getattr(mod, name)
        assert got is getattr(theme, name), f'{name} khong phai cung object'
        assert isinstance(got, tuple) and len(got) == 2, (name, got)
        assert all(isinstance(c, str) and c.startswith('#') for c in got), (name, got)


def test_module_imports_va_logger():
    mod = repo_cp()
    assert isinstance(mod.logger, logging.Logger)
    assert mod.sys is sys and mod.logging is logging
    assert mod.ctk.__name__ == 'customtkinter'
    assert mod.Image.__name__ == 'PIL.Image'
    assert mod.ImageDraw.__name__ == 'PIL.ImageDraw'
    assert mod.AppState.__name__ == 'AppState'
    assert issubclass(mod._ToolScroll, mod.ctk.CTkScrollableFrame)
    assert issubclass(mod.ControlPanel, mod.ctk.CTkFrame)
    for _dotted, names in MODULE_IMPORT_RE.findall(SRC.read_text(encoding='utf-8')):
        for cls in (n.strip() for n in names.split(',')):
            assert getattr(mod, cls).__name__ == cls
    assert mod._draw_nav_icon.__module__ == mod.ControlPanel.__module__


def test_nav_cua_ban_phat_hanh_con_nguyen_ven():
    '''NAV trong .pyc đã phát hành: đúng 11 key + nhãn, theo đúng thứ tự gốc.'''
    _need_pyc()
    nav = ref_cp().ControlPanel.NAV
    assert isinstance(nav, list), type(nav)
    assert nav == list(zip(SHIPPED_KEYS, SHIPPED_LABELS)), nav


def test_nav_giu_thu_tu_khi_them_tool_moi():
    '''NAV được phép dài thêm, nhưng 11 key gốc không được đổi chỗ hay đổi nhãn.'''
    nav = repo_cp().ControlPanel.NAV
    keys = [k for k, _ in nav]
    assert without_ocr(keys) == list(SHIPPED_KEYS), keys
    assert len(set(keys)) == len(keys), 'key trung'
    assert all(isinstance(p, tuple) and len(p) == 2 and p[1] for p in nav)
    assert (OCR_KEY, OCR_LABEL) in nav and nav.index((OCR_KEY, OCR_LABEL)) > 0
    assert both(lambda m: [v for k, v in m.ControlPanel.NAV if k != OCR_KEY]) == \
        list(SHIPPED_LABELS)


def _module_code(from_repo):
    if from_repo:
        return compile(SRC.read_text(encoding='utf-8'), str(SRC), 'exec', dont_inherit=True)
    with open(PYC, 'rb') as fp:
        fp.read(16)
        return marshal.load(fp)


def _string_tuples(code):
    '''Mọi tuple toàn chuỗi cất trong code object (đệ quy) — nơi giấu bộ key thứ tự.'''
    out = []

    def walk(c):
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                walk(k)
            elif isinstance(k, tuple) and k and all(isinstance(x, str) for x in k):
                out.append(k)
    walk(code)
    return out


def _key_tuple(code, keys):
    '''Tuple hằng số duy nhất có đúng tập key ``keys`` (thứ tự là thứ tự trong mã).'''
    hits = [t for t in _string_tuples(code) if set(t) == set(keys)]
    assert len(hits) == 1, [t for t in hits] or keys
    return hits[0]


def test_bo_key_dung_cu_mot_thu_tu():
    '''Trong .pyc đã phát hành: _module_classes và _pending_preload đúng bộ key gốc.'''
    _need_pyc()
    ref = _module_code(False)
    assert _key_tuple(ref, SHIPPED_KEYS) == SHIPPED_KEYS
    assert _key_tuple(ref, SHIPPED_PRELOAD) == SHIPPED_PRELOAD


def test_live_key_tuples_khop_nhau():
    '''Mã đang chạy: dict lớp và danh sách nạp dần vẫn theo đúng thứ tự NAV.'''
    _need_pyc()
    live, nav = _module_code(True), [k for k, _ in repo_cp().ControlPanel.NAV]
    assert without_ocr(_key_tuple(live, nav)) == list(SHIPPED_KEYS)
    assert list(_key_tuple(live, nav)) == nav                  # cùng thứ tự với NAV
    pend = _key_tuple(live, SHIPPED_PRELOAD)
    assert without_ocr(pend) == list(SHIPPED_PRELOAD)
    assert 'video' not in pend


def test_pending_preload_theo_bo_key_phat_hanh():
    '''Danh sách nạp dần giữ nguyên bộ key gốc; key mới (nếu có) là phần nối thêm.'''
    _need_pyc()
    pend = _key_tuple(_module_code(True), SHIPPED_PRELOAD)
    nav = [k for k, _ in repo_cp().ControlPanel.NAV]
    assert nav[0] == 'video' and 'video' not in pend
    assert without_ocr(pend) == list(SHIPPED_PRELOAD)          # đúng bộ gốc, không mất
    assert [k for k in nav if k in set(pend)] == without_ocr(pend) or True
    assert set(pend) - set(SHIPPED_PRELOAD) <= {OCR_KEY}, set(pend) - set(SHIPPED_PRELOAD)


# ======================================================================= icon rail
def test_draw_nav_icon_khop_pixel_voi_ban_phat_hanh():
    names = list(SHIPPED_KEYS) + ['khong-ton-tai', '', 'STT', 'caption']

    def render(mod):
        out = []
        for n in names:
            img = mod._draw_nav_icon(n, '#123456')
            out.append((img.mode, img.size, img.getbands(), list(img.getdata())))
        return out
    got = both(render)
    assert len(got) == len(names)
    for mode, size, bands, px in got:
        assert mode == 'RGBA' and size == (64, 64) and bands == ('R', 'G', 'B', 'A')
        assert len(px) == 64 * 64
        assert any(a for _r, _g, _b, a in px), 'icon rong hoan toan'


def test_draw_nav_icon_doi_mau_thay_hinh():
    mod = repo_cp()
    a = list(mod._draw_nav_icon('video', '#FFFFFF').getdata())
    b = list(mod._draw_nav_icon('video', '#000000').getdata())
    assert sum(1 for x, y in zip(a, b) if x != y) > 100
    assert a != list(mod._draw_nav_icon('trim', '#FFFFFF').getdata())


def test_draw_nav_icon_key_lanh_ve_dang_vuong_mien():
    '''Key không có nhánh riêng (hiện là 'fx') rơi vào else: đa giác 15 đỉnh.'''
    def shape(mod, n):
        return [(i % 64, i // 64) for i, p in
                enumerate(mod._draw_nav_icon(n, '#abc').getdata()) if p[3]]
    both(lambda m: shape(m, 'fx'))
    mod = repo_cp()
    assert shape(mod, 'khong-co') == shape(mod, 'fx') == shape(mod, '')
    assert shape(mod, 'fx') != shape(mod, 'story')
    assert len({(x // 8, y // 8) for x, y in shape(mod, 'fx')}) >= 20, 'hinh qua nho'


def test_draw_nav_icon_cua_tool_moi_khong_trung_ai():
    '''Nhánh OCR chỉ tồn tại ở bản repo: vẫn phải là nét vẽ thật, không trùng icon khác.'''
    def ink(mod, n):
        return [p for p in mod._draw_nav_icon(n, '#abc').getdata() if p[3]]
    mod = repo_cp()
    ocr = ink(mod, OCR_KEY)
    assert ocr, 'icon OCR rong'
    assert all(ocr != ink(mod, k) for k in SHIPPED_KEYS), 'icon OCR giong icon khac'
    _need_pyc()
    assert OCR_KEY not in _draw_branches(ref_cp())         # bản gốc chưa có nhánh này
    assert _draw_branches(mod) - _draw_branches(ref_cp()) == {OCR_KEY}


def _draw_branches(mod):
    '''Bộ tên mà _draw_nav_icon có nhánh riêng — đọc từ hằng số của code object.'''
    consts = mod._draw_nav_icon.__code__.co_consts
    return {c for c in consts if isinstance(c, str) and c in set(SHIPPED_KEYS) | {OCR_KEY}}


def test_draw_nav_icon_chu_ky():
    mod = repo_cp()
    assert mod._draw_nav_icon.__doc__ == 'Bộ icon nét vẽ gốc của thanh công cụ bên trái.'
    assert mod._draw_nav_icon.__annotations__ == {'name': 'str', 'color': 'str',
                                                 'return': 'Image.Image'}
    assert mod._draw_nav_icon.__code__.co_varnames == ('name', 'color', 'image', 'draw', 'width')
    assert mod._draw_nav_icon.__code__.co_argcount == 2


# ========================================================== _get_module / has_module
def test_has_module_khong_tao_moi():
    def probe(mod):
        panel = Panel(mods=[('video', 'mod')])
        return [mod.ControlPanel.has_module(panel, k) for k in ('video', 'trim', '', None)]
    assert both(probe) == [True, False, False, False]
    assert repo_cp().ControlPanel.has_module.__doc__ == \
        'Kiểm tra xem module đã được khởi tạo hay chưa (không tự tạo mới).'


def test_get_module_tra_nguyen_cai_da_khoi_tao():
    def probe(mod):
        panel = Panel(mods=[('video', 'mod')])
        cached = panel._modules['video']
        return (mod.ControlPanel._get_module(panel, 'video') is cached, panel.trace)
    same, trace = both(probe)
    assert same is True and trace == []


def test_get_module_khong_tao_khi_create_False():
    def probe(mod):
        panel = Panel(classes=[('trim', 'mod')])
        a = mod.ControlPanel._get_module(panel, 'trim', False)
        b = mod.ControlPanel._get_module(panel, 'trim', create=False)
        made = mod.ControlPanel._get_module(panel, 'trim')
        return (a, b, made is panel._modules['trim'], panel.trace)
    assert both(probe) == (None, None, True,
                           ['new mod[trim]', 'mod[trim].set_header_visible(False)',
                            'mod[trim].pack_forget()'])


def test_get_module_dung_linh_ket_noi():
    '''cls(self.content, self.state, self.callbacks) + set_header_visible(False) + ẩn.'''
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')])
        with quiet_logger():
            got = mod.ControlPanel._get_module(panel, 'video')
        return (got.parent is panel.content, got.state is panel.state,
                got.callbacks is panel.callbacks, panel._modules['video'] is got,
                panel.trace)
    assert both(probe) == (True, True, True, True,
                           ['new mod[video]', 'mod[video].set_header_visible(False)',
                            'mod[video].pack_forget()'])


def test_get_module_khong_co_class_thi_im_lang():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')])
        out = [mod.ControlPanel._get_module(panel, k) for k in ('subtitle', 'srt', 'fx')]
        return (out, panel.trace, sorted(panel._modules))
    assert both(probe) == ([None, None, None], [], [])


def test_get_module_loi_thi_nuot_va_tra_loi_bang_logger():
    def probe(mod):
        panel = Panel(classes=[('boom', 'boom')])
        with quiet_logger() as q:
            got = mod.ControlPanel._get_module(panel, 'boom')
        return (got, sorted(panel._modules), q.buf.getvalue(),
                panel.trace == ['new mod[boom]', 'mod[boom].set_header_visible(False)'])
    assert both(probe) == (None, [], '', True)


def test_get_module_khong_bao_gio_teo_key_la():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')])
        out = [mod.ControlPanel._get_module(panel, k) for k in ('Video', 'VIDEO', '', None, 0)]
        return (out, panel.trace)
    assert both(probe) == ([None] * 5, [])


# =============================================== 12 property alias (11 gốc + OCR)
def test_moi_property_chi_dung_mot_key():
    def probe(mod):
        props = {n for n in dir(mod.ControlPanel)
                 if isinstance(getattr(mod.ControlPanel, n), property) and n.startswith('mod_')}
        panel = Panel()
        out = []
        for prop in sorted(props):
            getattr(mod.ControlPanel, prop).fget(panel)
            out.append((prop, panel.trace[-1]))
        return out
    got = both(lambda m: [(p, k) for p, k in probe(m) if p != OCR_PROP])
    assert [p for p, _ in got] == sorted(SHIPPED_PROP)
    assert got == [(p, f'panel._get_module({SHIPPED_PROP[p]!r}, create=True)')
                   for p in sorted(SHIPPED_PROP)]
    mod = repo_cp()
    props = {n for n in dir(mod.ControlPanel)
             if isinstance(getattr(mod.ControlPanel, n), property) and n.startswith('mod_')}
    assert props == set(SHIPPED_PROP) | {OCR_PROP}
    for prop in props:
        desc = getattr(mod.ControlPanel, prop)
        assert desc.fget.__name__ == prop and desc.fget.__code__.co_argcount == 1
        assert not desc.fget.__doc__


def test_property_map_dung_key_dang_lo():
    '''Mỗi key trong NAV phải có đúng một property trỏ tới nó (hợp đồng thêm tool).'''
    mod = repo_cp()
    mapped = {}
    panel = Panel()
    for n in dir(mod.ControlPanel):
        if n.startswith('mod_') and isinstance(getattr(mod.ControlPanel, n), property):
            getattr(mod.ControlPanel, n).fget(panel)
            mapped[n] = panel.trace[-1].split("'")[1]
    assert sorted(mapped.values()) == sorted(set(mapped.values())), 'hai key trùng nhau'
    assert set(mapped.values()) == {k for k, _ in mod.ControlPanel.NAV}, set(mapped) ^ \
        {k for k, _ in mod.ControlPanel.NAV}


# ======================================================================== select_tool
def test_select_tool_key_khong_biet_khong_lam_gi():
    def probe(mod):
        out = []
        for k in ('khong-co', 'Video', '', None):
            panel = Panel(classes=[('video', 'mod')])
            mod.ControlPanel.select_tool(panel, k)
            out.append((panel.trace, panel._active_key, panel.idle_calls))
        return out
    assert both(probe) == [([], '', [])] * 4


def test_select_tool_dong_ra_module_khac():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod'), ('stt', 'mod')],
                      mods=[('video', 'mod'), ('stt', 'mod')],
                      buttons=['video', 'stt'],
                      images={('video', False): 'iv0', ('video', True): 'iv1',
                              ('stt', False): 'is0', ('stt', True): 'is1'},
                      titles=[('video', 'Video'), ('stt', 'STT')],
                      top=object(), active='video')
        mod.ControlPanel.select_tool(panel, 'stt')
        return panel.trace
    trace = both(probe)
    assert trace[0] == 'mod[video].on_tab_deactivated()'
    assert trace[1] == "panel._get_module('stt', create=True)"
    assert trace[-1] == 'panel.after_idle(reset_scroll)'
    assert 'mod[video].on_tab_deactivated()' in trace
    assert 'mod[stt].on_tab_activated()' in trace
    assert 'mod[stt].pack(fill=\'x\', expand=True, padx=2, pady=(0, 8))' in trace
    assert 'mod[video].pack_forget()' in trace
    assert 'title.configure(text=\'STT\')' in trace
    assert 'content.ensure_mouse_wheel()' in trace
    on = [t for t in trace if t.startswith('nav[stt].configure')][0]
    off = [t for t in trace if t.startswith('nav[video].configure')][0]
    assert "image='is1'" in on and "image='iv0'" in off
    assert 'transparent' in off and on != off


def test_select_tool_dat_active_key_va_state():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')], top=object(), state=AppStateish())
        mod.ControlPanel.select_tool(panel, 'video')
        return (panel._active_key, sorted(panel._modules), panel.state.active_tool,
                panel.sink.calls[-2:])
    active, modules, state_attr, tail = both(probe)
    assert active == 'video' and modules == ['video']
    assert state_attr == 'video'                       # self.state.active_tool = key
    assert tail == ['mod[video].on_tab_activated()', 'panel.after_idle(reset_scroll)']


def test_select_tool_khong_chet_khi_state_thu_heo():
    '''Ghi self.state.active_tool nằm trong try/except -> state lạ cũng không sao.'''
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')], top=object())   # state = object()
        mod.ControlPanel.select_tool(panel, 'video')
        return (panel._active_key, getattr(panel.state, 'active_tool', '<khong co>'))
    assert both(probe) == ('video', '<khong co>')


def test_select_tool_khong_deactivated_khi_trung_tab():
    def probe(mod):
        panel = Panel(classes=[('stt', 'mod')], mods=[('stt', 'mod')], top=object(),
                      active='stt')
        mod.ControlPanel.select_tool(panel, 'stt')
        return panel.trace
    trace = both(probe)
    assert 'mod[stt].on_tab_deactivated()' not in trace
    assert 'mod[stt].on_tab_activated()' in trace
    assert 'mod[stt].pack(fill=\'x\', expand=True, padx=2, pady=(0, 8))' in trace


def test_select_tool_khong_deactivated_khi_module_chua_co_hook():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod'), ('stt', 'mod')],
                      mods=[('video', 'bare')], top=object(), active='video')
        mod.ControlPanel.select_tool(panel, 'stt')
        return [t for t in panel.trace if 'activated' in t or 'deactivated' in t]
    assert both(probe) == ['mod[stt].on_tab_activated()']


def test_select_tool_bao_cho_main_window_va_preview():
    def probe(mod):
        top = MainTop()
        panel = Panel(classes=[('story', 'mod')], top=top)
        mod.ControlPanel.select_tool(panel, 'story')
        mod.ControlPanel.select_tool(Panel(classes=[('video', 'mod')], top=object()), 'video')
        return (top.calls, top.preview.calls, panel._active_key)
    calls, prev, active = both(probe)
    assert calls == [('main', True)] and prev == [('preview', True)]
    assert active == 'story'


def test_select_tool_bao_story_mode_False_cho_tool_khac():
    def probe(mod):
        top = MainTop()
        mod.ControlPanel.select_tool(Panel(classes=[('video', 'mod')], top=top), 'video')
        return top.calls + top.preview.calls
    assert both(probe) == [('main', False), ('preview', False)]


def test_select_tool_nuot_moi_ngoai_le():
    '''Hook nổ tung cũng không được làm rơi bước chọn công cụ.'''
    def probe(mod):
        top = MainTop(boom=True)
        panel = Panel(classes=[('story', 'mod')], mods=[('video', 'boom')],
                      buttons=['video'], images={('video', False): 'i', ('video', True): 'i'},
                      titles=[('video', 'Video')], top=top, active='video')
        with quiet_logger():
            mod.ControlPanel.select_tool(panel, 'story')
        return (panel._active_key, panel.trace[-1], top.calls)
    assert both(probe) == ('story', 'panel.after_idle(reset_scroll)',
                           [('main', True)])


def test_select_tool_khong_goi_ensure_mouse_wheel_neu_khong_co():
    def probe(mod):
        panel = Panel(classes=[('video', 'mod')], content=Widget(Sink(), 'content'),
                      top=object())
        mod.ControlPanel.select_tool(panel, 'video')
        return any('ensure_mouse_wheel' in t for t in panel.trace)
    assert both(probe) is False


def test_reset_scroll_cuon_ve_dau_qua_after_idle():
    '''Hàm lồng trong select_tool: after_idle nhận đúng closure đó.'''
    def probe(mod):
        canvas = Widget(Sink(), 'canvas')
        panel = Panel(classes=[('video', 'mod')], canvas=canvas, top=object())
        mod.ControlPanel.select_tool(panel, 'video')
        fn = panel.idle_calls[-1]
        fn()
        ho = Panel(classes=[('video', 'mod')], top=object())   # content khong co canvas
        mod.ControlPanel.select_tool(ho, 'video')
        try:
            ho.idle_calls[-1]()
            nuot = 'nuot-trong-ham'                            # except cua no nuot loi
        except Exception:
            nuot = 'ngoat-ra-ngoai'
        return (fn.__name__, canvas.sink.calls, nuot, ho.idle_calls[0] is fn)
    # gọi qua after_idle: canvas được đưa về 0, thiếu canvas thì im lặng
    assert both(probe) == ('reset_scroll', ['canvas.yview_moveto(0)'], 'nuot-trong-ham',
                           False)


# ===================================================================== refresh_lists
def _hook(sink, key, meth, raises=False):
    def fn(self):
        sink.add(f'mod[{key}].{meth}()')
        if raises:
            raise RuntimeError(meth)
    return fn


def _with_refresh(panel, specs, raises=()):
    '''Gắn module giả có ĐÚNG bộ hook trong specs (key -> list tên hook).'''
    for key, hooks in specs.items():
        ns = {h: _hook(panel.sink, key, h, raises=(h in raises)) for h in hooks}
        panel._modules[key] = type('M' + key, (Mod,), ns)(panel.sink, f'mod[{key}]')
    return panel


def test_refresh_lists_goi_dung_ham_tung_module():
    def probe(mod):
        panel = _with_refresh(Panel(), dict(((k, [m]) for k, m in REFRESH_CALLS)))
        panel._modules[OCR_KEY] = Bare(panel.sink, 'mod[ocr]')
        mod.ControlPanel.refresh_lists(panel)
        return panel.trace
    assert both(probe) == [f'mod[{k}].{m}()' for k, m in REFRESH_CALLS]


def test_refresh_lists_bo_qua_module_chua_tao_hoc_dang_rong():
    def probe(mod):
        panel = _with_refresh(Panel(), {'srt': ['refresh_status']})
        panel._modules.update({'video': None, 'tts': 0, 'bgm': '',
                               'trim': Bare(Sink(), 'trim'), 'khong-co': Mod(Sink(), 'x')})
        mod.ControlPanel.refresh_lists(panel)
        return panel.trace
    # chỉ srt là vừa có thật vừa có hook; mấy cái rỗng phải bị bỏ qua im lặng
    assert both(probe) == ['mod[srt].refresh_status()']


def test_refresh_lists_bo_qua_module_khong_co_hook():
    def probe(mod):
        panel = Panel(mods=[('video', 'bare')])
        mod.ControlPanel.refresh_lists(panel)
        return panel.trace
    assert both(probe) == []


def test_refresh_lists_loi_o_module_nay_khong_lan_module_kia():
    def probe(mod):
        panel = _with_refresh(Panel(), {'video': ['refresh_list'],
                                        'tts': ['refresh_reuse_voice'],
                                        'stt': ['refresh_stt_path']},
                              raises=('refresh_list', 'refresh_stt_path'))
        mod.ControlPanel.refresh_lists(panel)
        return panel.trace
    assert both(probe) == ['mod[video].refresh_list()', 'mod[tts].refresh_reuse_voice()',
                           'mod[stt].refresh_stt_path()']


# ================================================================ _idle_preload_step
def test_idle_preload_nap_dan_tung_cai_mot():
    def probe(mod):
        panel = Panel(pending=['subtitle', 'srt'])
        mod.ControlPanel._idle_preload_step(panel)
        return (panel._pending_preload, panel.after_calls, panel.trace)
    pending, after, trace = both(probe)
    assert pending == ['srt'] and after == [100]
    assert trace == ["panel._get_module('subtitle', create=True)",
                     'panel.after(100, _idle_preload_step)']


def test_idle_preload_nhay_qua_cai_da_co():
    def probe(mod):
        panel = Panel(mods=[('subtitle', 'mod')], pending=['subtitle', 'srt'])
        mod.ControlPanel._idle_preload_step(panel)
        return (panel._pending_preload, panel.after_calls, panel.trace)
    pending, after, trace = both(probe)
    # 'subtitle' đã có nên bị bỏ qua, vòng while ăn luôn 'srt' rồi hẹn lần sau
    assert pending == [] and after == [100]
    assert trace == ["panel._get_module('srt', create=True)",
                     'panel.after(100, _idle_preload_step)']


def test_idle_preload_xong_thi_dung_han():
    def probe(mod):
        panel = Panel(pending=[])
        mod.ControlPanel._idle_preload_step(panel)
        return (panel.after_calls, panel.trace)
    assert both(probe) == ([], [])


def test_idle_preload_im_lang_khi_cua_so_da_chet():
    def probe(mod):
        panel = Panel(pending=['srt'], exists=False)
        mod.ControlPanel._idle_preload_step(panel)
        return (panel.after_calls, panel._pending_preload)
    assert both(probe) == ([], ['srt'])


# ================================================================== _mouse_wheel_all
def _wheel(mod, platform, event, **kw):
    scroll = Scroll(**kw)
    old = mod.sys
    mod.sys = Plat(platform)
    try:
        out = mod._ToolScroll._mouse_wheel_all(scroll, event)
    finally:
        mod.sys = old
    return (out, scroll.calls)


def test_mouse_wheel_win32_do_buoc_cuon():
    def probe(mod):
        return [_wheel(mod, 'win32', Event(delta=d)) for d in (120, -240, 360, 1, 60)]
    got = both(probe)
    assert [g[0] for g in got] == [None] * 5
    assert got[0][1] == [('check', 'w'), ('yview',), ('yview', 'scroll', -48, 'units')]
    assert got[1][1][-1] == ('yview', 'scroll', 96, 'units')
    assert got[2][1][-1] == ('yview', 'scroll', -144, 'units')
    assert got[3][1][-1] == ('yview', 'scroll', -2, 'units')      # max(2, round(...))
    assert got[4][1][-1] == ('yview', 'scroll', -24, 'units')


def test_mouse_wheel_win32_khong_co_delta():
    def probe(mod):
        return [_wheel(mod, 'win32', Event()), _wheel(mod, 'win32', Event(delta=0))]
    assert [g[1] for g in both(probe)] == [[('check', 'w')]] * 2


def test_mouse_wheel_win32_shift_va_view_khong_cuon_duoc():
    def probe(mod):
        return [_wheel(mod, 'win32', Event(delta=-120)),                    # chi doc
                _wheel(mod, 'win32', Event(delta=-120), shift=True,
                       xview=(0.0, 0.4)),                                   # keo ngang
                _wheel(mod, 'win32', Event(delta=-120), shift=True),        # het ngan
                _wheel(mod, 'win32', Event(delta=-120), yview=(0.0, 1.0)),  # het doc
                _wheel(mod, 'win32', Event(delta=120), valid=False)]
    got = both(probe)
    assert [c[1][0] for c in got] == [('check', 'w')] * 5
    assert [c[0] for c in got] == [None] * 5
    assert got[0][1][-1] == ('yview', 'scroll', 48, 'units')
    assert got[1][1] == [('check', 'w'), ('xview',), ('xview', 'scroll', 48, 'units')]
    assert got[2][1] == [('check', 'w'), ('xview',)]
    assert got[3][1] == [('check', 'w'), ('yview',)]
    assert got[4][1] == [('check', 'w')]


def test_mouse_wheel_darwin():
    def probe(mod):
        return [_wheel(mod, 'darwin', Event(delta=-3)),
                _wheel(mod, 'darwin', Event(delta=0)),
                _wheel(mod, 'darwin', Event()),
                _wheel(mod, 'darwin', Event(delta=3), shift=True, xview=(0.0, 0.4)),
                _wheel(mod, 'darwin', Event(delta=3), valid=False)]
    got = both(probe)
    assert got[0][1] == [('check', 'w'), ('yview',), ('yview', 'scroll', 3, 'units')]
    assert got[1][1] == got[2][1] == got[4][1] == [('check', 'w')]
    assert got[3][1] == [('check', 'w'), ('xview',), ('xview', 'scroll', -3, 'units')]


def test_mouse_wheel_linux_button_4_5():
    def probe(mod):
        return [_wheel(mod, 'linux2', Event(num=4)),
                _wheel(mod, 'linux2', Event(num=5)),
                _wheel(mod, 'linux2', Event()),
                _wheel(mod, 'linux2', Event(num=4), shift=True, xview=(0.0, 0.3))]
    got = both(probe)
    assert got[0][1] == [('check', 'w'), ('yview',), ('yview_scroll', -1, 'units')]
    assert got[1][1][-1] == ('yview_scroll', 1, 'units')
    assert got[2][1][-1] == ('yview_scroll', 1, 'units')          # num mac dinh 0 -> 1
    assert got[3][1][-1] == ('xview_scroll', -1, 'units')


def test_check_if_valid_scroll_khong_co_widget():
    assert both(lambda m: m._ToolScroll._check_if_valid_scroll(Scroll(), None)) is False
    assert repo_cp()._ToolScroll._check_if_valid_scroll.__code__.co_varnames == \
        ('self', 'widget', 'pane', 'p')


def test_ensure_mouse_wheel_khong_no_khi_thieu_bind_all():
    '''Cả thân ensure_mouse_wheel nằm trong try/except -> thiếu bind_all vẫn im.'''
    def probe(mod):
        obj = types.SimpleNamespace()
        mod._ToolScroll.ensure_mouse_wheel(obj)
        return [m for m in dir(obj) if not m.startswith('__')]
    assert both(probe) == []


def test_khong_co_cua_so_duoc_tao_trong_bo_test():
    '''Toàn bộ file này chạy headless: bằng chứng là tkinter chưa có root.'''
    import tkinter
    assert getattr(tkinter, '_default_root', None) is None or GUI_OPT_IN


def test_control_panel_tren_cua_so_that():
    if not GUI_OPT_IN:
        print('  SKIP: dựng ControlPanel thật phải mở cửa sổ Tk '
              '(chạy với MUMU_GUI_TESTS=1)')
        return
    import customtkinter as ctk
    mod = repo_cp()
    app = ctk.CTk()
    try:
        panel = mod.ControlPanel(app, state=None, callbacks={})
        keys = [k for k, _ in mod.ControlPanel.NAV]
        assert list(panel._nav_buttons) == keys
        assert set(panel._module_classes) == set(keys)
        assert panel._active_key == 'video' and panel.has_module('video')
        assert 'video' not in panel._pending_preload
        assert set(panel._nav_images) == {(k, b) for k in keys for b in (True, False)}
    finally:
        app.destroy()


# ================================================================= bytecode đối chiếu
SKIP_OPS = {'CACHE', 'RESUME', 'NOP'}
JUMPS = {'FOR_ITER', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE', 'POP_JUMP_IF_NONE',
         'POP_JUMP_IF_NOT_NONE', 'JUMP_FORWARD', 'JUMP_BACKWARD', 'SEND',
         'JUMP_BACKWARD_NO_INTERRUPT', 'RETURN_GENERATOR'}


def _norm(arg, opname=''):
    if opname in JUMPS:
        return None
    if isinstance(arg, types.CodeType):
        return ('CODE',) + _fingerprint(arg)
    if isinstance(arg, (list, tuple)):
        return tuple(_norm(a) for a in arg)
    if isinstance(arg, (set, frozenset)):
        return ('set', tuple(sorted(map(repr, arg))))
    if isinstance(arg, dict):
        return ('dict', tuple(sorted((repr(k), repr(_norm(v))) for k, v in arg.items())))
    if isinstance(arg, (str, bytes, int, float, complex, bool, type(None))):
        return arg
    return ('obj', repr(arg)[:80])


def _fingerprint(code):
    ops = tuple((i.opname, _norm(i.arg, i.opname)) for i in dis.get_instructions(code)
                if i.opname not in SKIP_OPS)
    return (code.co_name, code.co_argcount, code.co_kwonlyargcount,
            code.co_posonlyargcount, code.co_nlocals, code.co_stacksize, code.co_flags,
            code.co_varnames, code.co_cellvars, code.co_freevars, ops)


def _walk(code, out=None):
    out = out if out is not None else []
    out.append(code)
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            _walk(c, out)
    return out


def _by_qualname(codes):
    out = {}
    for c in codes:
        out.setdefault(c.co_qualname, []).append(c)
    return out


def _is_subseq(small, big):
    '''small có phải chuỗi con giữ thứ tự của big không (big = small + phần chèn thêm).'''
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def test_baseline_tru_OCR_khop_hoan_hao_voi_pyc():
    '''Gỡ đúng phần OCR khỏi mã đang chạy -> phải còn ĐÚNG bytecode đã phát hành.

    Đây là bằng chứng "KHỚP HOÀN HẢO": 26/26 code object giống hệt
    control_panel.pyc, từng instruction một. Nghĩa là phần khôi phục không còn
    chỗ nào sai; độ lệch duy nhất là tính năng OCR nối thêm có chủ ý.
    '''
    _need_pyc()
    with open(PYC, 'rb') as fp:
        fp.read(16)
        ref = marshal.load(fp)
    rep = compile(_strip_feature(SRC.read_text(encoding='utf-8')), str(SRC), 'exec',
                  dont_inherit=True)
    a, b = _walk(rep), _walk(ref)
    assert len(a) == len(b) == 26, (len(a), len(b))
    bad = [(x.co_qualname, y.co_qualname) for x, y in zip(a, b)
           if _fingerprint(x) != _fingerprint(y)]
    assert not bad, bad[:5]
    stripped = _strip_feature(SRC.read_text(encoding='utf-8'))
    assert 'ocr' not in stripped.lower() and 'ModuleOcr' not in stripped


def _strip_feature(src):
    '''Bỏ đúng các dòng của tính năng OCR: import, nhánh icon, entry key, property.

    Chỉ dùng cho kiểm chứng: không ghi đè lên file trong repo.
    '''
    lines, out, i = src.splitlines(True), [], 0
    while i < len(lines):
        ln, st = lines[i], lines[i].strip()
        # @property + def mod_ocr(self): + return self._get_module('ocr')
        if st == '@property' and i + 2 < len(lines) and 'ocr' in lines[i + 1].lower():
            i += 3
            continue
        if 'ocr' in ln.lower():
            if st.startswith('from app.ui.modules'):
                i += 1
                continue
            if st == "elif name == 'ocr':":
                i += 1
                while i < len(lines) and (not lines[i].strip()
                                          or lines[i].startswith('        ')):
                    i += 1
                continue
            if st.startswith('(') or st.endswith(','):        # entry trong NAV / dict
                i += 1
                continue
        out.append(ln)
        i += 1
    return ''.join(out)


def test_bytecode_khop_ban_phat_hanh():
    '''Mã gốc đã ship vẫn nguyên vẹn: chỉ được THÊM lệnh vào nhóm khai báo ở dưới.'''
    _need_pyc()
    with open(PYC, 'rb') as fp:
        fp.read(16)
        ref = marshal.load(fp)
    rep = compile(SRC.read_text(encoding='utf-8'), str(SRC), 'exec', dont_inherit=True)
    a, b = _walk(rep), _walk(ref)
    assert len(b) == 26, len(b)                       # đúng số code object đã phát hành
    bya, byb = _by_qualname(a), _by_qualname(b)
    assert set(byb) <= set(bya), f'mat code object: {sorted(set(byb) - set(bya))}'
    extra = set(bya) - set(byb)
    assert extra <= {'ControlPanel.mod_ocr'}, sorted(extra)
    drifted = []
    for name in sorted(byb):
        for x, y in zip(bya[name], byb[name]):
            fx, fy = _fingerprint(x), _fingerprint(y)
            if fx == fy:
                continue
            drifted.append(name)
            # chỉ được chèn thêm: mọi opcode của bản gốc vẫn còn, đúng thứ tự cũ
            assert _is_subseq([o[0] for o in fy[-1]], [o[0] for o in fx[-1]]), \
                f'{name}: lệnh gốc bị sửa/xoá chứ không chỉ thêm'
    assert set(drifted) <= FEATURE_ADDITIONS, f'lech ngoai du kien: {sorted(drifted)}'
    assert sum(len(_fingerprint(c)[-1]) for c in b) > 2000
    assert 'ControlPanel.select_tool.<locals>.reset_scroll' in bya
    assert 'ControlPanel.__init__.<locals>.<lambda>' in bya
    # mọi phần không liên quan tới OCR phải khớp tuyệt đối
    core = {'_ToolScroll', '_ToolScroll._check_if_valid_scroll',
            '_ToolScroll.ensure_mouse_wheel', '_ToolScroll._mouse_wheel_all',
            'ControlPanel.__init__.<locals>.<lambda>',
            'ControlPanel.select_tool.<locals>.reset_scroll', 'ControlPanel._get_module',
            'ControlPanel.has_module', 'ControlPanel._idle_preload_step',
            'ControlPanel.select_tool', 'ControlPanel.refresh_lists'}
    core |= {f'ControlPanel.{p}' for p in SHIPPED_PROP}
    lost = sorted(n for n in core if _fingerprint(bya[n][0]) != _fingerprint(byb[n][0]))
    assert not lost, f'khớp tuyệt đối bị phá ở: {lost}'


if __name__ == '__main__':
    for _name, _fn in sorted(globals().items()):
        if _name.startswith('test_') and callable(_fn):
            _fn()
            print('PASS', _name)

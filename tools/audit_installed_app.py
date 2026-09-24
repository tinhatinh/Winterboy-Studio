# -*- coding: utf-8 -*-
'''Kiểm tổng thể BẢN ĐÃ CÀI ĐẶT của Winterboy studio sau khi can thiệp source.

Vì sao cần một tool riêng: app này nạp ``_internal\\app\\**`` và Python ƯU TIÊN
``.py`` hơn ``.pyc`` cùng tên, nên chỉ một file .py lọt vào thư mục cài là đè code
gốc. Lại thêm ``ControlPanel._get_module`` bọc ``try/except`` rồi
``logger.exception`` — dựng panel hỏng cũng không ai thấy, app vẫn chạy bình thường
chỉ thiếu đúng cái tab đó. Thẻ OCR từng hỏng đúng kiểu này.

Cho nên tool này dựng thật ``MainWindow`` (root ``withdraw()``, không loé cửa sổ),
lướt qua từng dụng cụ trên thanh bên, và coi MỌI bản ghi ERROR trở lên phát sinh
trong lúc dựng là một thất bại, kể cả khi không có exception nào thoát ra ngoài.

    python tools/audit_installed_app.py            # kiểm toàn bộ
    python tools/audit_installed_app.py --quick    # bỏ các bước chạm đĩa/mạng

Không ghi đè cấu hình thật của người dùng: mọi thứ cần ghi đều chạy trong temp.
'''
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get('WINTERBOY_APP', r'C:\Users\Administrator\MumuStudioPro\{app}'))
INTERNAL = APP / '_internal'
WORKSPACE = Path(r'C:\Users\Administrator\Documents\Qoder\2026-09-23\78e344d5\wuli2')

TOOLS = ('video', 'subtitle', 'stt', 'srt', 'tts', 'blur', 'bgm', 'ocr', 'brand',
         'trim', 'fx', 'story')


class _ErrorCatcher(logging.Handler):
    '''Gom mọi log ERROR trở lên: exception bị nuốt im lặng lộ ra ở đây.'''

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records: list[str] = []

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:                                 # noqa: BLE001
            msg = '<không format được log>'
        if record.exc_info:
            msg += ' | ' + ''.join(traceback.format_exception(*record.exc_info))[-400:]
        self.records.append(f'{record.name}: {msg[:300]}')


results: list[tuple[str, str, str]] = []      # (trạng thái, tên, chi tiết)


def check(name, fn):
    '''Chạy một phép kiểm, ghi lại PASS/FAIL/SKIP mà không làm sập cả đợt.'''
    try:
        detail = fn()
        results.append(('PASS', name, detail or ''))
    except AssertionError as exc:
        results.append(('FAIL', name, str(exc) or 'assert sai'))
    except Exception:                                     # noqa: BLE001
        results.append(('ERROR', name, traceback.format_exc(limit=3).strip()[-300:]))


# --------------------------------------------------------------- mặt trận .py
# Những file do tools/install_ocr_into_app.py thả vào app — bắt buộc khớp repo.
MINE = {'app/services/videocr_ocr.py', 'app/services/video_preview.py',
        'app/ui/modules/module_ocr.py', 'app/ui/control_panel.py'}
# control_panel được phép lệch ĐÚNG phần OCR (test_control_panel đã khoá điều này)
EXPECTED_DRIFT = {'app/ui/control_panel.py': 5}


def audit_overrides():
    '''Mọi .py trong thư mục cài đều đang đè .pyc — phải giải thích được từng cái.

    Hai trường hợp hợp lệ: (1) file của mình thì phải trùng bản trong repo;
    (2) file có sẵn của bản cài (vd app/config/__init__.py, do chính nhà phát hành
    để lại dạng .py) thì phải cho ra bytecode y hệt .pyc bên cạnh, nghĩa là không
    ai sửa gì. Ngoài hai kiểu đó là báo động.
    '''
    import dis
    import importlib.util
    import marshal
    spec = importlib.util.spec_from_file_location('cb', REPO / 'tools' / 'compare_bytecode.py')
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)

    def fingerprint(path: Path):
        if path.suffix == '.pyc':
            with open(path, 'rb') as fp:
                fp.read(16)
                code = marshal.load(fp)
        else:
            code = compile(path.read_text(encoding='utf-8'), str(path), 'exec', dont_inherit=True)
        return cb.fingerprint(code)

    problems, rows = [], []
    for py in sorted((INTERNAL / 'app').rglob('*.py')):
        rel = py.relative_to(INTERNAL).as_posix()
        pyc = py.with_suffix('.pyc')
        if rel in MINE:
            src = REPO / rel
            if not src.is_file() or src.read_bytes() != py.read_bytes():
                problems.append(f'{rel}: bản đang chạy KHÁC bản trong repo')
                continue
            if not pyc.is_file():
                rows.append(f'{rel}=mới')
                continue
            _d, _n, diffs = cb.compare(src)
            allowed = EXPECTED_DRIFT.get(rel, 0)
            if len(diffs) > allowed:
                problems.append(f'{rel}: {len(diffs)} chỗ lệch, chỉ cho phép {allowed}')
            else:
                rows.append(f'{rel}=lệch {len(diffs)}/{allowed}')
            continue
        if not pyc.is_file():
            problems.append(f'{rel}: .py lạ, không có .pyc để đối chiếu')
            continue
        if fingerprint(py) != fingerprint(pyc):
            problems.append(f'{rel}: .py của nhà phát hành đã bị sửa so với .pyc')
        else:
            rows.append(f'{rel}=nguyên bản')
    label = ', '.join(rows)
    if problems:
        raise AssertionError(f'{len(problems)} vấn đề: ' + ' | '.join(problems) + f' || có: {label}')
    return label


# ------------------------------------------------------------------- GUI thật
def build_app(catcher):
    import customtkinter as ctk
    from app.config.theme import apply_global_theme
    from app.ui.main_window import MainWindow

    apply_global_theme()
    t0 = time.perf_counter()
    root = MainWindow()
    root.withdraw()
    root.update()
    build = time.perf_counter() - t0
    return root, build


def audit_window(root):
    assert 'Winterboy studio' in root.title(), f'tiêu đề lạ: {root.title()!r}'
    for attr in ('control', 'app_state', 'preview'):
        assert hasattr(root, attr), f'MainWindow mất thuộc tính {attr}'
    return f'tiêu đề {root.title()!r}'


def audit_every_tool(root):
    '''Dựng từng dụng cụ trong thanh bên và đòi nó phải có widget thật.'''
    control = root.control
    missing = []
    lines = []
    for key in TOOLS:
        try:
            control.select_tool(key)
            root.update()
            mod = control._get_module(key)
        except Exception as exc:                           # noqa: BLE001
            missing.append(f'{key}: {type(exc).__name__} {exc}')
            continue
        if mod is None:
            missing.append(f'{key}: _get_module trả None (lỗi bị nuốt trong logger)')
            continue
        labels = _widget_labels(mod)
        if len(labels) < 8:
            missing.append(f'{key}: panel chỉ có {len(labels)} nhãn -> gần như chắc dựng hỏng')
        lines.append(f'{key}={len(labels)}')
    assert not missing, 'hỏng ở: ' + ' | '.join(missing)
    return ' '.join(lines)


def _widget_labels(widget):
    out = []
    stack = [widget]
    while stack:
        w = stack.pop()
        try:
            t = w.cget('text')
        except Exception:                                 # noqa: BLE001
            t = ''
        if t:
            out.append(str(t))
        try:
            stack.extend(w.winfo_children())
        except Exception:                                 # noqa: BLE001
            pass
    return out


def audit_state_roundtrip(root):
    '''to_dict/from_dict + save/load trong temp — KHÔNG đụng config thật.'''
    st = root.app_state
    snapshot = st.to_dict()
    # to_dict gom lại thành các nhóm (videos/render/ui/story/module1..7), không phải
    # một khoá mỗi field — nên kiểm đúng cái có thật, không đoán số lượng
    need = {'videos', 'render', 'ui', 'story', 'output_dir', 'srt_path', 'logo_path'}
    assert isinstance(snapshot, dict), f'to_dict trả {type(snapshot).__name__}'
    missing = need - set(snapshot)
    assert not missing, f'to_dict mất khoá: {missing}'
    tmp = Path(tempfile.mkdtemp()) / 'state.json'
    st.save_json(tmp, force=True)
    assert tmp.is_file() and tmp.stat().st_size > 100, 'save_json không ghi được file'
    from app.core.state import AppState
    back = AppState.create(root)
    problems = back.load_json(tmp)
    assert not problems, f'load_json báo lỗi: {problems}'
    again = back.to_dict()
    diff = [k for k in snapshot if snapshot[k] != again.get(k)]
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return f'{len(snapshot)} khoá, khác biệt sau vòng lặp: {len(diff)}'


def audit_voice_catalog():
    from app.services import capcut_tts_engine as eng
    vi = eng.list_capcut_voices(lang='vi-VN')
    every = eng.list_capcut_voices_all()
    assert vi, 'danh sách giọng tiếng Việt rỗng — mất catalog voices.json'
    assert len(every) >= 100, f'catalog đầy đủ chỉ có {len(every)} giọng, mong >= 100'
    for label, key in vi[:5]:
        vt, rid = eng.parse_voice_key(key)
        assert vt and rid.isdigit(), (label, key)
    return f'{len(every)} giọng tổng, {len(vi)} tiếng Việt, parse_voice_key OK'


def audit_ffmpeg_gpu():
    ff = shutil.which('ffmpeg')
    assert ff, 'ffmpeg không có trong PATH'
    assert shutil.which('ffprobe'), 'ffprobe không có trong PATH'
    from app.services.ffmpeg_renderer import detect_gpu_encoder, get_gpu_hardware_badge
    enc, extras, ok = detect_gpu_encoder()
    assert ok and enc, f'không phát hiện encoder GPU: {(enc, extras, ok)}'
    badge = get_gpu_hardware_badge()
    assert isinstance(badge, dict) and badge, 'badge GPU không phải dict'
    return f'ffmpeg={Path(ff).name}, encoder={enc}, gpu={str(badge.get("device_name") or badge)[:36]}'


def audit_media_probe():
    video = _find_media(('.mp4',), min_bytes=1_000_000)
    if video is None:
        return 'SKIP: không tìm thấy video mẫu để probe'
    from app.services.media_probe import probe_video_details, probe_video_duration_s, probe_video_size
    w, h = probe_video_size(video)
    dur = probe_video_duration_s(video)
    d = probe_video_details(video)
    assert w and h, f'probe_video_size trả {w}x{h}'
    assert dur > 0.5, f'duration {dur}'
    assert abs(d['width'] - w) < 2, 'details mâu thuẫn với size'
    return f'{video.name[:24]} {w}x{h} {dur:.1f}s @ {d.get("fps")}'


def audit_srt_roundtrip():
    srt = next(iter(sorted(WORKSPACE.glob('*.srt'))), None)
    if srt is None:
        return 'SKIP: không có file SRT mẫu'
    from app.services.srt_utils import load_srt, write_srt
    cues = load_srt(srt)
    assert cues, 'load_srt rỗng'
    tmp = Path(tempfile.mkdtemp()) / 'rt.srt'
    write_srt(cues, tmp)
    back = load_srt(tmp)
    assert len(back) == len(cues), f'{len(cues)} -> {len(back)} cue'
    assert [c.text for c in back] == [c.text for c in cues], 'mất chữ sau round-trip'
    assert all(c.duration_s >= 0.05 for c in back), 'có cue dài hơn 0 (sàn 50ms)'
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return f'{len(cues)} cue giữ nguyên'


def audit_workspace_services():
    '''service thuần đĩa: preset, cache, voice history, translation memory.

    Chỉ ghi vào những chỗ tự xoá được, và không gọi mấy hàm clear_* — chúng xoá
    thật.
    '''
    out = []
    from app.services import cache_manager, job_workspace, preset_manager, voice_history
    from app.services import translation_memory as tm

    locs = cache_manager.managed_locations()
    assert locs and all(hasattr(x, 'path') for x in locs), 'managed_locations rỗng'
    summary = cache_manager.cache_summary()
    assert isinstance(summary, dict) and summary, 'cache_summary không trả gì'
    out.append(f'cache({len(locs)} chỗ)')

    ws = job_workspace.create_job_workspace('audit')
    assert ws.is_dir(), 'create_job_workspace không tạo thư mục'
    assert job_workspace.is_managed_job_path(ws), 'is_managed_job_path không nhận ra chỗ của nó'
    try:
        ws.rmdir()                                     # chỉ xoá được khi còn trống
    except OSError:
        pass
    out.append('job_workspace')

    name = '_audit_preset_tmp'
    p = preset_manager.save_user_preset(name, {'ratio': '9:16', 'fps': '30'})
    try:
        assert p.is_file(), 'save_user_preset không ghi file'
        got = preset_manager.load_preset(name)
        assert isinstance(got, dict) and got.get('ratio') == '9:16' and got.get('fps') == '30',             f'preset đọc lại ra {got}'      # load_preset có gắn thêm _meta, đó là bình thường
        assert name in preset_manager.list_presets(), 'preset không xuất hiện trong list'
    finally:
        preset_manager.delete_user_preset(name)
    assert preset_manager.load_preset(name) is None, 'xoá preset mà còn đọc được'
    out.append('preset')

    entries = voice_history.scan_voices(APP / 'output' / 'jobs', limit=5)
    assert isinstance(entries, list), 'scan_voices không trả list'
    assert voice_history.format_duration(75.5) and voice_history.parse_job_folder('x')
    out.append(f'voice_history({len(entries)})')

    key = tm.memory_key('xin chào', source_lang='vi', target_lang='en', glossary={ })
    assert isinstance(key, str) and key, 'memory_key rỗng'
    assert tm.apply_glossary('máy tính lượng tử', {'máy tính': 'computer'}) == 'computer lượng tử', \
        'apply_glossary không thay'
    assert isinstance(tm.load_translation_memory(), dict), 'load_translation_memory không phải dict'
    out.append('translation_memory')
    return ', '.join(out)


def _find_media(exts, min_bytes=0):
    for base in (WORKSPACE, Path.home() / 'Downloads'):
        if not base.is_dir():
            continue
        for p in sorted(base.glob('*' + exts[0])):
            if p.is_file() and p.stat().st_size >= min_bytes:
                return p
    return None


def audit_ocr_tab(root):
    mod = root.control._get_module('ocr')
    assert mod is not None, 'tab OCR không dựng được (lỗi bị logger nuốt)'
    from app.services import videocr_ocr
    labels = _widget_labels(mod)
    for needed in ('Chạy OCR', 'Phát', 'Xoá vùng', 'Xem trước'.upper()):
        assert any(needed.upper() in t.upper() for t in labels), f'tab OCR mất {needed!r}'
    code = videocr_ocr.resolve_lang(mod.var_lang.get())
    assert code == 'ch', f'ngôn ngữ mặc định không phải ch: {mod.var_lang.get()!r}'
    bad = [c for c in videocr_ocr.language_labels() if videocr_ocr.resolve_lang(c) is None]
    assert not bad, f'có lựa chọn không map được sang mã: {bad}'
    exe = videocr_ocr.find_videocr_cli(None)
    return f'mặc định --lang {code}, {len(videocr_ocr.OCR_LANGUAGES)} ngôn ngữ, ' \
           f'engine={"có" if exe else "KHÔNG thấy"}'


def audit_draft_builder():
    """CapCut draft: quy đổi thời gian phải đảo ngược được và đọc SRT thật."""
    from app.services import capcut_draft_builder as db
    for sec in (0.0, 0.001, 1.5, 12.345, 3600.0):
        assert abs(db.us_to_sec(db.sec_to_us(sec)) - sec) < 1e-6, sec
    ids = {db.new_uuid() for _ in range(200)}
    assert len(ids) == 200, 'new_uuid sinh trùng'
    srt = next(iter(sorted(WORKSPACE.glob('*.srt'))), None)
    if srt is None:
        return 'quy đổi + uuid OK (không có SRT mẫu)'
    cues = db.load_srt_cues(srt)
    assert cues, 'load_srt_cues rỗng'
    # SubCue lưu theo GIÂY (start_s/end_s), không phải microsecond như tên dễ đoán
    assert all(hasattr(c, 'start_s') and hasattr(c, 'end_s') for c in cues), 'sai trường của SubCue'
    assert all(c.end_s > c.start_s for c in cues), 'có cue thời gian âm'
    assert [c.index for c in cues] == list(range(len(cues))), 'chỉ số cue không liên tục'
    return f'uuid 200/200 unique, {len(cues)} cue từ {srt.name[:22]}'


def audit_fonts_translate():
    from app.services import system_fonts as sf
    fonts = sf.list_system_fonts()
    assert fonts, 'danh sách font hệ thống rỗng -> menu font trong app sẽ trống'
    assert sf.resolve_system_font('Arial'), 'resolve_system_font("Arial") không ra gì'
    assert isinstance(sf.font_stats(), dict), 'font_stats không trả dict'
    from app.services import gemini_translate as gt
    key = gt.get_translation_api_key()                      # chỉ đọc, không gọi mạng
    model = gt.normalize_gemini_model(None)
    assert isinstance(model, str) and model, 'normalize_gemini_model trả rỗng'
    return (f'{len(fonts)} font, model mặc định {model}, '
            f'API key={"có" if key else "chưa cấu hình"}')


def audit_zerotts():
    """ZeroTTS là giọng Việt offline chủ lực: kiểm nó nạp được, chưa tổng hợp."""
    import importlib.util
    assert importlib.util.find_spec('onnxruntime'),         'onnxruntime không có trong runtime của app -> ZeroTTS chết'
    preview = APP / '_internal' / 'preview' / 'zerotts'
    have = sorted(p.name for p in preview.glob('*.wav')) if preview.is_dir() else []
    return f'onnxruntime OK, {len(have)} mẫu giọng trong preview/zerotts'


def audit_cloud_stt():
    """STT CapCut — gọi mạng thật, chỉ chạy khi có --cloud."""
    video = next((c for c in (WORKSPACE / 'bake30.mp4',) if c.is_file()), None)
    assert video, 'không tìm thấy video mẫu để test STT'
    work = Path(tempfile.mkdtemp(prefix='wb_audit_stt_'))
    try:
        from app.services.capcut_tts_engine import capcut_transcribe_to_srt
        from app.services.srt_utils import load_srt
        got = capcut_transcribe_to_srt(video, work / 'asr.srt', work_dir=work, timeout_s=240)
        # trả về (đường_dẫn, số_cue, ngôn_ngữ) chứ không phải mỗi đường dẫn
        srt = got[0] if isinstance(got, (tuple, list)) else got
        assert srt and Path(str(srt)).is_file(), f'ASR không trả file: {got!r}'
        cues = load_srt(Path(str(srt)))
        assert cues, 'SRT do ASR trả về rỗng'
        n = got[1] if isinstance(got, (tuple, list)) and len(got) > 1 else len(cues)
        lang = got[2] if isinstance(got, (tuple, list)) and len(got) > 2 else '?'
        return f'{len(cues)} cue đọc lại từ file (ASR báo {n}, lang={lang})'
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true', help='bỏ bước chạm đĩa nặng')
    ap.add_argument('--cloud', action='store_true', help='gọi thêm CapCut ASR (mạng thật)')
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not INTERNAL.is_dir():
        print(f'không thấy app ở {APP}')
        return 2
    sys.path.insert(0, str(INTERNAL))

    catcher = _ErrorCatcher()
    logging.getLogger().addHandler(catcher)
    logging.getLogger().setLevel(logging.INFO)

    root = None
    check('file .py đang đè .pyc', audit_overrides)
    try:
        import customtkinter as ctk
        root, build_s = build_app(catcher)
        check(f'cửa sổ chính dựng được ({build_s:.1f}s)', lambda: audit_window(root))
        check('12 dụng cụ thanh bên', lambda: audit_every_tool(root))
        check('tab OCR', lambda: audit_ocr_tab(root))
        check('state round-trip', lambda: audit_state_roundtrip(root))
    except Exception:                                     # noqa: BLE001
        results.append(('ERROR', 'dựng MainWindow', traceback.format_exc(limit=4).strip()[-400:]))

    check('catalog giọng CapCut', audit_voice_catalog)
    check('ffmpeg + GPU', audit_ffmpeg_gpu)
    check('dựng draft CapCut', audit_draft_builder)
    check('font + dịch', audit_fonts_translate)
    check('ZeroTTS offline', audit_zerotts)
    if not args.quick:
        check('media probe', audit_media_probe)
        check('SRT round-trip', audit_srt_roundtrip)
        check('dịch vụ workspace', audit_workspace_services)
    if args.cloud:
        check('CapCut ASR (mạng)', audit_cloud_stt)

    if root is not None:
        try:
            root.update()
            root.destroy()
        except Exception:                                 # noqa: BLE001
            pass

    # ControlPanel._get_module và nhiều chỗ khác bọc try/except + logger.exception,
    # nên dựng UI hỏng có thể không raise gì. Bắt buộc kiểm riêng.
    swallowed = [r for r in catcher.records if 'Error initializing module' in r]
    others = [r for r in catcher.records if r not in swallowed]
    if swallowed:
        results.append(('FAIL', f'{len(swallowed)} panel dựng hỏng bị nuốt im lặng', swallowed[0][:250]))
    else:
        results.append(('PASS', 'không có panel nào dựng hỏng trong log', ''))
    if others:
        results.append(('WARN', f'{len(others)} lỗi ERROR khác', others[0][:200]))

    width = max(len(n) for _s, n, _d in results)
    bad = 0
    for status, name, detail in results:
        if status in ('FAIL', 'ERROR'):
            bad += 1
        print(f'  {status:<5} {name:<{width}}  {detail[:120]}')
    print(f'\n{len(results) - bad}/{len(results)} đạt' if bad else
          f'\ntất cả {len(results)} hạng mục đều đạt')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

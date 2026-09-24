# -*- coding: utf-8 -*-
'''Cổng kiểm hồi quy: những module đã khôi phục không được hỏng lại.

Mỗi lần có người sửa một module đã "chốt" thì file này phải vẫn xanh. Nó kiểm 3 thứ
mà test đơn lẻ không bắt được:
  1. file vẫn compile() được;
  2. không xuất hiện lại "hỏng im lặng" (``x = None(...)``, ``= ''.'', nhánh if mất vế...);
  3. không còn marker ``Decompyle incomplete`` — khôi phục xong là phải xoá.
'''
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'tools'))

import check_source as cs                                    # noqa: E402

# Những module đã đối chiếu với .pyc và coi là xong. Thêm file vào đây sau mỗi lần khôi phục.
RESTORED = [
    'app/services/srt_utils.py',
    'app/services/trim_ranges.py',
    'app/services/subtitle_layout.py',
    'app/services/media_probe.py',
    'app/services/preset_manager.py',
    'app/services/cache_manager.py',
    'app/services/voice_history.py',
    'app/services/demucs_separator.py',
    'app/services/edge_tts_engine.py',
    'app/services/voice_engine/zerotts_engine.py',
    'app/services/tts_preview.py',
    'app/services/capcut_common_task_client.py',
    'app/services/capcut_tts_engine.py',
    'app/services/job_workspace.py',
    'app/services/log_cleaner.py',
    'app/services/license_service.py',
    'app/services/voice_engine/zerotts/codec.py',
    'app/services/voice_engine/zerotts/text_norm/vi_normalizer.py',
    'app/ui/fluent_icons.py',
    'app/ui/modules/module_subtitle.py',
    'main.py',
]

# Khóa cứng: nhóm này phải GIỮ bytecode y hệt bản đã phát hành. Sửa mấy file này là
# có ý thức hoặc phải cập nhật danh sách kèm lý do — không được lệch âm thầm.
#
# Từ 2026-09-24 `compare_bytecode` so cả **co_consts**, không chỉ chuỗi lệnh. Trước đó
# nó chỉ nhìn arg của LOAD_CONST (là CHỈ SỐ), nên đổi chữ trong chuỗi/docstring hay
# bọc ngoặc kép một annotation vẫn báo "KHỚP HOÀN HẢO". Bẫy này đã làm main.py lệch
# thật mà không ai thấy: 'Winterboy Studio' vs 'Winterboy studio', __version__ '3.5.6'
# vs '1.01', AppUserModelID '...1.0' vs '...1.01', và gọi AttachThreadInput qua
# kernel32 thay vì user32.
BYTE_EXACT = [
    'app/services/capcut_common_task_client.py',
    'app/services/demucs_separator.py',
    'app/services/edge_tts_engine.py',
    'app/services/job_workspace.py',
    'app/services/license_service.py',
    'app/services/log_cleaner.py',
    'app/services/media_probe.py',
    'app/services/preset_manager.py',
    'app/services/story_competitor_service.py',
    'app/services/subtitle_layout.py',
    'app/services/trim_ranges.py',
    'app/services/tts_preview.py',
    'app/services/voice_engine/plugin_base.py',
    'app/services/voice_engine/zerotts/codec.py',
    'app/services/voice_engine/zerotts/text_norm/vi_normalizer.py',
    'app/services/voice_engine/zerotts/cli.py',
    'app/services/voice_engine/zerotts_engine.py',
    'app/ui/fluent_icons.py',
    'app/ui/modules/module_subtitle.py',
    'main.py',
]

# File ĐƯỢC PHÉP lệch khỏi .pyc đã phát hành, kèm số chỗ tối đa và lý do.
# Không có mục này thì mỗi lần nâng phiên bản là cổng bytecode đỏ, và người ta sẽ
# bỏ qua cổng thay vì khai báo ý định.
ALLOWED_DRIFT = {
    'app/__init__.py': (1, 'nâng __version__ lên 1.2 (bản phát hành đang là 1.01)'),
}


def _paths():
    missing = [r for r in RESTORED if not (REPO / r).is_file()]
    assert not missing, f'khai báo sai đường dẫn: {missing}'
    return [REPO / r for r in RESTORED]


def test_restored_files_compile():
    bad = cs.check_syntax(_paths())
    assert not bad, [(f, e) for f, e in bad.items()]


def test_restored_files_have_no_silent_damage():
    dmg = cs.damage_scan(_paths())
    assert not dmg, {f: h[:3] for f, h in dmg.items()}


def test_restored_files_have_no_leftover_markers():
    marks = cs.count_markers(_paths())
    assert not marks, marks


def test_voice_catalog_still_loads_24_vietnamese_voices():
    '''Tính năng chính của branch này: dropdown phải còn đủ giọng VN.'''
    from _parity import repo_module
    mod = repo_module('app.services.capcut_tts_engine')
    voices = mod.list_capcut_voices(lang='vi-VN')
    assert len(voices) == 24, f'chỉ còn {len(voices)} giọng vi-VN'
    label, key = voices[0]
    vt, rid = mod.parse_voice_key(key)
    assert vt and rid.isdigit(), (vt, rid)
    # nhãn UI phải parse ngược ra đúng key
    assert mod.parse_voice_key(label) == (vt, rid)


def test_bytecode_lock_stays_exact():
    '''Nhóm BYTE_EXACT phải còn biên dịch ra đúng mã như .pyc đã phát hành.

    Đây là bằng chứng mạnh nhất repo đang có: không cần chạy, không cần gọi mạng,
    mã nguồn cho ra từng instruction một. Sửa mấy file này mà quên cập nhật danh
    sách là test này đỏ.
    '''
    import compare_bytecode as cbc
    missing, drifted = [], []
    for rel in (*BYTE_EXACT, *ALLOWED_DRIFT):
        path = REPO / rel
        if not path.is_file():
            missing.append(rel)
            continue
        try:
            _dotted, _n, bad = cbc.compare(path)
        except FileNotFoundError:
            missing.append(f'{rel} (không có .pyc đối chiếu)')
            continue
        except Exception as exc:
            drifted.append(f'{rel}: {type(exc).__name__} {str(exc)[:60]}')
            continue
        budget = ALLOWED_DRIFT.get(rel, (0, ''))[0]
        if len(bad) > budget:
            drifted.append(f'{rel}: {len(bad)} chỗ, chỉ cho phép {budget} — {bad[0][0]} '
                           f'{bad[0][1][:70]}')
    assert not missing, f'mất file cần khóa: {missing}'
    assert not drifted, 'bytecode lệch so với bản phát hành:\n  ' + '\n  '.join(drifted)


def test_phien_ban_khai_bao_o_dung_mot_ch():
    '''Phiên bản phải sống duy nhất ở app/__init__.py và UI lấy từ đó suy ra.'''
    import app as pkg

    assert pkg.__version__ == '1.2', pkg.__version__
    assert pkg.VERSION_LABEL == f'v{pkg.__version__}'
    # không được có nguồn phiên bản thứ hai âm thầm xuất hiện trong source đã khôi phục
    text = (REPO / 'app' / '__init__.py').read_text(encoding='utf-8')
    assert text.count('__version__ =') == 1, 'khai báo __version__ ở nhiều chỗ'


def test_check_source_cli_green_on_restored():
    code = cs.main(['--only', *RESTORED, '--damaged'])
    assert code == 0, 'check_source báo lỗi trên nhóm đã khôi phục'

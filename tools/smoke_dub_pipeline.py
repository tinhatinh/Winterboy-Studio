# -*- coding: utf-8 -*-
'''Smoke test end-to-end cho luồng lồng tiếng chạy từ MÃ NGUỒN (không phải .pyc).

Nạp các module trong repo theo đường dẫn file (bỏ qua app/services/__init__.py),
rồi đi hết chuỗi: SRT -> CapCut TTS -> AudioSyncEngine căn timeline -> master.wav.
Đây là phép thử mà so sánh bytecode không thay được: nó gọi mạng thật và ffmpeg
thật, nên chỉ chạy khi bạn chủ động muốn kiểm.

    python tools/smoke_dub_pipeline.py
    python tools/smoke_dub_pipeline.py --voice "BV075_streaming:7102355803792740865"

Cần: device profile ở ~/.winterboy/capcut_device.json, ffmpeg trên PATH, và
pysrt (app đã cài có sẵn; máy chưa có thì `pip install pysrt`).
'''
from __future__ import annotations

import argparse
import importlib.util as iu
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERNAL = Path(r'C:\Users\Administrator\MumuStudioPro\{app}\_internal')
DEFAULT_VOICE = 'BV421_vivn_streaming:7252594014782755330'
LINES = ['Xin chào, đây là bản thử lồng tiếng.',
         'Hai dòng nối tiếp nhau trên cùng một timeline.']

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def load(alias, rel):
    '''Nạp module thẳng từ file trong repo, không đi qua package __init__.'''
    path = (REPO / rel).resolve()
    spec = iu.spec_from_file_location(f'repo_{alias}', path)
    mod = iu.module_from_spec(spec)
    sys.modules[f'repo_{alias}'] = mod
    spec.loader.exec_module(mod)
    return mod


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return float((out.stdout or '0').strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice', default=DEFAULT_VOICE)
    ap.add_argument('--internal', default=str(INTERNAL),
                    help='lấy pysrt từ bản đã cài nếu máy chưa có')
    args = ap.parse_args()

    try:
        import pysrt                                              # noqa: F401
    except ImportError:
        sys.path.insert(0, str(Path(args.internal)))
        import pysrt                                              # noqa: F401
        sys.path.remove(str(Path(args.internal)))
        print('(mượn pysrt từ bản đã cài)')

    sys.path.insert(0, str(REPO))
    client = load('client', 'app/services/capcut_common_task_client.py')
    engine = load('engine', 'app/services/capcut_tts_engine.py')
    srt = load('srt', 'app/services/srt_utils.py')
    manifest = load('manifest', 'app/services/artifact_manifest.py')
    for key, mod in (('capcut_common_task_client', client), ('srt_utils', srt),
                     ('artifact_manifest', manifest)):
        sys.modules[f'app.services.{key}'] = mod
    sync = load('sync', 'app/services/audio_sync_engine.py')
    print('nạp module repo OK:', ', '.join(p for p in (
        'capcut_common_task_client', 'capcut_tts_engine', 'srt_utils',
        'artifact_manifest', 'audio_sync_engine')))

    voices = engine.list_capcut_voices(lang='vi-VN')
    print(f'catalog: {len(voices)} giọng vi-VN')
    if not voices:
        print('KHÔNG có giọng nào — thiếu app/services/capcut_voices.json?')
        return 1

    work = Path(tempfile.mkdtemp(prefix='dub_smoke_'))
    in_srt = work / 'in.srt'
    srt.write_srt([srt.SrtCue(i + 1, i * 2.8, i * 2.8 + 2.6, t) for i, t in enumerate(LINES)], in_srt)

    tts_func = engine.make_capcut_tts_func(voice=args.voice, speed=1.0, strict=True)
    job = sync.AudioSyncEngine(work / 'sync', tts_func=tts_func, ffmpeg_bin='ffmpeg',
                               ffprobe_bin='ffprobe', soft_timing_enabled=True,
                               voice_signature=f'capcut:smoke:{args.voice}')
    master = work / 'master.wav'
    res = job.build_voice_track(in_srt, master, align_to_timeline=True, engine_label='CapCut')

    print(f'build_voice_track: ok={res.ok} blocks={res.n_blocks} total={res.total_duration_s:.2f}s')
    for r in res.reports:
        print(f'   #{r.index} start={r.effective_start_s:5.2f} dur={r.d_voice:5.2f} '
              f'mode={r.mode} speed={r.speed_rate} err={r.error}')
    if not res.ok:
        print('FAIL: build_voice_track trả ok=False')
        return 1
    dur = duration(master)
    size = master.stat().st_size
    print(f'master.wav: {dur:.2f}s {size / 1024:.0f}KB')
    if dur < 1.0 or size < 100_000:
        print('FAIL: master.wav rỗng bất thường')
        return 1
    report = work / 'sync' / 'tts_quality_report.json'
    if report.is_file():
        data = json.loads(report.read_text(encoding='utf-8'))
        print('quality report:', {k: data[k] for k in list(data)[:5]})
    print('\nKẾT LUẬN: luồng lồng tiếng chạy được từ mã nguồn repo.')
    print('(chỉ giữ file ở', work, 'nếu bạn muốn nghe thử)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

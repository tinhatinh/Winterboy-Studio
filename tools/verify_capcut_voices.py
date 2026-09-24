# -*- coding: utf-8 -*-
'''Kiểm chứng từng giọng trong ``app/services/capcut_voices.json``.

Catalog chỉ là danh sách ``voice_type`` + ``resource_id`` do CapCut trả về; có giọng
bị gắn quyền riêng / thẻ sự kiện nên gửi lên vẫn nhận ``failed``. Chạy tool này để
biết giọng nào thực sự sinh ra được audio, rồi gắn kết quả vào trường ``verified``.

Cách chạy (đứng từ thư mục gốc repo):

    python tools/verify_capcut_voices.py --lang vi
    python tools/verify_capcut_voices.py --lang vi --write      # ghi verified vào json
    python tools/verify_capcut_voices.py --engine "C:/WinterboyStudio/_internal"

``--engine`` trỏ tới thư mục ``_internal`` của bản đã build/install, dùng khi chạy
từ mã nguồn mà engine chưa đủ hàm (file .py trong repo do decompile nên có thể thiếu).
'''
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VOICES = REPO / 'app' / 'services' / 'capcut_voices.json'
TEXT_DEFAULT = 'Hội nghị Solvay năm 1927 đánh dấu bước ngoặt của cơ học lượng tử.'

# Windows mặc định mở stdout bằng cp1252 -> in tên giọng có dấu tiếng Việt là vỡ
# UnicodeEncodeError, nên ép UTF-8 ngay từ đầu.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


def load_engine(engine_dir):
    '''Nạp capcut_tts_engine: ưu tiên bản trong --engine, nếu không thì dùng mã nguồn.'''
    if engine_dir:
        root = Path(engine_dir)
        if not (root / 'app' / 'services').is_dir():
            root = root / '_internal'
        sys.path.insert(0, str(root))
    else:
        sys.path.insert(0, str(REPO))
    from app.services import capcut_tts_engine as eng          # noqa: E402
    if not hasattr(eng, 'capcut_tts_generate'):
        raise SystemExit(
            'capcut_tts_engine trong mã nguồn thiếu hàm capcut_tts_generate (file .py do '
            'decompile, có thể chưa đủ).\nChạy với --engine <đường dẫn _internal của bản '
            'đã build> để dùng engine thật.')
    return eng


def main():
    ap = argparse.ArgumentParser(description='Probe danh sách giọng CapCut.')
    ap.add_argument('--lang', default='vi', help='Tiền tố ngôn ngữ cần thử (vi, en, ja, all).')
    ap.add_argument('--text', default=TEXT_DEFAULT, help='Câu dùng để sinh audio.')
    ap.add_argument('--out', default=None, help='File json ghi báo cáo.')
    ap.add_argument('--keep-audio', action='store_true', help='Giữ lại các file mp3 đã sinh.')
    ap.add_argument('--write', action='store_true',
                    help='Ghi ngược kết quả verified/note vào capcut_voices.json.')
    ap.add_argument('--engine', default=None, help='Thư mục _internal của bản đã cài đặt.')
    args = ap.parse_args()

    eng = load_engine(args.engine)
    catalog = json.loads(VOICES.read_text(encoding='utf-8-sig'))
    if args.lang and args.lang.lower() not in ('all', ''):
        want = args.lang.lower()
        items = [c for c in catalog
                 if str(c.get('lang') or c.get('lan') or '').lower().startswith(want)]
    else:
        items = catalog
    print(f'catalog: {len(catalog)} giọng | thử {len(items)} giọng lang={args.lang}', flush=True)

    out_dir = REPO / 'output' / 'voice_probe'
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M')
    ok, fail = [], []
    for n, it in enumerate(items, 1):
        key = f"{it['voice_type']}:{it['resource_id']}"
        name = it.get('display_name') or it['voice_type']
        safe = ''.join(ch if ch.isalnum() or ch in ' .-_' else '_' for ch in name)
        p = out_dir / f'{n:03d}_{safe}.mp3'
        t0 = time.time()
        try:
            eng.capcut_tts_generate(args.text, p, voice=key, speed='1.0', timeout_s=60)
            size = p.stat().st_size if p.exists() else 0
            if size > 2000:
                ok.append({'name': name, 'key': key, 'bytes': size})
                print(f'  [{n:3}/{len(items)}] OK   {name:28} {time.time() - t0:4.1f}s', flush=True)
            else:
                fail.append({'name': name, 'key': key, 'err': 'file rỗng'})
                print(f'  [{n:3}/{len(items)}] RỖNG {name}', flush=True)
        except Exception as exc:
            msg = f'{type(exc).__name__}: {str(exc)[:90]}'
            fail.append({'name': name, 'key': key, 'err': msg})
            print(f'  [{n:3}/{len(items)}] LỖI {name:28} {msg}', flush=True)
        finally:
            if p.exists() and not args.keep_audio:
                p.unlink()

    report = {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'lang': args.lang,
              'text': args.text, 'ok': ok, 'fail': fail}
    out_file = Path(args.out) if args.out else out_dir / f'probe_{args.lang}_{stamp}.json'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n{len(ok)} OK / {len(fail)} lỗi -> {out_file}')

    if args.write:
        good = {x['key'] for x in ok}
        errs = {x['key']: x['err'] for x in fail}
        for row in catalog:
            k = f"{row['voice_type']}:{row['resource_id']}"
            if k in good:
                row['verified'] = True
                row.pop('note', None)
            elif k in errs:
                row['verified'] = False
                row['note'] = errs[k].split(':')[0].strip()
            row['verified_at'] = report['generated_at']
        VOICES.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8')
        print(f'đã cập nhật verified vào {VOICES.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

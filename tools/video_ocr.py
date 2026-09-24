# -*- coding: utf-8 -*-
'''Chạy VideOCR cho một video từ dòng lệnh.

    python tools/video_ocr.py "C:\\Videos\\clip.mp4"
    python tools/video_ocr.py clip.mp4 -o out.srt --lang ch --no-gpu
    python tools/video_ocr.py clip.mp4 --start 00:01:00 --end 00:02:00 --print

Dùng đúng service mà module OCR trong app gọi, nên hai đường cho ra kết quả giống nhau.
'''
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.services import videocr_ocr                              # noqa: E402
from app.services.videocr_ocr import OcrOptions, find_videocr_cli, run_ocr  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        _s.reconfigure(encoding='utf-8', errors='replace')


def main(argv=None):
    ap = argparse.ArgumentParser(description='OCR phụ đề cứng trên video thành SRT (VideOCR).')
    ap.add_argument('video', nargs='?', help='file video cần OCR')
    ap.add_argument('-o', '--output', default=None, help='file .srt đầu ra (mặc định <video>.srt)')
    ap.add_argument('--lang', default='ch',
                    help='ngôn ngữ OCR: mã (ch, en, vi, japan…) hoặc nhãn '
                         '("Chinese & English"). Mặc định: ch. Thiếu '
                         '--list-languages để xem hết danh sách đã kiểm chứng.')
    ap.add_argument('--list-languages', action='store_true',
                    help='in mã + tên ngôn ngữ VideOCR bản này nhận, rồi thoát')
    ap.add_argument('--cli', default=None, help='đường dẫn videocr-cli.exe nếu không ở chỗ mặc định')
    ap.add_argument('--no-gpu', action='store_true', help='chạy CPU (chậm hơn nhưng không cần CUDA)')
    ap.add_argument('--min-duration', type=float, default=0.3, dest='min_subtitle_duration',
                    help='bỏ dòng hiển thị ngắn hơn giây này (0.3)')
    ap.add_argument('--start', default=None, dest='time_start', help='bỏ qua đầu video, vd 00:01:00')
    ap.add_argument('--end', default=None, dest='time_end', help='dừng ở, vd 00:02:00')
    ap.add_argument('--crop', nargs=4, type=int, metavar=('X', 'Y', 'W', 'H'), default=None,
                    help='chỉ đọc chữ trong vùng này (ảnh 1920x1080: 0 928 1920 152)')
    ap.add_argument('--timeout', type=float, default=1800.0)
    ap.add_argument('--print', action='store_true', dest='show', help='in nội dung SRT ra màn hình')
    args = ap.parse_args(argv)

    if args.list_languages:
        for code, label in videocr_ocr.OCR_LANGUAGES:
            print(f'{code:<13} {label}')
        return 0
    if not args.video:
        ap.error('thiếu file video (hoặc dùng --list-languages)')
    if videocr_ocr.resolve_lang(args.lang) is None:
        print(videocr_ocr.unknown_lang_message(args.lang))
        return 2

    video = Path(args.video)
    if not video.is_file():
        print(f'KHÔNG thấy video: {video}')
        return 2
    out = Path(args.output) if args.output else video.with_suffix('.ocr.srt')
    exe = find_videocr_cli(args.cli)
    if exe is None:
        print('Không tìm thấy videocr-cli.exe.\n'
              'Cài VideOCR vào C:\\Program Files\\VideOCR, hoặc đặt biến môi trường '
              'WINTERBOY_VIDEOCR trỏ tới thư mục cài.')
        return 2
    print(f'engine: {exe}')

    opts = OcrOptions(lang=args.lang, use_gpu=not args.no_gpu,
                      min_subtitle_duration=args.min_subtitle_duration,
                      time_start=args.time_start, time_end=args.time_end,
                      crop=tuple(args.crop) if args.crop else None)
    last = [-1.0]

    def progress(frac, label):
        if frac - last[0] >= 0.02 or frac >= 1.0:
            print(f'  {frac * 100:5.1f}%  {label}', flush=True)
            last[0] = frac

    t0 = time.time()
    res = run_ocr(video, out, cli=exe, opts=opts, progress=progress, timeout_s=args.timeout)
    dt = time.time() - t0
    if not res.ok:
        print(f'\nLỖI: {res.error}')
        for line in res.log_tail[-6:]:
            print('   |', line[:150])
        return 1
    print(f'\nOK: {res.n_cues} cue, {res.duration_s:.1f}s nội dung, {dt:.0f}s xử lý')
    print(f'file: {out}')
    if res.cues:
        first, mid = res.cues[0], res.cues[len(res.cues) // 2]
        print(f'  dòng 1     [{first.start_s:6.2f}-{first.end_s:6.2f}] {first.text[:60]}')
        print(f'  dòng giữa  [{mid.start_s:6.2f}-{mid.end_s:6.2f}] {mid.text[:60]}')
    if args.show:
        print('\n--- SRT ---')
        print(out.read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

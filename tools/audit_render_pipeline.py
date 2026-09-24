# -*- coding: utf-8 -*-
'''Kiểm end-to-end đường RENDER thật của bản đã cài: blur + phụ đề + tiếng lồng.

Vì sao phải render thật thay vì so bytecode: chính chỗ này từng đẻ ra file MP4
"hợp lệ giả" — ``ok=True``, đúng số packet, dung lượng đẹp, nhưng mọi NAL length
prefix là rác và avcC không parse được. Chỉ có ``ffmpeg -v error`` trên toàn bộ
file mới phát hiện được. Ngoài ra còn hai bẫy im lặng khác:

* ``fps``/``speed`` nhận NHÃN UI ("60 FPS (Mượt mà)", "100") thay vì số — renderer
  ``int()`` là vỡ hoặc chạy 4× tốc độ mà không báo gì;
* phụ đề có thể không được burn mà file vẫn "OK".

Nên phép kiểm này: render thật một đoạn 12 giây, rồi đo (1) giải mã sạch lỗi,
(2) thời lượng khớp, (3) có cả stream tiếng, (4) khung hình KHÁC hẳn bản không
phụ đề — tức là chữ đã được đưa vào hình thật.

    python tools/audit_render_pipeline.py
    python tools/audit_render_pipeline.py --seconds 20 --keep
'''
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

APP = Path(r'C:\Users\Administrator\MumuStudioPro\{app}')
INTERNAL = APP / '_internal'
WORKSPACE = Path(r'C:\Users\Administrator\Documents\Qoder\2026-09-23\78e344d5\wuli2')


def sh(args, timeout=600):
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout)


def cut(src: Path, dst: Path, seconds: float, *, audio=False):
    '''Cắt đầu vào. ``audio=False`` nghĩa là lấy VIDEO KÈM tiếng của nó.

    Phải giữ âm thanh của chính clip: renderer nối ``[0:a]`` khi
    keep_original_audio=True, mà input không có stream tiếng thì ffmpeg báo
    "matches no streams" — nhìn như hỏng renderer nhưng thật là đầu vào sai.
    '''
    args = [shutil.which('ffmpeg'), '-y', '-loglevel', 'error', '-ss', '0',
            '-t', str(seconds), '-i', str(src)]
    args += (['-vn', '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s16le'] if audio
             else ['-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy'])
    args.append(str(dst))
    r = sh(args, 300)
    return r.returncode == 0 and dst.is_file(), r.stderr[-200:]


def probe_streams(path: Path):
    r = sh([shutil.which('ffprobe'), '-v', 'error', '-show_entries',
            'stream=codec_type,duration:format=duration', '-of', 'json', str(path)])
    try:
        d = json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        return {}
    return {'kinds': sorted({s.get('codec_type') for s in d.get('streams', [])}),
            'duration': float((d.get('format') or {}).get('duration') or 0)}


def decode_errors(path: Path) -> str:
    '''Mọi dòng ffmpeg in ra khi giải mã cả file = file hỏng. Đây là phép thử chính.'''
    r = sh([shutil.which('ffmpeg'), '-v', 'error', '-i', str(path), '-f', 'null', '-'], 900)
    return (r.stderr or '').strip()


def grab_frame(video: Path, at_s: float, out: Path):
    return sh([shutil.which('ffmpeg'), '-y', '-loglevel', 'error', '-ss', str(at_s),
               '-i', str(video), '-frames:v', '1', str(out)]).returncode == 0 and out.is_file()


def frame_diff(a: Path, b: Path) -> float:
    '''Chênh lệch tuyệt đối trung bình giữa hai khung hình (0..255).'''
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return -1.0
    ia, ib = Image.open(a).convert('L'), Image.open(b).convert('L')
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    return float(ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0])


def write_srt_window(src_srt: Path, dst_srt: Path, limit: float) -> int:
    from app.services.srt_utils import load_srt, write_srt
    cues = [c for c in load_srt(src_srt) if c.start_s < limit - 0.4]
    write_srt(cues, dst_srt)
    return len(cues)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=12.0)
    ap.add_argument('--keep', action='store_true', help='giữ file kết quả để mắt xem')
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    sys.path.insert(0, str(INTERNAL))
    base = next((p for p in (WORKSPACE / 'bake_nosub.mp4',) if p.is_file()), None)
    srt_src = next((p for p in (WORKSPACE / 'subtitles_vi.srt',) if p.is_file()), None)
    voice_src = next((p for p in (WORKSPACE / 'ztts_quangminh.wav',) if p.is_file()), None)
    missing = [str(x) for x, ok in (('video', base), ('srt', srt_src), ('voice', voice_src)) if not ok]
    if missing:
        print('thiếu đầu vào:', ', '.join(missing))
        return 2

    work = Path(tempfile.mkdtemp(prefix='wb_audit_render_'))
    fails = []
    try:
        clip = work / 'in.mp4'
        ok, err = cut(base, clip, args.seconds)
        assert ok, f'không cắt được video: {err}'
        kinds = probe_streams(clip).get('kinds', [])
        assert 'video' in kinds, f'clip cắt ra không có hình: {kinds}'
        assert 'audio' in kinds, ('clip cắt ra không có tiếng, trong khi keep_original_audio=True '
                                  f'sẽ làm filtergraph vỡ: {kinds}')
        voice = work / 'voice.wav'
        ok, err = cut(voice_src, voice, args.seconds, audio=True)
        assert ok, f'không cắt được tiếng: {err}'
        srt = work / 'sub.srt'
        n_cues = write_srt_window(srt_src, srt, args.seconds)
        assert n_cues >= 2, f'chỉ {n_cues} cue trong cửa sổ {args.seconds}s'
        print(f'đầu vào: {clip.name} {args.seconds}s, {n_cues} cue, voice {voice.stat().st_size // 1024}KB')

        from app.services.ffmpeg_renderer import FFmpegRenderer

        # cố tình dùng giá trị ĐÚNG kiểu (số), không truyền nhãn UI
        options = {'ratio': 'Giữ nguyên', 'fps': '30', 'zoom': '100', 'speed': '1',
                   'use_gpu': True, 'video_codec': 'h264', 'flip_h': True,
                   'keep_original_audio': True, 'original_volume': 40, 'tts_volume': 130,
                   'adaptive_ducking': True, 'normalize_audio': True, 'vocal_filter': False,
                   'enable_subtitle': True, 'sub_font': 'Arial', 'sub_size': '54',
                   'sub_color': '#FFFFFF', 'sub_y': '1180', 'sub_x': '0',
                   'blur_enable': True, 'blur_x': '0', 'blur_y': '1240',
                   'blur_w': '2560', 'blur_h': '200', 'blur_strength': '20',
                   'blur_opacity': '1.0'}

        def run(out_name, opts):
            out = work / out_name
            res = FFmpegRenderer(work / f'wd_{out_name}').render(clip, out,
                                                                 srt_path=srt if opts.get('enable_subtitle') else None,
                                                                 voice_path=voice, options=opts)
            return res, out

        print('đang render bản đầy đủ (blur + phụ đề + tiếng)...')
        res, full = run('full.mp4', options)
        assert getattr(res, 'ok', False), f'render báo lỗi: {getattr(res, "message", res)}'
        assert full.is_file() and full.stat().st_size > 100_000, 'file ra quá nhỏ'

        errs = decode_errors(full)
        if errs:
            fails.append('file HỦY DIẾT về mặt stream:\n      ' + errs.replace('\n', '\n      ')[:600])
        info = probe_streams(full)
        dur = info.get('duration', 0)
        if not abs(dur - args.seconds) <= 1.0:
            fails.append(f'thời lượng {dur:.2f}s lệch nhiều so với {args.seconds}s')
        if 'audio' not in info.get('kinds', []):
            fails.append(f'mất stream tiếng: {info}')
        if 'video' not in info.get('kinds', []):
            fails.append(f'mất stream hình: {info}')
        print(f'  full.mp4: {dur:.2f}s, streams={info.get("kinds")}, '
              f'{full.stat().st_size // 1024}KB, decode_errors={"KHÔNG" if not errs else "CÓ"}')

        print('đang render bản đối chứng (không phụ đề, không blur)...')
        plain_opts = dict(options)
        plain_opts.update({'enable_subtitle': False, 'blur_enable': False})
        res2, plain = run('plain.mp4', plain_opts)
        assert getattr(res2, 'ok', False), f'bản đối chứng render lỗi: {getattr(res2, "message", res2)}'
        fa, fb = work / 'fa.png', work / 'fb.png'
        at = min(args.seconds - 1.0, 3.0)
        if grab_frame(full, at, fa) and grab_frame(plain, at, fb):
            diff = frame_diff(fa, fb)
            if diff == 0.0:
                fails.append('bản có phụ đề và bản không phụ đề GIỐNG HỆT nhau -> chữ không được đưa vào hình')
            elif diff < 0.4:
                fails.append(f'chênh lệch khung hình chỉ {diff:.2f}/255 — nghi phụ đề không hiện')
            else:
                print(f'  khung hình khác nhau {diff:.2f}/255 -> phụ đề + blur đã áp dụng thật')
        else:
            fails.append('không trích được khung hình để so sánh')

        print('đang kiểm bẫy nhãn UI (fps/speed dạng chuỗi)...')
        bad = dict(options)
        bad.update({'fps': '60 FPS (Mượt mà)', 'speed': '100'})
        try:
            res3, v3 = run('labelled.mp4', bad)
            d3 = probe_streams(v3).get('duration', 0)
            if getattr(res3, 'ok', False) and d3 and abs(d3 - args.seconds) > 1.5:
                fails.append(f'nhãn UI làm đổi tốc độ thật: {args.seconds}s -> {d3:.2f}s')
            print(f'  fps/speed dạng nhãn: ok={getattr(res3, "ok", "?")}, '
                  f'ra {d3:.2f}s (đầu vào {args.seconds}s)')
        except Exception as exc:                           # noqa: BLE001
            print(f'  fps/speed dạng nhãn: từ chối ngay ({type(exc).__name__}) — an toàn')

        if not args.keep:
            # Windows có thể còn giữ tay nắm file vừa ffprobe xong. Xoá được thì xoá,
            # không thì để rmtree ở finally dọn — không tính đây là audit hỏng.
            for f in work.glob('*.mp4'):
                try:
                    f.unlink(missing_ok=True)
                except PermissionError:
                    print(f'  (để lại {f.name}: Windows còn mở file)')
        else:
            print(f'  giữ file ở {work}')
    except AssertionError as exc:
        fails.append(str(exc))
    except Exception:                                      # noqa: BLE001
        import traceback
        fails.append('EXCEPTION: ' + traceback.format_exc(limit=4).strip()[-400:])
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)

    if fails:
        print('\nFAIL')
        for f in fails:
            print('  -', f)
        return 1
    print('\nOK — render thật chạy đúng: giải mã sạch, đủ stream, phụ đề hiện lên hình.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

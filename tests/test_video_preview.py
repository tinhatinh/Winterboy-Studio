# -*- coding: utf-8 -*-
'''Test app.services.video_preview — luồng frame phục vụ ô xem trước thẻ OCR.

Phần toán (fit_box / build_command / quy đổi index) chạy thuần, không cần ffmpeg.
Phần giải mã thật là test tích hợp: cần ffmpeg trong PATH và một video mẫu, thiếu
một trong hai thì in SKIP rồi bỏ qua — bộ test chạy trên máy không cài VideOCR vẫn
phải xanh.
'''
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.services.video_preview import (                       # noqa: E402
    FrameStream, PreviewInfo, build_command, fit_box)

SCRATCH = REPO / 'output' / '_restore' / 'video_preview'


def _mini_video(seconds: float = 2.0, size: str = '160x120', rate: int = 10):
    '''Tự tạo clip mẫu bằng ffmpeg.

    Không lấy video work ngoài thư mục khác: test phải chạy được trên máy khác và
    không phụ thuộc tập tin hàng trăm MB. Clip 160x120 dựng trong ~0,2 giây.
    '''
    if not shutil.which('ffmpeg'):
        return None
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = SCRATCH / f'mini_{size}_{int(seconds * rate)}.mp4'
    if out.is_file() and out.stat().st_size > 0:
        return out
    cmd = [shutil.which('ffmpeg'), '-y', '-loglevel', 'error',
           '-f', 'lavfi', '-i', f'testsrc2=size={size}:rate={rate}',
           '-t', f'{seconds:g}', '-pix_fmt', 'yuv420p', str(out)]
    done = subprocess.run(cmd, capture_output=True, timeout=60)
    if done.returncode != 0 or not out.is_file():
        return None
    return out


def test_fit_box_giu_ti_le_va_nam_trong_box():
    assert fit_box(2560, 1440, (330, 300)) == (330, 184)
    assert fit_box(1080, 1920, (330, 300)) == (168, 300)
    w, h = fit_box(320, 240, (330, 300))                # nhỏ hơn box thì không phóng to
    assert (w, h) == (320, 240)
    for box in ((330, 300), (200, 400)):
        for (sw, sh) in ((1920, 1080), (1080, 1920), (640, 640), (3840, 2160)):
            w, h = fit_box(sw, sh, box)
            assert w <= box[0] and h <= box[1], (sw, sh, w, h)
            assert abs((w / h) - (sw / sh)) < 0.05, (sw, sh, w, h)


def test_fit_box_chong_du_lieu_deu():
    assert fit_box(0, 0, (330, 300)) == (330, 300)       # không probe được -> trả box
    assert fit_box(100, 100, (0, 0)) == (0, 0)
    assert all(v > 0 for v in fit_box(1, 1, (330, 300)))


def test_build_command_xuat_jpeg_qua_pipe():
    cmd = build_command('v.mp4', 'ffmpeg', fps=6, out_w=330, out_h=184)
    assert cmd[0] == 'ffmpeg' and cmd[-1] == 'pipe:1'
    joined = ' '.join(cmd)
    assert '-an' in cmd and '-sn' in cmd                 # không cần audio/subtitle
    assert '-vcodec' in cmd and 'mjpeg' in cmd[cmd.index('-vcodec') + 1]
    assert 'image2pipe' in joined
    assert 'fps=fps=6' in joined and 'scale=330:184' in joined
    assert 'force_original_aspect_ratio=decrease' in joined
    assert '-ss' not in cmd                              # một lần decode, không seek lại


def _info(**kw):
    base = dict(video=Path('x.mp4'), width=1080, height=1920, duration_s=10.0, fps=6.0,
                out_w=168, out_h=300, total_frames=60)
    base.update(kw)
    return PreviewInfo(**base)


def test_index_va_giay_doi_choi_nhu_nhau():
    s = FrameStream('x.mp4', fps=6.0)
    s.info = _info()
    assert s.index_for(0) == 0
    assert s.index_for(1.0) == 6
    assert s.index_for(9.999) == 59                       # kẹp trong tổng số frame
    assert s.index_for(9999) == 59
    assert s.index_for(-3) == 0
    assert abs(s.seconds_for(30) - 5.0) < 1e-9
    for sec in (0, 1.5, 7.25):
        assert abs(s.seconds_for(s.index_for(sec)) - sec) < 1 / 6.0


def test_chua_start_thi_khong_vo_dinh():
    s = FrameStream('x.mp4')
    assert s.ready() == 0 and s.get(0) is None and s.index_for(5) == 0
    assert s.info is None and not s.exhausted
    s.close()                                             # close khi chưa start cũng ok


def test_close_chan_duoc_ffmpeg_dang_chay():
    '''Đóng giữa chừng phải giết tiến trình, không để ffmpeg mồ côi chạy âm ỉ.

    Clip phải DÀI đủ để ffmpeg còn đang giải mã lúc ta đóng: frame 160x120 được
    decode nhanh tới mức clip 20 giây đã xong trước khi test kịp chạy, và khi đó
    ``_proc`` đã được dọn sẵn — test sẽ xanh một cách rỗng tuếch. Nên dùng 720p.
    '''
    clip = _mini_video(seconds=30.0, size='1280x720', rate=25)
    if clip is None:
        print('  SKIP: không dựng được clip mẫu (thiếu ffmpeg?)')
        return
    s = FrameStream(clip, fps=6.0, max_frames=3000)
    info = s.start()
    assert info.total_frames > 60, info
    deadline = time.time() + 25
    while s.ready() < 5 and time.time() < deadline:
        time.sleep(0.05)
    assert s.ready() >= 5, f'ffmpeg không trả frame nào: {s.error}'
    if s.ready() >= info.total_frames:
        print('  SKIP: máy giải mã nhanh hơn lúc test bắt đầu, không còn ffmpeg để chặn')
        s.close()
        return
    proc = s._proc
    assert proc is not None, 'đã mất _proc trong lúc vẫn còn đang giải mã'
    s.close()
    assert proc.poll() is not None, 'ffmpeg vẫn sống sau close()'
    assert s._proc is None
    n = s.ready()                                          # đóng rồi là không lớn thêm
    time.sleep(0.5)
    assert s.ready() == n, 'vẫn giải mã sau close()'


def test_khung_hinh_la_jpeg_giai_duoc_dung_kich_thuoc():
    clip = _mini_video(seconds=3.0, size='320x240')
    if clip is None:
        print('  SKIP: không dựng được clip mẫu (thiếu ffmpeg?)')
        return
    s = FrameStream(clip, box=(200, 200), fps=4.0, max_frames=40)
    info = s.start()
    deadline = time.time() + 15
    while s.ready() < 4 and time.time() < deadline:
        time.sleep(0.05)
    data = s.get(2)
    try:
        s.close()
    except Exception:
        pass
    assert data, f'không đủ frame: {s.error}'
    assert data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9', 'không phải JPEG trọn vẹn'
    assert info.out_w == 200 and info.out_h == 150, info   # 320x240 thu về box 200x200
    try:
        from PIL import Image
    except ImportError:
        print('  SKIP: không có Pillow để kiểm kích thước')
        return
    w, h = Image.open(io.BytesIO(data)).size
    assert (w, h) == (info.out_w, info.out_h), (w, h, info)

# -*- coding: utf-8 -*-
'''Luồng khung hình preview cho thẻ OCR: giải mã cả video MỘT lần bằng ffmpeg.

Lý do không "xin từng frame": mỗi lần gọi ``ffmpeg -ss T -i video -frames:v 1`` tốn
~0.2-1,7 giây khởi động + seek, nên kéo thanh trượt là ảnh nhảy theo từng nhịp rất
chậm. Ở đây chỉ spawn đúng một tiến trình, cho nó xuất cả video thành JPEG nhỏ qua
pipe ở fps thấp (mặc định 6), và đọc dần. Thanh trượt khi đó chỉ việc đổi index đang
có sẵn trong bộ nhớ -> ảnh đổi tức thì, và bấm Phát chạy được thật.

JPEG là định dạng tự đóng gói nên tách frame khỏi stream bằng cặp marker SOI/EOI
(``FF D8`` / ``FF D9``), không cần thư viện giải mã container nào cả.
'''
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SOI = b'\xff\xd8'
EOI = b'\xff\xd9'
DEFAULT_FPS = 6.0
DEFAULT_BOX = (330, 300)          # ô preview trong panel OCR
MAX_FRAMES = 3000                 # ~8 phút ở 6fps, hết dung lượng thì dừng nạp thêm


@dataclass
class PreviewInfo:
    video: Path
    width: int                    # kích thước gốc của video
    height: int
    duration_s: float
    fps: float
    out_w: int                    # kích thước frame đã thu nhỏ
    out_h: int
    total_frames: int


def _probe(video: Path) -> 'tuple[int, int, float, float]':
    '''(rộng, cao, giây, fps) — dùng đúng probe của app, tự bổ ffmpeg nếu thiếu.'''
    try:
        from app.services.media_probe import probe_video_details

        d = probe_video_details(video) or { }
        w = int(d.get('width') or 0)
        h = int(d.get('height') or 0)
        dur = float(d.get('duration_s') or 0.0)
        fps = float(d.get('fps') or 0.0)
        if w and h:
            return w, h, dur, fps
    except Exception as exc:                              # noqa: BLE001
        logger.debug('preview probe fail: %s', exc)
    return 0, 0, 0.0, 0.0


def fit_box(width: int, height: int, box: 'tuple[int, int]') -> 'tuple[int, int]':
    '''Thu (width,height) vào trong box, giữ nguyên tỉ lệ, không phóng to.

    Không upscale là có lý: ffmpeg được truyền
    ``scale=...:force_original_aspect_ratio=decrease`` cũng chỉ thu nhỏ, nên nếu ở
    đây tính lớn hơn thì số đo UI đưa ra sẽ không khớp frame thật mà ffmpeg trả về.
    '''
    bw, bh = box
    if not width or not height or not bw or not bh:
        return (bw, bh)
    ratio = min(1.0, bw / width, bh / height)
    return (max(16, int(width * ratio) // 2 * 2), max(16, int(height * ratio) // 2 * 2))


def build_command(video: 'str | Path', ffmpeg: 'str | Path', *, fps: float,
                  out_w: int, out_h: int) -> 'list[str]':
    '''Dòng ffmpeg xuất JPEG liên tiếp ra stdout. Hàm thuần để test được.'''
    return [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-i', str(video),
            '-an', '-sn', '-vf',
            f"fps=fps={fps:g},scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,setsar=1",
            '-f', 'image2pipe', '-vcodec', 'mjpeg', '-q:v', '7', 'pipe:1']


class FrameStream:
    '''Một tiến trình ffmpeg -> danh sách frame JPEG trong bộ nhớ, đọc tuần tự.

    Mọi hàm công khai đều không chặn lâu: ``get()`` trả None nếu ffmpeg chưa giải
    mã tới index đó để UI giữ khung hình cũ thay vì đơ.
    '''

    def __init__(self, video: 'str | Path', *, box: 'tuple[int, int]' = DEFAULT_BOX,
                 fps: float = DEFAULT_FPS, max_frames: int = MAX_FRAMES,
                 on_ready: 'Callable[[int], None] | None' = None):
        self.video = Path(video)
        self.box = box
        self.fps = float(fps)
        self.max_frames = int(max_frames)
        self.on_ready = on_ready
        self.info: PreviewInfo | None = None
        self.error: str | None = None
        self._frames: list[bytes] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: 'subprocess.Popen | None' = None

    # ------------------------------------------------------------- vòng đời
    def start(self) -> PreviewInfo:
        '''Do kích thước rồi spawn ffmpeg. Trả về metadata để UI dựng thanh trượt.'''
        if self._thread is not None:
            return self.info
        w, h, dur, src_fps = _probe(self.video)
        out_w, out_h = fit_box(w, h, self.box)
        total = int(dur * self.fps) if dur else 0
        self.info = PreviewInfo(self.video, w, h, dur, self.fps, out_w, out_h,
                                min(total, self.max_frames) if total else 0)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self.info

    def close(self) -> None:
        self._stop.set()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except OSError:
                    pass
        for stream in (getattr(proc, 'stdout', None), getattr(proc, 'stderr', None)):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass
        self._proc = None

    # ----------------------------------------------------------------- dữ liệu
    def ready(self) -> int:
        with self._lock:
            return len(self._frames)

    def get(self, index: int) -> 'bytes | None':
        with self._lock:
            if 0 <= index < len(self._frames):
                return self._frames[index]
        return None

    def index_for(self, seconds: float) -> int:
        if not self.info or self.fps <= 0:
            return 0
        i = int(round(max(0.0, float(seconds)) * self.fps))
        cap = self.info.total_frames or self.max_frames
        return max(0, min(i, cap - 1)) if cap else max(0, i)

    def seconds_for(self, index: int) -> float:
        return (index / self.fps) if self.fps else 0.0

    @property
    def exhausted(self) -> bool:
        '''ffmpeg đã kết thúc (xong video hoặc chạm trần max_frames).'''
        return self._stop.is_set() or (self._thread is not None and not self._thread.is_alive())

    # -------------------------------------------------------------------- nền
    def _run(self) -> None:
        info = self.info
        try:
            ffmpeg = shutil.which('ffmpeg')
            if not ffmpeg:
                self.error = 'không tìm thấy ffmpeg trong PATH'
                return
            if not info or not info.width:
                self.error = f'không đọc được metadata của {self.video.name}'
                return
            cmd = build_command(self.video, ffmpeg, fps=self.fps,
                                out_w=info.out_w, out_h=info.out_h)
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    bufsize=0, **({'creationflags': flags} if flags else { }))
            self._proc = proc
            buf = bytearray()
            while not self._stop.is_set():
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                buf += chunk
                while True:
                    end = buf.find(EOI)
                    if end < 0:
                        break
                    start = buf.find(SOI)
                    frame = bytes(buf[start:end + len(EOI)]) if start >= 0 and start < end else None
                    del buf[:end + len(EOI)]
                    if not frame:
                        continue
                    with self._lock:
                        if len(self._frames) >= self.max_frames:
                            self._stop.set()
                            break
                        self._frames.append(frame)
                        n = len(self._frames)
                    if self.on_ready is not None:
                        try:
                            self.on_ready(n)
                        except Exception:                         # noqa: BLE001
                            pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            if proc.returncode not in (0, None) and self.ready() == 0:
                err = b''
                try:
                    err = proc.stderr.read(2000) if proc.stderr else b''
                except Exception:
                    pass
                self.error = f'ffmpeg mã hoá lỗi ({proc.returncode}): {err.decode("utf-8", "replace").strip()[:180]}'
        except BaseException as exc:                         # noqa: BLE001
            self.error = f'{type(exc).__name__}: {exc}'
            logger.warning('FrameStream fail: %s', exc)
        finally:
            self.close()

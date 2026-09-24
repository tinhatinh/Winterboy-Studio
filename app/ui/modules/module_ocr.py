# -*- coding: utf-8 -*-
'''Module OCR — đọc phụ đề cứng trên video thành file .srt bằng VideOCR.

Khác với nhận diện giọng nói: OCR lấy đúng nguyên văn chữ đang hiện trên hình, nên
tên riêng và thuật ngữ không bị nghe sai (伯努利 -> Bernoulli, không phải "Fourier").

Phần xem trước đi theo đúng kiểu cửa sổ VideOCR: có khung hình chạy được, thanh
trượt thời gian bên dưới, và kéo chuột ngay trên ảnh để khoanh vùng phụ đề — vì
VideOCR chỉ đọc chữ nằm trong crop rect, khoanh đúng dải sub thì logo/credit đè
ngang không bị nhận luôn thành chữ.
'''
from __future__ import annotations

import io
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from app.core.state import AppState
from app.services import videocr_ocr, video_preview
from app.ui.modules.base_module import BaseModule, TEXT_DIM

LANGS = ('ch', 'zh', 'en', 'vi', 'ja', 'ko', 'th', 'id', 'pt', 'es', 'fr', 'de')
CANVAS_W = 330                 # bề rộng ô preview
CANVAS_H = 260                 # chiều cao ô preview
PREVIEW_FPS = 6.0              # frame/giây của luồng giải mã trước
MIN_EDGE_PX = 8                # vùng nhỏ hơn mức này coi như click chuột nhầm


def _fmt_s(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0))
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}'


class ModuleOcr(BaseModule):
    '''Thẻ OCR trong thanh điều khiển bên trái.'''

    def __init__(self, master, state: AppState, callbacks: 'dict'):
        # KHÔNG được đặt tên hàm dựng UI là "_setup": tkinter.Widget._setup(master, cnf)
        # là hàm nội bộ mà Frame.__init__ gọi lại — ghi đè trúng là vỡ lúc tạo widget.
        super().__init__(master, 'OCR phụ đề trên video')
        self.state = state
        self.cb = callbacks or { }
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()
        self._q = queue.Queue()

        self.var_video = ctk.StringVar(value='')
        self.var_lang = ctk.StringVar(value='ch')
        self.var_gpu = ctk.BooleanVar(value=True)
        self.var_min = ctk.StringVar(value='0.3')
        self.var_out = ctk.StringVar(value='')
        self.var_use_region = ctk.BooleanVar(value=False)

        # preview
        self._stream: video_preview.FrameStream | None = None
        self._photo = None
        self._img_id = None
        self._shown = (0, 0)
        self._src = (0, 0)
        self._index = 0
        self._playing = False
        self._tick_job = None
        self._play_base = 0
        self._play_t0 = 0.0
        self._poll_job = None
        self._drag = None
        self._rect_id = None
        self.region: 'tuple[int, int, int, int] | None' = None
        # bốn ô số là nguồn sự thật lúc chạy: kéo chuột chỉ là cách nhanh để điền chúng
        self.vars_crop = [ctk.StringVar(value='') for _ in range(4)]

        self._build_ui()
        self.sync_from_state()
        self.bind('<Destroy>', self._on_destroy, add='+')
        # mở thẻ là tự nạp preview, không bắt người dùng bấm thêm nút nào
        self.after(120, self._autoload)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.section('Video cần OCR', first = True)
        self.stack('Tệp video', lambda parent: ctk.CTkEntry(
            parent, textvariable = self.var_video, placeholder_text = 'chưa chọn video'))
        self.button_grid([
            ('Chọn video', self.pick_video, { }),
            ('Làm mới', self.sync_from_state, { })])
        self.hint('Mặc định lấy video đang mở ở module Video, khỏi chọn lại.')

        self.section('Engine VideOCR')
        self.field('Ngôn ngữ', lambda parent: ctk.CTkOptionMenu(parent, values = list(LANGS),
                                                                variable = self.var_lang, width = 120))
        self.checks([('Dùng GPU (CUDA)', self.var_gpu)])
        self.number_grid([('Trễ (s)', self.var_min)], columns = 1)
        # tự giữ reference thay vì đoán tên thuộc tính bên trong BaseModule
        self.lbl_engine = self.hint('đang dò VideOCR…')
        self.lbl_status = self.status_label()

        self.section('Xem trước & chọn vùng')
        self.canvas = ctk.CTkCanvas(self, width = CANVAS_W, height = CANVAS_H,
                                    bg = '#141416', highlightthickness = 1,
                                    highlightbackground = '#3A3A3A')
        self.canvas.pack(fill = 'x', padx = 10, pady = (2, 2))
        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_motion)
        self.canvas.bind('<ButtonRelease-1>', self._drag_end)
        self._draw_placeholder('Đang nạp khung hình…')

        bar = self.row()
        self.btn_play = ctk.CTkButton(bar, text = '▶  Phát', width = 74,
                                      command = self.toggle_play)
        self.btn_play.pack(side = 'left')
        self.lbl_time = ctk.CTkLabel(bar, text = '00:00 / 00:00', width = 104)
        self.lbl_time.pack(side = 'right')
        self.slider = ctk.CTkSlider(bar, from_ = 0, to = 1, number_of_steps = 1,
                                    command = self._on_scrub)
        self.slider.pack(side = 'left', fill = 'x', expand = True, padx = 6)

        self.checks([('Chỉ OCR vùng đã khoanh (bỏ chọn = nguyên khung hình)', self.var_use_region)])
        # kéo chuột chỉ là cách nhanh; 4 ô này mới là giá trị thật sự gửi cho VideOCR,
        # vì ảnh preview bị thu nhỏ nên kéo không thể chính xác từng pixel
        self.number_grid([('X', self.vars_crop[0]), ('Y', self.vars_crop[1]),
                          ('Rộng', self.vars_crop[2]), ('Cao', self.vars_crop[3])],
                         columns = 2, on_commit = self._crop_from_fields)
        self.button_grid([
            ('Nạp lại', self.load_preview, { }),
            ('Xoá vùng', self.clear_region, { })])
        self.lbl_region = self.hint('Kéo chuột lên khung hình để khoanh dải phụ đề.')

        self.section('Kết quả')
        self.stack('File .srt', lambda parent: ctk.CTkEntry(
            parent, textvariable = self.var_out, placeholder_text = 'chưa chạy OCR'))
        self.text = ctk.CTkTextbox(self, height = 170, wrap = 'none',
                                   font = ctk.CTkFont(family = 'Consolas', size = 12))
        self.text.pack(fill = 'both', expand = False, padx = 10, pady = (0, 8))
        self.text.configure(state = 'disabled')
        self.button_grid([
            ('Chạy OCR', self.run_ocr, { }),
            ('Dừng', self.stop, { 'fg_color': ('#DC2626', '#E95364') })])
        self.button_grid([
            ('Lưu .srt…', self.save_as, { }),
            ('Mở thư mục', self.reveal, { })])
        self.refresh_engine()

    # ------------------------------------------------------------- dữ liệu
    def sync_from_state(self) -> None:
        '''Lấy video đang mở trong app làm mặc định, và gợi ý tên file .srt.'''
        current = str(getattr(self.state, 'active_video_path', '') or '').strip()
        if not current:
            paths = list(getattr(self.state, 'video_paths', []) or [])
            current = str(paths[0]) if paths else ''
        if not (current and Path(current).is_file()):
            return
        if current != self.var_video.get():
            self.reset_preview()             # ảnh preview cũ là của video khác
            self.load_preview()
        self.var_video.set(current)
        if not self.var_out.get():
            self.var_out.set(str(Path(current).with_suffix('.ocr.srt')))

    def pick_video(self) -> None:
        path = filedialog.askopenfilename(
            title = 'Chọn video cần OCR',
            filetypes = [('Video', '*.mp4 *.mov *.mkv *.avi *.webm'), ('Tất cả', '*.*')])
        if path and path != self.var_video.get():
            self.var_video.set(path)
            if not self.var_out.get():
                self.var_out.set(str(Path(path).with_suffix('.ocr.srt')))
            self.reset_preview()
            self.load_preview()

    def refresh_engine(self) -> None:
        exe = videocr_ocr.find_videocr_cli(getattr(self.state, 'videocr_cli_path', None))
        self._set_text(self.lbl_engine, f'engine: {exe}' if exe else
                       '⚠ không thấy videocr-cli.exe — cài VideOCR hoặc đặt WINTERBOY_VIDEOCR',
                       TEXT_DIM)

    def _set_text(self, label, text, color = None) -> None:
        try:
            label.configure(text = text, **({'text_color': color} if color else { }))
        except Exception:
            pass

    # ------------------------------------------------------------- preview
    def _autoload(self) -> None:
        if not self.winfo_exists():
            return
        if self._stream is None and Path(self.var_video.get() or '').is_file():
            self.load_preview()

    def load_preview(self) -> None:
        '''Spawn một ffmpeg duy nhất giải mã cả video; từ đó scrub là ăn ngay.'''
        video = Path(self.var_video.get() or '')
        if not video.is_file():
            self._status('Chọn video trước đã.')
            self._draw_placeholder('Chưa có video — chọn ở mục "Video cần OCR"')
            return
        self._stop_playback()
        if self._stream is not None:
            self._stream.close()
        self._index = 0
        try:
            stream = video_preview.FrameStream(video, box = (CANVAS_W, CANVAS_H),
                                               fps = PREVIEW_FPS)
            info = stream.start()
        except Exception as exc:                            # noqa: BLE001
            self._status(f'Lỗi preview: {exc}')
            self._draw_placeholder('Lỗi khi mở video')
            return
        if not info.width:
            self._status('Không đọc được kích thước video.')
            self._draw_placeholder('Không đọc được video')
            return
        self._stream = stream
        self._src = (info.width, info.height)
        total = max(1, info.total_frames)
        try:
            self.slider.configure(to = total - 1, number_of_steps = max(1, total - 1))
        except Exception:
            pass
        self._update_time()
        self._status(f'Đang giải mã preview… (fps {info.fps:g}, {info.total_frames} ảnh)')
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
        self._poll_job = self.after(60, self._poll_stream)

    def _poll_stream(self) -> None:
        stream = self._stream
        if stream is None or not self.winfo_exists():
            return
        ready = stream.ready()
        if ready:
            want = min(self._index, ready - 1)
            if want != self._index:
                self._index = want
            self._show_index(self._index)
        if stream.error:
            self._status(f'Lỗi preview: {stream.error}')
            self._draw_placeholder('ffmpeg không mở được video')
            return
        if ready >= (stream.info.total_frames if stream.info else 0) or stream.exhausted:
            self._poll_job = None
            if self._playing:
                self._status('Đang phát…')
            else:
                self._status(f'Preview sẵn sàng: {ready} ảnh')
            return
        total = stream.info.total_frames if stream.info else 0
        self._status(f'Đang giải mã preview… {ready}/{total}')
        self._poll_job = self.after(120, self._poll_stream)

    def _show_index(self, index: int) -> None:
        stream = self._stream
        if stream is None:
            return
        data = stream.get(index)
        if not data:
            return
        try:
            from PIL import Image, ImageTk

            img = Image.open(io.BytesIO(data))
            img.load()
            photo = ImageTk.PhotoImage(img)
        except Exception as exc:                            # noqa: BLE001
            self._status(f'Lỗi hiển thị: {exc}')
            return
        self._index = index
        self._photo = photo
        self._shown = (photo.width(), photo.height())
        if self._img_id is None:
            self.canvas.delete('all')
            # vẽ tại (0,0) để toạ độ chuột trên canvas == toạ độ ảnh: lệch 2px cũng
            # làm crop dịch ~16px theo video, đủ để xén mất hàng chữ trên cùng
            self._img_id = self.canvas.create_image(0, 0, anchor = 'nw', image = photo)
        else:
            self.canvas.itemconfigure(self._img_id, image = photo)
        self.canvas.tag_raise(self._img_id)
        self._redraw_rect()
        self._update_time()

    def _draw_placeholder(self, text: str) -> None:
        try:
            self.canvas.delete('all')
        except Exception:
            return
        self._img_id = None
        self._rect_id = None
        self._photo = None
        self._shown = (0, 0)
        self.canvas.create_text(CANVAS_W // 2, CANVAS_H // 2, text = text, fill = '#6B6B6B',
                                justify = 'center', width = CANVAS_W - 40)

    def _update_time(self) -> None:
        stream = self._stream
        if not stream or not stream.info:
            self._set_text(self.lbl_time, '00:00 / 00:00')
            return
        cur = stream.seconds_for(self._index)
        end = stream.info.duration_s or stream.seconds_for(max(0, stream.info.total_frames - 1))
        self._set_text(self.lbl_time, f'{_fmt_s(cur)} / {_fmt_s(end)}')

    # ------------------------------------------------------------- phát lại
    def toggle_play(self) -> None:
        if self._playing:
            self._stop_playback()
            return
        stream = self._stream
        if stream is None:
            self._status('Chưa có preview để phát.')
            return
        if stream.ready() == 0:
            self._status('Preview đang giải mã, đợi thêm giây.')
            self._poll_stream()
            return
        self._playing = True
        self._play_base = self._index
        self._play_t0 = time.perf_counter()
        try:
            self.btn_play.configure(text = '⏸  Tạm dừng')
        except Exception:
            pass
        self._schedule_tick()

    def _schedule_tick(self) -> None:
        self._tick_job = self.after(max(16, int(1000 / PREVIEW_FPS)), self._tick)

    def _tick(self) -> None:
        if not self._playing or self._stream is None or not self.winfo_exists():
            return
        stream = self._stream
        total = stream.info.total_frames if stream.info else 0
        # index tính theo ĐỒNG HỒ thật, không theo số lần tick: callback `after` của
        # Tk bị trễ khi event loop bận, mà đếm tick thì phim mỗi lúc một chạy chậm
        target = self._play_base + int((time.perf_counter() - self._play_t0) * PREVIEW_FPS)
        if total and target >= total:
            self._show_index(total - 1)
            self._stop_playback()
            self._status('Hết preview.')
            return
        if target < 0:
            target = 0
        if stream.get(target) is None:
            # ffmpeg chưa giải mã tới đây: giữ khung hình cũ và chỉnh lại mốc thời
            # gian để không bị "nợ" khung hình, chạy tiếp khi buffer theo kịp
            self._play_base = self._index
            self._play_t0 = time.perf_counter()
            self._status('đang chờ giải mã…')
            self._schedule_tick()
            return
        if target != self._index:
            self._show_index(target)
            try:
                self.slider.set(target)
            except Exception:
                pass
        self._schedule_tick()

    def _stop_playback(self) -> None:
        self._playing = False
        if self._tick_job is not None:
            try:
                self.after_cancel(self._tick_job)
            except Exception:
                pass
            self._tick_job = None
        try:
            self.btn_play.configure(text = '▶  Phát')
        except Exception:
            pass

    def _on_scrub(self, value) -> None:
        '''Kéo thanh trượt: chỉ đổi index trong bộ nhớ đã giải mã nên không delay.'''
        try:
            index = int(float(value))
        except (TypeError, ValueError):
            return
        if self._stream is not None:
            self._show_index(index)
            if self._playing:
                # vừa nhảy tới chỗ khác thì đặt lại mốc, không để _tick kéo về
                # đoạn cũ theo đồng hồ cũ
                self._play_base = index
                self._play_t0 = time.perf_counter()

    # ------------------------------------------------------------ kéo chuột
    def _drag_start(self, event) -> None:
        if not self._photo:
            self._status('Chưa có khung hình để khoanh.')
            return
        self._drag = (event.x, event.y)
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
            self._rect_id = None

    def _drag_motion(self, event) -> None:
        if not self._drag:
            return
        x0, y0 = self._drag
        if self._rect_id is None:
            self._rect_id = self.canvas.create_rectangle(x0, y0, event.x, event.y,
                                                         outline = '#F0A020', width = 2,
                                                         dash = (5, 3))
        else:
            self.canvas.coords(self._rect_id, x0, y0, event.x, event.y)

    def _drag_end(self, event) -> None:
        if not self._drag:
            return
        x0, y0 = self._drag
        self._drag = None
        region = self._to_source(x0, y0, event.x, event.y)
        if region is None:
            if self._rect_id is not None:
                self.canvas.delete(self._rect_id)
                self._rect_id = None
            self.region = None
            self._set_fields(None)
            self._set_text(self.lbl_region, f'Vùng quá nhỏ (tối thiểu {MIN_EDGE_PX}px) — kéo to hơn.')
            return
        # Tk không hứa có một lần <B1-Motion> cuối trước khi nhả chuột, nên ô vẽ phải
        # được kéo tới đúng điểm thả — nếu không vùng thật và ô nhìn thấy lệch nhau.
        if self._rect_id is None:
            self._rect_id = self.canvas.create_rectangle(x0, y0, event.x, event.y,
                                                         outline = '#F0A020', width = 2,
                                                         dash = (5, 3))
        else:
            self.canvas.coords(self._rect_id, x0, y0, event.x, event.y)
        self.region = region
        self._set_fields(region)
        self.var_use_region.set(True)
        self._report_region()

    def _to_source(self, x0: float, y0: float, x1: float, y1: float):
        '''Pixel trên canvas -> pixel gốc của video (logic nằm ở videocr_ocr, có test).'''
        return videocr_ocr.crop_from_drag(x0, y0, x1, y1, shown = self._shown,
                                          source = self._src, min_edge = MIN_EDGE_PX)

    # ------------------------------------------------------- 4 ô số của vùng
    def _set_fields(self, crop) -> None:
        values = ('', '', '', '') if not crop else tuple(str(int(v)) for v in crop)
        for var, value in zip(self.vars_crop, values):
            try:
                var.set(value)
            except Exception:
                pass

    def typed_crop(self) -> 'tuple[int, int, int, int] | None':
        '''Vùng đọc từ 4 ô số: tay nhập thẳng cũng chạy, không bắt buộc phải kéo chuột.'''
        try:
            x, y, w, h = (int(float(var.get().strip())) for var in self.vars_crop)
        except (ValueError, TypeError):
            return None
        if w < MIN_EDGE_PX or h < MIN_EDGE_PX or x < 0 or y < 0:
            return None
        return (x, y, w, h)

    def _crop_from_fields(self) -> None:
        '''Người sửa ô số -> vẽ lại rect và cập nhật nhãn (kéo chuột là chiều ngược lại).'''
        self.region = self.typed_crop()
        if self._photo:
            if self._rect_id is not None:
                try:
                    self.canvas.delete(self._rect_id)
                except Exception:
                    pass
                self._rect_id = None
            self._redraw_rect()
        self._report_region()

    def clear_region(self) -> None:
        self.region = None
        self._set_fields(None)
        if self._rect_id is not None:
            try:
                self.canvas.delete(self._rect_id)
            except Exception:
                pass
            self._rect_id = None
        self._report_region()

    def _redraw_rect(self) -> None:
        sw, sh = self._src
        dw, dh = self._shown
        crop = self.typed_crop()
        self.region = crop
        if self._rect_id is not None:
            try:
                self.canvas.delete(self._rect_id)
            except Exception:
                pass
            self._rect_id = None
        if not (crop and sw and sh and dw and dh):
            return
        x, y, w, h = crop
        self._rect_id = self.canvas.create_rectangle(x * dw / sw, y * dh / sh,
                                                     (x + w) * dw / sw, (y + h) * dh / sh,
                                                     outline = '#F0A020', width = 2, dash = (5, 3))
        self.canvas.tag_raise(self._rect_id)

    def _report_region(self) -> None:
        crop = self.typed_crop()
        if not crop:
            self._set_text(self.lbl_region, 'OCR nguyên khung hình (chưa khoanh vùng).')
            return
        x, y, w, h = crop
        note = '' if not self._src[0] else f' · video {self._src[0]}×{self._src[1]}'
        outside = bool(self._src[0] and self._src[1] and (x + w > self._src[0] or y + h > self._src[1]))
        self._set_text(self.lbl_region,
                       f'vùng gốc: x={x} y={y} {w}×{h}px{note}'
                       + ('  ⚠ tràn ra ngoài khung hình' if outside else ''))

    def reset_preview(self) -> None:
        '''Quên ảnh + vùng đang chọn (đổi video thì không dùng lại được nữa).'''
        self._stop_playback()
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        self.region = None
        self._set_fields(None)
        self._src = (0, 0)
        self._index = 0
        self._draw_placeholder('Đang nạp khung hình…')

    def _on_destroy(self, _event = None) -> None:
        self._stop_playback()
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def on_tab_deactivated(self) -> None:
        '''ControlPanel gọi khi chuyển sang thẻ khác: dừng phát cho đỡ tốn CPU.'''
        self._stop_playback()

    # ---------------------------------------------------------------- chạy
    def current_crop(self) -> 'tuple[int, int, int, int] | None':
        '''Vùng thực sự truyền cho VideOCR; None là OCR cả khung hình.'''
        if not self.var_use_region.get():
            return None
        return self.typed_crop()

    def run_ocr(self) -> None:
        if self._worker and self._worker.is_alive():
            self._status('OCR đang chạy, đợi hoặc bấm Dừng.')
            return
        video = Path(self.var_video.get() or '')
        if not video.is_file():
            self._status('Chọn video trước đã.')
            return
        out = Path(self.var_out.get() or '') or video.with_suffix('.ocr.srt')
        try:
            min_dur = float(self.var_min.get() or 0.3)
        except ValueError:
            self._status('Ô "Trễ (s)" phải là số, vd 0.3')
            return
        crop = self.current_crop()
        if self.var_use_region.get() and not crop:
            self._status('Bật "chỉ OCR vùng" mà chưa khoanh — kéo chuột lên preview hoặc nhập 4 ô.')
            return

        opts = videocr_ocr.OcrOptions(lang = self.var_lang.get() or 'ch',
                                      use_gpu = bool(self.var_gpu.get()),
                                      min_subtitle_duration = min_dur, crop = crop)
        self._stop_playback()
        self._cancel.clear()
        self.text.configure(state = 'normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state = 'disabled')
        self._status(f'Đang OCR… (vùng: {crop if crop else "cả hình"})')
        self._worker = threading.Thread(target = self._work, args = (video, out, opts),
                                        daemon = True)
        self._worker.start()
        # chỉ luồng chính được đụng widget: nền đẩy việc vào hàng đợi, luồng chính hút nó
        self.after(80, self._pump)

    def _work(self, video: Path, out: Path, opts) -> None:
        '''Chạy ở thread nền — KHÔNG gọi widget hay self.after từ đây.'''
        try:
            res = videocr_ocr.run_ocr(video, out, opts = opts, cancel_event = self._cancel,
                                      progress = lambda frac, label: self._q.put(('tick', frac, label)))
        except BaseException as exc:                       # noqa: BLE001
            self._q.put(('crash', f'{type(exc).__name__}: {exc}'))
            return
        self._q.put(('done', res))

    def _pump(self) -> None:
        try:
            while True:
                item = self._q.get_nowait()
                if item[0] == 'tick':
                    self._progress(item[1], item[2])
                elif item[0] == 'crash':
                    self._status(f'Lỗi: {item[1]}')
                elif item[0] == 'done':
                    self._finish(item[1])
        except queue.Empty:
            pass
        if self._worker and self._worker.is_alive():
            self.after(80, self._pump)

    def stop(self) -> None:
        if self._worker and self._worker.is_alive():
            self._cancel.set()
            self._status('Đang dừng…')

    # ----------------------------------------------------------- hiển thị
    def _finish(self, res) -> None:
        if not res.ok:
            self._status(f'Lỗi: {res.error}')
            detail = '\n'.join(res.log_tail[-6:])
            if detail:
                self.text.insert('end', detail)
            self.text.configure(state = 'disabled')
            return
        self.var_out.set(str(res.srt_path))
        self._status(f'Xong: {res.n_cues} cue, {res.duration_s:.1f}s nội dung')
        self.text.insert('end', '\n'.join(
            f'[{c.start_s:7.2f} → {c.end_s:7.2f}]  {c.text}' for c in res.cues))
        self.text.configure(state = 'disabled')

    def _progress(self, frac, label) -> None:
        self._status(f'{frac * 100:5.1f}%  {label}')

    def save_as(self) -> None:
        src = Path(self.var_out.get() or '')
        if not src.is_file():
            self._status('Chưa có file SRT — chạy OCR trước.')
            return
        dst = filedialog.asksaveasfilename(title = 'Lưu file SRT', defaultextension = '.srt',
                                           filetypes = [('SubRip', '*.srt')],
                                           initialfile = src.name)
        if dst:
            Path(dst).write_text(src.read_text(encoding = 'utf-8'), encoding = 'utf-8')
            self._status(f'Đã lưu: {dst}')

    def reveal(self) -> None:
        src = Path(self.var_out.get() or '')
        folder = src.parent if src.is_file() else Path(self.var_video.get() or '.').parent
        if folder.exists():
            import os
            os.startfile(str(folder))                       # chỉ Windows, đúng như app

    def _status(self, text) -> None:
        '''Chỉ được gọi từ luồng chính (nền đẩy việc qua _pump).'''
        self._set_text(self.lbl_status, text)

# -*- coding: utf-8 -*-
'''Module OCR — đọc phụ đề cứng trên video thành file .srt bằng VideOCR.

Khác với nhận diện giọng nói: OCR lấy đúng nguyên văn chữ đang hiện trên hình, nên
tên riêng và thuật ngữ không bị nghe sai (伯努利 -> Bernoulli, không phải "Fourier").

Có ô xem trước khung hình để KÉO CHUỘT khoanh vùng phụ đề: VideOCR chỉ đọc chữ nằm
trong crop rect, nên khoanh đúng dải sub thì logo/credit đè ngang không bị nhận
luôn thành chữ.
'''
from __future__ import annotations

import queue
import tempfile
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from app.core.state import AppState
from app.services import videocr_ocr
from app.ui.modules.base_module import BaseModule, TEXT_DIM

LANGS = ('ch', 'zh', 'en', 'vi', 'ja', 'ko', 'th', 'id', 'pt', 'es', 'fr', 'de')
CANVAS_H = 300                 # chiều cao tối đa của ô preview
CANVAS_W = 330                 # bề rộng mong muốn; panel có hẹp hơn thì ảnh co theo
MIN_EDGE_PX = 8                # vùng nhỏ hơn mức này coi như click chuột nhầm


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
        self.var_t = ctk.StringVar(value='1.0')
        self.var_use_region = ctk.BooleanVar(value=False)

        # ảnh preview + vùng đã kéo. region luôn tính bằng pixel GỐC của video,
        # không phụ thuộc ảnh preview to hay nhỏ.
        self._photo = None
        self._frame_path: Path | None = None
        self._img_id = None
        self._shown = (0, 0)
        self._src = (0, 0)
        self._rect_id = None
        self._drag = None
        self.region: 'tuple[int, int, int, int] | None' = None
        # bốn ô số là nguồn sự thật lúc chạy: kéo chuột chỉ là cách nhanh để điền chúng
        self.vars_crop = [ctk.StringVar(value='') for _ in range(4)]

        self._build_ui()
        self.sync_from_state()

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
        self.field('Giây', lambda parent: ctk.CTkEntry(parent, textvariable = self.var_t, width = 64),
                   trailing = lambda parent: ctk.CTkButton(parent, text = 'Nạp preview',
                                                            command = self.load_frame))
        self.canvas = ctk.CTkCanvas(self, width = CANVAS_W, height = 200, bg = '#1B1B1D',
                                    highlightthickness = 1, highlightbackground = '#3A3A3A')
        self.canvas.pack(fill = 'x', padx = 10, pady = (2, 4))
        self.canvas.bind('<ButtonPress-1>', self._drag_start)
        self.canvas.bind('<B1-Motion>', self._drag_motion)
        self.canvas.bind('<ButtonRelease-1>', self._drag_end)
        self.canvas.bind('<Configure>', self._on_resize)
        self.checks([('Chỉ OCR vùng đã khoanh (bỏ chọn = nguyên khung hình)', self.var_use_region)])
        # kéo chuột chỉ là cách nhanh; 4 ô này mới là giá trị thật sự gửi cho VideOCR,
        # vì ảnh preview bị thu nhỏ nên kéo không thể chính xác từng pixel
        self.number_grid([('X', self.vars_crop[0]), ('Y', self.vars_crop[1]),
                          ('Rộng', self.vars_crop[2]), ('Cao', self.vars_crop[3])],
                         columns = 2, on_commit = self._crop_from_fields)
        self.button_grid([
            ('Nạp lại', self.load_frame, { }),
            ('Xoá vùng', self.clear_region, { })])
        self.lbl_region = self.hint('chưa có ảnh — bấm “Nạp preview” rồi kéo chuột lên dải phụ đề.')

        self.section('Kết quả')
        self.stack('File .srt', lambda parent: ctk.CTkEntry(
            parent, textvariable = self.var_out, placeholder_text = 'chưa chạy OCR'))
        self.text = ctk.CTkTextbox(self, height = 180, wrap = 'none',
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
            self.reset_preview()             # ảnhpreview cũ là của video khác
        self.var_video.set(current)
        if not self.var_out.get():
            self.var_out.set(str(Path(current).with_suffix('.ocr.srt')))

    def pick_video(self) -> None:
        path = filedialog.askopenfilename(
            title = 'Chọn video cần OCR',
            filetypes = [('Video', '*.mp4 *.mov *.mkv *.avi *.webm'), ('Tất cả', '*.*')])
        if path:
            self.reset_preview()
            self.var_video.set(path)
            if not self.var_out.get():
                self.var_out.set(str(Path(path).with_suffix('.ocr.srt')))

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
    def load_frame(self) -> None:
        '''Xuất một khung hình bằng ffmpeg rồi vẽ lên canvas (nền, không đơ UI).'''
        if self._worker and self._worker.is_alive():
            self._status('Đang có việc chạy, đợi chút.')
            return
        video = Path(self.var_video.get() or '')
        if not video.is_file():
            self._status('Chọn video trước đã.')
            return
        try:
            at_s = max(0.0, float(self.var_t.get() or 0))
        except ValueError:
            self._status('Ô "Giây" phải là số, vd 1.0')
            return
        self._status('Đang lấy khung hình…')
        self._worker = threading.Thread(target = self._work_frame, args = (video, at_s),
                                        daemon = True)
        self._worker.start()
        self.after(80, self._pump)

    def _work_frame(self, video: Path, at_s: float) -> None:
        '''Chạy ở thread nền — KHÔNG gọi widget hay self.after từ đây.'''
        try:
            # dùng đúng hàm của app để không nhân bản logic ffmpeg ra hai nơi
            from app.services.media_probe import probe_video_size
            from app.ui.widgets.blur_region_editor import extract_video_frame

            out = Path(tempfile.gettempdir()) / 'winterboy_ocr_preview.jpg'
            if not extract_video_frame(video, out, t_s = at_s) or not out.is_file():
                self._q.put(('frame', None, 'ffmpeg không xuất được khung hình'))
                return
            self._q.put(('frame', (out, tuple(probe_video_size(video) or ( ))), None))
        except BaseException as exc:                       # noqa: BLE001
            self._q.put(('frame', None, f'{type(exc).__name__}: {exc}'))

    def _show_frame(self, payload, error) -> None:
        if error or not payload:
            self._status(f'Lỗi preview: {error or "không rõ"}')
            return
        out, src = payload
        width = max(120, min(CANVAS_W, self.canvas.winfo_width() or CANVAS_W))
        img = self._open_scaled(out, width)
        if img is None:
            return
        self._frame_path = out
        self._src = (int(src[0]), int(src[1])) if len(src) >= 2 and src[0] and src[1] else (0, 0)
        if not self._src[0]:
            from app.services.media_probe import probe_video_size
            self._src = tuple(probe_video_size(Path(self.var_video.get() or '')) or (0, 0))
        self._paint(img)
        self._status('Kéo chuột lên ảnh để khoanh đúng dải phụ đề.')
        self._report_region()

    def _open_scaled(self, path: Path, width: int):
        '''Mở JPEG preview và co về vừa ô canvas (both chiều), giữ nguyên tỉ lệ.'''
        try:
            from PIL import Image, ImageTk

            img = Image.open(path)
            ratio = min(1.0, width / max(1, img.width), CANVAS_H / max(1, img.height))
            img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))),
                             Image.LANCZOS)
            return ImageTk.PhotoImage(img), (img.width, img.height)
        except Exception as exc:                            # noqa: BLE001
            self._status(f'Lỗi hiển thị preview: {exc}')
            return None

    def _paint(self, painted) -> None:
        photo, (w, h) = painted
        self._photo = photo
        self._shown = (w, h)
        self.canvas.delete('all')
        self._img_id = self.canvas.create_image(0, 0, anchor = 'nw', image = self._photo)
        self._rect_id = None
        self._redraw_rect()

    def reset_preview(self) -> None:
        '''Quên ảnh + vùng đang chọn (đổi video thì không dùng lại được nữa).'''
        self.region = None
        self._set_fields(None)
        self._photo = None
        self._frame_path = None
        self._shown = (0, 0)
        self._src = (0, 0)
        self._img_id = None
        self._rect_id = None
        try:
            self.canvas.delete('all')
        except Exception:
            pass
        self._report_region()

    # ------------------------------------------------------------ kéo chuột
    def _drag_start(self, event) -> None:
        if not self._photo:
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
            if self.region:
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

    def _on_resize(self, _event = None) -> None:
        '''Panel co/giãn thì vẽ lại ảnh theo bề rộng mới; vùng kéo quy về gốc nên không lệch.'''
        if not self._frame_path:
            return
        width = max(120, min(CANVAS_W, self.canvas.winfo_width() or 0))
        if abs(width - self._shown[0]) <= 2:
            return
        painted = self._open_scaled(self._frame_path, width)
        if painted:
            self._paint(painted)

    def _redraw_rect(self) -> None:
        if not self.region:
            return
        sw, sh = self._src
        dw, dh = self._shown
        if not (sw and sh and dw and dh):
            return
        x, y, w, h = self.region
        self._rect_id = self.canvas.create_rectangle(x * dw / sw, y * dh / sh,
                                                     (x + w) * dw / sw, (y + h) * dh / sh,
                                                     outline = '#F0A020', width = 2, dash = (5, 3))

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

    def current_crop(self) -> 'tuple[int, int, int, int] | None':
        '''Vùng thực sự truyền cho VideOCR; None là OCR cả khung hình.'''
        if not self.var_use_region.get():
            return None
        return self.typed_crop()

    # ---------------------------------------------------------------- chạy
    def run_ocr(self) -> None:
        if self._worker and self._worker.is_alive():
            self._status('OCR/preview đang chạy, đợi hoặc bấm Dừng.')
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
            self._status('Bật "chỉ OCR vùng" mà chưa khoanh — nạp preview rồi kéo chuột.')
            return

        opts = videocr_ocr.OcrOptions(lang = self.var_lang.get() or 'ch',
                                      use_gpu = bool(self.var_gpu.get()),
                                      min_subtitle_duration = min_dur, crop = crop)
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
                elif item[0] == 'frame':
                    self._show_frame(item[1], item[2])
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

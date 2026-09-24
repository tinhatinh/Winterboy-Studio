# -*- coding: utf-8 -*-
'''Module OCR — đọc phụ đề cứng trên video thành file .srt bằng VideOCR.

Khác với nhận diện giọng nói: OCR lấy đúng nguyên văn chữ đang hiện trên hình, nên
tên riêng và thuật ngữ không bị nghe sai (伯努利 -> Bernoulli, không phải "Fourier").

Module này chỉ làm một việc: video vào, .srt ra. Không tự đụng vào ô phụ đề hay
trạng thái dịch của các module khác.
'''
from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from app.core.state import AppState
from app.services import videocr_ocr
from app.ui.modules.base_module import BaseModule, TEXT_DIM

LANGS = ('ch', 'zh', 'en', 'vi', 'ja', 'ko', 'th', 'id', 'pt', 'es', 'fr', 'de')


class ModuleOcr(BaseModule):
    '''Thẻ OCR trong thanh điều khiển bên trái.'''

    def __init__(self, master, state: AppState, callbacks: 'dict'):
        # KHÔNG được đặt tên hàm dựng UI là "_setup": tkinter.Widget._setup(master, cnf)
        # là hàm nội bộ mà Frame.__init__ gọi lại — ghi đè là vỡ lúc tạo widget.
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
        if current and Path(current).is_file():
            self.var_video.set(current)
            if not self.var_out.get():
                self.var_out.set(str(Path(current).with_suffix('.ocr.srt')))

    def pick_video(self) -> None:
        path = filedialog.askopenfilename(
            title = 'Chọn video cần OCR',
            filetypes = [('Video', '*.mp4 *.mov *.mkv *.avi *.webm'), ('Tất cả', '*.*')])
        if path:
            self.var_video.set(path)
            if not self.var_out.get():
                self.var_out.set(str(Path(path).with_suffix('.ocr.srt')))

    def refresh_engine(self) -> None:
        exe = videocr_ocr.find_videocr_cli(getattr(self.state, 'videocr_cli_path', None))
        try:
            self.lbl_engine.configure(
                text = f'engine: {exe}' if exe else
                       '⚠ không thấy videocr-cli.exe — cài VideOCR hoặc đặt WINTERBOY_VIDEOCR',
                text_color = TEXT_DIM)
        except Exception:
            pass

    # ---------------------------------------------------------------- chạy
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

        opts = videocr_ocr.OcrOptions(lang = self.var_lang.get() or 'ch',
                                      use_gpu = bool(self.var_gpu.get()),
                                      min_subtitle_duration = min_dur)
        self._cancel.clear()
        self.text.configure(state = 'normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state = 'disabled')
        self._status('Đang OCR…')
        self._worker = threading.Thread(target = self._work, args = (video, out, opts),
                                        daemon = True)
        self._worker.start()
        # chỉ luồng chính được đụng widget: nền bỏ việc vào hàng đợi, luồng chính hút nó
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
        try:
            self.lbl_status.configure(text = text)
        except Exception:
            pass

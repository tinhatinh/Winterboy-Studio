# -*- coding: utf-8 -*-
'''Công cụ OCR độc lập của Winterboy Studio — chạy VideOCR, xuất file .srt.

Chạy bằng cách double-click (hoặc `python ocr_tool.pyw`) khi app đặt ở thư mục này:
nó nạp thẳng module trong ``_internal`` nên dùng chung engine với app, không cần
build lại. Lý do tồn tại riêng: mục "OCR" trên thanh bên phải chờ khôi phục
control_panel, còn nhu cầu OCR thì cần ngay.
'''
from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTERNAL = HERE / '_internal'
if INTERNAL.is_dir():
    sys.path.insert(0, str(INTERNAL))
else:                                      # chạy từ repo khi chưa có _internal
    sys.path.insert(0, str(HERE))

import customtkinter as ctk                 # noqa: E402
from tkinter import filedialog              # noqa: E402

from app.services.videocr_ocr import (      # noqa: E402
    OcrOptions, find_videocr_cli, run_ocr)

LANGS = ('ch', 'zh', 'en', 'vi', 'ja', 'ko', 'th', 'id', 'pt', 'es', 'fr', 'de')
VIDEO_TYPES = [('Video', '*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v'), ('Tất cả', '*.*')]


class OcrWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Winterboy OCR — lấy phụ đề cứng trên video')
        self.geometry('760x620')
        self.minsize(620, 480)
        ctk.set_appearance_mode('dark')

        self.var_video = ctk.StringVar()
        self.var_out = ctk.StringVar()
        self.var_lang = ctk.StringVar(value='ch')
        self.var_gpu = ctk.BooleanVar(value=True)
        self.var_min = ctk.StringVar(value='0.3')
        self._cancel = threading.Event()
        self._worker = None
        self._q = queue.Queue()

        self._build()
        self._set_engine()

    # ------------------------------------------------------------------- UI
    def _build(self):
        grid = ctk.CTkFrame(self, fg_color='transparent')
        grid.pack(fill='both', expand=True, padx=14, pady=12)
        grid.columnconfigure(1, weight=1)

        row = 0
        self._entry_row(grid, row, 'Video', self.var_video, self.pick_video); row += 1
        self._entry_row(grid, row, 'Lưu .srt', self.var_out, self.pick_out); row += 1

        opts = ctk.CTkFrame(grid, fg_color='transparent')
        opts.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(10, 4)); row += 1
        ctk.CTkLabel(opts, text='Ngôn ngữ').pack(side='left', padx=(0, 6))
        ctk.CTkOptionMenu(opts, values=list(LANGS), variable=self.var_lang,
                          width=110).pack(side='left')
        ctk.CTkCheckBox(opts, text='Dùng GPU', variable=self.var_gpu).pack(side='left', padx=14)
        ctk.CTkLabel(opts, text='Trễ (s)').pack(side='left')
        ctk.CTkEntry(opts, textvariable=self.var_min, width=64).pack(side='left', padx=(4, 0))

        self.bar = ctk.CTkProgressBar(grid)
        self.bar.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(6, 2)); row += 1
        self.bar.set(0)
        self.status = ctk.CTkLabel(grid, text='sẵn sàng', anchor='w')
        self.status.grid(row=row, column=0, columnspan=2, sticky='ew'); row += 1

        self.text = ctk.CTkTextbox(grid, wrap='none',
                                   font=ctk.CTkFont(family='Consolas', size=12))
        self.text.grid(row=row, column=0, columnspan=2, sticky='nsew', pady=(8, 6)); row += 1
        grid.rowconfigure(row - 1, weight=1)
        self.text.configure(state='disabled')

        btns = ctk.CTkFrame(grid, fg_color='transparent')
        btns.grid(row=row, column=0, columnspan=2, sticky='ew'); row += 1
        self.btn_run = ctk.CTkButton(btns, text='Chạy OCR', width=130, command=self.start)
        self.btn_run.pack(side='left')
        ctk.CTkButton(btns, text='Dừng', width=90, fg_color=('#DC2626', '#E95364'),
                      command=self.stop).pack(side='left', padx=8)
        ctk.CTkButton(btns, text='Mở thư mục', width=110,
                      fg_color='transparent', hover_color=('#CBD5E1', '#454545'),
                      border_width=1, command=self.reveal).pack(side='left')

    def _entry_row(self, parent, r, label, var, command):
        ctk.CTkLabel(parent, text=label, width=86, anchor='w').grid(
            row=r, column=0, sticky='w', pady=3)
        box = ctk.CTkFrame(parent, fg_color='transparent')
        box.grid(row=r, column=1, sticky='ew')
        box.columnconfigure(0, weight=1)
        ctk.CTkEntry(box, textvariable=var).grid(row=0, column=0, sticky='ew')
        ctk.CTkButton(box, text='…', width=34, command=command).grid(row=0, column=1, padx=(6, 0))

    def _set_engine(self):
        exe = find_videocr_cli()
        if exe:
            self._say(f'engine: {exe}')
        else:
            self._say('⚠ không thấy videocr-cli.exe — cài VideOCR hoặc đặt biến '
                      'WINTERBOY_VIDEOCR', err=True)

    # --------------------------------------------------------------- action
    def pick_video(self):
        p = filedialog.askopenfilename(title='Chọn video', filetypes=VIDEO_TYPES)
        if p:
            self.var_video.set(p)
            if not self.var_out.get():
                self.var_out.set(str(Path(p).with_suffix('.ocr.srt')))
            self._set_engine()

    def pick_out(self):
        p = filedialog.asksaveasfilename(title='Lưu file .srt', defaultextension='.srt',
                                         filetypes=[('SubRip', '*.srt')],
                                         initialfile='subtitles.srt')
        if p:
            self.var_out.set(p)

    def start(self):
        if self._worker and self._worker.is_alive():
            self._say('đang chạy, đợi hoặc bấm Dừng', err=True)
            return
        video = Path(self.var_video.get() or '')
        if not video.is_file():
            self._say('chọn video trước đã', err=True)
            return
        out = Path(self.var_out.get() or '') or video.with_suffix('.ocr.srt')
        try:
            min_dur = float(self.var_min.get() or 0.3)
        except ValueError:
            self._say('ô "Trễ (s)" phải là số', err=True)
            return
        opts = OcrOptions(lang=self.var_lang.get() or 'ch', use_gpu=bool(self.var_gpu.get()),
                          min_subtitle_duration=min_dur)
        self._cancel.clear()
        self.bar.set(0)
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state='disabled')
        self._say('đang OCR…')
        self.btn_run.configure(state='disabled')
        self._worker = threading.Thread(target=self._work, args=(video, out, opts), daemon=True)
        self._worker.start()
        # only the main thread may touch Tk: pump the queue with after()
        self.after(80, self._pump)

    def _work(self, video, out, opts):
        '''Chạy ở thread nền — KHÔNG được gọi widget hay self.after ở đây.'''
        try:
            res = run_ocr(video, out, opts=opts, cancel_event=self._cancel,
                          progress=lambda f, label: self._q.put(('tick', f, label)))
        except BaseException as exc:                        # noqa: BLE001
            res = None
            self._q.put(('crash', f'{type(exc).__name__}: {exc}'))
            return
        self._q.put(('done', res))

    def _pump(self):
        try:
            while True:
                item = self._q.get_nowait()
                if item[0] == 'tick':
                    self._progress(item[1], item[2])
                elif item[0] == 'crash':
                    self._finish_crash(item[1])
                elif item[0] == 'done':
                    self._finish(item[1])
        except queue.Empty:
            pass
        if self._worker and self._worker.is_alive():
            self.after(80, self._pump)

    def stop(self):
        if self._worker and self._worker.is_alive():
            self._cancel.set()
            self._say('đang dừng…')

    def reveal(self):
        import os
        folder = (Path(self.var_out.get() or '').parent if self.var_out.get()
                  else Path(self.var_video.get() or '.').parent)
        if folder.exists():
            os.startfile(str(folder))

    # ------------------------------------------------------------ feedback
    def _progress(self, frac, label):
        self.bar.set(max(0.0, min(1.0, frac)))
        self._say(f'{frac * 100:5.1f}%  {label}')

    def _finish_crash(self, message):
        self.btn_run.configure(state='normal')
        self.bar.set(0)
        self._say(f'LỖI: {message}', err=True)

    def _finish(self, res):
        self.btn_run.configure(state='normal')
        if res is None or not res.ok:
            self.bar.set(0)
            self._say(f'LỖI: {res.error}', err=True)
            self._append('\n'.join(res.log_tail[-8:]))
            return
        self.bar.set(1)
        self.var_out.set(str(res.srt_path))
        self._say(f'xong: {res.n_cues} cue, {res.duration_s:.1f}s nội dung → {res.srt_path.name}')
        self._append('\n'.join(f'[{c.start_s:7.2f} → {c.end_s:7.2f}]  {c.text}' for c in res.cues))

    def _append(self, text):
        if not text:
            return
        self.text.configure(state='normal')
        self.text.insert('end', text + '\n')
        self.text.configure(state='disabled')

    def _say(self, text, err=False):
        try:
            if err:
                self.status.configure(text=text, text_color=('#DC2626', '#E95364'))
            else:
                self.status.configure(text=text)
        except Exception:
            pass


if __name__ == '__main__':
    OcrWindow().mainloop()

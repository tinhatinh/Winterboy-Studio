# Source Generated with Decompyle++
# File: render_pipeline.pyc (Python 3.12)

'''
RenderPipeline FULL — STT → Dịch → TTS → Sync → CapCut inject (+ mute/flip/BGM/logo).

Gọi từ nút RENDER VIDEO (background thread).
'''
from __future__ import annotations
import hashlib
import logging
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
logger = logging.getLogger(__name__)
ProgressCb = Callable[(..., None)]

class PipelineCancelled(Exception):
    '''Người dùng bấm Dừng render.'''
    pass

@dataclass
class JobResult:
    ok: bool
    video_path: str
    message: str = ''
    project_dir: str | None = None
    project_name: str | None = None
    final_voice: str | None = None
    srt_path: str | None = None
    n_subtitles: int = 0
    n_voice: int = 0
    output_path: str | None = None
    manifest_path: str | None = None
    quality_report_path: str | None = None


@dataclass
class PipelineResult:
    ok: bool
    jobs: list[JobResult] = field(default_factory = list)
    message: str = ''
    shared_srt: str | None = None


def _resolve_srt(state_dict: 'dict[str, Any]', work_dir: Path) -> 'Path | None':
    srt_path = state_dict.get('srt_path') or (state_dict.get('module2') or { }).get('srt_path')
    if srt_path and Path(srt_path).is_file():
        return Path(srt_path)
    buf = state_dict.get('srt_text_buffer') or ''
    if isinstance(buf, str) and buf.strip():
        p = work_dir / 'srt' / 'from_buffer.srt'
        p.parent.mkdir(parents = True, exist_ok = True)
        p.write_text(buf.strip() + '\n', encoding = 'utf-8')
        return p
    return None


def _draft_options_from_state(sd: 'dict[str, Any]') -> 'dict[str, Any]':
    # TODO(khôi phục hành vi): hàm gom option từ 6 module, ~29 biến local và có closure
    # (m3) — bản decompile mất sạch thân, chỉ còn marker. Cần dựng lại từ dis.
    raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline._draft_options_from_state')


class RenderPipeline:
    
    def __init__(self = None, work_dir = None, *, capcut_template, inject_mode, voice_volume):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents = True, exist_ok = True)
        self.capcut_template = capcut_template
        self.inject_mode = inject_mode
        self.voice_volume = voice_volume
        self._cancel = threading.Event()
        self._current_renderer = None

    
    def request_cancel(self):
        '''Dừng pipeline: flag + kill FFmpeg đang bake.'''
        self._cancel.set()
        renderer = self._current_renderer
        if renderer is not None:
            
            try:
                renderer.request_cancel()
            except Exception:
                return None

        return None

    
    def is_cancelled(self):
        return self._cancel.is_set()

    
    def _raise_if_cancelled(self):
        if self._cancel.is_set():
            raise PipelineCancelled('Đã dừng render theo yêu cầu')

    
    def render_srt_to_mp3(self, state_dict: 'dict[str, Any]', *, srt_text_buffer: str = '', output_dir, progress: 'ProgressCb | None' = None) -> 'PipelineResult':
        '''Create one timeline-aligned MP3 from the active SRT and TTS settings.'''
        # TODO(khôi phục hành vi): bản decompile chỉ còn `pass` + marker.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline.render_srt_to_mp3')

    
    def run(self, state_dict: 'dict[str, Any]', *, srt_text_buffer: str = '', progress: 'ProgressCb | None' = None, target: str = 'mp4') -> 'PipelineResult':
        # TODO(khôi phục hành vi): thân hàm mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline.run')

    
    def _run_body(self, state_dict: 'dict[str, Any]', *, srt_text_buffer: str, progress: 'ProgressCb', target: str, jobs: 'list[JobResult]') -> 'PipelineResult':
        # TODO(khôi phục hành vi): thân hàm mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline._run_body')

    
    def _translate(self, srt, *, source_lang = 'Tự nhận diện', target_lang = 'Tiếng Việt', engine = 'Gemini', model = None, reflow = False, natural_voice = False):
        from app.services.gemini_translate import translate_srt_file
        safe_target = re_safe(target_lang)
        out = self.work_dir / 'translated' / f'''{srt.stem}.{safe_target}.srt'''
        r = translate_srt_file(srt, out, source_lang = source_lang, target_lang = target_lang, engine = engine, model = model, reflow = reflow, natural_voice = natural_voice, cancel_check = self._cancel.is_set)
        if not r.ok or not r.srt_path:
            raise RuntimeError(r.message)
        return Path(r.srt_path)

    
    def _build_voice(self, srt, *, voice_id, tts_speed, provider = 'Edge TTS', model_id = None, stability = 0.5, similarity_boost = 0.75, style = 0.0, use_speaker_boost = True, capcut_strict = False, capcut_fast_mode = False, capcut_fix_shark_enabled = False, capcut_fix_shark_path = '', capcut_fix_shark_device_path = '', progress = None, natural_voice_sync = False, soft_timing_enabled = False, source_video = None, resume_target = 'mp4', resume_job_key = '') -> 'tuple[Path, list, int]':
        # TODO(khôi phục hành vi): thân hàm mất trong bản decompile.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline._build_voice')

    
    def _inject_one(self, *, video_path, srt, final_voice, sync_reports, index, draft_options = None) -> 'JobResult':
        # TODO(khôi phục hành vi): bản decompile dừng ở dòng đặt `project_name`.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline._inject_one')

    
    def _build_capcut_one(self, *, video_path, srt, final_voice, index, draft_options, progress = None) -> 'JobResult':
        '''Tạo project CapCut bằng capcut-cli (thay CapCutDraftBuilder nội bộ).

        Runner được gắn vào ``_current_renderer`` để nút Dừng dùng chung với
        render MP4 — cùng một đường huỷ, không cần cơ chế riêng.
        '''
        from app.services.capcut_cli import CapCutCliError, CapCutCliRunner
        self._raise_if_cancelled()
        sub_only = bool(draft_options.get('capcut_sub_only', True))
        stamp = time.strftime('%Y%m%d_%H%M%S')
        if sub_only and srt and srt.is_file():
            stem = re_safe(srt.stem)[:36]
        else:
            stem = re_safe(video_path.stem)[:36]
        project_name = f'''Mumu_{stamp}_{index + 1:02d}_{stem}'''
        
        try:
            bgm_volume = float(draft_options.get('bgm_volume') or 15.0) / 100.0
        except (TypeError, ValueError):
            bgm_volume = 0.15
        
        try:
            voice_volume = max(0.0, min(1.0, float(draft_options.get('tts_volume') or 1.0)))
        except (TypeError, ValueError):
            voice_volume = 1.0

        runner = CapCutCliRunner(cancel_event = self._cancel)
        self._current_renderer = runner
        
        try:
            result = runner.build_project(name = project_name, video = video_path if not sub_only else None, srt = srt, voice = final_voice if not sub_only else None, voice_volume = voice_volume, bgm_paths = list(draft_options.get('bgm_paths') or []) if not sub_only else [], bgm_clips = list(draft_options.get('bgm_clips') or []) if not sub_only else [], bgm_volume = bgm_volume, subtitle_only = sub_only, progress = progress)
        except CapCutCliError as exc:
            
            try:
                return JobResult(ok = False, video_path = str(video_path), message = str(exc))
            finally:
                self._current_renderer = None

        finally:
            self._current_renderer = None

        return JobResult(ok = result.ok, video_path = str(video_path), message = result.message, project_dir = str(result.project_dir) if result.project_dir else None, project_name = result.project_name, final_voice = str(final_voice) if final_voice else None, srt_path = str(srt) if srt else None, n_subtitles = result.n_captions, n_voice = result.n_audio)

    
    def _render_one(self, *, video_path, srt, final_voice, index, draft_options, output_dir, progress, output_label = None) -> 'JobResult':
        '''Render MP4 độc lập; output name duy nhất cho từng item queue.'''
        # TODO(khôi phục hành vi): bản decompile chỉ còn docstring + `pass`.
        raise NotImplementedError('chưa khôi phục từ bytecode: render_pipeline.RenderPipeline._render_one')



def re_safe(name: str) -> str:
    '''
    Tên an toàn cho folder CapCut / file Resources.

    CapCut path placeholder dùng ``##`` — ký tự ``#`` trong tên file
    dễ vỡ path → Media lost / không load video.
    '''
    import re
    import unicodedata
    name = unicodedata.normalize('NFKC', name or '')
    name = re.sub('[#<>:\\"/\\\\|?*\\s\\r\\n\\t]+', '_', name)
    name = re.sub('[^\\w.\\-]+', '_', name, flags = re.UNICODE)
    name = re.sub('_+', '_', name).strip('._')
    if len(name) > 36:
        name = name[:36].rstrip('._')
    name = name.replace('#', '_')
    return name or 'video'

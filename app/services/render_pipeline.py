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

JobResult = <NODE:12>()
PipelineResult = <NODE:12>()

def _resolve_srt(state_dict = None, work_dir = dataclass):
    if not state_dict.get('srt_path'):
        state_dict.get('srt_path')
        if not state_dict.get('module2'):
            state_dict.get('module2')
    srt_path = { }.get('srt_path')
    if srt_path and Path(srt_path).is_file():
        return Path(srt_path)
    if not None.get('srt_text_buffer'):
        None.get('srt_text_buffer')
    buf = ''
    if isinstance(buf, str) and buf.strip():
        p = work_dir / 'srt' / 'from_buffer.srt'
        p.parent.mkdir(parents = True, exist_ok = True)
        p.write_text(buf.strip() + '\n', encoding = 'utf-8')
        return p


def _draft_options_from_state(sd = None):
    pass
# WARNING: Decompyle incomplete


class RenderPipeline:
    
    def __init__(self = None, work_dir = None, *, capcut_template, inject_mode, voice_volume):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents = True, exist_ok = True)
        self.capcut_template = capcut_template
        self.inject_mode = inject_mode
        self.voice_volume = voice_volume
        self._cancel = threading.Event()
        self._current_renderer = None

    
    def request_cancel(self = None):
        '''Dừng pipeline: flag + kill FFmpeg đang bake.'''
        self._cancel.set()
        renderer = self._current_renderer
    # WARNING: Decompyle incomplete

    
    def is_cancelled(self = None):
        return self._cancel.is_set()

    
    def _raise_if_cancelled(self = None):
        if self._cancel.is_set():
            raise PipelineCancelled('Đã dừng render theo yêu cầu')

    
    def render_srt_to_mp3(self = None, state_dict = None, *, srt_text_buffer, output_dir, progress):
        '''Create one timeline-aligned MP3 from the active SRT and TTS settings.'''
        pass
    # WARNING: Decompyle incomplete

    
    def run(self = None, state_dict = None, *, srt_text_buffer, progress, target):
        pass
    # WARNING: Decompyle incomplete

    
    def _run_body(self = None, state_dict = None, *, srt_text_buffer, progress, target, jobs):
        pass
    # WARNING: Decompyle incomplete

    
    def _translate(self = None, srt = None, *, source_lang, target_lang, engine, model, reflow, natural_voice):
        translate_srt_file = translate_srt_file
        import app.services.gemini_translate
        safe_target = re_safe(target_lang)
        out = self.work_dir / 'translated' / f'''{srt.stem}.{safe_target}.srt'''
        r = translate_srt_file(srt, out, source_lang = source_lang, target_lang = target_lang, engine = engine, model = model, reflow = reflow, natural_voice = natural_voice, cancel_check = self._cancel.is_set)
        if not r.ok or r.srt_path:
            raise RuntimeError(r.message)
        return Path(r.srt_path)

    
    def _build_voice(self = None, srt = None, *, voice_id, tts_speed, provider, model_id, stability, similarity_boost, style, use_speaker_boost, capcut_strict, capcut_fast_mode, capcut_fix_shark_enabled, capcut_fix_shark_path, capcut_fix_shark_device_path, progress, natural_voice_sync, soft_timing_enabled, source_video, resume_target, resume_job_key):
        pass
    # WARNING: Decompyle incomplete

    
    def _inject_one(self = None, *, video_path, srt, final_voice, sync_reports, index, draft_options):
        BuildResult = BuildResult
        CapCutDraftBuilder = CapCutDraftBuilder
        VoiceCue = VoiceCue
        load_srt_cues = load_srt_cues
        import app.services.capcut_draft_builder
        stamp = time.strftime('%Y%m%d_%H%M%S')
        path_hash = hashlib.sha1(str(video_path.resolve()).encode('utf-8')).hexdigest()[:10]
        project_name = f'''Mumu_{stamp}_{index + 1:02d}_{path_hash}'''
    # WARNING: Decompyle incomplete

    
    def _build_capcut_one(self = None, *, video_path, srt, final_voice, index, draft_options, progress):
        '''Tạo project CapCut bằng capcut-cli (thay CapCutDraftBuilder nội bộ).

        Runner được gắn vào ``_current_renderer`` để nút Dừng dùng chung với
        render MP4 — cùng một đường huỷ, không cần cơ chế riêng.
        '''
        CapCutCliError = CapCutCliError
        CapCutCliRunner = CapCutCliRunner
        import app.services.capcut_cli
        self._raise_if_cancelled()
        sub_only = bool(draft_options.get('capcut_sub_only', True))
        stamp = time.strftime('%Y%m%d_%H%M%S')
        if sub_only and srt and srt.is_file():
            stem = re_safe(srt.stem)[:36]
        else:
            stem = re_safe(video_path.stem)[:36]
        project_name = f'''Mumu_{stamp}_{index + 1:02d}_{stem}'''
        
        try:
            if not draft_options.get('bgm_volume'):
                draft_options.get('bgm_volume')
            bgm_volume = float(15) / 100
            
            try:
                if not draft_options.get('tts_volume'):
                    draft_options.get('tts_volume')
                voice_volume = max(0, min(1, float(1)))
                runner = CapCutCliRunner(cancel_event = self._cancel)
                self._current_renderer = runner
                
                try:
                    result = runner.build_project(name = project_name, video = video_path if not sub_only else None, srt = srt, voice = final_voice if not sub_only else None, voice_volume = voice_volume, bgm_paths = list([]) if not sub_only else [], bgm_clips = list([]) if not sub_only else [], bgm_volume = bgm_volume, subtitle_only = sub_only, progress = progress)
                    self._current_renderer = None
                    return JobResult(ok = result.ok, video_path = str(video_path), message = result.message, project_dir = str(result.project_dir) if result.project_dir else None, project_name = result.project_name, final_voice = str(final_voice) if final_voice else None, srt_path = str(srt) if srt else None, n_subtitles = result.n_captions, n_voice = result.n_audio)
                    except (TypeError, ValueError):
                        bgm_volume = 0.15
                        continue
                    except (TypeError, ValueError):
                        voice_volume = 1
                        continue
                except CapCutCliError:
                    exc = None
                    
                    try:
                        del exc
                        None = None
                        return 
                        exc = None
                        del exc
                        
                        try:
                            pass
                        except:
                            self._current_renderer = None






    
    def _render_one(self = None, *, video_path, srt, final_voice, index, draft_options, output_dir, progress, output_label):
        '''Render MP4 độc lập; output name duy nhất cho từng item queue.'''
        pass
    # WARNING: Decompyle incomplete



def re_safe(name = None):
    '''
    Tên an toàn cho folder CapCut / file Resources.

    CapCut path placeholder dùng ``##`` — ký tự ``#`` trong tên file
    dễ vỡ path → Media lost / không load video.
    '''
    import re
    import unicodedata
    if not name:
        name
    name = unicodedata.normalize('NFKC', '')
    name = re.sub('[#<>:\\"/\\\\|?*\\s\\r\\n\\t]+', '_', name)
    name = re.sub('[^\\w.\\-]+', '_', name, flags = re.UNICODE)
    name = re.sub('_+', '_', name).strip('._')
    if len(name) > 36:
        name = name[:36].rstrip('._')
    name = name.replace('#', '_')
    if not name:
        name
    return 'video'


# Source Generated with Decompyle++
# File: capcut_draft_builder.pyc (Python 3.12)

'''
CapCutDraftBuilder — Khâu 3: clone template draft + inject phụ đề / giọng đọc.

CapCut Auto Captions / Text Reading KHÔNG lưu "lệnh Generate" trong JSON.
JSON chỉ chứa KẾT QUẢ:

  Subtitle  → materials.texts[]  +  tracks[type=text].segments[]
  Voice AI  → materials.audios[] (type text_to_audio) + tracks[type=audio].segments[]
              + file WAV/MP3 trong textReading/ (hoặc Resources/)

Chiến lược tool:
  1. Python tự STT/dịch/TTS + AudioSyncEngine (chống đè)
  2. Clone project mẫu (font/style/layout đã đẹp)
  3. Bơm SRT + file voice vào draft_content.json
  4. Mở CapCut → Export Pro (không bấm Generate / Start reading)

Đơn vị thời gian CapCut = microsecond (1s = 1_000_000).
'''
from __future__ import annotations
import json
import logging
import re
import shutil
import subprocess
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence
logger = logging.getLogger(__name__)
DEFAULT_PATH_PLACEHOLDER = '##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##'
DEFAULT_DRAFTS_ROOT = Path.home() / 'AppData' / 'Local' / 'CapCut' / 'User Data' / 'Projects' / 'com.lveditor.draft'
AUTO_BASE_TEMPLATE = 'Mumu_BASE'
DEFAULT_TEMPLATE_NAME = AUTO_BASE_TEMPLATE
TEMPLATE_FALLBACKS = (AUTO_BASE_TEMPLATE, 'Mumu_PoC_001', 'BASE_TEMPLATE', '0629', '0531', '0519', 'main')
CAPCUT_BLUR_EFFECT_ID = '7399464929830423813'
CAPCUT_BLUR_MASK_RESOURCE_ID = '7374021450748924432'
CAPCUT_CACHE_EFFECT = Path.home() / 'AppData' / 'Local' / 'CapCut' / 'User Data' / 'Cache' / 'effect'
CAPCUT_TTS_TONE_SPEAKER = 'BV074_streaming'
CAPCUT_TTS_TONE_TYPE = 'Cute Female'
CAPCUT_TTS_TONE_PLATFORM = 'sami'
CAPCUT_TTS_RESOURCE_ID = '7102355709945188865'
CAPCUT_TTS_PATH_PLACEHOLDER = DEFAULT_PATH_PLACEHOLDER
VOICE_CAPCUT_VOLUME_GAIN = 2
VOICE_FILE_GAIN_DB = 8
VOICE_VOLUME_DEFAULT = 2
US = 1000000
SubCue = <NODE:12>()
VoiceCue = <NODE:12>()
BuildResult = <NODE:12>()

def new_uuid():
    return str(uuid.uuid4()).upper()


def sec_to_us(sec = None):
    return int(round(float(sec) * US))


def us_to_sec(us = None):
    return float(us) / US


def load_srt_cues(srt_path = None):
    '''Parse SRT → SubCue. Ưu tiên pysrt; fallback regex.'''
    srt_path = Path(srt_path)
    if not srt_path.is_file():
        raise FileNotFoundError(f'''Không thấy SRT: {srt_path}''')
    
    try:
        import pysrt
        subs = pysrt.open(str(srt_path), encoding = 'utf-8')
        cues = []
        for i, item in enumerate(subs):
            start_s = item.start.hours * 3600 + item.start.minutes * 60 + item.start.seconds + item.start.milliseconds / 1000
            end_s = item.end.hours * 3600 + item.end.minutes * 60 + item.end.seconds + item.end.milliseconds / 1000
            if not item.text:
                item.text
            text = ''.replace('\n', ' ').strip()
            if not text:
                continue
            if end_s <= start_s:
                end_s = start_s + 0.3
            cues.append(SubCue(index = i, start_s = start_s, end_s = end_s, text = text))
        return cues
    except ImportError:
        pass

    raw = srt_path.read_text(encoding = 'utf-8', errors = 'replace')
    blocks = re.split('\\n\\s*\\n', raw.strip())
    cues = []
    idx = 0
    time_re = re.compile('(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})\\s*-->\\s*(\\d{2}):(\\d{2}):(\\d{2})[,.](\\d{3})')
# WARNING: Decompyle incomplete


def _ensure_list(d = None, key = None):
    v = d.get(key)
    if not isinstance(v, list):
        d[key] = []
    return d[key]


def _set_text_content_payload(material = None, text = None):
    '''Ghi nội dung chữ vào materials.texts[].content (JSON string lồng).'''
    if not text:
        text
    text = ''
    if not material.get('content'):
        material.get('content')
    raw = ''
# WARNING: Decompyle incomplete


def _placeholder_rel(rel_path = None, placeholder = None):
    rel = rel_path.replace('\\', '/').lstrip('/')
    return f'''{placeholder}/{rel}'''


def _capcut_path(path = None):
    '''draft_fold_path: slash xuôi (kiểu CapCut native).'''
    return str(path).replace('\\', '/')


def _capcut_root_path(path = None):
    '''draft_root_path: backslash Windows như project native (0713).'''
    return str(Path(path))


def _capcut_json_file(project_dir = None, filename = None):
    '''
    root_meta dùng mixed separator kiểu CapCut:
      C:/.../ProjectName\\draft_content.json
    '''
    return f'''{_capcut_path(project_dir)}\\{filename}'''


def _ensure_draft_cover(project_dir = None, video_path = None):
    '''Tạo draft_cover.jpg — CapCut hay từ chối project thiếu cover.'''
    project_dir = Path(project_dir)
    cover = project_dir / 'draft_cover.jpg'
    if cover.is_file() and cover.stat().st_size > 500:
        return cover
# WARNING: Decompyle incomplete


def _pick_seed_project(drafts_root = None):
    '''Chọn project CapCut làm seed (ưu tiên không-Mumu; fallback Mumu_* nếu cần).'''
    candidates = []
    if not drafts_root.is_dir():
        return None
    for entry in drafts_root.iterdir():
        if entry.is_dir() or entry.name.startswith('.'):
            continue
        if entry.name == AUTO_BASE_TEMPLATE:
            continue
        content = entry / 'draft_content.json'
        if not content.is_file():
            continue
        size = content.stat().st_size
        data = json.loads(content.read_text(encoding = 'utf-8'))
        if not data.get('materials'):
            data.get('materials')
        if not { }.get('videos'):
            { }.get('videos')
        videos = []
        if not data.get('materials'):
            data.get('materials')
        if not { }.get('texts'):
            { }.get('texts')
        texts = []
        n_photo = 0
        n_real = 0
        for v in videos:
            if not isinstance(v, dict):
                continue
            if not v.get('type'):
                v.get('type')
            vt = str('').lower()
            if not v.get('path'):
                v.get('path')
            path = str('').lower()
            if not v.get('name'):
                v.get('name')
                if not v.get('material_name'):
                    v.get('material_name')
            nm = str('').lower()
            if vt in ('photo', 'image') and 'chatgpt' in path or 'chatgpt' in nm:
                n_photo += 1
                continue
            if not vt == 'video' and path.endswith(('.mp4', '.mov', '.mkv', '.webm')):
                continue
            n_real += 1
        mumu_penalty = 5000 if entry.name.startswith('Mumu_') else 0
        score = 0 if n_real else 50000 + n_photo * 800 + len(texts) * 3 + size // 50000 + 500 if entry.name.lower() == 'main' else 0 + mumu_penalty
        candidates.append((score, entry))
    if not candidates:
        return None
    candidates.sort(key = (lambda x: x[0]))
    return candidates[0][1]
    except Exception:
        continue


def ensure_auto_base_template(drafts_root = None, *, force_rebuild):
    '''
    Tự tạo / bảo trì folder template sạch ``Mumu_BASE``.

    User không cần mở CapCut đặt tên BASE_TEMPLATE nữa.
    - Clone seed project bất kỳ (nhỏ/sạch nhất)
    - Sanitize: 1 video track, 0 text/audio/photo ChatGPT
    - Ghi meta để CapCut nhận folder
    '''
    root = Path(drafts_root) if drafts_root else DEFAULT_DRAFTS_ROOT
    root.mkdir(parents = True, exist_ok = True)
    dest = root / AUTO_BASE_TEMPLATE
    draft_json = dest / 'draft_content.json'
# WARNING: Decompyle incomplete


def _ensure_placeholder_mp4(project_dir = None):
    '''Tạo video đen 1s trong Resources — template không bao giờ Media lost.'''
    res = project_dir / 'Resources'
    res.mkdir(parents = True, exist_ok = True)
    out = res / 'mumu_placeholder.mp4'
    if out.is_file() and out.stat().st_size > 1000:
        return out
    ffmpeg = None.which('ffmpeg')
    if ffmpeg:
        
        try:
            subprocess.run([
                ffmpeg,
                '-y',
                '-f',
                'lavfi',
                '-i',
                'color=c=black:s=1080x1920:d=1',
                '-c:v',
                'libx264',
                '-t',
                '1',
                '-pix_fmt',
                'yuv420p',
                '-an',
                str(out)], capture_output = True, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout = 60)
            if out.is_file() or out.stat().st_size < 500:
                for f in res.glob('*.mp4'):
                    if not f.name != out.name:
                        continue
                    if not f.stat().st_size > 1000:
                        continue
                    shutil.copy2(f, out)
                    res.glob('*.mp4')
                    return out
            return out
        except Exception:
            e = None
            logger.warning('ffmpeg placeholder: %s', e)
            e = None
            del e
            continue
            e = None
            del e
            except OSError:
                continue



def _sanitize_template_dir(project_dir = None):
    '''Sanitize folder template — 1 video placeholder thật, không path chết.'''
    project_dir = Path(project_dir)
    path = project_dir / 'draft_content.json'
    data = json.loads(path.read_text(encoding = 'utf-8'))
    mats = data.setdefault('materials', { })
    mats['texts'] = []
    mats['audios'] = []
    for k in ('stickers', 'images'):
        if not k in mats:
            continue
        mats[k] = []
    ph = _ensure_placeholder_mp4(project_dir)
    ph_rel = _placeholder_rel(f'''Resources/{ph.name}''', DEFAULT_PATH_PLACEHOLDER)
    ph_dur = US
# WARNING: Decompyle incomplete


def _rewrite_template_meta(project_dir = None, name = None, drafts_root = None):
    meta_path = project_dir / 'draft_meta_info.json'
    now_us = int(time.time() * 1000000)
    draft_id = new_uuid()
    
    try:
        data = json.loads((project_dir / 'draft_content.json').read_text(encoding = 'utf-8'))
        if not data.get('duration'):
            data.get('duration')
        duration = int(0)
        data['id'] = draft_id
        (project_dir / 'draft_content.json').write_text(json.dumps(data, ensure_ascii = False, separators = (',', ':')), encoding = 'utf-8')
        _ensure_draft_cover(project_dir)
        meta = {
            'draft_id': draft_id,
            'draft_name': name,
            'draft_fold_path': _capcut_path(project_dir),
            'draft_root_path': _capcut_root_path(drafts_root),
            'draft_json_file': _capcut_json_file(project_dir, 'draft_content.json'),
            'draft_cover': 'draft_cover.jpg',
            'tm_draft_create': now_us,
            'tm_draft_modified': now_us,
            'tm_duration': duration,
            'tm_draft_removed': 0,
            'draft_is_invisible': False,
            'cloud_draft_sync': False }
        if meta_path.is_file():
            
            try:
                old = json.loads(meta_path.read_text(encoding = 'utf-8'))
                if isinstance(old, dict):
                    old.update(meta)
                    meta = old
                meta['draft_id'] = draft_id
                meta['draft_name'] = name
                meta['draft_fold_path'] = _capcut_path(project_dir)
                meta['draft_root_path'] = _capcut_root_path(drafts_root)
                meta['draft_json_file'] = _capcut_json_file(project_dir, 'draft_content.json')
                meta['draft_cover'] = 'draft_cover.jpg'
                meta_path.write_text(json.dumps(meta, ensure_ascii = False, indent = 2), encoding = 'utf-8')
                return None
                except Exception:
                    duration = 0
                    continue
            except Exception:
                continue




def resolve_template_name(drafts_root = None, preferred = None):
    '''
    Tìm / tự tạo template.
    Ưu tiên: auto Mumu_BASE → preferred → fallbacks → seed bất kỳ.
    '''
    root = Path(drafts_root)
# WARNING: Decompyle incomplete


def _blur_effect_path():
    base = CAPCUT_CACHE_EFFECT / CAPCUT_BLUR_EFFECT_ID
    if base.is_dir():
        for child in base.iterdir():
            if not child.is_dir():
                continue
            if child.name.endswith('_tmp'):
                continue
            
            return base.iterdir(), _capcut_path(child)
    return _capcut_path(base / '2db7bf49d9349e308ef0f46c39b14abf')


def _blur_mask_path():
    base = CAPCUT_CACHE_EFFECT / '1036120042'
    if base.is_dir():
        for child in base.iterdir():
            if not child.is_dir():
                continue
            if child.name.endswith('_tmp'):
                continue
            
            return base.iterdir(), _capcut_path(child)
    return _capcut_path(base / '6e7fa46ea829d76af5c4b45b3af75696')


def _probe_duration_s(path = None):
    '''Đo duration file audio bằng ffprobe; fallback 1.0s.'''
    
    try:
        import shutil
        import subprocess
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            return 1
            
            try:
                p = subprocess.run([
                    ffprobe,
                    '-v',
                    'error',
                    '-show_entries',
                    'format=duration',
                    '-of',
                    'default=noprint_wrappers=1:nokey=1',
                    str(path)], capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if p.returncode == 0 and p.stdout.strip():
                    return max(0.05, float(p.stdout.strip()))
            except Exception:
                e = None
                logger.warning('ffprobe fail %s: %s', path, e)
                e = None
                del e
                return 1
                e = None
                del e




def normalize_voice_volume(volume = None):
    '''
    Chuẩn hoá volume inject vào CapCut.

    UI 100% → 1.0 → * VOICE_CAPCUT_VOLUME_GAIN (2.0) = CapCut volume 2.0
    UI 140% → 1.4 → CapCut 2.8
    Edge-TTS luôn nhỏ hơn giọng CapCut native → luôn boost khi v ≤ 2.
    Clamp 0.05 .. 4.0
    '''
    pass
# WARNING: Decompyle incomplete


def _copy_audio_boosted(src = None, dest = None, *, gain_db):
    '''
    Copy audio sang textReading, tăng volume +gain_db (Edge-TTS khá nhỏ).
    Fallback shutil.copy2 nếu không có ffmpeg.
    '''
    import shutil
    import subprocess
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents = True, exist_ok = True)
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg or gain_db == 0:
        shutil.copy2(src, dest)
        return None
    
    try:
        ext = dest.suffix.lower()
        cmd = [
            ffmpeg,
            '-y',
            '-i',
            str(src),
            '-af',
            f'''volume={gain_db}dB''']
        if ext in frozenset({'.mp3'}):
            cmd += [
                '-codec:a',
                'libmp3lame',
                '-q:a',
                '2']
        elif ext in frozenset({'.wave', '.wav'}):
            cmd += [
                '-codec:a',
                'pcm_s16le']
        else:
            cmd += [
                '-codec:a',
                'libmp3lame',
                '-q:a',
                '2']
            dest = dest.with_suffix('.mp3')
        cmd.append(str(dest))
        p = subprocess.run(cmd, capture_output = True, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout = 120)
        if p.returncode != 0 and dest.is_file() or dest.stat().st_size < 100:
            logger.warning('ffmpeg gain fail → copy gốc')
            shutil.copy2(src, dest)
            return None
            
            try:
                logger.info('Boosted voice +%.1fdB → %s', gain_db, dest.name)
                return None
            except Exception:
                e = None
                logger.warning('boost audio fail %s — copy gốc', e)
                shutil.copy2(src, dest)
                e = None
                del e
                return None
                e = None
                del e




class CapCutDraftBuilder:
    '''
    Clone template CapCut + inject SRT + inject voice.

    Ví dụ nhanh:
        b = CapCutDraftBuilder()
        r = b.build_from_srt(
            srt_path="demo.srt",
            project_name="Mumu_Inject_Demo",
            voice_files=[("tts0.wav", 0.0, 1.2), ...],  # optional
        )
        print(r.project_dir)
    '''
    
    def __init__(self = None, drafts_root = None, template_name = None, *, path_placeholder, auto_resolve_template):
        self.drafts_root = Path(drafts_root) if drafts_root else DEFAULT_DRAFTS_ROOT
        self.path_placeholder = path_placeholder
        if not template_name:
            template_name
        preferred = DEFAULT_TEMPLATE_NAME
        if auto_resolve_template:
            
            try:
                resolved = resolve_template_name(self.drafts_root, preferred)
                if resolved != preferred:
                    logger.info("Template resolve: preferred=%s → dùng '%s' (auto sạch)", preferred, resolved)
                self.template_name = resolved
            if not (self.drafts_root / preferred / 'draft_content.json').is_file():
                preferred = ensure_auto_base_template(self.drafts_root)

        self.template_name = preferred
        self.template_dir = self.drafts_root / self.template_name
        if not self.template_dir.is_dir():
            raise FileNotFoundError(f'''Template CapCut không tồn tại: {self.template_dir}\nMở CapCut 1 lần rồi RENDER lại — tool tự tạo Mumu_BASE.''')
        if not (self.template_dir / 'draft_content.json').is_file():
            raise FileNotFoundError(f'''Thiếu draft_content.json trong {self.template_dir}''')
        return None
        except FileNotFoundError:
            raise 

    
    def clone_template(self = None, project_name = None, *, overwrite):
        '''
        Copy cả folder template → project mới dưới drafts_root.
        Cập nhật draft_meta_info (name, id, path, timestamps).
        '''
        project_name = self._safe_name(project_name)
        dest = self.drafts_root / project_name
        if dest.exists():
            if not overwrite:
                raise FileExistsError(f'''Project đã tồn tại: {dest} (dùng overwrite=True để ghi đè)''')
            shutil.rmtree(dest)
        
        def _ignore(dirpath = None, names = None):
            skip = {
                '.DS_Store',
                'Thumbs.db'}
        # WARNING: Decompyle incomplete

        shutil.copytree(self.template_dir, dest, ignore = _ignore)
        self._rewrite_meta(dest, project_name, force_new_id = True)
        self._sanitize_clone(dest)
        logger.info('Cloned template %s → %s', self.template_name, dest)
        return dest

    
    def _sanitize_clone(self = None, project_dir = None):
        '''
        Template clone mang theo sub/TTS/ảnh ChatGPT/logo → CapCut media lộn xộn.

        - Xóa texts/audios (inject lại)
        - materials.videos: CHỈ giữ 1 clip video thật đầu tiên (bỏ photo/ChatGPT/overlay)
        - Chỉ 1 track video chính có segment; track phụ video/audio/text clear
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _safe_name(self = None, name = None):
        if not name:
            name
        if not ''.strip():
            ''.strip()
        name = f'''Mumu_Auto_{int(time.time())}'''
        name = re.sub('[#<>:"/\\\\|?*\\s]+', '_', name)
        name = re.sub('_+', '_', name).strip('._')
        if not name[:72]:
            name[:72]
        return f'''Mumu_Auto_{int(time.time())}'''

    
    def _rewrite_meta(self = None, project_dir = None, project_name = None, *, force_new_id):
        """
        Ghi draft_meta + root_meta **cùng một draft_id**.

        CapCut 'unusual path' thường do:
          - draft_id lệch giữa folder meta và root_meta
          - thiếu draft_cover.jpg
          - draft_json_file trỏ nhầm (copy từ template)
        """
        meta_path = project_dir / 'draft_meta_info.json'
        if not meta_path.is_file():
            meta = { }
        else:
            
            try:
                meta = json.loads(meta_path.read_text(encoding = 'utf-8'))
                if not meta.get('draft_id'):
                    meta.get('draft_id')
                old_id = str('').strip()
                if force_new_id:
                    pass
                elif old_id and len(old_id) > 8:
                    pass
                
                new_id = new_uuid()
                fold = _capcut_path(project_dir)
                root = _capcut_root_path(self.drafts_root)
                now_us = int(time.time() * 1000000)
                if not meta.get('tm_duration'):
                    meta.get('tm_duration')
                duration = int(0)
                content_path = project_dir / 'draft_content.json'
                
                try:
                    data = json.loads(content_path.read_text(encoding = 'utf-8'))
                    if not data.get('duration'):
                        data.get('duration')
                        if not duration:
                            duration
                    duration = int(0)
                    data['id'] = new_id
                    content_path.write_text(json.dumps(data, ensure_ascii = False, separators = (',', ':')), encoding = 'utf-8')
                    _ensure_draft_cover(project_dir)
                    meta['draft_id'] = new_id
                    meta['draft_name'] = project_name
                    meta['draft_fold_path'] = fold
                    meta['draft_root_path'] = root
                    meta['draft_json_file'] = _capcut_json_file(project_dir, 'draft_content.json')
                    meta['draft_cover'] = 'draft_cover.jpg'
                    if not meta.get('tm_draft_create'):
                        meta.get('tm_draft_create')
                    meta['tm_draft_create'] = int(now_us)
                    meta['tm_draft_modified'] = now_us
                    meta['tm_duration'] = duration
                    meta['tm_draft_removed'] = 0
                    meta['draft_is_invisible'] = False
                    meta['draft_cloud_last_action_download'] = False
                    meta['cloud_draft_sync'] = False
                    meta['draft_is_from_deeplink'] = 'false'
                    meta_path.write_text(json.dumps(meta, ensure_ascii = False, indent = 2), encoding = 'utf-8')
                    self._register_in_root_meta(project_dir = project_dir, project_name = project_name, draft_id = new_id, duration = duration, modified_us = now_us)
                    return None
                    except json.JSONDecodeError:
                        new_uuid()
                        meta = { }
                        continue
                except Exception:
                    e = new_uuid()
                    logger.warning('Không rewrite draft id: %s', e)
                    e = None
                    del e
                    continue
                    e = None
                    del e



    
    def _register_in_root_meta(self = None, *, project_dir, project_name, draft_id, duration, modified_us):
        '''
        CapCut PC index project qua root_meta_info.json (all_draft_store).
        draft_id **phải** trùng draft_meta_info.json.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _touch_meta_duration(self = None, project_dir = None, duration_us = None):
        '''Đồng bộ tm_duration / modified + **draft_id** (meta ↔ root_meta).'''
        project_dir = Path(project_dir)
        meta_path = project_dir / 'draft_meta_info.json'
        now_us = int(time.time() * 1000000)
        draft_id = ''
        name = project_dir.name
        if not duration_us:
            duration_us
        duration = int(0)
        if duration <= 0:
            
            try:
                data = self.load_draft(project_dir)
                if not data.get('duration'):
                    data.get('duration')
                duration = int(0)
                _ensure_draft_cover(project_dir)
                if meta_path.is_file():
                    
                    try:
                        meta = json.loads(meta_path.read_text(encoding = 'utf-8'))
                        if not meta.get('draft_id'):
                            meta.get('draft_id')
                        draft_id = str('')
                        if not meta.get('draft_name'):
                            meta.get('draft_name')
                        name = str(name)
                        meta['tm_draft_modified'] = now_us
                        meta['tm_duration'] = duration
                        meta['draft_fold_path'] = _capcut_path(project_dir)
                        meta['draft_root_path'] = _capcut_root_path(self.drafts_root)
                        meta['draft_json_file'] = _capcut_json_file(project_dir, 'draft_content.json')
                        meta['draft_cover'] = 'draft_cover.jpg'
                        meta_path.write_text(json.dumps(meta, ensure_ascii = False, indent = 2), encoding = 'utf-8')
                        if not draft_id:
                            self._rewrite_meta(project_dir, name)
                            return None
                        self._register_in_root_meta(project_dir = project_dir, project_name = name, draft_id = draft_id, duration = duration, modified_us = now_us)
                        return None
                        except Exception:
                            duration = 0
                            continue
                    except Exception:
                        continue



    
    def repair_project_registration(self = None, project_dir = None, *, video_path):
        '''Sửa project Mumu hiện có: cover + id sync + path (mở được trong CapCut).'''
        if not project_dir:
            project_dir
        project_dir = Path(self.drafts_root / 'Mumu_Studio')
        if not project_dir.is_dir():
            logger.warning('repair: folder missing %s', project_dir)
            return False
        name = project_dir.name
        _ensure_draft_cover(project_dir, video_path = video_path)
        self._rewrite_meta(project_dir, name)
        
        try:
            data = self.load_draft(project_dir)
            if not data.get('duration'):
                data.get('duration')
            self._touch_meta_duration(project_dir, int(0))
            logger.info('Repaired CapCut registration → %s', project_dir)
            return True
        except Exception:
            continue


    
    def load_draft(self = None, project_dir = None):
        path = Path(project_dir) / 'draft_content.json'
        return json.loads(path.read_text(encoding = 'utf-8'))

    
    def save_draft(self = None, project_dir = None, data = None):
        path = Path(project_dir) / 'draft_content.json'
        path.write_text(json.dumps(data, ensure_ascii = False, separators = (',', ':')), encoding = 'utf-8')
        if not data.get('duration'):
            data.get('duration')
        self._touch_meta_duration(Path(project_dir), int(0))
        return path

    
    def _get_or_create_track(self = None, data = None, track_type = None):
        tracks = _ensure_list(data, 'tracks')
        for t in tracks:
            if not t.get('type') == track_type:
                continue
            
            return tracks, t
        tracks.append(track)
        return track

    
    def _get_text_template_material(self = None, data = None):
        if not data.get('materials'):
            data.get('materials')
        if not { }.get('texts'):
            { }.get('texts')
        texts = []
        if texts:
            return deepcopy(texts[0])
    # WARNING: Decompyle incomplete

    
    def _get_text_segment_template(self = None, data = None):
        if not data.get('tracks'):
            data.get('tracks')
        for t in []:
            if not t.get('type') == 'text':
                continue
            if not t.get('segments'):
                continue
            
            return [], deepcopy(t['segments'][0])
    # WARNING: Decompyle incomplete

    
    def _get_audio_material_template(self = None, data = None):
        if not data.get('materials'):
            data.get('materials')
        if not { }.get('audios'):
            { }.get('audios')
        audios = []
        for a in audios:
            if not a.get('type') == 'text_to_audio':
                continue
            
            return audios, deepcopy(a)
        if audios:
            return deepcopy(audios[0])
    # WARNING: Decompyle incomplete

    
    def _get_audio_segment_template(self = None, data = None):
        if not data.get('tracks'):
            data.get('tracks')
        for t in []:
            if not t.get('type') == 'audio':
                continue
            if not t.get('segments'):
                continue
            
            return [], deepcopy(t['segments'][0])
        None = self._get_text_segment_template(data)
        seg['uniform_scale'] = None
        seg['source_timerange'] = {
            'start': 0,
            'duration': US }
        seg['volume'] = 1
        return seg

    
    def _ensure_animation_ref(self = None, data = None, template_seg = None):
        '''Lấy / tạo material_animations rỗng cho text segment.'''
        mats = data.setdefault('materials', { })
        anims = _ensure_list(mats, 'material_animations')
        for a in anims:
            if not a.get('type') == 'sticker_animation':
                continue
            
            return anims, a['id']
        if not template_seg.get('extra_material_refs'):
            template_seg.get('extra_material_refs')
        for None in refs:
            for a in anims:
                if not a.get('id') == ref:
                    continue
                
                
                return [], anims, ref
        anims.append({
            'id': aid,
            'type': 'sticker_animation',
            'animations': [],
            'multi_language_current': 'none' })
        return aid

    
    def _make_audio_helper_refs(self = None, data = None):
        '''
        Bộ helper cho audio segment — clone từ «tìm voice» (CapCut TTS native):
          speeds + placeholder_infos + beats + sound_channel_mappings + vocal_separations
        '''
        mats = data.setdefault('materials', { })
        speed_id = new_uuid()
        ph_id = new_uuid()
        beats_id = new_uuid()
        ch_id = new_uuid()
        vs_id = new_uuid()
        _ensure_list(mats, 'speeds').append({
            'id': speed_id,
            'type': 'speed',
            'mode': 0,
            'speed': 1,
            'curve_speed': None })
        _ensure_list(mats, 'placeholder_infos').append({
            'id': ph_id,
            'type': 'placeholder_info',
            'meta_type': 'none',
            'res_path': '',
            'res_text': '',
            'error_path': '',
            'error_text': '' })
        _ensure_list(mats, 'beats').append({
            'id': beats_id,
            'type': 'beats',
            'enable_ai_beats': False,
            'gear': 404,
            'gear_count': 0,
            'mode': 404,
            'user_beats': [],
            'user_delete_ai_beats': None,
            'ai_beats': {
                'melody_url': '',
                'melody_path': '',
                'beats_url': '',
                'beats_path': '',
                'melody_percents': [
                    0],
                'beat_speed_infos': [] } })
        _ensure_list(mats, 'sound_channel_mappings').append({
            'id': ch_id,
            'type': 'none',
            'audio_channel_mapping': 0,
            'is_config_open': False })
        _ensure_list(mats, 'vocal_separations').append({
            'id': vs_id,
            'type': 'vocal_separation',
            'choice': 0,
            'removed_sounds': [],
            'time_range': None,
            'production_path': '',
            'final_algorithm': '',
            'enter_from': '' })
        return [
            speed_id,
            ph_id,
            beats_id,
            ch_id,
            vs_id]

    
    def inject_srt(self = None, project_dir = None, srt_path = None, *, cues, clear_existing, update_duration, style):
        '''
        Inject phụ đề vào draft.

        style (optional, từ UI preview):
          sub_font, sub_size, sub_bg_style, sub_bg_enable,
          sub_x, sub_y, sub_box_w, sub_box_h, canvas_w, canvas_h

        Returns: list text material ids (theo thứ tự cue).
        '''
        project_dir = Path(project_dir)
    # WARNING: Decompyle incomplete

    
    def inject_voice_cues(self = None, project_dir = None, voice_cues = None, *, clear_existing_tts, volume, new_track, track_name, file_gain_db):
        '''
        Inject nhiều file voice (mỗi câu 1 file) kiểu CapCut text_to_audio.

        Copy file → <project>/textReading/<name> (+ boost dB Edge-TTS)
        path trong JSON dùng draftpath_placeholder.
        volume: 1.0 = UI 100% → tự boost lên ~2.0 CapCut.
        '''
        project_dir = Path(project_dir)
        if not voice_cues:
            return []
        capcut_vol = None(volume)
        if not volume:
            volume
        logger.info('Voice inject volume: input=%.2f → CapCut=%.2f (+%.0fdB file)', float(0), capcut_vol, file_gain_db)
        data = self.load_draft(project_dir)
        mats = data.setdefault('materials', { })
        audios = _ensure_list(mats, 'audios')
    # WARNING: Decompyle incomplete

    
    def inject_voice_file(self = None, project_dir = None, audio_path = None, *, start_s, volume, track_name, clear_existing_tts, file_gain_db):
        '''
        Inject 1 file voice đã align timeline (final_voice.mp3 từ AudioSyncEngine).
        Đơn giản hơn per-cue; vẫn hiện trên timeline audio.
        volume 1.0 (UI 100%) → boost CapCut ~2.0 + file +8dB.
        '''
        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        dur = _probe_duration_s(audio_path)
        cues = [
            VoiceCue(index = 0, start_s = start_s, duration_s = dur, path = audio_path, text = audio_path.stem)]
        ids = self.inject_voice_cues(project_dir, cues, clear_existing_tts = clear_existing_tts, volume = volume, new_track = True, track_name = track_name, file_gain_db = file_gain_db)
        if ids:
            return ids[0]

    
    def set_main_video(self = None, project_dir = None, video_path = None, *, copy_into_resources, lock_duration):
        '''
        Gắn video user làm materials.videos chính (copy Resources/).

        - Ép type=video (không để photo template)
        - Probe width/height/duration
        - Gỡ material rác (ChatGPT png, photo lạ) — chỉ giữ main + mumu_* overlay
        - Track video chính trỏ đúng material_id
        '''
        project_dir = Path(project_dir)
        video_path = Path(video_path)
        if not video_path.is_file():
            raise FileNotFoundError(video_path)
        data = self.load_draft(project_dir)
        mats = data.setdefault('materials', { })
        videos = _ensure_list(mats, 'videos')
    # WARNING: Decompyle incomplete

    
    def _purge_junk_media(self = None, project_dir = None):
        '''Xóa materials photo/ChatGPT/path tuyệt đối chết — tránh CapCut Media lost + lag.'''
        project_dir = Path(project_dir)
        
        try:
            data = self.load_draft(project_dir)
            mats = data.setdefault('materials', { })
            if not mats.get('videos'):
                mats.get('videos')
            videos = []
            keep = []
            keep_ids = set()
            for v in videos:
                if not isinstance(v, dict):
                    continue
                if not v.get('name'):
                    v.get('name')
                    if not v.get('material_name'):
                        v.get('material_name')
                name = str('')
                if not v.get('path'):
                    v.get('path')
                path = str('')
                if not v.get('type'):
                    v.get('type')
                vtype = str('').lower()
                low_p = path.lower()
                low_n = name.lower()
                if 'chatgpt' in low_n or 'chatgpt' in low_p:
                    continue
                if not vtype in ('photo', 'image') and low_n.startswith('mumu_'):
                    continue
                if not path and path.startswith('##_'):
                    if ':/' in path and ':\\' in path or path.startswith('/'):
                        if not Path(path).is_file():
                            logger.info('drop missing media: %s', path[-80:])
                            continue
                keep.append(v)
                if not v.get('id'):
                    continue
                keep_ids.add(v['id'])
            mats['videos'] = keep
            new_tracks = []
            if not data.get('tracks'):
                data.get('tracks')
            for t in []:
                if t.get('type') != 'video':
                    new_tracks.append(t)
                    continue
                segs = []
                if not t.get('segments'):
                    t.get('segments')
                for s in []:
                    mid = s.get('material_id')
                    if mid and mid not in keep_ids:
                        continue
                    segs.append(s)
                t['segments'] = segs
                if not t.get('name'):
                    t.get('name')
                tname = ''
                if not segs and tname.startswith('Mumu'):
                    continue
                new_tracks.append(t)
            data['tracks'] = new_tracks
            self.save_draft(project_dir, data)
            logger.info('Purged junk media → %s (kept %d videos)', project_dir, len(keep))
            return None
        except Exception:
            return None
            except Exception:
                continue


    
    def lock_timeline_to_video(self = None, project_dir = None, video_path = None):
        '''
        Ép duration timeline = độ dài video gốc.

        Fix bug: SRT 2 phút + video 5 phút → export chỉ 2 phút (duration dính max SRT/voice).
        Sub/voice vẫn theo SRT; phần video còn lại giữ nguyên (im lặng / tiếng gốc đã mute).
        Returns duration microseconds.
        '''
        project_dir = Path(project_dir)
        data = self.load_draft(project_dir)
        mats = data.setdefault('materials', { })
        if not mats.get('videos'):
            mats.get('videos')
        videos = []
        vdur_us = 0
        if video_path and Path(video_path).is_file():
            
            try:
                probe_duration_s = probe_duration_s
                import app.services.audio_sync_engine
                vdur_us = sec_to_us(probe_duration_s(Path(video_path)))
                if vdur_us <= 0 and videos:
                    
                    try:
                        if not videos[0].get('duration'):
                            videos[0].get('duration')
                        vdur_us = int(0)
                        if vdur_us <= 0:
                            if not data.get('duration'):
                                data.get('duration')
                            vdur_us = int(0)
                            if not data.get('tracks'):
                                data.get('tracks')
                            for t in []:
                                if not t.get('segments'):
                                    t.get('segments')
                                for seg in []:
                                    if not seg.get('target_timerange'):
                                        seg.get('target_timerange')
                                    tr = { }
                                    if not tr.get('start'):
                                        tr.get('start')
                                    if not tr.get('duration'):
                                        tr.get('duration')
                                    end = int(0) + int(0)
                                    vdur_us = max(vdur_us, end)
                        if vdur_us <= 0:
                            return 0
                        data['duration'] = vdur_us
                        if videos:
                            if not videos[0].get('duration'):
                                videos[0].get('duration')
                            videos[0]['duration'] = max(int(0), vdur_us)
                        if not data.get('tracks'):
                            data.get('tracks')
                        for t in []:
                            if t.get('type') != 'video':
                                continue
                            if not t.get('name'):
                                t.get('name')
                            if ''.startswith('Mumu Logo'):
                                if not t.get('segments'):
                                    t.get('segments')
                                for seg in []:
                                    seg['source_timerange'] = {
                                        'start': 0,
                                        'duration': vdur_us }
                                    seg['target_timerange'] = {
                                        'start': 0,
                                        'duration': vdur_us }
                                continue
                            if not t.get('segments'):
                                t.get('segments')
                            segs = []
                            if not segs:
                                continue
                            seg = segs[0]
                            if not seg.get('source_timerange'):
                                seg.get('source_timerange')
                            src = {
                                'start': 0,
                                'duration': vdur_us }
                            if not src.get('start'):
                                src.get('start')
                            src_start = int(0)
                            seg['source_timerange'] = {
                                'start': src_start,
                                'duration': max(1, vdur_us - src_start) }
                            seg['target_timerange'] = {
                                'start': 0,
                                'duration': max(1, vdur_us - src_start) }
                            t['segments'] = [
                                seg]
                        self.save_draft(project_dir, data)
                        logger.info('Locked timeline duration to video: %.2fs (%d us) → %s', vdur_us / US, vdur_us, project_dir)
                        return vdur_us
                        except Exception:
                            e = None
                            logger.warning('probe video fail: %s', e)
                            e = None
                            del e
                            continue
                            e = None
                            del e
                    except (TypeError, ValueError):
                        vdur_us = 0
                        continue



    
    def apply_draft_options(self = None, project_dir = None, options = None):
        '''
        Áp dụng tuỳ chọn UI lên draft đã inject.

        Visual nặng (nhiễu / màu / GOP / zoompan / eq) → ffmpeg preprocess video.
        Text thương hiệu / watermark → text track full timeline.
        '''
        if not options:
            return None
        project_dir = Path(project_dir)
        options = dict(options)
    # WARNING: Decompyle incomplete

    
    def inject_brand_texts(self = None, project_dir = None, options = None):
        '''Chữ cố định + chữ mờ (watermark) → text track CapCut full duration.'''
        if not options:
            return []
        project_dir = None(project_dir)
        items = []
    # WARNING: Decompyle incomplete

    
    def inject_original_audio(self = None, project_dir = None, video_path = None, *, volume, mute_embedded, track_name, audio_filter, draft_options):
        '''
        Tách âm thanh từ video gốc (ffmpeg) → track audio riêng.

        CapCut đôi khi mute âm embedded khi inject TTS; track riêng đáng tin hơn.
        volume: 0..2 (CapCut segment volume).
        audio_filter / draft_options: tempo / lọc giọng (ffmpeg -af).
        '''
        project_dir = Path(project_dir)
        video_path = Path(video_path)
        if not video_path.is_file():
            return None
        import subprocess
        res = project_dir / 'Resources'
        res.mkdir(parents = True, exist_ok = True)
        out_audio = res / 'mumu_original_audio.m4a'
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            logger.warning('ffmpeg not found — cannot extract original audio')
            return None
    # WARNING: Decompyle incomplete

    
    def inject_bgm(self = None, project_dir = None, bgm_paths = None, *, volume, clips, track_name):
        '''Chèn nhạc nền (local extract_music) lên audio track mới.'''
        pass
    # WARNING: Decompyle incomplete

    
    def inject_logo(self = None, project_dir = None, logo_path = None, *, scale, track_name):
        '''
        Chèn logo PNG như video material (ảnh tĩnh) trên track video phụ.
        CapCut chấp nhận type photo/video cho ảnh.
        '''
        project_dir = Path(project_dir)
        logo_path = Path(logo_path)
        if not logo_path.is_file():
            logger.warning('Logo không tồn tại: %s', logo_path)
            return None
        data = self.load_draft(project_dir)
        mats = data.setdefault('materials', { })
        videos = _ensure_list(mats, 'videos')
        if not data.get('duration'):
            data.get('duration')
        total = int(US)
        res = project_dir / 'Resources'
        res.mkdir(parents = True, exist_ok = True)
        dest = res / f'''logo_{logo_path.name}'''
        if dest.resolve() != logo_path.resolve():
            shutil.copy2(logo_path, dest)
        mid = new_uuid()
        ph = _placeholder_rel(f'''Resources/{dest.name}''', self.path_placeholder)
        mat = {
            'id': mid,
            'type': 'photo',
            'path': ph,
            'media_path': ph,
            'material_name': dest.stem,
            'name': dest.stem,
            'duration': total,
            'width': 512,
            'height': 512,
            'has_audio': False,
            'check_flag': 1,
            'category_name': 'local' }
        videos.append(mat)
        track = {
            'attribute': 0,
            'flag': 0,
            'id': new_uuid(),
            'is_default_name': False,
            'name': track_name,
            'type': 'video',
            'segments': [] }
        seg_tpl = None
        if not data.get('tracks'):
            data.get('tracks')
        for t in []:
            if not t.get('type') == 'video':
                continue
            if not t.get('segments'):
                continue
            seg_tpl = deepcopy(t['segments'][0])
            []
    # WARNING: Decompyle incomplete

    
    def inject_subtitle_blur(self = None, project_dir = None, *, blur_x, blur_y, blur_w, blur_h, strength, feather, opacity, full_width_bottom, canvas_w, canvas_h, video_path):
        '''
        Che sub hardcode Trung:

        1) Overlay ảnh dải mờ (PIL blur từ frame video) — chắc chắn thấy trên timeline
        2) video_effect Blur + mask (nếu package CapCut còn trên máy)

        Mặc định: dải full-width đáy khung.
        strength / feather / opacity: 0..1
        '''
        project_dir = Path(project_dir)
        data0 = self.load_draft(project_dir)
        if not data0.get('canvas_config'):
            data0.get('canvas_config')
        canvas = { }
        if not canvas_w:
            canvas_w
            if not canvas.get('width'):
                canvas.get('width')
        cw = int(0)
        if not canvas_h:
            canvas_h
            if not canvas.get('height'):
                canvas.get('height')
        ch = int(0)
        if cw <= 0 or ch <= 0:
            vp = Path(video_path) if video_path else None
            if vp and vp.is_file():
                
                try:
                    probe_video_size = probe_video_size
                    import app.ui.widgets.blur_region_editor
                    (cw, ch) = probe_video_size(vp)
                if not canvas.get('width'):
                    canvas.get('width')

            if not canvas.get('height'):
                canvas.get('height')
            ch = int(1920)
            cw = int(1080)
        if cw <= 0:
            cw = 1080
        if ch <= 0:
            ch = 1920
        
        def _01(v = None, default = None):
            pass
        # WARNING: Decompyle incomplete

        strength_f = _01(strength, 0.7)
        feather_f = _01(feather, 0.25)
        opacity_f = _01(opacity, 0.9)
        capcut_feather = max(0, min(0.5, feather_f * 0.45))
        if full_width_bottom:
            full_width_bottom
            if not blur_w is None:
                blur_w is None
                if not blur_w:
                    blur_w
                if not float(0) <= 0:
                    float(0) <= 0
                    if not blur_h:
                        blur_h
        use_full = float(0) <= 0
        if use_full:
            by = int(ch * 0.88)
            bx = 0
            bh = max(8, int(ch * 0.12))
            bw = cw
            cfg = {
                'width': 1,
                'height': 0.12,
                'centerX': 0,
                'centerY': -0.78,
                'rotation': 0,
                'feather': capcut_feather if capcut_feather > 0 else 0.16,
                'expansion': 0,
                'roundCorner': 0.04,
                'invert': False,
                'aspectRatio': 1 }
    # WARNING: Decompyle incomplete

    
    def inject_blur_cover_overlay(self = None, project_dir = None, *, x, y, w, h, canvas_w, canvas_h, video_path, strength, feather, opacity, track_name):
        '''
        Dải mờ che sub Trung — PNG **chỉ đúng vùng blur** (không full-canvas).

        CapCut hay render PNG full-canvas + alpha thành **màn hình đen** / lag.
        Strip RGB mờ + scale/transform → ổn định.
        '''
        project_dir = Path(project_dir)
        data = self.load_draft(project_dir)
        mats = data.setdefault('materials', { })
        videos = _ensure_list(mats, 'videos')
        if not data.get('duration'):
            data.get('duration')
        total = int(US)
        strength = max(0.05, min(1, float(strength)))
        feather = max(0, min(1, float(feather)))
        opacity = max(0, min(1, float(opacity)))
        tracks = _ensure_list(data, 'tracks')
    # WARNING: Decompyle incomplete

    
    def build_from_srt(self = None, srt_path = None, *, project_name, overwrite, voice_cues, voice_file, video_path, voice_volume, draft_options):
        '''
        Full flow: clone template → inject SRT → inject voice → apply options.
        '''
        srt_path = Path(srt_path)
        if not project_name:
            project_name
        name = f'''Mumu_Inject_{time.strftime('%Y%m%d_%H%M%S')}'''
        
        try:
            project_dir = self.clone_template(name, overwrite = overwrite)
            cues = load_srt_cues(srt_path)
            sub_style = None
            if draft_options:
                if not draft_options.get('blur_canvas_w'):
                    draft_options.get('blur_canvas_w')
                if not draft_options.get('blur_canvas_h'):
                    draft_options.get('blur_canvas_h')
                sub_style = {
                    'sub_font': draft_options.get('sub_font'),
                    'sub_size': draft_options.get('sub_size'),
                    'sub_bg_style': draft_options.get('sub_bg_style'),
                    'sub_bg_enable': draft_options.get('sub_bg_enable'),
                    'sub_x': draft_options.get('sub_x'),
                    'sub_y': draft_options.get('sub_y'),
                    'sub_box_w': draft_options.get('sub_box_w'),
                    'sub_box_h': draft_options.get('sub_box_h'),
                    'canvas_w': draft_options.get('canvas_w'),
                    'canvas_h': draft_options.get('canvas_h') }
            text_ids = self.inject_srt(project_dir, cues = cues, update_duration = False, style = sub_style)
            audio_ids = []
            if voice_cues:
                linked = []
                for vc in voice_cues:
                    tid = text_ids[vc.index] if vc.index < len(text_ids) else None
                    if not vc.text:
                        vc.text
                    if not vc.text_material_id:
                        vc.text_material_id
                    linked.append(VoiceCue(index = vc.index, start_s = vc.start_s, duration_s = vc.duration_s, path = vc.path, text = cues[vc.index].text if vc.index < len(cues) else '', text_material_id = tid))
                audio_ids = self.inject_voice_cues(project_dir, linked, volume = voice_volume)
            elif voice_file:
                aid = self.inject_voice_file(project_dir, voice_file, volume = voice_volume)
                if aid:
                    audio_ids = [
                        aid]
            if video_path:
                self.set_main_video(project_dir, video_path, lock_duration = True)
            if draft_options:
                self.apply_draft_options(project_dir, draft_options)
            if video_path:
                self._purge_junk_media(project_dir)
            else:
                data = self.load_draft(project_dir)
                if not data.get('duration'):
                    data.get('duration')
                max_end = int(0)
                if not data.get('tracks'):
                    data.get('tracks')
                for t in []:
                    if not t.get('segments'):
                        t.get('segments')
                    for seg in []:
                        if not seg.get('target_timerange'):
                            seg.get('target_timerange')
                        tr = { }
                        if not tr.get('start'):
                            tr.get('start')
                        if not tr.get('duration'):
                            tr.get('duration')
                        max_end = max(max_end, int(0) + int(0))
                if not data.get('duration'):
                    data.get('duration')
                if max_end > int(0):
                    data['duration'] = max_end
                    self.save_draft(project_dir, data)
            
            try:
                write_export_readme = write_export_readme
                import app.services.capcut_export
                write_export_readme(project_dir, project_name = name)
                
                try:
                    return BuildResult(ok = True, project_dir = project_dir, project_name = name, n_subtitles = len(text_ids), n_voice_cues = len(audio_ids), draft_json = project_dir / 'draft_content.json', message = f'''OK — mở CapCut project \'{name}\' để xem sub + voice''', text_ids = text_ids, audio_ids = audio_ids)
                    except Exception:
                        
                        try:
                            continue
                            
                            try:
                                pass
                            except Exception:
                                e = None
                                logger.exception('build_from_srt failed')
                                del e
                                return None
                                None = 
                                del e






    
    def build_from_sync_result(self = None, srt_path = None, *, final_voice_path, segment_reports, project_name, prefer_per_cue, overwrite, voice_volume):
        '''
        Nối với AudioSyncEngine:
          - prefer_per_cue=False (mặc định): inject final_voice.mp3 1 track
          - prefer_per_cue=True: dùng reports[].segment_path từng câu
        '''
        voice_cues = None
        voice_file = Path(final_voice_path) if final_voice_path else None
    # WARNING: Decompyle incomplete



def main(argv = None):
    import argparse
    logging.basicConfig(level = logging.INFO, format = '%(levelname)s | %(message)s')
    p = argparse.ArgumentParser(description = 'CapCutDraftBuilder — inject SRT + voice vào draft CapCut')
    p.add_argument('--srt', required = True, help = 'Đường dẫn file .srt')
    p.add_argument('--name', default = None, help = 'Tên project CapCut mới')
    p.add_argument('--template', default = DEFAULT_TEMPLATE_NAME, help = 'Tên template project')
    p.add_argument('--drafts-root', default = None, help = 'Override drafts root')
    p.add_argument('--voice', default = None, help = 'File voice full timeline (mp3/wav)')
    p.add_argument('--video', default = None, help = 'Video thay thế (optional)')
    p.add_argument('--volume', type = float, default = 1.5, help = 'Volume voice track')
    p.add_argument('--no-overwrite', action = 'store_true')
    args = p.parse_args(argv)
    builder = CapCutDraftBuilder(drafts_root = args.drafts_root, template_name = args.template)
    result = builder.build_from_srt(args.srt, project_name = args.name, overwrite = not (args.no_overwrite), voice_file = args.voice, video_path = args.video, voice_volume = args.volume)
    print('ok:', result.ok)
    print('message:', result.message)
    print('project:', result.project_dir)
    print('subtitles:', result.n_subtitles, 'voice:', result.n_voice_cues)
    if result.ok:
        return 0

if __name__ == '__main__':
    raise SystemExit(main())

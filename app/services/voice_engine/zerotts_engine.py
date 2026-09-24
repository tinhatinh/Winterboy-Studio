'''
zerotts_engine — Lõi tổng hợp giọng nói ZeroTTS (AI tiếng Việt Offline 48kHz ONNX).

Đặc điểm kiến trúc:
1. Mô hình 202M tham số chạy hoàn toàn trên CPU qua ONNX Runtime + NumPy.
2. Bộ giải mã âm thanh MOSS codec chất lượng cao 48kHz.
3. Chuẩn hóa văn bản tiếng Việt tích hợp (số, tiền tệ, ngày tháng, từ viết tắt).
4. Tự động tải và cache model từ Hugging Face Hub (zeroweight-ai/ZeroTTS) dạng lazy load.
5. Danh mục 8 giọng chuẩn phòng thu với kho mẫu nghe thử tức thì 0ms.
'''
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}

# Kho giọng preset: 'name' là id gửi cho model, 'label' là thứ UI hiển thị.
ZEROTTS_PRESET_VOICES: List[Dict[str, str]] = [
    {
        'id': 'maichi',
        'name': 'maichi',
        'display_name': 'Mai Chi',
        'gender': 'Nữ',
        'style': 'Kể chuyện',
        'description': 'Nữ trẻ, kể chuyện, nhẹ nhàng, thân thiện',
        'label': 'Mai Chi (Nữ - Kể chuyện nhẹ nhàng)'
    },
    {
        'id': 'baotrang',
        'name': 'baotrang',
        'display_name': 'Bảo Trang',
        'gender': 'Nữ',
        'style': 'Tin tức',
        'description': 'Nữ trưởng thành, tin tức, rõ ràng, trung tính',
        'label': 'Bảo Trang (Nữ - Tin tức chuẩn)'
    },
    {
        'id': 'kimoanh',
        'name': 'kimoanh',
        'display_name': 'Kim Oanh',
        'gender': 'Nữ',
        'style': 'Kể chuyện',
        'description': 'Nữ trung niên, kể chuyện, ấm áp, truyền cảm',
        'label': 'Kim Oanh (Nữ - Truyền cảm ấm áp)'
    },
    {
        'id': 'hamy',
        'name': 'hamy',
        'display_name': 'Hà My',
        'gender': 'Nữ',
        'style': 'Hoạt hình',
        'description': 'Nữ trẻ, hoạt hình, cao, biểu cảm',
        'label': 'Hà My (Nữ - Hoạt hình vui vẻ)'
    },
    {
        'id': 'giahuy',
        'name': 'giahuy',
        'display_name': 'Gia Huy',
        'gender': 'Nam',
        'style': 'Kể chuyện',
        'description': 'Nam trẻ, kể chuyện, trầm ấm, tâm tình',
        'label': 'Gia Huy (Nam - Kể chuyện trầm ấm)'
    },
    {
        'id': 'huuduc',
        'name': 'huuduc',
        'display_name': 'Hữu Đức',
        'gender': 'Nam',
        'style': 'Kể chuyện',
        'description': 'Nam lớn tuổi, kể chuyện, trầm, điềm đạm',
        'label': 'Hữu Đức (Nam - Điềm đạm lớn tuổi)'
    },
    {
        'id': 'quangminh',
        'name': 'quangminh',
        'display_name': 'Quang Minh',
        'gender': 'Nam',
        'style': 'Tin tức',
        'description': 'Nam trẻ, tin tức, rõ ràng, dứt khoát',
        'label': 'Quang Minh (Nam - Tin tức dứt khoát)'
    },
    {
        'id': 'tiendat',
        'name': 'tiendat',
        'display_name': 'Tiến Đạt',
        'gender': 'Nam',
        'style': 'Bình luận',
        'description': 'Nam trẻ, bình luận, sôi nổi, năng lượng cao',
        'label': 'Tiến Đạt (Nam - Sôi nổi năng lượng)'
    },
]

VOICE_NAMES = [v['name'] for v in ZEROTTS_PRESET_VOICES]
VOICE_LABELS = {v['name']: v['label'] for v in ZEROTTS_PRESET_VOICES}

# Tra ngược: id / display_name / label / 'label | id' (lowercase) -> id chuẩn.
VOICE_MAP: Dict[str, str] = {}
for _v in ZEROTTS_PRESET_VOICES:
    VOICE_MAP[_v['name'].lower()] = _v['name']
    VOICE_MAP[_v['display_name'].lower()] = _v['name']
    VOICE_MAP[_v['label'].lower()] = _v['name']
    VOICE_MAP[f'{_v["label"]} | {_v["name"]}'.lower()] = _v['name']


def resolve_voice_name(voice: str) -> str:
    '''Chuyển đổi bất kỳ label, display_name hoặc voice_id nào thành tên voice id chuẩn (maichi, baotrang...).'''
    if not voice:
        return 'maichi'
    v_clean = str(voice).strip()
    if '|' in v_clean:
        v_id = v_clean.rsplit('|', 1)[-1].strip()
        if v_id in VOICE_NAMES:
            return v_id
        v_clean = v_id
    if v_clean in VOICE_NAMES:
        return v_clean
    low = v_clean.lower()
    if low in VOICE_MAP:
        return VOICE_MAP[low]
    # Nhãn UI có thể bị nối thêm hậu tố -> dò trong.
    for name in VOICE_NAMES:
        if name in low:
            return name
    for _v in ZEROTTS_PRESET_VOICES:
        if _v['display_name'].lower() in low:
            return _v['name']
    return 'maichi'


def _ensure_safe_environment() -> None:
    '''Đảm bảo không bị lỗi NoneType stream và tắt progress bar gây xung đột trên GUI Windows.'''
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    os.environ['TQDM_DISABLE'] = '1'
    if getattr(sys, 'stdout', None) is None:
        class _NullWriter:
            def write(self, s=''):
                return len(s) if s else 0

            def flush(self):
                pass

            def isatty(self):
                return False

            def reconfigure(self, **kw):
                pass
        sys.stdout = _NullWriter()
    if getattr(sys, 'stderr', None) is None:
        class _NullWriter:
            def write(self, s=''):
                return len(s) if s else 0

            def flush(self):
                pass

            def isatty(self):
                return False

            def reconfigure(self, **kw):
                pass
        sys.stderr = _NullWriter()


def _resolve_local_cached_model_path(model_id: str) -> str:
    '''Nếu model đã tải về trong Hugging Face cache hoặc đĩa cứng, trả về đường dẫn folder cục bộ để nạp thẳng.'''
    if not model_id:
        return model_id
    path_obj = Path(model_id).expanduser()
    if path_obj.is_dir():
        return str(path_obj)
    try:
        from huggingface_hub import try_to_load_from_cache
        cached_file = try_to_load_from_cache(str(model_id), 'config.json')
        if cached_file:
            cached_dir = Path(cached_file).parent
            req_files = ('config.json', 'null_voice_emb.npy', 'onnx/text_encoder.onnx')
            if all((cached_dir / f).exists() for f in req_files):
                logger.info('Phát hiện mô hình ZeroTTS đã nạp sẵn tại cache: %s', cached_dir)
                return str(cached_dir)
    except Exception as exc:
        logger.debug('Không thể đọc cache trực tiếp, dùng repo_id: %s', exc)
    return str(model_id)


def _load_zerotts_module():
    '''Nạp module zerotts ưu tiên từ hệ thống hoặc vendored package trong app.'''
    try:
        import zerotts
        return zerotts
    except ImportError:
        try:
            from app.services.voice_engine import zerotts
            return zerotts
        except ImportError as exc:
            logger.error('Không thể import gói zerotts: %s', exc)


class ZeroTTSEngine:
    '''Singleton điều khiển việc tải model và tổng hợp âm thanh với ZeroTTS.'''

    _instance: Optional['ZeroTTSEngine'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ZeroTTSEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_id: str = 'zeroweight-ai/ZeroTTS'):
        if self._initialized:
            return
        self.model_id = model_id
        self._tts = None
        self._is_loading = False
        self._initialized = True

    def is_model_loaded(self) -> bool:
        '''Kiểm tra model ONNX đã nạp vào RAM hay chưa.'''
        return self._tts is not None

    def _get_tts(self):
        '''Lazy load model ZeroTTS khi thực sự cần dùng để app khởi động nhanh.'''
        if self._tts is None:
            _ensure_safe_environment()
            zerotts_mod = _load_zerotts_module()
            if zerotts_mod is None:
                raise RuntimeError(
                    'Thư viện ZeroTTS chưa được cài đặt hoặc thiếu dependency (onnxruntime, tokenizers, soundfile).'
                )

            logger.info('Đang nạp mô hình ZeroTTS (%s)...', self.model_id)
            self._is_loading = True

            try:
                resolved_target = _resolve_local_cached_model_path(self.model_id)
                self._tts = zerotts_mod.ZeroTTS.from_pretrained(
                    resolved_target,
                    providers=['CPUExecutionProvider'],
                    warmup=True)

                logger.info('Mô hình ZeroTTS đã nạp và warmup thành công!')
            except Exception as exc:
                logger.error('Lỗi khi tải hoặc nạp mô hình ZeroTTS: %s', exc)
                raise RuntimeError(f'Không thể khởi tạo ZeroTTS: {exc}') from exc
            finally:
                self._is_loading = False

        return self._tts

    def list_preset_voices(self) -> List[Dict[str, str]]:
        '''Trả về danh mục 8 giọng đọc preset kèm thông tin hiển thị.'''
        return ZEROTTS_PRESET_VOICES

    def list_voice_tuples(self) -> List[Tuple[str, str]]:
        '''Trả về danh sách (display_label, voice_name) cho OptionMenu UI.'''
        return [(f'{v["label"]} | {v["name"]}', v['name']) for v in ZEROTTS_PRESET_VOICES]

    def get_preview_audio_path(self, voice_name: str) -> Optional[Path]:
        '''Lấy đường dẫn file nghe thử mẫu của giọng (ưu tiên file đóng gói sẵn).'''
        clean_voice = resolve_voice_name(voice_name)

        import sys
        candidates = [
            Path(__file__).resolve().parents[2] / 'assets' / 'tts_samples' / 'zerotts' / f'{clean_voice}.wav',
            Path(__file__).resolve().parents[3] / 'preview' / 'zerotts' / f'{clean_voice}.wav',
            Path.cwd() / 'preview' / 'zerotts' / f'{clean_voice}.wav',
        ]

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass = Path(sys._MEIPASS)
            candidates.insert(0, meipass / 'preview' / 'zerotts' / f'{clean_voice}.wav')
            candidates.insert(1, meipass / 'app' / 'assets' / 'tts_samples' / 'zerotts' / f'{clean_voice}.wav')

        for cand in candidates:
            if cand.is_file() and cand.stat().st_size > 1000:
                return cand

        return None

    def normalize_text(self, text: str) -> str:
        '''Chuẩn hóa văn bản tiếng Việt sang dạng nói tự nhiên (chữ, số, viết tắt).'''
        content = (text or '').strip()
        if not content:
            return ''

        zerotts_mod = _load_zerotts_module()
        if zerotts_mod is not None:
            try:
                from zerotts.text_norm import normalize_vi_text
                from zerotts.chunking import normalize_punctuation
                content = normalize_vi_text(content)
                content = normalize_punctuation(content)
            except Exception as e:
                logger.debug('Lỗi chuẩn hóa text_norm zerotts: %s, tiếp tục với text gốc.', e)

        return content

    def synthesize(self, text: str, voice: str = 'maichi', speed: float = 1.0,
                   out_path: Optional[str] = None,
                   cfg_scale: float = 1.0) -> str:
        '''
        Tổng hợp giọng đọc tiếng Việt bằng ZeroTTS ONNX (48kHz).
        Trả về đường dẫn tuyệt đối của file âm thanh được xuất ra.
        '''
        raw_text = (text or '').strip()
        if not raw_text:
            raise ValueError('Văn bản rỗng, không thể tổng hợp giọng đọc.')

        clean_text = self.normalize_text(raw_text)
        if not clean_text:
            clean_text = raw_text

        tts = self._get_tts()
        clean_voice = resolve_voice_name(voice)

        audio = tts.synthesize(
            clean_text,
            clean_voice,
            cfg_scale=cfg_scale)

        if not out_path:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                out_path = tmp.name

        out_path_obj = Path(out_path).resolve()
        out_path_obj.parent.mkdir(parents=True, exist_ok=True)

        is_mp3 = out_path_obj.suffix.lower() == '.mp3'
        temp_wav = str(out_path_obj.with_suffix('.temp.wav')) if (is_mp3 or abs(speed - 1.0) > 0.05) else str(out_path_obj)

        if isinstance(audio, np.ndarray):
            if audio.ndim == 2:
                audio_mono = audio[0]
            else:
                audio_mono = audio
            clip = np.clip(audio_mono, -1.0, 1.0)
            sf.write(temp_wav, clip, SAMPLE_RATE, subtype='PCM_16')
        else:
            tts.save_audio(audio, temp_wav)

        if abs(speed - 1.0) > 0.05 or is_mp3:
            self._process_audio_output(temp_wav, str(out_path_obj), speed=speed, is_mp3=is_mp3)
            try:
                if os.path.exists(temp_wav) and temp_wav != str(out_path_obj):
                    os.remove(temp_wav)
            except Exception:
                pass

        return str(out_path_obj)

    def _process_audio_output(self, src_wav: str, dst_path: str,
                              speed: float = 1.0, is_mp3: bool = False) -> None:
        '''Dùng ffmpeg để đổi tốc độ (atempo) và/hoặc nén MP3 192k.'''
        from app.services.voice_engine.audio_merger import find_ffmpeg_bin
        ff = find_ffmpeg_bin()

        filter_parts = []
        # ffmpeg chỉ nhận atempo trong 0.5..2.0 nên phải kẹp miền.
        cur_speed = max(0.5, min(2.0, speed))
        if abs(cur_speed - 1.0) > 0.05:
            filter_parts.append(f'atempo={cur_speed:.3f}')

        cmd = [ff, '-y', '-i', src_wav]
        if filter_parts:
            cmd.extend(['-filter:a', ','.join(filter_parts)])

        if is_mp3:
            cmd.extend(['-c:a', 'libmp3lame', '-b:a', '192k', '-ar', '48000', dst_path])
        else:
            cmd.extend(['-c:a', 'pcm_s16le', '-ar', '48000', dst_path])

        subprocess.run(
            cmd,
            capture_output=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            check=True)

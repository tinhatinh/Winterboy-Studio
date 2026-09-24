'''
Edge-TTS engine — giọng đọc Microsoft Edge (miễn phí, không API key).

Dùng làm thay thế Text Reading CapCut (Thanh Thanh / Tâm Sự…):
  Python sinh MP3/WAV → AudioSyncEngine fit D_sub → CapCutDraftBuilder inject.

Hàm chính:
  edge_tts_generate(text, out_path, voice=..., rate=...)  # sync, cho AudioSyncEngine
  make_tts_func(voice, rate) → Callable[[str, Path], Path]
  list_vietnamese_voices()
'''
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Hai giọng tiếng Việt chính thức của Microsoft — luôn có, không cần mạng.
VI_VOICES = [
    'vi-VN-HoaiMyNeural',
    'vi-VN-NamMinhNeural'
]

# Voice mặc định khi UI chưa chọn gì.
DEFAULT_VOICE = 'vi-VN-HoaiMyNeural'

# Nhãn rút gọn (được ghi đè ở dưới bằng nhãn đầy đủ của EDGE_ALL_VOICES).
VOICE_LABELS = {
    'vi-VN-HoaiMyNeural': 'Nữ - Cô Gái Hoạt Ngôn',
    'vi-VN-NamMinhNeural': 'Nam - Thanh Niên Tự Tin'
}

# Edge chỉ nhận rate dạng '+20%' / '-15%'.
_RATE_RE = re.compile(r'^[+-]?\d+%$')

# Danh mục tuyển chọn, gắn nhãn tiếng Việt để hiển thị trong OptionMenu.
EDGE_ALL_VOICES: list[tuple[str, str]] = [
    ('vi-VN-HoaiMyNeural', 'Nữ - Hoài My (Tiếng Việt)'),
    ('vi-VN-NamMinhNeural', 'Nam - Nam Minh (Tiếng Việt)'),
    (
        'en-US-AndrewMultilingualNeural',
        'Nam - Andrew (Đa ngôn ngữ - Đọc tiếng Việt)',
    ),
    ('en-US-AvaMultilingualNeural', 'Nữ - Ava (Đa ngôn ngữ - Đọc tiếng Việt)'),
    (
        'en-US-BrianMultilingualNeural',
        'Nam - Brian (Đa ngôn ngữ - Đọc tiếng Việt)',
    ),
    ('en-US-EmmaMultilingualNeural', 'Nữ - Emma (Đa ngôn ngữ - Đọc tiếng Việt)'),
    ('en-AU-WilliamMultilingualNeural', 'Nam - William (Đa ngôn ngữ - Úc)'),
    ('fr-FR-VivienneMultilingualNeural', 'Nữ - Vivienne (Đa ngôn ngữ - Pháp)'),
    ('fr-FR-RemyMultilingualNeural', 'Nam - Remy (Đa ngôn ngữ - Pháp)'),
    ('de-DE-SeraphinaMultilingualNeural', 'Nữ - Seraphina (Đa ngôn ngữ - Đức)'),
    ('de-DE-FlorianMultilingualNeural', 'Nam - Florian (Đa ngôn ngữ - Đức)'),
    ('it-IT-GiuseppeMultilingualNeural', 'Nam - Giuseppe (Đa ngôn ngữ - Ý)'),
    ('ko-KR-HyunsuMultilingualNeural', 'Nam - Hyunsu (Đa ngôn ngữ - Hàn Quốc)'),
    ('pt-BR-ThalitaMultilingualNeural', 'Nữ - Thalita (Đa ngôn ngữ - Bồ Đào Nha)'),
    ('en-US-JennyNeural', 'Nữ - Jenny (Tiếng Anh - US Tự nhiên)'),
    ('en-US-GuyNeural', 'Nam - Guy (Tiếng Anh - US Trầm ấm)'),
    ('en-US-AriaNeural', 'Nữ - Aria (Tiếng Anh - US Biểu cảm)'),
    ('en-US-ChristopherNeural', 'Nam - Christopher (Tiếng Anh - US Chuẩn)'),
    ('en-US-EricNeural', 'Nam - Eric (Tiếng Anh - US)'),
    ('en-US-MichelleNeural', 'Nữ - Michelle (Tiếng Anh - US)'),
    ('en-US-RogerNeural', 'Nam - Roger (Tiếng Anh - US)'),
    ('en-US-SteffanNeural', 'Nam - Steffan (Tiếng Anh - US)'),
    ('en-GB-SoniaNeural', 'Nữ - Sonia (Tiếng Anh - UK Quý phái)'),
    ('en-GB-RyanNeural', 'Nam - Ryan (Tiếng Anh - UK)'),
    ('en-GB-LibbyNeural', 'Nữ - Libby (Tiếng Anh - UK)'),
    ('en-AU-NatashaNeural', 'Nữ - Natasha (Tiếng Anh - Úc)'),
    ('en-CA-ClaraNeural', 'Nữ - Clara (Tiếng Anh - Canada)'),
    ('en-CA-LiamNeural', 'Nam - Liam (Tiếng Anh - Canada)'),
    ('en-IN-NeerjaNeural', 'Nữ - Neerja (Tiếng Anh - Ấn Độ)'),
    ('en-IN-PrabhatNeural', 'Nam - Prabhat (Tiếng Anh - Ấn Độ)'),
    ('zh-CN-XiaoxiaoNeural', 'Nữ - Xiaoxiao (Tiếng Trung - Phổ thông ấm áp)'),
    ('zh-CN-YunxiNeural', 'Nam - Yunxi (Tiếng Trung - Phổ thông trẻ trung)'),
    (
        'zh-CN-YunjianNeural',
        'Nam - Yunjian (Tiếng Trung - Kịch tính / Review phim)',
    ),
    ('zh-CN-XiaoyiNeural', 'Nữ - Xiaoyi (Tiếng Trung - Tự nhiên)'),
    ('zh-CN-YunyangNeural', 'Nam - Yunyang (Tiếng Trung - Tin tức / MC)'),
    (
        'zh-CN-liaoning-XiaobeiNeural',
        'Nữ - Xiaobei (Tiếng Trung - Đông Bắc/Liêu Ninh)',
    ),
    ('zh-CN-shaanxi-XiaoniNeural', 'Nữ - Xiaoni (Tiếng Trung - Thiểm Tây)'),
    ('zh-HK-HiuMaanNeural', 'Nữ - HiuMaan (Tiếng Trung - Quảng Đông/HK)'),
    ('zh-HK-WanLungNeural', 'Nam - WanLung (Tiếng Trung - Quảng Đông/HK)'),
    ('zh-TW-HsiaoChenNeural', 'Nữ - HsiaoChen (Tiếng Trung - Đài Loan)'),
    ('zh-TW-YunJheNeural', 'Nam - YunJhe (Tiếng Trung - Đài Loan)'),
    ('ja-JP-NanamiNeural', 'Nữ - Nanami (Tiếng Nhật - Ngọt ngào)'),
    ('ja-JP-KeitaNeural', 'Nam - Keita (Tiếng Nhật - Chuẩn)'),
    ('ko-KR-SunHiNeural', 'Nữ - Sun-Hi (Tiếng Hàn - Tự nhiên)'),
    ('ko-KR-InJoonNeural', 'Nam - InJoon (Tiếng Hàn - Chuẩn)'),
    ('th-TH-PremwadeeNeural', 'Nữ - Premwadee (Tiếng Thái)'),
    ('th-TH-NiwatNeural', 'Nam - Niwat (Tiếng Thái)'),
    ('fr-FR-DeniseNeural', 'Nữ - Denise (Tiếng Pháp)'),
    ('fr-FR-HenriNeural', 'Nam - Henri (Tiếng Pháp)'),
    ('de-DE-KatjaNeural', 'Nữ - Katja (Tiếng Đức)'),
    ('de-DE-ConradNeural', 'Nam - Conrad (Tiếng Đức)'),
    ('es-ES-ElviraNeural', 'Nữ - Elvira (Tiếng Tây Ban Nha)'),
    ('es-ES-AlvaroNeural', 'Nam - Alvaro (Tiếng Tây Ban Nha)'),
    ('pt-BR-FranciscaNeural', 'Nữ - Francisca (Tiếng Bồ Đào Nha - Brazil)'),
    ('pt-BR-AntonioNeural', 'Nam - Antonio (Tiếng Bồ Đào Nha - Brazil)'),
    ('ru-RU-SvetlanaNeural', 'Nữ - Svetlana (Tiếng Nga)'),
    ('ru-RU-DmitryNeural', 'Nam - Dmitry (Tiếng Nga)'),
    ('id-ID-GadisNeural', 'Nữ - Gadis (Tiếng Indonesia)'),
    ('id-ID-ArdiNeural', 'Nam - Ardi (Tiếng Indonesia)'),
    ('fil-PH-BlessicaNeural', 'Nữ - Blessica (Tiếng Philippines)'),
    ('ms-MY-YasminNeural', 'Nữ - Yasmin (Tiếng Malaysia)'),
    ('lo-LA-KeomanyNeural', 'Nữ - Keomany (Tiếng Lào)'),
    ('km-KH-SreymomNeural', 'Nữ - Sreymom (Tiếng Khmer)'),
    ('hi-IN-SwaraNeural', 'Nữ - Swara (Tiếng Hindi - Ấn Độ)'),
]

# Chuỗi 'voiceId|Nhãn' — định dạng UI lưu vào preset.
EDGE_CURATED_LABELS: list[str] = [f'{vid}|{lbl}' for vid, lbl in EDGE_ALL_VOICES]
VOICE_LABELS: dict[str, str] = {vid: lbl for vid, lbl in EDGE_ALL_VOICES}


def list_vietnamese_voices() -> list[str]:
    return list(VI_VOICES)


def list_all_edge_voices() -> list[tuple[str, str]]:
    options = list_edge_tts_options()
    results = []
    for opt in options:
        if '|' in opt:
            vid, lbl = opt.split('|', 1)
            results.append((vid.strip(), lbl.strip()))
        else:
            results.append((opt.strip(), opt.strip()))
    return results or list(EDGE_ALL_VOICES)


def fetch_all_edge_voices_online(force_refresh: bool = False) -> list[str]:
    '''Tải toàn bộ 300+ giọng Edge TTS từ máy chủ Microsoft và định dạng nhãn chuẩn.'''
    import edge_tts
    import json

    cache_file = Path('output') / 'edge_voices_cache.json'
    if not force_refresh and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding='utf-8'))
            if isinstance(cached, list) and len(cached) > len(EDGE_ALL_VOICES):
                return cached
        except Exception:
            pass

    async def _fetch():
        return await edge_tts.list_voices()

    try:
        voices = _run_coro(_fetch())
    except Exception as exc:
        logger.warning('fetch_all_edge_voices_online fail: %s', exc)
        return list_edge_tts_options()

    if not voices:
        return list_edge_tts_options()

    known_friendly = dict(EDGE_ALL_VOICES)

    def sort_key(v: dict) -> tuple[int, str, str]:
        sn = v.get('ShortName', '')
        loc = v.get('Locale', '')
        if loc.startswith('vi-'):
            return (0, loc, sn)
        if 'Multilingual' in sn or 'multilingual' in v.get('FriendlyName', '').lower():
            return (1, loc, sn)
        if loc.startswith('en-'):
            return (2, loc, sn)
        if loc.startswith('zh-'):
            return (3, loc, sn)
        if loc.startswith('ja-') or loc.startswith('ko-') or loc.startswith('th-'):
            return (4, loc, sn)
        return (5, loc, sn)

    sorted_voices = sorted(voices, key=sort_key)
    results = []

    for v in sorted_voices:
        sn = v.get('ShortName', '')
        if not sn:
            continue
        if sn in known_friendly:
            results.append(f'{sn}|{known_friendly[sn]}')
            continue
        gender = 'Nữ' if v.get('Gender') == 'Female' else 'Nam'
        name = sn.split('-')[-1].replace('Neural', '')
        loc = v.get('LocaleName', v.get('Locale', ''))
        results.append(f'{sn}|{gender} - {name} ({loc})')

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                              encoding='utf-8')
    except Exception as exc:
        logger.debug('Could not save edge_voices_cache.json: %s', exc)
    return results


def list_edge_tts_options() -> list[str]:
    '''Trả về danh sách giọng Edge TTS: ưu tiên cache đã nạp, fallback danh sách tuyển chọn phong phú.'''
    import json

    cache_file = Path('output') / 'edge_voices_cache.json'
    if cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding='utf-8'))
            if isinstance(cached, list) and len(cached) >= len(EDGE_CURATED_LABELS):
                return cached
        except Exception:
            pass
        return list(EDGE_CURATED_LABELS)
    return list(EDGE_CURATED_LABELS)


def normalize_voice(voice: str | None) -> str:
    '''
    UI có thể chọn 'vi-VN-HoaiMyNeural|Nữ - ...' hoặc chỉ nhãn hiển thị 'Nữ - Hoài My'.
    Luôn chuẩn hoá về voice ID chính xác của Microsoft Edge.
    '''
    if not voice:
        return DEFAULT_VOICE
    v = voice.strip().split('|')[0].strip()
    for vid, _ in EDGE_ALL_VOICES:
        if v == vid:
            return v
    if v in VI_VOICES:
        return v
    if '-' in v and 'neural' in v.lower():
        return v
    low = voice.casefold()
    if any(k in low for k in ('hoaimy', 'hoài my', 'hoat ngon', 'hoạt ngôn')):
        return 'vi-VN-HoaiMyNeural'
    if any(k in low for k in ('namminh', 'nam minh', 'tu tin', 'tự tin')):
        return 'vi-VN-NamMinhNeural'
    return v if '-' in v else DEFAULT_VOICE


def speed_to_edge_rate(speed: float | str | None) -> str:
    '''
    UI tts_speed: 0.8 / 1.0 / 1.2 …
    Edge rate: phần trăm lệch so với 1.0
      1.0 → +0%
      1.2 → +20%
      0.8 → -20%
    '''
    try:
        s = float(speed) if speed is not None else 1.0
    except (TypeError, ValueError):
        s = 1.0
    s = max(0.5, min(2.0, s))
    pct = int(round((s - 1.0) * 100))
    if pct >= 0:
        return f'+{pct}%'
    return f'{pct}%'


def _run_coro(coro):
    '''Chạy async edge-tts an toàn từ thread sync (UI / AudioSyncEngine).'''
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None or not loop.is_running():
        return asyncio.run(coro)

    # Đang ở trong event loop (GUI) -> phải đẩy coroutine sang thread khác.
    result = []
    error = []

    def _target() -> None:
        try:
            result.append(asyncio.run(coro))
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    if error:
        raise error[0]
    return result[0]


def sanitize_edge_text(text: str) -> str:
    '''
    Làm sạch text SRT trước khi gửi Edge-TTS.
    Server hay trả NoAudioReceived với ký tự lạ / SSML / quá ngắn.
    '''
    t = (text or '').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    # Bỏ tag SSML/HTML và placeholder {…} của CapCut
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\{[^}]*\}', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Dấu ba chấm dài -> rút về 2 dấu, server hay chặn chuỗi lặp
    t = re.sub(r'([.!?…。！？]){3,}', r'\1\1', t)
    t = t.replace('\ufeff', '').replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    return t.strip()


async def _synthesize_async(text: str, out_path: Path, *, voice: str, rate: str,
                            pitch: str = '+0Hz', max_retries: int = 6) -> Path:
    try:
        import edge_tts
    except ImportError as e:
        raise RuntimeError(
            'Chưa cài edge-tts. Chạy: pip install edge-tts'
        ) from e

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    raw = (text or '').strip()
    text = sanitize_edge_text(raw)
    if not text:
        raise ValueError('text rỗng — không TTS được')

    from app.services.capcut_tts_engine import is_speakable_text, _make_silence_audio
    if not is_speakable_text(text):
        logger.info('Edge-TTS text không chứa ký tự phát âm (text=%r), tạo silence audio', text)
        return _make_silence_audio(out_path, duration_s=0.2)

    primary = normalize_voice(voice)
    # Nếu giọng UI chọn lỗi thì còn Hoài My để thử, tránh mất cả clip.
    voices_try = [primary]
    if primary != DEFAULT_VOICE:
        voices_try.append(DEFAULT_VOICE)

    if not _RATE_RE.match((rate or '').strip()):
        rate = '+0%'

    want_wav = out_path.suffix.lower() in {'.wav', '.wave'}
    mp3_path = out_path.with_suffix('.edge.mp3') if want_wav else out_path

    last_err = None
    # Kế hoạch thử: mỗi giọng thử đúng rate trước, rồi rate +0%, rồi bản text đã cắt punctuation rác.
    attempts_plan = []
    for v in voices_try:
        attempts_plan.append((v, rate, text))
        if rate != '+0%':
            attempts_plan.append((v, '+0%', text))

        short = re.sub(r'^[\W_]+|[\W_]+$', '', text, flags=re.UNICODE).strip()
        if not short:
            continue
        if not short != text:      # .pyc gốc so kiểu 'not a != b' (== a == b)
            continue
        attempts_plan.append((v, '+0%', short))

    for attempt in range(max_retries):
        v, r, t = attempts_plan[min(attempt, len(attempts_plan) - 1)]
        try:
            if mp3_path.exists():
                mp3_path.unlink(missing_ok=True)
            communicate = edge_tts.Communicate(t, v, rate=r, pitch=pitch)
            await communicate.save(str(mp3_path))
            if mp3_path.is_file() and mp3_path.stat().st_size < 100:
                raise RuntimeError(f'Edge-TTS file rỗng: {mp3_path}')
            if attempt > 0:
                logger.info(
                    'Edge-TTS OK sau retry %s · voice=%s rate=%s text=%.40s',
                    attempt + 1,
                    v,
                    r,
                    t)
            last_err = None
            break
        except Exception as e:
            last_err = e
            wait = min(8.0, 0.8 * 1.7 ** attempt)
            logger.warning(
                'Edge-TTS retry %s/%s voice=%s rate=%s: %s (sleep %.1fs) text=%.50s',
                attempt + 1,
                max_retries,
                v,
                r,
                e,
                wait,
                t)
            await asyncio.sleep(wait)

    if last_err is not None:
        raise RuntimeError(
            f'Edge-TTS thất bại sau {max_retries} lần (giọng {primary}): {last_err}'
            '. Thử lại sau vài giây hoặc đổi giọng Hoài My / kiểm tra mạng.'
        ) from last_err

    if want_wav:
        _mp3_to_wav(mp3_path, out_path)
        try:
            mp3_path.unlink(missing_ok=True)
        except Exception:
            pass
    return out_path


def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    ff = shutil.which('ffmpeg')
    if not ff:
        # Không có ffmpeg thì chịu, thà báo lỗi còn hơn im lặng trả file sai.
        raise RuntimeError('Cần ffmpeg để convert Edge-TTS mp3 → wav')

    cmd = [ff, '-y', '-i', str(mp3),
           '-ar', '44100', '-ac', '1',
           str(wav)]

    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    if p.returncode != 0 or not wav.exists():
        raise RuntimeError(f'ffmpeg convert TTS lỗi: {(p.stderr or "")[-400:]}')


def edge_tts_generate(text: str, out_path: str | Path, *,
                      voice: str = DEFAULT_VOICE,
                      rate: str | float | None = '+0%',
                      pitch: str = '+0Hz') -> Path:
    '''
    Sync API — tương thích AudioSyncEngine.tts_func(text, path) -> Path.

    out_path .wav → convert sau; .mp3 → giữ nguyên.
    '''
    out_path = Path(out_path)
    from app.services.capcut_tts_engine import is_speakable_text, _make_silence_audio
    if not is_speakable_text(text):
        logger.info('Edge-TTS text không chứa ký tự phát âm (text=%r), tạo silence audio', text)
        return _make_silence_audio(out_path, duration_s=0.2)

    if isinstance(rate, (int, float)) or (isinstance(rate, str)
                                          and rate.replace('.', '', 1).isdigit()):
        rate_str = speed_to_edge_rate(rate)
    else:
        rate_str = str(rate or '+0%')

    logger.info(
        'Edge-TTS: voice=%s rate=%s text=%.40s…',
        normalize_voice(voice),
        rate_str,
        text)

    return _run_coro(
        _synthesize_async(
            text,
            out_path,
            voice=normalize_voice(voice),
            rate=rate_str,
            pitch=pitch))


def make_tts_func(voice: str = DEFAULT_VOICE, speed: float | str = 1.0, *,
                  pitch: str = '+0Hz') -> Callable[[str, Path], Path]:
    '''Tạo hàm (text, path) -> Path gắn voice/speed từ UI.'''
    voice_n = normalize_voice(voice)
    rate = speed_to_edge_rate(speed)

    def _fn(text: str, out_path: Path) -> Path:
        return edge_tts_generate(text, out_path, voice=voice_n, rate=rate, pitch=pitch)

    return _fn


def edge_tts_available() -> bool:
    try:
        import edge_tts
        return True
    except ImportError:
        return False

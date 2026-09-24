'''On-demand, cached samples for the TTS voice picker.

Samples intentionally use the same provider functions as a render.  They are
created only after the user clicks preview, never in bulk when a voice catalog
loads (which would consume ElevenLabs quota or trigger CapCut rate limits).
'''
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

PREVIEW_TEXT = 'Xin chào các bạn. Đây là giọng đọc mẫu trong Winterboy studio.'
TTS_PREVIEW_CACHE_ROOT = Path.home() / '.winterboy' / 'tts_voice_preview'
BUNDLED_TTS_PREVIEW_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'tts_samples'

# Mẫu nghe thử phải đúng ngôn ngữ của giọng, không để giọng Trung đọc câu tiếng Việt.
VOICE_SAMPLE_TEXTS: dict[str, str] = {
    'vi': 'Xin chào các bạn. Đây là giọng đọc mẫu trong Winterboy studio.',
    'en': 'Hello! This is a voice preview in Winterboy studio.',
    'zh': '你好！这是 Winterboy studio 的语音预览。',
    'ja': 'こんにちは！これは Winterboy studio の音声プレビューです。',
    'ko': '안녕하세요! Winterboy studio 음성 미리보기입니다.',
    'es': '¡Hola! Esta es una vista previa de voz en Winterboy studio.',
    'fr': 'Bonjour ! Ceci est un aperçu vocal dans Winterboy studio.',
    'de': 'Hallo! Dies ist eine Sprachvorschau in Winterboy studio.',
    'th': 'สวัสดี! นี่คือตัวอย่างเสียงใน Winterboy studio',
    'pt': 'Olá! Esta é uma prévia de voz no Winterboy studio.',
    'id': 'Halo! Ini adalah pratinjau suara di Winterboy studio.',
    'ru': 'Здравствуйте! Это предварительный просмотр голоса в Winterboy studio.',
    'it': "Ciao! Questa è un'anteprima vocale in Winterboy studio.",
    'tr': "Merhaba! Bu Winterboy studio'daki bir ses önizlemesidir.",
    'ar': 'مرحباً! هذه معاينة صوتية في Winterboy studio.',
    'hi': 'नमस्ते! यह Winterboy studio में एक वॉयस पूर्वावलोकन है।'
}


def get_sample_text_for_voice(voice: str, default: str = PREVIEW_TEXT) -> str:
    '''Return language-appropriate sample text based on voice identifier.'''
    v = (voice or '').strip().lower()
    if 'multilingual' in v or 'tiếng việt' in v or 'tieng viet' in v:
        return VOICE_SAMPLE_TEXTS['vi']
    for lang, txt in VOICE_SAMPLE_TEXTS.items():
        # Bản đã phát hành chỉ ghép '(' + mã ngôn ngữ (thiếu ')') — giữ nguyên để
        # đúng hành vi build, dù đây rõ ràng là lỗi nhẹ trong nguồn gốc.
        if v.startswith(f'{lang}-') or f'({lang}' in v:
            return txt
    if any(k in v for k in ('english', 'us ', 'uk ', 'british', 'american',
                            'male 1', 'male 2', 'female 1', 'female 2',
                            'adam', 'rachel', 'antoni', 'bella', 'josh', 'elli',
                            'charlotte')):
        return VOICE_SAMPLE_TEXTS['en']
    if any(k in v for k in ('chinese', 'mandarin', 'cantonese')):
        return VOICE_SAMPLE_TEXTS['zh']
    if 'japanese' in v:
        return VOICE_SAMPLE_TEXTS['ja']
    if 'korean' in v:
        return VOICE_SAMPLE_TEXTS['ko']
    return default


@dataclass(frozen=True)
class TtsPreviewResult:
    path: Path
    cache_hit: bool
    bundled: bool = False


def normalize_eleven_model(model_id: str | None) -> str:
    '''Accept a user-friendly OptionMenu label while sending only its model ID.'''
    return (model_id or 'eleven_multilingual_v2').split('—', 1)[0].strip()


def _stable_voice_key(provider: str, voice: str) -> str:
    value = (voice or '').strip()
    if provider == 'Edge TTS':
        from app.services.edge_tts_engine import normalize_voice
        return normalize_voice(value)
    if provider == 'CapCut':
        if '|' in value:
            return value.rsplit('|', 1)[-1].strip()
        try:
            from app.services.capcut_tts_engine import list_capcut_voices
            for label, key in list_capcut_voices():
                if value == label or value == label.split('|')[0].strip():
                    return key
        except Exception:
            pass
        return value
    # Provider khác (ElevenLabs / VieNeu / ZeroTTS …): bỏ nhãn, giữ id sau dấu '|'
    return value.rsplit('|', 1)[-1].strip()


def _cache_path(*, provider: str, voice: str, speed: str | float, model_id: str, text: str) -> Path:
    stable_voice = _stable_voice_key(provider, voice)
    payload = json.dumps(
        {
            'version': 1,
            'provider': str(provider or '').strip(),
            'voice': stable_voice,
            'speed': str(speed or '1.0').strip(),
            'model': normalize_eleven_model(model_id),
            'text': text,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'))
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return TTS_PREVIEW_CACHE_ROOT / f'{digest}.mp3'


def bundled_sample_path(provider: str, voice: str) -> Path:
    '''Stable source-controlled sample path shared by UI and build script.'''
    provider_dir = {
        'CapCut': 'capcut',
        'Edge TTS': 'edge',
    }.get((provider or '').strip(), '')
    if not provider_dir:
        return Path()
    identity = f'{provider}|{_stable_voice_key(provider, voice)}'
    filename = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20] + '.mp3'
    return BUNDLED_TTS_PREVIEW_ROOT / provider_dir / filename


def is_tts_preview_cached(*, provider: str, voice: str,
                          speed: str | float = '1.0',
                          model_id: str = 'eleven_multilingual_v2',
                          text: str = PREVIEW_TEXT) -> Path | None:
    '''Return the cached sample Path if it already exists, else None.'''
    provider = (provider or 'Edge TTS').strip()
    voice = (voice or '').strip()
    text = (text or PREVIEW_TEXT).strip()
    if text == PREVIEW_TEXT:
        text = get_sample_text_for_voice(voice, default=PREVIEW_TEXT)
    if not voice or voice.startswith('Chưa tải giọng'):
        return None

    bundled = bundled_sample_path(provider, voice)
    if bundled and bundled.is_file() and bundled.stat().st_size >= 128:
        return bundled

    if provider == 'ElevenLabs':
        official_target = _cache_path(
            provider=provider,
            voice=voice,
            speed='official-preview',
            model_id='voice-preview',
            text='official-preview')
        if official_target.is_file() and official_target.stat().st_size >= 128:
            return official_target

    target = _cache_path(
        provider=provider,
        voice=voice,
        speed=speed,
        model_id=model_id,
        text=text)

    if target.is_file() and target.stat().st_size >= 128:
        return target

    if provider in {'VieNeu', 'VieNeu-TTS'}:
        clean_voice = (voice or '').rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
        candidates = [
            BUNDLED_TTS_PREVIEW_ROOT / 'vieneu' / f'{clean_voice}.wav',
            Path(__file__).resolve().parents[1] / 'assets' / 'tts_samples' / 'vieneu' / f'{clean_voice}.wav',
            Path(__file__).resolve().parents[2] / 'preview' / 'vieneu' / f'{clean_voice}.wav',
            Path.cwd() / 'preview' / 'vieneu' / f'{clean_voice}.wav',
        ]
        import sys
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass = Path(sys._MEIPASS)
            candidates.insert(0, meipass / 'preview' / 'vieneu' / f'{clean_voice}.wav')
            candidates.insert(1, meipass / 'app' / 'assets' / 'tts_samples' / 'vieneu' / f'{clean_voice}.wav')
        for cand in candidates:
            if cand.is_file() and cand.stat().st_size >= 102400:
                return cand

    if provider in {'ZeroTTS', 'ZeroTTS (AI Offline)', 'zerotts'}:
        try:
            from app.services.voice_engine.zerotts_engine import resolve_voice_name
            clean_voice = resolve_voice_name(voice)
        except Exception:
            clean_voice = (voice or '').rsplit('|', 1)[-1].strip()
        candidates = [
            BUNDLED_TTS_PREVIEW_ROOT / 'zerotts' / f'{clean_voice}.wav',
            Path(__file__).resolve().parents[1] / 'assets' / 'tts_samples' / 'zerotts' / f'{clean_voice}.wav',
            Path(__file__).resolve().parents[2] / 'preview' / 'zerotts' / f'{clean_voice}.wav',
            Path.cwd() / 'preview' / 'zerotts' / f'{clean_voice}.wav',
        ]
        import sys
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass = Path(sys._MEIPASS)
            candidates.insert(0, meipass / 'preview' / 'zerotts' / f'{clean_voice}.wav')
            candidates.insert(1, meipass / 'app' / 'assets' / 'tts_samples' / 'zerotts' / f'{clean_voice}.wav')
        for cand in candidates:
            if cand.is_file() and cand.stat().st_size >= 1000:
                return cand

    return None


def prewarm_tts_samples_async(provider: str | None = None,
                              voice: str | None = None) -> None:
    '''Quietly pre-generate and cache voice samples in background so clicking preview plays instantly.'''
    import threading

    def _worker():
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        except Exception:
            pass

        if provider and voice:
            try:
                generate_tts_preview(provider=provider, voice=voice)
            except Exception:
                pass
            return

        for v in ('vi-VN-HoaiMyNeural', 'vi-VN-NamMinhNeural'):
            try:
                generate_tts_preview(provider='Edge TTS', voice=v)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True, name='tts-prewarm').start()


def generate_tts_preview(*, provider: str, voice: str,
                         speed: str | float = '1.0',
                         model_id: str = 'eleven_multilingual_v2',
                         text: str = PREVIEW_TEXT) -> TtsPreviewResult:
    '''Create one short provider-accurate sample or return its local cache.'''
    provider = (provider or 'Edge TTS').strip()
    voice = (voice or '').strip()
    text = (text or PREVIEW_TEXT).strip()
    if text == PREVIEW_TEXT:
        text = get_sample_text_for_voice(voice, default=PREVIEW_TEXT)
    if not voice or voice.startswith('Chưa tải giọng'):
        raise ValueError('Hãy chọn một giọng hợp lệ trước khi nghe thử.')

    bundled = bundled_sample_path(provider, voice)
    if bundled and bundled.is_file() and bundled.stat().st_size >= 128:
        return TtsPreviewResult(bundled, cache_hit=True, bundled=True)

    if provider == 'ElevenLabs':
        official_target = _cache_path(
            provider=provider,
            voice=voice,
            speed='official-preview',
            model_id='voice-preview',
            text='official-preview')
        if official_target.is_file() and official_target.stat().st_size >= 128:
            return TtsPreviewResult(official_target, cache_hit=True)
        try:
            from app.services.cloud_voice import download_elevenlabs_voice_preview

            output = download_elevenlabs_voice_preview(voice, official_target)
            return TtsPreviewResult(Path(output), cache_hit=False)
        except ValueError:
            # Không có voice ID hợp lệ -> quay về đường sinh TTS chung bên dưới
            pass

    target = _cache_path(
        provider=provider,
        voice=voice,
        speed=speed,
        model_id=model_id,
        text=text)

    if target.is_file() and target.stat().st_size >= 128:
        return TtsPreviewResult(target, cache_hit=True)
    target.parent.mkdir(parents=True, exist_ok=True)

    if provider == 'Edge TTS':
        from app.services.edge_tts_engine import edge_tts_generate

        output = edge_tts_generate(text, target, voice=voice, rate=speed)
    elif provider == 'CapCut':
        from app.services.capcut_tts_engine import capcut_tts_generate

        output = capcut_tts_generate(text, target, voice=voice, speed=speed, timeout_s=90)
    elif provider == 'ElevenLabs':
        from app.services.cloud_voice import elevenlabs_tts_generate

        output = elevenlabs_tts_generate(
            text,
            target,
            voice_id=voice,
            speed=speed,
            model_id=normalize_eleven_model(model_id))
    elif provider == 'Google Cloud TTS':
        from app.services.cloud_voice import google_cloud_tts_generate

        output = google_cloud_tts_generate(text, target, voice_name=voice, speed=speed)
    elif provider in {'VieNeu-TTS', 'VieNeu'}:
        clean_voice = (voice or '').rsplit('|', 1)[-1].strip().replace('🧬 [Clone] ', '')
        preset_sample = Path.cwd() / 'preview' / 'vieneu' / f'{clean_voice}.wav'
        if preset_sample.is_file() and preset_sample.stat().st_size >= 102400:
            return TtsPreviewResult(preset_sample, cache_hit=True, bundled=True)
        from app.services.cloud_voice import vieneu_tts_generate

        output = vieneu_tts_generate(text, target, voice_name=clean_voice, temperature=0.7)
    elif provider in {'zerotts', 'ZeroTTS', 'ZeroTTS (AI Offline)'}:
        try:
            from app.services.voice_engine.zerotts_engine import resolve_voice_name

            clean_voice = resolve_voice_name(voice)
        except Exception:
            clean_voice = (voice or '').rsplit('|', 1)[-1].strip()
        bundled_zero = BUNDLED_TTS_PREVIEW_ROOT / 'zerotts' / f'{clean_voice}.wav'
        if bundled_zero.is_file() and bundled_zero.stat().st_size >= 1000:
            return TtsPreviewResult(bundled_zero, cache_hit=True, bundled=True)
        preset_sample = Path.cwd() / 'preview' / 'zerotts' / f'{clean_voice}.wav'
        if preset_sample.is_file() and preset_sample.stat().st_size >= 1000:
            return TtsPreviewResult(preset_sample, cache_hit=True, bundled=True)
        from app.services.cloud_voice import download_zerotts_voice_preview

        output = download_zerotts_voice_preview(clean_voice, target)
    else:
        raise ValueError(f'Nhà cung cấp TTS không hỗ trợ nghe thử: {provider}')

    output = Path(output)
    if not output.is_file() or output.stat().st_size < 128:
        raise RuntimeError('TTS không tạo được file nghe thử hợp lệ.')
    return TtsPreviewResult(output, cache_hit=False)

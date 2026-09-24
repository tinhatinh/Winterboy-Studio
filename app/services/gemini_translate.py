'''
Dịch SRT bằng LLM — hai chế độ:

  - reflow=True  (mặc định): AI tái cấu trúc timeline, được gộp/tách cue
    (dùng cho SRT STT bị vỡ; prompt REFLOW_SYSTEM).
  - reflow=False: giữ đúng N dòng, chỉ dịch text, copy timestamp cũ.

Providers:
  - Gemini (Google AI Studio) — mặc định gemini-2.5-flash
  - Groq — OpenAI-compatible API, mặc định llama-3.3-70b-versatile
  - OpenAI — gpt-4o-mini
  - DeepSeek — deepseek-chat

Env keys (theo thứ tự):
  Gemini: AUTO_RENDER_GEMINI_API_KEY, WINTERBOY_GEMINI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY
  OpenAI: AUTO_RENDER_OPENAI_API_KEY, OPENAI_API_KEY
  DeepSeek: AUTO_RENDER_DEEPSEEK_API_KEY, DEEPSEEK_API_KEY

Dùng REST (không bắt buộc SDK).
'''
from __future__ import annotations
import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.services.manual_translate import looks_untranslated
from app.services.srt_utils import SrtCue, load_srt, write_srt
from app.services.translation_memory import apply_glossary, load_glossary, load_translation_memory, memory_key, save_translation_memory

logger = logging.getLogger('app.services.translation_engine')

DEFAULT_MODEL = 'gemini-3.5-flash'
GEMINI_MODELS = [
    'gemini-3.8-flash',
    'gemini-3.7-flash',
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-3-flash-preview',
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-flash-latest',
    'gemini-flash-lite-latest',
    'gemini-1.5-flash']

# Model đã hết quota trong phiên chạy hiện tại — chỉ đổi khi user đổi key.
_EXHAUSTED_MODELS: set[str] = set()
# (engine, model) mà provider đã khai tử — xem clear_exhausted_models().
_DECOMMISSIONED_MODELS: set[tuple[str, str]] = set()
# (engine, key fingerprint) -> model dùng được gần nhất.
_LAST_WORKING_MODEL: dict[tuple[str, str], str] = {}
# Vị trí key kế tiếp nên thử cho (engine, model); nhiều key thì xoay đều.
_KEY_ROTATION_CURSOR: dict[tuple[str, str], int] = {}
# (engine, model, fingerprint key) -> thời điểm được thử lại.
_KEY_COOLDOWN_UNTIL: dict[tuple[str, str, str], float] = {}


def clear_exhausted_models() -> None:
    '''Xóa danh sách các model bị khóa quota (gọi khi đổi key hoặc mở app).'''
    _EXHAUSTED_MODELS.clear()
    _DECOMMISSIONED_MODELS.clear()
    _LAST_WORKING_MODEL.clear()
    _KEY_ROTATION_CURSOR.clear()
    _KEY_COOLDOWN_UNTIL.clear()


def _key_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]


def _key_cooldown_seconds(error: BaseException | str) -> float:
    '''Cooldown đủ để tránh gọi lại key lỗi ở ngay batch kế tiếp.'''
    text = str(error).casefold()
    if any(mark in text for mark in ('401', '403', 'invalid_api_key', 'authentication')):
        return 3600.0
    if 'quota' in text and 'rate' not in text:
        return 900.0
    return 90.0


ENGINE_MODELS = {
    'Gemini': GEMINI_MODELS,
    'Groq': [
        'openai/gpt-oss-120b',
        'openai/gpt-oss-20b',
        'groq/compound',
        'qwen/qwen3.6-27b',
        'llama-3.1-8b-instant'],
    'OpenAI': [
        'gpt-4o-mini',
        'gpt-4o',
        'o3-mini',
        'o1-mini',
        'gpt-4.5-preview',
        'gpt-3.5-turbo'],
    'DeepSeek': ['deepseek-chat', 'deepseek-reasoner']}

PROVIDER_DEFAULTS = {
    'Gemini': 'gemini-3.5-flash',
    'Groq': 'openai/gpt-oss-120b',
    'OpenAI': 'gpt-4o-mini',
    'DeepSeek': 'deepseek-chat'}

PROVIDER_ENV = {
    'Gemini': ('AUTO_RENDER_GEMINI_API_KEY', 'WINTERBOY_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'),
    'Groq': ('AUTO_RENDER_GROQ_API_KEY', 'GROQ_API_KEY'),
    'OpenAI': ('AUTO_RENDER_OPENAI_API_KEY', 'OPENAI_API_KEY'),
    'DeepSeek': ('AUTO_RENDER_DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY')}


def _provider_name(engine: str | None) -> str:
    selected = (engine or '').strip()
    if selected in PROVIDER_DEFAULTS:
        return selected
    raise ValueError(
        f'Engine dịch không hỗ trợ: {selected or "(trống)"}. Chọn một trong: '
        f'{", ".join(PROVIDER_DEFAULTS)}.')


def _split_api_keys(value: str | None) -> list[str]:
    '''Return unique API keys entered one per line, preserving their order.'''
    seen = set()
    keys = []
    for raw in (value or '').splitlines():
        key = raw.strip()
        if not key:
            continue
        if key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def get_translation_api_keys(engine: str = 'Gemini') -> list[str]:
    '''Read the configured key list for one translation provider.

    Environment variables retain their previous priority.  A value may now
    contain several keys separated by newlines; the saved key file follows the
    same format for the Settings multi-line editor.
    '''
    engine = _provider_name(engine)
    for key_name in PROVIDER_ENV[engine]:
        values = _split_api_keys(os.environ.get(key_name))
        if not values:
            continue
        return values
    key_file = Path.home() / '.winterboy' / f'{engine.lower()}_api_key.txt'
    if key_file.is_file():
        try:
            values = _split_api_keys(key_file.read_text(encoding='utf-8'))
        except OSError:
            values = []
        if values:
            return values
    return []


def get_translation_api_key(engine: str = 'Gemini') -> str | None:
    '''Compatibility helper returning the configured keys as newline text.'''
    keys = get_translation_api_keys(engine)
    return '\n'.join(keys) or None


def set_translation_api_key(engine: str, key: str, *, persist: bool = True) -> None:
    engine = _provider_name(engine)
    value = '\n'.join(_split_api_keys(key))
    os.environ[PROVIDER_ENV[engine][0]] = value
    clear_exhausted_models()
    if persist:
        path = Path.home() / '.winterboy' / f'{engine.lower()}_api_key.txt'
        path.parent.mkdir(parents=True, exist_ok=True)
        if value:
            path.write_text(value, encoding='utf-8')
            return None
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                return None
            return None
        return None
    return None


def get_gemini_api_key() -> str | None:
    return get_translation_api_key('Gemini')


def set_gemini_api_key(key: str, *, persist: bool = True) -> None:
    set_translation_api_key('Gemini', key, persist=persist)


def normalize_gemini_model(model: str | None) -> str:
    m = (model or '').strip() or DEFAULT_MODEL
    # Người dùng gõ tắt trong ô Model; map hết về id thật của API.
    aliases = {
        '3.8 flash': 'gemini-3.8-flash',
        '3.8-flash': 'gemini-3.8-flash',
        'flash 3.8': 'gemini-3.8-flash',
        '3.7 flash': 'gemini-3.7-flash',
        '3.7-flash': 'gemini-3.7-flash',
        'flash 3.7': 'gemini-3.7-flash',
        '3.6 flash': 'gemini-3.6-flash',
        '3.6-flash': 'gemini-3.6-flash',
        'flash 3.6': 'gemini-3.6-flash',
        '3.5 flash': 'gemini-3.5-flash',
        '3.5-flash': 'gemini-3.5-flash',
        'flash 3.5': 'gemini-3.5-flash',
        '3.5 flash-lite': 'gemini-3.5-flash-lite',
        '3.5-flash-lite': 'gemini-3.5-flash-lite',
        '3.5 flash lite': 'gemini-3.5-flash-lite',
        'flash lite 3.5': 'gemini-3.5-flash-lite',
        'flash-lite 3.5': 'gemini-3.5-flash-lite',
        '3.1 flash-lite': 'gemini-3.1-flash-lite',
        '3.1-flash-lite': 'gemini-3.1-flash-lite',
        '3.1 flash lite': 'gemini-3.1-flash-lite',
        'flash lite 3.1': 'gemini-3.1-flash-lite',
        'flash-lite 3.1': 'gemini-3.1-flash-lite',
        '3 flash': 'gemini-3-flash-preview',
        '3-flash': 'gemini-3-flash-preview',
        'flash 3': 'gemini-3-flash-preview',
        '3.1 pro': 'gemini-3.1-pro-preview',
        '3.1-pro': 'gemini-3.1-pro-preview',

        '2.5 flash': 'gemini-2.5-flash',
        '2.5-flash': 'gemini-2.5-flash',
        'flash 2.5': 'gemini-2.5-flash',
        '2.5 pro': 'gemini-2.5-pro',
        '2.5-pro': 'gemini-2.5-pro',
        'pro 2.5': 'gemini-2.5-pro',

        'flash': 'gemini-flash-latest',
        'flash-latest': 'gemini-flash-latest',
        'flash latest': 'gemini-flash-latest',
        'gemini-flash': 'gemini-flash-latest',
        'gemini flash': 'gemini-flash-latest',
        'flash-lite-latest': 'gemini-flash-lite-latest',
        'flash lite latest': 'gemini-flash-lite-latest',
        'gemini-flash-lite': 'gemini-flash-lite-latest',

        '2.5 flash-lite': 'gemini-3.5-flash-lite',
        '2.5-flash-lite': 'gemini-3.5-flash-lite',
        '2.5 flash lite': 'gemini-3.5-flash-lite',
        'gemini-2.5-flash-lite': 'gemini-3.5-flash-lite',
        '2.0 flash': 'gemini-3.5-flash',
        '2.0-flash': 'gemini-3.5-flash',
        'flash 2.0': 'gemini-3.5-flash',
        'gemini-2.0-flash': 'gemini-3.5-flash',
        '2.0 flash-lite': 'gemini-3.5-flash-lite',
        '2.0-flash-lite': 'gemini-3.5-flash-lite',
        'gemini-2.0-flash-lite': 'gemini-3.5-flash-lite',
        '1.5 flash': 'gemini-1.5-flash',
        '1.5-flash': 'gemini-1.5-flash',
        'flash 1.5': 'gemini-1.5-flash'}
    key = m.casefold()
    if key in aliases:
        return aliases[key]
    if m in GEMINI_MODELS:
        return m
    if any(m.startswith(p) for p in ('gemini-3', 'gemini-2.5', 'gemini-flash', 'gemini-1.5', 'gemini-pro')):
        return m
    return DEFAULT_MODEL


def resolve_translation_model(engine: str, model: str | None) -> str:
    '''Chọn đúng model của provider; tuyệt đối không fallback chéo provider.'''
    engine = _provider_name(engine)
    raw = (model or '').strip()
    if not raw:
        return PROVIDER_DEFAULTS[engine]

    if engine == 'Gemini':
        selected = normalize_gemini_model(raw)
        return selected

    if engine == 'Groq':
        # Groq đã bỏ nhiều id cũ; map thẳng sang model còn sống để user không phải sửa.
        groq_deprecated = {
            'llama3-70b-8192': 'openai/gpt-oss-120b',
            'llama-3-70b-8192': 'openai/gpt-oss-120b',
            'llama3-8b-8192': 'openai/gpt-oss-20b',
            'llama-3-8b-8192': 'openai/gpt-oss-20b',
            'llama-3.3-70b-versatile': 'openai/gpt-oss-120b',
            'mixtral-8x7b-32768': 'groq/compound'}
        if raw in groq_deprecated:
            migrated = groq_deprecated[raw]
            logger.info('Model Groq %r đã bị khai tử; tự động chuyển sang %s', raw, migrated)
            return migrated
    if raw not in ENGINE_MODELS[engine]:
        logger.info('Dùng model %r cho engine %s (ngoài danh mục mặc định).', raw, engine)
    return raw


@dataclass
class TranslateResult:
    ok: bool
    srt_path: Path | None
    n_lines: int = 0
    message: str = ''
    model: str = ''
    completed_lines: int = 0
    remaining_lines: int = 0
    progress_path: Path | None = None
    log_path: Path | None = None
    quality_report: dict[str, Any] | None = None


SYSTEM = 'Bạn là chuyên gia biên dịch phụ đề chuyên nghiệp, hỗ trợ dịch chuẩn xác mọi cặp ngôn ngữ.\nQUY TẮC BẮT BUỘC:\n1. Input là đúng N dòng đánh số 1..N.\n2. Output PHẢI đúng N dòng, mỗi dòng một bản dịch, GIỮ NGUYÊN số thứ tự.\n3. KHÔNG gộp 2 dòng thành 1. KHÔNG tách 1 dòng thành 2.\n4. Giữ timestamp không đổi (bạn chỉ dịch text).\n5. Văn phong tự nhiên, đúng ngữ cảnh (phim ảnh, vlog, đời sống, khoa học...). Tên riêng giữ nhất quán.\n6. Nếu đích là Tiếng Việt: dịch câu tự nhiên, thoát ý, không để sót từ ngữ của tiếng nguồn.\n7. Chỉ trả về các dòng dạng: 1|bản dịch\n   Không markdown, không giải thích.\n'

REFLOW_SYSTEM = 'Bạn là một chuyên gia Dịch thuật và Biên tập Phụ đề (Subtitle Editor) hàng đầu thế giới.\nNhiệm vụ của bạn là dịch file SRT sang ngôn ngữ đích được yêu cầu, đồng thời CHUẨN HÓA LẠI CẤU TRÚC TIMELINE.\n\nTình trạng file đầu vào:\nFile SRT này được tạo ra từ phần mềm Speech-to-Text (STT) tự động, nên các câu thoại thường bị cắt vụn lộn xộn, sai ngữ pháp (ví dụ: một từ hoặc một câu bị bẻ đôi ra làm 2 block thời gian khác nhau). Nếu là chữ Hán, đôi khi bị chèn khoảng trắng giữa từng ký tự — hãy tự nối lại khi đọc.\n\nYêu cầu thực thi:\n1. Đọc và hiểu toàn bộ ngữ cảnh liền mạch của các dòng SRT đầu vào trước khi dịch. KHÔNG dịch máy móc từng dòng một.\n2. Dịch sang ngôn ngữ đích tự nhiên, đúng văn phong thực tế (vlog, phim ảnh, đời sống, tài liệu...). Tên riêng nhất quán; không bịa thêm thoại.\n   - Nếu đích là Tiếng Việt: dịch thoát ý, tự nhiên, mượt mà, đầy đủ thanh điệu và dấu câu.\n   - Nếu nguồn là tiếng Trung: dịch âm Hán Việt phù hợp bối cảnh, tuyệt đối không để sót chữ Hán.\n   - Nếu nguồn là tiếng Anh / ngôn ngữ phương Tây: dịch trôi chảy, đúng thành ngữ/ngữ cảnh, không dịch thô word-by-word.\n   - Nếu nguồn là tiếng Nhật / Hàn: xưng hô tự nhiên theo ngữ cảnh nhân vật, phiên âm tên chuẩn.\n3. GỘP DÒNG THÔNG MINH (Quan trọng nhất):\n   - Nếu bạn phát hiện các block SRT liên tiếp nhau đang tạo thành một câu hoàn chỉnh, BẮT BUỘC phải gộp chúng lại thành 1 block SRT duy nhất.\n   - Khi gộp, Thời gian Bắt đầu (Start Time) là thời gian của block đầu tiên, và Thời gian Kết thúc (End Time) là thời gian của block cuối cùng trong nhóm được gộp.\n   - Đảm bảo mỗi block SRT đầu ra phải là một câu (hoặc một cụm từ) hoàn chỉnh về mặt ý nghĩa, tuyệt đối không bị đứt đoạn vô lý giữa từ/cụm từ.\n   - Ưu tiên phụ đề dễ đọc (khoảng 1–2 dòng/câu), không nhồi cả đoạn dài vào một cue quá ngắn.\n4. Giữ nguyên chuẩn định dạng SRT:\n   Số thứ tự\n   HH:MM:SS,mmm --> HH:MM:SS,mmm\n   Text\n   (một dòng trống giữa các block). Timestamp chỉ lấy từ phạm vi đầu vào — không tạo mốc ngoài video.\n5. Chỉ trả về nội dung file SRT, không giải thích gì thêm. Không Markdown, không code fence.\n'

_SRT_BLOCK_RE = re.compile(
    '(?ms)^\\s*(?:\\d+\\s*\\n)?\\s*(\\d{2}:\\d{2}:\\d{2}[,.]\\d{3})\\s*-->\\s*(\\d{2}:\\d{2}:\\d{2}[,.]\\d{3})\\s*\\n(.*?)(?=\\n\\s*\\n|\\Z)')


def _cues_as_srt(cues: list[SrtCue]) -> str:
    """Serialize cues for the LLM without touching the user's original SRT."""
    def ts(seconds: float) -> str:
        total = int(round(max(0.0, seconds) * 1000))
        hours, total = divmod(total, 3600000)
        minutes, total = divmod(total, 60000)
        seconds_i, millis = divmod(total, 1000)
        return f'{hours:02d}:{minutes:02d}:{seconds_i:02d},{millis:03d}'

    return '\n\n'.join(
        f'{i + 1}\n{ts(c.start_s)} --> {ts(c.end_s)}\n{c.text.strip()}'
        for i, c in enumerate(cues) if c.text.strip())


def _strip_code_fence(text: str) -> str:
    text = (text or '').strip()
    text = re.sub('^```(?:srt|text|plaintext)?\\s*', '', text, flags=re.IGNORECASE)
    return re.sub('\\s*```$', '', text).strip()


def _clean_cue_text(text: str) -> str:
    """Loại bỏ triệt để các tiền tố số thứ tự và ký tự phân cách thừa (ví dụ '1|', '1. 1|', '1: ', '- 1|')."""
    s = (text or '').strip()
    while True:
        cleaned = re.sub('^(?:[-*•]\\s*)?\\d+\\s*[|.:)\\-]\\s*', '', s).strip()
        if cleaned == s:
            break
        s = cleaned
    return s


def _parse_reflow_srt(raw: str, *, source_count: int) -> list[SrtCue]:
    '''Parse LLM SRT defensively and reject partial/non-SRT prose.'''
    parsed = []
    for match in _SRT_BLOCK_RE.finditer(_strip_code_fence(raw)):
        def parse(value: str) -> float:
            (h, m, tail) = value.replace('.', ',').split(':')
            (s, ms) = tail.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        start, end = parse(match.group(1)), parse(match.group(2))
        text = _clean_cue_text(re.sub('\\s+', ' ', match.group(3)).strip())
        if not text:
            continue
        if not end > start:
            continue
        parsed.append(SrtCue(len(parsed) + 1, start, end, text))
    minimum = max(1, source_count // 16)
    if len(parsed) < minimum:
        raise RuntimeError(f'AI trả SRT thiếu ({len(parsed)}/{source_count} block hợp lệ).')
    if len(parsed) > source_count * 2:
        raise RuntimeError('AI trả quá nhiều block SRT, không dùng kết quả không an toàn.')

    stray = _monotonic_outliers(parsed)
    previous_end = 0.0
    normalized = []
    for i, cue in enumerate(parsed):
        if i in stray:
            normalized.append(SrtCue(len(normalized) + 1, cue.start_s, cue.end_s, cue.text))
            continue
        start = max(cue.start_s, previous_end)
        if cue.end_s - start < 0.2:
            continue
        normalized.append(SrtCue(len(normalized) + 1, start, cue.end_s, cue.text))
        previous_end = cue.end_s
    if not normalized:
        raise RuntimeError('AI trả SRT không có timeline hợp lệ.')
    return normalized


def _is_quota_error(exc: BaseException) -> bool:
    '''Lỗi hết quota / bị chặn rate — thử tiếp chỉ làm nặng thêm.'''
    text = str(exc).casefold()
    markers = (
        '429', 'quota', 'resource_exhausted', 'resourceexhausted',
        'rate limit', 'rate-limit', 'too many requests')
    return any(marker in text for marker in markers)


class ReflowDensityError(RuntimeError):
    '''Cue vượt ngưỡng chữ/giây — bản dịch vẫn phủ đủ timeline.

    Tách khỏi lỗi phủ timeline vì hai loại này cần cách xử lý khác nhau: thiếu
    timeline là câu trả lời hỏng, còn quá dày chỉ là câu nguồn dài hơn chỗ
    trống.  Chế độ natural giao trường hợp sau cho AudioSync bù nhịp.
    '''


def _monotonic_outliers(cues: Sequence[SrtCue]) -> set[int]:
    '''Chỉ số các cue phá vỡ mạch thời gian chung của file.

    Whisper thỉnh thoảng chèn một dòng có timestamp nhảy hẳn ra ngoài mạch
    (thực tế gặp: cue 1 ghi 00:02:00 trong khi cue 2 bắt đầu ở 00:00:01).  Chỉ
    một cue như vậy cũng đủ kéo min/max ra sai, khiến mọi bản dịch đều bị coi
    là "chưa phủ hết timeline".

    Lấy dãy con không giảm dài nhất theo start_s làm mạch chuẩn; cue nằm ngoài
    dãy đó là lệch.  Chỉ dùng khi TÍNH khoảng timeline — nội dung cue vẫn được
    dịch và giữ nguyên vị trí.
    '''
    if len(cues) < 3:
        return set()
    tails = []
    tail_at = []
    parent = [-1] * len(cues)
    for i, cue in enumerate(cues):
        pos = bisect_right(tails, cue.start_s)
        if pos:
            parent[i] = tail_at[pos - 1]
        if pos == len(tails):
            tails.append(cue.start_s)
            tail_at.append(i)
            continue
        tails[pos] = cue.start_s
        tail_at[pos] = i
    keep = set()
    node = tail_at[-1] if tail_at else -1
    while node >= 0:
        keep.add(node)
        node = parent[node]
    return set(range(len(cues))) - keep


def _timeline_window(cues: Sequence[SrtCue]) -> tuple[float, float, int]:
    '''(bắt_đầu, kết_thúc, số_cue_lệch) — bỏ qua cue lệch mạch khi đo.'''
    if not cues:
        return (0.0, 0.0, 0)
    outliers = _monotonic_outliers(cues)
    usable = [c for i, c in enumerate(cues) if i not in outliers] or list(cues)
    return (
        min(c.start_s for c in usable),
        max(c.end_s for c in usable),
        len(outliers))


def _validate_reflow_coverage(cues: list[SrtCue], source_cues: list[SrtCue], *,
                              natural_voice: bool = False) -> None:
    '''Reject valid-looking but incomplete or unreadably dense LLM SRT.'''
    if not source_cues:
        return None
    (source_start, source_end, stray) = _timeline_window(source_cues)
    if stray:
        logger.warning(
            'SRT nguồn có %d cue lệch thứ tự thời gian; đã bỏ qua khi đo timeline (khoảng dùng để kiểm tra: %.1f-%.1fs)',
            stray, source_start, source_end)
    (result_start, result_end, _) = _timeline_window(cues)
    if source_end - source_start > 4.0:
        slack = 1.5
        if result_start < source_start - slack or result_end > source_end + slack:
            raise RuntimeError('AI tạo timestamp nằm ngoài timeline nguồn; sẽ yêu cầu AI làm lại.')
        if result_start > source_start + slack or result_end < source_end - slack:
            raise RuntimeError('AI trả SRT chưa phủ hết timeline nguồn; sẽ yêu cầu AI làm lại.')
    for cue in cues:
        chars = len(re.sub('\\s+', '', cue.text))
        if cue.duration_s > 7.5:
            raise RuntimeError('AI tạo cue quá dài; sẽ yêu cầu AI chia lại subtitle.')
        if chars / cue.duration_s > 18.5:
            raise ReflowDensityError(
                'AI tạo cue quá dày chữ so với thời lượng; sẽ yêu cầu AI chia/gọn lại.')
        if natural_voice and (cue.duration_s < 0.5 or chars / cue.duration_s > 13.0):
            logger.warning(
                'Natural voice cue needs attention: %.2fs, %.1f chars/s',
                cue.duration_s,
                chars / cue.duration_s)
    return None


def _repair_reflow_batch_edges(cues: list[SrtCue], source_cues: list[SrtCue]) -> list[SrtCue]:
    """Correct small first/last timestamp drift from an otherwise valid LLM SRT.

    Gemini commonly translates every sentence but starts/ends a batch a few
    seconds inside its source window.  Retrying burns quota without improving
    the wording.  We may safely extend only the first/last output cue when the
    drift is modest; a large gap is still rejected by the coverage validator.
    """
    if not cues or not source_cues:
        return cues
    (source_start, source_end, _) = _timeline_window(source_cues)

    stray = _monotonic_outliers(cues)
    inside = [i for i in range(len(cues)) if i not in stray]
    if not inside:
        return cues
    head, tail = inside[0], inside[-1]
    first_gap = cues[head].start_s - source_start
    last_gap = source_end - cues[tail].end_s

    repair_limit = 5.0
    if first_gap > 1.5 and first_gap <= repair_limit:
        first = cues[head]
        cues = [*cues[:head], SrtCue(first.index, source_start, first.end_s, first.text),
                *cues[head + 1:]]
        logger.info('Reflow batch edge repair: extended first cue by %.2fs', first_gap)
    if last_gap > 1.5 and last_gap <= repair_limit:
        last = cues[tail]
        cues = [*cues[:tail], SrtCue(last.index, last.start_s, source_end, last.text),
                *cues[tail + 1:]]
        logger.info('Reflow batch edge repair: extended last cue by %.2fs', last_gap)
    return cues


def _reflow_batches(cues: list[SrtCue], *, limit: int = 12) -> list[list[SrtCue]]:
    '''Split long jobs only at a likely sentence end, never inside a cue.'''
    batches = []
    start = 0
    while start < len(cues):
        end = min(len(cues), start + limit)
        if end < len(cues):
            lower = max(start + 6, end - 10)
            for index in range(end - 1, lower - 1, -1):
                tail = re.sub('\\s+', '', cues[index].text)
                if not tail.endswith(('。', '！', '？', '!', '?', '…')):
                    continue
                end = index + 1
                break
        batches.append(cues[start:end])
        start = end
    return batches


def _request_reflow_batch(cues: list[SrtCue], *, api_key: str, model: str | None,
                          engine: str,
                          source_lang: str,
                          target_lang: str,
                          batch_index: int,
                          batch_total: int,
                          natural_voice: bool = False,
                          cancel_check: Callable[[], bool] | None = None) -> list[SrtCue]:
    from app.services.language_detector import get_pair_translation_prompt, normalize_lang_name
    src_clean = normalize_lang_name(source_lang)
    tgt_clean = normalize_lang_name(target_lang)
    source_instruction = (
        f'Ngôn ngữ nguồn là {src_clean}.'
        if src_clean != 'Tự nhận diện'
        else 'Tự nhận diện ngôn ngữ nguồn từ ngữ cảnh phụ đề.')
    guidance = get_pair_translation_prompt(src_clean, tgt_clean)
    user = (
        f'{source_instruction} Dịch sang {tgt_clean}. Đây là phần {batch_index}/{batch_total} liền mạch của một SRT dài; không bịa text trước/sau phần này. Gộp các block STT bị cắt vụn thành câu hoàn chỉnh (start = block đầu, end = block cuối), rồi chỉ trả về SRT mới.\n\nYÊU CẦU DỊCH THUẬT:\n'
        f'{guidance}\n\n'
        f'{_cues_as_srt(cues)}')
    constraints = (
        '\nBắt buộc: phủ trọn timeline của phần này từ cue đầu tới cue cuối; mỗi cue tối đa 7 giây, tối đa khoảng 18 ký tự/giây. Nếu câu dài, chia ở cụm từ tự nhiên hoặc viết gọn.')
    if natural_voice:
        constraints += (
            '\nCHẾ ĐỘ ĐỒNG BỘ VOICE TỰ NHIÊN: ưu tiên gộp các cue STT liên tiếp bị cắt vụn thành câu hoàn chỉnh; mỗi cue tối thiểu 0.5 giây và tối đa 13 ký tự không tính khoảng trắng/giây. Dịch sang tiếng Việt tự nhiên nhưng cô đọng theo thời lượng, giữ ý quan trọng thay vì dịch từng chữ. Chỉ kéo dài một cue vào khoảng lặng có sẵn, tuyệt đối không chồng timestamp giữa các cue.')

    last_error = None

    dense_fallback = None

    max_attempts = 2 if natural_voice else 3
    for attempt in range(max_attempts):
        if cancel_check and cancel_check():
            raise InterruptedError('Đã dừng dịch theo yêu cầu.')
        retry = ''
        if attempt == 1:
            retry = '\nKết quả trước bị từ chối vì chưa phủ hết timeline. BẮT BUỘC: cue đầu start ≈ timestamp đầu nguồn, cue cuối end ≈ timestamp cuối nguồn. Trả TOÀN BỘ phần SRT, không bỏ dở, không tóm tắt.'
        elif attempt >= 2:
            retry = '\nLần trước vẫn thiếu timeline. Giữ gần số block nguồn nếu cần, ưu tiên phủ đủ từ đầu đến cuối phần này. Chỉ trả SRT thuần.'
        raw = _call_provider(engine, api_key, REFLOW_SYSTEM, user + constraints + retry,
                             model=model, cancel_check=cancel_check)
        try:
            result = _parse_reflow_srt(raw, source_count=len(cues))
            if natural_voice:
                result = _repair_reflow_batch_edges(result, cues)
            _validate_reflow_coverage(result, cues, natural_voice=natural_voice)
            return result
        except ReflowDensityError as exc:
            last_error = exc
            if natural_voice and dense_fallback is None:
                dense_fallback = result
                logger.info(
                    'reflow batch %s/%s: nhận kết quả dày chữ ngay, bỏ lần thử %s (thử lại không nhắm vào mật độ nên vô ích)',
                    batch_index, batch_total, attempt + 2)
                break
            logger.info('reflow batch %s/%s attempt %s dense: %s', batch_index, batch_total, attempt + 1, exc)
        except RuntimeError as exc:
            last_error = exc
            logger.info('reflow batch %s/%s attempt %s fail: %s', batch_index, batch_total, attempt + 1, exc)

    if dense_fallback is not None:
        over = sum(
            1 for cue in dense_fallback
            if len(re.sub('\\s+', '', cue.text)) / cue.duration_s > 18.5)
        logger.warning(
            'Reflow batch %s/%s: giữ bản dịch phủ đủ timeline, giao %d/%d cue dày cho AudioSync bù nhịp (mượn khoảng lặng, tối đa 1.35×)',
            batch_index, batch_total, over, len(dense_fallback))
        return dense_fallback
    raise RuntimeError(str(last_error or 'AI không trả SRT hợp lệ.'))


def translate_cues_reflow(cues: list[SrtCue], *, api_key: str, model: str | None,
                          engine: str, source_lang: str, target_lang: str,
                          natural_voice: bool = False,
                          report: dict | None = None,
                          on_checkpoint: Callable[[list[SrtCue], int, int], None] | None = None,
                          cancel_check: Callable[[], bool] | None = None) -> list[SrtCue]:
    '''Repair semantic boundaries; batch long files to prevent truncated output.

    report: nếu truyền vào thì được ghi thêm khóa "degraded"/"batches" để nơi
    gọi báo cho người dùng biết có phần nào phải hạ xuống dịch 1:1 hay không.
    '''
    engine = _provider_name(engine)
    selected = resolve_translation_model(engine, model)
    batches = _reflow_batches(cues, limit=20 if natural_voice else 12)
    out = []
    previous_end = 0.0
    degraded = 0
    consumed_source = 0
    for index, batch in enumerate(batches, start=1):
        if cancel_check and cancel_check():
            logger.info('translate_cues_reflow: cancelled by user before batch %d', index)
            break
        try:
            repaired = _request_reflow_batch(
                batch, api_key=api_key, model=selected, engine=engine,
                source_lang=source_lang, target_lang=target_lang,
                batch_index=index, batch_total=len(batches),
                natural_voice=natural_voice, cancel_check=cancel_check)
        except InterruptedError:
            logger.info('translate_cues_reflow: cancelled by user during batch %d', index)
            break
        except RuntimeError as exc:
            if cancel_check and cancel_check():
                break
            if _is_quota_error(exc):
                raise RuntimeError(
                    f'{exc}\n(Đã chuẩn hóa xong {index - 1}/{len(batches)} phần trước khi hết quota.)'
                ) from exc
            logger.warning(
                'Reflow lô %s/%s hỏng (%s) — chuyển lô này sang dịch 1:1 để không mất cả bản render',
                index, len(batches), exc)
            repaired = translate_cues(
                batch, api_key=api_key, model=selected, engine=engine,
                source_lang=source_lang, target_lang=target_lang,
                repair_residual=False,
                cancel_check=cancel_check)
            degraded += 1

        stray = _monotonic_outliers(repaired)
        for i, cue in enumerate(repaired):
            if i in stray:
                out.append(SrtCue(len(out) + 1, cue.start_s, cue.end_s, cue.text))
                continue
            start = max(cue.start_s, previous_end)
            if not cue.end_s - start >= 0.2:
                continue
            out.append(SrtCue(len(out) + 1, start, cue.end_s, cue.text))
            previous_end = cue.end_s
        consumed_source += len(batch)
        if on_checkpoint:
            on_checkpoint(list(out), consumed_source, len(cues))

    try:
        _validate_reflow_coverage(out, cues, natural_voice=natural_voice)
    except ReflowDensityError:
        if not natural_voice:
            raise
        over = sum(
            1 for cue in out
            if len(re.sub('\\s+', '', cue.text)) / cue.duration_s > 18.5)
        logger.warning(
            'Natural voice: %d/%d cue vượt 18.5 ký tự/giây — AudioSync sẽ bù nhịp',
            over, len(out))

    if report is not None:
        report['degraded'] = degraded
        report['batches'] = len(batches)
    if degraded:
        logger.warning(
            'Natural voice: %d/%d lô phải dịch 1:1 do reflow hỏng — các cue đó giữ nguyên timestamp gốc, không được gộp câu',
            degraded, len(batches))
    if natural_voice:
        dense = sum(
            1
            for cue in out
            if len(re.sub('\\s+', '', cue.text)) / cue.duration_s > 11.5)
        logger.info(
            'Natural voice SRT preflight: %d source cues -> %d cues; %d cue(s) near 1.35x limit',
            len(cues), len(out), dense)

    out = _repair_vietnamese_residuals(
        out,
        api_key=api_key,
        model=selected,
        engine=engine,
        target_lang=target_lang,
        cancel_check=cancel_check)
    return out


def _natural_voice_preflight(cues: list[SrtCue]) -> tuple[int, int]:
    """Count source cues that cannot reasonably be spoken as-is.

    This is a report, not a rejection: the natural reflow prompt is expected
    to merge or shorten these cues before the TTS phase.
    """
    too_short = sum(1 for cue in cues if cue.duration_s < 0.5)
    too_dense = sum(
        1
        for cue in cues
        if cue.duration_s >= 0.5
        and len(re.sub('\\s+', '', cue.text)) / cue.duration_s > 13.0)
    if too_short or too_dense:
        logger.warning(
            'Natural voice preflight: %d cue(s) <0.5s, %d cue(s) >13 chars/s; reflow required',
            too_short,
            too_dense)
        return (too_short, too_dense)
    logger.info('Natural voice preflight: source SRT is within basic duration/density limits')
    return (too_short, too_dense)


def _chunk_indices(n: int, chunk_size: int = 40) -> list[tuple[int, int]]:
    '''[start, end) index ranges.'''
    out = []
    i = 0
    while i < n:
        out.append((i, min(n, i + chunk_size)))
        i += chunk_size
    return out


def _http_json(url: str, body: dict, *,
               headers: dict[str, str],
               timeout: int = 30,
               retries: int = 3,
               retry_on: frozenset[int] = frozenset({429, 500, 502, 503}),
               service: str = 'API dịch',
               fast_fail_429: bool = False,
               cancel_check: Callable[[], bool] | None = None) -> dict:
    '''POST JSON với retry/backoff (đặc biệt 429 rate limit) và hỗ trợ ngắt tức thì.'''
    if cancel_check and cancel_check():
        raise InterruptedError('Đã dừng dịch theo yêu cầu.')
    data = json.dumps(body).encode('utf-8')
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    if headers:
        req_headers.update(headers)
    last_err = None

    def _sleep_interruptible(seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if cancel_check and cancel_check():
                raise InterruptedError('Đã dừng dịch theo yêu cầu.')
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))

    for attempt in range(max(1, retries)):
        if cancel_check and cancel_check():
            raise InterruptedError('Đã dừng dịch theo yêu cầu.')
        req = urllib.request.Request(url, data=data, headers=req_headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if cancel_check and cancel_check():
                raise InterruptedError('Đã dừng dịch theo yêu cầu.') from e
            err_body = e.read().decode('utf-8', errors='replace')[:600]
            last_err = e
            is_quota_exhausted = (
                'resource_exhausted' in err_body.casefold()
                or 'quota' in err_body.casefold())

            if e.code in retry_on and attempt + 1 < retries and not (
                    (e.code == 429 or e.code == 503)
                    and (fast_fail_429 or is_quota_exhausted)):
                wait = 2.0 * 2 ** attempt
                ra = e.headers.get('Retry-After') if e.headers else None
                if ra:
                    try:
                        wait = max(wait, float(ra))
                    except (TypeError, ValueError):
                        pass
                    wait = min(wait, 45.0)
                logger.warning(
                    '%s HTTP %s — retry %s/%s sau %.1fs · %s',
                    service,
                    e.code,
                    attempt + 1,
                    retries,
                    wait,
                    err_body[:120])
                _sleep_interruptible(wait)
                continue
            elif e.code == 429:
                raise RuntimeError(
                    f'{service} đã hết quota hoặc bị giới hạn rate (HTTP 429).\nApp sẽ chỉ chuyển key dự phòng của cùng provider (nếu được cấu hình).'
                ) from e
            elif e.code == 503:
                raise RuntimeError(
                    f'{service} máy chủ quá tải (HTTP 503 High Demand).\nApp sẽ chuyển sang model hoặc key khác ngay lập tức.'
                ) from e
            else:
                raise RuntimeError(f'{service} HTTP {e.code}: {err_body}') from e
        except Exception as e:
            if isinstance(e, InterruptedError) or cancel_check and cancel_check():
                raise InterruptedError('Đã dừng dịch theo yêu cầu.') from e
            last_err = e
            if attempt + 1 < retries:
                _sleep_interruptible(1.5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(str(last_err) if last_err else 'API request failed')


def _call_gemini(api_key: str, system: str, user: str, *,
                 model: str = DEFAULT_MODEL,
                 temperature: float = 0.2,
                 fast_fail_429: bool = False,
                 cancel_check: Callable[[], bool] | None = None) -> str:
    model = normalize_gemini_model(model)
    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{model}:generateContent?key={api_key}')
    generation_config = {'maxOutputTokens': 8192}
    if model.startswith('gemini-2.5'):
        generation_config['temperature'] = temperature
        generation_config['thinkingConfig'] = {'thinkingBudget': 0}
    else:
        generation_config['temperature'] = temperature
    body = {
        'systemInstruction': {'parts': [{'text': system}]},
        'contents': [{'role': 'user', 'parts': [{'text': user}]}],
        'generationConfig': generation_config}
    try:
        payload = _http_json(
            url,
            body,
            headers={'Content-Type': 'application/json'},
            retries=3,
            service=f'Gemini/{model}',
            fast_fail_429=fast_fail_429,
            cancel_check=cancel_check)
    except Exception as exc:
        err_str = str(exc).casefold()
        if 'thinking' in err_str or '400' in err_str and 'thinkingconfig' in str(body).casefold():
            body['generationConfig'].pop('thinkingConfig', None)
            body['generationConfig']['temperature'] = temperature
            payload = _http_json(
                url,
                body,
                headers={'Content-Type': 'application/json'},
                retries=2,
                service=f'Gemini/{model}',
                fast_fail_429=fast_fail_429,
                cancel_check=cancel_check)
        else:
            raise

    candidates = payload.get('candidates') or []
    if not candidates:
        raise RuntimeError(f'Gemini empty: {payload}')
    finish = str(candidates[0].get('finishReason') or '').upper()
    parts = (candidates[0].get('content') or {}).get('parts') or []
    text = ''.join(p.get('text') or '' for p in parts).strip()

    if finish == 'MAX_TOKENS':
        raise RuntimeError(
            'Gemini bị cắt vì chạm giới hạn token đầu ra (finishReason=MAX_TOKENS).\nGiảm số cue mỗi batch hoặc đổi sang model khác.')
    if finish in {'SAFETY', 'BLOCKLIST', 'RECITATION', 'PROHIBITED_CONTENT'}:
        raise RuntimeError(f'Gemini từ chối nội dung (finishReason={finish}).')
    if not text:
        raise RuntimeError(f'Gemini returned empty text (finishReason={finish or "không rõ"})')
    return text


def _call_openai_compatible(api_key: str, system: str, user: str, *,
                            endpoint: str,
                            engine: str,
                            model: str,
                            temperature: float = 0.2,
                            fast_fail_429: bool = False,
                            cancel_check: Callable[[], bool] | None = None) -> str:
    body = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}],
        'temperature': temperature,
        'max_tokens': 4096}
    if engine == 'Groq':
        if 'gpt-oss' in model or 'compound' in model:
            body['reasoning_effort'] = 'low'
    payload = _http_json(
        endpoint,
        body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'},
        retries=3,
        service=f'{engine}/{model}',
        fast_fail_429=fast_fail_429,
        cancel_check=cancel_check)
    choices = payload.get('choices') or []
    content = (((choices[0] if choices else {}).get('message') or {}).get('content') or '').strip()
    if not content:
        raise RuntimeError(f'API dịch trả về rỗng: {payload}')
    return content


def _is_model_failover_error(error: BaseException | str) -> bool:
    '''Kiểm tra lỗi liên quan đến model/quota có thể khắc phục bằng cách đổi model trên cùng key.'''
    text = str(error).casefold()
    markers = (
        'http 429', 'rate limit', 'rate-limit', 'quota', 'resource exhausted',
        'exceeded your current quota', 'http 404', 'model_not_found', 'model not found',
        'not found', 'is no longer available', 'is not supported', 'deprecated',
        'does not exist', 'do not have access', 'model_decommissioned', 'decommissioned',
        'no longer supported', 'not available to new users', 'http 503', 'high demand',
        'temporarily unavailable', 'overloaded')
    if any(marker in text for marker in markers):
        return True
    if 'http 400' in text and any(m in text for m in ('model', 'decommissioned', 'unsupported', 'invalid_request_error')):
        return True
    return False


def _is_key_failover_error(error: BaseException | str) -> bool:
    '''Return whether trying another key of the same provider can help.'''
    text = str(error).casefold()
    markers = (
        'http 429', 'rate limit', 'rate-limit', 'quota', 'resource exhausted',
        'http 401', 'http 403', 'invalid_api_key', 'invalid api key',
        'authentication_error', 'authentication error', 'unauthorized', 'forbidden',
        'has not been used in project', 'is disabled',
        'http 503', 'high demand', 'temporarily unavailable')
    return any(marker in text for marker in markers)


def _call_provider_single(engine: str, api_key: str, system: str, user: str, *,
                          model: str | None = None,
                          fast_fail_429: bool = False,
                          cancel_check: Callable[[], bool] | None = None) -> str:
    engine = _provider_name(engine)
    selected = resolve_translation_model(engine, model)
    if engine == 'Gemini':
        return _call_gemini(api_key, system, user, model=selected,
                            fast_fail_429=fast_fail_429, cancel_check=cancel_check)

    if engine == 'Groq':
        endpoint = 'https://api.groq.com/openai/v1/chat/completions'
    elif engine == 'OpenAI':
        endpoint = 'https://api.openai.com/v1/chat/completions'
    else:
        endpoint = 'https://api.deepseek.com/chat/completions'
    return _call_openai_compatible(
        api_key,
        system,
        user,
        endpoint=endpoint,
        engine=engine,
        model=selected,
        fast_fail_429=fast_fail_429,
        cancel_check=cancel_check)


def get_candidate_models_for_engine(engine: str, initial_model: str | None = None) -> list[str]:
    engine = _provider_name(engine)
    all_models = [m for m in ENGINE_MODELS.get(engine, []) if (engine, m) not in _DECOMMISSIONED_MODELS]
    resolved = resolve_translation_model(engine, initial_model)
    candidates = [resolved] if (engine, resolved) not in _DECOMMISSIONED_MODELS else []
    for m in all_models:
        if m != resolved and m not in candidates:
            candidates.append(m)
    return candidates or list(ENGINE_MODELS.get(engine, []))


def _call_provider(engine: str, api_key: str, system: str, user: str, *,
                   model: str | None = None,
                   status_callback: Callable[[str], None] | None = None,
                   cancel_check: Callable[[], bool] | None = None) -> str:
    '''Gọi provider dịch thuật với cơ chế xoay vòng siêu tốc:
    1. Ưu tiên xoay ngay sang API key kế tiếp khi gặp rate-limit/quota (HTTP 429) để giữ nguyên model chất lượng cao nhất.
    2. Nếu tất cả các key đều chạm hạn mức cho model hiện tại, mới tự động chuyển sang model tiếp theo.
    3. Nếu gặp lỗi 404/decommissioned, loại bỏ model đó ngay lập tức và chuyển model khác không chờ đợi.
    '''
    if cancel_check and cancel_check():
        raise InterruptedError('Đã dừng dịch theo yêu cầu.')

    engine = _provider_name(engine)
    keys = _split_api_keys(api_key)
    if not keys:
        raise RuntimeError(f'Chưa có API key cho {engine}.')

    initial_model = resolve_translation_model(engine, model)
    candidate_models = get_candidate_models_for_engine(engine, initial_model)

    key_count = len(keys)
    cursor_key = (engine, initial_model)
    start_index = _KEY_ROTATION_CURSOR.get(cursor_key, 0) % key_count
    now = time.monotonic()

    last_error = None
    for m_idx, current_model in enumerate(candidate_models):
        if (engine, current_model) in _DECOMMISSIONED_MODELS:
            continue
        if cancel_check and cancel_check():
            raise InterruptedError('Đã dừng dịch theo yêu cầu.')
        ordered_indices = [(start_index + offset) % key_count for offset in range(key_count)]

        for attempt_no, key_index in enumerate(ordered_indices, start=1):
            if cancel_check and cancel_check():
                raise InterruptedError('Đã dừng dịch theo yêu cầu.')

            key = keys[key_index]
            key_fp = _key_fingerprint(key)
            display_key_idx = key_index + 1

            if _KEY_COOLDOWN_UNTIL.get((engine, '*', key_fp), 0.0) > now:
                continue

            if _KEY_COOLDOWN_UNTIL.get((engine, current_model, key_fp), 0.0) > now:
                continue
            try:
                result = _call_provider_single(
                    engine,
                    key,
                    system,
                    user,
                    model=current_model,
                    fast_fail_429=True,
                    cancel_check=cancel_check)
                _LAST_WORKING_MODEL[(engine, key_fp)] = current_model
                _KEY_ROTATION_CURSOR[cursor_key] = key_index
                _KEY_COOLDOWN_UNTIL.pop((engine, current_model, key_fp), None)
                _KEY_COOLDOWN_UNTIL.pop((engine, '*', key_fp), None)
                return result
            except Exception as exc:
                if isinstance(exc, InterruptedError) or cancel_check and cancel_check():
                    raise InterruptedError('Đã dừng dịch theo yêu cầu.') from exc

                last_error = exc
                exc_str = str(exc).casefold()

                if any(mark in exc_str for mark in ('401', '403', 'invalid_api_key', 'forbidden', 'disabled', 'not been used')):
                    logger.warning(
                        '%s API key %s/%s bị lỗi xác thực/cấm (%s); bỏ qua toàn bộ key này.',
                        engine, display_key_idx, key_count, exc)
                    _KEY_COOLDOWN_UNTIL[(engine, '*', key_fp)] = now + 3600.0
                    continue

                is_decommissioned = any(k in exc_str for k in ('decommission', 'not found', '404', 'does not exist', 'not available'))
                if is_decommissioned:
                    logger.warning(
                        "%s model '%s' đã bị khai tử hoặc 404 (%s); loại bỏ ngay lập tức.",
                        engine, current_model, exc)
                    _DECOMMISSIONED_MODELS.add((engine, current_model))
                    break

                if _is_model_failover_error(exc):
                    cooldown_s = 60.0 if '429' in exc_str or 'rate' in exc_str else 180.0
                    _KEY_COOLDOWN_UNTIL[(engine, current_model, key_fp)] = now + cooldown_s
                    if attempt_no < len(ordered_indices):
                        next_key_idx = ordered_indices[attempt_no] + 1
                        logger.warning(
                            "%s key %s/%s gặp rate-limit (HTTP 429) với model '%s'; chuyển ngay sang key %s/%s...",
                            engine, display_key_idx, key_count, current_model, next_key_idx, key_count)

                        if status_callback:
                            status_callback(f'{engine}: Chuyển sang key dự phòng {next_key_idx}/{key_count} ({current_model})...')
                        _KEY_ROTATION_CURSOR[cursor_key] = (key_index + 1) % key_count
                        continue
                    logger.warning(
                        "%s: Toàn bộ %s API key đều đã chạm hạn mức cho model '%s'; chuyển sang model tiếp theo.",
                        engine, key_count, current_model)

                    break
                raise
    raise RuntimeError(
        f'{engine}: Tất cả các model và {key_count} API key khả dụng đều bị rate-limit/quota/lỗi. Lỗi cuối cùng: {last_error}')


def _parse_numbered_lines(raw: str, expected_n: int) -> list[str]:
    """Parse '1|text' or '1. text' or '1) text' và lọc sạch mọi tiền tố đánh số thừa/kép."""
    lines_map = {}
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.match('^(\\d+)\\s*[|.:)\\-]\\s*(.+)$', ln)
        if not m:
            continue
        idx = int(m.group(1))
        val = _clean_cue_text(m.group(2))
        lines_map[idx] = val
    if len(lines_map) >= expected_n:
        return [_clean_cue_text(lines_map.get(i + 1, '')) for i in range(expected_n)]
    plain = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.startswith('```')]
    cleaned = []
    for ln in plain:
        cleaned.append(_clean_cue_text(ln))
    if len(cleaned) < expected_n:
        while len(cleaned) < expected_n:
            cleaned.append('')
    return [_clean_cue_text(t) for t in cleaned[:expected_n]]


def _is_vietnamese_target(target_lang: str) -> bool:
    value = (target_lang or '').strip().casefold()
    return value in {'tiếng việt', 'vi-vn', 'vi', 'vietnamese'}


def _repair_vietnamese_residuals(cues: list[SrtCue], *, api_key: str, model: str,
                                 engine: str,
                                 target_lang: str,
                                 source_lang: str | None = None,
                                 max_passes: int = 2,
                                 cancel_check: Callable[[], bool] | None = None) -> list[SrtCue]:
    '''Dịch lại riêng cue còn chữ Hán, giữ nguyên index và timestamp.'''
    if not _is_vietnamese_target(target_lang) or not cues:
        return cues

    out = list(cues)
    initial = [
        i for i, cue in enumerate(out)
        if looks_untranslated(cue.text, target_lang='Tiếng Việt', source_lang=source_lang)]

    if not initial:
        return out

    logger.warning(
        '%s/%s hậu kiểm: phát hiện %d/%d cue còn chữ nguồn — dịch lại đúng các cue này',
        engine, model, len(initial), len(out))

    previous_count = len(initial) + 1
    repair_system = (
        SYSTEM
        + '\nĐây là lượt HẬU KIỂM. Mỗi dòng dưới đây chưa được dịch hoàn chỉnh hoặc còn lẫn tiếng nguồn. Bắt buộc chuyển toàn bộ sang tiếng Việt tự nhiên, đúng nghĩa. Tên riêng phiên âm chuẩn xác; tuyệt đối không để sót từ ngữ hoặc ký tự của tiếng nguồn.')

    for pass_index in range(max(1, max_passes)):
        if cancel_check and cancel_check():
            break
        positions = [
            i for i, cue in enumerate(out)
            if looks_untranslated(cue.text, target_lang='Tiếng Việt', source_lang=source_lang)]

        if not positions or len(positions) >= previous_count and pass_index > 0:
            break
        previous_count = len(positions)

        for offset in range(0, len(positions), 16):
            if cancel_check and cancel_check():
                break
            batch_positions = positions[offset:offset + 16]
            numbered = '\n'.join(
                f'{index + 1}|{out[pos].text}'
                for index, pos in enumerate(batch_positions))
            user = (
                f'Dịch lại đúng {len(batch_positions)} dòng sau sang tiếng Việt. Giữ số thứ tự cục bộ 1..N và chỉ trả SỐ|BẢN DỊCH.\n\n'
                f'{numbered}')
            try:
                raw = _call_provider(
                    engine, api_key, repair_system, user,
                    model=model, cancel_check=cancel_check)
            except (InterruptedError, Exception) as exc:
                if isinstance(exc, InterruptedError):
                    logger.info('%s/%s hậu kiểm dừng theo lệnh người dùng', engine, model)
                else:
                    logger.warning('%s/%s hậu kiểm chữ nguồn dừng ở lượt %d: %s', engine, model, pass_index + 1, exc)
                return out
            repaired = _parse_numbered_lines(raw, len(batch_positions))
            for pos, text in zip(batch_positions, repaired):
                cleaned = _clean_cue_text((text or '').strip())
                if not cleaned:
                    continue
                cue = out[pos]
                out[pos] = SrtCue(
                    cue.index,
                    cue.start_s,
                    cue.end_s,
                    cleaned)

    remaining = sum(
        1 for cue in out
        if looks_untranslated(cue.text, target_lang='Tiếng Việt', source_lang=source_lang))

    logger.info(
        '%s/%s hậu kiểm chữ nguồn: %d → %d cue còn sót',
        engine, model, len(initial), remaining)

    return out


def _estimated_tokens(text: str) -> int:
    '''Cheap conservative token estimate; avoids an extra tokenizer dependency.'''
    return max(1, (len((text or '').strip()) + 1) // 2) + 12


def _token_batches(cues: Sequence[SrtCue], positions: Sequence[int], *,
                   max_cues: int,
                   token_budget: int) -> list[list[int]]:
    '''Group selected cues by estimated token load, never merely by count.'''
    batches = []
    batch = []
    used = 0
    for pos in positions:
        cost = _estimated_tokens(cues[pos].text)
        if batch and (len(batch) >= max_cues or used + cost > token_budget):
            batches.append(batch)
            batch, used = [], 0
        batch.append(pos)
        used += cost
    if batch:
        batches.append(batch)
    return batches


def _glossary_instruction(glossary: Mapping[str, str]) -> str:
    if not glossary:
        return ''
    lines = []
    for source, target in list(glossary.items())[:80]:
        line = f'{source} => {target}'
        if sum(len(item) + 1 for item in lines) + len(line) > 3500:
            break
        lines.append(line)
    if not lines:
        return ''
    return '\n\nTỪ ĐIỂN TÊN RIÊNG BẮT BUỘC (giữ đúng bản dịch sau dấu =>):\n' + '\n'.join(lines)


def _batch_quality(cues: Sequence[SrtCue], translated_texts: Sequence[str],
                   positions: Sequence[int], *,
                   target_lang: str,
                   source_lang: str | None = None) -> tuple[list[int], list[int]]:
    '''Return retryable unresolved cue positions and dense cue warning positions.'''
    retryable = []
    dense = []
    for pos in positions:
        text = (translated_texts[pos] or '').strip()
        if not text or looks_untranslated(text, target_lang=target_lang, source_lang=source_lang):
            retryable.append(pos)
            continue
        duration = max(0.1, cues[pos].end_s - cues[pos].start_s)
        if len(text) / duration > 22:
            dense.append(pos)
    return (retryable, dense)


def _repair_batch_quality(cues: Sequence[SrtCue], translated_texts: list[str],
                          positions: Sequence[int], *,
                          api_key: str,
                          model: str,
                          engine: str,
                          target_lang: str,
                          source_lang: str | None = None,
                          glossary: Mapping[str, str],
                          status_callback: Callable[[str], None] | None = None,
                          cancel_check: Callable[[], bool] | None = None) -> int:
    '''One targeted retry for empty/source-script residue from a just-finished batch.'''
    if not positions or (cancel_check and cancel_check()):
        return 0
    system = SYSTEM + ('\nĐây là hậu kiểm một batch. Bắt buộc trả bản dịch hoàn chỉnh, không để sót chữ nguồn.'
                       + _glossary_instruction(glossary))

    fixed = 0
    for offset in range(0, len(positions), 12):
        if cancel_check and cancel_check():
            break
        group = list(positions[offset:offset + 12])
        numbered = '\n'.join(
            f'{i + 1}|{translated_texts[pos] or cues[pos].text}'
            for i, pos in enumerate(group))
        user = (
            f'Hậu kiểm và chuyển hoàn toàn sang {target_lang}. Trả đúng {len(group)} dòng 1..N, chỉ dạng SỐ|BẢN DỊCH.\n\n'
            + numbered)
        if status_callback:
            status_callback(f'{engine}/{model}: Đang hậu kiểm {len(group)} câu...')
        try:
            repaired = _parse_numbered_lines(
                _call_provider(
                    engine,
                    api_key,
                    system,
                    user,
                    model=model,
                    status_callback=status_callback,
                    cancel_check=cancel_check),
                len(group))
        except Exception as exc:
            if isinstance(exc, InterruptedError) or cancel_check and cancel_check():
                logger.info('%s/%s batch quality retry cancelled by user', engine, model)
            else:
                logger.warning('%s/%s batch quality retry paused: %s', engine, model, exc)
            return fixed
        for pos, text in zip(group, repaired):
            cleaned = apply_glossary(_clean_cue_text(text or ''), glossary)
            if not cleaned:
                continue
            if looks_untranslated(cleaned, target_lang=target_lang, source_lang=source_lang):
                continue
            translated_texts[pos] = cleaned
            fixed += 1
    return fixed


def translate_cues(cues: list[SrtCue], *,
                   api_key: str | None = None,
                   model: str | None = None,
                   engine: str = 'Gemini',
                   source_lang: str = 'auto-detect',
                   target_lang: str = 'Vietnamese',
                   chunk_size: int = 40,
                   repair_residual: bool = True,
                   positions: Sequence[int] | None = None,
                   on_checkpoint: Callable[[list[SrtCue], int, int, int], None] | None = None,
                   glossary: Mapping[str, str] | None = None,
                   quality_report: dict[str, Any] | None = None,
                   status_callback: Callable[[str], None] | None = None,
                   cancel_check: Callable[[], bool] | None = None) -> list[SrtCue]:
    '''Translate selected cues and optionally expose a durable batch checkpoint.

    ``positions`` keeps already translated cues untouched.  This is the core of
    resume: a later run may use another provider/model and submit only text
    which still looks untranslated.  ``on_checkpoint`` receives a full SRT
    snapshot with partial progress and may be called multiple times.
    '''
    engine = _provider_name(engine)
    cues = list(cues)
    n = len(cues)
    if n == 0:
        return []

    if engine == 'Gemini' and chunk_size > 32:
        chunk_size = 32
    selected = resolve_translation_model(engine, model)
    key = api_key or get_translation_api_key(engine)
    if not key:
        raise RuntimeError(f'Chưa có API key cho {engine}.')

    if positions is None:
        target_positions = list(range(n))
    else:
        target_positions = sorted({int(pos) for pos in positions if 0 <= int(pos) < n})
    if not target_positions:
        return [SrtCue(c.index, c.start_s, c.end_s, c.text) for c in cues]

    translated_texts = [c.text for c in cues]
    total_targets = len(target_positions)
    configured_glossary = dict(glossary if glossary is not None else load_glossary())
    memory = load_translation_memory()
    report = quality_report if quality_report is not None else {}
    report.setdefault('cache_hits', 0)
    report.setdefault('cache_misses', 0)
    report.setdefault('quality_fixed', 0)
    report.setdefault('quality_pending', 0)
    report.setdefault('dense_cues', [])

    pending_request_positions = []
    for pos in target_positions:
        cache_id = memory_key(
            cues[pos].text,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary=configured_glossary)
        cached = (memory.get(cache_id) or '').strip()
        if cached and not looks_untranslated(cached, target_lang=target_lang, source_lang=source_lang):
            translated_texts[pos] = cached
            report['cache_hits'] = int(report['cache_hits']) + 1
        else:
            pending_request_positions.append(pos)
            report['cache_misses'] = int(report['cache_misses']) + 1
    completed = total_targets - len(pending_request_positions)

    def snapshot() -> list[SrtCue]:
        return [
            SrtCue(c.index, c.start_s, c.end_s, translated_texts[i] or c.text)
            for i, c in enumerate(cues)]

    if completed and on_checkpoint:
        on_checkpoint(snapshot(), completed, total_targets, cues[target_positions[completed - 1]].index + 1)

    token_budget = 4200 if engine == 'Gemini' else 5600
    batches = _token_batches(
        cues,
        pending_request_positions,
        max_cues=chunk_size,
        token_budget=token_budget)

    for batch_number, batch_positions in enumerate(batches, start=1):
        if cancel_check and cancel_check():
            logger.info('translate_cues: user requested cancellation before batch %d', batch_number)
            break
        batch = [cues[pos] for pos in batch_positions]
        bn = len(batch)
        numbered = '\n'.join(f'{i + 1}|{c.text}' for i, c in enumerate(batch))
        from app.services.language_detector import get_pair_translation_prompt, normalize_lang_name
        src_clean = normalize_lang_name(source_lang)
        tgt_clean = normalize_lang_name(target_lang)
        source_instruction = (
            f'Ngôn ngữ nguồn là {src_clean}.'
            if src_clean != 'Tự nhận diện' else 'Tự nhận diện ngôn ngữ nguồn từ từng câu.')
        guidance = get_pair_translation_prompt(src_clean, tgt_clean)
        user = (
            f'{source_instruction} Dịch sang {tgt_clean}. ĐÚNG {bn} dòng. Giữ số thứ tự.\n\nYÊU CẦU DỊCH THUẬT:\n'
            f'{guidance}\n\n'
            f'{numbered}'
            + _glossary_instruction(configured_glossary))
        logger.info(
            '%s/%s translate cue %s-%s · adaptive batch %s/%s · %s-%s / %s',
            engine,
            selected,
            cues[batch_positions[0]].index + 1,
            cues[batch_positions[-1]].index + 1,
            batch_number,
            len(batches),
            completed + 1,
            completed + bn,
            total_targets)
        if status_callback:
            status_callback(
                f'{engine}/{selected}: Đang dịch {completed + 1}-{completed + bn}/{total_targets} cue (batch '
                f'{batch_number}/{len(batches)})...')
        try:
            raw = _call_provider(
                engine,
                key,
                SYSTEM,
                user,
                model=selected,
                status_callback=status_callback,
                cancel_check=cancel_check)
        except InterruptedError:
            logger.info('translate_cues: user requested cancellation during batch %d', batch_number)
            break
        parts = _parse_numbered_lines(raw, bn)
        for pos, text, cue in zip(batch_positions, parts, batch):
            raw_text = _clean_cue_text(text or cue.text)
            translated_texts[pos] = apply_glossary(raw_text.strip(), configured_glossary)

        retryable, dense = _batch_quality(
            cues, translated_texts, batch_positions,
            target_lang=target_lang, source_lang=source_lang)
        if retryable and not (cancel_check and cancel_check()):
            logger.warning(
                '%s/%s batch quality: retry %d unresolved cue(s)',
                engine, selected, len(retryable))
            report['quality_fixed'] = int(report['quality_fixed']) + _repair_batch_quality(
                cues,
                translated_texts,
                retryable,
                api_key=key,
                model=selected,
                engine=engine,
                target_lang=target_lang,
                source_lang=source_lang,
                glossary=configured_glossary,
                status_callback=status_callback,
                cancel_check=cancel_check)

        unresolved, _dense_after = _batch_quality(
            cues, translated_texts, batch_positions,
            target_lang=target_lang, source_lang=source_lang)
        report['quality_pending'] = int(report['quality_pending']) + len(unresolved)
        report['dense_cues'].extend(cues[pos].index + 1 for pos in dense)
        for pos in batch_positions:
            translated = (translated_texts[pos] or '').strip()
            if not translated:
                continue
            if looks_untranslated(translated, target_lang=target_lang, source_lang=source_lang):
                continue
            memory[memory_key(
                cues[pos].text,
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=configured_glossary)] = translated
        try:
            save_translation_memory(memory)
        except Exception as exc:
            logger.warning('Cannot save translation memory: %s', exc)
        completed += bn
        if on_checkpoint:
            on_checkpoint(
                snapshot(),
                completed,
                total_targets,
                cues[batch_positions[-1]].index + 1)

    out = snapshot()
    if repair_residual and not (cancel_check and cancel_check()):
        out = _repair_vietnamese_residuals(
            out,
            api_key=key,
            model=selected,
            engine=engine,
            target_lang=target_lang,
            source_lang=source_lang,
            cancel_check=cancel_check)
    return out


def _translation_sidecar_paths(out_path: Path) -> tuple[Path, Path]:
    '''Return persistent progress and append-only batch log paths for an SRT.'''
    return (
        out_path.with_suffix(out_path.suffix + '.progress.json'),
        out_path.with_suffix(out_path.suffix + '.translation.jsonl'))


def _persist_translation_checkpoint(snapshot: list[SrtCue], *,
                                    out_path: Path,
                                    progress_path: Path,
                                    log_path: Path,
                                    source_path: Path,
                                    engine: str,
                                    model: str,
                                    target_lang: str,
                                    source_lang: str | None = None,
                                    initial_pending: int,
                                    last_source_cue: int,
                                    status: str,
                                    note: str = '',
                                    quality_report: Mapping[str, Any] | None = None) -> tuple[int, int]:
    '''Save the usable SRT first, then a machine-readable resume checkpoint.

    The SRT is intentionally complete at every checkpoint: translated cue(s)
    followed by untouched ones.  Therefore it stays editable and can be used as
    the input of the next run after the user changes provider or model.
    '''
    write_srt(snapshot, out_path)
    remaining = sum(
        1 for cue in snapshot
        if looks_untranslated(cue.text, target_lang=target_lang, source_lang=source_lang))

    completed = max(0, initial_pending - remaining)
    record = {
        'version': 1,
        'status': status,
        'source_srt': str(source_path),
        'output_srt': str(out_path),
        'engine': engine,
        'model': model,
        'target_lang': target_lang,
        'total_cues': len(snapshot),
        'initial_pending': initial_pending,
        'translated_in_run': completed,
        'remaining_cues': remaining,
        'last_source_cue': max(0, int(last_source_cue)),
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'note': note,
        'quality': dict(quality_report or {})}
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = progress_path.with_suffix(progress_path.suffix + '.tmp')
    temp_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    temp_path.replace(progress_path)
    with log_path.open('a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + '\n')
    logger.info(
        'Translation checkpoint %s: +%s/%s, remaining=%s, last cue=%s',
        status, completed, initial_pending, remaining, last_source_cue)

    return (completed, remaining)


def translate_srt_file(srt_path: str | Path, out_path: str | Path | None = None, *,
                       api_key: str | None = None,
                       model: str | None = None,
                       engine: str = 'Gemini',
                       source_lang: str = 'auto-detect',
                       target_lang: str = 'Vietnamese',
                       reflow: bool = False,
                       natural_voice: bool = False,
                       progress_callback: Callable[[int, int, str], None] | None = None,
                       status_callback: Callable[[str], None] | None = None,
                       cancel_check: Callable[[], bool] | None = None) -> TranslateResult:
    '''Translate with durable batch checkpoints and provider-agnostic resume.

    If quota/network fails, the return value is ``ok=False`` *but* ``srt_path``
    points to a usable partially translated SRT.  Calling this again with that
    path and a different engine/model only sends cue(s) that still look
    untranslated.\n    '''
    srt_path = Path(srt_path)
    out = Path(out_path) if out_path else srt_path.with_suffix('.translated.srt')
    progress_path, log_path = _translation_sidecar_paths(out)
    last_snapshot = []
    initial_pending = 0
    used_model = ''
    selected_engine = str(engine or 'Gemini')
    last_checkpoint_cue = 0
    quality_report = {
        'cache_hits': 0,
        'cache_misses': 0,
        'quality_fixed': 0,
        'quality_pending': 0,
        'dense_cues': []}

    try:
        selected_engine = _provider_name(engine)
        used_model = resolve_translation_model(selected_engine, model)
        cues = load_srt(srt_path)
        n = len(cues)
        if n == 0:
            return TranslateResult(False, None, 0, 'SRT rỗng')
        key = api_key or get_translation_api_key(selected_engine)
        if not key:
            return TranslateResult(False, None, n, f'Chưa có API key cho {selected_engine}')
        active_glossary = load_glossary()

        from app.services.language_detector import detect_srt_language, is_untranslated_cue, normalize_lang_name

        effective_source = normalize_lang_name(source_lang)
        if effective_source == 'Tự nhận diện':
            detected = detect_srt_language(cues)
            if detected != 'Tự nhận diện':
                effective_source = detected
                logger.info('Tự nhận diện ngôn ngữ nguồn SRT: %s', effective_source)
        normalized_target = normalize_lang_name(target_lang)

        if effective_source != 'Tự nhận diện' and effective_source == normalized_target:
            return TranslateResult(
                True, out, n,
                f'Phụ đề nguồn đã là {effective_source} (trùng với ngôn ngữ đích {normalized_target}), không cần dịch lại.',
                used_model, n, 0, progress_path, log_path)

        pending_positions = [
            i for i, cue in enumerate(cues)
            if is_untranslated_cue(cue.text, target_lang=normalized_target, source_lang=effective_source)]

        initial_pending = len(pending_positions)
        last_snapshot = list(cues)

        def save_snapshot(snapshot: list[SrtCue], *, last_source_cue: int,
                          status: str = 'running',
                          note: str = '') -> tuple[int, int]:
            nonlocal last_snapshot, last_checkpoint_cue
            last_snapshot = list(snapshot)
            last_checkpoint_cue = max(0, int(last_source_cue))
            completed, remaining = _persist_translation_checkpoint(
                last_snapshot,
                out_path=out,
                progress_path=progress_path,
                log_path=log_path,
                source_path=srt_path,
                engine=selected_engine,
                model=used_model,
                target_lang=target_lang,
                source_lang=effective_source,
                initial_pending=initial_pending,
                last_source_cue=last_source_cue,
                status=status,
                note=note,
                quality_report=quality_report)
            if progress_callback:
                cache_hits = int(quality_report.get('cache_hits') or 0)
                repaired = int(quality_report.get('quality_fixed') or 0)
                pending_quality = int(quality_report.get('quality_pending') or 0)
                metrics = (
                    (f' · cache {cache_hits}' if cache_hits else '')
                    + (f' · hậu kiểm sửa {repaired}' if repaired else '')
                    + (f' · cần kiểm tra {pending_quality}' if pending_quality else ''))
                progress_callback(
                    completed,
                    initial_pending,
                    f'Dịch {completed}/{initial_pending} cue mới · còn {remaining} cue chưa dịch{metrics}')
            return (completed, remaining)

        save_snapshot(cues, last_source_cue=0, note='Bắt đầu hoặc tiếp tục dịch')
        if not pending_positions:
            completed, remaining = save_snapshot(
                cues, last_source_cue=n, status='complete', note='Không còn cue cần dịch')
            return TranslateResult(
                True, out, n,
                f'SRT đã dịch xong, không có cue cần gọi API ({selected_engine}/{used_model}).',
                used_model, completed, remaining, progress_path, log_path)

        short_n = dense_n = 0
        reflow_report = {}
        if natural_voice:
            short_n, dense_n = _natural_voice_preflight(cues)
        effective_reflow = bool(reflow or natural_voice)

        try:
            if effective_reflow and len(pending_positions) == n:
                def on_reflow_checkpoint(partial_reflow: list[SrtCue], consumed: int, _total: int) -> None:
                    hybrid = list(partial_reflow) + list(cues[consumed:])
                    last_cue = cues[consumed - 1].index + 1 if consumed else 0
                    save_snapshot(
                        hybrid,
                        last_source_cue=last_cue,
                        note='Checkpoint AI gộp timeline')
                translated = translate_cues_reflow(
                    cues,
                    api_key=key,
                    model=used_model,
                    engine=selected_engine,
                    source_lang=effective_source,
                    target_lang=normalized_target,
                    natural_voice=natural_voice,
                    report=reflow_report,
                    on_checkpoint=on_reflow_checkpoint,
                    cancel_check=cancel_check)
            else:
                resume_note = (
                    'Tiếp tục cue chưa dịch theo 1:1 để giữ nguyên phần đã gộp trước đó'
                    if effective_reflow and len(pending_positions) < n
                    else 'Checkpoint dịch 1:1')

                def on_direct_checkpoint(snapshot: list[SrtCue], _done: int, _total: int, last_cue: int) -> None:
                    save_snapshot(snapshot, last_source_cue=last_cue, note=resume_note)
                translated = translate_cues(
                    cues,
                    api_key=key,
                    model=used_model,
                    engine=selected_engine,
                    source_lang=effective_source,
                    target_lang=normalized_target,
                    positions=pending_positions,
                    on_checkpoint=on_direct_checkpoint,
                    glossary=active_glossary,
                    quality_report=quality_report,
                    status_callback=status_callback,
                    cancel_check=cancel_check)
        except InterruptedError:
            logger.info('translate_srt_file: process interrupted by user cancellation')
            translated = list(last_snapshot)

        if active_glossary:
            translated = [
                SrtCue(cue.index, cue.start_s, cue.end_s, apply_glossary(cue.text, active_glossary))
                for cue in translated]

        if cancel_check and cancel_check():
            completed, remaining = save_snapshot(
                translated,
                last_source_cue=last_checkpoint_cue,
                status='paused',
                note='Người dùng đã dừng dịch')
            return TranslateResult(
                ok=False,
                srt_path=out,
                n_lines=n,
                message=f'Đã dừng dịch theo yêu cầu. Đã lưu {completed}/{initial_pending} cue đã dịch.',
                model=used_model,
                completed_lines=completed,
                remaining_lines=remaining,
                progress_path=progress_path,
                log_path=log_path,
                quality_report=quality_report)

        if not effective_reflow and len(translated) != n:
            return TranslateResult(False, out, n, f'N lệch: input {n} output {len(translated)}')

        completed, remaining = save_snapshot(
            translated,
            last_source_cue=n,
            status='complete',
            note='Dịch hoàn tất')
        vietnamese_target = _is_vietnamese_target(target_lang)
        residual_note = (
            f' · còn {remaining} cue có chữ nguồn, có thể dịch tiếp trong bảng dịch tay'
            if vietnamese_target and remaining
            else ' · hậu kiểm: không còn chữ Hán' if vietnamese_target else '')
        degraded = int(reflow_report.get('degraded') or 0)
        degraded_note = (
            f' · {degraded}/{reflow_report.get("batches")} phần phải dịch 1:1'
            if degraded else '')
        cache_hits = int(quality_report.get('cache_hits') or 0)
        quality_fixed = int(quality_report.get('quality_fixed') or 0)
        quality_pending = int(quality_report.get('quality_pending') or 0)
        quality_note = (
            (f' · cache {cache_hits} cue' if cache_hits else '')
            + (f' · hậu kiểm sửa {quality_fixed} cue' if quality_fixed else '')
            + (f' · còn {quality_pending} lỗi batch cần kiểm tra' if quality_pending else ''))
        mode = ('chuẩn hóa voice tự nhiên' if natural_voice else
                'tối ưu câu + timeline' if effective_reflow else 'dịch giữ timestamp')
        return TranslateResult(
            ok=True,
            srt_path=out,
            n_lines=n,
            message=(f'Đã {mode}: thêm {completed}/{initial_pending} cue ({selected_engine}/{used_model}) → {out.name}'
                     f'{residual_note}{degraded_note}{quality_note}'
                     + (f' · quét trước render: {short_n} cue ngắn, {dense_n} cue dày chữ' if natural_voice else '')),
            model=used_model,
            completed_lines=completed,
            remaining_lines=remaining,
            progress_path=progress_path,
            log_path=log_path,
            quality_report=quality_report)
    except Exception as exc:
        logger.exception('translate paused/failed')

        if last_snapshot:
            try:
                completed, remaining = _persist_translation_checkpoint(
                    last_snapshot,
                    out_path=out,
                    progress_path=progress_path,
                    log_path=log_path,
                    source_path=srt_path,
                    engine=selected_engine,
                    model=used_model,
                    target_lang=target_lang,
                    initial_pending=initial_pending,
                    last_source_cue=last_checkpoint_cue,
                    status='paused',
                    note=f'Tạm dừng: {exc}',
                    quality_report=quality_report)
                if progress_callback:
                    progress_callback(
                        completed, initial_pending,
                        f'Tạm dừng ở quota/lỗi · đã lưu {completed}/{initial_pending} cue mới')
                return TranslateResult(
                    ok=False,
                    srt_path=out,
                    n_lines=len(last_snapshot),
                    message=(f'Dịch tạm dừng: {exc}'
                             f'\n\nĐã lưu {completed}/{initial_pending} cue mới, còn {remaining} cue chưa dịch. Đổi provider/model/API key rồi bấm Dịch phụ đề lại để tiếp tục; app chỉ gửi các cue còn thiếu.'),
                    model=used_model,
                    completed_lines=completed,
                    remaining_lines=remaining,
                    progress_path=progress_path,
                    log_path=log_path,
                    quality_report=quality_report)
            except Exception:
                logger.exception('Could not save failed translation checkpoint')
        return TranslateResult(ok=False, srt_path=None, message=str(exc), model=used_model)

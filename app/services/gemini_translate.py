# Source Generated with Decompyle++
# File: gemini_translate.pyc (Python 3.12)

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
  Gemini: AUTO_RENDER_GEMINI_API_KEY, MUMU_GEMINI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY
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
import urllib.error as urllib
import urllib.request as urllib
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
_EXHAUSTED_MODELS: 'set[str]' = set()
_DECOMMISSIONED_MODELS: 'set[tuple[str, str]]' = set()
_LAST_WORKING_MODEL: 'dict[tuple[str, str], str]' = { }
_KEY_ROTATION_CURSOR: 'dict[tuple[str, str], int]' = { }
_KEY_COOLDOWN_UNTIL: 'dict[tuple[str, str, str], float]' = { }

def clear_exhausted_models():
    '''Xóa danh sách các model bị khóa quota (gọi khi đổi key hoặc mở app).'''
    _EXHAUSTED_MODELS.clear()
    _DECOMMISSIONED_MODELS.clear()
    _LAST_WORKING_MODEL.clear()
    _KEY_ROTATION_CURSOR.clear()
    _KEY_COOLDOWN_UNTIL.clear()


def _key_fingerprint(api_key = None):
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]


def _key_cooldown_seconds(error = None):
    '''Cooldown đủ để tránh gọi lại key lỗi ở ngay batch kế tiếp.'''
    pass
# WARNING: Decompyle incomplete

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
    'DeepSeek': [
        'deepseek-chat',
        'deepseek-reasoner'] }
PROVIDER_DEFAULTS = {
    'Gemini': 'gemini-3.5-flash',
    'Groq': 'openai/gpt-oss-120b',
    'OpenAI': 'gpt-4o-mini',
    'DeepSeek': 'deepseek-chat' }
PROVIDER_ENV = {
    'Gemini': ('AUTO_RENDER_GEMINI_API_KEY', 'MUMU_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'),
    'Groq': ('AUTO_RENDER_GROQ_API_KEY', 'GROQ_API_KEY'),
    'OpenAI': ('AUTO_RENDER_OPENAI_API_KEY', 'OPENAI_API_KEY'),
    'DeepSeek': ('AUTO_RENDER_DEEPSEEK_API_KEY', 'DEEPSEEK_API_KEY') }

def _provider_name(engine = None):
    if not engine:
        engine
    selected = ''.strip()
    if selected in PROVIDER_DEFAULTS:
        return selected
    if not selected:
        selected
    raise None(f'''Engine dịch không hỗ trợ: {'(trống)'}. Chọn một trong: {', '.join(PROVIDER_DEFAULTS)}.''')


def _split_api_keys(value = None):
    '''Return unique API keys entered one per line, preserving their order.'''
    seen = set()
    keys = []
    if not value:
        value
    for raw in ''.splitlines():
        key = raw.strip()
        if not key:
            continue
        if not key not in seen:
            continue
        keys.append(key)
        seen.add(key)
    return keys


def get_translation_api_keys(engine = None):
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
        
        return PROVIDER_ENV[engine], values
    if key_file.is_file():
        
        try:
            _split_api_keys(key_file.read_text(encoding = 'utf-8')) = Path.home() / '.mumu' / f'''{engine.lower()}_api_key.txt'''
            if values:
                return values
            return None
        except OSError:
            values = []
            continue



def get_translation_api_key(engine = None):
    '''Compatibility helper returning the configured keys as newline text.'''
    keys = get_translation_api_keys(engine)
    if not '\n'.join(keys):
        '\n'.join(keys)


def set_translation_api_key(engine = None, key = None, *, persist):
    engine = _provider_name(engine)
    value = '\n'.join(_split_api_keys(key))
    os.environ[PROVIDER_ENV[engine][0]] = value
    clear_exhausted_models()
    if persist:
        path = Path.home() / '.mumu' / f'''{engine.lower()}_api_key.txt'''
        path.parent.mkdir(parents = True, exist_ok = True)
        if value:
            path.write_text(value, encoding = 'utf-8')
            return None
        if path.is_file():
            
            try:
                path.unlink()
                return None
                return None
                return None
            except OSError:
                return None



def get_gemini_api_key():
    return get_translation_api_key('Gemini')


def set_gemini_api_key(key = None, *, persist):
    set_translation_api_key('Gemini', key, persist = persist)


def normalize_gemini_model(model = None):
    pass
# WARNING: Decompyle incomplete


def resolve_translation_model(engine = None, model = None):
    '''Chọn đúng model của provider; tuyệt đối không fallback chéo provider.'''
    engine = _provider_name(engine)
    if not model:
        model
    raw = ''.strip()
    if not raw:
        return PROVIDER_DEFAULTS[engine]
    if None == 'Gemini':
        selected = normalize_gemini_model(raw)
        return selected
    if None == 'Groq':
        groq_deprecated = {
            'llama3-70b-8192': 'openai/gpt-oss-120b',
            'llama-3-70b-8192': 'openai/gpt-oss-120b',
            'llama3-8b-8192': 'openai/gpt-oss-20b',
            'llama-3-8b-8192': 'openai/gpt-oss-20b',
            'llama-3.3-70b-versatile': 'openai/gpt-oss-120b',
            'mixtral-8x7b-32768': 'groq/compound' }
        if raw in groq_deprecated:
            migrated = groq_deprecated[raw]
            logger.info('Model Groq %r đã bị khai tử; tự động chuyển sang %s', raw, migrated)
            return migrated
        if None not in ENGINE_MODELS[engine]:
            logger.info('Dùng model %r cho engine %s (ngoài danh mục mặc định).', raw, engine)
    return raw

TranslateResult = <NODE:12>()
SYSTEM = 'Bạn là chuyên gia biên dịch phụ đề chuyên nghiệp, hỗ trợ dịch chuẩn xác mọi cặp ngôn ngữ.\nQUY TẮC BẮT BUỘC:\n1. Input là đúng N dòng đánh số 1..N.\n2. Output PHẢI đúng N dòng, mỗi dòng một bản dịch, GIỮ NGUYÊN số thứ tự.\n3. KHÔNG gộp 2 dòng thành 1. KHÔNG tách 1 dòng thành 2.\n4. Giữ timestamp không đổi (bạn chỉ dịch text).\n5. Văn phong tự nhiên, đúng ngữ cảnh (phim ảnh, vlog, đời sống, khoa học...). Tên riêng giữ nhất quán.\n6. Nếu đích là Tiếng Việt: dịch câu tự nhiên, thoát ý, không để sót từ ngữ của tiếng nguồn.\n7. Chỉ trả về các dòng dạng: 1|bản dịch\n   Không markdown, không giải thích.\n'
REFLOW_SYSTEM = 'Bạn là một chuyên gia Dịch thuật và Biên tập Phụ đề (Subtitle Editor) hàng đầu thế giới.\nNhiệm vụ của bạn là dịch file SRT sang ngôn ngữ đích được yêu cầu, đồng thời CHUẨN HÓA LẠI CẤU TRÚC TIMELINE.\n\nTình trạng file đầu vào:\nFile SRT này được tạo ra từ phần mềm Speech-to-Text (STT) tự động, nên các câu thoại thường bị cắt vụn lộn xộn, sai ngữ pháp (ví dụ: một từ hoặc một câu bị bẻ đôi ra làm 2 block thời gian khác nhau). Nếu là chữ Hán, đôi khi bị chèn khoảng trắng giữa từng ký tự — hãy tự nối lại khi đọc.\n\nYêu cầu thực thi:\n1. Đọc và hiểu toàn bộ ngữ cảnh liền mạch của các dòng SRT đầu vào trước khi dịch. KHÔNG dịch máy móc từng dòng một.\n2. Dịch sang ngôn ngữ đích tự nhiên, đúng văn phong thực tế (vlog, phim ảnh, đời sống, tài liệu...). Tên riêng nhất quán; không bịa thêm thoại.\n   - Nếu đích là Tiếng Việt: dịch thoát ý, tự nhiên, mượt mà, đầy đủ thanh điệu và dấu câu.\n   - Nếu nguồn là tiếng Trung: dịch âm Hán Việt phù hợp bối cảnh, tuyệt đối không để sót chữ Hán.\n   - Nếu nguồn là tiếng Anh / ngôn ngữ phương Tây: dịch trôi chảy, đúng thành ngữ/ngữ cảnh, không dịch thô word-by-word.\n   - Nếu nguồn là tiếng Nhật / Hàn: xưng hô tự nhiên theo ngữ cảnh nhân vật, phiên âm tên chuẩn.\n3. GỘP DÒNG THÔNG MINH (Quan trọng nhất):\n   - Nếu bạn phát hiện các block SRT liên tiếp nhau đang tạo thành một câu hoàn chỉnh, BẮT BUỘC phải gộp chúng lại thành 1 block SRT duy nhất.\n   - Khi gộp, Thời gian Bắt đầu (Start Time) là thời gian của block đầu tiên, và Thời gian Kết thúc (End Time) là thời gian của block cuối cùng trong nhóm được gộp.\n   - Đảm bảo mỗi block SRT đầu ra phải là một câu (hoặc một cụm từ) hoàn chỉnh về mặt ý nghĩa, tuyệt đối không bị đứt đoạn vô lý giữa từ/cụm từ.\n   - Ưu tiên phụ đề dễ đọc (khoảng 1–2 dòng/câu), không nhồi cả đoạn dài vào một cue quá ngắn.\n4. Giữ nguyên chuẩn định dạng SRT:\n   Số thứ tự\n   HH:MM:SS,mmm --> HH:MM:SS,mmm\n   Text\n   (một dòng trống giữa các block). Timestamp chỉ lấy từ phạm vi đầu vào — không tạo mốc ngoài video.\n5. Chỉ trả về nội dung file SRT, không giải thích gì thêm. Không Markdown, không code fence.\n'
_SRT_BLOCK_RE = re.compile('(?ms)^\\s*(?:\\d+\\s*\\n)?\\s*(\\d{2}:\\d{2}:\\d{2}[,.]\\d{3})\\s*-->\\s*(\\d{2}:\\d{2}:\\d{2}[,.]\\d{3})\\s*\\n(.*?)(?=\\n\\s*\\n|\\Z)')

def _cues_as_srt(cues = None):
    """Serialize cues for the LLM without touching the user's original SRT."""
    pass
# WARNING: Decompyle incomplete


def _strip_code_fence(text = None):
    if not text:
        text
    text = ''.strip()
    text = re.sub('^```(?:srt|text|plaintext)?\\s*', '', text, flags = re.IGNORECASE)
    return re.sub('\\s*```$', '', text).strip()


def _clean_cue_text(text = None):
    """Loại bỏ triệt để các tiền tố số thứ tự và ký tự phân cách thừa (ví dụ '1|', '1. 1|', '1: ', '- 1|')."""
    if not text:
        text
    s = ''.strip()
    cleaned = re.sub('^(?:[-*•]\\s*)?\\d+\\s*[|.:)\\-]\\s*', '', s).strip()
    if cleaned == s:
        return s
    s = None
    continue


def _parse_reflow_srt(raw = None, *, source_count):
    '''Parse LLM SRT defensively and reject partial/non-SRT prose.'''
    parsed = []
    for match in _SRT_BLOCK_RE.finditer(_strip_code_fence(raw)):
        
        def parse(value = None):
            (h, m, tail) = value.replace('.', ',').split(':')
            (s, ms) = tail.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        end = parse(match.group(2))
        start = parse(match.group(1))
        text = _clean_cue_text(re.sub('\\s+', ' ', match.group(3)).strip())
        if not text:
            continue
        if not end > start:
            continue
        parsed.append(SrtCue(len(parsed) + 1, start, end, text))
    minimum = max(1, source_count // 16)
    if len(parsed) < minimum:
        raise RuntimeError(f'''AI trả SRT thiếu ({len(parsed)}/{source_count} block hợp lệ).''')
    if len(parsed) > source_count * 2:
        raise RuntimeError('AI trả quá nhiều block SRT, không dùng kết quả không an toàn.')
    stray = _monotonic_outliers(parsed)
    previous_end = 0
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


def _is_quota_error(exc = None):
    '''Lỗi hết quota / bị chặn rate — thử tiếp chỉ làm nặng thêm.'''
    pass
# WARNING: Decompyle incomplete


class ReflowDensityError(RuntimeError):
    '''Cue vượt ngưỡng chữ/giây — bản dịch vẫn phủ đủ timeline.

    Tách khỏi lỗi phủ timeline vì hai loại này cần cách xử lý khác nhau: thiếu
    timeline là câu trả lời hỏng, còn quá dày chỉ là câu nguồn dài hơn chỗ
    trống.  Chế độ natural giao trường hợp sau cho AudioSync bù nhịp.
    '''
    pass


def _monotonic_outliers(cues = None):
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
    tails = None
    tail_at = []
    parent = [
        -1] * len(cues)
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
    if node >= 0:
        keep.add(node)
        node = parent[node]
        if node >= 0:
            continue
    return set(range(len(cues))) - keep


def _timeline_window(cues = None):
    '''(bắt_đầu, kết_thúc, số_cue_lệch) — bỏ qua cue lệch mạch khi đo.'''
    if not cues:
        return (0, 0, 0)
    outliers = _monotonic_outliers(cues)
# WARNING: Decompyle incomplete


def _validate_reflow_coverage(cues = None, source_cues = None, *, natural_voice):
    '''Reject valid-looking but incomplete or unreadably dense LLM SRT.'''
    if not source_cues:
        return None
    (source_start, source_end, stray) = _timeline_window(source_cues)
    if stray:
        logger.warning('SRT nguồn có %d cue lệch thứ tự thời gian; đã bỏ qua khi đo timeline (khoảng dùng để kiểm tra: %.1f-%.1fs)', stray, source_start, source_end)
    (result_start, result_end, _) = _timeline_window(cues)
    if source_end - source_start > 4:
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
            raise ReflowDensityError('AI tạo cue quá dày chữ so với thời lượng; sẽ yêu cầu AI chia/gọn lại.')
        if not natural_voice:
            continue
        if not cue.duration_s < 0.5 and chars / cue.duration_s > 13:
            continue
        logger.warning('Natural voice cue needs attention: %.2fs, %.1f chars/s', cue.duration_s, chars / cue.duration_s)


def _repair_reflow_batch_edges(cues = None, source_cues = None):
    '''Correct small first/last timestamp drift from an otherwise valid LLM SRT.

    Gemini commonly translates every sentence but starts/ends a batch a few
    seconds inside its source window.  Retrying burns quota without improving
    the wording.  We may safely extend only the first/last output cue when the
    drift is modest; a large gap is still rejected by the coverage validator.
    '''
    if not cues or source_cues:
        return cues
    (source_start, source_end, _) = None(source_cues)
    stray = _monotonic_outliers(cues)
# WARNING: Decompyle incomplete


def _reflow_batches(cues = None, *, limit):
    '''Split long jobs only at a likely sentence end, never inside a cue.'''
    batches = []
    start = 0
    if start < len(cues):
        end = min(len(cues), start + limit)
        if end < len(cues):
            lower = max(start + 6, end - 10)
            for index in range(end - 1, lower - 1, -1):
                tail = re.sub('\\s+', '', cues[index].text)
                if not tail.endswith(('。', '！', '？', '!', '?', '…')):
                    continue
                end = index + 1
                range(end - 1, lower - 1, -1)
        batches.append(cues[start:end])
        start = end
        if start < len(cues):
            continue
    return batches


def _request_reflow_batch(cues = None, *, api_key, model, engine, source_lang, target_lang, batch_index, batch_total, natural_voice, cancel_check):
    get_pair_translation_prompt = get_pair_translation_prompt
    normalize_lang_name = normalize_lang_name
    import app.services.language_detector
    src_clean = normalize_lang_name(source_lang)
    tgt_clean = normalize_lang_name(target_lang)
    source_instruction = f'''Ngôn ngữ nguồn là {src_clean}.''' if src_clean != 'Tự nhận diện' else 'Tự nhận diện ngôn ngữ nguồn từ ngữ cảnh phụ đề.'
    guidance = get_pair_translation_prompt(src_clean, tgt_clean)
    user = f'''{source_instruction} Dịch sang {tgt_clean}. Đây là phần {batch_index}/{batch_total} liền mạch của một SRT dài; không bịa text trước/sau phần này. Gộp các block STT bị cắt vụn thành câu hoàn chỉnh (start = block đầu, end = block cuối), rồi chỉ trả về SRT mới.\n\nYÊU CẦU DỊCH THUẬT:\n{guidance}\n\n{_cues_as_srt(cues)}'''
    constraints = '\nBắt buộc: phủ trọn timeline của phần này từ cue đầu tới cue cuối; mỗi cue tối đa 7 giây, tối đa khoảng 18 ký tự/giây. Nếu câu dài, chia ở cụm từ tự nhiên hoặc viết gọn.'
    if natural_voice:
        constraints += '\nCHẾ ĐỘ ĐỒNG BỘ VOICE TỰ NHIÊN: ưu tiên gộp các cue STT liên tiếp bị cắt vụn thành câu hoàn chỉnh; mỗi cue tối thiểu 0.5 giây và tối đa 13 ký tự không tính khoảng trắng/giây. Dịch sang tiếng Việt tự nhiên nhưng cô đọng theo thời lượng, giữ ý quan trọng thay vì dịch từng chữ. Chỉ kéo dài một cue vào khoảng lặng có sẵn, tuyệt đối không chồng timestamp giữa các cue.'
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
        raw = _call_provider(engine, api_key, REFLOW_SYSTEM, user + constraints + retry, model = model, cancel_check = cancel_check)
        result = _parse_reflow_srt(raw, source_count = len(cues))
        if natural_voice:
            result = _repair_reflow_batch_edges(result, cues)
        _validate_reflow_coverage(result, cues, natural_voice = natural_voice)
        
        return range(max_attempts), result
# WARNING: Decompyle incomplete


def translate_cues_reflow(cues = None, *, api_key, model, engine, source_lang, target_lang, natural_voice, report, on_checkpoint, cancel_check):
    '''Repair semantic boundaries; batch long files to prevent truncated output.

    report: nếu truyền vào thì được ghi thêm khóa "degraded"/"batches" để nơi
    gọi báo cho người dùng biết có phần nào phải hạ xuống dịch 1:1 hay không.
    '''
    engine = _provider_name(engine)
    selected = resolve_translation_model(engine, model)
    batches = _reflow_batches(cues, limit = 20 if natural_voice else 12)
    out = []
    previous_end = 0
    degraded = 0
    consumed_source = 0
    for index, batch in enumerate(batches, start = 1):
        if cancel_check and cancel_check():
            logger.info('translate_cues_reflow: cancelled by user before batch %d', index)
            enumerate(batches, start = 1)
        else:
            repaired = _request_reflow_batch(batch, api_key = api_key, model = selected, engine = engine, source_lang = source_lang, target_lang = target_lang, batch_index = index, batch_total = len(batches), natural_voice = natural_voice, cancel_check = cancel_check)
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
            if not on_checkpoint:
                continue
            on_checkpoint(list(out), consumed_source, len(cues))
# WARNING: Decompyle incomplete


def _natural_voice_preflight(cues = None):
    '''Count source cues that cannot reasonably be spoken as-is.

    This is a report, not a rejection: the natural reflow prompt is expected
    to merge or shorten these cues before the TTS phase.
    '''
    too_short = (lambda .0: pass# WARNING: Decompyle incomplete
)(cues())
    too_dense = (lambda .0: pass# WARNING: Decompyle incomplete
)(cues())
    if too_short or too_dense:
        logger.warning('Natural voice preflight: %d cue(s) <0.5s, %d cue(s) >13 chars/s; reflow required', too_short, too_dense)
        return (too_short, too_dense)
    sum.info('Natural voice preflight: source SRT is within basic duration/density limits')
    return (too_short, too_dense)


def _chunk_indices(n = None, chunk_size = None):
    '''[start, end) index ranges.'''
    out = []
    i = 0
    if i < n:
        out.append((i, min(n, i + chunk_size)))
        i += chunk_size
        if i < n:
            continue
    return out


def _http_json(url = None, body = None, *, headers, timeout, retries, retry_on, service, fast_fail_429, cancel_check):
    '''POST JSON với retry/backoff (đặc biệt 429 rate limit) và hỗ trợ ngắt tức thì.'''
    pass
# WARNING: Decompyle incomplete


def _call_gemini(api_key = None, system = None, user = None, *, model, temperature, fast_fail_429, cancel_check):
    model = normalize_gemini_model(model)
    url = f'''https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'''
    generation_config = {
        'maxOutputTokens': 8192 }
    if model.startswith('gemini-2.5'):
        generation_config['temperature'] = temperature
        generation_config['thinkingConfig'] = {
            'thinkingBudget': 0 }
    else:
        generation_config['temperature'] = temperature
    body = {
        'systemInstruction': {
            'parts': [
                {
                    'text': system }] },
        'contents': [
            {
                'role': 'user',
                'parts': [
                    {
                        'text': user }] }],
        'generationConfig': generation_config }
    
    try:
        payload = _http_json(url, body, headers = {
            'Content-Type': 'application/json' }, retries = 3, service = f'''Gemini/{model}''', fast_fail_429 = fast_fail_429, cancel_check = cancel_check)
        if not payload.get('candidates'):
            payload.get('candidates')
        candidates = []
        if not candidates:
            raise RuntimeError(f'''Gemini empty: {payload}''')
        if not candidates[0].get('finishReason'):
            candidates[0].get('finishReason')
        finish = str('').upper()
        if not candidates[0].get('content'):
            candidates[0].get('content')
        if not { }.get('parts'):
            { }.get('parts')
        parts = []
        text = (lambda .0: pass# WARNING: Decompyle incomplete
)(parts()).strip()
        if finish == 'MAX_TOKENS':
            raise RuntimeError('Gemini bị cắt vì chạm giới hạn token đầu ra (finishReason=MAX_TOKENS).\nGiảm số cue mỗi batch hoặc đổi sang model khác.')
        if finish in frozenset({'SAFETY', 'BLOCKLIST', 'RECITATION', 'PROHIBITED_CONTENT'}):
            raise RuntimeError(f'''Gemini từ chối nội dung (finishReason={finish}).''')
        if not text:
            if not finish:
                finish
            raise RuntimeError(f'''Gemini returned empty text (finishReason={'không rõ'})''')
        return text
    except Exception:
        exc = None
        err_str = str(exc).casefold()
        if ('thinking' in err_str or '400' in err_str) and 'thinkingconfig' in str(body).casefold():
            body['generationConfig'].pop('thinkingConfig', None)
            body['generationConfig']['temperature'] = temperature
            payload = _http_json(url, body, headers = {
                'Content-Type': 'application/json' }, retries = 2, service = f'''Gemini/{model}''', fast_fail_429 = fast_fail_429, cancel_check = cancel_check)
        else:
            raise 
        exc = None
        del exc
        continue
        exc = None
        del exc



def _call_openai_compatible(api_key = None, system = None, user = None, *, endpoint, engine, model, temperature, fast_fail_429, cancel_check):
    body = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': system },
            {
                'role': 'user',
                'content': user }],
        'temperature': temperature,
        'max_tokens': 4096 }
    if engine == 'Groq':
        if 'gpt-oss' in model or 'compound' in model:
            body['reasoning_effort'] = 'low'
    payload = _http_json(endpoint, body, headers = {
        'Content-Type': 'application/json',
        'Authorization': f'''Bearer {api_key}''' }, retries = 3, service = f'''{engine}/{model}''', fast_fail_429 = fast_fail_429, cancel_check = cancel_check)
    if not payload.get('choices'):
        payload.get('choices')
    choices = []
    if not choices[0] if choices else { }.get('message'):
        choices[0] if choices else { }.get('message')
    if not { }.get('content'):
        { }.get('content')
    content = ''.strip()
    if not content:
        raise RuntimeError(f'''API dịch trả về rỗng: {payload}''')
    return content


def _is_model_failover_error(error = None):
    '''Kiểm tra lỗi liên quan đến model/quota có thể khắc phục bằng cách đổi model trên cùng key.'''
    pass
# WARNING: Decompyle incomplete


def _is_key_failover_error(error = None):
    '''Return whether trying another key of the same provider can help.'''
    pass
# WARNING: Decompyle incomplete


def _call_provider_single(engine = None, api_key = None, system = None, user = None, *, model, fast_fail_429, cancel_check):
    engine = _provider_name(engine)
    selected = resolve_translation_model(engine, model)
    if engine == 'Gemini':
        return _call_gemini(api_key, system, user, model = selected, fast_fail_429 = fast_fail_429, cancel_check = cancel_check)
    if None == 'Groq':
        endpoint = 'https://api.groq.com/openai/v1/chat/completions'
    elif engine == 'OpenAI':
        endpoint = 'https://api.openai.com/v1/chat/completions'
    else:
        endpoint = 'https://api.deepseek.com/chat/completions'
    return _call_openai_compatible(api_key, system, user, endpoint = endpoint, engine = engine, model = selected, fast_fail_429 = fast_fail_429, cancel_check = cancel_check)


def get_candidate_models_for_engine(engine = None, initial_model = None):
    engine = _provider_name(engine)
# WARNING: Decompyle incomplete


def _call_provider(engine = None, api_key = None, system = None, user = None, *, model, status_callback, cancel_check):
    '''Gọi provider dịch thuật với cơ chế xoay vòng siêu tốc:
    1. Ưu tiên xoay ngay sang API key kế tiếp khi gặp rate-limit/quota (HTTP 429) để giữ nguyên model chất lượng cao nhất.
    2. Nếu tất cả các key đều chạm hạn mức cho model hiện tại, mới tự động chuyển sang model tiếp theo.
    3. Nếu gặp lỗi 404/decommissioned, loại bỏ model đó ngay lập tức và chuyển model khác không chờ đợi.
    '''
    pass
# WARNING: Decompyle incomplete


def _parse_numbered_lines(raw = None, expected_n = None):
    """Parse '1|text' or '1. text' or '1) text' và lọc sạch mọi tiền tố đánh số thừa/kép."""
    lines_map = { }
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
# WARNING: Decompyle incomplete


def _is_vietnamese_target(target_lang = None):
    if not target_lang:
        target_lang
    value = ''.strip().casefold()
    return value in frozenset({'tiếng việt', 'vi-vn', 'vi', 'vietnamese'})


def _repair_vietnamese_residuals(cues = None, *, api_key, model, engine, target_lang, source_lang, max_passes, cancel_check):
    '''Dịch lại riêng cue còn chữ Hán, giữ nguyên index và timestamp.'''
    pass
# WARNING: Decompyle incomplete


def _estimated_tokens(text = None):
    '''Cheap conservative token estimate; avoids an extra tokenizer dependency.'''
    if not text:
        text
    return max(1, (len(''.strip()) + 1) // 2) + 12


def _token_batches(cues = None, positions = None, *, max_cues, token_budget):
    '''Group selected cues by estimated token load, never merely by count.'''
    batches = []
    batch = []
    used = 0
    for pos in positions:
        cost = _estimated_tokens(cues[pos].text)
        if batch:
            if len(batch) >= max_cues or used + cost > token_budget:
                batches.append(batch)
                used = 0
                batch = []
        batch.append(pos)
        used += cost
    if batch:
        batches.append(batch)
    return batches


def _glossary_instruction(glossary = None):
    if not glossary:
        return ''
    lines = []
    for source, target in list(glossary.items())[:80]:
        line = f'''{source} => {target}'''
        if (lambda .0: pass# WARNING: Decompyle incomplete
)(lines()) + len(line) > 3500:
            sum
        else:
            lines.append(line)
    if not lines:
        return ''
    return '\n\nTỪ ĐIỂN TÊN RIÊNG BẮT BUỘC (giữ đúng bản dịch sau dấu =>):\n' + '\n'.join(lines)


def _batch_quality(cues = None, translated_texts = None, positions = None, *, target_lang, source_lang):
    '''Return retryable unresolved cue positions and dense cue warning positions.'''
    retryable = []
    dense = []
    for pos in positions:
        if not translated_texts[pos]:
            translated_texts[pos]
        text = ''.strip()
        if text or looks_untranslated(text, target_lang = target_lang, source_lang = source_lang):
            retryable.append(pos)
            continue
        duration = max(0.1, cues[pos].end_s - cues[pos].start_s)
        if not len(text) / duration > 22:
            continue
        dense.append(pos)
    return (retryable, dense)


def _repair_batch_quality(cues = None, translated_texts = None, positions = None, *, api_key, model, engine, target_lang, source_lang, glossary, status_callback, cancel_check):
    '''One targeted retry for empty/source-script residue from a just-finished batch.'''
    pass
# WARNING: Decompyle incomplete


def translate_cues(cues = None, *, api_key, model, engine, source_lang, target_lang, chunk_size, repair_residual, positions, on_checkpoint, glossary, quality_report, status_callback, cancel_check):
    '''Translate selected cues and optionally expose a durable batch checkpoint.

    ``positions`` keeps already translated cues untouched.  This is the core of
    resume: a later run may use another provider/model and submit only text
    which still looks untranslated.  ``on_checkpoint`` receives a full SRT
    snapshot with partial progress and may be called multiple times.
    '''
    pass
# WARNING: Decompyle incomplete


def _translation_sidecar_paths(out_path = None):
    '''Return persistent progress and append-only batch log paths for an SRT.'''
    return (out_path.with_suffix(out_path.suffix + '.progress.json'), out_path.with_suffix(out_path.suffix + '.translation.jsonl'))


def _persist_translation_checkpoint(snapshot = None, *, out_path, progress_path, log_path, source_path, engine, model, target_lang, source_lang, initial_pending, last_source_cue, status, note, quality_report):
    '''Save the usable SRT first, then a machine-readable resume checkpoint.

    The SRT is intentionally complete at every checkpoint: translated cue(s)
    followed by untouched ones.  Therefore it stays editable and can be used as
    the input of the next run after the user changes provider or model.
    '''
    pass
# WARNING: Decompyle incomplete


def translate_srt_file(srt_path = None, out_path = None, *, api_key, model, engine, source_lang, target_lang, reflow, natural_voice, progress_callback, status_callback, cancel_check):
    '''Translate with durable batch checkpoints and provider-agnostic resume.

    If quota/network fails, the return value is ``ok=False`` *but* ``srt_path``
    points to a usable partially translated SRT.  Calling this again with that
    path and a different engine/model only sends cue(s) that still look
    untranslated.
    '''
    pass
# WARNING: Decompyle incomplete


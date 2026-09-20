# Source Generated with Decompyle++
# File: language_detector.pyc (Python 3.12)

'''
Bộ nhận diện ngôn ngữ tự động (Language Detector) và kiểm tra câu chưa dịch (Untranslated Cue Validator).
Hỗ trợ toàn bộ 9 ngôn ngữ:
- Tiếng Việt
- English
- 中文 (Chinese)
- ไทย (Thai)
- 日本語 (Japanese)
- 한국어 (Korean)
- Español (Spanish)
- Français (French)
- Deutsch (German)
'''
from __future__ import annotations
import re
from typing import Sequence
from app.services.srt_utils import SrtCue
RE_HAN = re.compile('[\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff]')
RE_KANA = re.compile('[\\u3040-\\u309f\\u30a0-\\u30ff]')
RE_HANGUL = re.compile('[\\u1100-\\u11ff\\u3130-\\u318f\\uac00-\\ud7af]')
RE_THAI = re.compile('[\\u0e00-\\u0e7f]')
RE_VN_DIACRITICS = re.compile('[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]')
RE_DE_SPECIAL = re.compile('[äöüßÄÖÜẞ]')
RE_FR_SPECIAL = re.compile('[çœæÇŒÆ]')
RE_ES_SPECIAL = re.compile('[ñÑ¿¡]')
WORDS_EN = {
    'a',
    'am',
    'an',
    'as',
    'at',
    'be',
    'by',
    'do',
    'go',
    'he',
    'if',
    'in',
    'is',
    'it',
    'me',
    'my',
    'no',
    'of',
    'on',
    'or',
    'so',
    'to',
    'up',
    'us',
    'we',
    'all',
    'and',
    'any',
    'are',
    'but',
    'can',
    'did',
    'few',
    'for',
    'get',
    'had',
    'has',
    'her',
    'him',
    'his',
    'how',
    'its',
    'may',
    'new',
    'nor',
    'not',
    'now',
    'off',
    'one',
    'our',
    'out',
    'own',
    'see',
    'she',
    'the',
    'too',
    'two',
    'use',
    'was',
    'way',
    'who',
    'why',
    'you',
    'also',
    'back',
    'been',
    'both',
    'does',
    'down',
    'each',
    'even',
    'from',
    'give',
    'good',
    'have',
    'here',
    'hers',
    'into',
    'just',
    'know',
    'like',
    'look',
    'make',
    'many',
    'more',
    'most',
    'much',
    'must',
    'once',
    'only',
    'ours',
    'over',
    'same',
    'some',
    'such',
    'take',
    'than',
    'that',
    'them',
    'then',
    'they',
    'this',
    'time',
    'used',
    'very',
    'want',
    'well',
    'were',
    'what',
    'when',
    'whom',
    'will',
    'with',
    'work',
    'year',
    'your',
    'about',
    'above',
    'after',
    'again',
    'being',
    'below',
    'could',
    'doing',
    'every',
    'first',
    'might',
    'other',
    'shall',
    'their',
    'there',
    'these',
    'thing',
    'think',
    'those',
    'under',
    'until',
    'where',
    'which',
    'while',
    'would',
    'yours',
    'around',
    'before',
    'during',
    'having',
    'itself',
    'myself',
    'people',
    'should',
    'theirs',
    'against',
    'because',
    'between',
    'further',
    'herself',
    'himself',
    'through',
    'without',
    'yourself',
    'ourselves',
    'themselves',
    'yourselves'}
WORDS_VN = {
    'bà',
    'có',
    'gì',
    'là',
    'mà',
    'nó',
    'và',
    'ăn',
    'đi',
    'ở',
    'các',
    'hãy',
    'họ',
    'làm',
    'lên',
    'như',
    'nào',
    'này',
    'nói',
    'sẽ',
    'thì',
    'tôi',
    'từ',
    'về',
    'ông',
    'đã',
    'bạn',
    'chỉ',
    'cùng',
    'cũng',
    'của',
    'luôn',
    'lại',
    'một',
    'nữa',
    'rất',
    'rồi',
    'thế',
    'tại',
    'vẫn',
    'với',
    'đang',
    'đâu',
    'để',
    'biết',
    'chúng',
    'không',
    'muốn',
    'nhưng',
    'phải',
    'thấy',
    'uống',
    'đến',
    'nhiều',
    'những',
    'xuống',
    'người',
    'được',
    'em',
    'ra',
    'anh',
    'cho',
    'hay',
    'khi',
    'chua',
    'cung',
    'duoc',
    'giua',
    'hoac',
    'khac',
    'minh',
    'ngay',
    'nuoc',
    'phim',
    'quen',
    'sinh',
    'theo',
    'thoi',
    'vien',
    'xung',
    'chieu',
    'chung',
    'duong',
    'hoang',
    'huong',
    'khong',
    'luong',
    'ngang',
    'nguoi',
    'nhanh',
    'nhieu',
    'nhung',
    'quanh',
    'thang',
    'thanh',
    'tieng',
    'trang',
    'trieu',
    'trong',
    'truoc',
    'chuyen',
    'khoang',
    'nghiem',
    'nguyen',
    'phuong',
    'thuong',
    'truong',
    'truyen'}
WORDS_VN_UNACCENTED_DISTINCT = {
    'canh',
    'chua',
    'cung',
    'duoc',
    'giua',
    'hoac',
    'khac',
    'minh',
    'nuoc',
    'phim',
    'quen',
    'sinh',
    'thoi',
    'vien',
    'xung',
    'chieu',
    'chung',
    'duong',
    'hoang',
    'huong',
    'khong',
    'luong',
    'ngang',
    'nguoi',
    'nhanh',
    'nhieu',
    'nhung',
    'quanh',
    'thang',
    'thanh',
    'tieng',
    'trang',
    'trieu',
    'trong',
    'truoc',
    'chuyen',
    'khoang',
    'nghiem',
    'nguyen',
    'phuong',
    'thuong',
    'truong',
    'truyen'}
WORDS_ES = {
    'mí',
    'más',
    'qué',
    'está',
    'también',
    'o',
    'al',
    'de',
    'el',
    'en',
    'ha',
    'la',
    'le',
    'lo',
    'me',
    'ni',
    'se',
    'si',
    'su',
    'un',
    'ya',
    'yo',
    'con',
    'del',
    'ese',
    'eso',
    'fue',
    'hay',
    'las',
    'les',
    'los',
    'muy',
    'nos',
    'por',
    'que',
    'ser',
    'sin',
    'son',
    'sus',
    'una',
    'uno',
    'ante',
    'como',
    'esta',
    'este',
    'esto',
    'para',
    'pero',
    'unos',
    'antes',
    'desde',
    'donde',
    'ellos',
    'entre',
    'hasta',
    'otros',
    'quien',
    'sobre',
    'tiene',
    'todos',
    'contra',
    'porque',
    'quando',
    'algunos',
    'durante'}
WORDS_FR = {
    'même',
    'très',
    'été',
    'après',
    'au',
    'ce',
    'de',
    'du',
    'en',
    'et',
    'la',
    'le',
    'ne',
    'on',
    'ou',
    'sa',
    'se',
    'si',
    'un',
    'aux',
    'ces',
    'des',
    'est',
    'ils',
    'les',
    'lui',
    'par',
    'pas',
    'que',
    'qui',
    'ses',
    'son',
    'sur',
    'une',
    'avec',
    'bien',
    'dans',
    'deux',
    'fait',
    'leur',
    'mais',
    'nous',
    'peut',
    'plus',
    'pour',
    'sans',
    'sont',
    'tous',
    'tout',
    'vous',
    'aussi',
    'autre',
    'cette',
    'comme',
    'elles',
    'faire',
    'temps'}
WORDS_DE = {
    'für',
    'über',
    'an',
    'er',
    'es',
    'im',
    'in',
    'so',
    'um',
    'zu',
    'als',
    'auf',
    'aus',
    'bei',
    'das',
    'dem',
    'den',
    'der',
    'des',
    'die',
    'ein',
    'hat',
    'ich',
    'ihm',
    'ist',
    'man',
    'mir',
    'mit',
    'nur',
    'sie',
    'und',
    'von',
    'war',
    'was',
    'wie',
    'wir',
    'zur',
    'aber',
    'auch',
    'dass',
    'eine',
    'nach',
    'noch',
    'oder',
    'sein',
    'sich',
    'sind',
    'wenn',
    'wird',
    'diese',
    'durch',
    'einen',
    'einer',
    'haben',
    'nicht',
    'welche',
    'werden'}

def normalize_lang_name(name = None):
    '''Chuẩn hóa tên ngôn ngữ về tên chuẩn trong danh sách TRANSLATE_LANGUAGES.'''
    if not name:
        name
    s = ''.strip()
    if s or s in ('Tự nhận diện', 'auto', 'auto-detect'):
        return 'Tự nhận diện'
    low = s.casefold()
    if 'việt' in low or low in ('vi', 'vietnamese'):
        return 'Tiếng Việt'
    if 'eng' in low or low in ('en', 'english'):
        return 'English'
    if 'trung' in low and 'chinese' in low and '中文' in s or low in ('zh', 'zh-cn', 'zh-tw'):
        return '中文 (Chinese)'
    if 'thai' in low and 'ไทย' in s or low in ('th',):
        return 'ไทย (Thai)'
    if 'nhật' in low and 'japan' in low and '日本語' in s or low in ('ja',):
        return '日本語 (Japanese)'
    if 'hàn' in low and 'korean' in low and '한국어' in s or low in ('ko',):
        return '한국어 (Korean)'
    if 'tây ban nha' in low and 'spanish' in low and 'español' in low or low in ('es',):
        return 'Español (Spanish)'
    if 'pháp' in low and 'french' in low and 'français' in low or low in ('fr',):
        return 'Français (French)'
    if 'đức' in low and 'german' in low and 'deutsch' in low or low in ('de',):
        return 'Deutsch (German)'
    return s


def detect_language(text = None):
    '''Nhận diện ngôn ngữ từ đoạn văn bản và trả về (tên_ngôn_ngữ, độ_tin_cậy 0.0 - 1.0).'''
    if not text:
        text
    s = ''.strip()
    if not s:
        return ('Tự nhận diện', 0)
    if RE_THAI.search(s):
        return ('ไทย (Thai)', 0.99)
    if RE_HANGUL.search(s):
        return ('한국어 (Korean)', 0.99)
    if RE_KANA.search(s):
        return ('日本語 (Japanese)', 0.99)
    if RE_HAN.search(s):
        return ('中文 (Chinese)', 0.99)
    words = set(re.findall('\\b[a-zA-ZàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐäöüßéèêëàâîïôùûüçñ]+\\b', s.lower()))
    vn_chars = len(RE_VN_DIACRITICS.findall(s))
    vn_matches = len(words & WORDS_VN)
    vn_score = vn_chars * 3 + vn_matches * 2
    de_chars = len(RE_DE_SPECIAL.findall(s))
    de_matches = len(words & WORDS_DE)
    de_score = de_chars * 4 + de_matches * 2
    fr_chars = len(RE_FR_SPECIAL.findall(s))
    fr_matches = len(words & WORDS_FR)
    fr_score = fr_chars * 4 + fr_matches * 2
    es_chars = len(RE_ES_SPECIAL.findall(s))
    es_matches = len(words & WORDS_ES)
    es_score = es_chars * 4 + es_matches * 2
    en_matches = len(words & WORDS_EN)
    en_score = en_matches * 2
    scores = {
        'Tiếng Việt': vn_score,
        'Deutsch (German)': de_score,
        'Français (French)': fr_score,
        'Español (Spanish)': es_score,
        'English': en_score }
    (best_lang, best_score) = max(scores.items(), key = (lambda item: item[1]))
    if best_score >= 2:
        confidence = min(1, 0.5 + best_score / 20)
        return (best_lang, confidence)
    if None.search('[a-zA-Z]', s):
        return ('English', 0.6)
    return ('Tự nhận diện', 0)


def detect_srt_language(cues = None, sample_size = None):
    '''Quét mẫu các dòng SRT để nhận diện ngôn ngữ chính xác của toàn bộ file.'''
    if not cues:
        return 'Tự nhận diện'
    samples = []
    for c in cues:
        if not c.text:
            c.text
        txt = ''.strip()
        if len(txt) >= 2:
            samples.append(txt)
        if not len(samples) >= sample_size:
            continue
        cues
    if not samples:
        return 'Tự nhận diện'
    combined = '\n'.join(samples)
    (lang, _) = detect_language(combined)
    return lang


def is_untranslated_cue(text = None, *, target_lang, source_lang):
    '''Xác định chính xác xem câu này đã được dịch sang target_lang hay chưa.'''
    if not text:
        text
    s = ''.strip()
    if not s:
        return True
    target = normalize_lang_name(target_lang)
    source = normalize_lang_name(source_lang) if source_lang else None
    if target == 'Tiếng Việt':
        if RE_HAN.search(s) and RE_KANA.search(s) and RE_HANGUL.search(s) or RE_THAI.search(s):
            return True
        if RE_DE_SPECIAL.search(s) and RE_ES_SPECIAL.search(s) or RE_FR_SPECIAL.search(s):
            return True
        if RE_VN_DIACRITICS.search(s):
            return False
        words = set(re.findall('\\b[a-zA-Z]+\\b', s.lower()))
        if not words:
            return False
        if words & WORDS_VN_UNACCENTED_DISTINCT:
            return False
        if source in ('中文 (Chinese)', '日本語 (Japanese)', '한국어 (Korean)', 'ไทย (Thai)'):
            en_hits = words & WORDS_EN
            if len(en_hits) >= max(2, len(words) // 2):
                return True
            return False
        en_hits = words & WORDS_EN
        if en_hits:
            return True
        if len(words) <= 2:
            return False
        (detected, conf) = detect_language(s)
        if detected in ('English', 'Deutsch (German)', 'Français (French)', 'Español (Spanish)') and conf >= 0.75:
            return True
        return False
    if target == 'English':
        if RE_HAN.search(s) and RE_KANA.search(s) and RE_HANGUL.search(s) and RE_THAI.search(s) or RE_VN_DIACRITICS.search(s):
            return True
        if RE_DE_SPECIAL.search(s) and RE_ES_SPECIAL.search(s) or RE_FR_SPECIAL.search(s):
            return True
        words = set(re.findall('\\b[a-zA-Z]+\\b', s.lower()))
        if not words:
            return False
        if words & WORDS_EN:
            return False
        if words & WORDS_VN_UNACCENTED_DISTINCT:
            return True
        (detected, conf) = detect_language(s)
        if detected == 'English' and conf >= 0.5:
            return False
        if detected in ('Tiếng Việt', 'Deutsch (German)', 'Français (French)', 'Español (Spanish)') and conf >= 0.7:
            return True
        return False
    if target == '中文 (Chinese)':
        if not RE_HAN.search(s):
            return True
        if RE_VN_DIACRITICS.search(s) and RE_KANA.search(s) and RE_HANGUL.search(s) or RE_THAI.search(s):
            return True
        return False
    if target == '日本語 (Japanese)':
        if not RE_KANA.search(s) and RE_HAN.search(s):
            return True
        if RE_VN_DIACRITICS.search(s) and RE_HANGUL.search(s) or RE_THAI.search(s):
            return True
        return False
    if target == '한국어 (Korean)':
        if not RE_HANGUL.search(s):
            return True
        if RE_VN_DIACRITICS.search(s) and RE_KANA.search(s) or RE_THAI.search(s):
            return True
        return False
    if target == 'ไทย (Thai)':
        if not RE_THAI.search(s):
            return True
        if RE_VN_DIACRITICS.search(s) and RE_HAN.search(s) and RE_KANA.search(s) or RE_HANGUL.search(s):
            return True
        return False
    if RE_HAN.search(s) and RE_KANA.search(s) and RE_HANGUL.search(s) and RE_THAI.search(s) or RE_VN_DIACRITICS.search(s):
        return True
    (detected, _) = detect_language(s)
    if detected == target:
        return False
    words = set(re.findall('\\b[a-zA-Z]+\\b', s.lower()))
    if target == 'Deutsch (German)':
        if words & WORDS_DE or RE_DE_SPECIAL.search(s):
            return False
    if target == 'Français (French)':
        if words & WORDS_FR or RE_FR_SPECIAL.search(s):
            return False
    if target == 'Español (Spanish)':
        if words & WORDS_ES or RE_ES_SPECIAL.search(s):
            return False
    return False


def get_pair_translation_prompt(source_lang = None, target_lang = None):
    '''Tạo chỉ dẫn dịch thuật chuyên biệt, chuẩn văn phong cho từng cặp ngôn ngữ.'''
    src = normalize_lang_name(source_lang)
    tgt = normalize_lang_name(target_lang)
    rules = [
        f'''• Dịch chuẩn xác, tự nhiên từ {src if src != 'Tự nhận diện' else 'ngôn ngữ nguồn'} sang {tgt}.''',
        '• Văn phong mượt mà, phù hợp ngữ cảnh đàm thoại/video, không dịch thô máy móc word-by-word.',
        '• Giữ nguyên cấu trúc dòng và timestamp phụ đề.']
    if tgt == 'Tiếng Việt':
        if src == '中文 (Chinese)':
            rules.append('• Nguồn là Tiếng Trung: Tự động ghép các chữ Hán bị chèn khoảng trắng rời rạc (nếu có). Tên riêng, địa danh, kỹ năng dịch sang âm Hán Việt tự nhiên và nhất quán. Tuyệt đối không để sót chữ Hán.')
        elif src == 'English':
            rules.append('• Nguồn là Tiếng Anh: Dịch thành câu tiếng Việt trôi chảy, hiện đại, thoát ý. Các thuật ngữ quốc tế phổ biến (AI, App, Tool, CEO, Marketing...) có thể giữ nguyên nếu tự nhiên hơn.')
        elif src in ('日本語 (Japanese)', '한국어 (Korean)'):
            rules.append(f'''• Nguồn là {src}: Chuyển ngữ tự nhiên sang tiếng Việt, xưng hô phù hợp với quan hệ nhân vật, phiên âm tên riêng Latin hoặc âm chuẩn thông dụng.''')
        else:
            rules.append('• Đảm bảo bản dịch tiếng Việt đầy đủ dấu câu và thanh điệu, tự nhiên và dễ đọc.')
    elif tgt == 'English':
        rules.append('• Dịch sang tiếng Anh tự nhiên, chuẩn ngữ pháp bản xứ (Native English), từ vựng phong phú, trôi chảy, không dịch thô.')
    elif tgt == '中文 (Chinese)':
        rules.append('• Dịch sang tiếng Trung Giản thể (Simplified Chinese) tự nhiên, văn phong hiện đại, đúng ngữ pháp và khẩu ngữ thông dụng.')
    elif tgt == '한국어 (Korean)':
        rules.append('• Dịch sang tiếng Hàn (Hangul) tự nhiên, dùng kính ngữ chuẩn mực (존댓말) phù hợp với ngữ cảnh video và đàm thoại.')
    elif tgt == '日本語 (Japanese)':
        rules.append('• Dịch sang tiếng Nhật tự nhiên (kết hợp Kanji và Kana), hành văn mượt mà, phù hợp với phong cách phụ đề video.')
    return '\n'.join(rules)


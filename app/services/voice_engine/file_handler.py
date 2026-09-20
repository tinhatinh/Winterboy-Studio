# Source Generated with Decompyle++
# File: file_handler.pyc (Python 3.12)

import os
import re

def _read_file_text(file_path = None):
    '''
    Đọc nội dung file với cơ chế thử nhiều bảng mã (fallback):
    utf-8-sig (xử lý BOM tự động), utf-8, cp1252, latin-1.
    '''
    encodings = [
        'utf-8-sig',
        'utf-8',
        'cp1252',
        'latin-1']
    for enc in encodings:
        f = open(file_path, 'r', encoding = enc)
        None(None, None)
        
        return encodings, f.read(), 
    None(None, None)
    return 
    with None:
        if not open(file_path, 'r', encoding = 'utf-8', errors = 'replace'), f.read():
            pass
    continue


def clean_sub_text(text = None):
    '''
    Xóa bỏ các thẻ định dạng phụ đề HTML (<i>, <b>, <font...>),
    các mã ASS/SSA ({...}) và chuẩn hóa khoảng trắng.
    '''
    text = re.sub('<[^>]+>', '', text)
    text = re.sub('\\{[^}]+\\}', '', text)
    text = re.sub('\\s+', ' ', text).strip()
    return text


def parse_txt(file_path = None):
    '''
    Đọc .txt: mỗi dòng thành một đoạn nói.
    Trả về list các dict: {"text": ..., "timing": None, "id": i}
    '''
    content = _read_file_text(file_path)
# WARNING: Decompyle incomplete


def parse_srt(file_path_or_content = None):
    '''
    Đọc file phụ đề .srt hoặc chuỗi text SRT trực tiếp:
    - Hỗ trợ cả timestamp dùng dấu phẩy (00:00:01,200) hoặc dấu chấm (00:00:01.200)
    - Tự động bỏ BOM, xử lý xuống dòng Windows (CRLF) và Unix (LF)
    - Làm sạch các thẻ định dạng <i>, <b>, <font>, {\x07n8}, v.v.
    - Ghép nối các dòng text cùng 1 phụ đề thành 1 câu hoàn chỉnh.
    '''
    if '\n' in file_path_or_content or '-->' in file_path_or_content:
        content = file_path_or_content
    elif os.path.isfile(file_path_or_content):
        content = _read_file_text(file_path_or_content)
    else:
        content = file_path_or_content
    normalized = content.replace('\r\n', '\n').replace('\r', '\n').strip()
    blocks = re.split('\\n\\s*\\n', normalized)
    entries = []
# WARNING: Decompyle incomplete


def parse_dgt(file_path = None):
    '''
    Giả định .dgt tương tự .txt (hoặc custom parse nếu có định dạng khác).
    '''
    return parse_txt(file_path)


def load_subtitles(file_path = None):
    '''
    Tự động chọn parser dựa vào extension (.srt, .txt, .dgt).
    '''
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.srt':
        return parse_srt(file_path)
    if None in ('.txt', '.dgt'):
        return parse_txt(file_path)
    
    try:
        entries = parse_srt(file_path)
        if entries:
            return entries
        return parse_txt(file_path)
    except Exception:
        return parse_txt(file_path)



def get_subtitles_stats(entries = None):
    '''
    Tính toán thống kê: tổng số dòng, tổng ký tự, tổng số từ.
    '''
    total_lines = len(entries)
    total_chars = (lambda .0: pass# WARNING: Decompyle incomplete
)(entries())
    total_words = (lambda .0: pass# WARNING: Decompyle incomplete
)(entries())
    return {
        'total_lines': total_lines,
        'total_chars': total_chars,
        'total_words': total_words }


def parse_timestamp_to_seconds(ts_str = None):
    """
    Chuyển chuỗi timestamp định dạng SRT (HH:MM:SS,mmm hoặc HH:MM:SS.mmm hoặc MM:SS,mmm) thành số giây (float).
    Ví dụ: '00:01:23,450' -> 83.45
    """
    if not ts_str:
        return 0
    ts_clean = ts_str.strip().replace(',', '.')
    parts = ts_clean.split(':')
    
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600 + m * 60 + s
        if None(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return m * 60 + s
        return None(parts[0])
    except (ValueError, IndexError):
        return 0



def seconds_to_srt_timestamp(seconds = None):
    """
    Chuyển số giây (float) thành định dạng timestamp SRT: 'HH:MM:SS,mmm'.
    Ví dụ: 83.45 -> '00:01:23,450'
    """
    if seconds < 0:
        seconds = 0
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hours = total_min // 60
    return f'''{hours:02d}:{min_:02d}:{sec:02d},{ms:03d}'''


def save_subtitles_to_srt(entries = None, output_path = None):
    '''
    Lưu danh sách entries thành file định dạng .srt chuẩn UTF-8.
    '''
    lines = []
    for idx, entry in enumerate(entries, 1):
        timing = entry.get('timing')
        if not timing:
            start_s = entry.get('start_s', 0)
            end_s = entry.get('end_s', start_s + 2)
            timing = f'''{seconds_to_srt_timestamp(start_s)} --> {seconds_to_srt_timestamp(end_s)}'''
        text = entry.get('text', '').strip()
        lines.append(str(idx))
        lines.append(timing)
        lines.append(text)
        lines.append('')
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok = True)
    f = open(output_path, 'w', encoding = 'utf-8')
    f.write('\n'.join(lines).strip() + '\n')
    None(None, None)
    return output_path
    with None:
        if not None:
            pass
    return output_path


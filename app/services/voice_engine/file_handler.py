import os
import re

def _read_file_text(file_path: str) -> str:
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
        try:
            with open(file_path, 'r', encoding = enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(file_path, 'r', encoding = 'utf-8', errors = 'replace') as f:
        return f.read()


def clean_sub_text(text: str) -> str:
    '''
    Xóa bỏ các thẻ định dạng phụ đề HTML (<i>, <b>, <font...>),
    các mã ASS/SSA ({...}) và chuẩn hóa khoảng trắng.
    '''
    text = re.sub('<[^>]+>', '', text)
    text = re.sub('\\{[^}]+\\}', '', text)
    text = re.sub('\\s+', ' ', text).strip()
    return text


def parse_txt(file_path: str) -> list[dict]:
    '''
    Đọc .txt: mỗi dòng thành một đoạn nói.
    Trả về list các dict: {"text": ..., "timing": None, "id": i}
    '''
    content = _read_file_text(file_path)
    lines = [ line.strip() for line in content.splitlines() if line.strip() ]
    return [{
        'id': idx,
        'text': line,
        'timing': None } for idx, line in enumerate(lines, 1)]


def parse_srt(file_path_or_content: str) -> list[dict]:
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

    for block in blocks:
        lines = [ l.strip() for l in block.split('\n') if l.strip() ]
        if not lines:
            continue
        # tìm dòng timing trong 3 dòng đầu của block
        time_match = None
        time_line_idx = -1
        for idx, line in enumerate(lines[:3]):
            m = re.search('(\\d{1,2}:\\d{2}:\\d{2}[,\\.]\\d{1,3})\\s*-->\\s*(\\d{1,2}:\\d{2}:\\d{2}[,\\.]\\d{1,3})', line)
            if not m:
                continue
            time_match = m
            time_line_idx = idx
            break
        if time_match and time_line_idx >= 0:
            start_ts = time_match.group(1).replace('.', ',')
            end_ts = time_match.group(2).replace('.', ',')
            timing = f'''{start_ts} --> {end_ts}'''
            # các dòng sau dòng timing là nội dung câu
            text_lines = lines[time_line_idx + 1:]
            raw_text = ' '.join(text_lines)
            cleaned = clean_sub_text(raw_text)
            if not cleaned:
                continue
            entry_num = len(entries) + 1
            entries.append({
                'id': entry_num,
                'text': cleaned,
                'timing': timing,
                'start_ts': start_ts,
                'end_ts': end_ts})
        elif len(lines) == 1 and not lines[0].isdigit():
            cleaned = clean_sub_text(lines[0])
            if cleaned:
                entries.append({
                    'id': len(entries) + 1,
                    'text': cleaned,
                    'timing': None })
    return entries


def parse_dgt(file_path: str) -> list[dict]:
    '''
    Giả định .dgt tương tự .txt (hoặc custom parse nếu có định dạng khác).
    '''
    return parse_txt(file_path)


def load_subtitles(file_path: str) -> list[dict]:
    '''
    Tự động chọn parser dựa vào extension (.srt, .txt, .dgt).
    '''
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.srt':
        return parse_srt(file_path)
    if ext in ('.txt', '.dgt'):
        return parse_txt(file_path)
    # không rõ extension: thử đọc như SRT trước, rỗng/hỏng thì mới coi là TXT
    try:
        entries = parse_srt(file_path)
        if entries:
            return entries
    except Exception:
        pass
    return parse_txt(file_path)


def get_subtitles_stats(entries: list[dict]) -> dict:
    '''
    Tính toán thống kê: tổng số dòng, tổng ký tự, tổng số từ.
    '''
    total_lines = len(entries)
    total_chars = sum(len(e.get('text', '')) for e in entries)
    total_words = sum(len(e.get('text', '').split()) for e in entries)
    return {
        'total_lines': total_lines,
        'total_chars': total_chars,
        'total_words': total_words }


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Chuyển chuỗi timestamp định dạng SRT (HH:MM:SS,mmm hoặc HH:MM:SS.mmm hoặc MM:SS,mmm) thành số giây (float).
    Ví dụ: '00:01:23,450' -> 83.45
    """
    if not ts_str:
        return 0.0
    ts_clean = ts_str.strip().replace(',', '.')
    parts = ts_clean.split(':')
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600.0 + m * 60.0 + s
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return m * 60.0 + s
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


def seconds_to_srt_timestamp(seconds: float) -> str:
    """
    Chuyển số giây (float) thành định dạng timestamp SRT: 'HH:MM:SS,mmm'.
    Ví dụ: 83.45 -> '00:01:23,450'
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hours = total_min // 60
    return f'''{hours:02d}:{min_:02d}:{sec:02d},{ms:03d}'''


def save_subtitles_to_srt(entries: list[dict], output_path: str) -> str:
    '''
    Lưu danh sách entries thành file định dạng .srt chuẩn UTF-8.
    '''
    lines = []
    for idx, entry in enumerate(entries, 1):
        timing = entry.get('timing')
        if not timing:
            start_s = entry.get('start_s', 0.0)
            end_s = entry.get('end_s', start_s + 2.0)
            timing = f'''{seconds_to_srt_timestamp(start_s)} --> {seconds_to_srt_timestamp(end_s)}'''
        text = entry.get('text', '').strip()
        lines.append(str(idx))
        lines.append(timing)
        lines.append(text)
        lines.append('')
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok = True)
    with open(output_path, 'w', encoding = 'utf-8') as f:
        f.write('\n'.join(lines).strip() + '\n')
    return output_path

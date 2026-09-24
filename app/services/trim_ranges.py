'''Chuẩn hóa các khoảng In/Out cho chức năng render nhiều đoạn.'''
from __future__ import annotations
from typing import Any


def parse_timecode(value: Any, default: float | None = None) -> float:
    '''Đổi số giây hoặc ``HH:MM:SS.mmm`` thành giây.

    Dấu phẩy thập phân cũng được chấp nhận để khớp cách ghi thời gian SRT.
    '''
    text = str(value if value is not None else '').strip().replace(',', '.')
    if not text:
        if default is not None:
            return default
        raise ValueError('thời gian đang để trống')
    parts = text.split(':')
    if len(parts) > 3:
        raise ValueError(f'''thời gian không hợp lệ: {text}''')

    try:
        numbers = [float(part.strip()) for part in parts]
    except (TypeError, ValueError) as exc:
        raise ValueError(f'''thời gian không hợp lệ: {text}''') from exc

    if any(number < 0 for number in numbers):
        raise ValueError('thời gian không được âm')
    if len(numbers) == 1:
        return numbers[0]
    if any(number >= 60 for number in numbers[1:]):
        raise ValueError(f'''phút/giây phải nhỏ hơn 60: {text}''')
    if len(numbers) == 2:
        return numbers[0] * 60.0 + numbers[1]
    return numbers[0] * 3600.0 + numbers[1] * 60.0 + numbers[2]


def normalize_trim_segments(
        raw_segments: Any,
        *,
        source_duration: float | None = None,
) -> list[dict[str, Any]]:
    '''Kiểm tra danh sách đoạn, giữ nguyên thứ tự và cho phép chồng lấn.
    
    Hỗ trợ để trống In (mặc định = 0.0) và để trống Out (mặc định = hết video).
    '''
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ValueError('Chưa có đoạn nào để render')
    duration = float(source_duration or 0.0)
    result = []
    for index, raw in enumerate(raw_segments, start = 1):
        if not isinstance(raw, dict):
            raise ValueError(f'''Đoạn {index} không hợp lệ''')

        raw_start = str(raw.get('start') or '').strip()
        raw_end = str(raw.get('end') or '').strip()

        try:
            start = parse_timecode(raw_start, default = 0.0)
        except ValueError as exc:
            raise ValueError(f'''Đoạn {index} (In): {exc}''') from exc

        if not raw_end:
            if duration > 0.0:
                end = duration
            else:
                raise ValueError(f'''Đoạn {index}: Hãy nhập thời điểm kết thúc (Out)''')
        else:
            try:
                end = parse_timecode(raw_end)
            except ValueError as exc:
                raise ValueError(f'''Đoạn {index} (Out): {exc}''') from exc

        if end <= start + 0.04:
            raise ValueError(f'''Đoạn {index}: Điểm Out ({end:.2f}s) phải lớn hơn In ({start:.2f}s)''')
        if duration > 0.0:
            if start >= duration:
                raise ValueError(f'''Đoạn {index}: In nằm ngoài thời lượng video ({duration:.2f}s)''')
            if end > duration + 0.05:
                # vượt quá một frame dung sai: coi như chạm hết video
                end = duration
            end = min(end, duration)
        result.append({
            'start': round(start, 6),
            'end': round(end, 6),
            'name': str(raw.get('name') or f'''Đoạn {index}''').strip() or f'''Đoạn {index}''' })
    return result

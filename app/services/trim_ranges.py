# Source Generated with Decompyle++
# File: trim_ranges.pyc (Python 3.12)

'''Chuẩn hóa các khoảng In/Out cho chức năng render nhiều đoạn.'''
from __future__ import annotations
from typing import Any

def parse_timecode(value = None, default = None):
    '''Đổi số giây hoặc ``HH:MM:SS.mmm`` thành giây.

    Dấu phẩy thập phân cũng được chấp nhận để khớp cách ghi thời gian SRT.
    '''
    pass
# WARNING: Decompyle incomplete


def normalize_trim_segments(raw_segments = None, *, source_duration):
    '''Kiểm tra danh sách đoạn, giữ nguyên thứ tự và cho phép chồng lấn.
    
    Hỗ trợ để trống In (mặc định = 0.0) và để trống Out (mặc định = hết video).
    '''
    if not isinstance(raw_segments, list) or raw_segments:
        raise ValueError('Chưa có đoạn nào để render')
    if not source_duration:
        source_duration
    duration = float(0)
    result = []
    for index, raw in enumerate(raw_segments, start = 1):
        if not isinstance(raw, dict):
            raise ValueError(f'''Đoạn {index} không hợp lệ''')
        if not raw.get('start'):
            raw.get('start')
        raw_start = str('').strip()
        if not raw.get('end'):
            raw.get('end')
        raw_end = str('').strip()
        start = parse_timecode(raw_start, default = 0)
        if not raw_end:
            if duration > 0:
                end = duration
            else:
                raise ValueError(f'''Đoạn {index}: Hãy nhập thời điểm kết thúc (Out)''')
        end = parse_timecode(raw_end)
        if end <= start + 0.04:
            raise ValueError(f'''Đoạn {index}: Điểm Out ({end:.2f}s) phải lớn hơn In ({start:.2f}s)''')
        if duration > 0:
            if start >= duration:
                raise ValueError(f'''Đoạn {index}: In nằm ngoài thời lượng video ({duration:.2f}s)''')
            if end > duration + 0.05:
                end = duration
            end = min(end, duration)
        if not raw.get('name'):
            raw.get('name')
        if not str(f'''Đoạn {index}''').strip():
            str(f'''Đoạn {index}''').strip()
        result.append({
            'start': round(start, 6),
            'end': round(end, 6),
            'name': f'''Đoạn {index}''' })
    return result
    except ValueError:
        exc = None
        raise ValueError(f'''Đoạn {index} (In): {exc}'''), exc
        exc = None
        del exc
    except ValueError:
        exc = None
        raise ValueError(f'''Đoạn {index} (Out): {exc}'''), exc
        exc = None
        del exc


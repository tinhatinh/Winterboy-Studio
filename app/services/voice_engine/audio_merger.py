# Source Generated with Decompyle++
# File: audio_merger.pyc (Python 3.12)

'''
AudioSyncMerger — Bộ công cụ đồng bộ và gộp âm thanh theo Timeline SRT.

Học hỏi kiến trúc từ AudioSyncEngine của Winterboy Studio:
1. Mỗi câu thoại trong SRT có mốc [start_s, end_s] -> D_sub = end_s - start_s.
2. Đo độ dài thực tế D_voice của file MP3 được ElevenLabs tạo ra.
3. Nếu D_voice > D_sub:
   - Tự động tăng tốc bằng FFmpeg atempo (speed_rate = D_voice / D_sub, giới hạn tối đa max_speed_rate).
   - Đảm bảo câu thoại kết thúc đúng trước khi câu tiếp theo bắt đầu.
4. Nếu D_voice <= D_sub:
   - Giữ nguyên tốc độ đọc tự nhiên, chèn thêm khoảng lặng (silence padding) ở đuôi cho tròn D_sub.
5. Lắp ráp Timeline hoàn chỉnh:
   - Chèn khoảng lặng từ 0.00s đến câu đầu tiên.
   - Chèn khoảng lặng vào các khoảng trống (gap) giữa các câu.
   - Dùng FFmpeg Concat Demuxer xuất ra 1 file MP3 đồng bộ hoàn chỉnh 100% với SRT/Video.
'''
import os
import shutil
import subprocess
import tempfile
import logging
from typing import Callable, Optional
from app.services.voice_engine.file_handler import parse_timestamp_to_seconds
logger = logging.getLogger(__name__)

def find_ffmpeg_bin():
    ff = shutil.which('ffmpeg')
    if ff:
        return ff
    common_paths = [
        None.path.expandvars('%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffmpeg.exe'),
        'C:\\ffmpeg\\bin\\ffmpeg.exe']
    for p in common_paths:
        if not os.path.isfile(p):
            continue
        
        return common_paths, p
    raise FileNotFoundError('Không tìm thấy ffmpeg trong hệ thống. Vui lòng cài đặt FFmpeg.')


def find_ffprobe_bin():
    ffp = shutil.which('ffprobe')
    if ffp:
        return ffp
    ff = None.which('ffmpeg')
    if ff:
        cand = os.path.join(os.path.dirname(ff), 'ffprobe.exe')
        if os.path.isfile(cand):
            return cand
        common_paths = [
            None.path.expandvars('%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffprobe.exe'),
            'C:\\ffmpeg\\bin\\ffprobe.exe']
        for p in common_paths:
            if not os.path.isfile(p):
                continue
            
            return common_paths, p
        raise FileNotFoundError('Không tìm thấy ffprobe trong hệ thống.')


def probe_audio_duration(file_path = None):
    '''
    Đo độ dài thực tế của file âm thanh (tính bằng giây) bằng ffprobe.
    '''
    ffprobe = find_ffprobe_bin()
    cmd = [
        ffprobe,
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        file_path]
    
    try:
        p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode == 0 and p.stdout.strip():
            return max(0, float(p.stdout.strip()))
        
        try:
            AudioSegment = AudioSegment
            import pydub
            seg = AudioSegment.from_file(file_path)
            return len(seg) / 1000
            except Exception:
                e = None
                logger.warning('ffprobe error on %s: %s', file_path, e)
                e = None
                del e
                continue
                e = None
                del e
        except Exception:
            return 0




def build_atempo_filters(speed_rate = None):
    '''
    Tạo chuỗi filter atempo cho FFmpeg.
    FFmpeg chỉ chấp nhận giá trị trong khoảng [0.5, 2.0] cho mỗi bộ lọc atempo đơn lẻ.
    Nếu tốc độ cần tăng > 2.0 hoặc < 0.5, ta phân rã thành nhiều bộ lọc atempo nối tiếp.
    '''
    if speed_rate <= 0:
        return 'atempo=1.0'
    factors = []
    r = float(speed_rate)
    if r > 2:
        factors.append(2)
        r /= 2
        if r > 2:
            continue
    if r < 0.5:
        factors.append(0.5)
        r /= 0.5
        if r < 0.5:
            continue
    factors.append(max(0.5, min(2, r)))
    return (lambda .0: pass# WARNING: Decompyle incomplete
)(factors())


class AudioSyncMerger:
    
    def __init__(self = None, sample_rate = None, max_speed_rate = None, min_segment_s = (44100, 1.85, 0.1)):
        self.sample_rate = sample_rate
        self.max_speed_rate = max_speed_rate
        self.min_segment_s = min_segment_s
        self.ffmpeg = find_ffmpeg_bin()
        self.ffprobe = find_ffprobe_bin()

    
    def _run_cmd(self = None, cmd = None):
        p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode != 0:
            if not p.stderr:
                p.stderr
                if not p.stdout:
                    p.stdout
            err = ''[-600:]
            raise RuntimeError(f'''FFmpeg error ({p.returncode}): {err}''')

    
    def make_silence(self = None, output_path = None, duration_s = None):
        '''
        Tạo file âm thanh khoảng lặng (silence) chuẩn sample rate với độ dài duration_s.
        '''
        cmd = [
            self.ffmpeg,
            '-y',
            '-f',
            'lavfi',
            '-i',
            f'''anullsrc=r={self.sample_rate}:cl=stereo''',
            '-t',
            f'''{duration_s:.4f}''',
            '-c:a',
            'pcm_s16le',
            output_path]
        self._run_cmd(cmd)
        return output_path

    
    def fit_segment(self = None, src_path = None, dst_path = None, target_duration = ('src_path', str, 'dst_path', str, 'target_duration', float, 'return', float)):
        '''
        Khớp file âm thanh với khung thời lượng target_duration:
        - Nếu dài hơn: Tự động atempo để câu nói kịp kết thúc trước mốc tiếp theo.
        - Nếu ngắn hơn: Chèn silence ở đuôi (apad).
        '''
        d_voice = probe_audio_duration(src_path)
        if d_voice <= 0:
            d_voice = target_duration
        target_dur = max(self.min_segment_s, target_duration)
        eps = 0.03
        if d_voice > target_dur + eps:
            speed_rate = d_voice / target_dur
            applied_rate = min(speed_rate, self.max_speed_rate)
            filt = build_atempo_filters(applied_rate)
            filt += f''',atrim=0:{target_dur:.4f},apad=whole_dur={target_dur:.4f}'''
            cmd = [
                self.ffmpeg,
                '-y',
                '-i',
                src_path,
                '-filter:a',
                filt,
                '-ar',
                str(self.sample_rate),
                '-ac',
                '2',
                dst_path]
            self._run_cmd(cmd)
            return target_dur
        cmd = [
            None.ffmpeg,
            '-y',
            '-i',
            src_path,
            '-af',
            f'''atrim=0:{target_dur:.4f},apad=whole_dur={target_dur:.4f}''',
            '-ar',
            str(self.sample_rate),
            '-ac',
            '2',
            dst_path]
        self._run_cmd(cmd)
        return target_dur

    
    def merge_voice_with_srt(self = None, entries = None, audio_files = None, output_path = (None,), progress_cb = ('entries', list[dict], 'audio_files', list[Optional[str]], 'output_path', str, 'progress_cb', Optional[Callable[([
        float,
        str], None)]], 'return', dict)):
        '''
        Gộp toàn bộ các đoạn voice thành một file master duy nhất, căn chỉnh timeline khớp 100% SRT.

        Parameters:
        - entries: Danh sách các câu phụ đề đã parse (chứa start_ts, end_ts hoặc timing).
        - audio_files: Danh sách đường dẫn file MP3 tương ứng với từng câu (line_001.mp3,...).
        - output_path: Đường dẫn file MP3 đầu ra hoàn chỉnh.
        - progress_cb: Hàm callback(tiến_độ_0_đến_1, thông_báo) để cập nhật UI.
        '''
        if not entries:
            raise ValueError('Danh sách phụ đề trống.')
        if len(entries) != len(audio_files):
            raise ValueError(f'''Số lượng câu ({len(entries)}) không khớp số lượng file audio ({len(audio_files)}).''')
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok = True)
        temp_dir = tempfile.TemporaryDirectory(prefix = 'mumu_sync_')
        temp_path = temp_dir
        timeline_pieces = []
        cursor = 0
        total_items = len(entries)
        valid_items = []
    # WARNING: Decompyle incomplete



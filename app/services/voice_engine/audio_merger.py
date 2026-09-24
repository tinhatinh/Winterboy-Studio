'''
AudioSyncMerger — Bộ công cụ đồng bộ và gộp âm thanh theo Timeline SRT.

Học hỏi kiến trúc từ AudioSyncEngine của Winterboy studio:
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

def find_ffmpeg_bin() -> str:
    ff = shutil.which('ffmpeg')
    if ff:
        return ff
    common_paths = [
        os.path.expandvars('%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffmpeg.exe'),
        'C:\\ffmpeg\\bin\\ffmpeg.exe']
    for p in common_paths:
        if not os.path.isfile(p):
            continue
        return p
    raise FileNotFoundError('Không tìm thấy ffmpeg trong hệ thống. Vui lòng cài đặt FFmpeg.')


def find_ffprobe_bin() -> str:
    ffp = shutil.which('ffprobe')
    if ffp:
        return ffp
    ff = shutil.which('ffmpeg')
    if ff:
        cand = os.path.join(os.path.dirname(ff), 'ffprobe.exe')
        if os.path.isfile(cand):
            return cand
        common_paths = [
            os.path.expandvars('%LOCALAPPDATA%\\Microsoft\\WinGet\\Links\\ffprobe.exe'),
            'C:\\ffmpeg\\bin\\ffprobe.exe']
        for p in common_paths:
            if not os.path.isfile(p):
                continue
            return p
    raise FileNotFoundError('Không tìm thấy ffprobe trong hệ thống.')


def probe_audio_duration(file_path: str) -> float:
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
            return max(0.0, float(p.stdout.strip()))
    except Exception as e:
        logger.warning('ffprobe error on %s: %s', file_path, e)
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(file_path)
        return len(seg) / 1000.0
    except Exception:
        return 0.0


def build_atempo_filters(speed_rate: float) -> str:
    '''
    Tạo chuỗi filter atempo cho FFmpeg.
    FFmpeg chỉ chấp nhận giá trị trong khoảng [0.5, 2.0] cho mỗi bộ lọc atempo đơn lẻ.
    Nếu tốc độ cần tăng > 2.0 hoặc < 0.5, ta phân rã thành nhiều bộ lọc atempo nối tiếp.
    '''
    if speed_rate <= 0:
        return 'atempo=1.0'
    factors = []
    r = float(speed_rate)
    while r > 2.0:
        factors.append(2.0)
        r /= 2.0
    while r < 0.5:
        factors.append(0.5)
        r /= 0.5
    factors.append(max(0.5, min(2.0, r)))
    return ','.join(f'''atempo={f:.6f}''' for f in factors)


class AudioSyncMerger:

    def __init__(self, sample_rate: int = 44100, max_speed_rate: float = 1.85,
                 min_segment_s: float = 0.1):
        self.sample_rate = sample_rate
        self.max_speed_rate = max_speed_rate
        self.min_segment_s = min_segment_s
        self.ffmpeg = find_ffmpeg_bin()
        self.ffprobe = find_ffprobe_bin()


    def _run_cmd(self, cmd: list[str]) -> None:
        p = subprocess.run(cmd, capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if p.returncode != 0:
            err = (p.stderr or p.stdout or '')[-600:]
            raise RuntimeError(f'''FFmpeg error ({p.returncode}): {err}''')


    def make_silence(self, output_path: str, duration_s: float) -> str:
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


    def fit_segment(self, src_path: str, dst_path: str, target_duration: float) -> float:
        '''
        Khớp file âm thanh với khung thời lượng target_duration:
        - Nếu dài hơn: Tự động atempo để câu nói kịp kết thúc trước mốc tiếp theo.
        - Nếu ngắn hơn: Chèn silence ở đuôi (apad).
        '''
        d_voice = probe_audio_duration(src_path)
        if d_voice <= 0.0:
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
            self.ffmpeg,
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


    def merge_voice_with_srt(self, entries: list[dict], audio_files: list[Optional[str]],
                             output_path: str,
                             progress_cb: Optional[Callable[[float, str], None]] = None) -> dict:
        '''
        Gộp toàn bộ các đoạn voice thành một file master duy nhất, căn chỉnh timeline khớp 100% SRT.

        Parameters:
        - entries: Danh sách các câu phụ đề đã parse (chứa start_ts, end_ts hoặc timing).
        - audio_files: Danh sách đường dẫn file MP3 tương ứng với từng câu (line_001.mp3,...).
        - output_path: Đường dẫn file MP3 đầu ra hoàn chỉnh.
        - progress_cb: Hàm callback(tiến_độ_0_đến_1, thông_báo) để cập nhật UI.
        '''
        # Decompyle++ dừng ở dòng 226 (thân khối `with tempfile.TemporaryDirectory(...)`)
        # nên toàn bộ phần lắp timeline + concat FFmpeg mất theo. Khung đầu vào đã xác minh
        # được từ bytecode nhưng dựng lại phần còn lại là đoán -> để nguyên stub.
        raise NotImplementedError('chưa khôi phục từ bytecode: app.services.voice_engine.audio_merger.merge_voice_with_srt')

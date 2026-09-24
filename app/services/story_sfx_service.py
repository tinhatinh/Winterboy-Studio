# Source Generated with Decompyle++
# File: story_sfx_service.pyc (Python 3.12)

'''Dịch vụ quản lý và chèn âm thanh hiệu ứng SFX & Foleys theo ngữ cảnh (Auto-SFX Engine) cho Winterboy Studio Pro.

Hỗ trợ:
- Thư viện âm thanh offline tích hợp sẵn (libraries/sfx/)
- Thư mục tùy biến người dùng tự thêm (libraries/sfx/custom/)
- Tự động sinh sound pack chuẩn điện ảnh (Whoosh, Impact, Heartbeat, Riser, Thunder, Door, Footsteps, Clock, Glass, Sub Bass)
- Bộ nhận diện ngữ cảnh và hành động thông minh (Context Action Sound Matcher)
- Gán SFX hàng loạt và mở thư mục trong Windows Explorer.
'''
from __future__ import annotations
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)

def get_sfx_root_dir():
    import sys
    candidates = [
        Path(__file__).resolve().parents[2] / 'libraries' / 'sfx',
        Path(__file__).resolve().parents[1] / 'assets' / 'sfx',
        Path.cwd() / 'libraries' / 'sfx']
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = Path(sys._MEIPASS)
        candidates.insert(0, meipass / 'libraries' / 'sfx')
        candidates.insert(1, meipass / 'app' / 'assets' / 'sfx')
    for c in candidates:
        if not c.is_dir():
            continue
        if not any(c.glob('*.wav')):
            continue
        
        return c
    root = Path(__file__).resolve().parents[2]
    sfx_dir = root / 'libraries' / 'sfx'
    sfx_dir.mkdir(parents = True, exist_ok = True)
    return sfx_dir


def get_custom_sfx_dir():
    custom_dir = get_sfx_root_dir() / 'custom'
    custom_dir.mkdir(parents = True, exist_ok = True)
    readme = custom_dir / 'HD_THEM_SFX_CUA_BAN.txt'
    if not readme.is_file():
        
        try:
            readme.write_text('THƯ MỤC CHỨA ÂM THANH HIỆU ỨNG (SFX) TỰ THÊM CỦA BẠN\n---------------------------------------------------\nBạn có thể copy/paste bất kỳ file âm thanh nào (.mp3, .wav, .m4a, .ogg, .aac, .flac) vào thư mục này.\nPhần mềm Winterboy Studio Pro sẽ tự động nhận diện và hiển thị trong danh sách chọn SFX của từng phân cảnh.\n', encoding = 'utf-8')
            return custom_dir
            return custom_dir
        except Exception:
            return custom_dir



def _ffmpeg_bin():
    
    try:
        get_ffmpeg_path = get_ffmpeg_path
        import app.services.ffmpeg_utils
        return get_ffmpeg_path()
    except Exception:
        return 'ffmpeg'



def _hidden_kwargs():
    kw = { }
    if os.name == 'nt':
        kw['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kw


def ensure_default_sfx_pack():
    '''Tạo bộ âm thanh hiệu ứng điện ảnh tích hợp sẵn chất lượng cao bằng FFmpeg audio synthesis
    nếu thư mục libraries/sfx chưa có file.
    '''
    sfx_dir = get_sfx_root_dir()
    ffmpeg = _ffmpeg_bin()
    sound_specs = [
        ('whoosh_fast.wav', 'anoisesrc=d=0.75:c=white:r=44100', [
            'bandpass=f=1400:w=1000,volume=3.2,afade=t=in:ss=0:d=0.2,afade=t=out:st=0.35:d=0.4']),
        ('cinematic_impact.wav', 'aevalsrc=sin(2*PI*55*exp(-t*8))*exp(-t*4):d=1.5:s=44100', [
            'lowpass=f=400,volume=4.0,afade=t=out:st=0.3:d=1.2']),
        ('sub_bass_drop.wav', 'aevalsrc=sin(2*PI*45*(1-t/2.2))*exp(-t*1.5):d=2.2:s=44100', [
            'lowpass=f=120,volume=4.5,afade=t=out:st=0.5:d=1.7']),
        ('heartbeat_suspense.wav', 'aevalsrc=(sin(2*PI*52*t)*exp(-mod(t\\,0.85)*16) + 0.7*sin(2*PI*48*(t-0.2))*exp(-max(0\\,mod(t\\,0.85)-0.2)*18)):d=2.6:s=44100', [
            'lowpass=f=160,volume=5.0,afade=t=out:st=1.8:d=0.8']),
        ('tension_riser.wav', 'aevalsrc=sin(2*PI*(150 + 400*t*t)*t)*exp(t*0.5):d=2.5:s=44100', [
            'bandpass=f=800:w=600,volume=2.8,afade=t=in:ss=0:d=0.8,afade=t=out:st=2.1:d=0.4']),
        ('thunder_storm.wav', 'anoisesrc=d=3.0:c=pink:r=44100', [
            'lowpass=f=220,tremolo=f=4.0:d=0.7,volume=4.2,afade=t=in:ss=0:d=0.3,afade=t=out:st=1.5:d=1.5']),
        ('clock_tick.wav', 'aevalsrc=sin(2*PI*1800*t)*exp(-mod(t\\,0.5)*70):d=2.0:s=44100', [
            'highpass=f=1000,volume=3.5,afade=t=out:st=1.5:d=0.5']),
        ('door_creak.wav', 'aevalsrc=sin(2*PI*(220+sin(2*PI*6*t)*80)*t)*exp(-t*0.8):d=1.8:s=44100', [
            'bandpass=f=350:w=200,volume=3.0,afade=t=in:ss=0:d=0.2,afade=t=out:st=1.0:d=0.8']),
        ('footsteps.wav', 'aevalsrc=sin(2*PI*120*t)*exp(-mod(t\\,0.6)*40):d=2.4:s=44100', [
            'bandpass=f=180:w=120,volume=4.0,afade=t=out:st=1.8:d=0.6']),
        ('glass_shatter.wav', 'anoisesrc=d=1.2:c=white:r=44100', [
            'highpass=f=3500,volume=3.8,afade=t=in:ss=0:d=0.05,afade=t=out:st=0.2:d=1.0']),
        ('chime_bell.wav', 'aevalsrc=(sin(2*PI*880*t) + 0.5*sin(2*PI*1760*t))*exp(-t*2.5):d=1.6:s=44100', [
            'highpass=f=600,volume=2.5,afade=t=out:st=0.5:d=1.1']),
        ('ambient_drone.wav', 'aevalsrc=(sin(2*PI*65*t) + 0.4*sin(2*PI*98*t) + 0.3*sin(2*PI*131*t)):d=3.0:s=44100', [
            'lowpass=f=250,volume=2.2,afade=t=in:ss=0:d=0.6,afade=t=out:st=2.2:d=0.8'])]
# WARNING: Decompyle incomplete

BUILTIN_SFX_NAMES: 'dict[str, str]' = {
    'whoosh_fast.wav': '⚡ Lướt Nhanh / Chuyển Cảnh (Whoosh)',
    'cinematic_impact.wav': '💥 Cú Đấm / Va Đập Điện Ảnh (Impact Hit)',
    'sub_bass_drop.wav': '🌌 Sub Bass Rền Sâu (Sub Drop)',
    'heartbeat_suspense.wav': '💓 Tim Đập Dồn Dập (Heartbeat)',
    'tension_riser.wav': '📈 Kịch Tính Căng Thẳng (Tension Riser)',
    'thunder_storm.wav': '⛈️ Sấm Sét & Mưa Bão (Thunder Storm)',
    'clock_tick.wav': '⏱️ Đồng Hồ Tích Tắc (Clock Ticking)',
    'door_creak.wav': '🚪 Cánh Cửa Cót Két (Door Creak)',
    'footsteps.wav': '👣 Tiếng Bước Chân (Footsteps)',
    'glass_shatter.wav': '🔨 Rơi Vỡ / Kính Vỡ (Glass Break)',
    'chime_bell.wav': '🔔 Chuông Ngân / Nhận Thức (Chime Bell)',
    'ambient_drone.wav': '🌫️ Không Khí Bí Ẩn / U Ám (Mystery Drone)' }
_SFX_CACHE: 'list[tuple[str, str]] | None' = None

def get_available_sfx(force_refresh = None):
    '''Trả về danh sách tất cả các hiệu ứng âm thanh SFX khả dụng (có cache in-memory):
    [("Không Dùng SFX", ""), ("⚡ Lướt Nhanh (Whoosh)", "path/to/file.wav"), ...]
    Gồm cả sound pack tích hợp và file custom do người dùng thêm vào.
    '''
    pass
# WARNING: Decompyle incomplete


def open_custom_sfx_folder():
    '''Mở thư mục libraries/sfx/custom trong Windows Explorer để người dùng thả file âm thanh vào.'''
    global _SFX_CACHE
    _SFX_CACHE = None
    custom_dir = get_custom_sfx_dir()
    
    try:
        if os.name == 'nt':
            os.startfile(str(custom_dir))
            return custom_dir
        subprocess.run([
            'xdg-open',
            str(custom_dir)])
    except Exception as exc:
        logger.warning('Không thể mở thư mục SFX: %s', exc)
    return custom_dir


SFX_KEYWORD_RULES: 'list[dict[str, Any]]' = [
    {
        'file': 'thunder_storm.wav',
        'volume': 0.2,
        'offset': 0,
        'keywords': [
            'sấm sét',
            'sấm rền',
            'tia chớp',
            'bão tố',
            'giông bão',
            'sét đánh',
            'thunderstorm',
            'lightning strike',
            'thunder roar'] },
    {
        'file': 'heartbeat_suspense.wav',
        'volume': 0.22,
        'offset': 0,
        'keywords': [
            'tim đập thình thịch',
            'nghẹt thở',
            'nín thở',
            'nhịp tim đập nhanh',
            'hoảng loạn tột độ',
            'heart pounding',
            'breathless',
            'terrified heartbeat'] },
    {
        'file': 'cinematic_impact.wav',
        'volume': 0.22,
        'offset': 0,
        'keywords': [
            'tiếng nổ',
            'sụp đổ',
            'đâm sầm',
            'va đập mạnh',
            'cú đánh chí mạng',
            'chấn động kinh hoàng',
            'tai nạn thảm khốc',
            'bùng nổ',
            'explosion',
            'violent crash',
            'heavy impact'] },
    {
        'file': 'tension_riser.wav',
        'volume': 0.18,
        'offset': 0,
        'keywords': [
            'ngàn cân treo sợi tóc',
            'căng thẳng tột độ',
            'kịch tính dồn dập',
            'hiểm nguy cận kề',
            'extreme tension',
            'climax suspense'] },
    {
        'file': 'door_creak.wav',
        'volume': 0.18,
        'offset': 0,
        'keywords': [
            'cửa cót két',
            'cót két',
            'tiếng mở cửa',
            'đẩy cửa bước vào',
            'cánh cửa từ từ mở',
            'creaking door',
            'door creaks'] },
    {
        'file': 'footsteps.wav',
        'volume': 0.18,
        'offset': 0,
        'keywords': [
            'tiếng bước chân',
            'bước chân rón rén',
            'bước chân dồn dập',
            'chạy trốn thục mạng',
            'sneaking footsteps',
            'running footsteps'] },
    {
        'file': 'clock_tick.wav',
        'volume': 0.15,
        'offset': 0,
        'keywords': [
            'đồng hồ tích tắc',
            'tiếng tích tắc',
            'đếm ngược từng giây',
            'thời gian cạn kiệt',
            'clock ticking',
            'ticking sound',
            'seconds counting down'] },
    {
        'file': 'glass_shatter.wav',
        'volume': 0.22,
        'offset': 0,
        'keywords': [
            'kính vỡ',
            'vỡ vụn',
            'ly vỡ',
            'mảnh vỡ rơi',
            'tiếng gương vỡ',
            'chai vỡ',
            'glass shattering',
            'shattered glass',
            'mirror breaks'] },
    {
        'file': 'sub_bass_drop.wav',
        'volume': 0.2,
        'offset': 0,
        'keywords': [
            'vực thẳm tuyệt vọng',
            'sụp đổ hoàn toàn',
            'chìm vào bóng tối',
            'bi kịch ập đến',
            'falling into darkness',
            'hopeless tragedy'] },
    {
        'file': 'whoosh_fast.wav',
        'volume': 0.18,
        'offset': 0,
        'keywords': [
            'lao vụt tới',
            'vụt qua',
            'phóng vụt đi',
            'lướt qua như cơn gió',
            'vụt tắt chớp nhoáng',
            'fast whoosh',
            'swoosh by',
            'dashing through'] },
    {
        'file': 'chime_bell.wav',
        'volume': 0.16,
        'offset': 0,
        'keywords': [
            'tiếng chuông ngân',
            'chợt bừng tỉnh',
            'nhận ra sự thật',
            'chợt hiểu ra',
            'sudden realization',
            'church bell rings'] },
    {
        'file': 'ambient_drone.wav',
        'volume': 0.15,
        'offset': 0,
        'keywords': [
            'không khí u ám',
            'vắng lặng rợn người',
            'tĩnh mịch đến nghẹt thở',
            'hoang vu lạnh lẽo',
            'creepy silence',
            'eerie atmosphere'] }]

def detect_sfx_for_text(text = None, visual_hint = None):
    '''Phân tích văn bản phân cảnh và gợi ý hình ảnh để tìm hiệu ứng âm thanh SFX phù hợp nhất.
    Chỉ kích hoạt khi có từ khóa hành động cụ thể rõ rệt (score >= 3).
    Trả về: (sfx_path, sfx_volume, sfx_offset_s).
    '''
    combined = f'''{text or ''} {visual_hint or ''}'''.lower()
    if not combined.strip():
        return ('', 0.2, 0)
    sfx_dir = get_sfx_root_dir()
    best_match = None
    best_score = 0
    for rule in SFX_KEYWORD_RULES:
        score = 0
        for kw in rule['keywords']:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            if not kw_clean in combined:
                continue
            score += 4 if ' ' in kw_clean else 2
        if not score > best_score:
            continue
        best_score = score
        best_match = rule
    if best_match and best_score >= 3:
        target_file = sfx_dir / best_match['file']
        if target_file.is_file():
            return (str(target_file.resolve()), float(best_match.get('volume', 0.2)), float(best_match.get('offset', 0)))
    return ('', 0.2, 0)


def assign_auto_sfx_to_scenes(scenes = None, overwrite_existing = None, min_gap = None):
    '''Quét danh sách phân cảnh và tự động gán hiệu ứng âm thanh SFX theo ngữ cảnh.
    - min_gap: Khoảng cách tối thiểu giữa 2 cảnh có SFX để tránh gây bội thực âm thanh (mặc định 4 cảnh).
    - overwrite_existing: Nếu True sẽ ghi đè các cảnh đã có SFX.
    Trả về số lượng phân cảnh đã được gán SFX.
    '''
    ensure_default_sfx_pack()
    assigned_count = 0
    last_assigned_idx = -999
    for idx, sc in enumerate(scenes, start = 1):
        cur_sfx = getattr(sc, 'sfx_path', '')
        if isinstance(sc, dict):
            cur_sfx = sc.get('sfx_path', '')
        if not cur_sfx and Path(cur_sfx).is_file() and overwrite_existing:
            last_assigned_idx = idx
            continue
        if idx - last_assigned_idx < min_gap:
            if overwrite_existing:
                pass
            continue
        text = getattr(sc, 'text_segment', '') if not isinstance(sc, dict) else sc.get('text_segment', '')
        hint = getattr(sc, 'visual_hint_vi', '') if not isinstance(sc, dict) else sc.get('visual_hint_vi', '')
        (sfx_path, vol, offset) = detect_sfx_for_text(text, hint)
        if sfx_path:
            assigned_count += 1
            last_assigned_idx = idx
            continue
        if not overwrite_existing:
            continue
        if isinstance(sc, dict):
            sc['sfx_path'] = ''
            continue
        setattr(sc, 'sfx_path', '')
    return assigned_count


def clear_all_sfx_from_scenes(scenes = None):
    '''Xóa sạch toàn bộ cấu hình âm thanh hiệu ứng (SFX) trên tất cả các phân cảnh.'''
    cleared = 0
    for sc in scenes:
        has_sfx = False
        if isinstance(sc, dict):
            if sc.get('sfx_path'):
                sc['sfx_path'] = ''
                has_sfx = True
            sc['sfx_volume'] = 0.2
            sc['sfx_offset_s'] = 0
        elif getattr(sc, 'sfx_path', ''):
            setattr(sc, 'sfx_path', '')
            has_sfx = True
        setattr(sc, 'sfx_volume', 0.2)
        setattr(sc, 'sfx_offset_s', 0)
        if not has_sfx:
            continue
        cleared += 1
    return cleared


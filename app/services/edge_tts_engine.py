# Source Generated with Decompyle++
# File: edge_tts_engine.pyc (Python 3.12)

__doc__ = '\nEdge-TTS engine — giọng đọc Microsoft Edge (miễn phí, không API key).\n\nDùng làm thay thế Text Reading CapCut (Thanh Thanh / Tâm Sự…):\n  Python sinh MP3/WAV → AudioSyncEngine fit D_sub → CapCutDraftBuilder inject.\n\nHàm chính:\n  edge_tts_generate(text, out_path, voice=..., rate=...)  # sync, cho AudioSyncEngine\n  make_tts_func(voice, rate) → Callable[[str, Path], Path]\n  list_vietnamese_voices()\n'
from __future__ import annotations
import asyncio
import logging
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable
logger = logging.getLogger(__name__)
VI_VOICES = [
    'vi-VN-HoaiMyNeural',
    'vi-VN-NamMinhNeural']
DEFAULT_VOICE = 'vi-VN-HoaiMyNeural'
VOICE_LABELS = {
    'vi-VN-HoaiMyNeural': 'Nữ - Cô Gái Hoạt Ngôn',
    'vi-VN-NamMinhNeural': 'Nam - Thanh Niên Tự Tin' }
_RATE_RE = re.compile('^[+-]?\\d+%$')
EDGE_ALL_VOICES: 'list[tuple[str, str]]' = [
    ('vi-VN-HoaiMyNeural', 'Nữ - Hoài My (Tiếng Việt)'),
    ('vi-VN-NamMinhNeural', 'Nam - Nam Minh (Tiếng Việt)'),
    ('en-US-AndrewMultilingualNeural', 'Nam - Andrew (Đa ngôn ngữ - Đọc tiếng Việt)'),
    ('en-US-AvaMultilingualNeural', 'Nữ - Ava (Đa ngôn ngữ - Đọc tiếng Việt)'),
    ('en-US-BrianMultilingualNeural', 'Nam - Brian (Đa ngôn ngữ - Đọc tiếng Việt)'),
    ('en-US-EmmaMultilingualNeural', 'Nữ - Emma (Đa ngôn ngữ - Đọc tiếng Việt)'),
    ('en-AU-WilliamMultilingualNeural', 'Nam - William (Đa ngôn ngữ - Úc)'),
    ('fr-FR-VivienneMultilingualNeural', 'Nữ - Vivienne (Đa ngôn ngữ - Pháp)'),
    ('fr-FR-RemyMultilingualNeural', 'Nam - Remy (Đa ngôn ngữ - Pháp)'),
    ('de-DE-SeraphinaMultilingualNeural', 'Nữ - Seraphina (Đa ngôn ngữ - Đức)'),
    ('de-DE-FlorianMultilingualNeural', 'Nam - Florian (Đa ngôn ngữ - Đức)'),
    ('it-IT-GiuseppeMultilingualNeural', 'Nam - Giuseppe (Đa ngôn ngữ - Ý)'),
    ('ko-KR-HyunsuMultilingualNeural', 'Nam - Hyunsu (Đa ngôn ngữ - Hàn Quốc)'),
    ('pt-BR-ThalitaMultilingualNeural', 'Nữ - Thalita (Đa ngôn ngữ - Bồ Đào Nha)'),
    ('en-US-JennyNeural', 'Nữ - Jenny (Tiếng Anh - US Tự nhiên)'),
    ('en-US-GuyNeural', 'Nam - Guy (Tiếng Anh - US Trầm ấm)'),
    ('en-US-AriaNeural', 'Nữ - Aria (Tiếng Anh - US Biểu cảm)'),
    ('en-US-ChristopherNeural', 'Nam - Christopher (Tiếng Anh - US Chuẩn)'),
    ('en-US-EricNeural', 'Nam - Eric (Tiếng Anh - US)'),
    ('en-US-MichelleNeural', 'Nữ - Michelle (Tiếng Anh - US)'),
    ('en-US-RogerNeural', 'Nam - Roger (Tiếng Anh - US)'),
    ('en-US-SteffanNeural', 'Nam - Steffan (Tiếng Anh - US)'),
    ('en-GB-SoniaNeural', 'Nữ - Sonia (Tiếng Anh - UK Quý phái)'),
    ('en-GB-RyanNeural', 'Nam - Ryan (Tiếng Anh - UK)'),
    ('en-GB-LibbyNeural', 'Nữ - Libby (Tiếng Anh - UK)'),
    ('en-AU-NatashaNeural', 'Nữ - Natasha (Tiếng Anh - Úc)'),
    ('en-CA-ClaraNeural', 'Nữ - Clara (Tiếng Anh - Canada)'),
    ('en-CA-LiamNeural', 'Nam - Liam (Tiếng Anh - Canada)'),
    ('en-IN-NeerjaNeural', 'Nữ - Neerja (Tiếng Anh - Ấn Độ)'),
    ('en-IN-PrabhatNeural', 'Nam - Prabhat (Tiếng Anh - Ấn Độ)'),
    ('zh-CN-XiaoxiaoNeural', 'Nữ - Xiaoxiao (Tiếng Trung - Phổ thông ấm áp)'),
    ('zh-CN-YunxiNeural', 'Nam - Yunxi (Tiếng Trung - Phổ thông trẻ trung)'),
    ('zh-CN-YunjianNeural', 'Nam - Yunjian (Tiếng Trung - Kịch tính / Review phim)'),
    ('zh-CN-XiaoyiNeural', 'Nữ - Xiaoyi (Tiếng Trung - Tự nhiên)'),
    ('zh-CN-YunyangNeural', 'Nam - Yunyang (Tiếng Trung - Tin tức / MC)'),
    ('zh-CN-liaoning-XiaobeiNeural', 'Nữ - Xiaobei (Tiếng Trung - Đông Bắc/Liêu Ninh)'),
    ('zh-CN-shaanxi-XiaoniNeural', 'Nữ - Xiaoni (Tiếng Trung - Thiểm Tây)'),
    ('zh-HK-HiuMaanNeural', 'Nữ - HiuMaan (Tiếng Trung - Quảng Đông/HK)'),
    ('zh-HK-WanLungNeural', 'Nam - WanLung (Tiếng Trung - Quảng Đông/HK)'),
    ('zh-TW-HsiaoChenNeural', 'Nữ - HsiaoChen (Tiếng Trung - Đài Loan)'),
    ('zh-TW-YunJheNeural', 'Nam - YunJhe (Tiếng Trung - Đài Loan)'),
    ('ja-JP-NanamiNeural', 'Nữ - Nanami (Tiếng Nhật - Ngọt ngào)'),
    ('ja-JP-KeitaNeural', 'Nam - Keita (Tiếng Nhật - Chuẩn)'),
    ('ko-KR-SunHiNeural', 'Nữ - Sun-Hi (Tiếng Hàn - Tự nhiên)'),
    ('ko-KR-InJoonNeural', 'Nam - InJoon (Tiếng Hàn - Chuẩn)'),
    ('th-TH-PremwadeeNeural', 'Nữ - Premwadee (Tiếng Thái)'),
    ('th-TH-NiwatNeural', 'Nam - Niwat (Tiếng Thái)'),
    ('fr-FR-DeniseNeural', 'Nữ - Denise (Tiếng Pháp)'),
    ('fr-FR-HenriNeural', 'Nam - Henri (Tiếng Pháp)'),
    ('de-DE-KatjaNeural', 'Nữ - Katja (Tiếng Đức)'),
    ('de-DE-ConradNeural', 'Nam - Conrad (Tiếng Đức)'),
    ('es-ES-ElviraNeural', 'Nữ - Elvira (Tiếng Tây Ban Nha)'),
    ('es-ES-AlvaroNeural', 'Nam - Alvaro (Tiếng Tây Ban Nha)'),
    ('pt-BR-FranciscaNeural', 'Nữ - Francisca (Tiếng Bồ Đào Nha - Brazil)'),
    ('pt-BR-AntonioNeural', 'Nam - Antonio (Tiếng Bồ Đào Nha - Brazil)'),
    ('ru-RU-SvetlanaNeural', 'Nữ - Svetlana (Tiếng Nga)'),
    ('ru-RU-DmitryNeural', 'Nam - Dmitry (Tiếng Nga)'),
    ('id-ID-GadisNeural', 'Nữ - Gadis (Tiếng Indonesia)'),
    ('id-ID-ArdiNeural', 'Nam - Ardi (Tiếng Indonesia)'),
    ('fil-PH-BlessicaNeural', 'Nữ - Blessica (Tiếng Philippines)'),
    ('ms-MY-YasminNeural', 'Nữ - Yasmin (Tiếng Malaysia)'),
    ('lo-LA-KeomanyNeural', 'Nữ - Keomany (Tiếng Lào)'),
    ('km-KH-SreymomNeural', 'Nữ - Sreymom (Tiếng Khmer)'),
    ('hi-IN-SwaraNeural', 'Nữ - Swara (Tiếng Hindi - Ấn Độ)')]
# WARNING: Decompyle incomplete

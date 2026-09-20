# Source Generated with Decompyle++
# File: module_subtitle.pyc (Python 3.12)

'''Hằng số dùng chung cho các panel phụ đề / STT / TTS.

Panel thật nằm ở ``module_caption_tools.py`` (ModuleCaptionStyle,
ModuleSrtTools, ModuleStt, ModuleTts). File này từng chứa thêm một class
``ModuleSubtitle`` gộp tất cả vào một pane, nhưng ``control_panel.py``
chưa bao giờ nạp nó — chỉ các hằng số bên dưới được import. Class đó đã
được gỡ để không phải bảo trì hai bản UI song song.
'''
from __future__ import annotations
from app.services.edge_tts_engine import list_edge_tts_options
VOICES = list_edge_tts_options()
FONTS = [
    'Arial',
    'Segoe UI',
    'Tahoma',
    'Calibri',
    'ANTON',
    'BANGERS',
    'Microsoft YaHei',
    'Malgun Gothic',
    'Yu Gothic',
    'Noto Sans',
    'Nirmala UI']
BG_STYLES = [
    'Viền đen',
    'Viền đậm',
    'Bóng đổ',
    'Glow trắng',
    'Neon xanh',
    'Neon hồng',
    'Nền đen mờ',
    'Nền đen đặc',
    'Nền vàng chữ đen',
    'Nền trắng',
    'Nền xanh',
    'Nền đỏ',
    'Nền hồng',
    'Hộp viền trắng',
    'Không nền']
ENGINES = [
    'Gemini',
    'Groq',
    'OpenAI',
    'DeepSeek']
TRANSLATE_LANGUAGES = [
    'Tự nhận diện',
    'Tiếng Việt',
    'English',
    '中文 (Chinese)',
    'ไทย (Thai)',
    '日本語 (Japanese)',
    '한국어 (Korean)',
    'Español (Spanish)',
    'Français (French)',
    'Deutsch (German)']
STT_MODELS = [
    'tiny',
    'base',
    'small']
STT_LANGUAGES = [
    'auto',
    'vi (Tiếng Việt)',
    'zh (Tiếng Trung)',
    'en (English)',
    'th (ไทย)',
    'ja (日本語)',
    'ko (한국어)']

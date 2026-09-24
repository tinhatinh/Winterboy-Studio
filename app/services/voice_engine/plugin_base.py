'''
Modular Voice AI Plugin Architecture — Kiến trúc Plugin mở rộng cho Voice & TTS.

Cho phép dễ dàng tích hợp thêm các nhà cung cấp AI mới (OpenAI TTS, Vbee, FPT AI, Suno, v.v.)
vào Winterboy Studio Pro mà không cần sửa đổi mã nguồn lõi.
'''
from __future__ import annotations
import importlib.util as importlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)

class BaseVoicePlugin(ABC):
    '''Lớp cơ sở trừu tượng cho mọi plugin giọng đọc AI.'''

    @property
    @abstractmethod
    def name(self) -> str:
        '''Tên hiển thị của nhà cung cấp (VD: 'ElevenLabs', 'OpenAI TTS').'''

    @property
    @abstractmethod
    def provider_id(self) -> str:
        '''Định danh kỹ thuật duy nhất (VD: 'elevenlabs', 'openai').'''

    @abstractmethod
    def is_available(self) -> bool:
        '''Kiểm tra xem provider này đã sẵn sàng (đã có key/môi trường) hay chưa.'''

    @abstractmethod
    def list_voices(self) -> list[dict[str, Any]]:
        '''
        Trả về danh sách giọng khả dụng.
        Mỗi phần tử: {'id': str, 'name': str, 'lang': str, 'gender': str}
        '''

    @abstractmethod
    def synthesize(self, text: str, voice_id: str, speed: str, output_path: Path,
                   **kwargs: Any) -> Path:
        '''Sinh file audio từ văn bản và lưu vào output_path.'''


class VoicePluginRegistry:
    '''Kho đăng ký và điều phối các plugin giọng đọc AI.'''
    _plugins: dict[str, BaseVoicePlugin] = {}

    @classmethod
    def register(cls, plugin: BaseVoicePlugin) -> None:
        key = plugin.provider_id.strip().lower()
        cls._plugins[key] = plugin
        logger.info('Đã đăng ký Voice Plugin: %s (%s)', plugin.name, key)

    @classmethod
    def get(cls, provider_id: str) -> BaseVoicePlugin | None:
        return cls._plugins.get(provider_id.strip().lower())

    @classmethod
    def list_providers(cls) -> list[str]:
        return [p.name for p in cls._plugins.values()]

    @classmethod
    def load_external_plugins(cls, plugins_dir: Path | None = None) -> int:
        '''Tự động quét và nạp các file plugin .py bên ngoài.'''
        if plugins_dir is None:
            root = Path(__file__).resolve().parents[3]
            plugins_dir = root / 'plugins' / 'voice'
        # chưa có thư mục plugin thì coi như không có gì để nạp
        if not plugins_dir.is_dir():
            return 0
        loaded = 0
        for py_file in sorted(plugins_dir.glob('*.py')):
            if py_file.name.startswith('_'):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for attr_name in dir(mod):
                        obj = getattr(mod, attr_name)
                        # chỉ nhận lớp con thật sự, bỏ qua chính lớp nền
                        if (isinstance(obj, type)
                                and issubclass(obj, BaseVoicePlugin)
                                and obj is not BaseVoicePlugin):
                            instance = obj()
                            cls.register(instance)
                            loaded += 1
            except Exception as exc:
                logger.error('Lỗi khi nạp external voice plugin %s: %s', py_file, exc)
        return loaded

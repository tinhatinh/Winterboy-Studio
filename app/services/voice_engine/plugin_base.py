# Source Generated with Decompyle++
# File: plugin_base.pyc (Python 3.12)

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
    name = (lambda self = None: pass)()()
    provider_id = (lambda self = None: pass)()()
    is_available = (lambda self = None: pass)()
    list_voices = (lambda self = None: pass)()
    synthesize = (lambda self, text = None, voice_id = None, speed = abstractmethod, output_path = ('text', 'str', 'voice_id', 'str', 'speed', 'str', 'output_path', 'Path', 'kwargs', 'Any', 'return', 'Path'): pass)()


class VoicePluginRegistry:
    '''Kho đăng ký và điều phối các plugin giọng đọc AI.'''
    _plugins: 'dict[str, BaseVoicePlugin]' = { }
    register = (lambda cls = None, plugin = None: key = plugin.provider_id.strip().lower()cls._plugins[key] = pluginlogger.info('Đã đăng ký Voice Plugin: %s (%s)', plugin.name, key))()
    get = (lambda cls = None, provider_id = None: cls._plugins.get(provider_id.strip().lower()))()
    list_providers = (lambda cls = None: pass# WARNING: Decompyle incomplete
)()
    load_external_plugins = (lambda cls = None, plugins_dir = None: pass# WARNING: Decompyle incomplete
)()


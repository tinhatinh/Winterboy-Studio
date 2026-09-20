# Source Generated with Decompyle++
# File: tts_preview.pyc (Python 3.12)

__doc__ = 'On-demand, cached samples for the TTS voice picker.\n\nSamples intentionally use the same provider functions as a render.  They are\ncreated only after the user clicks preview, never in bulk when a voice catalog\nloads (which would consume ElevenLabs quota or trigger CapCut rate limits).\n'
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
PREVIEW_TEXT = 'Xin chào các bạn. Đây là giọng đọc mẫu trong Winterboy Studio.'
TTS_PREVIEW_CACHE_ROOT = Path.home() / '.winterboy' / 'tts_voice_preview'
BUNDLED_TTS_PREVIEW_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'tts_samples'
# WARNING: Decompyle incomplete

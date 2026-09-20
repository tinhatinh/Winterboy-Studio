import logging
import customtkinter as ctk

logger = logging.getLogger(__name__)

UI_FONT_FAMILY = 'Segoe UI'
MONO_FONT_FAMILY = 'Consolas'

# Light colors based on standard light mode palette
ACCENT = ('#059669', '#10B981')
ACCENT_HOVER = ('#047857', '#34D399')
ACCENT_GOLD = ('#047857', '#6EE7B7')
ACCENT_TEXT = ('#047857', '#10B981')
ACCENT_SOFT = ('#D1FAE5', '#A7F3D0')
ON_ACCENT = ('#FFFFFF', '#101010')

BG_DARK = ('#F1F5F9', '#1B1B1B')
BG_PANEL = ('#F8FAFC', '#222222')
BG_CARD = ('#FFFFFF', '#2A2A2A')
BG_INPUT = ('#FFFFFF', '#191919')
BG_HEADER = ('#FFFFFF', '#1E1E1E')
BG_ELEVATED = ('#E2E8F0', '#343434')
BG_SUNKEN = ('#E2E8F0', '#151515')

SURFACE_BTN = ('#E2E8F0', '#343434')
SURFACE_BTN_HOVER = ('#CBD5E1', '#454545')
SURFACE_ALT = ('#FFFFFF', '#252525')
SURFACE_ALT_2 = ('#F1F5F9', '#262626')

DROPDOWN_BG = ('#FFFFFF', '#202020')
DROPDOWN_HOVER = ('#E2E8F0', '#343434')

TEXT = ('#0F172A', '#ECECEC')
TEXT_DIM = ('#334155', '#A6A6A6')
TEXT_MUTED = ('#64748B', '#7C7C7C')
TEXT_ON_DARK = ('#0F172A', '#FFFFFF')

SUCCESS = ('#16A34A', '#22C55E')
SUCCESS_HOVER = ('#15803D', '#16A34A')
ON_SUCCESS = ('#FFFFFF', '#FFFFFF')

DANGER = ('#DC2626', '#E95364')
DANGER_HOVER = ('#B91C1C', '#C43A3A')
DANGER_SOFT = ('#FEE2E2', '#5A2A2A')
DANGER_SOFT_HOVER = ('#FECACA', '#7A3535')
ON_DANGER = ('#FFFFFF', '#FFFFFF')
ON_DANGER_SOFT = ('#991B1B', '#FFFFFF')

WARNING = ('#D97706', '#F6C344')
INFO = ('#0891B2', '#00C7D9')

BORDER = ('#CBD5E1', '#3A3A3A')
BORDER_SOFT = ('#E2E8F0', '#303030')

SCROLLBAR = ('#0891B2', '#00C7D9')
SCROLLBAR_HOVER = ('#0E7490', '#12AAB9')

DEFAULT_MODE = 'light'
_VALID = ('light', 'oled', 'dark')
_mode = DEFAULT_MODE

_listeners = []
_appearance_generation = 0
_APPEARANCE_BATCH_SIZE = 32
_APPEARANCE_BATCH_DELAY_MS = 4

_current_accent_name = 'emerald'

def set_appearance(mode: str):
    global _mode
    if mode not in _VALID:
        return
    _mode = mode
    ctk.set_appearance_mode(mode)
    _notify_appearance_listeners()

def _notify_appearance_listeners(root=None):
    pass

def apply_global_theme():
    mode = DEFAULT_MODE
    target_mode = mode
    ctk.set_default_color_theme('dark-blue')
    ctk.set_appearance_mode('light')
    
    font_theme = ctk.ThemeManager.theme.get('CTkFont')
    if isinstance(font_theme, dict):
        font_theme['family'] = UI_FONT_FAMILY
        
    for widget in ('CTkButton', 'CTkLabel', 'CTkCheckBox', 'CTkRadioButton', 'CTkSwitch', 'CTkOptionMenu', 'CTkComboBox', 'CTkEntry', 'CTkSegmentedButton', 'CTkTextbox'):
        entry = ctk.ThemeManager.theme.get(widget)
        if isinstance(entry, dict) and 'text_color' in entry:
            entry['text_color'] = list(TEXT)
            
    set_appearance(target_mode)


def resolve(color_tuple):
    return color_tuple[0] if _mode == 'light' else color_tuple[1]


def on_appearance_change(listener):
    _listeners.append(listener)

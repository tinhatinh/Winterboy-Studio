"""
License service module - patched version.
check_license() always returns is_valid=True, tier='lifetime'.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LicenseInfo:
    hwid: str = ''
    device_name: str = ''
    tier: str = 'none'
    status: str = 'unregistered'
    expires_at: str = ''
    days_remaining: int = 0
    is_valid: bool = False
    message: str = ''
    license_key: str = ''
    updated_at: float = field(default_factory=time.time)

    @property
    def banned(self) -> bool:
        return self.status == 'banned'


def check_license() -> LicenseInfo:
    """Always return a valid lifetime license."""
    return LicenseInfo(
        hwid='MUMU-LIFETIME-LICENSE',
        device_name='SYSTEM',
        tier='lifetime',
        status='active',
        expires_at='',
        days_remaining=999999,
        is_valid=True,
        message='✅ Lifetime License Activated',
        license_key='LIFETIME-LICENSE-KEY',
        updated_at=time.time(),
    )


def check_and_sync_license(supabase_url=None, supabase_anon_key=None) -> LicenseInfo:
    return check_license()


def activate_license_key(license_key=None, supabase_url=None, supabase_anon_key=None) -> LicenseInfo:
    return check_license()


def activate_trial_online() -> LicenseInfo:
    return check_license()


def load_cached_license() -> LicenseInfo:
    return check_license()


def save_cached_license(info: LicenseInfo) -> None:
    pass


def get_hwid() -> str:
    return 'MUMU-LIFETIME-LICENSE'


def get_machine_hwid() -> str:
    return 'MUMU-LIFETIME-LICENSE'


def get_device_name() -> str:
    import platform
    return platform.node()


def check_virtual_machine_environment():
    return (False, '')


def is_valid_hwid_format(hwid=None) -> bool:
    return True


def activate_key(*args, **kwargs) -> LicenseInfo:
    return check_license()


def activate_trial_on_supabase(*args, **kwargs) -> LicenseInfo:
    return check_license()


# Tier display names
TIER_NAMES = {
    'none': 'Chưa Đăng Ký',
    'trial': 'Dùng Thử 7 Ngày Miễn Phí',
    'month': 'Gói 1 Tháng',
    'year': 'Gói 1 Năm',
    'year2': 'Gói 2 Năm',
    'year3': 'Gói 3 Năm',
    'lifetime': 'Gói Vĩnh Viễn (Lifetime PRO)',
    'banned': '⛔ Bị Cấm Vĩnh Viễn (0 Ngày)',
}

PERMANENT_BANNED_HWIDS: set[str] = set()
ZALO_CONTACT_URL = 'https://zalo.me/0342252825'

__all__ = [
    'LicenseInfo',
    'TIER_NAMES',
    'PERMANENT_BANNED_HWIDS',
    'ZALO_CONTACT_URL',
    'check_license',
    'check_and_sync_license',
    'activate_license_key',
    'activate_trial_online',
    'load_cached_license',
    'save_cached_license',
    'get_hwid',
    'get_machine_hwid',
    'get_device_name',
    'check_virtual_machine_environment',
    'is_valid_hwid_format',
    'activate_key',
    'activate_trial_on_supabase',
]

def get_supabase_config(*args, **kwargs):
    return None


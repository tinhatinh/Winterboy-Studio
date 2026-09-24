# Source Generated with Decompyle++
# File: license_service.pyc (Python 3.12)

'''
License service module - patched version
This module is a minimal replacement that provides unlimited lifetime access
'''
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
    updated_at: float = field(default_factory = time.time)


def check_license():
    '''Always return a valid lifetime license'''
    return LicenseInfo(hwid = 'MUMU-LIFETIME-LICENSE', device_name = 'SYSTEM', tier = 'lifetime', status = 'active', expires_at = '', days_remaining = 999999, is_valid = True, message = '✅ Lifetime License Activated', license_key = 'LIFETIME-LICENSE-KEY', updated_at = time.time())


def check_and_sync_license():
    '''Always return a valid lifetime license'''
    return check_license()


def activate_license_key(key = None):
    '''Always return a valid lifetime license'''
    return check_license()


def activate_trial_online():
    '''Always return a valid lifetime license'''
    return check_license()


def load_cached_license():
    '''Always return a valid lifetime license'''
    return check_license()


def get_hwid():
    return 'MUMU-LIFETIME-LICENSE'


def check_virtual_machine_environment():
    return False


def is_valid_hwid_format(hwid = None):
    return True


def activate_key(*args, **kwargs):
    return check_license()


def activate_trial_on_supabase(*args, **kwargs):
    return check_license()

__all__ = [
    'LicenseInfo',
    'check_license',
    'check_and_sync_license',
    'activate_license_key',
    'activate_trial_online',
    'load_cached_license',
    'get_hwid',
    'check_virtual_machine_environment',
    'is_valid_hwid_format',
    'activate_key',
    'activate_trial_on_supabase']

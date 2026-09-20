# Source Generated with Decompyle++
# File: api_key_manager.pyc (Python 3.12)

'''
api_key_manager — Quản lý danh sách ElevenLabs API Keys (hỗ trợ nhiều Account/Workspace),
hiển thị số dư Balance (character_limit, character_count, remaining) và tự động Swap Key:
1. Pre-check chủ động: Kiểm tra (character_limit - character_count) < độ dài văn bản cần đọc.
2. Reactive Failover: Bắt lỗi 429 hoặc quota_exceeded để fallback sang key kế tiếp.
'''
import time
import logging
from typing import Optional, List, Dict, Any
from app.services.voice_engine.voice_fetcher import get_user_subscription
logger = logging.getLogger(__name__)

def mask_api_key(key = None):
    '''Rút gọn hiển thị API key: sk_...1234'''
    if not key:
        key
    key = ''.strip()
    if not key:
        return 'Chưa có key'
    if len(key) <= 8:
        return key
    return f'''{None[:5]}...{key[-4:]}'''


class ApiKeyManager:
    
    def __init__(self = None, keys = None, auto_swap = None):
        self.keys = []
        self.active_index = 0
        self.auto_swap = auto_swap
        if keys:
            for k in keys:
                if isinstance(k, dict):
                    self.add_key(k.get('key', ''), label = k.get('label', ''), probe = False)
                    continue
                if not isinstance(k, str):
                    continue
                self.add_key(k, probe = False)
            return None

    
    def add_key(self = None, key = None, label = None, probe = ('', False)):
        '''Thêm API Key vào pool với tên gợi nhớ (label)'''
        pass
    # WARNING: Decompyle incomplete

    
    def remove_key(self = None, index = None):
        '''Xóa key tại vị trí index'''
        if  <= 0, index or 0, index < len(self.keys):
            pass
        else:
            return False
        self.keys.pop(index)
        if self.active_index >= len(self.keys):
            pass
        return True
        return False

    
    def update_key_label(self = None, index = None, new_label = None):
        """Đổi tên gợi nhớ cho tài khoản (e.g. 'Account Chính', 'Workspace Team')"""
        if  <= 0, index or 0, index < len(self.keys):
            pass
        else:
            return False
        if new_label.strip():
            return True
        return False

    
    def update_key_balance(self = None, key = None, sub_info = None):
        '''Cập nhật dữ liệu balance trực tiếp từ phản hồi API'''
        for item in self.keys:
            if not item['key'] == key:
                continue
            limit = sub_info.get('character_limit', 0)
            used = sub_info.get('character_count', 0)
            rem = sub_info.get('remaining', max(0, limit - used))
            pct_used = sub_info.get('percent_used', 0)
            item['tier'] = str(sub_info.get('tier', 'free')).capitalize()
            item['limit'] = limit
            item['count'] = used
            item['character_limit'] = limit
            item['character_count'] = used
            item['remaining'] = rem
            item['percent_used'] = pct_used
            item['percent_remaining'] = max(0, 100 - pct_used)
            item['status'] = 'active' if rem > 0 else 'exhausted'
            item['cached_at'] = time.time()
            item['error'] = ''
            self.keys
            return None

    
    def deduct_credits(self = None, key = None, amount = None):
        '''
        Khấu trừ credits cục bộ sau mỗi lần TTS thành công.
        Giúp chiến lược pre-check luôn nắm chính xác số dư tức thời mà không cần spam API.
        '''
        for itm in self.keys:
            if not itm['key'] == key:
                continue
            itm['count'] = itm.get('count', 0) + amount
            itm['character_count'] = itm['count']
            lim = itm.get('limit', 0)
            if itm['remaining'] <= 0:
                itm['status'] = 'exhausted'
            None if lim > 0 else self.keys
            return None

    
    def _probe_item(self = None, item = None):
        '''Truy vấn GET /v1/user/subscription để cập nhật balance tài khoản'''
        sub = get_user_subscription(item['key'])
        if sub.get('ok'):
            limit = sub.get('character_limit', 0)
            count = sub.get('character_count', 0)
            rem = sub.get('remaining', max(0, limit - count))
            pct_used = sub.get('percent_used', 0)
            item['tier'] = str(sub.get('tier', 'free')).capitalize()
            item['limit'] = limit
            item['count'] = count
            item['character_limit'] = limit
            item['character_count'] = count
            item['remaining'] = rem
            item['percent_used'] = pct_used
            item['percent_remaining'] = sub.get('percent_remaining', max(0, 100 - pct_used))
            item['status'] = 'active' if rem > 0 else 'exhausted'
            item['cached_at'] = time.time()
            item['error'] = ''
            return None
        item['status'] = sub.get('status', 'error')
        item['error'] = sub.get('error', 'Lỗi kiểm tra')

    
    def probe_key_at(self = None, index = None):
        if  <= 0, index or 0, index < len(self.keys):
            pass
        else:
            return None
        self._probe_item(self.keys[index])
        return self.keys[index]

    
    def probe_all(self = None):
        for item in self.keys:
            self._probe_item(item)
        return self.keys

    
    def get_active_key(self = None):
        if not self.keys:
            return ''
        idx = max(0, min(self.active_index, len(self.keys) - 1))
        return self.keys[idx]['key']

    
    def get_active_info(self = None):
        if not self.keys:
            return None
        idx = max(0, min(self.active_index, len(self.keys) - 1))
        return self.keys[idx]

    
    def set_active_index(self = None, index = None):
        if  <= 0, index or 0, index < len(self.keys):
            pass
        else:
            return None
        return None

    
    def check_and_ensure_quota(self = None, needed_chars = None):
        '''
        Chiến Lược Pre-check (Kiểm tra chủ động trước khi gọi API):
        Nếu (character_limit - character_count) < độ dài văn bản cần đọc,
        tự động chuyển ngay sang key tiếp theo trong pool có đủ quota mà không cần đợi lỗi xảy ra!
        '''
        if not self.keys or self.auto_swap:
            return (self.get_active_key(), None)
        active_info = None.get_active_info()
        if not active_info:
            return ('', None)
        if active_info.get('status') == 'untested' or time.time() - active_info.get('cached_at', 0) > 300:
            self._probe_item(active_info)
        if active_info.get('status') == 'active' and active_info.get('remaining', 0) >= needed_chars:
            return (active_info['key'], None)
        total = None(self.keys)
        old_label = active_info.get('label', 'Key hiện tại')
        for step in range(1, total + 1):
            next_idx = (self.active_index + step) % total
            candidate = self.keys[next_idx]
            if candidate['status'] in ('untested', 'error'):
                self._probe_item(candidate)
            if not candidate['status'] == 'active':
                continue
            if not candidate.get('remaining', 0) >= needed_chars:
                continue
            self.active_index = next_idx
            new_key = candidate['key']
            msg = f'''⚡ Pre-check: {old_label} chỉ còn {active_info.get('remaining', 0)} credits (cần {needed_chars} ký tự). Đã chủ động chuyển sang {candidate['label']} ({candidate['masked']}, còn {candidate['remaining']:,} credits).'''
            logger.info(msg)
            
            return range(1, total + 1), (new_key, msg)
        return (active_info['key'], None)

    
    def swap_to_next_available(self = None, current_failed_key = None):
        '''
        Chiến Lược Reactive Failover (Xử lý khi ElevenLabs trả về lỗi 429 hoặc quota_exceeded):
        Đánh dấu key hiện tại là cạn quota và fallback ngay sang key kế tiếp trong danh sách.
        '''
        if not self.keys:
            return (None, 'Không có API key nào trong danh sách.')
        if current_failed_key:
            for item in self.keys:
                if not item['key'] == current_failed_key:
                    continue
                item['status'] = 'exhausted'
                item['remaining'] = 0
        total = len(self.keys)
        for step in range(1, total + 1):
            next_idx = (self.active_index + step) % total
            candidate = self.keys[next_idx]
            if candidate['status'] in ('untested', 'error'):
                self._probe_item(candidate)
            if not candidate['status'] == 'active':
                continue
            if not candidate['remaining'] > 0:
                continue
            old_key_mask = mask_api_key(self.get_active_key())
            self.active_index = next_idx
            new_key = candidate['key']
            msg = f'''🔄 Auto-swap Reactive: Key {old_key_mask} hết quota. Đã chuyển sang {candidate.get('label', f'''Key #{next_idx + 1}''')} ({candidate['masked']}, còn {candidate['remaining']:,} credits).'''
            logger.info(msg)
            
            return range(1, total + 1), (new_key, msg)
        return (None, 'Tất cả các API Key đều đã hết hạn mức (quota) hoặc không hợp lệ!')

    
    def load_from_config(self = None, cfg = None):
        raw_keys = cfg.get('api_keys', [])
        if raw_keys and cfg.get('api_key'):
            raw_keys = [
                cfg.get('api_key')]
        self.keys.clear()
        for idx, k in enumerate(raw_keys, 1):
            if isinstance(k, dict):
                key_str = k.get('key', '').strip()
                label_str = k.get('label', f'''Tài khoản {idx}''')
                if not key_str:
                    continue
                self.add_key(key_str, label = label_str, probe = False)
                item = self.keys[-1]
                item['limit'] = k.get('limit', k.get('character_limit', 0))
                item['count'] = k.get('count', k.get('character_count', 0))
                item['character_limit'] = item['limit']
                item['character_count'] = item['count']
                item['remaining'] = k.get('remaining', max(0, item['limit'] - item['count']))
                item['percent_used'] = k.get('percent_used', 0)
                item['tier'] = k.get('tier', 'unknown')
                item['status'] = k.get('status', 'untested')
                continue
            if not isinstance(k, str):
                continue
            if not k.strip():
                continue
            self.add_key(k.strip(), label = f'''Tài khoản {idx}''', probe = False)
        self.active_index = int(cfg.get('active_key_index', 0))
        if self.active_index >= len(self.keys):
            self.active_index = 0
        self.auto_swap = bool(cfg.get('auto_swap_keys', True))

    
    def to_config(self = None):
        '''Lưu trữ cấu trúc pool API key chuẩn hỗ trợ label, remaining, status'''
        pass
    # WARNING: Decompyle incomplete



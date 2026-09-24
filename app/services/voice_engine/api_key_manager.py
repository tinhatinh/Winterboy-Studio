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

def mask_api_key(key: str) -> str:
    '''Rút gọn hiển thị API key: sk_...1234'''
    key = (key or '').strip()
    if not key:
        return 'Chưa có key'
    if len(key) <= 8:
        return key
    return f'''{key[:5]}...{key[-4:]}'''


class ApiKeyManager:

    def __init__(self, keys: Optional[List[Any]] = None, auto_swap: bool = True):
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


    def add_key(self, key: str, label: str = '', probe: bool = False) -> bool:
        '''Thêm API Key vào pool với tên gợi nhớ (label)'''
        clean = (key or '').strip()
        if not clean:
            return False
        if any(item['key'] == clean for item in self.keys):
            return False
        account_num = len(self.keys) + 1
        clean_label = (label or '').strip() or f'''Tài khoản {account_num}'''
        item = {
            'key': clean,
            'label': clean_label,
            'masked': mask_api_key(clean),
            'tier': 'unknown',
            'limit': 0,
            'count': 0,
            'character_limit': 0,
            'character_count': 0,
            'remaining': 0,
            'percent_used': 0.0,
            'percent_remaining': 0.0,
            'status': 'untested',
            'cached_at': 0.0,
            'error': ''}
        if probe:
            self._probe_item(item)
        self.keys.append(item)
        return True


    def remove_key(self, index: int) -> bool:
        '''Xóa key tại vị trí index'''
        if 0 <= index < len(self.keys):
            self.keys.pop(index)
            if self.active_index >= len(self.keys):
                self.active_index = max(0, len(self.keys) - 1)
            return True
        return False


    def update_key_label(self, index: int, new_label: str) -> bool:
        """Đổi tên gợi nhớ cho tài khoản (e.g. 'Account Chính', 'Workspace Team')"""
        if 0 <= index < len(self.keys) and new_label.strip():
            self.keys[index]['label'] = new_label.strip()
            return True
        return False


    def update_key_balance(self, key: str, sub_info: dict) -> None:
        '''Cập nhật dữ liệu balance trực tiếp từ phản hồi API'''
        for item in self.keys:
            if not item['key'] == key:
                continue
            limit = sub_info.get('character_limit', 0)
            used = sub_info.get('character_count', 0)
            rem = sub_info.get('remaining', max(0, limit - used))
            pct_used = sub_info.get('percent_used', 0.0)
            item['tier'] = str(sub_info.get('tier', 'free')).capitalize()
            item['limit'] = limit
            item['count'] = used
            item['character_limit'] = limit
            item['character_count'] = used
            item['remaining'] = rem
            item['percent_used'] = pct_used
            item['percent_remaining'] = max(0.0, 100.0 - pct_used)
            item['status'] = 'active' if rem > 0 else 'exhausted'
            item['cached_at'] = time.time()
            item['error'] = ''
            return None


    def deduct_credits(self, key: str, amount: int) -> None:
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
            if lim > 0:
                itm['remaining'] = max(0, lim - itm['count'])
                itm['percent_used'] = round(itm['count'] / lim * 100, 1)
                itm['percent_remaining'] = max(0.0, 100.0 - itm['percent_used'])
            else:
                itm['remaining'] = max(0, itm.get('remaining', 0) - amount)
            if itm['remaining'] <= 0:
                itm['status'] = 'exhausted'
            return None


    def _probe_item(self, item: Dict[str, Any]) -> None:
        '''Truy vấn GET /v1/user/subscription để cập nhật balance tài khoản'''
        sub = get_user_subscription(item['key'])
        if sub.get('ok'):
            limit = sub.get('character_limit', 0)
            count = sub.get('character_count', 0)
            rem = sub.get('remaining', max(0, limit - count))
            pct_used = sub.get('percent_used', 0.0)
            item['tier'] = str(sub.get('tier', 'free')).capitalize()
            item['limit'] = limit
            item['count'] = count
            item['character_limit'] = limit
            item['character_count'] = count
            item['remaining'] = rem
            item['percent_used'] = pct_used
            item['percent_remaining'] = sub.get('percent_remaining', max(0.0, 100.0 - pct_used))
            item['status'] = 'active' if rem > 0 else 'exhausted'
            item['cached_at'] = time.time()
            item['error'] = ''
        else:
            item['status'] = sub.get('status', 'error')
            item['error'] = sub.get('error', 'Lỗi kiểm tra')


    def probe_key_at(self, index: int) -> Optional[Dict[str, Any]]:
        if 0 <= index < len(self.keys):
            self._probe_item(self.keys[index])
            return self.keys[index]
        return None


    def probe_all(self) -> List[Dict[str, Any]]:
        for item in self.keys:
            self._probe_item(item)
        return self.keys


    def get_active_key(self) -> str:
        if not self.keys:
            return ''
        idx = max(0, min(self.active_index, len(self.keys) - 1))
        return self.keys[idx]['key']


    def get_active_info(self) -> Optional[Dict[str, Any]]:
        if not self.keys:
            return None
        idx = max(0, min(self.active_index, len(self.keys) - 1))
        return self.keys[idx]


    def set_active_index(self, index: int) -> None:
        if 0 <= index < len(self.keys):
            self.active_index = index


    def check_and_ensure_quota(self, needed_chars: int = 1) -> tuple[str, Optional[str]]:
        '''
        Chiến Lược Pre-check (Kiểm tra chủ động trước khi gọi API):
        Nếu (character_limit - character_count) < độ dài văn bản cần đọc,
        tự động chuyển ngay sang key tiếp theo trong pool có đủ quota mà không cần đợi lỗi xảy ra!
        '''
        if not self.keys or not self.auto_swap:
            return (self.get_active_key(), None)
        active_info = self.get_active_info()
        if not active_info:
            return ('', None)
        if active_info.get('status') == 'untested' or time.time() - active_info.get('cached_at', 0) > 300:
            self._probe_item(active_info)
        if active_info.get('status') == 'active' and active_info.get('remaining', 0) >= needed_chars:
            return (active_info['key'], None)
        total = len(self.keys)
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
            return (new_key, msg)
        return (active_info['key'], None)


    def swap_to_next_available(self, current_failed_key: Optional[str] = None) -> tuple[Optional[str], str]:
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
            return (new_key, msg)
        return (None, 'Tất cả các API Key đều đã hết hạn mức (quota) hoặc không hợp lệ!')


    def load_from_config(self, cfg: dict) -> None:
        raw_keys = cfg.get('api_keys', [])
        if not raw_keys and cfg.get('api_key'):
            raw_keys = [cfg.get('api_key')]
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
                item['percent_used'] = k.get('percent_used', 0.0)
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


    def to_config(self) -> dict:
        '''Lưu trữ cấu trúc pool API key chuẩn hỗ trợ label, remaining, status'''
        return {
            'api_keys': [{
                'key': item['key'],
                'label': item.get('label', f'''Tài khoản {idx}'''),
                'remaining': item.get('remaining', 0),
                'character_limit': item.get('limit', 0),
                'character_count': item.get('count', 0),
                'tier': item.get('tier', 'free'),
                'status': item.get('status', 'untested'),
                'percent_used': item.get('percent_used', 0.0)} for idx, item in enumerate(self.keys, 1)],
            'active_key_index': self.active_index,
            'auto_swap_keys': self.auto_swap}

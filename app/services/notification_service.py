# Source Generated with Decompyle++
# File: notification_service.pyc (Python 3.12)

'''Module quản lý thông báo và bản cập nhật ứng dụng (App Notifications & Updates).

Các tính năng:
- Đồng bộ thông báo mới từ bảng Supabase app_notifications.
- Lưu bộ đệm cục bộ 10 thông báo gần nhất (~/.mumu/notifications_cache.json).
- Kiểm soát quy tắc: Chỉ hiển thị modal tự động 1 LẦN DUY NHẤT trong ngày khi khởi động app.
- Hỗ trợ Tagline màu đỏ quan trọng cho các bản cập nhật để người dùng biết tải file mới cài đè lên.
'''
from __future__ import annotations
import json
import logging
import os
import time
import urllib.error as urllib
import urllib.request as urllib
from datetime import datetime
from pathlib import Path
from typing import Any
from app.services.license_service import get_supabase_config
logger = logging.getLogger('app.services.notification_service')
NOTIFICATION_CACHE_DIR = Path.home() / '.mumu'
NOTIFICATION_CACHE_FILE = NOTIFICATION_CACHE_DIR / 'notifications_cache.json'
NOTIFICATION_STATE_FILE = NOTIFICATION_CACHE_DIR / 'notification_state.json'
DEFAULT_DOWNLOAD_URL = 'https://mumu-studio-pro-o1xc.vercel.app/'
DEFAULT_UPDATE_TAGLINE = '🚨 BẢN CẬP NHẬT QUAN TRỌNG: Vui lòng lên website tải file mới và cài chồng lên để tiếp tục sử dụng ổn định.'

def _ensure_cache_dir():
    
    try:
        NOTIFICATION_CACHE_DIR.mkdir(parents = True, exist_ok = True)
        return None
    except Exception:
        return None



def load_cached_notifications():
    '''Đọc danh sách thông báo đã lưu trong bộ đệm cục bộ (tối đa 10 thông báo).'''
    
    try:
        if NOTIFICATION_CACHE_FILE.is_file():
            raw = NOTIFICATION_CACHE_FILE.read_text(encoding = 'utf-8')
            data = json.loads(raw)
            if isinstance(data, list):
                return data[:10]
            if None(data, dict) and 'notifications' in data:
                return data.get('notifications', [])[:10]
            return None
        except Exception:
            exc = None
            logger.debug('Không thể đọc cache thông báo: %s', exc)
            exc = None
            del exc
            return []
            exc = None
            del exc



def save_cached_notifications(notifications = None):
    '''Lưu tối đa 10 thông báo gần nhất vào file bộ đệm cục bộ.'''
    
    try:
        _ensure_cache_dir()
        payload = {
            'notifications': notifications[:10],
            'updated_at': time.time(),
            'updated_at_str': datetime.now().strftime('%Y-%m-%d %H:%M:%S') }
        NOTIFICATION_CACHE_FILE.write_text(json.dumps(payload, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        return None
    except Exception:
        exc = None
        logger.warning('Không thể lưu cache thông báo: %s', exc)
        exc = None
        del exc
        return None
        exc = None
        del exc



def load_notification_state():
    '''Đọc trạng thái hiển thị thông báo (ngày hiển thị gần nhất, id đã xem...).'''
    
    try:
        if NOTIFICATION_STATE_FILE.is_file():
            raw = NOTIFICATION_STATE_FILE.read_text(encoding = 'utf-8')
            return json.loads(raw)
        return { }
    except Exception:
        return { }



def save_notification_state(state = None):
    '''Lưu trạng thái hiển thị thông báo.'''
    
    try:
        _ensure_cache_dir()
        NOTIFICATION_STATE_FILE.write_text(json.dumps(state, ensure_ascii = False, indent = 2), encoding = 'utf-8')
        return None
    except Exception:
        exc = None
        logger.warning('Không thể lưu trạng thái thông báo: %s', exc)
        exc = None
        del exc
        return None
        exc = None
        del exc



def fetch_latest_notifications(limit = None, force_online = None):
    '''Lấy danh sách thông báo mới nhất từ Supabase REST API hoặc fallback cache.

    Trả về tối đa `limit` thông báo (mặc định 10).
    '''
    (url, key) = get_supabase_config()
    if url and 'your-project' in url and key or 'your-anon' in key:
        return load_cached_notifications()
    target_url = f'''{None.rstrip('/')}/rest/v1/app_notifications?is_active=eq.true&order=created_at.desc&limit={limit}'''
    req = urllib.request.Request(target_url, headers = {
        'apikey': key,
        'Authorization': f'''Bearer {key}''',
        'Accept': 'application/json' }, method = 'GET')
    
    try:
        resp = urllib.request.urlopen(req, timeout = 6)
        data = json.loads(resp.read().decode('utf-8'))
        if isinstance(data, list):
            save_cached_notifications(data)
            
            try:
                None(None, None)
                return 
                
                try:
                    None(None, None)
                    return load_cached_notifications()
                    with None:
                        if not None, data[:limit]:
                            pass
                    
                    try:
                        return load_cached_notifications()
                        
                        try:
                            pass
                        except Exception:
                            logger.debug('Không thể tải thông báo trực tuyến từ Supabase (%s), sử dụng cache.', exc)
                            None = None
                            del exc
                            return load_cached_notifications()
                            exc = None
                            del exc







def should_show_startup_modal():
    '''Kiểm tra điều kiện hiển thị modal khởi động ứng dụng:

    Quy tắc nghiệp vụ:
    - Chỉ hiển thị 1 LẦN DUY NHẤT TRONG NGÀY (dựa trên ngày theo lịch YYYY-MM-DD).
    - Nếu hôm nay đã từng hiển thị và người dùng đã tắt modal -> KHÔNG hiển thị lại trong các lần mở app tiếp theo cùng ngày.
    - Nếu có thông báo đang hoạt động -> trả về (True, notification_item).
    - Nếu không có thông báo nào -> trả về (False, None).
    '''
    today_str = datetime.now().strftime('%Y-%m-%d')
    state = load_notification_state()
    last_shown_date = state.get('last_shown_date', '')
    if last_shown_date == today_str:
        return (False, None)
    items = fetch_latest_notifications(limit = 10, force_online = True)
    if not items:
        items = load_cached_notifications()
    if not items:
        return (False, None)
    newest = items[0]
    return (True, newest)


def mark_notification_shown_today(notif_id = None):
    '''Đánh dấu thông báo đã hiển thị trong ngày hôm nay.'''
    today_str = datetime.now().strftime('%Y-%m-%d')
    state = load_notification_state()
    state['last_shown_date'] = today_str
    if notif_id:
        state['last_shown_id'] = str(notif_id)
    state['last_shown_timestamp'] = time.time()
    save_notification_state(state)


def reset_daily_flag_for_test():
    '''Xóa cờ ngày hôm nay để test hiển thị modal.'''
    state = load_notification_state()
    state.pop('last_shown_date', None)
    save_notification_state(state)


def get_recent_notifications(limit = None, force_online = None):
    '''Lấy danh sách 10 thông báo gần nhất để hiển thị trong mục Tài Khoản.'''
    items = fetch_latest_notifications(limit = limit, force_online = force_online)
    if not items:
        items = load_cached_notifications()
    return items[:limit]


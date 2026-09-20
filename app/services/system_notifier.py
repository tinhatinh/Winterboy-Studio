# Source Generated with Decompyle++
# File: system_notifier.pyc (Python 3.12)

'''Dịch vụ thông báo Windows Native Toast Notifications.

Gửi thông báo hệ thống trực tiếp vào Windows Action Center (góc dưới bên phải màn hình)
khi các tác vụ dài hoàn tất (xuất video MP4/MP3, báo lỗi render).
Chạy hoàn toàn trong luồng nền (background thread), an toàn và không bao giờ làm đơ giao diện.
'''
from __future__ import annotations
import base64
import html
import logging
import subprocess
import sys
import threading
from pathlib import Path
logger = logging.getLogger(__name__)
APP_ID = 'Mumu Studio Pro'

def _send_toast_worker(title = None, message = None, app_id = None, sound = ('title', 'str', 'message', 'str', 'app_id', 'str', 'sound', 'bool', 'return', 'bool')):
    '''Worker thực thi gửi Toast qua PowerShell WinRT.'''
    if not sys.platform.startswith('win'):
        return False
    safe_title = html.escape(str(title).strip())
    safe_msg = html.escape(str(message).strip())
    audio_tag = '' if sound else "<audio silent='true'/>"
    xml_content = f'''<toast><visual><binding template=\'ToastGeneric\'><text>{safe_title}</text><text>{safe_msg}</text></binding></visual>{audio_tag}</toast>'''
    ps_xml = xml_content.replace("'", "''")
    ps_script = f'''[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;\n[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null;\n$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;\n$xml.LoadXml(\'{ps_xml}\');\n$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);\n$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(\'{app_id}\');\n$notifier.Show($toast);\n'''
    
    try:
        encoded = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
        proc = subprocess.run([
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-EncodedCommand',
            encoded], capture_output = True, text = True, encoding = 'utf-8', errors = 'replace', timeout = 8, creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 134217728))
        return proc.returncode == 0
    except Exception:
        exc = None
        logger.debug('Không thể gửi Windows toast notification: %s', exc)
        exc = None
        del exc
        return False
        exc = None
        del exc



def send_windows_toast(title = None, message = None, *, app_id, sound, async_call):
    '''Gửi thông báo Toast Windows Native.

    Args:
        title: Tiêu đề thông báo.
        message: Nội dung thông báo.
        app_id: Tên ứng dụng hiển thị trên đầu Toast.
        sound: Có phát âm thanh thông báo Windows không.
        async_call: Nếu True, chạy trong daemon thread để không chặn UI.
    '''
    if async_call:
        t = threading.Thread(target = _send_toast_worker, args = (title, message, app_id, sound), daemon = True, name = 'windows-toast-notifier')
        t.start()
        return None
    _send_toast_worker(title, message, app_id, sound)


def notify_render_complete(video_name = None, count = None, output_path = None):
    '''Thông báo khi render video MP4 hoàn tất.'''
    name = Path(video_name).name if video_name else 'video'
    if count > 1:
        msg = f'''Đã xuất hoàn tất {count} video (bao gồm {name})'''
    else:
        msg = f'''Video đã xuất hoàn tất: {name}'''
    send_windows_toast('Mumu Studio Pro · Xuất Video', msg)


def notify_render_error(error_msg = None):
    '''Thông báo khi tiến trình xuất video gặp sự cố.'''
    short_err = str(error_msg).strip()
    if len(short_err) > 120:
        short_err = short_err[:117] + '...'
    send_windows_toast('Mumu Studio Pro · Lỗi Xuất Video', f'''❌ {short_err}''')


def notify_mp3_complete(audio_name = None):
    '''Thông báo khi xuất file âm thanh MP3 hoàn tất.'''
    name = Path(audio_name).name if audio_name else 'audio.mp3'
    msg = f'''🎵 File âm thanh đã sẵn sàng: {name}'''
    send_windows_toast('Mumu Studio Pro · Âm Thanh', msg)


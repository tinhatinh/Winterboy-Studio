# Source Generated with Decompyle++
# File: downloader.pyc (Python 3.12)

import os
import requests
from config import ELEVENLABS_API_KEY, ELEVENLABS_BASE_URL

def download_audio(history_item_id = None, output_dir = None):
    '''
    Tải file MP3 của một history item về thư mục output_dir.
    Trả về đường dẫn tới file đã lưu.
    '''
    url = f'''{ELEVENLABS_BASE_URL}/history/{history_item_id}/download'''
    headers = {
        'xi-api-key': ELEVENLABS_API_KEY }
    resp = requests.get(url, headers = headers)
    resp.raise_for_status()
    os.makedirs(output_dir, exist_ok = True)
    output_path = os.path.join(output_dir, f'''{history_item_id}.mp3''')
    f = open(output_path, 'wb')
    f.write(resp.content)
    None(None, None)
    return output_path
    with None:
        if not None:
            pass
    return output_path


# Source Generated with Decompyle++
# File: __init__.pyc (Python 3.12)

'''Auto Render application package.'''
import os
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

# Phiên bản chỉ được khai báo ở ĐÂY một chỗ duy nhất.
# Bản đã phát hành ghi '1.01'; mọi chuỗi 'v1.01' nhìn thấy trong UI (tiêu đề cửa sổ,
# badge trên header, hộp Cài đặt) hiện còn nằm trong main_window.pyc /
# settings_dialog.pyc vì thân hai module đó chưa được khôi phục xong trong source —
# code object của main_window.py mới có 1/207. Vì thế chưa thể sửa chúng ở đây, và
# cũng không được thả main_window.py chưa khôi phục vào _internal để "đổi chữ": sẽ
# đè code đang chạy tốt bằng code thiếu. Nâng cấp thật sự diễn ra khi build lại từ
# source (build.bat) sau khi hai module kia đạt KHỚP HOÀN HẢO.
# tests/test_repo_health.py khoá số chỗ lệch so với .pyc ở ALLOWED_DRIFT, nên đổi
# phiên bản là hành động có khai báo, không phải lệch âm thầm.
__version__ = '1.2'
VERSION_LABEL = f'v{__version__}'

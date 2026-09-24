# Nhật ký phát hành

## v1.2 — 2026-09-24

Bản này chủ yếu là **sửa cho đúng** và thêm công cụ OCR, không đổi workflow. Điểm
xuyên suốt: mọi khẳng định "đã khớp bản phát hành" đều phải có bằng chứng máy kiểm
được, không dựa vào người đọc code thấy hợp lý.

### Mới

- **OCR phụ đề cứng trên video → SRT**, chạy bằng VideOCR (PaddleOCR) có sẵn, thêm
  thẳng vào ứng dụng: mục **OCR** trên thanh bên, cửa sổ độc lập `ocr_tool.pyw`, và
  `python tools/video_ocr.py clip.mp4` từ dòng lệnh. Lý do có OCR: nhận diện giọng
  nói nghe sai tên riêng và thuật ngữ (伯努利 → "Fourier"), còn OCR đọc nguyên văn
  chữ trên hình.
- **Xem trước video trong thẻ OCR** theo kiểu cửa sổ VideOCR: khung hình tự nạp,
  thanh trượt thời gian + nhãn giờ, nút Phát, và kéo chuột ngay trên ảnh để khoanh
  dải phụ đề. `FrameStream` giải mã cả video bằng **một** tiến trình ffmpeg xuất
  JPEG qua pipe, nên kéo thanh trượt đổi hình trong ~2–5 ms (cách cũ xin từng frame
  tốn tới 1,7 s mỗi nhịp).
- **Bảng giọng CapCut đầy đủ** (`app/services/capcut_voices.json`): 127 giọng, 24
  tiếng Việt, dropdown TTS liệt kê hết thay vì một mục duy nhất.
- Bộ test **484 test / 0 fail**, chạy không cần pytest hay mạng.
- Tool kiểm kê: `tools/audit_installed_app.py` (dựng thật cửa sổ app đã cài, lướt cả
  12 dụng cụ, và tính mọi bản ghi ERROR trong log là thất bại vì app nuốt exception
  im lặng) và `tools/audit_render_pipeline.py` (render thật rồi bắt `ffmpeg -v error`
  phải im lặng, so khung hình có/không phụ đề để chắc chắn chữ được burn thật).

### Sửa

- `--lang` của OCR: danh sách ngôn ngữ trước đó là **đoán**, chứa `zh` nên chọn
  tiếng Trung là chết. Đã đo lại bằng cách gọi thật `videocr-cli` với ~45 ứng viên;
  mã đúng là `ch` / `japan` / `korean`, tổng cộng 35 ngôn ngữ. Dropdown giờ hiện tên
  đầy đủ ("Chinese & English") và in rõ mã sẽ gửi. Lưu ý `ch` đọc được cả chữ Latin
  lẫn chữ Hán, còn `en` mất sạch chữ Hán.
- Thẻ OCR không dựng được panel: hàm khởi tạo tên là `_setup`, trùng
  `tkinter.Widget._setup` nội bộ mà `Frame.__init__` gọi lại. Import vẫn sạch, app
  vẫn chạy, chỉ im lặng mất cái tab.
- **Cổng so bytecode trước đây không so hằng số**, nên đổi chuỗi trong
  code/docstring không hề bị phát hiện — khiến các khẳng định "KHỚP HOÀN HẢO" cũ
  mạnh hơn bằng chứng. Sửa cổng xong, đo lại và thấy `main.py` lệch 13 chỗ, trong
  đó có lỗi thật:
  - `_activate_existing_instance` gọi `AttachThreadInput` qua **kernel32** (hàm đó
    thuộc user32) → bấm icon lần hai mở thêm cửa sổ mới thay vì bật cửa sổ cũ;
  - `_ensure_ffmpeg_on_path` thiếu `break` → quét hết danh sách ứng viên trong khi
    bản phát hành chỉ lấy ứng viên đầu tiên hợp lệ;
  - `main()` thiếu khối `finally: os._exit(0)` → thread nền còn sống sau khi đóng
    cửa sổ;
  - `__version__` `'3.5.6'` và AppUserModelID `'...1.0'` so với `'1.01'` của bản
    phát hành — hệ quả của một đợt đổi thương hiệu ghi đè cả chuỗi mã.
- `run_ocr` không absolute hoá đường dẫn trong khi tiến trình con chạy ở cwd của
  VideOCR → báo "chạy xong mà không có file SRT" khi gọi từ CLI.
- `--time_start` chỉ nhận `MM:SS`/`HH:MM:SS`; gõ `20` làm VideOCR dump nguyên bảng
  help. Thêm `normalize_time()` nhận `20`, `1:20`, `00:01:20`.
- Khung preview nằm gọn một góc trong khi viền to hơn: canvas `pack(fill='x')` bị
  Tk kéo rộng hơn ảnh còn ảnh neo góc trên-trái.
- `requirements.txt` khai báo `tkinter` (stdlib) làm `pip install -r` fail outright,
  và thiếu 9 gói code import vô điều kiện.
- `test_clear_logs_counts_temp_bytes` đỏ ngẫu nhiên: `clear_logs` cộng cả kích thước
  `winterboy_preview_audio` trong temp hệ thống, nên số đo phụ thuộc `%TEMP%` của
  máy lúc chạy.

### Phiên bản

`__version__` khai báo một chỗ duy nhất ở `app/__init__.py` = `1.2`. Chuỗi `v1.01`
còn hiển thị trong tiêu đề cửa sổ / badge / hộp Cài đặt đến từ `main_window.pyc` và
`settings_dialog.pyc`: thân hai module đó chưa được khôi phục xong trong source
(`main_window.py` mới có 1/207 code object), nên chưa có chỗ để đổi trong source.
Nó sẽ khớp khi build lại từ source sau khi hai module kia đạt KHỚP HOÀN HẢO.

### Trạng thái khôi phục mã nguồn

Ứng dụng chạy từ `.pyc` gốc; chỉ 5 file `.py` đang đè lên code phát hành
(`control_panel.py` và 4 file OCR), và `tools/audit_installed_app.py` bắt buộc mỗi
file trong số đó giải thích được sự lệch của nó. Nhóm đã khớp bytecode từng
instruction: xem `docs/RESTORE_STATUS.md`. Phần còn lại (thân hàm chưa dựng xong
trong các module GUI lớn) là việc còn mở, không phải lỗi ẩn.

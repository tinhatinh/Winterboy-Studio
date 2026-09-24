# CHANGELOG

## v1.2

**Mới**
- **OCR phụ đề cứng trên video → SRT**, tích hợp ngay trong ứng dụng: mục **OCR**
  trên thanh bên, cửa sổ độc lập, và `python tools/video_ocr.py clip.mp4`.
- **Xem trước video có thanh trượt thời gian + Phát**, kéo chuột trên khung hình để
  khoanh vùng cần OCR (chỉ đọc chữ trong vùng đã chọn).
- **Thêm 24 giọng tiếng Việt** cho CapCut TTS — dropdown giờ liệt kê đầy đủ
  127 giọng / 10 ngôn ngữ.
- Bộ test đối chiếu và các cổng kiểm mã nguồn (`tools/`).

**Sửa**
- Danh sách ngôn ngữ OCR khớp đúng VideOCR; dropdown hiển thị tên đầy đủ
  ("Chinese & English", "Vietnamese", …) thay vì mã viết tắt.
- Panel OCR không dựng được trong bản đã cài.
- Đường dẫn tương đối khi chạy OCR từ dòng lệnh.
- `requirements.txt` khai báo `tkinter` làm `pip install -r` thất bại.

## v1.01
- Phát hành lần đầu: phụ đề, lồng tiếng, che mờ, nhạc nền, logo, cắt, hiệu ứng
  lách bản quyền, dựng truyện.

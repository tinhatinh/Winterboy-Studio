# MumuStudio Pro (Winterboy Studio) - Open Source Edition ❄️

Chào mừng bạn đến với phiên bản mã nguồn mở của MumuStudio Pro (Winterboy Studio). Đây là công cụ đắc lực hỗ trợ các nhà sáng tạo nội dung, editor và tiktoker với hàng loạt tính năng xử lý video, AI tự động hoá chuyên nghiệp.

Phiên bản này đã được thiết kế lại hoàn toàn:
- **Bypass License 100%**: Loại bỏ toàn bộ yêu cầu đăng nhập, máy chủ kiểm tra bản quyền. Bạn có gói Lifetime vĩnh viễn mặc định!
- **Giao diện Light Mode**: Mặc định sử dụng giao diện Sáng (Light Theme) với tone màu xanh chủ đạo tươi mát thay vì giao diện tối ngột ngạt.
- **Tính năng Tuyết rơi (Snow Overlay)**: Bổ sung hiệu ứng tuyết rơi bắt mắt ngay trong màn hình làm việc, có thể **Bật/Tắt dễ dàng** thông qua nút bấm trên thanh Header.

---

## 🌟 Các tính năng nổi bật (Features)

1. **Auto Subtitle (Phụ đề tự động & Dịch thuật)**:
   - Nhận diện giọng nói STT (Speech-to-Text) thông qua Whisper / CapCut / ZeroTTS.
   - Dịch phụ đề tự động bằng AI (Gemini / Google Translate).
   - Chỉnh sửa, xuất/nhập file SRT dễ dàng.

2. **Text-To-Speech (Lồng tiếng AI - TTS)**:
   - Tích hợp rất nhiều Engine lồng tiếng: CapCut TTS, Edge TTS (Miễn phí), ElevenLabs, ZeroTTS.
   - Cho phép tinh chỉnh tốc độ, âm lượng, ghép nối audio khớp với timeline video.

3. **Chỉnh sửa Video & Render (Video Editor)**:
   - Che mờ (Blur) thông minh, làm mờ vùng chỉ định.
   - Cắt ghép (Trim) video đa phân đoạn.
   - Chèn Logo, Watermark tùy chỉnh có hiệu ứng chuyển động.
   - Tối ưu hóa render bằng FFmpeg (GPU Acceleration) cho tốc độ xuất cực nhanh.

4. **Story AI Creator (Tạo video tự động)**:
   - Dựng video hoàn toàn tự động dựa trên prompt và tài nguyên có sẵn.
   - Tự động tách nền (Vocal / BGM Separation) sử dụng thuật toán Demucs (AI).
   - Tự chọn nhạc nền (BGM), trộn âm lượng (Audio ducking) thông minh.

---

## 🚀 Hướng dẫn cài đặt và chạy từ mã nguồn

### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10 / 11.
- Môi trường: Python 3.10 đến 3.12.
- FFmpeg (cần thêm vào biến môi trường PATH để render video).

### Các bước chạy code:
1. **Tải mã nguồn**: Clone repository này về máy.
   ```bash
   git clone https://github.com/TEN_CUA_BAN/MumuStudio-OpenSource.git
   cd MumuStudio-OpenSource
   ```
2. **Cài đặt thư viện**:
   Dự án sử dụng nhiều thư viện xử lý hình ảnh và GUI, cài đặt qua pip:
   ```bash
   pip install customtkinter tkinter opencv-python pydub requests
   # (Và các thư viện cần thiết khác tuỳ theo tính năng bạn sử dụng)
   ```
3. **Khởi chạy ứng dụng**:
   ```bash
   python main.py
   ```

---

## ⚖️ Giấy phép (License)
Dự án được giải phóng mã nguồn mở hoàn toàn nhằm mục đích học tập, nghiên cứu và phát triển cộng đồng (Community Fork). Mọi người đều có thể tự do phát triển thêm tính năng, đóng góp mã nguồn mà không lo ngại vấn đề giới hạn bản quyền gốc.

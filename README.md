# Winterboy Studio - Open Source Edition ❄️

Chào các đạo hữu, sau 1 thời gian mò mẫm reverse engineer ở trên các group MMO, tool thì cuối cùng t đã hiểu được workflow của các tool làm video trên đó. Winterboy Studio có hầu như đủ công cụ hỗ trợ các nhà sáng tạo nội dung, editor và tiktoker. Do t học an toàn cũng ko giỏi code lắm nên vibe code khá là nhiều, nhưng cốt lõi workflow thì đầy đủ, t open-source cho mọi người dùng chung, nếu bác nào muốn mày mò thì cứ fork về làm tiếp

---

## 🌟 Các tính năng nổi bật (Features)

1. **Auto Subtitle (Phụ đề tự động & Dịch thuật)**:
   - Nhận diện giọng nói STT (Speech-to-Text) thông qua Whisper / CapCut / ZeroTTS.
   - Dịch phụ đề tự động bằng AI (Gemini / Google Translate).
   - Chỉnh sửa, xuất/nhập file SRT dễ dàng.

2. **Text-To-Speech (Lồng tiếng AI - TTS)**:
   - Tích hợp rất nhiều Engine lồng tiếng: CapCut TTS, Edge TTS, ElevenLabs, ZeroTTS, VietneuTTS(clone voice).
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

## 📥 Tải về và sử dụng ngay (Không cần cài đặt)
Bạn không cần phải biết code hay tự build lại phần mềm! Chỉ cần tải bản đóng gói sẵn (.exe) và sử dụng ngay:
1. Nhấn vào mục **[Releases]** ở menu bên phải của trang GitHub này (hoặc biểu tượng tag).
2. Tải về file `WinterboyStudio_OpenSource_Release.zip`.
3. Giải nén ra một thư mục bất kỳ.
4. Chạy file `WinterboyStudio.exe` để bắt đầu làm việc!

---

## 🚀 Dành cho nhà phát triển (Chạy từ mã nguồn)

### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10 / 11.
- Môi trường: Python 3.10 đến 3.12.
- FFmpeg (cần thêm vào biến môi trường PATH để render video).

### Các bước chạy code:
1. **Tải mã nguồn**: Clone repository này về máy.
   ```bash
   git clone https://github.com/TEN_CUA_BAN/WinterboyStudio-OpenSource.git
   cd WinterboyStudio-OpenSource
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

# Winterboy Studio - Open Source Edition ❄️

**Phiên bản: v1.2**

Chào các đạo hữu,

Sau một thời gian mò mẫm reverse engineer các tool trên những group MMO, cuối cùng mình cũng hiểu được workflow phía sau cách các tool làm video hoạt động.

Vì vậy mình build Winterboy Studio - một bộ công cụ tương đối đầy đủ để hỗ trợ các nhà sáng tạo nội dung, editor và TikToker trong quá trình làm video.

Do mình học An toàn thông tin và cũng không quá giỏi code nên project có khá nhiều đoạn được vibe code. Tuy nhiên, phần cốt lõi về workflow và các chức năng chính thì mình đã hoàn thiện tương đối đầy đủ.

Mình quyết định open-source Winterboy Studio để mọi người có thể dùng chung. Bác nào hứng thú muốn nghiên cứu, customize hoặc phát triển thêm thì cứ fork về làm tiếp.

Hy vọng project có thể hữu ích cho anh em.

![Winterboy Studio Preview](assets/ui_preview.png)

---

## 🌟 Các tính năng nổi bật (Features)

1. **Auto Subtitle (Phụ đề tự động & Dịch thuật)**:
   - Nhận diện giọng nói STT (Speech-to-Text) thông qua Whisper / CapCut / ZeroTTS.
   - Dịch phụ đề tự động bằng AI (Gemini / Google Translate).
   - Chỉnh sửa, xuất/nhập file SRT dễ dàng.

2. **Text-To-Speech (Lồng tiếng AI - TTS)**:
   - Tích hợp rất nhiều Engine lồng tiếng: CapCut TTS, Edge TTS, ElevenLabs, ZeroTTS, VietneuTTS(clone voice).
   - Kho giọng CapCut cloud mở khoá: **24 giọng tiếng Việt** (và 103 giọng ngôn ngữ khác) nạp thẳng vào dropdown, xem mục [Danh sách giọng CapCut](#-danh-sách-giọng-capcut-voice-catalog).
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

5. **Chống quét bản quyền (Bypass / Reup MMO)**:
   - Các thuật toán xử lý video chuyên sâu: xáo trộn Subpixel, thêm nhiễu (Noise), đổi Colorspace.
   - Can thiệp tốc độ (Tempo), khung hình (GOP), thay đổi Zoom/Pan động (Dynamic motion) để né thuật toán dò trùng lặp.
   - Chế độ **Ultimate Bypass** giúp lách bản quyền nền tảng (TikTok, YouTube), tạo ra video 100% unique cho dân Reup.

---

## 📥 Tải về và sử dụng ngay (Không cần cài đặt)
Bạn không cần phải biết code hay tự build lại phần mềm! Chỉ cần tải bản đóng gói sẵn (.exe) và sử dụng ngay:
1. Nhấn vào mục **[Releases]** ở menu bên phải của trang GitHub này (hoặc biểu tượng tag).
2. Tải về file `WinterboyStudio_OpenSource_Release.zip`.
3. Giải nén ra một thư mục bất kỳ.
4. Chạy file `WinterboyStudio.exe` để bắt đầu làm việc!

> **Về số phiên bản hiển thị trong giao diện.** `__version__` khai báo một chỗ duy
> nhất ở `app/__init__.py` (hiện là `1.2`). Chuỗi `v1.01` bạn còn thấy trên tiêu đề
> cửa sổ, badge trên header và hộp Cài đặt đến từ `main_window.pyc` /
> `settings_dialog.pyc`: thân hai module đó chưa được khôi phục xong trong source
> (`main_window.py` mới có 1/207 code object), nên chưa có chỗ để đổi chữ trong
> source. Đây là điểm khác biệt giữa "mã nguồn" và "bản đã build" cần nói thẳng,
> không phải chỗ bị bỏ quên — nó sẽ khớp khi build lại từ source bằng `build.bat`.

---

## 🚀 Dành cho nhà phát triển (Chạy từ mã nguồn)

### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10 / 11.
- Môi trường: Python 3.10 đến 3.12 (bản đã phát hành biên dịch bằng 3.12).
- FFmpeg (phải có trên `PATH` để render video).

### Các bước chạy code:
1. **Tải mã nguồn**: Clone repository này về máy.
   ```bash
   git clone https://github.com/tinhatinh/Winterboy-Studio.git
   cd Winterboy-Studio
   ```
2. **Cài đặt thư viện**:
   ```bash
   pip install -r requirements.txt
   ```
   `tkinter` KHÔNG cần cài vì nó đi kèm CPython. Các nhóm nặng (torch/onnxruntime
   cho ZeroTTS, demucs cho tách lời) có chú thích riêng trong `requirements.txt`.
3. **Kiểm tra mã nguồn trước khi sửa**:
   ```bash
   python tools/check_source.py --damaged --parity   # cổng kiểm tổng
   python tools/compare_bytecode.py --all            # bao nhiêu module khớp bytecode
   ```
4. **Khởi chạy ứng dụng**:
   ```bash
   python main.py
   ```
   **Hiện vẫn chưa chạy được từ source, nói thẳng để bạn khỏi mất công debug.**
   Tính tới bản này, `app/ui/main_window.py` mới khôi phục được 1/207 code object
   nên cửa sổ chính còn trống; `import main` thì OK nhưng nạp `app.ui.control_panel`
   sẽ fail. Muốn dùng ngay, tải Release zip ở mục trên. Muốn đóng góp, hãy sửa các
   module rồi chạy `tools/audit_installed_app.py` — tool dựng thật cửa sổ của **bản đã
   cài** nên bắt được cả lỗi mà `import` không lộ.

---

## ⚖️ Giấy phép (License)
Dự án được giải phóng mã nguồn mở hoàn toàn nhằm mục đích học tập, nghiên cứu và phát triển cộng đồng (Community Fork). Mọi người đều có thể tự do phát triển thêm tính năng, đóng góp mã nguồn mà không lo ngại vấn đề giới hạn bản quyền gốc.

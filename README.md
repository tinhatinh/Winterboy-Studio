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

2. **OCR phụ đề cứng (Extract Burned-in Subtitles)**:
   - Đọc chữ hardsub trên video (phụ đề Trung Quốc, text cài sẵn trong khung hình) rồi xuất ra SRT.
   - Xem trước từng khung hình, kéo thanh trượt đến câu cần lấy, kéo chuột chọn vùng OCR.
   - Chọn ngôn ngữ theo tên đầy đủ (Chinese & English, Vietnamese, English, …).
   - Có sẵn ở panel bên phải, làm độc lập (`tools/video_ocr.py`) hoặc chạy bằng lệnh.

3. **Text-To-Speech (Lồng tiếng AI - TTS)**:
   - Tích hợp rất nhiều Engine lồng tiếng: CapCut TTS, Edge TTS, ElevenLabs, ZeroTTS, VietneuTTS(clone voice).
   - Kho giọng CapCut cloud: **127 giọng / 10 ngôn ngữ**, trong đó **24 giọng tiếng Việt**, nạp thẳng vào dropdown.
   - Cho phép tinh chỉnh tốc độ, âm lượng, ghép nối audio khớp với timeline video.

4. **Chỉnh sửa Video & Render (Video Editor)**:
   - Che mờ (Blur) thông minh, làm mờ vùng chỉ định.
   - Cắt ghép (Trim) video đa phân đoạn.
   - Chèn Logo, Watermark tùy chỉnh có hiệu ứng chuyển động.
   - Tối ưu hóa render bằng FFmpeg (GPU Acceleration) cho tốc độ xuất cực nhanh.

5. **Story AI Creator (Tạo video tự động)**:
   - Dựng video hoàn toàn tự động dựa trên prompt và tài nguyên có sẵn.
   - Tự động tách nền (Vocal / BGM Separation) sử dụng thuật toán Demucs (AI).
   - Tự chọn nhạc nền (BGM), trộn âm lượng (Audio ducking) thông minh.

6. **Chống quét bản quyền (Bypass / Reup MMO)**:
   - Các thuật toán xử lý video chuyên sâu: xáo trộn Subpixel, thêm nhiễu (Noise), đổi Colorspace.
   - Can thiệp tốc độ (Tempo), khung hình (GOP), thay đổi Zoom/Pan động (Dynamic motion) để né thuật toán dò trùng lặp.
   - Chế độ **Ultimate Bypass** giúp lách bản quyền nền tảng (TikTok, YouTube), tạo ra video 100% unique cho dân Reup.

---

## 📕 Cài VideOCR để dùng tính năng OCR

Chức năng OCR phụ đề cứng chạy qua **VideOCR** (PaddleOCR, mã mở, giấy phép MIT) — một
chương trình độc lập, Winterboy Studio chỉ gọi `videocr-cli.exe` của nó, nên bản phát hành
**không kèm engine này**. Chưa cài thì vào mục OCR app sẽ báo *"Không tìm thấy
videocr-cli.exe"*, còn lại mọi chức năng khác vẫn dùng bình thường.

1. Vào <https://github.com/timminator/VideOCR/releases>, tải **một** file `.exe` cho đúng máy
   (số liệu theo bản v1.6.0):

   | Máy của bạn | File cần tải | Nặng khoảng |
   | --- | --- | --- |
   | Có card NVIDIA, driver còn mới | `VideOCR-GPU-v1.6.0-CUDA-12.9-setup-x64.exe` | 1,65 GB |
   | Có card NVIDIA, driver chỉ tới CUDA 11.x | `VideOCR-GPU-v1.6.0-CUDA-11.8-setup-x64.exe` | 1,33 GB |
   | Không có card NVIDIA | `VideOCR-CPU-v1.6.0-setup-x64.exe` | 516 MB |

   Gõ `nvidia-smi` ở Command Prompt rồi nhìn cột **CUDA Version** để biết nên chọn bản CUDA
   nào. Ưu tiên bản GPU: bản CPU chậm hơn rõ rệt, chỉ dùng khi máy không có NVIDIA.

2. Cứ để thư mục cài mặc định `C:\Program Files\VideOCR` — không phải cấu hình gì thêm.
   Studio tự dò engine theo thứ tự: biến môi trường → `C:\Program Files\VideOCR` →
   `C:\Program Files (x86)\VideOCR` → `%LOCALAPPDATA%\Programs\VideOCR` → `PATH`.

   Muốn đặt VideOCR ở chỗ khác thì khai một biến môi trường trước khi mở Studio —
   `WINTERBOY_VIDEOCR`, `VIDEOOCR_CLI` hoặc `VIDEOOCR_HOME` — giá trị là đường dẫn tới file
   `videocr-cli.exe` **hoặc** tới thư mục chứa nó.

3. Mở Studio → mục **OCR** → chọn video. App bật CUDA theo mặc định, nên nếu bạn cài bản
   **CPU** thì bỏ dấu chọn **"Dùng GPU (CUDA)"** trong panel OCR trước khi chạy, nếu không
   lần OCR sẽ thất bại.

VideOCR là dự án độc lập của [timminator](https://github.com/timminator/VideOCR), giấy phép
MIT; các model OCR đi kèm do
[PaddleOCR-Standalone](https://github.com/timminator/PaddleOCR-Standalone) cung cấp.

---

## 🚀 Dành cho nhà phát triển

### Yêu cầu
- Windows 10 / 11, Python 3.10 – 3.12 (bản phát hành dùng 3.12).
- FFmpeg có trên `PATH` (bắt buộc để render video).
- VideOCR cho riêng tính năng OCR: xem mục
  [Cài VideOCR để dùng tính năng OCR](#-cài-videocr-để-dùng-tính-năng-ocr).

`tkinter` đi kèm CPython nên không cần cài. Nhóm nặng (torch / onnxruntime cho
ZeroTTS, demucs cho tách lời) có chú thích riêng trong `requirements.txt`.

Muốn đóng gói thành `.exe`: chạy `build.bat`, kết quả ở `dist/`.

Trước khi mở PR, chạy `python tools/check_source.py --damaged` để chắc không có file
nào vừa sửa thành mã không hợp lệ.

> **Cần dùng ngay hôm nay?** Lấy bản đóng gói ở mục [Releases](../../releases).
> Source của ứng dụng đang được cập nhật dần cho khớp bản phát hành, nên một số
> module chưa chạy được từ mã nguồn.

---

## ⚖️ Giấy phép (License)
Dự án được giải phóng mã nguồn mở hoàn toàn nhằm mục đích học tập, nghiên cứu và phát triển cộng đồng (Community Fork). Mọi người đều có thể tự do phát triển thêm tính năng, đóng góp mã nguồn mà không lo ngại vấn đề giới hạn bản quyền gốc.

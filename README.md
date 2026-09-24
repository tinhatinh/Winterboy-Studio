# Winterboy Studio - Open Source Edition ❄️

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

---

## 🚀 Dành cho nhà phát triển (Chạy từ mã nguồn)

### Yêu cầu hệ thống:
- Hệ điều hành: Windows 10 / 11.
- Môi trường: Python 3.10 đến 3.12.
- FFmpeg (cần thêm vào biến môi trường PATH để render video).

### Các bước chạy code:
1. **Tải mã nguồn**: Clone repository này về máy.
   ```bash
   git clone https://github.com/tinhatinh/Winterboy-Studio.git
   cd Winterboy-Studio
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

## 🗣️ Danh sách giọng CapCut (Voice catalog)

Engine CapCut TTS đọc kho giọng từ **`app/services/capcut_voices.json`**. Có file là dropdown
trong ứng dụng hiện đầy đủ giọng, không cần sửa code; thiếu file thì chỉ còn 1 giọng mặc định.

Bản đang có trong repo: **127 giọng / 10 ngôn ngữ** (en-US 40, **vi-VN 24**, ja-JP 19, zh-CN 15,
es-ES 9, th-TH 6, id-ID 4, pt-BR 4, de-DE 3, fr-FR 3), xếp tiếng Việt lên đầu.

24 giọng tiếng Việt — `voice_type:resource_id` nằm trong file JSON:

> Alex Đại Đế · Ban Mai · Bản Tin 1 · Bản Tin nữ · Cô Gái Hoạt Ngôn · Giọng Bé · Giọng Gái Mới Lớn ·
> Giọng Nam Trầm · Giọng Nữ Phổ Thông · Kenny Đại Đế · Mai · Nam bản tin · Nhỏ Ngọt Ngào ·
> Quên Tên Tự Test · Review Phim 2 · Review Phim 3 · Review Phim 4 · Review Phim new · Robot VN ·
> Sunny Idol · Thanh Niên Tự Tin · Việt Méo · Hoai My · Nam Minh

Dòng định dạng mỗi phần tử (thừa khoá thì engine bỏ qua):

```json
{
  "display_name": "Nhỏ Ngọt Ngào",
  "voice_type": "BV421_vivn_streaming",
  "resource_id": "7252594014782755330",
  "lang": "vi-VN",
  "lan": "vi",
  "captured_at": "2026-04-16T16:54:58.535653",
  "verified": true
}
```

### Kiểm chứng giọng nào thực sự sinh được audio

Catalog chỉ là danh sách do CapCut trả về; có giọng bị gắn quyền riêng nên gọi vẫn nhận `failed`
(Hoai My và Nam Minh trong danh sách trên là hai giọng như vậy, đã đánh dấu `"verified": false`).
Chạy tool để dò lại và ghi kết quả vào file:

```bash
python tools/verify_capcut_voices.py --lang vi --write
# bản đã cài đặt (bỏ qua mã nguồn chưa hoàn chỉnh):
python tools/verify_capcut_voices.py --lang vi --write --engine "C:/WinterboyStudio/_internal"
```

### Lưu ý khi build

`build.bat` đã truyền `--add-data "app/services/capcut_voices.json;app/services"` để file nằm đúng
chỗ `_internal/app/services/` trong bản đóng gói. Ngoài ra cần device profile thật ở
`~/.winterboy/capcut_device.json`, nếu không CapCut sẽ trả `shark block only` (chống bot).

---

## ⚖️ Giấy phép (License)
Dự án được giải phóng mã nguồn mở hoàn toàn nhằm mục đích học tập, nghiên cứu và phát triển cộng đồng (Community Fork). Mọi người đều có thể tự do phát triển thêm tính năng, đóng góp mã nguồn mà không lo ngại vấn đề giới hạn bản quyền gốc.

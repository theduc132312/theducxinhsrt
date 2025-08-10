# theducxinhsrt

Desktop SRT Translator (build to `.exe` via GitHub Actions)

## Mục tiêu
- Dịch file `.srt` sang ngôn ngữ đích (EN / VI / FR / ES) bằng Gemini (Google).
- Đảm bảo **không chồng chéo thời gian**; nếu phát hiện, app ép `start_next = end_prev`.
- Chọn chế độ dịch: **Nhanh** (tiết kiệm token) hoặc **Mượt + Hài** (dịch sáng tạo).
- Xuất file `<originalname>_translated.srt`.

## Files
- `main.py` - ứng dụng Python (PySimpleGUI) chính.
- `requirements.txt` - dependencies.
- `.github/workflows/build.yml` - workflow build `.exe`.
- `README.md` - hướng dẫn này.

## Hướng dẫn nhanh (push lên GitHub & build exe)
1. Tạo repo trống trên GitHub (ví dụ `yourname/theducxinhsrt`).
2. Clone repo về local, copy toàn bộ file trong thư mục này vào repo local.
3. Commit & push lên `main` (hoặc `master`) branch.
4. Vào tab **Actions** trên trang repo GitHub - workflow `Build theducxinhsrt exe (Windows)` sẽ chạy. Nếu không tự chạy, vào workflow và click **Run workflow**.
5. Khi workflow hoàn tất, mở run -> **Artifacts** -> download artifact `theducxinhsrt-exe`. Bên trong có file `theducxinhsrt.exe`.
6. Tải file `.exe` về máy Windows, chạy:
   - Lần đầu app sẽ yêu cầu **API Key (Gemini)** — nhập API key của bạn rồi bấm Save Key.
   - Chọn file `.srt`, chọn ngôn ngữ, chọn chế độ dịch, bấm Translate. Khi xong bấm Export để lưu file dịch.

## Lưu ý
- **Không** lưu API key vào repo; app lưu key cục bộ ở `~/.theducxinhsrt_config.json` khi bạn bấm Save Key.
- Để dùng Gemini, bạn cần có API key từ Google (Gemini). Mình khuyên dùng model `gemini-2.0-flash` nếu có.
- Workflow build không chèn API key nào; tất cả key chỉ nhập khi chạy exe.
- Nếu `google-generativeai` không hoạt động, bạn cần cài thêm hoặc chỉnh code gọi HTTP. Phiên bản trong `requirements.txt` là ví dụ.

## Nếu cần
- Muốn mình thay `main.py` để dùng HTTP POST (curl-like) thay vì thư viện `google-generativeai`, mình chỉnh được.
- Muốn mình build và upload file `.exe` thay bạn (mình có thể hướng dẫn hoặc thực hiện theo phương án B — cần token GitHub để push), liên hệ và mình hướng dẫn tiếp.

Chúc bạn dùng ngon!

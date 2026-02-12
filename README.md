# Phần mềm chuyển ghi âm sang văn bản tự động

Dự án này giúp bạn chuyển file ghi âm (`.wav`, `.mp3`, `.m4a`, …) sang văn bản bằng **OpenAI Whisper**, có cả chế độ theo dõi thư mục để tự động xử lý khi có file mới.

## 1) Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Lưu ý: Whisper cần `ffmpeg` để đọc file audio/video.

## 2) Chạy chuyển đổi một lần

### Chuyển 1 file

```bash
python transcribe.py --input ./recordings/ghi_am_01.m4a --output ./output/ghi_am_01.txt --model base --language vi
```

### Chuyển tất cả file trong thư mục

```bash
python transcribe.py --input ./recordings --output ./output --model base --language vi
```

## 3) Chế độ tự động (watch folder)

Lệnh dưới sẽ:
- quét các file có sẵn trong thư mục `recordings`
- tiếp tục theo dõi thư mục này
- khi có file ghi âm mới, tự động chuyển sang `.txt`

```bash
python transcribe.py --input ./recordings --output ./output --watch --model base --language vi
```

## 4) Tùy chọn hữu ích

- `--model`: `tiny`, `base`, `small`, `medium`, `large`
- `--language`: ví dụ `vi`, `en` (để trống để model tự nhận diện)
- `--task transcribe|translate`: ghi lại đúng ngôn ngữ hoặc dịch sang tiếng Anh
- `--interval`: số giây chờ trước khi xử lý file mới (mặc định `1.0`)

## 5) Gợi ý cho tiếng Việt chính xác hơn

- Dùng model lớn hơn (`small` hoặc `medium`) nếu máy đủ mạnh.
- Ghi âm rõ, ít tạp âm.
- Dùng micro gần người nói.

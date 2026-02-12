#!/usr/bin/env python3
"""Chuyển âm thanh ghi âm sang văn bản bằng Whisper.

Ví dụ:
  python transcribe.py --input recordings --output transcripts --watch
  python transcribe.py --input audio.wav --output output.txt --model small
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import whisper

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # watchdog là tùy chọn khi không dùng --watch
    FileSystemEventHandler = object
    Observer = None

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".webm", ".mp4"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tự động chuyển file ghi âm sang văn bản bằng OpenAI Whisper",
    )
    parser.add_argument("--input", required=True, help="Đường dẫn file hoặc thư mục chứa audio")
    parser.add_argument("--output", required=True, help="File .txt đầu ra hoặc thư mục lưu transcript")
    parser.add_argument("--model", default="base", help="Model Whisper: tiny, base, small, medium, large")
    parser.add_argument("--language", default=None, help="Mã ngôn ngữ (vd: vi, en). Để trống để tự nhận diện")
    parser.add_argument(
        "--task",
        default="transcribe",
        choices=["transcribe", "translate"],
        help="transcribe: giữ nguyên ngôn ngữ, translate: dịch sang tiếng Anh",
    )
    parser.add_argument("--watch", action="store_true", help="Theo dõi thư mục và chuyển đổi tự động khi có file mới")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Số giây chờ trước khi xử lý file mới (giảm lỗi khi file còn đang ghi)",
    )
    return parser.parse_args()


def is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def output_path_for(input_file: Path, output_arg: Path) -> Path:
    if output_arg.suffix.lower() == ".txt":
        return output_arg
    return output_arg / f"{input_file.stem}.txt"


def transcribe_file(model: whisper.Whisper, audio_path: Path, output_path: Path, language: str | None, task: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Đang xử lý: {audio_path}")
    result = model.transcribe(str(audio_path), language=language, task=task)
    text = result.get("text", "").strip()
    output_path.write_text(text + "\n", encoding="utf-8")
    print(f"[OK] Đã lưu transcript: {output_path}")


class AutoTranscribeHandler(FileSystemEventHandler):
    def __init__(
        self,
        model: whisper.Whisper,
        output_dir: Path,
        language: str | None,
        task: str,
        interval: float,
    ) -> None:
        self.model = model
        self.output_dir = output_dir
        self.language = language
        self.task = task
        self.interval = interval
        self.processed: set[Path] = set()

    def on_created(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        self._try_process(path)

    def on_moved(self, event):  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.dest_path)
        self._try_process(path)

    def _try_process(self, path: Path) -> None:
        if not is_audio_file(path) or path in self.processed:
            return
        time.sleep(self.interval)
        try:
            transcribe_file(
                model=self.model,
                audio_path=path,
                output_path=output_path_for(path, self.output_dir),
                language=self.language,
                task=self.task,
            )
            self.processed.add(path)
        except Exception as exc:
            print(f"[ERROR] Không thể xử lý {path}: {exc}", file=sys.stderr)


def run_once(model: whisper.Whisper, input_path: Path, output_path: Path, language: str | None, task: str) -> int:
    if input_path.is_file():
        if not is_audio_file(input_path):
            print("[ERROR] File đầu vào không phải định dạng audio được hỗ trợ.", file=sys.stderr)
            return 1
        transcribe_file(model, input_path, output_path_for(input_path, output_path), language, task)
        return 0

    if not input_path.is_dir():
        print("[ERROR] --input phải là file hoặc thư mục tồn tại.", file=sys.stderr)
        return 1

    files = sorted(p for p in input_path.iterdir() if is_audio_file(p))
    if not files:
        print("[WARN] Không tìm thấy file audio nào trong thư mục input.")
        return 0

    for audio_file in files:
        transcribe_file(model, audio_file, output_path_for(audio_file, output_path), language, task)
    return 0


def run_watch(model: whisper.Whisper, input_dir: Path, output_dir: Path, language: str | None, task: str, interval: float) -> int:
    if Observer is None:
        print("[ERROR] Chưa cài watchdog. Hãy chạy: pip install watchdog", file=sys.stderr)
        return 1
    if not input_dir.is_dir():
        print("[ERROR] --watch chỉ dùng khi --input là thư mục.", file=sys.stderr)
        return 1

    print("[INFO] Quét các file hiện có trước khi bật theo dõi...")
    run_once(model, input_dir, output_dir, language, task)

    handler = AutoTranscribeHandler(model, output_dir, language, task, interval)
    observer = Observer()
    observer.schedule(handler, str(input_dir), recursive=False)

    print(f"[INFO] Đang theo dõi thư mục: {input_dir}")
    print("[INFO] Nhấn Ctrl+C để dừng.")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Dừng theo dõi.")
    finally:
        observer.stop()
        observer.join()
    return 0


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    print(f"[INFO] Đang tải model Whisper: {args.model}")
    model = whisper.load_model(args.model)

    if args.watch:
        return run_watch(model, input_path, output_path, args.language, args.task, args.interval)
    return run_once(model, input_path, output_path, args.language, args.task)


if __name__ == "__main__":
    raise SystemExit(main())

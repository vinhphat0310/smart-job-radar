# Development Log

## 2026-08-21

### Đã hoàn thành
- Tạo repository Smart Job Radar.
- Tạo branch VinhPhat.
- Clone repository về máy.
- Tạo môi trường Python `.venv`.
- Tạo cấu trúc dự án ban đầu.

### Cập nhật kiến trúc
- Chốt database chính V1: PostgreSQL chạy trên Neon; lưu `jobs`, `scores`, `notifications`, `runs`, `source_runs`.
- Dự kiến SQLAlchemy + psycopg; chỉ thêm Alembic khi bắt đầu quản lý schema/migration. SQLite không dùng làm database chính; S3-compatible ngoài phạm vi V1.

### Telegram milestone
- Hoàn thành: thêm gửi tin nhắn thử qua Telegram Bot API bằng biến môi trường; `.env.example` cung cấp tên biến an toàn.
- Kiểm tra: cần điền token và chat ID cục bộ để gửi tin nhắn thật.

### Neon connection milestone
- Hoàn thành: thêm kiểm tra kết nối PostgreSQL/Neon bằng `SELECT 1` qua `DATABASE_URL`; chưa tạo schema hoặc bảng.

### PostgreSQL schema milestone
- Hoàn thành: cập nhật SQLAlchemy models và Alembic migration đầu tiên theo contract V1 cho `sources`, `jobs`, `job_occurrences`, `search_profiles`, `scores`, `notifications`, `runs`, `source_runs`, `job_status_history`.
- Hoàn thành: migration `20260821_01` đã áp dụng thành công lên Neon PostgreSQL.
- Kiểm tra: `.venv/bin/alembic upgrade head` pass; `.venv/bin/python src/main.py --check-schema` xác nhận schema; `.venv/bin/alembic current` là `20260821_01 (head)`.

- Ghi chú V1: dedupe dùng `fingerprint`; khi cần nhận diện repost, mở rộng bằng company/title/location và thời gian repost. Retry notification cập nhật cùng bản ghi `job/profile/channel` và `last_attempt_run_id`; chưa có `notification_attempts`.

### RemoteOK adapter milestone
- Hoàn thành: thêm `NormalizedJob`, adapter contract và RemoteOK public JSON adapter; bỏ qua metadata/bản ghi không phải job, chuẩn hóa chuỗi trống, ngày, URL, remote mode và salary nguồn.
- Kiểm tra: `python3 -m unittest discover -s tests`; `python3 -m py_compile src/*.py src/adapters/*.py`; `python3 src/main.py --fetch-remoteok`; `git diff --check`.
- Phạm vi: `--fetch-remoteok` chỉ fetch/normalize/in tối đa 3 ví dụ, không ghi PostgreSQL hoặc gửi Telegram.

### Tiếp theo
- Điền cấu hình Telegram cục bộ và xác nhận gửi tin nhắn thật.
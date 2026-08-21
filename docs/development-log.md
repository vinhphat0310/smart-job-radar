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

### Tiếp theo
- Tạo Telegram Bot.
- Gửi thử tin nhắn bằng Python.
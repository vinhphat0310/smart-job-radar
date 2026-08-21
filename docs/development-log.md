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

### Tiếp theo
- Điền cấu hình Telegram cục bộ và xác nhận gửi tin nhắn thật.
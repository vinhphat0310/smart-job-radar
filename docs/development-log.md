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

### RemoteOK persistence milestone
- Hoàn thành: thêm fingerprint xác định theo company/title/location với chuẩn hóa Unicode/casefold/khoảng trắng; `--sync-remoteok` ghi `sources`, `jobs`, `job_occurrences` qua savepoint từng job.
- Hoàn thành: exact match theo `source_job_id` rồi canonical URL cập nhật `last_seen_at`/`fetched_at`; fingerprint khớp tạo occurrence cross-source; thống kê `fetched`, `new_jobs`, `new_occurrences`, `exact`, `cross_source`, `failed`.
- Kiểm tra: `pytest`; `python3 -m py_compile src/*.py src/adapters/*.py`; `python3 src/main.py --fetch-remoteok`; `git diff --check`.
- Hoàn thành: đã sync Neon thật thành công hai lần; lần thứ hai phát hiện `100` exact duplicates, không tạo job hoặc occurrence trùng.

### Config validation and hard filters milestone
- Hoàn thành: thêm `SearchProfile` YAML, validation source-independent và hard filters case-insensitive, cấu hình được tại `config/search-profile.yaml`.
- Kiểm tra: `pytest`; `python3 -m py_compile src/*.py src/adapters/*.py`; `python3 src/main.py --filter-remoteok`; `git diff --check`.
- Phạm vi: `--filter-remoteok` chỉ fetch/validate/filter/in tối đa 3 ví dụ, không ghi PostgreSQL hoặc gửi Telegram.

### Milestone 6 relevance filtering
- Hoàn thành: cấu hình profile IT/IT Support/Technical Support/QA và junior/fresher/intern, remote cùng part-time/freelance/internship; hard filter tìm include/exclude trong title, description và trường job liên quan.
- Kiểm tra: `python3 -m py_compile src/*.py src/adapters/*.py`; `.venv/bin/python -m pytest`; `python3 src/main.py --filter-remoteok`; `git diff --check`.
- Phạm vi: criteria chỉ ở `config/search-profile.yaml`; salary/hours thiếu vẫn pass; không ghi PostgreSQL hoặc gửi Telegram.

### RemoteOK rejection analysis milestone
- Hoàn thành: `--filter-remoteok` in số rejected, tối đa ba lý do phổ biến và ba ví dụ title/lý do; chỉ phân tích kết quả hard filter đã có, không đổi quyết định lọc.
- Kiểm tra: `.venv/bin/python -m pytest` pass `8`; `python3 src/main.py --filter-remoteok` trả `rejected=100`, top `not_allowed:work_mode=96`, `no_include_keyword=68`, `excluded_keyword=15`; `git diff --check` pass.


### RemoteOK work mode mapping
- Hoàn thành: RemoteOK adapter chuẩn hóa mọi bản ghi hợp lệ từ public RemoteOK feed thành `work_mode="REMOTE"`; `location` là giới hạn/khu vực tuyển dụng, không phải tín hiệu on-site.
- Kiểm tra: live feed trả `100` job hợp lệ, toàn bộ thiếu `remote` và không có tag `remote`, nhưng URL là `/remote-jobs/`; `.venv/bin/python -m pytest`; `python3 src/main.py --filter-remoteok`; `git diff --check`.


### RemoteOK final filter result
- Kết quả: fetched `100`, valid `100`, passed `27`, rejected `73`.
- Top rejection: `no_include_keyword=68`, `excluded_keyword=15`.
- Fix: RemoteOK jobs được normalize `work_mode=REMOTE`.

### Tiếp theo
- Điền cấu hình Telegram cục bộ và xác nhận gửi tin nhắn thật.
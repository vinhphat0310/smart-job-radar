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

### Milestone 7 config-driven deterministic scoring
- Hoàn thành: thêm `minimum_score`, `scoring_weights` hợp lệ, scoring giải thích được 0..100 và `--score-remoteok`; không ghi PostgreSQL hoặc gửi Telegram.
- Kiểm tra: `python3 -m py_compile src/*.py src/adapters/*.py`, `.venv/bin/python -m pytest` pass 13, `git diff --check` pass; live score `fetched=100`, `valid=100`, `filtered=27`, `scored=27`, `passed=27`.
- Live top 3: `Account Officer`, `Accounts Receivable Clerk`, `Airport Ground Staff Freshers Kochi`, mỗi job score `75`.

### Milestone 7 scoring review fixes
- Hoàn thành: profile dùng `experience_keywords`; keyword/phrase matching không match trong từ dài hơn trên hard filter và scoring.
- Kiểm tra: `python3 -m py_compile src/*.py src/adapters/*.py`; `.venv/bin/python -m pytest` pass 15; `python3 src/main.py --score-remoteok` trả fetched 100, valid 100, filtered 2, scored 2, passed 2; `git diff --check` pass.
- Live top: `QA Tester Entry Level` score 75; `Collections Agent` score 60.

### Milestone 7 scoring configuration revision
- Hoàn thành: `minimum_score=80`; weights `field=25`, `include=25`, `employment=15`, `workmode=15`, `experience=10`, `location=5`, `recent=5`; parser bắt buộc đúng keys và tổng 100; CLI giữ toàn bộ job qua hard filter, in top score và đếm `qualified`.
- Kiểm tra: `.venv/bin/python -m pytest` pass 15; `git diff --check` pass; live `--score-remoteok`: `fetched=100`, `valid=100`, `filtered=2`, `scored=2`, `qualified=1`; top `QA Tester Entry Level` 80, `Collections Agent` 70.

### Milestone 7 approved fixes
- Hoàn thành: relevance include chỉ dùng `title`/`description`, exclude chỉ dùng `title`; `Help-Desk` khớp `Help Desk`; `work_mode` là required config thường; freshness chỉ 0..7 ngày; scoring reason ghi criterion và điểm dương, bỏ weight 0; raw score giữ riêng trước cap 100.
- Hoàn thành: loader bắt buộc `scoring_weights` đủ bảy key và tổng 100; `--score-remoteok` in explanation compact bằng dấu `;`.
- Kiểm tra: `.venv/bin/python -m pytest` pass 19; `python3 src/main.py --score-remoteok` trả fetched 99, valid 99, filtered 4, scored 4, qualified 0; `git diff --check` pass.

### Milestone 7 final profile cleanup
- Hoàn thành: `include_keywords` chỉ còn domain IT/QA; Fresher/Intern giữ ở `experience_keywords`; `employment_types` chỉ part-time/freelance/internship/intern; exclude bổ sung Senior/Lead/Manager.
- Kiểm tra: `.venv/bin/python -m pytest` pass 25; `python3 src/main.py --score-remoteok` trả fetched 99, valid 99, filtered 3, scored 3, qualified 0; top Collections Agent, DESARROLLADOR FULL STACK, Project Systems Specialist cùng score 70; `git diff --check` pass.
- Kết quả: Collections Agent vẫn pass live do title/description có domain keyword; Senior Specialist Global QMS không pass do title chứa Senior.

### Milestone 8 run lifecycle, source health, score persistence
- Hoàn thành: `--run-remoteok` reuse `search_profiles.default`/RemoteOK source, tạo một `runs` + `source_runs`, sync job, hard-filter, score và lưu mọi score cùng explanation; kết thúc run/source với counters/status thực tế, không gửi Telegram.
- Kiểm tra: `.venv/bin/python -m pytest` pass 28; Neon run 1 `run_id=1`: fetched/valid 99, filtered/scored 3, qualified/failed 0; run 2 `run_id=2`: cùng counters, deduplicated 99; `--check-db`, `--check-schema`, `git diff --check` pass.
- Neon xác nhận: runs 1/2 mỗi run có một source_run `OK`, fetched 99, accepted/scores 3; `search_profiles.default=1`, RemoteOK source=1, `job_occurrences=129`.

### Milestone 9 Telegram notification, persistence, dry-run
- Hoàn thành: `--run-remoteok` mặc định không gửi; `--notify` gửi từng job qualified chưa có notification `sent`; success/failure update cùng record notification, retry failure ở run sau; `--dry-run` không gọi Telegram và không ghi delivery state.
- Kiểm tra: `.venv/bin/python -m pytest` pass 39; `py_compile` main/persistence/telegram/tests pass; Neon dry-run `run_id=3`: fetched/valid 99, filtered/scored 3, qualified/candidates/sent/failed 0; run có `dry_run=true`, `notified_count=0`, không notification attempt/sent từ run dry-run; `git diff --check` pass.
- Live Telegram: không chạy vì live RemoteOK qualified=0; không hạ threshold hay gửi notification giả.

### Tiếp theo
- Điền cấu hình Telegram cục bộ và xác nhận gửi tin nhắn thật.
# scripts

Entry point đã có: `python scripts/build_fixture.py` tạo lại fixture tổng hợp; `python scripts/evaluate_pilot.py data/normalized/pilot-v2 --output docs/report/pilot-retrieval-smoke-2026-11-02.json` chạy kiểm tra retrieval pilot offline. CLI chính: đặt `PYTHONPATH=src`, chạy `python -m legal_ai.cli --help`. Xem `docs/planning/local-pilot-review-2026-11-02.md`.

CLI hiện có: snapshot, parse, build-pilot, validate, search. Các lệnh extract/index/ask và batch resume trong kế hoạch vẫn chưa triển khai.

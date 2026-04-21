#!/bin/sh
set -e
# Cold-start profiling: stderr line before uvicorn loads backend_api.main (same clock as HSM_MAIN_MODULE_START).
/app/.venv/bin/python -c "import sys,time; print('HSM_ENTRYPOINT_PRE_UVICORN', f't={time.time():.6f}', file=sys.stderr, flush=True)"
exec /app/.venv/bin/uvicorn backend_api.main:app --host 0.0.0.0 --port 8000

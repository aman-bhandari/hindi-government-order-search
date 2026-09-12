#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
exec uvicorn api.main:app --host 127.0.0.1 --port "${PORT:-8000}"

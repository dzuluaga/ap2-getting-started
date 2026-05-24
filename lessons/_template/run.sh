#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"   # the lesson's own directory (copy-safe)
uv run python example.py

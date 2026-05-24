#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
uv run python lessons/_template/example.py

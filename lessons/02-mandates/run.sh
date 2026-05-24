#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root
echo "== build ==";  uv run python lessons/02-mandates/build_mandate.py
echo; echo "== verify =="; uv run python lessons/02-mandates/verify_mandate.py
echo; echo "== map ==";    uv run python lessons/02-mandates/map_to_sdk.py

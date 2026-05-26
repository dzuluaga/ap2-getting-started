#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root
echo "== build ==";  uv run python lessons/03-selective-disclosure/build_sdjwt.py
echo; echo "== verify =="; uv run python lessons/03-selective-disclosure/verify_sdjwt.py
echo; echo "== map ==";    uv run python lessons/03-selective-disclosure/map_to_sdk.py

#!/usr/bin/env bash
# One-command setup for Revenue Jarvis on an Apple Silicon Mac (M1/M2/M3, 8 GB is enough).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Checking Homebrew tools (ffmpeg for voice)…"
if ! command -v brew >/dev/null; then
  echo "Homebrew not found. Install it from https://brew.sh then re-run."; exit 1
fi
command -v ffmpeg >/dev/null || brew install ffmpeg

PY=${PYTHON:-python3}
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ needed (brew install python@3.12)"'

echo "==> Creating virtual environment (.venv)…"
"$PY" -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e ".[voice,dev]"

echo "==> Downloading the multilingual embedding model (one time, ~470 MB)…"
python -c "from sentence_transformers import SentenceTransformer as S; S('intfloat/multilingual-e5-small')"

if [ ! -f .env ]; then cp .env.example .env; fi

echo "==> System check"
jarvis doctor || true
cat <<'EOF'

Done. Next:
  1. Make sure Claude Code is logged in:   claude      (then /exit)
  2. (optional) point Jarvis at your book PDF in .env:  JARVIS_BOOK_PDF=/Users/you/Documents/Punjabi book .pdf
  3. Start Jarvis:                          source .venv/bin/activate && jarvis serve
EOF

#!/bin/zsh
set -e
cd "$(dirname "$0")"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python scripts/run_jarvis.py "$@"
elif [[ -f /tmp/revenue-jarvis-model-path.txt ]]; then
  export PYTHONPATH="$(cat /tmp/revenue-jarvis-model-path.txt):src:scripts"
  exec /Users/karamjot/.local/share/uv/tools/browser-use/bin/python scripts/run_jarvis.py "$@"
else
  print 'Jarvis environment missing. Run scripts/setup_mac.sh first.'
  read '?Press Enter to close.'
  exit 1
fi

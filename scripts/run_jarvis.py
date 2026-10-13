#!/usr/bin/env python3
"""Launch Jarvis locally; --replace stops only an identified Jarvis listener."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))


def looks_like_jarvis(value):
    return (isinstance(value, dict) and isinstance(value.get('book_pages'), int)
            and isinstance(value.get('laws'), list)
            and value.get('backend') in ('claude-code', 'codex', 'sources-only')
            and 'book_pages_indexed' in value and 'stt_engine' in value and 'title' in value)


def stop_existing(port):
    url = f'http://127.0.0.1:{port}/api/status'
    try:
        with urlopen(url, timeout=8) as response:
            status = json.load(response)
    except URLError:
        return
    if not looks_like_jarvis(status):
        raise RuntimeError('This port is occupied by another application. Nothing was stopped.')
    result = subprocess.run(['lsof', '-a', '-u', str(os.getuid()), '-t', '-nP',
                             f'-iTCP@127.0.0.1:{port}', '-sTCP:LISTEN'],
                            capture_output=True, text=True, timeout=8, check=False)
    pids = set(result.stdout.split())
    if len(pids) != 1 or not next(iter(pids)).isdigit():
        raise RuntimeError('Cannot identify a single Jarvis process. Close its Terminal window, then start Jarvis again.')
    pid = int(next(iter(pids)))
    command = subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                             capture_output=True, text=True, timeout=8, check=True).stdout
    if 'python' not in command.lower() and 'uvicorn' not in command.lower():
        raise RuntimeError('Listener is not the expected Python Jarvis process. Nothing was stopped.')
    print(f'Restarting the identified Jarvis service (PID {pid}).', flush=True)
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                pass
        except (ConnectionRefusedError, TimeoutError):
            return
        time.sleep(.25)
    raise RuntimeError('Jarvis is still finishing a request. Start it again after that request finishes.')


def create_local_app():
    from revenue_jarvis.config import Settings
    from revenue_jarvis.server import create_app
    settings = Settings()
    if settings.embed_model == 'intfloat/multilingual-e5-small':
        from repair_law_index import CachedE5
        from revenue_jarvis import retrieve
        print('Loading cached multilingual E5. No embedding download.', flush=True)
        encoder = CachedE5()
        retrieve.load_encoder = lambda *a, **k: encoder
    return create_app(settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace', action='store_true', help='Restart the identified Jarvis service')
    parser.add_argument('--reload', action='store_true', help='Reload automatically during source development')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    from revenue_jarvis.config import Settings
    import uvicorn
    settings = Settings()
    if settings.host != '127.0.0.1':
        raise RuntimeError('This launcher serves only on 127.0.0.1.')
    if args.replace:
        stop_existing(settings.port)
    url = f'http://127.0.0.1:{settings.port}'
    if not args.no_browser:
        def open_ready():
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                try:
                    with urlopen(url + '/api/status', timeout=2) as response:
                        if looks_like_jarvis(json.load(response)):
                            webbrowser.open(url)
                            return
                except (URLError, ValueError):
                    pass
                time.sleep(.3)
        threading.Thread(target=open_ready, daemon=True).start()
    print('Keep this Terminal window open. Ctrl+C stops Jarvis.', flush=True)
    uvicorn.run('run_jarvis:create_local_app', factory=True, host=settings.host,
                port=settings.port, reload=args.reload, reload_dirs=[str(ROOT / 'src')] if args.reload else None)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f'Jarvis could not start: {exc}', file=sys.stderr)
        raise SystemExit(1)

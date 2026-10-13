#!/bin/zsh
set -e
cd "$(dirname "$0")"
exec './Start Jarvis.command' --replace "$@"

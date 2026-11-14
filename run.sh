#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v qs >/dev/null || { echo 'Quickshell missing. Run ./install.sh --deps in your system terminal.' >&2; exit 1; }
exec qs -p "$project_dir/app/MacDock" "$@"

#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
    --experimental-backend|--experimental-backend-remove) printf "%s\n" "Experimental Noctalia backend support has been retired." >&2; exit 2 ;;
    --plugin|--plugin-update|--plugin-remove) exec python3 "$project_dir/tools/plugin_install.py" "$1" ;;
esac
if [[ "${1:-}" == --deps ]]; then
    exec sudo pacman -S --needed quickshell qt6-multimedia inotify-tools xdg-utils
fi
exec python3 "$project_dir/tools/manage.py" install "$@"

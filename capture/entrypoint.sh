#!/bin/sh
# Capture image entrypoint. Each command replaces this shell (exec), so the
# runner is the process `docker stop` signals and its SIGTERM handler runs.
set -eu

queue=/app/queue/capture-queue.json
pin=$(cut -d' ' -f1 /app/queue/capture-queue.sha256)
if [ "$(sha256sum "$queue" | cut -d' ' -f1)" != "$pin" ]; then
    echo "capture image refused: the queue does not match its pinned SHA-256" >&2
    exit 2
fi

case "${1:-run}" in
run)
    mkdir -p /data/www
    for asset in index.html status.mjs; do
        rm -f /data/www/$asset.new
        cp /app/www-assets/$asset /data/www/$asset.new
        mv /data/www/$asset.new /data/www/$asset
        if ! cmp -s /app/www-assets/$asset /data/www/$asset; then
            echo "capture image refused: could not publish www/$asset" >&2
            exit 2
        fi
    done
    exec python /app/capture_runner.py run --queue "$queue" --state /data/state \
        --out /data/out --cache /data/cache --www /data/www --secrets /secrets
    ;;
status-server)
    # Its own container: only the public directory is mounted, read-only, at
    # /www. Bind every address inside the container; Docker publishes the
    # port on the host's LAN address only.
    exec python -m http.server --directory /www --bind 0.0.0.0 "${2:-8080}"
    ;;
clear-attention)
    exec python /app/capture_runner.py clear-attention --state /data/state
    ;;
test-alert)
    exec python /app/capture_runner.py test-alert --secrets /secrets
    ;;
*)
    echo "usage: run | status-server [PORT] | clear-attention | test-alert" >&2
    exit 2
    ;;
esac

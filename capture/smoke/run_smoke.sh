#!/bin/sh
# Slice 5B image smoke in WSL Docker. No live API: every container runs with
# --network none (S2 shares only the fake's loopback), and an audit hook logs and
# refuses every socket attempt except the loopback Notifiarr fake.
# Usage: run_smoke.sh IMAGE HARNESS_DIR RESULTS_DIR (HARNESS_DIR is capture/smoke;
# RESULTS_DIR must be new or empty, and is never cleared)
set -eu
IMAGE=$1
H=$2
OUT=$3
A=$HOME/necropsy-capture-smoke
NAME=necropsy-capture-smoke
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT")" ]; then
    echo "refused: $OUT is not empty; choose a new results directory" >&2
    exit 2
fi
mkdir -p "$OUT"
log() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

prep() {
    docker rm -f $NAME smoke-notifiarr >/dev/null 2>&1 || true
    docker run --rm -v "$HOME:/h" --user 0 --entrypoint sh "$IMAGE" -c \
        "rm -rf /h/necropsy-capture-smoke" >/dev/null
    mkdir -p "$A"/secrets "$A"/state "$A"/out "$A"/cache "$A"/www "$A"/smoke
    cp -r "$H"/audit "$H"/bin "$H"/notifiarr_fake.py "$A"/smoke/
    chmod 0755 "$A"/smoke/bin/necropsy
    if [ "${1:-}" = notifiarr ]; then
        printf '{"api_key": "smoke-dummy-key", "channel_id": 1}\n' > "$A"/secrets/notifiarr.json
        chmod 0600 "$A"/secrets/notifiarr.json
    fi
    docker run --rm -v "$A:/a" --user 0 --entrypoint sh "$IMAGE" -c \
        "chown -R 99:100 /a/secrets /a/state /a/out /a/cache /a/www /a/smoke && chmod 0700 /a/secrets"
}

# Production run flags (slice 6 uses the same, plus --restart unless-stopped and
# the bridge network). $1: extra flags for the smoke.
start() {
    docker run -d --name $NAME --init --stop-timeout 90 $1 \
        -v "$A/secrets:/secrets" -v "$A/state:/data/state" -v "$A/out:/data/out" \
        -v "$A/cache:/data/cache" -v "$A/www:/data/www" \
        -v "$A/smoke:/smoke" -e PYTHONPATH=/smoke/audit -e SMOKE_NET_LOG=/smoke/net.jsonl \
        $2 "$IMAGE" >/dev/null
}

wait_for() {  # wait_for SECONDS PYTHON_EXPR_ON_STATUS
    i=0
    while [ $i -lt "$1" ]; do
        if [ -f "$A/www/status.json" ] && python3 -c "import json,sys; s=json.load(open('$A/www/status.json')); sys.exit(0 if ($2) else 1)" 2>/dev/null; then
            return 0
        fi
        sleep 1; i=$((i + 1))
    done
    log "TIMEOUT waiting for: $2"; python3 -m json.tool "$A/www/status.json" | head -40; docker logs $NAME | tail -20
    return 1
}

# ---- S1: real necropsy 0.5.0, no credential file, no network.
log "S1 real wheel, missing sign-in"
prep
start "--network none" ""
wait_for 120 "s['state']=='attention'"
docker stop $NAME >/dev/null
mkdir -p "$OUT/s1"; docker logs $NAME > "$OUT/s1/container.log" 2>&1
mkdir -p "$OUT/s1"
docker run --rm -v "$A:/a" -v "$OUT/s1:/r" --user 0 --entrypoint sh "$IMAGE" -c \
    "cp /a/state/state.json /a/www/status.json /r/; cp /a/smoke/net.jsonl /r/ 2>/dev/null || :; cp -r /a/state/attempts /r/attempts; find /a/out /a/state -type f > /r/files.txt; ls -la /a/www > /r/www-ls.txt; chmod -R a+r /r"
docker rm $NAME >/dev/null
log "S1 done"

# ---- S2: fake analyze with the exact generated argv, stop/restart, quota wait,
# auth pause, Notifiarr fake on the shared loopback.
log "S2 fake analyze, stop/restart, quota wait, alerts"
prep notifiarr
docker run -d --name smoke-notifiarr --network none -v "$A/smoke:/smoke" --user 99:100 \
    --entrypoint python "$IMAGE" /smoke/notifiarr_fake.py /smoke/notifiarr.jsonl >/dev/null
sleep 1
start "--network container:smoke-notifiarr" \
    "-e PATH=/smoke/bin:/usr/local/bin:/usr/bin:/bin -e SMOKE_ARGV_LOG=/smoke/argv.jsonl -e SMOKE_NOTIFIARR_FAKE=127.0.0.1:5454"
wait_for 60 "s['state']=='running' and s.get('current')"
sleep 5
log "S2 docker stop (grace 90 s)"
t0=$(date +%s)
docker stop $NAME >/dev/null
t1=$(date +%s)
code=$(docker inspect -f '{{.State.ExitCode}}' $NAME)
log "S2 stopped in $((t1 - t0)) s, exit $code"
mkdir -p "$OUT/s2"
echo "{\"stop_seconds\": $((t1 - t0)), \"exit_code\": $code}" > "$OUT/s2/stop1.json"
docker run --rm -v "$A:/a" --user 0 --entrypoint cat "$IMAGE" /a/state/state.json > "$OUT/s2/state-after-stop.json"
log "S2 restart"
docker start $NAME >/dev/null
wait_for 240 "s['state']=='waiting'"
log "S2 waiting for quota; restart during the wait"
docker restart $NAME >/dev/null
wait_for 30 "s['state']=='waiting'"
wait_for 300 "s['state']=='attention'"
sleep 5
docker stop $NAME >/dev/null
mkdir -p "$OUT/s2"
docker logs $NAME > "$OUT/s2/container.log" 2>&1
docker run --rm -v "$A:/a" -v "$OUT/s2:/r" --user 0 --entrypoint sh "$IMAGE" -c \
    "cp /a/state/state.json /a/www/status.json /a/smoke/*.jsonl /r/; cp -r /a/state/attempts /r/attempts; ls -la /a/www /a/secrets > /r/ls.txt; chmod -R a+r /r"
docker rm -f $NAME smoke-notifiarr >/dev/null
log "S2 done"

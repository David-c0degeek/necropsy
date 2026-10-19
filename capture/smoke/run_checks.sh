#!/bin/sh
# Process, user, mount and status-server checks on the capture image, with the
# production run flags. Prints what it observes and exits non-zero if any
# expectation fails. Run after run_smoke.sh, which leaves its data directories.
# Usage: run_checks.sh IMAGE
set -eu
IMAGE=$1
A=$HOME/necropsy-capture-smoke
fail=0
check() { if eval "$2"; then echo "ok    $1"; else echo "FAIL  $1"; fail=1; fi; }
cleanup() { docker rm -f nc-pid nc-www >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name nc-pid --init --stop-timeout 90 --network none \
    -v "$A/secrets:/secrets" -v "$A/state:/data/state" -v "$A/out:/data/out" \
    -v "$A/cache:/data/cache" -v "$A/www:/data/www" "$IMAGE" >/dev/null
sleep 3
procs=$(docker exec nc-pid sh -c 'for p in /proc/[0-9]*; do [ -r $p/cmdline ] || continue; [ "${p#/proc/}" = "$$" ] && continue; printf "%s %s %s\n" ${p#/proc/} "$(awk "/^Uid:/{print \$2}" $p/status)" "$(tr "\0" " " < $p/cmdline)"; done' | grep -v -E ' (sh -c for p in|awk |tr )')
echo "$procs"
runner="python /app/capture_runner.py run --queue /app/queue/capture-queue.json --state /data/state --out /data/out --cache /data/cache --www /data/www --secrets /secrets "
check "PID 1 is docker-init running the entrypoint as UID 99" \
    "echo \"\$procs\" | grep -qx '1 99 /sbin/docker-init -- /app/entrypoint.sh run '"
check "the only other process is the runner, as UID 99, with the production arguments" \
    "[ \$(echo \"\$procs\" | wc -l) -eq 2 ] && echo \"\$procs\" | grep -qx \"[0-9]* 99 \$runner\""
check "the runner cannot write the image" "! docker exec nc-pid touch /app/x 2>/dev/null"
check "the runner is UID 99, GID 100" "[ \"\$(docker exec nc-pid id -u):\$(docker exec nc-pid id -g)\" = 99:100 ]"
check "the page assets were published" \
    "docker exec nc-pid cmp /app/www-assets/index.html /data/www/index.html && docker exec nc-pid cmp /app/www-assets/status.mjs /data/www/status.mjs"
t0=$(date +%s)
docker stop nc-pid >/dev/null
seconds=$(( $(date +%s) - t0 ))
code=$(docker inspect -f '{{.State.ExitCode}}' nc-pid)
echo "stop $seconds s exit $code"
check "docker stop ends the runner within the 90 s grace with exit 0" "[ $seconds -le 90 ] && [ $code -eq 0 ]"

docker run -d --name nc-www --init -p 127.0.0.1:18790:8080 -v "$A/www:/www:ro" "$IMAGE" status-server 8080 >/dev/null
sleep 2
get() { curl -s --path-as-is -o /dev/null -w '%{http_code} %{content_type}' "http://127.0.0.1:18790$1"; }
for request in "/ 200 text/html" "/index.html 200 text/html" "/status.mjs 200 text/javascript" \
    "/status.json 200 application/json" "/missing 404" "/../state/state.json 404" \
    "/%2e%2e/state/state.json 404"; do
    set -- $request
    got=$(get "$1")
    echo "$1 -> $got"
    check "$1 answers $2${3:+ $3}" "echo \"\$got\" | grep -q '^$2${3:+ $3}'"
done
check "the status server's /www is read-only" "! docker exec nc-www touch /www/x 2>/dev/null"
check "the status server sees no data, state or secrets mount" \
    "docker exec nc-www sh -c '[ ! -e /data ] && [ ! -e /secrets ]'"
exit $fail

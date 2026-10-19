#!/bin/sh
# Credential-file smoke in the image, as the runner user and with no network:
# the real `necropsy auth import` saves a synthetic sign-in into /secrets, an
# import replaces it atomically, and bad input or a wrong directory mode leaves
# the file as it was. Usage: run_credentials.sh IMAGE
set -eu
IMAGE=$1
A=$HOME/necropsy-capture-credentials
fail=0
check() { if eval "$2"; then echo "ok    $1"; else echo "FAIL  $1"; fail=1; fi; }
root() { docker run --rm -v "$A:/a" --user 0 --entrypoint sh "$IMAGE" -c "$1"; }
as_runner() {  # as_runner STDIN_FILE ARGS...
    input=$1; shift
    docker run --rm -i --network none -v "$A/secrets:/secrets" -v "$A/in:/in:ro" \
        --entrypoint necropsy "$IMAGE" "$@" < "$input"
}
payload() {  # payload REFRESH_TOKEN: a synthetic sign-in, never a real one
    python3 -c "import json,sys; t={'access':'smoke-access','refresh':sys.argv[1],'expires_at':4102444800.0}; r=json.dumps({'mode':'personal','secret':'smoke-secret','token':t}); print(json.dumps({'version':1,'values':{'client-id':'smoke-cid','client:smoke-cid':r}}))" "$1"
}
listing() { root "stat -c '%a %u %i %n' /a/secrets /a/secrets/* 2>/dev/null"; }

mkdir -p "$A"
root "rm -rf /a/secrets /a/in" >/dev/null 2>&1 || true
mkdir -p "$A/secrets" "$A/in"
payload R1 > "$A/in/one.json"
payload R2 > "$A/in/two.json"
printf 'garbage' > "$A/in/bad.json"
root "chown 99:100 /a/secrets && chmod 0700 /a/secrets"

as_runner "$A/in/one.json" auth import > /dev/null
first=$(listing)
echo "$first"
check "first import wrote one 0600 file owned by UID 99" \
    "echo \"\$first\" | grep -q '^600 99 [0-9]* /a/secrets/credentials.json$' && [ \$(echo \"\$first\" | wc -l) -eq 2 ]"
check "the saved file holds the first sign-in" \
    "root 'cat /a/secrets/credentials.json' | grep -q R1"

as_runner "$A/in/two.json" auth import > /dev/null
second=$(listing)
echo "$second"
inode1=$(echo "$first" | awk '/credentials.json/{print $3}')
inode2=$(echo "$second" | awk '/credentials.json/{print $3}')
check "a second import replaced the file by rename (new inode)" "[ \"$inode1\" != \"$inode2\" ]"
check "the replacement is 0600, UID 99, with no temporary file left" \
    "echo \"\$second\" | grep -q '^600 99 ' && [ \$(echo \"\$second\" | wc -l) -eq 2 ]"
check "the file now holds the second sign-in" \
    "root 'cat /a/secrets/credentials.json' | grep -q R2 && ! root 'cat /a/secrets/credentials.json' | grep -q R1"
status=$(as_runner /dev/null auth status 2>&1) && status_code=0 || status_code=$?
echo "$status"
check "status reads it back without the network or printing secrets" \
    "[ $status_code -eq 0 ] && ! echo \"\$status\" | grep -q -e R2 -e smoke-access -e smoke-secret"

before=$(root "sha256sum /a/secrets/credentials.json")
check "bad input is refused" "! as_runner \"$A/in/bad.json\" auth import > /dev/null 2>&1"
check "bad input leaves the file unchanged" "[ \"\$(root 'sha256sum /a/secrets/credentials.json')\" = \"\$before\" ]"
root "chmod 0755 /a/secrets"
check "a 0755 secrets directory is refused" "! as_runner \"$A/in/one.json\" auth import > /dev/null 2>&1"
check "the refusal leaves the file unchanged" "[ \"\$(root 'sha256sum /a/secrets/credentials.json')\" = \"\$before\" ]"
root "chmod 0700 /a/secrets"

root "rm -rf /a/secrets /a/in"
exit $fail

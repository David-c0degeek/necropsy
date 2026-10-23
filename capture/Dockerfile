# Unattended capture runner image.
# Build only from a context staged by scripts/stage_capture_image.py, never from
# the checkout. The context holds no secrets; they are mounted at /secrets.
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170

ARG CAPTURE_UID=99
ARG CAPTURE_GID=100

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    NECROPSY_CREDENTIAL_FILE=/secrets/credentials.json

COPY . /build/
RUN set -eu; cd /build; \
    python -c "import hashlib, json, pathlib, sys; m = json.load(open('manifest.json')); bad = [p for p, h in m['files'].items() if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() != h]; sys.exit('manifest mismatch: ' + ', '.join(bad) if bad else 0)"; \
    (cd wheel && sha256sum -c ../SHA256SUMS); \
    [ "$(cut -d' ' -f1 queue/capture-queue.sha256)" = "$(sha256sum queue/capture-queue.json | cut -d' ' -f1)" ] \
        || { echo "the queue does not match its pinned SHA-256" >&2; exit 1; }; \
    pip install --require-hashes --only-binary :all: --no-deps -r requirements.txt; \
    pip install --no-deps wheel/necropsy-*.whl; \
    pip check; \
    mkdir -p /app/queue /app/www-assets; \
    install -m 0444 capture_runner.py manifest.json SHA256SUMS /app/; \
    install -m 0444 queue/capture-queue.json queue/capture-queue.sha256 /app/queue/; \
    install -m 0444 www/index.html www/status.mjs /app/www-assets/; \
    install -m 0555 entrypoint.sh /app/entrypoint.sh; \
    cd /; rm -rf /build; \
    getent group "$CAPTURE_GID" >/dev/null || groupadd -g "$CAPTURE_GID" capture; \
    useradd -u "$CAPTURE_UID" -g "$CAPTURE_GID" -M -d /nonexistent -s /usr/sbin/nologin capture; \
    necropsy --version

USER ${CAPTURE_UID}:${CAPTURE_GID}
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["run"]

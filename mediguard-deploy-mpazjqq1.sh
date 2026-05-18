#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="mpazjqq1"
SHA256="a4a6458d93b69c8a8107d768d7c8b83db216d553e545dba0f1498cf862a9effc"
BASE_URL="https://raw.githubusercontent.com/frezaade31-pixel/claim-auditor-ui/main"
ARTIFACT="/tmp/mediguard-static-${VERSION}.tgz"
APP_DIR="/opt/mediguard-pro"

printf '[1/6] Download full static artifact %s\n' "$VERSION"
rm -f "${ARTIFACT}" "${ARTIFACT}.part"*
for part in 01 02 03 04; do
  curl -fL --retry 5 --retry-delay 2 --connect-timeout 20 \
    -o "${ARTIFACT}.part${part}" \
    "${BASE_URL}/mediguard-static-${VERSION}.tgz.part${part}"
done
cat "${ARTIFACT}.part"* > "${ARTIFACT}"
printf '%s  %s\n' "$SHA256" "$ARTIFACT" | sha256sum -c -

printf '[2/6] Replace backend/static with one complete bundle\n'
cd "$APP_DIR"
stamp=$(date +%Y%m%d%H%M%S)
test -f "$ARTIFACT"
test -d backend/static
cp -a backend/static "backend/static.prev.scan-code-desc-${stamp}"
rm -rf backend/static
mkdir -p backend/static
tar -xzf "$ARTIFACT" -C backend/static
cp backend/static/index.html backend/static/app.html
cat backend/static/version.json

printf '[3/6] Verify local static references\n'
python3 - <<'PY'
from pathlib import Path
import re
root = Path('/opt/mediguard-pro/backend/static')
app = (root / 'app.html').read_text(encoding='utf-8')
main = re.search(r'assets/index-[^" ]+\.js', app).group(0)
js = (root / main).read_text(encoding='utf-8')
assets = sorted(set(re.findall(r'assets/[A-Za-z0-9_./-]+\.js', js)))
missing = [a for a in assets if not (root / a).exists()]
print('main bundle:', main)
print('assets referenced:', len(assets))
print('missing:', len(missing))
print('scan bundle:', [a for a in assets if 'ScanResumePage' in a])
if missing:
    print('\n'.join(missing[:20]))
    raise SystemExit(1)
PY

printf '[4/6] Rebuild/restart API container\n'
docker compose up -d --build api
docker compose ps api

printf '[5/6] Health check\n'
for n in $(seq 1 12); do
  if curl -fsS http://127.0.0.1:8080/api/v1/health; then
    echo
    break
  fi
  if [ "$n" = "12" ]; then
    echo 'Health check failed after retries' >&2
    exit 1
  fi
  sleep 5
done

printf '[6/6] Done: %s\n' "$VERSION"

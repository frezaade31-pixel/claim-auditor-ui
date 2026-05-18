#!/usr/bin/env bash
set -euo pipefail
VERSION="mpbd83dj"
BRANCH="mediguard-static-mpbd83dj"
BASE="https://raw.githubusercontent.com/frezaade31-pixel/claim-auditor-ui/${BRANCH}"
WORK="/tmp/mediguard-static-${VERSION}"
PASS="${PASS:-}"
if [ -z "$PASS" ]; then
  echo "PASS env is required" >&2
  exit 2
fi

rm -rf "$WORK"
mkdir -p "$WORK/extracted" /opt/mediguard-pro-backups
cd "$WORK"

for part in 001 002 003; do
  file="mediguard-static-${VERSION}.vol.7z.${part}"
  echo "Downloading $file"
  curl -fL --retry 3 --retry-delay 2 "$BASE/$file" -o "$file"
done

cat > SHA256SUMS <<'SUMS'
642e26978b00a0465cc0c055f27087a52eb432188f85a29601b9bcba75de4459  mediguard-static-mpbd83dj.vol.7z.001
86d2f2f600db3570811e654060811300234b4bd49e8a2e1b21a75ac151de06f9  mediguard-static-mpbd83dj.vol.7z.002
cb0f1c79190092891686e4196784009c6de12dd43d9d4089c16f4585e387ccf1  mediguard-static-mpbd83dj.vol.7z.003
SUMS
sha256sum -c SHA256SUMS

7z x -p"$PASS" "mediguard-static-${VERSION}.vol.7z.001" -o"$WORK/extracted" -y >/tmp/mediguard-static-${VERSION}-7z.log
PKG="$WORK/extracted/mediguard-static-${VERSION}.tgz"
echo "ee7751a7a6f4387229d232e4124fb27ce542452bfd06c921cb2808e070d88764  $PKG" | sha256sum -c -

cd /opt/mediguard-pro
stamp=$(date +%Y%m%d%H%M%S)
test -f "$PKG"
cp -a backend/static "backend/static.prev.select-dx-${VERSION}-$stamp"
rm -rf backend/static
mkdir -p backend/static
tar -xzf "$PKG" -C backend/static
cp backend/static/index.html backend/static/app.html

docker compose up -d --build api
cat backend/static/version.json

for i in $(seq 1 30); do
  code=$(curl -o /dev/null -s -w "%{http_code}" https://mediguard.tech/api/v1/health || true)
  if [ "$code" = "200" ]; then
    echo "health=200"
    break
  fi
  echo "health=$code retry=$i"
  sleep 3
done
curl -fsS https://mediguard.tech/version.json
curl -fsS https://mediguard.tech/app.html | grep -E "assets/index-|ScanResumePage" || true
echo "Done: $VERSION"
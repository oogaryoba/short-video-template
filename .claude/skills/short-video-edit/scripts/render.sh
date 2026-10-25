#!/usr/bin/env bash
# 檢查並輸出影片；不覆寫既有版本，自動往下編號 v1、v2、v3…
# 用法：render.sh <專案資料夾> <檔名前綴，例如 咖啡廳試喝>
set -euo pipefail
P=$(cd "$1" && pwd); NAME=$2; HF="npx --yes hyperframes@0.8.141"
cd "$P"; $HF check --json > edits/check.json 2>&1 || true
grep -q '"ok": *true' edits/check.json || { echo "❌ check 沒過，看 $P/edits/check.json"; exit 1; }
v=1; while [ -e "renders/${NAME}_v$v.mp4" ]; do v=$((v+1)); done
OUT="renders/${NAME}_v$v.mp4"; $HF render -o "$OUT" --quiet
echo "✅ $P/$OUT"

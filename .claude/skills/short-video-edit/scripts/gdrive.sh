#!/usr/bin/env bash
# Google 雲端硬碟：授權、拉素材、放成品。雲端主機用 rclone（遠端名稱 gdrive），
# 電腦有裝「Google 雲端硬碟」桌面版時也可以直接寫掛載路徑。
#
# 用法：
#   gdrive.sh auth-start              # 第一次授權：印出 Google 登入網址，請使用者用手機打開登入
#   gdrive.sh auth-finish '<網址>'     # 使用者登入後，把瀏覽器顯示「無法連線」那頁的完整網址貼回來
#                                     # → 印出 GDRIVE_TOKEN_B64=…，請使用者存到雲端環境的環境變數
#   gdrive.sh connect                 # 用環境變數 GDRIVE_TOKEN_B64 接上雲端硬碟（每次開對話自動跑）
#   gdrive.sh ls [資料夾]              # 列出雲端硬碟資料夾
#   gdrive.sh pull <雲端素材資料夾> footage        # 素材 → 本機 footage/（只複製影片，不動雲端原片）
#   gdrive.sh push <成品.mp4> <雲端成品資料夾>      # 成品 → 雲端硬碟（同名不覆寫）
# 雲端資料夾可以寫「影片素材/某支影片」，會自動補成 gdrive:影片素材/某支影片。
set -euo pipefail
cmd=${1:-}; a=${2:-}; b=${3:-}
LOG=/tmp/rclone-auth.log
local_path(){ [[ -e "$1" || "$1" == /* || "$1" == ~* || "$1" == [A-Za-z]:/* || "$1" == ./* ]]; }
rpath(){ if local_path "$1"; then echo "$1"; elif [[ "$1" == *:* ]]; then echo "$1"; else echo "gdrive:$1"; fi; }
need_remote(){ rclone listremotes 2>/dev/null | grep -q '^gdrive:$' || "$0" connect || { echo "❌ 還沒授權雲端硬碟：先跑 gdrive.sh auth-start"; exit 1; }; }
case $cmd in
 auth-start)
  command -v rclone >/dev/null || { echo "❌ 沒有 rclone：apt-get install -y rclone"; exit 1; }
  pkill -f "rclone authorize" 2>/dev/null || true; : > "$LOG"
  nohup rclone authorize drive --auth-no-open-browser > "$LOG" 2>&1 &
  for i in $(seq 1 30); do grep -q 'http://127.0.0.1:53682/auth' "$LOG" && break; sleep 1; done
  local_url=$(grep -o 'http://127.0.0.1:53682/auth[^ ]*' "$LOG" | head -1)
  [ -n "$local_url" ] || { echo "❌ rclone 沒有產生授權網址："; cat "$LOG"; exit 1; }
  g=$(curl -s -o /dev/null -w '%{redirect_url}' "$local_url")
  [ -n "$g" ] || { echo "❌ 取不到 Google 登入網址"; exit 1; }
  echo "請用手機打開下面這個網址，登入你的 Google 帳號並按「允許」："
  echo "$g"
  echo "允許之後瀏覽器會顯示「無法連線」，那是正常的：把網址列整串網址（開頭是 http://127.0.0.1:53682/）複製貼回對話。"
  echo "這個等待最多 30 分鐘，超過就重跑 auth-start。" ;;
 auth-finish)
  [ -n "$a" ] || { echo "用法：gdrive.sh auth-finish '<網址>'"; exit 1; }
  [[ "$a" == http://127.0.0.1:53682/* || "$a" == http://localhost:53682/* ]] || { echo "❌ 網址要以 http://127.0.0.1:53682/ 開頭"; exit 1; }
  curl -s "${a/localhost/127.0.0.1}" >/dev/null || true
  for i in $(seq 1 30); do grep -q 'End paste' "$LOG" && break; sleep 1; done
  tok=$(sed -n '/Paste the following into your remote machine/,/<---End paste/p' "$LOG" | grep -o '{.*}' | head -1)
  [ -n "$tok" ] || { echo "❌ 授權沒完成："; tail -5 "$LOG"; exit 1; }
  b64=$(printf '%s' "$tok" | base64 | tr -d '\n')
  GDRIVE_TOKEN_B64=$b64 "$0" connect
  echo "✅ 雲端硬碟已接上（這次對話可以直接用）。"
  echo "要讓之後每次對話都自動接上，請把下面這一整行加到雲端環境的「環境變數」："
  echo "GDRIVE_TOKEN_B64=$b64" ;;
 connect)
  [ -n "${GDRIVE_TOKEN_B64:-}" ] || exit 1
  tok=$(printf '%s' "$GDRIVE_TOKEN_B64" | base64 -d)
  rclone config delete gdrive >/dev/null 2>&1 || true
  rclone config create gdrive drive scope=drive token="$tok" --non-interactive >/dev/null 2>&1 \
   || rclone config create gdrive drive scope drive token "$tok" >/dev/null
  rclone lsd gdrive: --max-depth 1 >/dev/null 2>&1 || { echo "❌ 授權碼無效或已過期：重跑 auth-start"; exit 1; } ;;
 ls)
  need_remote; rclone lsf "$(rpath "${a:-}")" ;;
 pull)
  mkdir -p "$b"; src=$(rpath "$a")
  if local_path "$src"; then find "$src" -maxdepth 1 -type f \( -iname '*.mov' -o -iname '*.mp4' -o -iname '*.m4v' \) -exec cp -n {} "$b"/ \; ;
  else need_remote; rclone copy "$src" "$b" --include "*.{MOV,mov,MP4,mp4,M4V,m4v}" --stats-one-line -P; fi
  ls -lh "$b" ;;
 push)
  n=$(basename "$a"); dst=$(rpath "$b")
  if local_path "$dst"; then
   mkdir -p "$dst"; [ -e "$dst/$n" ] && { echo "❌ $dst/$n 已存在，請改版本號"; exit 1; }
   cp "$a" "$dst"/
  else
   need_remote
   [ -n "$(rclone lsf "$dst/$n" 2>/dev/null)" ] && { echo "❌ 雲端硬碟已有 $n，請改版本號"; exit 1; }
   rclone copy "$a" "$dst" --stats-one-line -P
  fi
  echo "✅ 已放到 $dst/$n（手機打開 Google 雲端硬碟 App 就能下載）" ;;
 *) sed -n '2,15p' "$0"; exit 1;;
esac

#!/usr/bin/env bash
# 檢查剪輯所需工具；缺什麼就印出安裝方式（Linux／雲端以 apt 為例）。
ok=1
need(){ command -v "$1" >/dev/null 2>&1 && echo "✅ $1" || { echo "❌ $1 — $2"; ok=0; }; }
need ffmpeg  "apt-get install -y ffmpeg ／ brew install ffmpeg"
need ffprobe "隨 ffmpeg 安裝"
need node    "需要 Node 18+（HyperFrames CLI 用 npx 執行）"
need npx     "隨 Node 安裝"
need python3 "apt-get install -y python3"
python3 -c "import numpy,fontTools" 2>/dev/null && echo "✅ numpy／fontTools" || { echo "❌ numpy／fontTools — pip install numpy fonttools"; ok=0; }
if command -v whisper-cli >/dev/null || python3 -c "import faster_whisper" 2>/dev/null; then echo "✅ 語音辨識（whisper-cli 或 faster-whisper）"; else echo "⚠️ 沒有語音辨識 — pip install faster-whisper（或 brew install whisper-cpp）"; fi
command -v opencc >/dev/null || python3 -c "import opencc" 2>/dev/null && echo "✅ opencc（簡轉繁）" || echo "⚠️ 沒有 opencc — pip install opencc-python-reimplemented；沒有就要人工把簡體改繁體"
ffmpeg -hide_banner -filters 2>/dev/null | grep -q zscale && echo "✅ ffmpeg zscale（HDR 轉 SDR）" || echo "⚠️ ffmpeg 沒有 zscale — iPhone HDR 片要先跑 to_sdr.sh（macOS 用 avconvert）"
ls "/System/Library/Fonts/STHeiti Medium.ttc" /usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc /usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc 2>/dev/null | head -1 | sed 's/^/✅ 字型 /' | grep . || echo "⚠️ 沒找到預設中文字型 — apt-get install -y fonts-noto-cjk，或 build.py --font 指定"
npx --yes hyperframes@0.8.141 --version >/dev/null 2>&1 && echo "✅ hyperframes 0.8.141" || { echo "❌ hyperframes CLI 無法執行（npx --yes hyperframes@0.8.141 --version）"; ok=0; }
npx --yes hyperframes@0.8.141 browser path >/dev/null 2>&1 && echo "✅ 輸出用瀏覽器" || { echo "❌ 沒有輸出用瀏覽器 — npx --yes hyperframes@0.8.141 browser ensure（雲端主機不要用 apt 的 chromium）"; ok=0; }
command -v rclone >/dev/null && echo "✅ rclone（雲端主機存取 Google 雲端硬碟用）" || echo "ℹ️ 沒有 rclone — 只有在沒裝 Google Drive 電腦版的雲端主機才需要：apt-get install -y rclone；授權用 gdrive.sh auth-start"
[ $ok = 1 ] && echo "環境 OK" || { echo "有必要工具缺少"; exit 1; }

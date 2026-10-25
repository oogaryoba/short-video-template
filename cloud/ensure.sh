#!/bin/bash
# 每次開雲端對話時自動跑：工具缺了就補裝，雲端硬碟授權碼在就接上。本機（非雲端）直接跳過。
[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
D="$(cd "$(dirname "$0")" && pwd)"
if ! command -v ffmpeg >/dev/null || ! command -v rclone >/dev/null || ! python3 -c "import faster_whisper,fontTools,opencc" 2>/dev/null; then
  echo "第一次使用：補裝剪輯工具（約 3～5 分鐘）…"
  bash "$D/setup.sh"
fi
bash "$D/../.claude/skills/short-video-edit/scripts/gdrive.sh" connect >/dev/null 2>&1 || true
exit 0

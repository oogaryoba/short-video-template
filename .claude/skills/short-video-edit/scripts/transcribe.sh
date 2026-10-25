#!/usr/bin/env bash
# 逐支原片轉逐字稿（含時間碼 SRT），輸出到 <輸出資料夾>/<檔名>.srt，並自動簡轉繁。
# 用法：transcribe.sh <輸出資料夾> 原片1.MOV [原片2.MOV ...]
set -euo pipefail
OUT=$1; shift; mkdir -p "$OUT"
MODEL=${WHISPER_MODEL:-$HOME/whisper-models/ggml-large-v3-turbo.bin}
for f in "$@"; do
  n=$(basename "${f%.*}"); wav="$OUT/$n.wav"
  ffmpeg -v error -y -i "$f" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$wav"
  if command -v whisper-cli >/dev/null && [ -f "$MODEL" ]; then
    whisper-cli -m "$MODEL" -l zh -f "$wav" -np -osrt -of "$OUT/$n" >/dev/null
  else
    python3 - "$wav" "$OUT/$n.srt" <<'PY'
import sys
from faster_whisper import WhisperModel
m=WhisperModel(__import__('os').environ.get('FW_MODEL','large-v3-turbo'),compute_type='int8')
segs,_=m.transcribe(sys.argv[1],language='zh',vad_filter=False)
def ts(t):h,r=divmod(t,3600);mi,s=divmod(r,60);return f'{int(h):02}:{int(mi):02}:{s:06.3f}'.replace('.',',')
with open(sys.argv[2],'w') as o:
 for i,s in enumerate(segs,1):o.write(f'{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n\n')
PY
  fi
  if command -v opencc >/dev/null; then opencc -c s2twp.json -i "$OUT/$n.srt" -o "$OUT/$n.srt"
  elif python3 -c "import opencc" 2>/dev/null; then python3 -c "import opencc,sys;p=sys.argv[1];c=opencc.OpenCC('s2twp');t=open(p).read();open(p,'w').write(c.convert(t))" "$OUT/$n.srt"
  else echo "⚠️ 沒有 opencc，$n.srt 可能有簡體字，要人工改繁體" >&2; fi
  echo "✅ $OUT/$n.srt"
done

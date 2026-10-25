#!/usr/bin/env bash
# 驗證成品：規格、黑畫面、音量、8 格縮圖總覽。用法：verify.sh 成品.mp4
set -euo pipefail
F=$1; B=${F%.mp4}
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of json "$F" > "$B.probe.json"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$F")
ffmpeg -hide_banner -i "$F" -vf blackdetect=d=0.3:pic_th=0.98 -af volumedetect -f null - 2> "$B.av.log" || true
python3 - "$F" "$D" <<'PY'
import sys,subprocess
f,d=sys.argv[1],float(sys.argv[2])
ts=[d*(i+.5)/8 for i in range(8)]
inp=sum([['-ss',f'{t:.2f}','-i',f] for t in ts],[])
fc=''.join(f'[{i}:v]scale=270:480[v{i}];' for i in range(8))+''.join(f'[v{i}]' for i in range(8))+'xstack=inputs=8:layout='+'|'.join(f'{(i%4)*270}_{(i//4)*480}' for i in range(8))
subprocess.run(['ffmpeg','-v','error','-y',*inp,'-filter_complex',fc,'-frames:v','1',f[:-4]+'.contact.jpg'],check=True)
PY
echo "長度：${D}s（上限 59s）"; grep -o '"width": [0-9]*\|"height": [0-9]*\|"r_frame_rate": "[0-9/]*"' "$B.probe.json" | head -3 | tr '\n' ' '; echo
grep -E "black_start|mean_volume|max_volume" "$B.av.log" || true
echo "縮圖：$B.contact.jpg（要用眼睛看：字幕位置、上方無標題、沒有黑畫面）"

#!/usr/bin/env bash
# iPhone HLG HDR 原片轉 SDR（只在 ffmpeg 沒有 zscale 時需要；build.py 有 zscale 會自動處理）。
# 用法：to_sdr.sh 輸入.MOV 輸出.mov
set -euo pipefail
if command -v avconvert >/dev/null; then avconvert -s "$1" -o "$2" -p Preset1920x1080 --multiPass
else ffmpeg -v error -y -i "$1" -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" -c:v libx264 -crf 16 -c:a copy "$2"; fi

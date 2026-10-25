#!/usr/bin/env bash
# 抽指定時間點畫面檢查字幕。用法：frames.sh 成品.mp4 6 7 8 9
set -euo pipefail
F=$1; shift; for t in "$@"; do ffmpeg -v error -y -ss "$t" -i "$F" -frames:v 1 -vf scale=540:960 "${F%.mp4}.t$t.jpg"; echo "${F%.mp4}.t$t.jpg"; done

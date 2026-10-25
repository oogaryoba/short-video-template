#!/bin/bash
# 雲端環境安裝腳本：把整份內容貼到 claude.ai/code 雲端環境的「Setup script」欄位。
# 裝好後雲端會快取，之後開新對話不用再裝。沒貼也沒關係，第一次開對話時會自動補裝（比較慢）。
export DEBIAN_FRONTEND=noninteractive
log=/tmp/short-video-setup.log
( apt-get update -qq && apt-get install -y -qq ffmpeg fonts-noto-cjk rclone \
    libnss3 libatk-bridge2.0-0 libgbm1 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libpango-1.0-0 libcups2 libasound2t64 ) >>$log 2>&1 &
( pip install -q numpy fonttools faster-whisper opencc-python-reimplemented \
  || pip install -q --break-system-packages numpy fonttools faster-whisper opencc-python-reimplemented ) >>$log 2>&1 &
( npx --yes hyperframes@0.8.141 browser ensure ) >>$log 2>&1 &
wait
exit 0

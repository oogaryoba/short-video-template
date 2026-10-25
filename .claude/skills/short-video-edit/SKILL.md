---
name: short-video-edit
description: 直式短影音剪輯流程（HyperFrames）。把手機拍的口播／對話原片剪成 1080×1920、59 秒內、約 1.13 倍速、下方字幕加說話者小字卡的 FB／IG／Reels 短片；素材從 Google 雲端硬碟讀取，成品放回 Google 雲端硬碟。用在「剪影片」「剪短影音」「上字幕」「改字幕」「出下一版」「拆上下集」時。內含逐字稿、剪點靜音吸附、產生專案、輸出、驗證腳本，Mac 與 Linux 都能跑。
---

# 直式短影音剪輯（HyperFrames）＋ Google 雲端硬碟

整個流程以一份 `spec.json` 為準：先寫好要留哪幾段、每一句字幕、強調卡，`build.py` 會生成 HyperFrames 專案，再用 `render.sh` 輸出成片。之後要改字幕或剪點，**只改 spec.json 再重新 build 和 render**，不要直接手改產出的 HTML。

## 0. 環境（第一次或換機器時）

```bash
bash scripts/check_env.sh
```

- **Claude 雲端版（手機 App 的 Code 分頁／claude.ai/code）**：範本 repo 的 `cloud/setup.sh` 會裝好全部工具；沒裝到的話，每次開對話時 `cloud/ensure.sh` 會自動補裝。輸出用的瀏覽器用 `npx --yes hyperframes@0.8.141 browser ensure` 下載，**不要用 apt 的 chromium**（雲端主機跑不起來）。
- Mac：`brew install ffmpeg node whisper-cpp rclone && pip3 install numpy fonttools opencc-python-reimplemented`
- 其他 Linux：`sudo apt-get install -y ffmpeg fonts-noto-cjk rclone nodejs npm && pip install numpy fonttools faster-whisper opencc-python-reimplemented`
- 字型：Linux 預設 Noto Sans CJK TC，Mac 預設系統黑體（STHeiti）。指定別的字型用 `--font 字型檔` 或環境變數 `SHORTVIDEO_FONT`。
- HyperFrames 版本固定 `npx --yes hyperframes@0.8.141`。
- 語音辨識：有 whisper-cli 加 `~/whisper-models/ggml-large-v3-turbo.bin`（或 `WHISPER_MODEL`）就用它；否則用 faster-whisper，第一次會從 HuggingFace 下載約 1.6GB 模型（雲端環境的網路權限要能連到 huggingface.co）。

## 1. 收原片（Google 雲端硬碟）

先問使用者：素材在雲端硬碟哪個資料夾、成品要放回哪個資料夾（或改用 GitHub 下載，見第 4 節）。

**第一次要授權（只用手機就能完成）**：

```bash
bash scripts/gdrive.sh auth-start        # 印出 Google 登入網址 → 原樣貼給使用者
bash scripts/gdrive.sh auth-finish '<使用者貼回來的 http://127.0.0.1:53682/... 網址>'
```

- 跟使用者說：用手機打開網址、登入、按允許；之後瀏覽器會顯示「無法連線」，**這是正常的**，把網址列整串網址複製貼回來。
- `auth-finish` 會印出一行 `GDRIVE_TOKEN_B64=…`。請使用者到 claude.ai/code 的雲端環境設定 →「環境變數」貼上這一行，之後每次開對話都會自動接上。**這行等同雲端硬碟鑰匙**：只給使用者本人，不要寫進 repo、不要 commit。
- 已經有環境變數時，開對話會自動跑 `gdrive.sh connect`；`gdrive.sh ls` 可以確認接上了沒。

**拉素材**：

```bash
bash scripts/gdrive.sh ls 影片素材
bash scripts/gdrive.sh pull "影片素材/某支影片" footage
```

- 資料夾寫「影片素材/某支影片」即可，會自動補成 `gdrive:` 開頭。電腦有裝 Google 雲端硬碟桌面版時，也可以直接寫掛載路徑。
- 素材一律**複製**，不搬移、不刪除雲端上的原片。
- iPhone HDR 片：ffmpeg 有 zscale 時 build.py 會自動轉 SDR；沒有就先跑 `scripts/to_sdr.sh 輸入 輸出`。

## 2. 逐字稿

```bash
bash scripts/transcribe.sh work/tr footage/IMG_0001.MOV footage/IMG_0002.MOV
```

- 會產生帶時間碼的 `work/tr/<檔名>.srt`，並自動把簡體轉成繁體。
- 辨識結果一定要**人工逐句校對**：品牌名、品項、數字、同音字、口頭禪；不能留下簡體字。不確定的用詞要問使用者。

## 3. 寫 spec.json

格式參考 `references/spec-example.json`。

| 欄位 | 說明 |
|---|---|
| `title` / `out_dir` / `source_dir` / `source_ext` | 片名、專案輸出資料夾、素材資料夾、副檔名（.MOV／.mp4） |
| `rate` | 播放倍速，預設 1.13 |
| `max_duration` | 長度上限，預設 59 秒，超過時 build 會停下來 |
| `snap` | true：把剪點和字幕邊界吸到 ±0.35 秒內最安靜的位置，避免切在字中間 |
| `speakers` | `{代號: {label, color}}`。`label` 是字幕上方的小字卡，留空就不顯示（例如鏡頭前的主角） |
| `clips` | `[素材檔名, 起秒, 迄秒]`，用**原片時間**，照播放順序排 |
| `captions` | `[素材檔名, 起秒, 迄秒, 文字, 說話者代號]`，用原片時間，會自動換算成成片時間 |
| `moments` | `[素材檔名, 秒, 文字, "pop"/"error"/""]`：字幕正上方的黃色強調卡，顯示 1.5 秒，可以配音效 |
| `punch` | `[素材檔名, 秒]`：鏡頭放大到 1.08 倍，1.4 秒後回原大小 |
| `next` | 最後 1.6 秒的「接下集」卡，可省略 |

字幕切分：
- 一張字幕卡只放一個意思。13 個字以內用 70px，超過自動縮成 60px。
- 要把某個詞移到下一張卡時，就調整兩段字幕的分界秒數，讓分界落在那個詞開始的時間點。

## 4. 生成專案 → 輸出 → 驗證 → 放回雲端硬碟

```bash
python3 scripts/build.py spec.json
bash scripts/render.sh <out_dir> 片名
bash scripts/verify.sh <out_dir>/renders/片名_vN.mp4
bash scripts/frames.sh <成品.mp4> 6 7 8 9
bash scripts/gdrive.sh push <成品.mp4> "影片成品"
```

- `render.sh` 會先做檢查，再輸出 `renders/片名_vN.mp4`；版本號自動往下編，不覆寫舊版。
- `verify.sh` 會檢查長度、1080×1920、30fps，偵測黑畫面和音量，並產生 8 格縮圖 `.contact.jpg`。**要用眼睛看縮圖**：字幕位置對不對、有沒有黑畫面。
- `frames.sh` 用來抽看有改動的那幾秒。
- `gdrive.sh push` 只上傳正式成品；log、縮圖這類檢查檔不用上傳。雲端已有同名檔案時會停下來，不會覆寫。
- **交付給手機**：預設用 `gdrive.sh push` 放回雲端硬碟，跟使用者說「打開手機的 Google 雲端硬碟 App →『影片成品』就能下載」。
- **不用雲端硬碟時改用 GitHub 下載**：把成品複製到 repo 的 `成品/片名_vN.mp4`，`git add -f` 後 commit、push 到目前的分支，再給使用者連結 `https://github.com/<帳號>/<repo>/blob/<分支>/成品/<檔名>`（手機打開按下載）。單檔要小於 100MB；repo 必須是**私人**的，不是的話先提醒使用者。
- 改了 `clips` 的秒數後，要先刪掉 `<out_dir>/assets/c*.mp4` 這些舊片段快取，再重新 build。

## 風格預設（可依使用者喜好調整）

- 畫面上方保持乾淨，不放標題，只留 8px 進度條。字幕放下方，強調卡放在字幕正上方。
- 節奏：約 1.13 倍速，刪掉等待、停頓、重複的話。旁人收音比較小，要小心別被當成靜音剪掉。
- 超過 59 秒就拆成連續的上下集，不要靠大幅加速硬塞進去。
- 要加配樂的話，只用確定**可以商用**的音樂（例如 Apache-2.0 授權的 AI 音樂模型 ACE-Step；MusicGen 權重是 CC-BY-NC，不能商用）。人聲出現時音樂要壓低。預設不加配樂，只用少量合成音效。
- 所有文字一律用繁體中文。

## 安全

- 不刪除使用者的原片，不覆寫舊版成品，不幫使用者發布到社群。
- 刪除任何檔案前，先列清單請使用者確認。

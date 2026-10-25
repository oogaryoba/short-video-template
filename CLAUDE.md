# 短影音剪輯（給 Claude 的工作說明）

這個 repo 是用手機＋Claude 雲端版剪直式短影音的範本。使用者通常只用手機，不會開電腦。

## 規則

- 一律用**繁體中文**回覆，不要出現簡體字。
- 剪片照 `.claude/skills/short-video-edit/SKILL.md` 的流程做；第一次先跑 `bash .claude/skills/short-video-edit/scripts/check_env.sh`。
- 使用者說「設定雲端硬碟」或還沒授權時，照 SKILL.md 第 1 節用 `gdrive.sh auth-start`／`auth-finish` 帶他用手機完成，最後提醒他把 `GDRIVE_TOKEN_B64=…` 那一行貼到雲端環境的「環境變數」。這行是他的雲端硬碟鑰匙，**不要寫進任何檔案、不要 commit**。
- 雲端硬碟上的原片只複製，不搬移、不刪除。成品命名 `片名_v1.mp4`、`片名_v2.mp4`，不覆蓋舊版。
- 素材、逐字稿、工作檔（`footage/`、`work/`、`projects/`）不要 commit。
- 成品交付：預設放回雲端硬碟（`gdrive.sh push`）；使用者說不用雲端硬碟時，放到 repo 的 `成品/` 資料夾 commit、push，給他 GitHub 下載連結（repo 必須是私人的）。
- 回覆要短，使用者在手機上看；每一步告訴他現在在做什麼、大概要等多久。

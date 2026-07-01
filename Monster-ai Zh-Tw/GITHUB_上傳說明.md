# Monster-Ai-ZH-TW GitHub 上傳說明

本資料夾為 **繁體中文版** 的本地工作副本，對應遠端：

**https://github.com/SB00001090/Monster-Ai-ZH-TW**

英文主倉庫（origin）：

**https://github.com/SB00001090/Guardian-Ai**

### Clone 指令

```bash
# 繁體中文 Repo（建議）
gh repo clone SB00001090/Monster-Ai-ZH-TW
cd Monster-Ai-ZH-TW

# 英文主 Repo
gh repo clone SB00001090/Guardian-Ai
```

或使用 git：

```bash
git clone https://github.com/SB00001090/Monster-Ai-ZH-TW.git
git clone https://github.com/SB00001090/Guardian-Ai.git
```

---

## 一、同步專案內容到此資料夾

在專案根目錄執行：

```powershell
.\scripts\sync_monster_ai_zh_tw_folder.ps1
```

會將 `monster-ai` 根目錄的程式碼複製到 `Monster-ai Zh-Tw\`，並排除：

- `.git`、`node_modules`、`.venv`、`data`、`dist`、`__pycache__`
- 本資料夾自身（避免遞迴複製）

複製完成後，**本資料夾內的 `README.md` 會保留繁體中文版**（不會被英文 README 覆蓋）。

---

## 二、推送到 Monster-Ai-ZH-TW（zh-tw 遠端）

在 **專案根目錄**（`C:\MonsterAI\monster-ai`）執行：

```powershell
.\scripts\publish_zh_tw_github.ps1
```

此腳本會：

1. 執行同步（`sync_monster_ai_zh_tw_folder.ps1`）
2. 將 `Monster-ai Zh-Tw\README.md` 設為倉庫根目錄的 `README.md`（僅用於 zh-tw 推送）
3. 提交並 `git push zh-tw main`
4. 還原英文 `README.md`（不影響 origin 主倉庫）

### 手動推送（進階）

```powershell
# 1. 同步
.\scripts\sync_monster_ai_zh_tw_folder.ps1

# 2. 暫時改用繁中 README
Copy-Item -Force "Monster-ai Zh-Tw\README.md" "README.md"

# 3. 提交並推送 zh-tw
git add README.md
git commit -m "docs(zh-TW): update README for Monster-Ai-ZH-TW"
git push zh-tw main

# 4. 還原英文 README（從 git 取回）
git checkout HEAD -- README.md
```

---

## 三、發布 Release（APK + SHA256）

```powershell
.\scripts\publish_zh_tw_release.ps1
```

會在 **Monster-Ai-ZH-TW** 建立或更新 `v1.3.1` Release，並上傳 APK 與 SHA256 校驗檔。

---

## 四、遠端設定確認

```powershell
git remote -v
```

應包含：

| 遠端 | URL |
|------|-----|
| `origin` | `https://github.com/SB00001090/Guardian-Ai.git` |
| `zh-tw` | `https://github.com/SB00001090/Monster-Ai-ZH-TW.git` |

若缺少 `zh-tw`：

```powershell
git remote add zh-tw https://github.com/SB00001090/Monster-Ai-ZH-TW.git
```

---

## 五、檔案對照

| 檔案 | 用途 |
|------|------|
| `Monster-ai Zh-Tw/README.md` | 繁體中文完整說明（ZH-TW 倉庫首頁用） |
| `Monster-ai Zh-Tw/README.en.md` | 指向父目錄英文 README |
| `README.md`（根目錄） | 英文版（Guardian-Ai 主倉庫） |
| `scripts/sync_monster_ai_zh_tw_folder.ps1` | 同步程式碼到此資料夾 |
| `scripts/publish_zh_tw_github.ps1` | 一鍵推送繁中 README 到 zh-tw |
| `scripts/publish_zh_tw_release.ps1` | 發布 ZH-TW Release 資產 |

---

## 六、注意事項

- `config.yaml`、`data/`、`.venv/` 不會被同步（本地執行時請在根目錄或同步後自行建立）。
- 程式開發建議仍在根目錄 `monster-ai` 進行；本資料夾主要用於 **繁中文檔與 ZH-TW 發布**。
- 推送至 `origin` 時請使用英文 `README.md`，勿將繁中 README 誤推到英文主倉庫。
"""Hardcoded legal disclaimer — cannot be disabled or overridden by config."""
from __future__ import annotations

DEVELOPER = "Developed by Suckbob | Monster Guardian AI"

DISCLAIMER_ZH = f"""【Monster Guardian AI 免責聲明】

{DEVELOPER}

1. **服務性質**
   - 本軟體為本地優先 AI 平台，生成內容僅供私人創作與娛樂。
   - NSFW / R18+ 描述已作模糊處理；實際輸出由您本地模型決定，平台不代為審查。

2. **付款與退款**
   - 7 日免費試用後可選一次性付費解鎖（區域定價）。
   - **付款完成後，因本地環境、硬體、模型或網絡差異導致之結果，可能性無法退款。**
   - 請於試用期充分評估後再購買。

3. **隱私與雲端同步**
   - OC 文案與對話預設僅存本機（AES-256-GCM 加密）。
   - **訓練檔案（好圖／爛圖／模板／prompt／LoRA 資料）全面加密儲存**，禁止明文存放。
   - 金鑰由用戶 passphrase 或裝置硬體指紋（MonsterLock / Android Keystore）綁定。
   - 雲端同步為**可選**；訓練檔案須先本機加密後才上傳（端到端）。
   - Google / GitHub 登入僅用於身份驗證，不解密您的內容。

4. **OC 反抄襲**
   - 角色指紋、浮水印與網絡學習保護預設啟用。
   - 未經授權不得複製他人 OC 指紋或訓練資料。

5. **安全保護**
   - 聊天區：加密儲存 + Ephemeral Chat + 反監聽提示。
   - 防毒、反暗網、反監視模組依 CrimeGuard / CallGuard 規則運作。
   - 生成品質低於 70% 視為失敗並自動重試。

6. **Likeness 與多模態**
   - 圖片／影片／音訊 likeness 僅限您擁有權利或已授權之參考。
   - 您對所有生成內容負全部法律責任。

使用本軟體即表示您已閱讀、理解並同意上述條款。"""

DISCLAIMER_EN = f"""Monster Guardian AI — Disclaimer

{DEVELOPER}

1. Local-first AI for private creative use. NSFW descriptions are blurred in UI; output is your responsibility.

2. 7-day trial, then one-time regional pricing. **No refunds** for results affected by your hardware, models, or network.

3. Training assets (good/bad images, templates, LoRA data) are AES-256-GCM encrypted at rest — no plaintext on disk. Keys bind to hardware or user passphrase.

4. OC and chats stay local unless you opt into E2E encrypted cloud sync (Google/GitHub auth only). Training vault sync exports ciphertext only.

5. Chat vault encryption, ephemeral mode, anti-surveillance hooks. Quality below 70% counts as failure.

6. Likeness/multimodal features require authorized references only.

By using this software you accept these terms."""


def get_disclaimer(locale: str = "zh-TW") -> dict[str, str]:
    if locale.startswith("en"):
        return {"locale": "en", "text": DISCLAIMER_EN, "developer": DEVELOPER, "version": "guardian_v1"}
    return {"locale": locale, "text": DISCLAIMER_ZH, "developer": DEVELOPER, "version": "guardian_v1"}
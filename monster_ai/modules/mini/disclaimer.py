"""Mini Monster AI — legal disclaimer and privacy notice."""
from __future__ import annotations

DISCLAIMER_ZH = """【免責聲明與隱私說明】

Developed by Suckbob | Mini Monster AI v1.0

1. **Likeness（肖像相似）僅限合法用途**
   - 您必須上傳**本人擁有權利**或**已獲明確授權**的參考圖／音訊。
   - 禁止未經同意模仿真實公眾人物、偶像、名人進行惡意或非法用途。
   - 同人創作請遵守當地法律與平台規範；本軟體不提供任何侵權內容。

2. **R18+ 內容**
   - 僅供成年用戶在**本地私人環境**使用。
   - 您對生成內容負全部責任。

3. **網絡學習模式（可選）**
   - 預設關閉；啟用需明確同意。
   - 上傳資料為**匿名化**成功率／相似度指標，不含原圖、原音、可識別個資。
   - 可隨時撤銷同意；本機參考檔不會自動上傳。

4. **隱私**
   - 參考圖與語音樣本存於本機 `data/mini/references/`。
   - 我們不收集可識別您身份的生成內容，除非您主動啟用匿名統計。

使用本軟體即表示您已閱讀並同意上述條款。"""

DISCLAIMER_EN = """Mini Monster AI — Disclaimer & Privacy

Developed by Suckbob

1. Likeness features require references you own or are authorized to use.
   Do not impersonate real persons without consent.

2. R18+ output is for local adult use only; you are solely responsible.

3. Optional network learning uploads anonymized success/similarity metrics only.

4. Reference files stay on your machine unless you opt in to anonymous stats."""


def get_disclaimer(locale: str = "zh-TW") -> dict[str, str]:
    if locale.startswith("en"):
        return {"locale": "en", "text": DISCLAIMER_EN}
    return {"locale": locale, "text": DISCLAIMER_ZH}
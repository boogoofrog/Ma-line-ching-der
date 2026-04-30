# 2330 台積電每日追蹤器

執行台積電 (2330) 每日追蹤，彙整股價、新聞、PTT 輿論。

## 執行步驟

### 1. 執行追蹤腳本

用 Bash 執行專案根目錄的 `tsmc_tracker.py`：

```bash
python3 tsmc_tracker.py
```

若腳本執行失敗，改用以下備用流程（步驟 2–4）手動抓取。

---

### 2. 備用：股價

用 WebFetch 取得 TWSE 即時報價：

**URL:** `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_2330.tw&json=1&delay=0`

解析 JSON：
- `msgArray[0].z` = 成交價
- `msgArray[0].y` = 昨收
- `msgArray[0].h` / `.l` / `.o` = 最高 / 最低 / 開盤
- `msgArray[0].v` = 成交量

若 TWSE 失敗，改用 Yahoo Finance：
**URL:** `https://query1.finance.yahoo.com/v8/finance/chart/2330.TW?interval=1d&range=1d`

---

### 3. 備用：新聞

用 WebFetch 取 Google News RSS：

**URL:** `https://news.google.com/rss/search?q=台積電+2330&hl=zh-TW&gl=TW&ceid=TW:zh-Hant`

解析 XML，列出前 8 則 `<item>` 的 `<title>`、`<pubDate>`。

---

### 4. 備用：PTT 輿論

用 WebFetch 抓 PTT Stock 板搜尋結果：

**URL:** `https://www.ptt.cc/bbs/Stock/search?q=2330`

（需帶 Cookie: `over18=1`）

從 HTML 的 `r-ent` class div 抓出文章標題與推文數。

---

## 輸出格式

以下列格式整理並回報，語言用繁體中文：

```
========================================================
  台積電 (2330) 每日追蹤報告 — YYYY-MM-DD
========================================================

【 股價 】
  成交價 : XXX 元
  漲跌   : +X.XX (+X.XX%)
  開盤/最高/最低 : XXX / XXX / XXX
  昨收   : XXX   成交量: XXX 張

【 最新新聞 】（最多 8 則）
   1. 標題 [來源]  日期
   2. ...

【 PTT Stock 板輿論 】（最多 8 篇）
   1. [推數] 標題  日期
   2. ...

========================================================
```

最後加上一段 **2-3 句的整體小結**，說明今日 2330 的市場氛圍與值得注意的重點。

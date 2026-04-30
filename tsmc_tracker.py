#!/usr/bin/env python3
"""
2330 台積電每日追蹤器
追蹤股價、新聞、PTT 輿論
"""

import sys
import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

TODAY = datetime.date.today().strftime("%Y-%m-%d")
STOCK_CODE = "2330"
STOCK_NAME = "台積電"


def fetch(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; TSMC-Tracker/1.0)")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None


# ── 1. 股價（TWSE 即時行情 API）──────────────────────────────────────────────

def get_stock_price():
    url = (
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        f"?ex_ch=tse_{STOCK_CODE}.tw&json=1&delay=0"
    )
    raw = fetch(url)
    if not raw:
        return get_stock_price_yahoo()
    try:
        data = json.loads(raw)
        msg = data["msgArray"][0]
        name   = msg.get("n", STOCK_NAME)
        price  = msg.get("z", msg.get("y", "N/A"))   # z=成交價, y=昨收
        high   = msg.get("h", "N/A")
        low    = msg.get("l", "N/A")
        open_  = msg.get("o", "N/A")
        prev   = msg.get("y", "N/A")
        vol    = msg.get("v", "N/A")
        if price not in ("-", "", "N/A") and prev not in ("-", "", "N/A"):
            try:
                change = round(float(price) - float(prev), 2)
                pct    = round(change / float(prev) * 100, 2)
                change_str = f"{'+' if change >= 0 else ''}{change} ({'+' if pct >= 0 else ''}{pct}%)"
            except Exception:
                change_str = "N/A"
        else:
            change_str = "N/A"
        return {
            "source": "TWSE",
            "name":   name,
            "price":  price,
            "open":   open_,
            "high":   high,
            "low":    low,
            "prev":   prev,
            "change": change_str,
            "volume": vol,
        }
    except Exception:
        return get_stock_price_yahoo()


def get_stock_price_yahoo():
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW"
        "?interval=1d&range=1d"
    )
    raw = fetch(url, headers={"Accept": "application/json"})
    if not raw:
        return {"source": "N/A", "price": "無法取得"}
    try:
        data   = json.loads(raw)
        meta   = data["chart"]["result"][0]["meta"]
        price  = meta.get("regularMarketPrice", "N/A")
        prev   = meta.get("previousClose", "N/A")
        high   = meta.get("regularMarketDayHigh", "N/A")
        low    = meta.get("regularMarketDayLow", "N/A")
        open_  = meta.get("regularMarketOpen", "N/A")
        vol    = meta.get("regularMarketVolume", "N/A")
        if price != "N/A" and prev != "N/A":
            change = round(float(price) - float(prev), 2)
            pct    = round(change / float(prev) * 100, 2)
            change_str = f"{'+' if change >= 0 else ''}{change} ({'+' if pct >= 0 else ''}{pct}%)"
        else:
            change_str = "N/A"
        return {
            "source": "Yahoo Finance",
            "name":   STOCK_NAME,
            "price":  price,
            "open":   open_,
            "high":   high,
            "low":    low,
            "prev":   prev,
            "change": change_str,
            "volume": vol,
        }
    except Exception as e:
        return {"source": "Error", "price": str(e)}


# ── 2. 新聞（Google News RSS）────────────────────────────────────────────────

def get_news(limit=8):
    query = urllib.parse.quote(f"{STOCK_NAME} {STOCK_CODE}")
    url = (
        f"https://news.google.com/rss/search"
        f"?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    )
    raw = fetch(url)
    if not raw:
        return []
    items = []
    try:
        root = ET.fromstring(raw)
        channel = root.find("channel")
        for item in (channel.findall("item") if channel else [])[:limit]:
            title   = (item.findtext("title") or "").strip()
            link    = (item.findtext("link") or "").strip()
            pubdate = (item.findtext("pubDate") or "").strip()
            source_el = item.find("{https://news.google.com/rss}source")
            source  = source_el.text if source_el is not None else ""
            # Strip Google redirect prefix
            if title.startswith("<"):
                continue
            items.append({"title": title, "date": pubdate[:16], "source": source, "link": link})
    except Exception:
        pass
    return items


# ── 3. PTT Stock 板輿論 ──────────────────────────────────────────────────────

def get_ptt(limit=8):
    url = f"https://www.ptt.cc/bbs/Stock/search?q={STOCK_CODE}"
    # PTT 需要 over18 cookie
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("Cookie", "over18=1")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    posts = []
    # 簡單的 HTML parsing，不依賴 BeautifulSoup
    import re
    # 抓 r-ent div 區塊
    blocks = re.findall(r'<div class="r-ent">(.*?)</div>\s*</div>', html, re.DOTALL)
    for block in blocks[:limit]:
        title_m = re.search(r'class="title">\s*(?:<a[^>]*>)?\s*(.*?)(?:</a>)?\s*</div>', block, re.DOTALL)
        like_m  = re.search(r'class="nrec"><span[^>]*>([^<]*)</span>', block)
        date_m  = re.search(r'class="date">\s*([^<]+)</div>', block)
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else "N/A"
        like  = like_m.group(1).strip() if like_m else "0"
        date  = date_m.group(1).strip() if date_m else ""
        if title and title != "N/A":
            posts.append({"title": title, "like": like, "date": date})
    return posts


# ── 輸出報告 ──────────────────────────────────────────────────────────────────

def print_report():
    print(f"\n{'='*60}")
    print(f"  台積電 ({STOCK_CODE}) 每日追蹤報告 — {TODAY}")
    print(f"{'='*60}\n")

    # 股價
    print("【 股價 】")
    info = get_stock_price()
    if "price" in info:
        print(f"  來源   : {info.get('source', '')}")
        print(f"  名稱   : {info.get('name', STOCK_NAME)}")
        price_display = f"{info['price']} 元" if info['price'] not in ("N/A", "無法取得") else info['price']
        print(f"  成交價 : {price_display}")
        print(f"  漲跌   : {info.get('change', 'N/A')}")
        print(f"  開盤   : {info.get('open', 'N/A')}  最高: {info.get('high', 'N/A')}  最低: {info.get('low', 'N/A')}")
        print(f"  昨收   : {info.get('prev', 'N/A')}")
        print(f"  成交量 : {info.get('volume', 'N/A')}")
    print()

    # 新聞
    print("【 最新新聞 】")
    news = get_news()
    if news:
        for i, n in enumerate(news, 1):
            src = f" [{n['source']}]" if n['source'] else ""
            print(f"  {i:2}. {n['title']}{src}")
            if n['date']:
                print(f"       {n['date']}")
    else:
        print("  （無法取得新聞）")
    print()

    # PTT
    print("【 PTT Stock 板輿論 】")
    posts = get_ptt()
    if posts:
        for i, p in enumerate(posts, 1):
            print(f"  {i:2}. [{p['like']:>3}] {p['title']}  {p['date']}")
    else:
        print("  （無法取得 PTT 資料）")
    print()
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print_report()

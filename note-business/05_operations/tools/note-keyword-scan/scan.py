#!/usr/bin/env python3
"""noteキーワードページの一次データ抽出ツール（競合・需要調査用）

note.com の公開キーワードページ（https://note.com/tag/<キーワード>）を通常閲覧し、
ページに埋め込まれた人気記事の一覧（タイトル・価格・スキ数・公開日・セール有無）と、
関連キーワードの記事数（供給量の目安）を抽出する。

利用ルール（事業の方針 D-003）:
- 公開ページの通常閲覧のみ。非公開API（/api/...）は使わない。アクセス制限の回避（ヘッダー偽装等）はしない。
- 1回の調査で最大30ページ、リクエスト間隔は4秒以上あける。

使い方:
    python3 -I scan.py --out result.csv GAS スプレッドシート 経理
    python3 -I scan.py --html saved.html --keyword GAS     # 保存済みHTMLを解析（通信なし）
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
import urllib.parse

MAX_PAGES = 30


def fetch(keyword):
    url = "https://note.com/tag/" + urllib.parse.quote(keyword)
    out = subprocess.run(["curl", "-sS", "-L", "-m", "30", url], capture_output=True, check=True)
    return out.stdout.decode("utf-8", errors="replace")


def rsc_payload(html):
    """Next.jsのRSCペイロード（self.__next_f.push([1,"..."])）を連結して返す。"""
    chunks = []
    for m in re.finditer(r'self\.__next_f\.push\((\[.*?\])\)</script>', html, re.S):
        try:
            arr = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if len(arr) >= 2 and isinstance(arr[1], str):
            chunks.append(arr[1])
    return "".join(chunks)


def parse(html):
    text = rsc_payload(html)
    dec = json.JSONDecoder()
    notes = []
    i = text.find('"initialData":{"notes":[')
    if i >= 0:
        obj, _ = dec.raw_decode(text, i + len('"initialData":'))
        notes = obj.get("notes", [])
    related = []
    for m in re.finditer(r'"keyword":\{"name":"([^"]+)","noteCount":(\d+)\}', text):
        related.append((m.group(1), int(m.group(2))))
    return notes, related


def rows_for(keyword, notes):
    rows = []
    for rank, n in enumerate(notes, 1):
        user = n.get("user") or {}
        sale = next((d for d in (n.get("discountCampaigns") or []) if d.get("status") == "available"), None)
        rows.append({
            "keyword": keyword,
            "rank": rank,
            "title": n.get("name", ""),
            "price": n.get("price") or 0,
            "sale_price": (sale or {}).get("discountedPrice", ""),
            "likes": n.get("likeCount", 0),
            "membership_only": (n.get("readPermissions") or {}).get("membership", False),
            "published": (n.get("publishAt") or "")[:10],
            "author": user.get("nickname", ""),
            "url": f"https://note.com/{user.get('urlname', '')}/n/{n.get('key', '')}",
        })
    return rows


def summarize(keyword, rows, related):
    paid = [r for r in rows if r["price"]]
    prices = sorted(r["price"] for r in paid)
    med = prices[len(prices) // 2] if prices else 0
    likes_paid = sorted((r["likes"] for r in paid), reverse=True)
    print(f"\n## {keyword}: 人気記事{len(rows)}件中 有料{len(paid)}件 / 有料価格の中央値 {med:,}円"
          f" / 有料のスキ上位3 {likes_paid[:3]} / セール中 {sum(1 for r in paid if r['sale_price'] != '')}件")
    if related:
        print("   関連キーワード（記事数）: " + "、".join(f"{k}({c:,})" for k, c in related[:10]))
    for r in sorted(paid, key=lambda r: -r["likes"])[:5]:
        print(f"   - ¥{r['price']:,} ♡{r['likes']} {r['published']} {r['title'][:60]}（{r['author']}）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="*")
    ap.add_argument("--out", help="CSV出力先")
    ap.add_argument("--html", help="保存済みHTMLを解析する（通信なし）")
    ap.add_argument("--keyword", default="(saved)")
    ap.add_argument("--sleep", type=float, default=4.0)
    a = ap.parse_args()

    all_rows = []
    if a.html:
        notes, related = parse(open(a.html, encoding="utf-8").read())
        rows = rows_for(a.keyword, notes)
        summarize(a.keyword, rows, related)
        all_rows += rows
    else:
        if len(a.keywords) > MAX_PAGES:
            sys.exit(f"キーワードは{MAX_PAGES}個までにしてください")
        for idx, kw in enumerate(a.keywords):
            if idx:
                time.sleep(max(a.sleep, 4.0))
            notes, related = parse(fetch(kw))
            rows = rows_for(kw, notes)
            summarize(kw, rows, related)
            all_rows += rows
    if a.out and all_rows:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f"\nCSV: {a.out}（{len(all_rows)}行）")


if __name__ == "__main__":
    main()

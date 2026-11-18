#!/usr/bin/env python3
"""108 検証: 文例6本の字数（件名つき200〜350字）、日付と曜日、金額の計算を確かめる。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
date_pat = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日（([月火水木金土日])）")
ng = 0
for f in sorted((here / "templates").glob("t*.txt")):
    t = f.read_text(encoding="utf-8")
    n = len(re.sub(r"\s", "", t.replace("（署名）", "")))
    ok_len = 200 <= n <= 350
    print(f"[{f.name}] 字数（空白・署名欄を除く）{n} {'OK' if ok_len else 'NG（200〜350字の外）'}")
    ng += not ok_len
    for y, m, d, w in date_pat.findall(t):
        real = W[dt.date(int(y or 2026), int(m), int(d)).weekday()]
        print(f"  {y or '2026'}/{m}/{d}（{w}） 暦では（{real}） {'OK' if real == w else 'NG'}")
        ng += real != w
    for a in re.findall(r"(\d{1,3}(?:,\d{3})+)円", t):
        print(f"  金額 {a}円")
# 金額の計算（税抜×1.1）と、文例どうしの一致
calc = {"165,000": 150000 * 110 // 100, "176,000": 160000 * 110 // 100}
for k, v in calc.items():
    ok = int(k.replace(",", "")) == v
    print(f"計算 {k}円 = 税抜{v*100//110:,}円×1.1 → {v:,}円 {'OK' if ok else 'NG'}")
    ng += not ok
amounts = set()
for f in (here / "templates").glob("t*.txt"):
    t = f.read_text(encoding="utf-8")
    amounts |= set(re.findall(r"(\d{1,3}(?:,\d{3})+)円", t))
print("文例に出てくる金額:", sorted(amounts), "（176,000円は文例3の訂正前のみ）")
print("NG件数:", ng)

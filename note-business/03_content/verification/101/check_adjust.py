#!/usr/bin/env python3
"""101 調整用プロンプトの出力を、元の文面と見比べる。
- 日付（曜日つき）と〔　〕の置き換え記号が、元の文面と同じ集合か
- 字数（空白・改行を除く）が短くなったか
- 敬語の語尾「いたします」「申し上げます」が減っていないか（丁寧さが下がっていないかの目安）
使い方: python3 -I -B check_adjust.py output_adjust_v1.md [output_adjust_v2.md]
"""
import re, sys
SRC = open("output_create_v2.md", encoding="utf-8").read().split("## 文例1")[1].split("## 文例2")[0]
DATE = re.compile(r"(?:\d{4}年)?\d{1,2}月\d{1,2}日[（(][月火水木金土日][）)]")
PH = re.compile(r"〔[^〕]+〕")
def parts(t):
    t = t.split("## 直した文面", 1)[1] if "## 直した文面" in t else t
    letter = t.split("## 変えた箇所", 1)[0]
    return letter.split("\n---")[0]
def stats(t):
    return {"dates": sorted(set(DATE.findall(t))), "ph": sorted(set(PH.findall(t))),
            "chars": len(re.sub(r"\s", "", t)), "itashimasu": t.count("いたします") + t.count("申し上げます"),
            "casual": re.findall(r"[^。\n]{0,8}(?<!いた)します。", t)}
src = stats(SRC.split("\n", 1)[1])
print("元の文面:", src)
for p in sys.argv[1:]:
    raw = open(p, encoding="utf-8").read()
    out = stats(parts(raw.split("---", 1)[1]))
    print(f"\n== {p}")
    print("  日付:", "一致" if out["dates"] == src["dates"] else f"不一致 {out['dates']}")
    print("  置き換え記号:", "一致" if out["ph"] == src["ph"] else f"不一致 {out['ph']}")
    print(f"  字数: {src['chars']} → {out['chars']}字")
    print(f"  「いたします」「申し上げます」の数: {src['itashimasu']} → {out['itashimasu']}")
    print(f"  「いたします」を崩した語尾（〜します。）: {out['casual'] if out['casual'] else 'なし'}")
    print("  変えた箇所の一覧:", "あり" if "## 変えた箇所" in raw else "なし")

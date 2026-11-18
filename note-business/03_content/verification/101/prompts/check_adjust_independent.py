#!/usr/bin/env python3
"""101 調整用プロンプトの独立実行の出力を、元の文面（create_v2.run1 の文例1）と見比べる。
- 曜日つきの日付と〔　〕が元と同じ集合か／年を省いた日付がないか
- 敬語の崩れ（「いたします」→「します」）がないか
- 変えた箇所の一覧があるか、字数（空白・改行を除く）
使い方: python3 -I -B check_adjust_independent.py adjust_v1.run1.md ...
"""
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "create_v2.run1.article.txt"), encoding="utf-8").read().split("=== ")[1].split("\n", 1)[1].strip()
DATE = re.compile(r"(?:\d{4}年)?\d{1,2}月\d{1,2}日[（(][月火水木金土日][）)]")
PH = re.compile(r"〔[^〕]+〕")
CASUAL = re.compile(r"[^。\n]{0,10}(?<!いた)(?<!申し上げ)(?<!ござい)します[。が]")
def stats(t):
    return {"dates": sorted(set(DATE.findall(t))), "ph": sorted(set(PH.findall(t))),
            "chars": len(re.sub(r"\s", "", t)), "casual": CASUAL.findall(t),
            "no_year": [d for d in DATE.findall(t) if "年" not in d]}
s0 = stats(src)
print("元の文面:", {k: s0[k] for k in ("dates", "chars", "casual", "no_year")})
for p in sys.argv[1:]:
    raw = open(p, encoding="utf-8").read().split("\n---\n", 1)[1]
    letter, _, changes = raw.partition("\n---\n")
    s = stats(letter)
    print(f"\n== {os.path.basename(p)}")
    print("  曜日つきの日付:", "元と同じ" if s["dates"] == s0["dates"] else f"元と違う {s['dates']}")
    print("  年を省いた日付:", s["no_year"] or "なし")
    print("  〔　〕:", "元と同じ" if s["ph"] == s0["ph"] else f"元と違う {s['ph']}")
    print(f"  字数: {s0['chars']} → {s['chars']}字")
    print("  敬語の崩れ（〜します。／〜しますが）:", s["casual"] or "なし")
    print("  変えた箇所の一覧:", "あり" if re.search(r"変更点|変えた箇所", changes) else "なし")

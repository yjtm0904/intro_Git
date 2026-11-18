#!/usr/bin/env python3
"""203 作り直す依頼文の出力を点検する（字数・日付と曜日・元の条件の残り・【要確認】・変えた箇所の数）。
使い方: python3 -I -B check_rebuild.py output_rebuild_v1.md output_rebuild_v2.md
"""
import re, sys, datetime
W = "月火水木金土日"
for p in sys.argv[1:]:
    t = open(p, encoding="utf-8").read()
    doc = t.split("## 作り直した文書", 1)[1].split("## 変えた箇所", 1)[0].strip()
    changes = t.split("## 変えた箇所", 1)[1]
    n = len(re.sub(r"\s", "", doc))
    print(f"== {p}")
    print("  字数（空白・改行を除く）:", n, "→", "100字以内" if n <= 100 else "100字超")
    for m in re.finditer(r"(\d{1,2})月(\d{1,2})日[（(]([月火水木金土日])[）)]", doc):
        mo, d, w = int(m.group(1)), int(m.group(2)), m.group(3)
        real = W[datetime.date(2027 if mo < 11 else 2026, mo, d).weekday()]
        print("  日付", m.group(0), "→", real, "曜日", "一致" if real == w else "不一致")
    for k in ["件名", "社員各位", "休み中の問い合わせ」シート", "1月6日"]:
        print(f"  元の「{k}」が残っているか:", k in doc)
    print("  【要確認】:", "【要確認" in doc)
    print("  変えた箇所の数:", len(re.findall(r"^- ", changes, flags=re.M)))
    if "100字以内に" in changes and n > 100:
        print("  注意: 「変えた箇所」で100字以内と説明しているが、実際は", n, "字")

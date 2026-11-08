#!/usr/bin/env python3
"""改造した依頼文の出力が、【形式】の指定（150字以内、件名なし、決まりの一文）を守っているかを確かめる。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
md = (here / "customize-run.md").read_text(encoding="utf-8")
out = md.split("出力：")[1].split("```")[1].strip("\n")
n = len(re.sub(r"\s", "", out))
W = "月火水木金土日"
dates = re.findall(r"(\d{1,2})月(\d{1,2})日（([月火水木金土日])）", out)
ok_dates = all(W[dt.date(2026, int(m), int(d)).weekday()] == w for m, d, w in dates)
print(f"字数（空白を除く）: {n}（上限150） {'OK' if n <= 150 else 'NG'}")
print(f"件名の行: {'あり（NG）' if '件名' in out else 'なし（OK）'}")
print(f"決まりの一文「分からない点は総務まで」: {'あり（OK）' if '分からない点は総務まで' in out else 'なし（NG）'}")
print(f"日付と曜日: {len(dates)}か所 {'OK' if ok_dates else 'NG'}")
print(f"記号: {sorted(set(re.findall(r'〔[^〕]+〕', out)))}")

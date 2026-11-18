#!/usr/bin/env python3
"""104 検証: 出力の日付と曜日が暦と合っているか、入力にない数字が出ていないかを確かめる。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
memo = (here / "input-memo.txt").read_text(encoding="utf-8")
tr = (here / "input-transcript.txt").read_text(encoding="utf-8")
pairs = [("p1-v1.txt", memo), ("p1-v2.txt", memo), ("p2-v1.txt", tr), ("p2-v2.txt", tr)]
date_pat = re.compile(r"(?:(\d{4})年)?(\d{1,2})(?:月|/)(\d{1,2})日?（([月火水木金土日])）")
num_pat = re.compile(r"\d[\d,]*")
def nums(s):
    # 箇条書きの番号（行頭の「1.」）と、項目番号への言及（「1〜5が一致」「決定事項4」）は数えない
    s = re.sub(r"(?m)^\s*\d+\.\s", "", s)
    s = re.sub(r"\d+〜\d+が一致|決定事項\d+", "", s)
    return {n.replace(",", "") for n in num_pat.findall(s)}
for name, src in pairs:
    out = (here / "outputs" / name).read_text(encoding="utf-8")
    print(f"[{name}]")
    bad = 0
    for y, m, d, w in date_pat.findall(out):
        real = W[dt.date(int(y or 2026), int(m), int(d)).weekday()]
        ok = real == w
        bad += not ok
        print(f"  日付 {m}/{d}（{w}） 暦では（{real}） {'OK' if ok else 'NG'}")
    extra = sorted(nums(out) - nums(src), key=lambda x: int(x))
    print(f"  曜日の誤り: {bad}件")
    print(f"  入力にない数字: {extra if extra else 'なし'}")

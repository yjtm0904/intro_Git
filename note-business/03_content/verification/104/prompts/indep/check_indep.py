#!/usr/bin/env python3
"""104 独立実行の出力：日付と曜日、入力にない数字、「来週中」の扱い、年の補足を機械で確かめる（目視の点検は README）。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
memo = (here.parent.parent / "input-memo.txt").read_text(encoding="utf-8")
tr = (here.parent.parent / "input-transcript.txt").read_text(encoding="utf-8")
DATE = re.compile(r"(?:(\d{4})年)?(\d{1,2})(?:月|/)(\d{1,2})日?（([月火水木金土日])）")
def nums(s):
    s = re.sub(r"(?m)^\s*(\d+)\.\s", "", s)
    s = re.sub(r"[①-⑳]|\(\d\)", "", s)
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", s)}
out = []
for name, src in [("p1-v1", memo), ("p1-v2", memo), ("p2-v1", tr), ("p2-v2", tr)]:
    for n in (1, 2):
        t = (here / f"{name}.run{n}.txt").read_text(encoding="utf-8")
        body = re.split(r"\n### メモから読み取れなかった点|\n確認していただきたい点|\n補足：", t)[0]
        bad = [f"{m}/{d}（{w}）" for y, m, d, w in DATE.findall(body) if W[dt.date(int(y or 2026), int(m), int(d)).weekday()] != w]
        extra = sorted(nums(body) - nums(src), key=int)
        kotoba = re.findall(r"来週中[^\n|]*", body)
        out.append(f"[{name} run{n}] 曜日の誤り:{bad or 'なし'}／入力にない数字:{extra or 'なし'}／年の補足:{'あり' if '2026年' in body else 'なし'}／「来週中」の書き方:{kotoba}")
res = "\n".join(out); (here / "check_indep-result.txt").write_text(res + "\n", encoding="utf-8"); print(res)

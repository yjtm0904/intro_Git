#!/usr/bin/env python3
"""1回目（共通の前置きv1）の場面1〜5の出力を、check.py と同じ観点で点検する。"""
import re, datetime as dt, pathlib, json
here = pathlib.Path(__file__).parent
md = (here / "batch1-v1.md").read_text(encoding="utf-8")
scenes = json.load(open(here / "scenes_part1.json", encoding="utf-8"))[:5]
blocks = re.findall(r"## 場面(\d) [^\n]*\n\n```\n(.*?)```", md, flags=re.S)
W = "月火水木金土日"
for (no, out), s in zip(blocks, scenes):
    dates = re.findall(r"(\d{1,2})月(\d{1,2})日（([月火水木金土日])）", out)
    bad = [f"{m}/{d}" for m, d, w in dates if W[dt.date(2026, int(m), int(d)).weekday()] != w]
    new = sorted(set(re.findall(r"〔[^〕]+〕", out)) - set(re.findall(r"〔[^〕]+〕", s["input"])))
    rel = sorted(set(re.findall(r"本日|明日|昨日", out)))
    print(f"場面{no}: 日付{len(dates)}か所 曜日の誤り{len(bad)}／入力にない記号{new}／言い換え{rel or 'なし'}／説明の付記{'あり' if '※' in out else 'なし'}")

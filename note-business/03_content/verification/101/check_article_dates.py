#!/usr/bin/env python3
"""原稿の中の「M月D日（曜）」「M/D（曜）」をすべて抜き出し、カレンダーと照合する。
年の書いていない日付は、11〜12月を2026年、1〜10月を2027年として扱う（記事の対象期間：2026年11月〜2027年4月）。
使い方: python3 -I -B check_article_dates.py <原稿.md>
"""
import datetime, re, sys
W = "月火水木金土日"
PAT = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日[（(]([月火水木金土日])[）)]|(?<![\d/])(\d{1,2})/(\d{1,2})[（(]([月火水木金土日])[）)]")
def main(path):
    text = open(path, encoding="utf-8").read()
    n = ng = 0
    for no, line in enumerate(text.splitlines(), 1):
        for m in PAT.finditer(line):
            if m.group(2):
                y, mo, d, w = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            else:
                y, mo, d, w = None, int(m.group(5)), int(m.group(6)), m.group(7)
            yy = int(y) if y else (2026 if mo >= 11 else 2027)
            real = W[datetime.date(yy, mo, d).weekday()]
            n += 1
            if real != w:
                ng += 1
                print(f"  NG L{no}: {m.group(0)} → {yy}-{mo:02d}-{d:02d} は{real}曜日")
    print(f"{path}: 曜日つきの日付 {n}件、誤り {ng}件")
    return ng
if __name__ == "__main__":
    sys.exit(1 if sum(main(p) for p in sys.argv[1:]) else 0)

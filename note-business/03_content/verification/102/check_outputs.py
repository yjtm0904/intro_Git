#!/usr/bin/env python3
"""102 文例の出力を点検する。

点検すること
1. 本文の字数（件名を除く。空白・改行は数えない）… 改善版の条件は200〜300字
2. 日付と曜日がカレンダーと合うか（11〜12月は2026年、1〜4月は2027年として照合）
3. 依頼文の条件にない日付が足されていないか／曜日のない日付がないか
4. 税・控除の扱いや、申告書の中身に触れる語がないか（本記事の範囲外）

使い方: python3 -I -B check_outputs.py output_v1.md [output_v2.md ...]
"""
import calendar
import datetime
import re
import sys

WEEK = "月火水木金土日"
ALLOWED = {(11, 27), (12, 2), (12, 3)}  # 依頼文の【条件】にある日付
TOPIC = r"確定申告|還付|追徴|控除証明|控除を受け|税額|所得税|損|不利益|罰|法律|義務|マイナンバー|扶養親族|生命保険|所得"
DATE_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日(?:[（(]([月火水木金土日])[）)])?")


def year_of(month):
    return 2026 if month >= 11 else 2027


def sections(text):
    parts = re.split(r"^## (文例\d.*)$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        body = parts[i + 1].split("\n---")[0]
        yield parts[i].strip(), body


def check(path):
    text = open(path, encoding="utf-8").read()
    print(f"\n==== {path}")
    total_issues = 0
    for title, block in sections(text):
        lines = [l for l in block.strip().splitlines()]
        subj = next((l for l in lines if l.startswith("件名：")), None)
        body_lines = lines[lines.index(subj) + 1:] if subj else lines
        body = "".join("".join(body_lines).split())
        n = len(body)
        issues = []
        if subj is None:
            issues.append("件名がない")
        if not (200 <= n <= 300):
            issues.append(f"本文の字数が200〜300字の範囲外（{n}字）")
        for m in DATE_RE.finditer(block):
            y, mo, d, w = m.groups()
            mo, d = int(mo), int(d)
            yy = int(y) if y else year_of(mo)
            real = WEEK[datetime.date(yy, mo, d).weekday()]
            if w is None:
                issues.append(f"曜日のない日付「{m.group(0)}」")
            elif w != real:
                issues.append(f"曜日の誤り「{m.group(0)}」（正しくは{real}）")
            if (mo, d) not in ALLOWED:
                issues.append(f"条件にない日付「{m.group(0)}」")
        for m in re.finditer(TOPIC, block):
            s = max(0, m.start() - 15)
            issues.append(f"範囲外の語「{m.group(0)}」…{block[s:m.end() + 15].strip()}…".replace("\n", " "))
        total_issues += len(issues)
        print(f"-- {title}｜件名：{'あり' if subj else 'なし'}｜本文 {n}字")
        for i in issues:
            print(f"   要確認: {i}")
        if not issues:
            print("   問題なし")
    print(f"== 要確認の合計: {total_issues}件")


if __name__ == "__main__":
    calendar.setfirstweekday(calendar.SUNDAY)
    for p in sys.argv[1:]:
        check(p)

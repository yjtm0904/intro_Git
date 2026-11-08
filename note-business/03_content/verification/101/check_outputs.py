#!/usr/bin/env python3
"""101 休業案内の出力を点検する。

点検すること
1. 件名（Web告知は見出し）があるか。本文の字数（空白・改行を除く）が200〜350字か
   ※文面3は「Webサイト掲載用」に字数の基準を当て、「メール署名用」は告知の行数（1〜2行）を数える
2. 日付と曜日がカレンダーと合うか（12月は2026年、1月は2027年として照合）
3. 条件にない日付がないか／曜日のない日付がないか
4. 条件にないサービス内容（注文・発送など）、電話番号・メールアドレス、根拠を示せない日数、不安をあおる語がないか

使い方: python3 -I -B check_outputs.py output_create_v1.md [...]
"""
import datetime
import re
import sys

WEEK = "月火水木金土日"
ALLOWED = {(2026, 12, 29), (2027, 1, 4), (2027, 1, 5)}
DATE_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日(?:[（(]([月火水木金土日])[）)])?"
                     r"|(?<![\d/])(\d{1,2})/(\d{1,2})(?:[（(]([月火水木金土日])[）)])?")
CHECKS = {
    "条件にないサービス内容": r"注文|発送|出荷|納品|配送|お支払|入金",
    "条件にない連絡先": r"\d{2,4}-\d{2,4}-\d{3,4}|[\w.+-]+@[\w-]+\.[\w.]+",
    "根拠を示せない日数": r"\d+\s*[〜~～-]\s*\d+\s*(週間|日)|\d+\s*(週間|日)前|\d+営業日",
    "不安をあおる語": r"失礼|マナー違反|必ず|今すぐ",
}


def year_of(month):
    return 2026 if month >= 11 else 2027


def date_issues(block):
    out = []
    for m in DATE_RE.finditer(block):
        if m.group(2):
            y, mo, d, w = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        else:
            y, mo, d, w = None, int(m.group(5)), int(m.group(6)), m.group(7)
        yy = int(y) if y else year_of(mo)
        real = WEEK[datetime.date(yy, mo, d).weekday()]
        if w is None:
            out.append(f"曜日のない日付「{m.group(0)}」")
        elif w != real:
            out.append(f"曜日の誤り「{m.group(0)}」（正しくは{real}）")
        if (yy, mo, d) not in ALLOWED:
            out.append(f"条件にない日付「{m.group(0)}」")
    return out


def count(text):
    return len(re.sub(r"\s", "", text))


def body_after_subject(lines):
    subj = next((l for l in lines if l.startswith(("件名：", "見出し："))), None)
    body = lines[lines.index(subj) + 1:] if subj else lines
    return subj, "\n".join(body)


def check(path):
    text = open(path, encoding="utf-8").read()
    print(f"\n==== {path}")
    parts = re.split(r"^## ((?:文面|文例)\d.*)$", text, flags=re.M)
    total = 0
    for i in range(1, len(parts), 2):
        title, block = parts[i].strip(), parts[i + 1].split("\n---")[0]
        issues = []
        if "【メール署名用】" in block:
            web, sig = block.split("【メール署名用】", 1)
            subj, body = body_after_subject(web.strip().splitlines())
            n = count(body)
            sig_lines = [l for l in sig.strip().splitlines() if l.strip() and not re.fullmatch(r"[━─\-=]+", l.strip())]
            info = f"Web告知 {n}字／署名の告知 {len(sig_lines)}行"
            if not (200 <= n <= 350):
                issues.append(f"Web告知の字数が200〜350字の範囲外（{n}字）")
            if len([l for l in sig_lines if not l.startswith("【")]) > 2:
                issues.append("署名の告知が2行を超える")
        else:
            subj, body = body_after_subject(block.strip().splitlines())
            n = count(body)
            info = f"本文 {n}字"
            if not (200 <= n <= 350):
                issues.append(f"本文の字数が200〜350字の範囲外（{n}字）")
        if subj is None:
            issues.append("件名（見出し）がない")
        issues += date_issues(block)
        for label, pat in CHECKS.items():
            for m in re.finditer(pat, block):
                s = max(0, m.start() - 12)
                issues.append(f"{label}「{m.group(0)}」…{block[s:m.end() + 12].strip()}…".replace("\n", " "))
        total += len(issues)
        print(f"-- {title}｜件名：{'あり' if subj else 'なし'}｜{info}")
        for x in issues:
            print(f"   要確認: {x}")
        if not issues:
            print("   問題なし")
    # 文面の外（前置き・ポイント）も、根拠のない日数と不安をあおる語だけ見る
    outside = parts[0] + "".join(p.split("\n---", 1)[1] if "\n---" in p else "" for p in parts[2::2])
    for label in ("根拠を示せない日数", "不安をあおる語"):
        for m in re.finditer(CHECKS[label], outside):
            s = max(0, m.start() - 15)
            print(f"   要確認（文面の外）: {label}「{m.group(0)}」…{outside[s:m.end() + 15].strip()}…".replace("\n", " "))
            total += 1
    print(f"== 要確認の合計: {total}件")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        check(p)

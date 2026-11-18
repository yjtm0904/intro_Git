#!/usr/bin/env python3
"""プロンプト1 v2 の出力（タブ区切り）が、依頼文の条件を満たすかを確かめる。"""
import csv, re, sys, pathlib
path = pathlib.Path(__file__).parent / "p1-sample-data-v2-output.tsv"
rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
head, body = rows[0], rows[1:]
ng = []
def chk(cond, msg):
    if not cond: ng.append(msg)
chk(head == ["顧客コード","会社名","担当者","電話番号","メールアドレス","前月請求額","支払期日"], f"見出しが違う: {head}")
chk(len(body) == 10, f"行数が10でない: {len(body)}")
codes = [r[0] for r in body]
chk(len(set(codes)) == len(codes), "顧客コードが重複")
for i, r in enumerate(body, 2):
    chk(len(r) == 7, f"{i}行目: 列数が7でない")
    code, co, tanto, tel, mail, amt, due = r
    chk(re.search(r"サンプル|テスト|見本|ダミー", co) is not None, f"{i}行目: 架空と分かる語がない社名 {co}")
    chk(re.fullmatch(r"担当[A-Z]", tanto) is not None, f"{i}行目: 担当者が記号でない {tanto}")
    chk(re.fullmatch(r"03-0000-\d{4}", tel) is not None, f"{i}行目: 電話番号の形が違う {tel}")
    chk(mail.endswith("@example.com"), f"{i}行目: メールのドメインが違う {mail}")
    chk(re.fullmatch(r"\d+", amt) is not None, f"{i}行目: 金額が数字だけでない {amt}")
    if amt.isdigit():
        v = int(amt)
        chk(10000 <= v <= 500000 and v % 1000 == 0, f"{i}行目: 金額が範囲外か1,000円単位でない {v}")
    chk(due in ("2026/11/30", "2026/12/31"), f"{i}行目: 支払期日が候補外 {due}")
print(f"行数: {len(body)} / 列数: {len(head)}")
print("NG: なし（全条件を満たす）" if not ng else "NG:\n- " + "\n- ".join(ng))

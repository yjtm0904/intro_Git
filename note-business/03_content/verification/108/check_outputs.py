#!/usr/bin/env python3
"""108 検証: AIの出力に、強い表現・入力にない約束・日付と曜日の誤り・入力にない金額・記号の書き換えがないかを確かめる。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
STRONG = r"遅延損害金|延滞金|法的|訴訟|裁判|弁護士|内容証明|督促状|取引.{0,10}(停止|見直|検討|中止)|支払条件|然るべき|しかるべき|措置|至急|必ず"
PROMISE = r"電話|再発防止|確認体制|二度と|今後は|今後このような"
date_pat = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日（([月火水木金土日])）")
pairs = [("create-v1", "create-v1"), ("create-v1b", "create-v1b"), ("create-v2", "create-v2"),
         ("create-v2b", "create-v2b"), ("adjust-v1", "adjust-v1"), ("adjust-v2", "adjust-v2")]
for out_name, in_name in pairs:
    out = (here / "outputs" / f"{out_name}.txt").read_text(encoding="utf-8")
    src = (here / "prompts" / f"{in_name}.txt").read_text(encoding="utf-8")
    mail = out.split("\n変えた箇所")[0]
    # 本文の字数（件名・宛名・署名の行を除く）
    lines = [l for l in mail.splitlines() if l.strip()]
    body = [l for l in lines[1:] if not re.fullmatch(r"〔[^〕]+〕(様)?|〔自社〕〔氏名〕|〔氏名〕|〔自社〕", l.strip())]
    n_body = len(re.sub(r"\s", "", "".join(body)))
    # 依頼文の【守ること】にある語は除いて探す（出力だけを見る）
    strong = sorted({m.group() for m in re.finditer(STRONG, mail)})
    promise_out = {m.group() for m in re.finditer(PROMISE, mail)}
    promise_in = {m.group() for m in re.finditer(PROMISE, src.split("【守ること】")[0])}
    promise = sorted(promise_out - promise_in)
    bad_dates = []
    for y, m, d, w in date_pat.findall(mail):
        real = W[dt.date(int(y or 2026), int(m), int(d)).weekday()]
        if real != w:
            bad_dates.append(f"{m}/{d}（{w}→{real}）")
    amt = lambda s: set(re.findall(r"\d{1,3}(?:,\d{3})+", s))
    extra_amt = sorted(amt(mail) - amt(src))
    sym_in = set(re.findall(r"〔[^〕]+〕", src)) - {"〔 〕"}  # 指示文の「〔 〕の記号は…」は記号ではない
    sym_out = set(re.findall(r"〔[^〕]+〕", mail))
    lost = sorted(sym_in - sym_out)
    print(f"[{out_name}] 本文{n_body}字")
    print(f"  強い表現: {strong or 'なし'}")
    print(f"  入力にない約束の語: {promise or 'なし'}")
    print(f"  曜日の誤り: {bad_dates or 'なし'}／入力にない金額: {extra_amt or 'なし'}／消えた記号: {lost or 'なし'}")

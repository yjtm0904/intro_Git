#!/usr/bin/env python3
"""108 独立実行（各2回）の出力の点検：強い表現・入力にない約束や依頼・曜日・金額・記号・文面のあとの説明。"""
import re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
STRONG = r"遅延損害金|損害金|延滞金|法的|訴訟|裁判|弁護士|内容証明|督促状|取引.{0,10}(停止|見直|検討|中止)|支払条件|然るべき|しかるべき|措置|至急|必ず"
PROMISE = r"電話|再発防止|確認体制|徹底|二度と|再発行|破棄|上長より"
DATE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日（([月火水木金土日])）")
out = []
for name in ["create-v1", "create-v1b", "create-v2", "create-v2b", "create-v3", "create-v3b", "adjust-v1", "adjust-v2"]:
    src = (here / f"{name}.prompt.txt").read_text(encoding="utf-8")
    src_info = src.split("【守ること】")[0]
    for n in (1, 2):
        t = (here / f"{name}.run{n}.txt").read_text(encoding="utf-8")
        mail = re.split(r"\n---\n\n?\*\*(主な変更点|補足|変えた箇所)|\n---\n\n[-・]|\n---\n\n本文は|\n---\n\n\*\*変えた箇所", t)[0]
        note = len(mail.strip()) < len(t.strip()) - 5
        strong = sorted({m.group() for m in re.finditer(STRONG, mail)} - {m.group() for m in re.finditer(STRONG, src_info)})
        nosym = re.sub(r"〔[^〕]*〕", "", mail)  # 署名の〔電話番号〕などは約束ではない
        prom = sorted({m.group() for m in re.finditer(PROMISE, nosym)} - {m.group() for m in re.finditer(PROMISE, src_info)})
        bad = [f"{m}/{d}" for y, m, d, w in DATE.findall(mail) if W[dt.date(int(y or 2026), int(m), int(d)).weekday()] != w]
        amt = sorted(set(re.findall(r"\d{1,3}(?:,\d{3})+", mail)) - set(re.findall(r"\d{1,3}(?:,\d{3})+", src)))
        lost = sorted(set(re.findall(r"〔[^〕]+〕", src_info)) - set(re.findall(r"〔[^〕]+〕", mail)) - {"〔 〕"})
        out.append(f"[{name} run{n}] 強い表現:{strong or 'なし'}／入力にない約束・依頼の語:{prom or 'なし'}／曜日の誤り:{bad or 'なし'}／入力にない金額:{amt or 'なし'}／消えた記号:{lost or 'なし'}／文面のあとの説明:{'あり' if note else 'なし'}")
res = "\n".join(out); (here / "check_indep-result.txt").write_text(res + "\n", encoding="utf-8"); print(res)

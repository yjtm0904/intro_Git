#!/usr/bin/env python3
"""102 提出管理表の検算（Python）。

sample_data.csv（架空の20名。社員番号と日付・記号だけ。氏名と申告の中身は入れていない）を読み、
記事に載せる関数と同じ規則で「状況」「件数」「未提出者の一覧」を求める。
LibreOffice で計算した結果（lo_result.csv）があれば、値を突き合わせる。

使い方: python3 -I -B check_table.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = ["扶養控除等申告書", "基礎控除申告書など", "保険料控除申告書"]


def status(row):
    # 記事の式: =IF(COUNTBLANK(B2:D2)>0,"未提出",IF(E2="あり","差し戻し",IF(E2="なし","完了","確認待ち")))
    if any(row[d] == "" for d in DOCS):
        return "未提出"
    if row["不備"] == "あり":
        return "差し戻し"
    if row["不備"] == "なし":
        return "完了"
    return "確認待ち"


def expected():
    with open(os.path.join(HERE, "sample_data.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["状況"] = status(r)
    exp = {
        "rows": rows,
        "未提出の人数(COUNTIF)": sum(r["状況"] == "未提出" for r in rows),
        "差し戻しの人数(COUNTIF)": sum(r["状況"] == "差し戻し" for r in rows),
        "確認待ちの人数(COUNTIF)": sum(r["状況"] == "確認待ち" for r in rows),
        "完了の人数(COUNTIF)": sum(r["状況"] == "完了" for r in rows),
    }
    for d in DOCS:
        exp[f"{d}の空欄(COUNTBLANK)"] = sum(r[d] == "" for r in rows)
    # FILTER(A2:A21,G2:G21="未提出") と、Excel 2019以前向けの INDEX/MATCH で並ぶはずの順番
    exp["未提出者の一覧(FILTER)"] = [r["社員番号"] for r in rows if r["状況"] == "未提出"]
    exp["未提出者の連絡した日(FILTER)"] = [r["連絡した日"] for r in rows if r["状況"] == "未提出"]
    # 補助列 H: =IF(G2="未提出",COUNTIF($G$2:G2,"未提出"),"")
    n = 0
    helper = []
    for r in rows:
        if r["状況"] == "未提出":
            n += 1
            helper.append(n)
        else:
            helper.append("")
    exp["補助列H"] = helper
    return exp


def main():
    exp = expected()
    print("== Pythonで求めた期待値（架空の20名、2026-11-30時点の想定）")
    for r in exp["rows"]:
        print(f"  {r['社員番号']}: {r['状況']}")
    for k, v in exp.items():
        if k != "rows":
            print(f"  {k}: {v}")

    lo_path = os.path.join(HERE, "lo_result.csv")
    if not os.path.exists(lo_path):
        print("\n(lo_result.csv がないため、LibreOffice との照合は省略)")
        return
    with open(lo_path, encoding="utf-8") as f:
        lo = {row[0]: row[1:] for row in csv.reader(f)}
    print("\n== LibreOffice Calc 24.2 の計算結果との照合")
    ng = 0

    def same(label, a, b):
        nonlocal ng
        ok = a == b
        ng += 0 if ok else 1
        print(f"  [{'一致' if ok else '不一致'}] {label}: Python={a} / LibreOffice={b}")

    same("状況（G列・20行）", [r["状況"] for r in exp["rows"]], lo["status"])
    same("未提出の人数", str(exp["未提出の人数(COUNTIF)"]), lo["count_mitei"][0])
    same("差し戻しの人数", str(exp["差し戻しの人数(COUNTIF)"]), lo["count_sashimodoshi"][0])
    same("確認待ちの人数", str(exp["確認待ちの人数(COUNTIF)"]), lo["count_machi"][0])
    same("完了の人数", str(exp["完了の人数(COUNTIF)"]), lo["count_kanryo"][0])
    for i, d in enumerate(DOCS):
        same(f"{d}の空欄", str(exp[f"{d}の空欄(COUNTBLANK)"]), lo["countblank"][i])
    same("補助列H（20行）", [str(x) for x in exp["補助列H"]], lo["helper"])
    lo_list = [x for x in lo["list_index_match"] if x != ""]
    same("Excel 2019以前向けの一覧（INDEX/MATCH）", exp["未提出者の一覧(FILTER)"], lo_list)
    print(f"\n不一致: {ng}件")


if __name__ == "__main__":
    main()

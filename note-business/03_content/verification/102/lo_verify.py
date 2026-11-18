#!/usr/bin/env python3
"""102 提出管理表の関数を LibreOffice Calc 24.2 で実計算する（UNO経由）。

- sample_data.csv（架空の20名）をシートに入れ、記事と同じ式を入れて calculateAll() する。
- 計算結果を lo_result.csv に書き出す（check_table.py が Python の期待値と照合する）。
- オーナー確認用に、同じ表を kanrihyo_sample.xlsx として保存する（FILTER はこの版で計算できないため入れていない）。

使い方: /usr/bin/python3 -I -B lo_verify.py   （LibreOffice の uno モジュールが必要）
UNO の setFormula は英語の関数名と「;」区切りで書く。記事では Excel・スプレッドシート向けに「,」区切りで載せている。
"""
import csv
import datetime
import os
import subprocess
import time

import uno
from com.sun.star.beans import PropertyValue

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = "lo_verify_102"
NULL_DATE = datetime.date(1899, 12, 30)


def prop(name, value):
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def connect():
    proc = subprocess.Popen(
        ["soffice", "--headless", "--invisible", "--nologo", "--norestore", "--nodefault",
         f"--accept=pipe,name={PIPE};urp;StarOffice.ComponentContext"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(120):
        try:
            return proc, resolver.resolve(f"uno:pipe,name={PIPE};urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("LibreOffice に接続できませんでした")


FORMULAS = {
    # 状況（G列）
    "G": '=IF(COUNTBLANK(B{r}:D{r})>0;"未提出";IF(E{r}="あり";"差し戻し";IF(E{r}="なし";"完了";"確認待ち")))',
    # Excel 2019以前向けの補助列（H列）
    "H": '=IF(G{r}="未提出";COUNTIF($G$2:G{r};"未提出");"")',
    # Excel 2019以前向けの一覧（J列）
    "J": '=IFERROR(INDEX($A$2:$A$21;MATCH(ROWS($J$2:J{r});$H$2:$H$21;0));"")',
}
COUNTS = {
    "count_mitei": '=COUNTIF(G2:G21;"未提出")',
    "count_sashimodoshi": '=COUNTIF(G2:G21;"差し戻し")',
    "count_machi": '=COUNTIF(G2:G21;"確認待ち")',
    "count_kanryo": '=COUNTIF(G2:G21;"完了")',
}
BLANKS = ['=COUNTBLANK(B2:B21)', '=COUNTBLANK(C2:C21)', '=COUNTBLANK(D2:D21)']


def main():
    with open(os.path.join(HERE, "sample_data.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    proc, ctx = connect()
    try:
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", True),))
        sh = doc.Sheets.getByIndex(0)
        sh.Name = "提出管理"
        locale = uno.createUnoStruct("com.sun.star.lang.Locale")
        locale.Language, locale.Country = "ja", "JP"
        date_fmt = doc.NumberFormats.queryKey("M/D", locale, False)
        if date_fmt == -1:
            date_fmt = doc.NumberFormats.addNew("M/D", locale)

        for c, h in enumerate(header + ["状況", "補助（2019以前用）", "", "未提出者の一覧（2019以前用）"]):
            sh.getCellByPosition(c, 0).setString(h)
        for r, row in enumerate(data, start=1):
            for c, v in enumerate(row):
                cell = sh.getCellByPosition(c, r)
                if v == "":
                    continue
                try:
                    d = datetime.date.fromisoformat(v)
                    cell.setValue((d - NULL_DATE).days)
                    cell.NumberFormat = date_fmt
                except ValueError:
                    cell.setString(v)
            for col, tmpl in FORMULAS.items():
                ci = ord(col) - ord("A")
                sh.getCellByPosition(ci, r).setFormula(tmpl.format(r=r + 1))

        # 集計欄（L・M列）と書類ごとの空欄数（23行目）
        labels = {"count_mitei": "未提出の人数", "count_sashimodoshi": "差し戻しの人数",
                  "count_machi": "確認待ちの人数", "count_kanryo": "完了の人数"}
        for i, (key, f) in enumerate(COUNTS.items(), start=1):
            sh.getCellByPosition(11, i).setString(labels[key])
            sh.getCellByPosition(12, i).setFormula(f)
        sh.getCellByPosition(0, 22).setString("空欄の数")
        for i, f in enumerate(BLANKS, start=1):
            sh.getCellByPosition(i, 22).setFormula(f)

        doc.calculateAll()

        def col_values(ci):
            return [sh.getCellByPosition(ci, r).getString() for r in range(1, 21)]

        out = [
            ["status"] + col_values(6),
            ["helper"] + col_values(7),
            ["list_index_match"] + col_values(9),
        ]
        for i, key in enumerate(COUNTS, start=1):
            out.append([key, sh.getCellByPosition(12, i).getString()])
        out.append(["countblank"] + [sh.getCellByPosition(i, 22).getString() for i in range(1, 4)])
        with open(os.path.join(HERE, "lo_result.csv"), "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(out)

        # 入れた式の記録（G2・H2・J2 と集計）
        with open(os.path.join(HERE, "lo_formulas.txt"), "w", encoding="utf-8") as f:
            f.write("LibreOffice Calc 24.2 に入れた式（UNOの表記。記事では「,」区切り）\n")
            for addr in ["G2", "H2", "J2", "M2", "M3", "M4", "M5", "B23", "C23", "D23"]:
                cell = sh.getCellRangeByName(addr)
                f.write(f"{addr}: {cell.getFormula()}  → {cell.getString()}\n")

        url = uno.systemPathToFileUrl(os.path.join(HERE, "kanrihyo_sample.xlsx"))
        doc.storeToURL(url, (prop("FilterName", "Calc MS Excel 2007 XML"),))
        doc.close(True)
        print("lo_result.csv / lo_formulas.txt / kanrihyo_sample.xlsx を保存しました")
    finally:
        try:
            desktop.terminate()
        except Exception:
            pass
        proc.wait(timeout=30)


if __name__ == "__main__":
    main()

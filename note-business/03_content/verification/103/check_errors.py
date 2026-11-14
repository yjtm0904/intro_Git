#!/usr/bin/env python3
"""記事103「ExcelとスプレッドシートのエラーをAIに聞く方法」の検算。

1. 架空のサンプル（取引先マスタ10社・商品マスタ10件・請求明細20行。105・107・202と同じ列）を作る
2. エラー7種を起こすブック（103-check.xlsx）を作り、LibreOffice 24.2 で実際に計算させる
   - #N/A・#VALUE!・#DIV/0!・#NAME?・合計のずれ：そのまま計算して、エラーと修正後の値を確かめる
   - #REF!：LibreOffice の上で H列（単価）を実際に削除して、数式が #REF! になることを確かめる
   - 配列が展開できない（#SPILL!）：LibreOffice 24.2 は UNIQUE に対応していないため、Pythonで期待値だけを求め、
     オーナーが Excel（Microsoft 365）とスプレッドシートで表示を確かめる（device-check.md）
3. 修正前後の値を、Pythonで別に求めた期待値と照合する（AIの相談で返ってきた修正の式も含む）
実行: python3 -B check_errors.py   （UNOを使うため -I は付けない。LibreOffice が必要）
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.formula import ArrayFormula

HERE = Path(__file__).resolve().parent
XLSX = HERE / "103-check.xlsx"

MASTER = [
    ("C-001", "株式会社サンプル商事", "経理部", "sample-shoji@example.com"),
    ("C-002", "サンプル工業株式会社", "総務部", "sample-kogyo@example.com"),
    ("C-003", "株式会社見本デザイン", "管理部", "mihon-design@example.com"),
    ("C-004", "架空物流株式会社", "経理課", "kaku-butsuryu@example.com"),
    ("C-005", "株式会社テスト食品", "経理部", "test-foods@example.com"),
    ("C-006", "サンプル建設株式会社", "総務課", "sample-kensetsu@example.com"),
    ("C-007", "有限会社見本印刷", "", "mihon-print@example.com"),
    ("C-008", "株式会社架空システム", "経理部", "kaku-system@example.com"),
    ("C-009", "テスト電機株式会社", "管理課", "test-denki@example.com"),
    ("C-010", "株式会社サンプル企画", "経理部", "sample-kikaku@example.com"),
]
PRODUCTS = [
    ("P-01", "月額保守サービス", 33000, 0.10), ("P-02", "作業費（1時間）", 4500, 0.10),
    ("P-03", "名刺印刷（100枚）", 1650, 0.10), ("P-04", "送料", 980, 0.10),
    ("P-05", "コーヒー豆（軽減税率）", 1296, 0.08), ("P-06", "お弁当（軽減税率）", 864, 0.08),
    ("P-07", "消耗品", 1234, 0.10), ("P-08", "ソフトウェア利用料", 12345, 0.10),
    ("P-09", "飲料（軽減税率）", 157, 0.08), ("P-10", "コピー用紙", 553, 0.10),
]
DETAILS = [  # 取引日（11月の日）, 取引先コード, 商品コード, 数量（20行。すべてマスタにある）
    (2, "C-001", "P-01", 1), (4, "C-002", "P-03", 2), (5, "C-003", "P-02", 3), (6, "C-001", "P-05", 2),
    (9, "C-004", "P-04", 1), (10, "C-005", "P-06", 5), (11, "C-006", "P-07", 3), (12, "C-007", "P-10", 10),
    (13, "C-008", "P-08", 1), (16, "C-009", "P-09", 24), (17, "C-010", "P-02", 2), (18, "C-002", "P-04", 1),
    (19, "C-003", "P-05", 1), (20, "C-002", "P-07", 2), (24, "C-004", "P-01", 1), (25, "C-005", "P-03", 4),
    (26, "C-006", "P-06", 10), (27, "C-008", "P-08", 1), (30, "C-009", "P-10", 5), (30, "C-010", "P-09", 12),
]
M = {r[0]: r for r in MASTER}
P = {r[0]: r for r in PRODUCTS}
NA, VALUE, REF, DIV0, NAME = "#N/A", "#VALUE!", "#REF!", "#DIV/0!", "#NAME?"
AMOUNTS = [q * P[p][2] for (_, _, p, q) in DETAILS]
TOTAL = sum(AMOUNTS)
TEXT_ROWS = (6, 13)  # E7：CSVから貼って「文字」になった金額の行（どちらも 980）
MONTHLY = [("C-001", 33000), ("C-002", 4280), ("C-003", 13500), ("C-004", 0), ("C-005", None)]  # 前月（C-004は0、C-005は空欄）


def this_month(code):
    return sum(a for (d, c, p, q), a in zip(DETAILS, AMOUNTS) if c == code)


EXPECT = {}  # (シート, セル) -> 期待値。削除のあとに読むセルは REF_AFTER で別に持つ


def detail_rows(ws, overrides=None):
    """請求明細と同じ20行を書く。overrides で特定のセルだけ差し替える（エラーを起こす）"""
    ws.append(["対象月", "取引日", "取引先コード", "取引先名", "商品コード", "品目", "数量", "単価", "税率", "金額"])
    for i, (day, c, p, q) in enumerate(DETAILS, start=2):
        row = ["2026-11", f"2026/11/{day:02d}", c, f'=_xlfn.IFNA(VLOOKUP(C{i},取引先マスタ!$A$2:$D$11,2,FALSE),"未登録")',
               p, P[p][1], q, P[p][2], P[p][3], f"=G{i}*H{i}"]
        for (r, col), v in (overrides or {}).items():
            if r == i:
                row[col] = v
        ws.append(row)


def build():
    wb = openpyxl.Workbook()
    wb.calculation.fullCalcOnLoad = True
    ws = wb.active
    ws.title = "取引先マスタ"
    ws.append(["取引先コード", "取引先名", "部署", "メール"])
    for r in MASTER:
        ws.append(list(r))
    ws = wb.create_sheet("商品マスタ")
    ws.append(["商品コード", "品目", "単価", "税率"])
    for r in PRODUCTS:
        ws.append(list(r))
    # 正しい請求明細（比べる元）
    ws = wb.create_sheet("請求明細")
    detail_rows(ws)
    ws["J22"] = "=SUM(J2:J21)"
    EXPECT[("請求明細", "J22")] = TOTAL
    # E1 #N/A：C4 の取引先コードの後ろに空白（CSVから貼った値）
    ws = wb.create_sheet("E1_NA")
    detail_rows(ws, {(4, 2): "C-003 ", (4, 3): "=VLOOKUP(C4,取引先マスタ!$A$2:$D$11,2,FALSE)"})
    ws["L1"], ws["M1"], ws["N1"] = "文字数", "C-003と同じか", "直した式（TRIM）"
    ws["L4"], ws["M4"] = "=LEN(C4)", '=C4="C-003"'
    ws["N4"] = "=VLOOKUP(TRIM(C4),取引先マスタ!$A$2:$D$11,2,FALSE)"
    ws["O1"] = "AIの相談で出た式"
    ws["O4"] = '=VLOOKUP(TRIM(SUBSTITUTE(C4,CHAR(160)," ")),取引先マスタ!$A$2:$D$11,2,FALSE)'
    EXPECT.update({("E1_NA", "D4"): NA, ("E1_NA", "L4"): 6, ("E1_NA", "M4"): False, ("E1_NA", "N4"): M["C-003"][1],
                   ("E1_NA", "D5"): M["C-001"][1], ("E1_NA", "O4"): M["C-003"][1]})
    # E2 #VALUE!：G7 の数量が「5個」
    ws = wb.create_sheet("E2_VALUE")
    detail_rows(ws, {(7, 6): "5個"})
    ws["L1"], ws["M1"] = "数値か", "直した式（文字を取る）"
    ws["L7"], ws["M7"] = "=ISNUMBER(G7)", '=VALUE(SUBSTITUTE(G7,"個",""))*H7'
    ws["N1"] = "AIの相談で出た式"
    ws["N7"], ws["N8"] = '=SUBSTITUTE(G7,"個","")*H7', '=SUBSTITUTE(G8,"個","")*H8'
    EXPECT.update({("E2_VALUE", "J7"): VALUE, ("E2_VALUE", "L7"): False, ("E2_VALUE", "M7"): 5 * 864,
                   ("E2_VALUE", "J8"): AMOUNTS[6], ("E2_VALUE", "N7"): 5 * 864, ("E2_VALUE", "N8"): AMOUNTS[6]})
    # E3 #REF!：H列（単価）を削除する（削除は recalc() の中で LibreOffice に行わせる）。直した式は商品マスタから単価を引く
    ws = wb.create_sheet("E3_REF")
    detail_rows(ws)
    # E4 #DIV/0!：前月比（今月÷前月）。C-004 は前月0、C-005 は前月が空欄
    ws = wb.create_sheet("E4_DIV0")
    ws.append(["取引先コード", "前月の金額", "今月の金額", "前月比", "直した式（0・空欄なら空欄）", "AIの式（N関数）", "AIの式（OR）", "IFERROR（ほかのエラーも隠れる）"])
    for i, (c, prev) in enumerate(MONTHLY, start=2):
        ws.append([c, prev, this_month(c), f"=C{i}/B{i}", f'=IF(B{i}=0,"",C{i}/B{i})',
                   f'=IF(N(B{i})=0,"",C{i}/B{i})', f'=IF(OR(B{i}="",B{i}=0),"",C{i}/B{i})', f'=IFERROR(C{i}/B{i},"")'])
        EXPECT[("E4_DIV0", f"D{i}")] = DIV0 if not prev else this_month(c) / prev
        for col in "EFGH":
            EXPECT[("E4_DIV0", f"{col}{i}")] = "" if not prev else this_month(c) / prev
    # E5 #NAME?：XLOOKUP（LibreOffice 24.2 では未対応＝Excel 2019 と同じく #NAME?）と、関数名の打ち間違い
    ws = wb.create_sheet("E5_NAME")
    detail_rows(ws, {(2, 3): '=_xlfn.XLOOKUP(C2,取引先マスタ!$A$2:$A$11,取引先マスタ!$B$2:$B$11,"未登録")',
                     (3, 3): "=VLOOKUPP(C3,取引先マスタ!$A$2:$D$11,2,FALSE)"})
    ws["L1"] = "直した式（INDEX/MATCH）"
    ws["L2"] = '=_xlfn.IFNA(INDEX(取引先マスタ!$B$2:$B$11,MATCH(C2,取引先マスタ!$A$2:$A$11,0)),"未登録")'
    ws["L3"] = "=VLOOKUP(C3,取引先マスタ!$A$2:$D$11,2,FALSE)"
    ws["M1"] = "AIの相談で出た式（VLOOKUP版）"
    ws["M2"] = '=_xlfn.IFNA(VLOOKUP(C2,取引先マスタ!$A$2:$B$11,2,FALSE),"未登録")'
    EXPECT.update({("E5_NAME", "D2"): NAME, ("E5_NAME", "D3"): NAME, ("E5_NAME", "L2"): M["C-001"][1], ("E5_NAME", "L3"): M["C-002"][1],
                   ("E5_NAME", "M2"): M["C-001"][1]})
    # E6 配列が展開できない：F2 に UNIQUE、F5 に文字（LibreOffice 24.2 は UNIQUE 未対応のため、実機確認の対象）
    ws = wb.create_sheet("E6_SPILL")
    ws["A1"] = "UNIQUEの結果（F2から下）が、F5の文字にぶつかる例"
    ws["F1"], ws["F2"], ws["F5"] = "取引先コード（重複なし）", "=_xlfn.UNIQUE(請求明細!C2:C21)", "メモ：要確認"
    # E7 合計が合わない：CSVから貼った金額のうち、2行が「文字」の 980
    ws = wb.create_sheet("E7_SUM")
    ws.append(["対象月", "取引日", "取引先コード", "取引先名", "商品コード", "品目", "数量", "単価", "税率", "金額", "数値か", "数値に直した金額"])
    for i, ((day, c, p, q), a) in enumerate(zip(DETAILS, AMOUNTS), start=2):
        ws.append(["2026-11", f"2026/11/{day:02d}", c, M[c][1], p, P[p][1], q, P[p][2], P[p][3],
                   str(a) if i in TEXT_ROWS else a, f"=ISNUMBER(J{i})", f"=VALUE(J{i})"])
    ws["J22"], ws["K22"], ws["L22"] = "=SUM(J2:J21)", "=COUNTA(J2:J21)-COUNT(J2:J21)", "=SUM(L2:L21)"
    ws["M21"], ws["N21"], ws["O21"] = "AIの式：数値の件数", "AIの式：文字のセルの合計", "AIの式：文字も数える合計（配列）"
    ws["M22"], ws["N22"] = "=COUNT(J2:J21)", "=SUMPRODUCT(--ISTEXT(J2:J21),--TRIM(J2:J21))"
    ws["O22"] = ArrayFormula("O22", '=SUM(--ASC(TRIM(SUBSTITUTE(J2:J21,CHAR(160),""))))')
    EXPECT.update({("E7_SUM", "M22"): len(DETAILS) - len(TEXT_ROWS), ("E7_SUM", "N22"): sum(AMOUNTS[i - 2] for i in TEXT_ROWS),
                   ("E7_SUM", "O22"): TOTAL})
    EXPECT.update({("E7_SUM", "J22"): TOTAL - sum(AMOUNTS[i - 2] for i in TEXT_ROWS), ("E7_SUM", "K22"): len(TEXT_ROWS),
                   ("E7_SUM", "L22"): TOTAL, ("E7_SUM", "K6"): False, ("E7_SUM", "K5"): True})
    for w in wb.worksheets:
        for cell in w[1]:
            cell.font = Font(bold=True)
    wb.save(XLSX)


REF_AFTER = {}  # H列を削除したあとのセル -> 期待値（金額の列はJからIへ1つ左にずれる）


def recalc(path):
    import uno
    from com.sun.star.beans import PropertyValue
    pipe = f"lo103_{os.getpid()}"
    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--nologo", "--norestore", f"--accept=pipe,name={pipe};urp;"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    ctx = None
    for _ in range(80):
        try:
            ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    hidden = PropertyValue()
    hidden.Name, hidden.Value = "Hidden", True
    doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(path)), "_blank", 0, (hidden,))
    doc.calculateAll()

    def read(sheet, a1):
        cell = doc.Sheets.getByName(sheet).getCellRangeByName(a1)
        kind = cell.getType().value
        if cell.getError():
            return cell.getString(), cell.getFormula()
        if kind == "VALUE" or (kind == "FORMULA" and cell.FormulaResultType2 == 1):
            v = cell.getValue()
            return (int(v) if float(v).is_integer() else round(v, 10)), cell.getFormula()
        s = cell.getString()
        return {"TRUE": True, "FALSE": False}.get(s, s), cell.getFormula()

    got = {k: read(*k) for k in EXPECT}
    # E3：H列（単価）を削除 → 金額の式（もとの J2）は I2 に移り、#REF! になる。そのあと直した式を入れる
    sh = doc.Sheets.getByName("E3_REF")
    before = sh.getCellRangeByName("J2").getFormula()
    sh.Columns.removeByIndex(7, 1)
    doc.calculateAll()
    for i in (2, 3, 21):
        REF_AFTER[("E3_REF", f"I{i}")] = REF
    fix = "=G{i}*VLOOKUP(E{i};$商品マスタ.$A$2:$D$11;3;FALSE())"
    for i in (2, 3, 21):
        sh.getCellRangeByName(f"K{i}").setFormula(fix.format(i=i))
        REF_AFTER[("E3_REF", f"K{i}")] = AMOUNTS[i - 2]
    doc.calculateAll()
    for k in REF_AFTER:
        got[k] = read(*k)
    office = "LibreOffice"
    try:
        cp = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
        node = PropertyValue()
        node.Name, node.Value = "nodepath", "/org.openoffice.Setup/Product"
        acc = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (node,))
        office = f"{acc.getByName('ooName')} {acc.getByName('ooSetupVersionAboutBox')}"
    except Exception:
        pass
    spill = read("E6_SPILL", "F2")
    doc.close(True)
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=60)
    return got, office, before, spill


def main():
    build()
    got, office, before, spill = recalc(XLSX)
    lines = [f"# 記事103 エラー7種の検算結果（{office}・Python {sys.version.split()[0]}）",
             "# 実行: python3 -B check_errors.py ／ ブック: 103-check.xlsx（架空データ）", ""]
    ok = ng = 0
    for k, exp in list(EXPECT.items()) + list(REF_AFTER.items()):
        val, formula = got[k]
        same = (val == exp) or (isinstance(exp, float) and isinstance(val, (int, float)) and abs(val - exp) < 1e-9)
        ok += same
        ng += not same
        lines.append(f"{'一致' if same else '不一致'}  {k[0]}!{k[1]}  期待={exp!r}  LibreOffice={val!r}  数式={formula}")
    uniq = list(dict.fromkeys(c for (_, c, _, _) in DETAILS))
    lines += ["", f"E3_REF: 削除の前の J2 の数式 = {before} → H列を削除したあとは上の I列（#REF!）",
              f"E6_SPILL: LibreOffice の F2 = {spill[0]!r}（UNIQUE 未対応）。Excel・スプレッドシートでの期待：F5 の文字を消すと F2〜F{1 + len(uniq)} に {', '.join(uniq)}",
              "", f"実計算での照合: 一致 {ok}件 / 不一致 {ng}件",
              f"参考: 請求明細の金額の合計 = {TOTAL:,}円、E7で文字になった2行を除いた合計 = {TOTAL - sum(AMOUNTS[i - 2] for i in TEXT_ROWS):,}円"]
    (HERE / "check-result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-6:]))
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()

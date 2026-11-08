#!/usr/bin/env python3
"""記事105「VLOOKUP・XLOOKUPをAIに書かせる頼み方」の検算。

1. 架空のサンプル（取引先マスタ10社・商品マスタ10件・請求明細20行・送付記録10行）を作る
2. 記事の8例の数式の「期待する結果」を、Pythonで別に計算する
3. 同じ数式を書いたブック（105-check.xlsx）を作り、LibreOffice 24.2 で実際に計算させて照合する
   - VLOOKUP・INDEX/MATCH・IFNA・SUMPRODUCT は実計算で一致を確認
   - XLOOKUP は LibreOffice 24.2 では #NAME? になる（＝ロジックの検算のみ）。
     105-check.xlsx の「XLOOKUP確認」シートを Excel（Microsoft 365）とスプレッドシートで開き、
     オーナーが「一致」と出ることを確かめる（device-check.md）
実行: python3 -B check_formulas.py   （UNOを使うため -I は付けない。LibreOffice が必要）
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

HERE = Path(__file__).resolve().parent
XLSX = HERE / "105-check.xlsx"

# ---------- 1. 架空のサンプル（会社名・アドレスはすべて架空。202・107と同じ列の構成） ----------
MASTER = [  # 取引先コード, 取引先名, 部署, メール（コードの昇順）
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
PRODUCTS = [  # 商品コード, 品目, 単価（税抜）, 税率
    ("P-01", "月額保守サービス", 33000, 0.10), ("P-02", "作業費（1時間）", 4500, 0.10),
    ("P-03", "名刺印刷（100枚）", 1650, 0.10), ("P-04", "送料", 980, 0.10),
    ("P-05", "コーヒー豆（軽減税率）", 1296, 0.08), ("P-06", "お弁当（軽減税率）", 864, 0.08),
    ("P-07", "消耗品", 1234, 0.10), ("P-08", "ソフトウェア利用料", 12345, 0.10),
    ("P-09", "飲料（軽減税率）", 157, 0.08), ("P-10", "コピー用紙", 553, 0.10),
]
DETAILS = [  # 取引日（11月の日）, 取引先コード, 商品コード, 数量。C-011・P-11 はマスタにない（未登録の確認用）
    (2, "C-001", "P-01", 1), (4, "C-002", "P-03", 2), (5, "C-003", "P-02", 3), (6, "C-001", "P-05", 2),
    (9, "C-004", "P-04", 1), (10, "C-005", "P-06", 5), (11, "C-006", "P-07", 3), (12, "C-007", "P-10", 10),
    (13, "C-008", "P-08", 1), (16, "C-009", "P-09", 24), (17, "C-010", "P-02", 2), (18, "C-002", "P-04", 1),
    (19, "C-003", "P-05", 1), (20, "C-011", "P-07", 2), (24, "C-004", "P-01", 1), (25, "C-005", "P-03", 4),
    (26, "C-006", "P-06", 10), (27, "C-008", "P-11", 1), (30, "C-009", "P-10", 5), (30, "C-010", "P-09", 12),
]
SENT = [  # 送付記録（対象月, 取引先コード, 合計（税込））。202の送付記録と同じ列の位置（C・D・G列）に置く
    ("2026-10", "C-001", 36300), ("2026-10", "C-002", 4708), ("2026-10", "C-003", 14850),
    ("2026-10", "C-004", 1078), ("2026-10", "C-005", 4665), ("2026-11", "C-001", 39099),
    ("2026-11", "C-002", 4708), ("2026-11", "C-003", 16249), ("2026-11", "C-004", 37378),
    ("2026-11", "C-005", 11925),
]
NA, NAME = "#N/A", "#NAME?"
M = {r[0]: r for r in MASTER}
P = {r[0]: r for r in PRODUCTS}


# ---------- 2. Pythonでの期待値（表計算ソフトの関数と同じ考え方で別に計算する） ----------
def vlookup_exact(key, table, col):
    for row in table:
        if row[0] == key:
            return row[col - 1]
    return NA


def vlookup_approx(key, table, col):
    """近似一致（4つ目の引数を省いたとき）。表がコードの昇順なら「key以下で最大の行」を返す"""
    hit = NA
    for row in table:
        if row[0] <= key:
            hit = row[col - 1]
        else:
            break
    return hit


def ifna(v, alt):
    return alt if v == NA else v


def mul(a, b):
    return NA if NA in (a, b) else a * b


EXPECT = {}  # (シート名, セル) -> 期待値
for i, (day, c, p, q) in enumerate(DETAILS, start=2):
    EXPECT[("請求明細", f"D{i}")] = ifna(vlookup_exact(c, MASTER, 2), "未登録")      # 例4（VLOOKUP版）
    EXPECT[("請求明細", f"F{i}")] = ifna(vlookup_exact(p, PRODUCTS, 2), "未登録")
    EXPECT[("請求明細", f"H{i}")] = vlookup_exact(p, PRODUCTS, 3)                     # 例3
    EXPECT[("請求明細", f"I{i}")] = vlookup_exact(p, PRODUCTS, 4)
    EXPECT[("請求明細", f"J{i}")] = mul(q, vlookup_exact(p, PRODUCTS, 3))            # 例3（金額）
    EXPECT[("請求明細", f"L{i}")] = vlookup_exact(c, MASTER, 2)                      # 例1（VLOOKUP版）
    EXPECT[("請求明細", f"M{i}")] = vlookup_exact(c, MASTER, 4)                      # 例2（VLOOKUP版）
    EXPECT[("請求明細", f"N{i}")] = vlookup_approx(c, MASTER, 2)                     # 例7（近似一致）
    EXPECT[("請求明細", f"O{i}")] = ifna(vlookup_exact(c, MASTER, 2), "未登録")      # 例8（INDEX/MATCH版）
LOOKUP_MAILS = ["test-foods@example.com", "sample-kikaku@example.com", "unknown@example.com"]
for i, mail in enumerate(LOOKUP_MAILS, start=2):
    hit = next((r[0] for r in MASTER if r[3] == mail), NA)
    EXPECT[("逆引き", f"B{i}")] = ifna(hit, "未登録")                                   # 例5（INDEX/MATCH版）
TWO = [("2026-10", "C-003"), ("2026-11", "C-004"), ("2026-12", "C-001")]
for i, (mo, c) in enumerate(TWO, start=2):
    hit = next((r[2] for r in SENT if r[0] == mo and r[1] == c), NA)
    EXPECT[("逆引き", f"F{i}")] = ifna(hit, "未登録")                                   # 例6（INDEX/MATCH版）
    EXPECT[("逆引き", f"G{i}")] = sum(1 for r in SENT if r[0] == mo and r[1] == c)      # 1件か確かめる（SUMPRODUCT）
# XLOOKUPの式（LibreOffice 24.2 では #NAME?。期待値は「XLOOKUP確認」シートのE列に書いておく）
XL = [  # (例, 数式, 期待値)
    ("例1 取引先名", '=_xlfn.XLOOKUP(請求明細!C4,取引先マスタ!$A$2:$A$11,取引先マスタ!$B$2:$B$11)', vlookup_exact("C-003", MASTER, 2)),
    ("例2 メール", '=_xlfn.XLOOKUP(請求明細!C2,取引先マスタ!$A$2:$A$11,取引先マスタ!$D$2:$D$11)', vlookup_exact("C-001", MASTER, 4)),
    ("例3 単価", '=_xlfn.XLOOKUP(請求明細!E7,商品マスタ!$A$2:$A$11,商品マスタ!$C$2:$C$11)', vlookup_exact("P-06", PRODUCTS, 3)),
    ("例4 未登録", '=_xlfn.XLOOKUP(請求明細!C15,取引先マスタ!$A$2:$A$11,取引先マスタ!$B$2:$B$11,"未登録")', "未登録"),
    ("例5 左の列", '=_xlfn.XLOOKUP(逆引き!A2,取引先マスタ!$D$2:$D$11,取引先マスタ!$A$2:$A$11,"未登録")', "C-005"),
    ("例6 2つの条件", '=_xlfn.XLOOKUP(1,(送付記録!$C$2:$C$11=逆引き!D2)*(送付記録!$D$2:$D$11=逆引き!E2),送付記録!$G$2:$G$11,"未登録")', 14850),
]
for i, (_, _, exp) in enumerate(XL, start=2):
    EXPECT[("XLOOKUP確認", f"D{i}")] = exp  # LibreOffice では #NAME? になる（下で別に扱う）


# ---------- 3. ブックを作る ----------
def build():
    wb = openpyxl.Workbook()
    wb.calculation.fullCalcOnLoad = True  # Excel・スプレッドシートで開いたときに計算し直す
    ws = wb.active
    ws.title = "取引先マスタ"
    ws.append(["取引先コード", "取引先名", "部署", "メール"])
    for r in MASTER:
        ws.append(list(r))
    ws = wb.create_sheet("商品マスタ")
    ws.append(["商品コード", "品目", "単価", "税率"])
    for r in PRODUCTS:
        ws.append(list(r))
    ws = wb.create_sheet("請求明細")
    ws.append(["対象月", "取引日", "取引先コード", "取引先名", "商品コード", "品目", "数量", "単価", "税率", "金額", "",
               "例1 VLOOKUP", "例2 メール", "例7 近似一致", "例8 INDEX/MATCH"])
    for i, (day, c, p, q) in enumerate(DETAILS, start=2):
        ws.append(["2026-11", f"2026/11/{day:02d}", c,
                   f'=_xlfn.IFNA(VLOOKUP(C{i},取引先マスタ!$A$2:$D$11,2,FALSE),"未登録")', p,
                   f'=_xlfn.IFNA(VLOOKUP(E{i},商品マスタ!$A$2:$D$11,2,FALSE),"未登録")', q,
                   f"=VLOOKUP(E{i},商品マスタ!$A$2:$D$11,3,FALSE)", f"=VLOOKUP(E{i},商品マスタ!$A$2:$D$11,4,FALSE)",
                   f"=G{i}*H{i}", "",
                   f"=VLOOKUP(C{i},取引先マスタ!$A$2:$D$11,2,FALSE)", f"=VLOOKUP(C{i},取引先マスタ!$A$2:$D$11,4,FALSE)",
                   f"=VLOOKUP(C{i},取引先マスタ!$A$2:$D$11,2)",
                   f'=_xlfn.IFNA(INDEX(取引先マスタ!$B$2:$B$11,MATCH(C{i},取引先マスタ!$A$2:$A$11,0)),"未登録")'])
    ws = wb.create_sheet("送付記録")
    ws.append(["記録日時", "モード", "対象月", "取引先コード", "取引先名", "請求書番号", "合計（税込）", "宛先", "状態", "PDFファイル名", "PDFのURL", "メモ"])
    for mo, c, total in SENT:
        ws.append(["", "本番", mo, c, M[c][1], f"INV-{mo.replace('-', '')}-{c}", total, M[c][3], "下書き済み", "", "", ""])
    ws = wb.create_sheet("逆引き")
    ws.append(["メール（例5）", "取引先コード", "", "対象月（例6）", "取引先コード", "合計（税込）", "件数"])
    for i in range(2, 5):
        mail = LOOKUP_MAILS[i - 2]
        mo, c = TWO[i - 2]
        ws.append([mail, f'=_xlfn.IFNA(INDEX(取引先マスタ!$A$2:$A$11,MATCH(A{i},取引先マスタ!$D$2:$D$11,0)),"未登録")', "",
                   mo, c,
                   f'=_xlfn.IFNA(INDEX(送付記録!$G$2:$G$11,MATCH(1,INDEX((送付記録!$C$2:$C$11=D{i})*(送付記録!$D$2:$D$11=E{i}),0),0)),"未登録")',
                   f"=SUMPRODUCT((送付記録!$C$2:$C$11=D{i})*(送付記録!$D$2:$D$11=E{i}))"])
    ws = wb.create_sheet("XLOOKUP確認")
    ws.append(["例", "数式（D列と同じもの）", "", "結果", "期待する結果", "判定"])
    for i, (label, f, exp) in enumerate(XL, start=2):
        ws.append([label, f.replace("_xlfn.", "")[1:], "", f, exp, f'=IF(D{i}=E{i},"一致","不一致")'])
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
    wb.save(XLSX)


# ---------- 4. LibreOffice で計算させる（UNO） ----------
def recalc(path):
    import uno
    from com.sun.star.beans import PropertyValue
    pipe = f"lo105_{os.getpid()}"
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
    out = {}
    for (sheet, a1) in EXPECT:
        cell = doc.Sheets.getByName(sheet).getCellRangeByName(a1)
        err = cell.getError()
        kind = cell.getType().value
        numeric = (kind == "VALUE") or (kind == "FORMULA" and cell.FormulaResultType2 == 1)  # 1 = 数値の結果
        if err:
            val = cell.getString()
        elif numeric:
            v = cell.getValue()
            val = int(v) if float(v).is_integer() else round(v, 10)
        else:
            val = cell.getString()
        out[(sheet, a1)] = (val, cell.getFormula())
    office = {"version": "LibreOffice"}
    try:
        cp = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
        node = PropertyValue()
        node.Name, node.Value = "nodepath", "/org.openoffice.Setup/Product"
        acc = cp.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (node,))
        office["version"] = f"{acc.getByName('ooName')} {acc.getByName('ooSetupVersionAboutBox')}"
    except Exception:
        pass
    doc.close(True)
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=60)
    return out, office


def main():
    build()
    got, office = recalc(XLSX)
    lines = [f"# 記事105 数式の検算結果（{office['version']}・Python {sys.version.split()[0]}）",
             "# 実行: python3 -B check_formulas.py ／ ブック: 105-check.xlsx（架空データ）", ""]
    ok = ng = 0
    for (sheet, a1), exp in EXPECT.items():
        val, formula = got[(sheet, a1)]
        if sheet == "XLOOKUP確認":
            status = "LibreOffice 24.2 は未対応（#NAME?）→ ロジックの検算のみ。実機確認の対象" if val == NAME else f"想定外: {val}"
            lines.append(f"{sheet}!{a1}  期待={exp!r}  LibreOffice={val!r}  {status}")
            continue
        same = (val == exp) or (isinstance(exp, float) and isinstance(val, (int, float)) and abs(val - exp) < 1e-9)
        ok += same
        ng += not same
        lines.append(f"{'一致' if same else '不一致'}  {sheet}!{a1}  期待={exp!r}  LibreOffice={val!r}  数式={formula}")
    total_j = sum(v for (s, a), v in EXPECT.items() if s == "請求明細" and a.startswith("J") and v != NA)
    lines += ["", f"実計算での照合: 一致 {ok}件 / 不一致 {ng}件（XLOOKUPの{len(XL)}式は別扱い）",
              f"参考: 請求明細の金額（J列）の合計（#N/Aの行を除く）= {total_j:,}円"]
    (HERE / "check-result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (HERE / "expected.json").write_text(json.dumps({f"{s}!{a}": v for (s, a), v in EXPECT.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines[-3:]))
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()

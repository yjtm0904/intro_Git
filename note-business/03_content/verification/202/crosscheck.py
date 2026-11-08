#!/usr/bin/env python3
"""記事202の検算（Python）：Node.jsのテスト04が保存した架空データ（dataset.json）を、
Decimal で別に計算し、GASのコードの集計結果（gas-output.json）と1社ずつ照合する。

実行: python3 -I -B crosscheck.py   （先に TZ=Asia/Tokyo node --test code.test.js を実行しておく）
"""
import json
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = {"切り捨て": ROUND_FLOOR, "四捨五入": ROUND_HALF_UP, "切り上げ": ROUND_CEILING}


def rate_of(v):
    """税率のセルの値（0.1・10・'10%'）を 10 / 8 に直す"""
    if isinstance(v, str):
        return int(Decimal(v.strip("%")))
    d = Decimal(str(v))
    return int(d * 100) if d < 1 else int(d)


def main():
    data = json.loads((HERE / "dataset.json").read_text(encoding="utf-8"))
    gas = json.loads((HERE / "gas-output.json").read_text(encoding="utf-8"))
    head = data["details"][0]
    col = {h: i for i, h in enumerate(head)}
    sums = {}
    used = 0
    for row in data["details"][1:]:
        if row[col["対象月"]] != "2026-11":
            continue
        used += 1
        code = row[col["取引先コード"]]
        r = rate_of(row[col["税率"]])
        amount = Decimal(str(row[col["数量"]])) * Decimal(str(row[col["単価"]]))
        s = sums.setdefault(code, {10: Decimal(0), 8: Decimal(0)})
        s[r] += amount
    print(f"対象月 2026-11 の明細: {used}行 / 取引先: {len(sums)}社（マスタ {len(data['master']) - 1}社）")
    ng = 0
    for mode, rounding in MODES.items():
        rows = {x["code"]: x for x in gas[mode]}
        match = 0
        grand = Decimal(0)
        for code, s in sorted(sums.items()):
            tax10 = (s[10] * 10 / 100).quantize(Decimal(1), rounding=rounding)
            tax8 = (s[8] * 8 / 100).quantize(Decimal(1), rounding=rounding)
            total = s[10] + tax10 + s[8] + tax8
            grand += total
            g = rows.get(code)
            mine = [int(s[10]), int(tax10), int(s[8]), int(tax8), int(total)]
            theirs = [g["base10"], g["tax10"], g["base8"], g["tax8"], g["total"]] if g else None
            if mine == theirs:
                match += 1
            else:
                ng += 1
                print(f"  不一致 {mode} {code}: Python={mine} GAS={theirs}")
        extra = set(rows) - set(sums)
        if extra:
            ng += len(extra)
            print(f"  GASにだけある取引先 {mode}: {sorted(extra)}")
        print(f"{mode}: {match}/{len(sums)}社が一致（請求額の合計 {int(grand):,}円）")
    print("結果:", "すべて一致" if ng == 0 else f"不一致 {ng}件")
    sys.exit(1 if ng else 0)


if __name__ == "__main__":
    main()

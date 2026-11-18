#!/usr/bin/env python3
"""週次KPIレポート生成（市場PDCAのCheck工程）

入力: 05_operations/kpi-tracker.csv（オーナーが毎週記入。1行＝1週×1記事）
出力: 標準出力にMarkdown（週次レビューの「1. 今週の数字」と「4. 改善ルール」の判定材料）

使い方:
    python3 -I kpi-report/report.py note-business/05_operations/kpi-tracker.csv [--week 2026-11-16]

判定ルールは 05_operations/weekly-review-template.md §4 と同じ。
計画との比較は、収益シミュレーター（revenue-model）の標準シナリオの月次値を週割りした目安と比べる。
"""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import date

NET_RATE = 0.855  # クレカ決済の手取り率（事務手数料5%＋プラットフォーム利用料10%）。決済方法で変わる
# 標準シナリオの月次手取り（revenue-model 標準、2026年11月始まり）。週の目安は÷4.3
PLAN_MONTHLY_NET = {"2026-11": 1094, "2026-12": 5776, "2027-01": 14799, "2027-02": 22537, "2027-03": 26992,
                    "2027-04": 35224, "2027-05": 43137, "2027-06": 50732}


def num(v):
    try:
        return float(v) if v not in ("", None) else 0.0
    except ValueError:
        return 0.0


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("week_start") or "記入例" in (r.get("memo") or ""):
                continue
            rows.append(r)
    return rows


def flags_for(article_rows):
    """記事ごとの判定（weekly-review-template §4）。"""
    out = []
    for r in article_rows:
        views, sales = num(r["views"]), num(r["sales_count"])
        title = r["title"][:30]
        if r["type"] == "paid":
            if views < 30:
                out.append(f"「{title}」: 有料記事のビューが週30未満 → 集客の問題（導線追加・タイトル・見出し画像・SNS）")
            elif views >= 100 and sales / views < 0.01:
                out.append(f"「{title}」: ビュー{int(views)}で購入率{sales / views:.1%} → 訴求の問題（無料部分の価値提示・対象読者・目次。価格は最後）")
            elif sales > 0 and num(r["likes"]) == 0 and num(r["comments"]) == 0:
                out.append(f"「{title}」: 購入はあるが反応がない → 満足度を確認（追記・アップデート）")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--week", help="対象週の開始日（省略時は最新週）")
    a = ap.parse_args()
    rows = load(a.csv)
    if not rows:
        sys.exit("記録がありません（記入例の行は集計から除外しています）")
    by_week = defaultdict(list)
    for r in rows:
        by_week[r["week_start"]].append(r)
    weeks = sorted(by_week)
    week = a.week or weeks[-1]
    if week not in by_week:
        sys.exit(f"{week} の記録がありません。記録のある週: {', '.join(weeks)}")
    prev = weeks[weeks.index(week) - 1] if weeks.index(week) > 0 else None

    def totals(rs):
        t = defaultdict(float)
        for r in rs:
            for k in ("views", "likes", "comments", "new_followers", "sales_count", "gross_revenue_jpy"):
                t[k] += num(r[k])
            if r["type"] == "paid":
                t["paid_views"] += num(r["views"])
        t["net"] = t["gross_revenue_jpy"] * NET_RATE
        return t

    cur, pre = totals(by_week[week]), totals(by_week[prev]) if prev else None

    def delta(k):
        if not pre or not pre[k]:
            return ""
        return f"（前週比 {(cur[k] - pre[k]) / pre[k]:+.0%}）"

    cvr = cur["sales_count"] / cur["paid_views"] if cur["paid_views"] else 0
    ym = week[:7]
    plan_week = PLAN_MONTHLY_NET.get(ym, 0) / 4.3
    print(f"# 週次KPIレポート（{week}の週）\n")
    print("## 1. 今週の数字")
    print(f"- 総ビュー: {int(cur['views']):,}{delta('views')}")
    print(f"- スキ: {int(cur['likes'])}／コメント: {int(cur['comments'])}／フォロワー増: {int(cur['new_followers'])}")
    print(f"- 売上: {int(cur['sales_count'])}件・{int(cur['gross_revenue_jpy']):,}円{delta('gross_revenue_jpy')}／推定手取り: {int(cur['net']):,}円")
    print(f"- 有料記事の購入率（購入数÷有料記事ビュー）: {cvr:.2%}（有料記事ビュー {int(cur['paid_views'])}）")
    if plan_week:
        print(f"- 計画（標準シナリオ）の週あたり手取りの目安: {int(plan_week):,}円 → 達成率 {cur['net'] / plan_week:.0%}")
    print("\n## 2. 記事別（ビュー順）")
    for r in sorted(by_week[week], key=lambda r: -num(r["views"])):
        print(f"- [{r['type']}] {r['title'][:40]}: ビュー{int(num(r['views']))}・スキ{int(num(r['likes']))}・販売{int(num(r['sales_count']))}")
    print("\n## 3. 改善ルールの判定（weekly-review-template §4）")
    flags = flags_for(by_week[week])
    free_top = sorted([r for r in by_week[week] if r["type"] == "free"], key=lambda r: -num(r["views"]))[:3]
    if free_top:
        flags.append("ビュー上位の無料記事（需要の発見 → 同じテーマの有料記事・続編を検討）: " + "、".join(f"「{r['title'][:20]}」" for r in free_top))
    if pre and cur["views"] <= pre["views"] and cur["sales_count"] <= pre["sales_count"]:
        flags.append("ビュー・販売とも前週から伸びていない → 2週続いたら月次レビューを前倒しする")
    print("\n".join(f"- {f}" for f in flags) if flags else "- 該当なし")


if __name__ == "__main__":
    main()

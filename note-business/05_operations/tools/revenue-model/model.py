#!/usr/bin/env python3
"""note事業の収益シミュレーター（依存ライブラリなし）

使い方:
    python3 model.py                 # 内蔵の3シナリオで12か月分を出力
    python3 model.py params.json     # パラメータを上書きして実行

モデル（月次）:
    無料記事PV = Σ(各無料記事の月間PV。公開からの経過月で立ち上がる)
    有料記事PV = 無料記事PV × 有料記事への送客率 + 有料記事数 × 有料記事1本あたりの直接PV
    販売数     = 有料記事PV × 購入率
    売上       = 販売数 × 平均単価
    手取り     = 売上 × 手取り率（決済手数料とプラットフォーム手数料を控除）
    + メンバーシップ（会員数 × 月額 × 手取り率）

パラメータの既定値は仮置き。市場・集客調査のベンチマークで更新すること。
"""
import json
import sys

SCENARIOS = {
    "保守": {
        "months": 12,
        "free_per_month": [8, 8, 6, 6, 6, 6, 4, 4, 4, 4, 4, 4],
        "paid_per_month": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "free_pv_ramp": [15, 30, 45, 60],      # 公開0,1,2,3か月目以降の1本あたり月間PV
        "paid_direct_pv_per_article": 20,       # SNS・note内から有料記事へ直接来るPV/月
        "free_to_paid_ctr": 0.02,
        "purchase_cvr": 0.02,
        "avg_price": 980,
        "net_rate": 0.85,
        "membership_start_month": 7,
        "membership_members_per_month": 1,
        "membership_price": 500,
    },
    "標準": {
        "months": 12,
        "free_per_month": [10, 10, 8, 8, 8, 8, 6, 6, 6, 6, 6, 6],
        "paid_per_month": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        "free_pv_ramp": [30, 60, 100, 130],
        "paid_direct_pv_per_article": 40,
        "free_to_paid_ctr": 0.03,
        "purchase_cvr": 0.03,
        "avg_price": 1280,
        "net_rate": 0.85,
        "membership_start_month": 5,
        "membership_members_per_month": 3,
        "membership_price": 800,
    },
    "楽観": {
        "months": 12,
        "free_per_month": [12, 12, 10, 10, 10, 10, 8, 8, 8, 8, 8, 8],
        "paid_per_month": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
        "free_pv_ramp": [60, 120, 200, 260],
        "paid_direct_pv_per_article": 80,
        "free_to_paid_ctr": 0.04,
        "purchase_cvr": 0.04,
        "avg_price": 1480,
        "net_rate": 0.85,
        "membership_start_month": 4,
        "membership_members_per_month": 6,
        "membership_price": 980,
    },
}


def simulate(p):
    months = p["months"]
    ramp = p["free_pv_ramp"]
    free_cohorts = []  # 各月に公開した無料記事数
    paid_total = 0
    members = 0
    rows = []
    cum_net = 0
    for m in range(months):
        free_cohorts.append(p["free_per_month"][m])
        paid_total += p["paid_per_month"][m]
        free_pv = 0
        for born, n in enumerate(free_cohorts):
            age = m - born
            free_pv += n * ramp[min(age, len(ramp) - 1)]
        paid_pv = free_pv * p["free_to_paid_ctr"] + paid_total * p["paid_direct_pv_per_article"]
        sales = paid_pv * p["purchase_cvr"]
        gross = sales * p["avg_price"]
        if m + 1 >= p["membership_start_month"]:
            members += p["membership_members_per_month"]
        member_gross = members * p["membership_price"]
        net = (gross + member_gross) * p["net_rate"]
        cum_net += net
        rows.append({
            "month": m + 1,
            "free_articles": sum(free_cohorts),
            "paid_articles": paid_total,
            "free_pv": round(free_pv),
            "paid_pv": round(paid_pv),
            "sales": round(sales, 1),
            "members": members,
            "gross": round(gross + member_gross),
            "net": round(net),
            "cum_net": round(cum_net),
        })
    return rows


def to_markdown(name, rows):
    head = "| 月 | 無料記事累計 | 有料記事累計 | 無料PV | 有料PV | 販売数 | 会員数 | 売上 | 手取り | 手取り累計 |\n|---|---|---|---|---|---|---|---|---|---|"
    body = "\n".join(
        f"| {r['month']} | {r['free_articles']} | {r['paid_articles']} | {r['free_pv']:,} | {r['paid_pv']:,} | "
        f"{r['sales']} | {r['members']} | {r['gross']:,}円 | {r['net']:,}円 | {r['cum_net']:,}円 |"
        for r in rows
    )
    return f"### シナリオ: {name}\n\n{head}\n{body}\n"


def main():
    scenarios = dict(SCENARIOS)
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            override = json.load(f)
        for name, params in override.items():
            base = scenarios.get(name, scenarios["標準"])
            scenarios[name] = {**base, **params}
    for name, params in scenarios.items():
        print(to_markdown(name, simulate(params)))


if __name__ == "__main__":
    main()

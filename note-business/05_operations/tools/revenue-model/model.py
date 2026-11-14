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

パラメータは 01_research の調査値（2026-11-07時点）で較正した仮説値。
公開後はDay30から、自分のダッシュボードの実測値（記事あたりPV・遷移率・購入率）で置き換えること。

較正の根拠:
- 手取り率: クレカ決済で1,000円→855円（事務手数料5%、プラットフォーム利用料10%）。キャリア決済などを考慮して0.84とした
- 価格: 売れ筋の実用ノウハウ記事の平均は1,842円。入口980円と主力1,980円を組み合わせる前提で、平均単価を保守980円／標準1,480円／楽観1,680円とした
- 遷移率（無料記事→有料記事ページ）5〜15%、購入率（有料記事ページ→購入）2〜8%（集客調査の仮説値）
- 季節性: noteの流通額は毎年12〜2月に大きく伸びる。1か月目を2026年11月とし、2〜4か月目に係数をかけた
- 公開ペース: 無料記事は週2〜3本（月約10本）、有料記事は月1〜2本（集客調査の90日計画）
"""
import json
import sys

_SEASON = [1.0, 1.15, 1.2, 1.1, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]  # 11月始まり（12〜2月に上振れ）

SCENARIOS = {
    "保守": {
        "months": 12,
        "free_per_month": [8, 8, 8, 8, 6, 6, 6, 6, 6, 6, 6, 6],
        "paid_per_month": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "free_pv_ramp": [10, 25, 40, 60],       # 公開0,1,2,3か月目以降の、無料記事1本あたりの月間PV
        "paid_direct_pv_per_article": 15,       # 検索・note内・SNSから有料記事に直接来るPV（1本あたり/月）
        "free_to_paid_ctr": 0.05,
        "purchase_cvr": 0.02,
        "avg_price": 980,
        "net_rate": 0.84,
        "season": _SEASON,
        "membership_start_month": 8,
        "membership_members_per_month": 1,
        "membership_price": 500,
    },
    "標準": {
        "months": 12,
        "free_per_month": [10, 10, 10, 10, 8, 8, 8, 8, 8, 8, 8, 8],
        "paid_per_month": [1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1],
        "free_pv_ramp": [20, 50, 90, 130],
        "paid_direct_pv_per_article": 30,
        "free_to_paid_ctr": 0.08,
        "purchase_cvr": 0.04,
        "avg_price": 1480,
        "net_rate": 0.84,
        "season": _SEASON,
        "membership_start_month": 6,
        "membership_members_per_month": 3,
        "membership_price": 780,
    },
    "楽観": {
        "months": 12,
        "free_per_month": [12, 12, 12, 12, 10, 10, 10, 10, 10, 10, 10, 10],
        "paid_per_month": [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1],
        "free_pv_ramp": [30, 80, 140, 200],
        "paid_direct_pv_per_article": 40,
        "free_to_paid_ctr": 0.10,
        "purchase_cvr": 0.05,
        "avg_price": 1580,
        "net_rate": 0.84,
        "season": _SEASON,
        "membership_start_month": 5,
        "membership_members_per_month": 5,
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
        season = p.get("season", [1.0] * months)
        s = season[m] if m < len(season) else 1.0
        free_pv *= s
        # 新規アカウントは有料記事への直接流入（検索順位・note内露出）が立ち上がるまで時間がかかる
        acct = p.get("account_ramp", [0.2, 0.5, 1.0])
        a = acct[min(m, len(acct) - 1)]
        paid_pv = free_pv * p["free_to_paid_ctr"] + paid_total * p["paid_direct_pv_per_article"] * s * a
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

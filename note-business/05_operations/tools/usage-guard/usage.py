#!/usr/bin/env python3
"""使用量ガード：このプロジェクトが5時間枠の上限（既定90%）を超えないようにする

オーナーの依頼（2026-11-09）:「5時間枠の90%の量のトークンしかこのプロジェクトでは使わないようにしたい」

仕組み:
1. このプロジェクトの作業記録（~/.claude/projects/-home-user-intro-Git/ 配下のJSONL。メインと全エージェント）と、
   独立実行（claude -p）の結果JSON（note-business/03_content/verification/**/prompts/*.json）から、
   リクエストごとの使用量を集める。
2. 5時間枠を再現する（枠の開始＝前の枠が終わった後の最初のリクエスト時刻を10分単位で切り捨て。過去6回の
   リセット時刻で検証済み）。
3. 過去に上限（HTTP 429）に達した枠で「上限到達までの使用量」を集計し、その中央値を枠の容量（100%）と推定する。
4. 現在の枠の使用量 ÷ 容量 を表示する。--check N は、N%以上なら終了コード1を返す（作業を止める合図）。

限界（必ず理解して使うこと）:
- アカウント全体の公式の計器ではなく、このプロジェクトの記録からの推定。オーナーが他で使った分は数えない
  （＝「このプロジェクトの使用量」を測る目的には合っている）。
- 上限の計算方法は公開されていないため、重みは料金の比率（入力1・キャッシュ作成1.25〜2・キャッシュ読込0.1・出力5）で
  近似し、過去の上限到達のばらつきが最も小さい指標を自動で選ぶ。
- 稼働中のエージェントは次の確認までに使用量が増えるので、止める閾値は90%より低く（既定85%）設定する。

使い方:
    python3 -I usage.py            # 枠ごとの使用量・推定容量・現在の使用率を表示
    python3 -I usage.py --check 85 # 85%以上なら exit 1（エージェントは作業を保存して停止する）
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone

PROJECT_LOGS = os.path.expanduser("~/.claude/projects/-home-user-intro-Git")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # note-business/
WINDOW = timedelta(hours=5)
LIMIT_RE = re.compile(r"hit your 5-hour limit · resets (\d{1,2})(?::(\d{2}))?(am|pm) \(UTC\)")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def floor10(t):
    return t.replace(minute=t.minute - t.minute % 10, second=0, microsecond=0)


def weights(u):
    """3つの指標を返す。raw: 入力+キャッシュ作成+出力 / light: raw+0.1×キャッシュ読込 / cost: 料金比率の近似"""
    inp = u.get("input_tokens", 0) or 0
    out = u.get("output_tokens", 0) or 0
    cc = u.get("cache_creation_input_tokens", 0) or 0
    cr = u.get("cache_read_input_tokens", 0) or 0
    cc1h = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
    cc5m = cc - cc1h
    return {
        "raw": inp + cc + out,
        "light": inp + cc + out + 0.1 * cr,
        "cost": inp + 1.25 * cc5m + 2.0 * cc1h + 0.1 * cr + 5.0 * out,
    }


def collect():
    events, seen, limits = [], set(), []
    for f in glob.glob(os.path.join(PROJECT_LOGS, "**", "*.jsonl"), recursive=True):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # 実際のエラー記録だけを数える（作業中の検索結果などに文字列が含まれても誤検出しない）
                if "hit your 5-hour limit" in line and "error type rate_limit" in line:
                    m = LIMIT_RE.search(line)
                    try:
                        ts = parse_ts(json.loads(line).get("timestamp"))
                    except Exception:
                        ts = None
                    if m and ts:
                        limits.append((ts, m.groups()))
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = o.get("message") if isinstance(o.get("message"), dict) else None
                if not msg or not msg.get("usage") or not o.get("timestamp"):
                    continue
                key = msg.get("id") or (o.get("requestId"), o.get("timestamp"))
                if key in seen:
                    continue
                seen.add(key)
                events.append((parse_ts(o["timestamp"]), weights(msg["usage"])))
    for f in glob.glob(os.path.join(REPO, "03_content", "verification", "**", "*.json"), recursive=True):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("usage"), dict) and "total_cost_usd" in d:
            ts = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
            events.append((ts, weights(d["usage"])))
    events.sort(key=lambda e: e[0])
    return events, limits


def build_windows(events):
    wins = []
    for ts, w in events:
        if not wins or ts >= wins[-1]["end"]:
            start = floor10(ts)
            wins.append({"start": start, "end": start + WINDOW, "events": []})
        wins[-1]["events"].append((ts, w))
    return wins


def reset_dt(hit_ts, groups):
    h, m, ap = int(groups[0]), int(groups[1] or 0), groups[2]
    h = (h % 12) + (12 if ap == "pm" else 0)
    r = hit_ts.replace(hour=h, minute=m, second=0, microsecond=0)
    return r if r > hit_ts else r + timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", type=float, help="現在の使用率がこの%以上なら exit 1")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    events, limits = collect()
    if not events:
        sys.exit("使用量の記録が見つかりません")
    wins = build_windows(events)
    # 上限到達：リセット時刻ごとに最初の到達時刻
    hits = {}
    for ts, g in limits:
        r = reset_dt(ts, g)
        if r not in hits or ts < hits[r]:
            hits[r] = ts
    samples = {"raw": [], "light": [], "cost": []}
    rows = []
    for w in wins:
        hit = next((t for r, t in hits.items() if w["start"] <= t < w["end"]), None)
        reset_known = next((r for r in hits if w["start"] <= hits[r] < w["end"]), None)
        upto = [e for e in w["events"] if hit is None or e[0] <= hit]
        tot = {k: sum(e[1][k] for e in upto) for k in samples}
        if hit:
            for k in samples:
                samples[k].append(tot[k])
        rows.append((w, hit, reset_known, tot))
    # 最も安定した指標（変動係数が最小）を選ぶ
    def cv(v):
        return statistics.pstdev(v) / statistics.mean(v) if len(v) >= 2 and statistics.mean(v) else 9
    metric = min(samples, key=lambda k: cv(samples[k])) if samples["cost"] else "cost"
    cap = statistics.median(samples[metric]) if samples[metric] else None
    now = datetime.now(timezone.utc)
    cur = wins[-1] if now < wins[-1]["end"] else None
    used = sum(e[1][metric] for e in cur["events"]) if cur else 0
    pct = (used / cap * 100) if (cap and cur) else 0.0

    if not a.quiet:
        print("## 5時間枠ごとの使用量（このプロジェクトのみ）")
        for w, hit, reset_known, tot in rows:
            flag = f"上限到達 {hit:%m/%d %H:%M}（リセット {reset_known:%H:%M} と枠の終わり {w['end']:%H:%M} の一致: {'OK' if reset_known == w['end'] else 'ずれ'}）" if hit else ""
            print(f"- {w['start']:%m/%d %H:%M}〜{w['end']:%H:%M}: {tot[metric]:,.0f}（{metric}） {flag}")
        print("\n## 容量の推定（上限に達した枠の、到達までの使用量）")
        for k, v in samples.items():
            if v:
                print(f"- {k}: 中央値 {statistics.median(v):,.0f} / 変動係数 {cv(v):.2f} / n={len(v)}" + ("  ← 採用" if k == metric else ""))
        print("\n## 現在の枠")
    if cur:
        left = cur["end"] - now
        print(f"{cur['start']:%m/%d %H:%M}〜{cur['end']:%H:%M} UTC: 使用率 {pct:.0f}%（{used:,.0f} / 推定容量 {cap:,.0f}、{metric}）。リセットまで約{int(left.total_seconds() // 60)}分")
    else:
        print("現在の枠での使用はまだありません（0%）")
    if a.check is not None and pct >= a.check:
        print(f"STOP: 使用率が{a.check:.0f}%以上です。作業を保存して停止し、枠のリセット（{cur['end']:%H:%M} UTC）後に再開してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()

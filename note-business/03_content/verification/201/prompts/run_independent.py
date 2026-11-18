#!/usr/bin/env python3
"""独立実行（修正計画R2）：<dir>/*.prompt.txt を claude -p で実行し、JSONと出力本文を保存する。

コマンド: claude -p --tools "" --no-session-persistence --output-format json（プロンプトは標準入力で渡す）
保存: <name>.runN.json（CLIの出力そのまま。session_id・トークン数を含む）、<name>.runN.txt（resultの本文）
使い方: python3 -I -B run_independent.py <dir> [--runs 2] [--only a,b] [--workers 8]
"""
import argparse, concurrent.futures as cf, datetime, json, pathlib, subprocess

def run_one(prompt, n):
    out = prompt.with_name(prompt.name.replace(".prompt.txt", f".run{n}.json"))
    if out.exists() and out.stat().st_size > 0:
        return prompt.name, n, "既存"
    with open(prompt, "rb") as f:
        p = subprocess.run(["claude", "-p", "--tools", "", "--no-session-persistence", "--output-format", "json"],
                           stdin=f, capture_output=True, timeout=900)
    out.write_bytes(p.stdout)
    try:
        d = json.loads(p.stdout)
    except Exception:
        return prompt.name, n, "JSONの読み取り失敗: " + p.stderr.decode("utf-8", "replace")[:200]
    out.with_suffix(".txt").write_text(d.get("result", ""), encoding="utf-8")
    return prompt.name, n, ("エラー" if d.get("is_error") else f"成功 session={d.get('session_id')}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--only", default=""); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    prompts = sorted(d.glob("*.prompt.txt"))
    if a.only:
        keep = set(a.only.split(","))
        prompts = [p for p in prompts if p.name.replace(".prompt.txt", "") in keep]
    jobs = [(p, n) for p in prompts for n in range(1, a.runs + 1)]
    log = d / "run-log.txt"
    with cf.ThreadPoolExecutor(a.workers) as ex, open(log, "a", encoding="utf-8") as lf:
        for name, n, status in ex.map(lambda j: run_one(*j), jobs):
            line = f"{datetime.datetime.now().isoformat(timespec='seconds')} {name} run{n} {status}"
            print(line, flush=True); lf.write(line + "\n")

if __name__ == "__main__":
    main()

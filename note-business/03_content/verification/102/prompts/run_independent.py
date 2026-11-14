#!/usr/bin/env python3
"""依頼文を、執筆の文脈と切り離して独立に実行する（content-guidelines §4・R2）。

コマンド: claude -p --tools "" --no-session-persistence --output-format json（依頼文は標準入力で渡す）
保存: <名前>.run<N>.json（CLIの出力そのまま）と <名前>.run<N>.md（result の本文と実行情報）
使い方: python3 -I -B run_independent.py --runs 1 2 [--force] <名前>.prompt.txt ...
"""
import concurrent.futures as cf
import datetime
import json
import os
import subprocess
import sys

CMD = ["claude", "-p", "--tools", "", "--no-session-persistence", "--output-format", "json"]


def run_one(prompt_path, n, force):
    base = prompt_path[: -len(".prompt.txt")]
    jpath, mpath = f"{base}.run{n}.json", f"{base}.run{n}.md"
    if os.path.exists(jpath) and not force:
        return f"skip {os.path.basename(jpath)}"
    text = open(prompt_path, encoding="utf-8").read()
    p = subprocess.run(CMD, input=text, capture_output=True, text=True, timeout=600)
    open(jpath, "w", encoding="utf-8").write(p.stdout)
    d = json.loads(p.stdout)
    model = ",".join(d.get("modelUsage", {}).keys())
    u = d.get("usage", {})
    head = (f"# {os.path.basename(base)} run{n}（独立実行）\n\n"
            f"- 実行日時：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"- コマンド：{' '.join(repr(c) if c == '' else c for c in CMD)}（依頼文は {os.path.basename(prompt_path)} を標準入力で渡した）\n"
            f"- モデル：{model}／session_id：{d.get('session_id')}／入力 {u.get('input_tokens', 0) + u.get('cache_creation_input_tokens', 0) + u.get('cache_read_input_tokens', 0)}・出力 {u.get('output_tokens')} トークン\n"
            f"- 結果：{d.get('subtype')}（is_error={d.get('is_error')}）\n\n---\n\n")
    open(mpath, "w", encoding="utf-8").write(head + (d.get("result") or "") + "\n")
    return f"ok   {os.path.basename(mpath)}  {d.get('subtype')}  out={u.get('output_tokens')}"


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    runs = [1]
    if "--runs" in args:
        i = args.index("--runs")
        j = i + 1
        while j < len(args) and args[j].isdigit():
            j += 1
        runs = [int(x) for x in args[i + 1:j]]
        args = args[:i] + args[j:]
    jobs = [(p, n) for p in args for n in runs]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda a: run_one(a[0], a[1], force), jobs):
            print(r, flush=True)


if __name__ == "__main__":
    main()

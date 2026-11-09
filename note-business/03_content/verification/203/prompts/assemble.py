#!/usr/bin/env python3
"""203 独立実行の出力（<名前>.run<N>.md）を、check_scenes.py が読む「=== 番号」形式にまとめる。
- 実行情報の見出し（最初の --- まで）を外す
- マークダウンの記号（``` と **）を外す。文面は変えない
- 文書の後ろの「---」以降（補足など）は文書から外し、別に記録する（前置きの「文書だけを出力する」の点検）
使い方: python3 -I -B assemble.py <接頭辞 例: scene または v1_scene> <run番号> <出力ファイル>
"""
import glob, os, re, sys
prefix, run, out = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
blocks, extras = [], []
for p in sorted(glob.glob(os.path.join(HERE, f"{prefix}[0-9][0-9].run{run}.md"))):
    no = int(re.search(r"(\d\d)\.run", p).group(1))
    t = open(p, encoding="utf-8").read().split("\n---\n", 1)[1]
    t = t.replace("```", "").replace("**", "").strip("\n")
    doc, sep, rest = t.partition("\n---\n")
    doc = doc.strip("\n").strip()
    rest = rest.strip()
    # 先頭が「---」で始まる区切り（見出しの下の線など）は文書の一部として扱う
    if doc.startswith("# ") and not doc.startswith("件名"):
        pass
    blocks.append(f"=== {no}\n{doc}\n")
    if rest:
        extras.append(f"- 場面{no}: 文書の後ろに説明あり（{len(re.sub(r'\\s', '', rest))}字）: {rest.splitlines()[0][:60]}")
head = (f"# 203 独立実行の出力（{prefix} run{run}）\n\n- assemble.py で作成。実行情報の見出しとマークダウンの記号（``` と **）を外した。文面は変えていない\n"
        f"- 文書の後ろの補足（--- 以降）は文書から外した。補足があった場面: {len(extras)}\n\n")
open(out, "w", encoding="utf-8").write(head + "\n".join(blocks))
print(f"wrote {out}（{len(blocks)}場面）")
for e in extras:
    print(e)

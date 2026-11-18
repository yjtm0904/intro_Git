#!/usr/bin/env python3
"""記事201に載せた依頼文・出力例・NG例が、検証ログ（scenes_part*.json、preface-v2.txt）と1字も違わないかを確かめる。"""
import json, re, pathlib
here = pathlib.Path(__file__).parent
art = (here.parents[1] / "articles" / "201-office-ai-request-templates.md").read_text(encoding="utf-8")
blocks = re.findall(r"```\n(.*?)\n```", art, flags=re.S)
scenes = json.load(open(here / "scenes_part1.json", encoding="utf-8")) + json.load(open(here / "scenes_part2.json", encoding="utf-8"))
preface = (here / "preface-v2.txt").read_text(encoding="utf-8").strip()
ng_total = 0
for s in scenes:
    inp_ok = any(b == s["input"] or b == preface + "\n\n" + s["input"] for b in blocks)
    out_ok = s["output"] in blocks
    ng_lines = set(s["ng_output"].splitlines())
    # NG例：記事のブロックのうち、この場面のNG出力の行だけでできたもの（「（中略）」を除く）
    ng_ok = any(all((l in ng_lines) or l == "（中略）" for l in b.splitlines()) and len(set(b.splitlines()) & ng_lines) >= 1 for b in blocks)
    ng_total += ng_ok
    print(f"場面{s['no']:>2}: 依頼文 {'一致' if inp_ok else '不一致'}／出力例 {'一致' if out_ok else '不一致'}／NG例 {'ログの行だけ' if ng_ok else '要確認'}")
print("共通の前置き:", "一致" if preface in blocks or any(b.startswith(preface) for b in blocks) else "不一致")

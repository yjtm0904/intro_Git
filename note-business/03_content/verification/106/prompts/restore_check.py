#!/usr/bin/env python3
"""AIの出力に残った〔 〕の記号を、置換表で元に戻し、戻し残りを確かめる。"""
import csv, re, pathlib
here = pathlib.Path(__file__).parent
masked_in = (here.parent / "masked/v2/doc1-invoice-email.txt").read_text(encoding="utf-8")
out = (here / "p3-restore-ai-output.txt").read_text(encoding="utf-8")
table = list(csv.DictReader(open(here.parent / "replace-table-v2.csv", encoding="utf-8")))
# 記号 → 戻す語（表の最初の行を正式な表記として使う）
back = {}
for r in table:
    back.setdefault(r["置き換え後"], r["元の語"])
sym_in = re.findall(r"〔[^〕]+〕", masked_in)
sym_out = re.findall(r"〔[^〕]+〕", out)
print(f"入力の記号: {len(sym_in)}個 {sorted(set(sym_in))}")
print(f"出力の記号: {len(sym_out)}個 {sorted(set(sym_out))}")
print("入力にあった記号の種類が出力にもすべて残ったか:", set(sym_in) <= set(sym_out))
print("出力に新しく現れた記号:", sorted(set(sym_out) - set(sym_in)) or "なし")
restored = out
for sym, word in sorted(back.items(), key=lambda kv: -len(kv[0])):
    restored = restored.replace(sym, word)
(here / "p3-restored.txt").write_text(restored, encoding="utf-8")
left = re.findall(r"〔[^〕]+〕", restored)
xs = re.findall(r"[X]{1,3}(?:[,\-][X]{3,4})+円?|〒X{3}-X{4}", restored)
print(f"置換表で戻したあとに残った記号: {left or 'なし'}（置換表にない記号は人が元の書類から入れる）")
print(f"Xで伏せた数字（置換表では戻らない）: {xs}")
# 名字だけだった箇所が、正式な表記（フルネーム）に戻っていないか
orig = (here.parent / "docs/doc1-invoice-email.txt").read_text(encoding="utf-8")
for name in ["山田　太郎", "佐藤　花子"]:
    print(f"「{name}」の出現: 元の文書 {orig.count(name)}回 → 戻した文書 {restored.count(name)}回")

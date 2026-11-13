#!/usr/bin/env python3
"""203 原稿のうち、場面の節・30場面の全リスト・送る時期の一覧を、検証済みのファイルから組み立てる。

入力: scenes.md（送る時期・プロンプト・確認点）、prompts/outputs_independent.md（独立実行の出力＝完成例）、prompts/preamble.txt（共通の前置き）
出力: 原稿のテンプレートの {{...}} を置き換えた本文（標準出力、または --write <テンプレート> <原稿>）
完成例を手で写さないことで、原稿と検証ログの食い違いを防ぐ。
"""
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_scenes import load_blocks, load_scenes  # noqa: E402

FREE = {1, 26}
MONTHS = ["12月", "1月", "2月", "3月", "4月"]
EXAMPLE_RE = re.compile(r"例：(\d{1,2})月(\d{1,2})日（([月火水木金土日])）")


def preamble():
    # 記事に載せる前置き（第1ラウンドの修正後。独立実行で使ったもの）
    return open(os.path.join(HERE, "prompts", "preamble.txt"), encoding="utf-8").read().strip("\n")


# 文体の編集（2026-11-13、style-guide S15）：完成例のうち、重なった敬語だけを直す。
# 出力そのものは prompts/outputs_independent.md に残し、直した箇所はここと style/ の記録に置く
S15_EDITS = {
    3: [("にございますので、分別の際にご参照いただければ幸いです。", "にありますので、分別の際にご参照ください。")],
    6: [("切っていただけますと幸いです。", "切ってください。"),
        ("鍵を閉めていただけますでしょうか。", "鍵を閉めてください。"),
        ("トレイに入れていただけますようお願いいたします。", "トレイに入れてください。")],
    10: [("別のメールにてお願いさせていただきます。", "別のメールにてお願いいたします。")],
    25: [("各部署で次の準備をお願いできますでしょうか。", "各部署で次の準備をお願いいたします。")],
}


def outputs(edited=True):
    # 完成例は、執筆と別の独立実行の出力（prompts/assemble.py でまとめたもの）。edited=True で S15_EDITS を当てる
    outs = load_blocks(os.path.join(HERE, "prompts", "outputs_independent.md"))
    if edited:
        for no, pairs in S15_EDITS.items():
            for old, new in pairs:
                if outs[no].count(old) != 1:
                    raise SystemExit(f"S15_EDITS: 場面{no}に「{old}」が1か所だけない")
                outs[no] = outs[no].replace(old, new)
    return outs


def example_date(timing):
    m = EXAMPLE_RE.search(timing)
    mo, d = int(m.group(1)), int(m.group(2))
    return datetime.date(2026 if mo >= 11 else 2027, mo, d), f"{mo}月{d}日（{m.group(3)}）"


def scene_list(scenes):
    # 月ごとに見出しの行を置き、場面は1行に1つ（2026-11-13：1行に並べると80字を超えるため）
    blocks = []
    for month in MONTHS:
        items = [f"- {no}{'★' if no in FREE else ''} {s['名前']}" for no, s in sorted(scenes.items()) if s["月"] == month]
        blocks.append(f"{month}の{len(items)}場面\n" + "\n".join(items))
    return "\n\n".join(blocks)


def schedule(scenes, months=None):
    rows = {}
    for no, s in scenes.items():
        if months and s["月"] not in months:
            continue
        d, label = example_date(s["時期"])
        rows.setdefault((d, label), []).append(f"場面{no}{'★' if no in FREE else ''} {s['名前']}")
    out = []
    for (d, label), items in sorted(rows.items()):
        out.append(f"- {label}：" + "／".join(items))
    return "\n".join(out)


def scene_block(no, s, out, with_preamble=False):
    prompt = (preamble() + "\n\n" + s["prompt"]) if with_preamble else s["prompt"]
    return "\n".join([
        f"送る時期：{s['時期']}",
        "",
        "プロンプト" + ("（共通の前置き＋場面の依頼文）" if with_preamble else ""),
        "",
        "```",
        prompt,
        "```",
        "",
        "完成例",
        "",
        "```",
        out,
        "```",
        "",
        f"確認点：{s['確認点']}",
    ])


def paid_sections(scenes, outs):
    parts = []
    for month in MONTHS:
        nos = [no for no, s in sorted(scenes.items()) if s["月"] == month]
        parts.append(f"## {month}の文書{len(nos)}場面\n")
        for no in nos:
            s = scenes[no]
            parts.append(f"### 場面{no} {s['名前']}\n")
            if no in FREE:
                parts.append(f"プロンプトと完成例は、無料部分のサンプルに全文を載せています。\n\n送る時期：{s['時期']}\n\n確認点：{s['確認点']}\n")
            else:
                parts.append(scene_block(no, s, outs[no]) + "\n")
    return "\n".join(parts).rstrip("\n")


def fill(template):
    scenes, outs = load_scenes(), outputs()
    repl = {
        "{{SCENE_LIST}}": scene_list(scenes),
        "{{PREAMBLE}}": preamble(),
        "{{FREE_SAMPLE_1}}": scene_block(1, scenes[1], outs[1], with_preamble=True),
        "{{FREE_SAMPLE_26}}": scene_block(26, scenes[26], outs[26], with_preamble=False),
        "{{PAID_SCENES}}": paid_sections(scenes, outs),
        "{{SCHEDULE_ALL}}": schedule(scenes),
    }
    # 送る時期の一覧の見本（12月分）＝12月中に送るもの（1月の文書でも12月に送るものを含む）
    dec = {no: s for no, s in scenes.items() if example_date(s["時期"])[0].month == 12}
    repl["{{SCHEDULE_DEC}}"] = schedule(dec)
    for k, v in repl.items():
        template = template.replace(k, v)
    left = re.findall(r"\{\{[A-Z_0-9]+\}\}", template)
    if left:
        raise SystemExit(f"置き換え残り: {left}")
    return template


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--write":
        text = fill(open(sys.argv[2], encoding="utf-8").read())
        open(sys.argv[3], "w", encoding="utf-8").write(text)
        print(f"wrote {sys.argv[3]}")
    else:
        scenes = load_scenes()
        print(scene_list(scenes))
        print()
        print(schedule(scenes))

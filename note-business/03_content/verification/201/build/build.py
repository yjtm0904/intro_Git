#!/usr/bin/env python3
"""201の原稿を、検証ログ（scenes_part*.json、preface-v2.txt、customize-run.md）から組み立てる。
NG例の抜粋は、実際の出力に含まれる行だけを使う（含まれない行があれば止める）。"""
import json, pathlib, sys
V = pathlib.Path("/home/user/intro_Git/note-business/03_content/verification/201")
OUT = pathlib.Path("/home/user/intro_Git/note-business/03_content/articles/201-office-ai-request-templates.md")
HERE = pathlib.Path(__file__).parent
scenes = json.load(open(V / "scenes_part1.json", encoding="utf-8")) + json.load(open(V / "scenes_part2.json", encoding="utf-8"))
S = {s["no"]: s for s in scenes}
preface = (V / "preface-v2.txt").read_text(encoding="utf-8").strip()
cust = (V / "customize-run.md").read_text(encoding="utf-8")

def block(t):
    return "```\n" + t.strip("\n") + "\n```"

NG_LABEL = {
    9: "「このメモを議事録にして」と、メモだけを貼った",
    19: "「この文をやわらかくして」と、元の文だけを貼って頼んだ",
    20: "「このメールを要約して、返信を書いて」と、届いたメールだけを貼った",
}
NG_EXCERPT = {
    1: ["さて、先日お打ち合わせの際にお話しいただいた資料につきまして、ご送付をお願いしたくご連絡いたしました。", "お手数をおかけしますが、〇月〇日までにお送りいただけますと幸いです。"],
    2: ["・〇月24日（〇）13:00〜17:00", "上記以外でも調整いたしますので、お気軽にお申し付けください。", "場所は弊社会議室、またはオンラインでも対応可能です。"],
    4: ["〇〇の事情により、当初〇月〇日にお届け予定でございましたが、〇月〇日のお届けとなる見込みです。", "ご迷惑をおかけしましたことを重ねてお詫び申し上げますとともに、今後はこのようなことのないよう、社内の管理体制を見直し、再発防止に努めてまいります。"],
    5: ["大変申し訳ございません。深くお詫び申し上げます。", "今後はこのようなことのないよう、送信前の確認を徹底してまいります。"],
    6: ["社内で慎重に検討いたしました結果、誠に恐縮ながら、今回は他社様のサービスを採用させていただくことになりました。"],
    7: ["〇〇様から貴重なお話を伺うことができ、大変参考になりました。", "本日いただいたご意見をもとに、社内で検討を進めてまいります。"],
    8: ["〇〇部　各位", "1．提出書類：〇〇", "2．提出期限：〇月〇日（〇）", "ご多忙のところ大変恐縮ではございますが、期限厳守にてご提出くださいますよう、よろしくお願い申し上げます。"],
    9: ["・年末の大掃除を12月25日（金）午後に実施する。詳細は別途連絡する", "・来客用の駐車場について、次回継続審議とする"],
    10: ["関係者各位", "それぞれ、期限までにご対応をお願いします。", "進捗があれば、共有いただけると助かります。"],
    11: ["日時：〇月〇日（〇）〇時〇分", "折り返し：お願いします（至急）"],
    12: ["・請求書の発行（32件）を、期日どおりに滞りなく完了しました。", "・年末調整の書類の回収を進めました（回収状況：〇割）。", "今週は請求業務と年末調整が重なりましたが、計画的に進めることができました。", "・引き続き、請求関連業務の対応"],
    14: ["・請求書発行件数：128件（前月比 +7件、約5.8%増）", "・入金確認件数：120件（未入金：8件）", "請求書の発行件数は前月から増加しましたが、遅延なく対応できました。", "未入金の8件については、引き続き確認を進めてまいります。"],
    15: None,  # 4行なので全文
    16: ["〇月〇日より、5,000円以上の備品を購入する際は、事前に申請が必要となります。", "申請のない購入については、経費精算の対象外となりますのでご注意ください。", "申請方法については、別途ご案内いたします。"],
    17: ["■住所：〒〇〇〇-〇〇〇〇 〇〇県〇〇市〇〇", "当日は、1階受付にてお名前をお伝えください。", "お車でお越しの際は、近隣のコインパーキングをご利用ください。"],
    18: ["1. 会計ソフトから当月の売上データを出力する", "5. PDFにしてメールで送付する（送付後、送付記録を台帳に記入）", "・締め日は毎月末日です"],
    19: None,  # 3行と短いので全文
    20: ["数量を150個に変更されたお見積りを、改めてお送りいたします。", "納期につきましては、150個の場合でも12月18日（金）に間に合うよう手配いたします。"],
}
# 問題点の書き方（地の文に「必ず」などを出さないよう、場面19だけ言い換える）
PROBLEM_OVERRIDE = {
    19: ["意味が変わった：必須のお願い（原本を出す）が「できれば原本」「お手すきの際に」になり、任意に読める", "消えた：「コピーでは精算できない」「まだ3人が出していない」"],
}

def excerpt(no):
    ng = S[no]["ng_output"]
    lines = NG_EXCERPT[no]
    if lines is None:
        return ng
    src = ng.splitlines()
    idx = []
    for l in lines:
        if l not in src:
            sys.exit(f"場面{no}のNG抜粋が出力にない: {l}")
        idx.append(src.index(l))
    out = [lines[0]]
    for prev, cur, l in zip(idx, idx[1:], lines[1:]):
        # 元の出力で、あいだに空行以外の行があるときだけ（中略）を入れる
        between = [x for x in src[prev + 1:cur] if x.strip()]
        out.append(("（中略）\n" if between else "") + l)
    return "\n".join(out)

def ng_label(no):
    return NG_LABEL.get(no, "「" + S[no]["ng_prompt"] + "」とだけ頼んだ")

def problems(no):
    return PROBLEM_OVERRIDE.get(no, S[no]["ng_problems"])

def scene_section(no):
    s = S[no]
    if s.get("free"):
        return f"### 場面{no} {s['name']}\n\nこの記事の前半（無料サンプル）に、依頼文・出力例・NG例の全文を載せています。"
    parts = [f"### 場面{no} {s['name']}", "",
             "依頼文（入力例を入れた状態）", "", block(s["input"]), "",
             "出力例", "", block(s["output"]), "",
             f"NG例：前置きなしで{ng_label(no)}出力（{'全文' if NG_EXCERPT[no] is None else '抜粋'}）", "", block(excerpt(no)), ""]
    parts += ["問題点", ""] + [f"- {p}" for p in problems(no)]
    parts += ["", "送る前の確認点", ""] + [f"- {c}" for c in s["checks"]]
    return "\n".join(parts)

def free_sample(no, with_preface):
    s = S[no]
    intro = ("依頼文です。共通の前置き（有料部分にも全文あり）を先頭に入れているので、このままコピーして試せます。【 】の右側を書き換えて使います。"
             if with_preface else "依頼文です。場面3と同じ共通の前置きを先に貼り、そのあとに次の部分を貼ります。")
    txt = (preface + "\n\n" + s["input"]) if with_preface else s["input"]
    parts = [f"## 無料サンプル：★場面{no} {s['name']}", "", intro, "", block(txt), "",
             "出力例です。", "", block(s["output"]), "",
             "出力例はClaudeで生成。AIの出力は毎回少しずつ変わります。", "",
             f"NG例：前置きなしで{ng_label(no)}出力（全文）です。", "", block(s["ng_output"]), ""]
    parts += ["問題点", ""] + [f"- {p}" for p in problems(no)]
    parts += ["", "送る前の確認点", ""] + [f"- {c}" for c in s["checks"]]
    return "\n".join(parts)

# 改造の例（customize-run.md から、職場のことと直った依頼文の【形式】を抜き出す）
cust_prompt = cust.split("## 1.")[1].split("```")[1]
workplace = cust_prompt.split("【職場のこと】")[1].split("【直し方】")[0].strip("\n")
fixed = cust.split("## 2.")[1].split("```")[1].strip("\n")
fixed_form = [l for l in fixed.splitlines() if l.startswith("【形式】")][0]
fixed_scene = [l for l in fixed.splitlines() if l.startswith("【場面】")][0]
cust_full = cust_prompt.split("【職場のこと】")[0] + "【職場のこと】\n・業種と人数：\n・よく送る相手：\n・文の決まり：（例：社内の連絡はチャット。件名の付け方）\n・いつも入れる一文：\n・入れてはいけない情報：（例：社員名は〔社員C〕のような記号にする）\n【直し方】" + cust_prompt.split("【直し方】")[1].split("【直す依頼文】")[0] + "【直す依頼文】\n（20場面のどれかを貼る）"
for l in ["・【 】の見出しは残す。職場で毎回書く情報があれば、見出しを足してよい", "・共通の前置きのルール（情報を足さない、〔要確認〕と書く、〔 〕の記号を残す）に反する指示は入れない", "・直した依頼文だけを出し、そのあとに変えた点を3つまで書く"]:
    assert l in cust_full, l
cust_out_msg = cust.split("出力：")[1].split("```")[1].strip("\n")

free_text = (HERE / "free_part.md").read_text(encoding="utf-8").rstrip("\n")
rest_free = (HERE / "free_rest.md").read_text(encoding="utf-8").rstrip("\n")
paid_tail = (HERE / "paid_tail.md").read_text(encoding="utf-8").rstrip("\n")
paid_head = (HERE / "paid_head.md").read_text(encoding="utf-8").rstrip("\n")

rest_free = rest_free.replace("{{WORKPLACE}}", block(workplace)).replace("{{FIXED_EXCERPT}}", block(fixed_scene + "\n（中略）\n" + fixed_form)).replace("{{CUST_MSG}}", block(cust_out_msg))
paid_head = paid_head.replace("{{PREFACE}}", block(preface))
paid_tail = paid_tail.replace("{{CUST_FULL}}", block(cust_full))

groups = [("メールの8場面", range(1, 9)), ("議事録・記録の3場面", range(9, 12)), ("報告の4場面", range(12, 16)),
          ("社内連絡の3場面", range(16, 19)), ("文章の手直しの2場面", range(19, 21))]
paid_scenes = []
for title, nos in groups:
    paid_scenes.append(f"## {title}")
    for no in nos:
        paid_scenes.append(scene_section(no))
doc = "\n\n".join([free_text, free_sample(3, True), free_sample(13, False), rest_free,
                   "**━━━━━━ ここから有料（noteの有料ラインをこの位置に設定）━━━━━━**",
                   paid_head] + paid_scenes + [paid_tail]) + "\n"
OUT.write_text(doc, encoding="utf-8")
print("書き出し:", OUT, len(doc), "字（空白込み）")

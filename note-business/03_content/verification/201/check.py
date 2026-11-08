#!/usr/bin/env python3
"""201 検証: 20場面の出力（共通の前置きv2）を機械で点検し、場面ごとの記録 scenes/scene-NN.md を書き出す。

点検すること
- 日付と曜日：「11月20日（金）」「12/3（木）」の曜日が2026年の暦と合うか
- 入力にない数字：出力の数字が、入力に出てくる数字だけか（箇条書きの番号は除く）
- 記号：入力の〔 〕が出力に残っているか／入力にない記号が増えていないか（〔自社〕〔氏名〕〔要確認：…〕〔計算：…〕は可）
- 字数：【形式】の「◯字以内」を本文が守っているか（件名・宛名・署名は除く）
- 言い換え・強い言い方・二重敬語・文面のあとの説明
"""
import json, re, datetime as dt, pathlib
here = pathlib.Path(__file__).parent
W = "月火水木金土日"
scenes = json.load(open(here / "scenes_part1.json", encoding="utf-8")) + json.load(open(here / "scenes_part2.json", encoding="utf-8"))
preface = (here / "preface-v2.txt").read_text(encoding="utf-8").strip()

DATE = re.compile(r"(?:(\d{4})年)?(\d{1,2})(?:月|/)(\d{1,2})日?（([月火水木金土日])）")
RELATIVE = r"本日|明日|昨日|明後日|今週|来週"
STRONG = r"至急|必ず|再三|期限厳守|法的|訴訟|遅延損害金|取引.{0,6}(停止|見直|中止)|然るべき|しかるべき|措置"
DOUBLE_KEIGO = r"おっしゃられ|お伺いさせていただ|拝見させていただ|ご覧になられ|お召し上がりになられ|させていただけますでしょうか"
ALLOWED_NEW = re.compile(r"〔(自社|氏名|要確認[^〕]*|計算[^〕]*)〕")

def numbers(s):
    s = re.sub(r"(?m)^\s*\d+[\.．]\s", "", s)          # 箇条書きの番号
    s = re.sub(r"〔[^〕]*〕", "", s)                    # 記号の中（〔社員1〕など）
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", s)}

def symbols(s):
    return set(re.findall(r"〔[^〕]+〕", s)) - {"〔 〕"}

def body_len(out, no):
    """件名・宛名・名乗りの記号行・署名を除いた本文の字数（場面10は1通ずつ、場面20は返信部分）"""
    def strip(block):
        lines = [l for l in block.splitlines() if l.strip()]
        lines = [l for l in lines if not l.startswith("件名：")]
        drop = re.compile(r"^(〔[^〕]+〕(様|さん)?|[^\s]+の皆さん|営業部の皆さん|社員の皆さん|〔自社〕〔氏名〕|総務　〔氏名〕|経理　〔氏名〕|〔[^〕]+〕さんへ　〔[^〕]+〕より)$")
        lines = [l for l in lines if not drop.match(l.strip())]
        return len(re.sub(r"\s", "", "".join(lines)))
    if no == 10:
        return [strip(b) for b in out.split("\n\n") if b.strip()]
    if no == 20:
        return [strip(out.split("件名：", 1)[1])]
    return [strip(out)]

results = []
for s in scenes:
    out, inp = s["output"], s["input"]
    r = {"no": s["no"], "name": s["name"]}
    bad = []
    for y, m, d, w in DATE.findall(out):
        real = W[dt.date(int(y or 2026), int(m), int(d)).weekday()]
        if real != w:
            bad.append(f"{m}/{d}（{w}→{real}）")
    r["dates"] = len(DATE.findall(out)); r["date_ng"] = bad
    r["extra_numbers"] = sorted(numbers(out) - numbers(inp), key=lambda x: int(x))
    r["lost_symbols"] = sorted(symbols(inp) - symbols(out))
    r["new_symbols"] = sorted(x for x in symbols(out) - symbols(inp) if not ALLOWED_NEW.fullmatch(x))
    r["relative"] = sorted(set(re.findall(RELATIVE, out)) - set(re.findall(RELATIVE, inp)))
    r["strong"] = sorted(set(m.group() for m in re.finditer(STRONG, out)) - set(m.group() for m in re.finditer(STRONG, inp)))
    r["double_keigo"] = sorted(set(re.findall(DOUBLE_KEIGO, out)))
    r["note"] = "※" in out
    r["len"] = body_len(out, s["no"]); r["limit"] = s["limit"]
    r["len_ng"] = bool(s["limit"]) and any(n > s["limit"] for n in r["len"])
    # NG例：〇の空欄の数と、出力にある日付の曜日
    r["ng_blanks"] = len(re.findall(r"〇+", s["ng_output"]))
    results.append(r)

lines = ["# 201 点検結果（共通の前置きv2 × 20場面）", "", f"実行日：2026-11-08／点検：check.py", ""]
total = {"date_ng": 0, "extra_numbers": 0, "lost_symbols": 0, "new_symbols": 0, "relative": 0, "strong": 0, "double_keigo": 0, "note": 0, "len_ng": 0}
for r in results:
    flags = []
    for k in total:
        v = r[k]
        if v:
            total[k] += 1
            flags.append(k)
    lens = "・".join(str(n) for n in r["len"])
    lines.append(f"- 場面{r['no']} {r['name']}：日付{r['dates']}か所（曜日の誤り{len(r['date_ng'])}）／本文{lens}字（上限{r['limit'] or 'なし'}）／入力にない数字{r['extra_numbers'] or 'なし'}／消えた記号{r['lost_symbols'] or 'なし'}／増えた記号{r['new_symbols'] or 'なし'}／言い換え{r['relative'] or 'なし'}／強い言い方{r['strong'] or 'なし'}／二重敬語{r['double_keigo'] or 'なし'}／説明の付記{'あり' if r['note'] else 'なし'}")
lines += ["", "## 合計（問題があった場面の数）"] + [f"- {k}: {v}" for k, v in total.items()]
lines += ["", "## NG例（前置きなしの短い頼み方）の空欄（〇）の数", ""] + [f"- 場面{r['no']}：{r['ng_blanks']}か所" for r in results]
(here / "check-result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

# 場面ごとの記録
for s, r in zip(scenes, results):
    md = [f"# 場面{s['no']} {s['name']}（{s['group']}）", "",
          "- 実行日：2026-11-08／モデル：Claude（claude-opus-5-5。ライターAが、入力だけを条件に回答を作成）",
          "- 入力：共通の前置きv2（`../preface-v2.txt`）のあとに、下の依頼文を貼った", "",
          "## 依頼文（入力例を入れた状態）", "", "```", s["input"], "```", "",
          "## 出力（共通の前置きv2）", "", "```", s["output"], "```", "",
          "## NG例：前置きなしの頼み方", "", "```", s["ng_prompt"], "```", "",
          "## NG例：出力", "", "```", s["ng_output"], "```", "",
          "## 点検", "",
          f"- 機械（check.py）：曜日の誤り{len(r['date_ng'])}件／入力にない数字{r['extra_numbers'] or 'なし'}／消えた記号{r['lost_symbols'] or 'なし'}／増えた記号{r['new_symbols'] or 'なし'}／本文{'・'.join(map(str, r['len']))}字（上限{s['limit'] or 'なし'}）"]
    md += [f"- NG例の問題：{p}" for p in s["ng_problems"]]
    md += [f"- 送る前の確認点：{c}" for c in s["checks"]]
    (here / "scenes" / f"scene-{s['no']:02d}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

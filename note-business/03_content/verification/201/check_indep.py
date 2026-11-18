#!/usr/bin/env python3
"""201 独立実行（claude -p）の20場面の出力を、check.py と同じ観点で点検する。結果は check_indep-result.md
入力は prompts/scene-NN.prompt.txt（共通の前置きv2＋依頼文）、出力は prompts/scene-NN.run1.txt"""
import re, datetime as dt, pathlib, json
here = pathlib.Path(__file__).parent
P = here / "prompts"
W = "月火水木金土日"
DATE = re.compile(r"(?:(\d{4})年)?(\d{1,2})(?:月|/)(\d{1,2})日?（([月火水木金土日])）")
RELATIVE = r"本日|明日|昨日|明後日|今週|来週"
STRONG = r"至急|必ず|再三|期限厳守|法的|訴訟|遅延損害金|取引.{0,6}(停止|見直|中止)|然るべき|しかるべき|措置"
DOUBLE = r"おっしゃられ|お伺いさせていただ|拝見させていただ|ご覧になられ|させていただけますでしょうか"
OK_NEW = re.compile(r"〔(自社|氏名|要確認[^〕]*|計算[^〕]*)〕")
limits = {s["no"]: s["limit"] for s in json.load(open(here/"scenes_part1.json", encoding="utf-8")) + json.load(open(here/"scenes_part2.json", encoding="utf-8"))}
def numbers(s):
    s = re.sub(r"(?m)^\s*\d+[\.．]\s", "", s); s = re.sub(r"〔[^〕]*〕", "", s)
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", s)}
def syms(s): return set(re.findall(r"〔[^〕]+〕", s)) - {"〔 〕"}
lines = ["# 201 独立実行の点検（共通の前置きv2 × 20場面、claude -p 各1回）", ""]
tot = {k: 0 for k in ["曜日", "数字", "消えた記号", "増えた記号", "言い換え", "強い", "二重敬語", "説明", "字数"]}
for no in range(1, 21):
    prompt = (P / f"scene-{no:02d}.prompt.txt").read_text(encoding="utf-8")
    inp = prompt.split("\n\n", 1)[1]           # 前置きを除いた依頼文
    t = (P / f"scene-{no:02d}.run1.txt").read_text(encoding="utf-8").strip()
    # 前置き・後書きの検出：コードブロックの外に文がある／「---」のあとに説明がある
    note = bool(re.search(r"\n---\n", t)) or t.startswith(("以下", "承知", "こちら"))
    body = re.sub(r"```\w*\n?", "", t)
    bad = [f"{m}/{d}（{w}）" for y, m, d, w in DATE.findall(body) if W[dt.date(int(y or 2026), int(m), int(d)).weekday()] != w]
    extra = sorted(numbers(body) - numbers(inp), key=lambda x: int(x))
    lost = sorted(syms(inp) - syms(body)); new = sorted(x for x in syms(body) - syms(inp) if not OK_NEW.fullmatch(x))
    rel = sorted(set(re.findall(RELATIVE, body)) - set(re.findall(RELATIVE, inp)))
    strong = sorted({m.group() for m in re.finditer(STRONG, body)} - {m.group() for m in re.finditer(STRONG, inp)})
    dbl = sorted(set(re.findall(DOUBLE, body)))
    flags = {"曜日": bad, "数字": extra, "消えた記号": lost, "増えた記号": new, "言い換え": rel, "強い": strong, "二重敬語": dbl, "説明": note}
    for k, v in flags.items():
        if v: tot[k] += 1
    lines.append(f"- 場面{no}：曜日の誤り{bad or 'なし'}／入力にない数字{extra or 'なし'}／消えた記号{lost or 'なし'}／増えた記号{new or 'なし'}／言い換え{rel or 'なし'}／強い言い方{strong or 'なし'}／二重敬語{dbl or 'なし'}／前後の説明{'あり' if note else 'なし'}（字数の上限{limits[no] or 'なし'}）")
lines += ["", "## 問題があった場面の数"] + [f"- {k}: {v}" for k, v in tot.items()]
(here / "check_indep-result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

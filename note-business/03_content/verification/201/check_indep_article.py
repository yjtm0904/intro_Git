#!/usr/bin/env python3
"""201 記事に載せる出力例（独立実行 claude -p）を、check.py と同じ観点で点検する。結果は check_indep_article-result.md

対象（記事に載せるもの）
- 場面1〜18・20：prompts/scene-NN.run1.txt（場面20は、AIの作業メモのあとの最後の文面「**要約**」以降）
- 場面19：prompts/scene-19c.run1.txt（【形式】を直した版。scene-19・scene-19b は記録として残す）
- 改造の例：prompts/custom-08.run1.txt（customize.run1.txt の直った依頼文に、場面8の値を入れたもの）
入力は、それぞれの .prompt.txt から共通の前置きを除いた部分。"""
import re, datetime as dt, pathlib, json

here = pathlib.Path(__file__).parent
P = here / "prompts"
W = "月火水木金土日"
DATE = re.compile(r"(?:(\d{4})年)?(\d{1,2})(?:月|/)(\d{1,2})日?（([月火水木金土日])）")
RELATIVE = r"本日|明日|昨日|明後日|今週|来週"
STRONG = r"至急|必ず|再三|期限厳守|法的|訴訟|遅延損害金|取引.{0,6}(停止|見直|中止)|然るべき|しかるべき|措置"
DOUBLE = r"おっしゃられ|お伺いさせていただ|拝見させていただ|ご覧になられ|させていただけますでしょうか"
OK_NEW = re.compile(r"〔(自社|氏名|要確認[^〕]*|計算[^〕]*)〕")
limits = {s["no"]: s["limit"] for s in json.load(open(here / "scenes_part1.json", encoding="utf-8")) + json.load(open(here / "scenes_part2.json", encoding="utf-8"))}
limits["改造"] = 200


def source(no):
    if no == 19:
        return "scene-19c"
    if no == "改造":
        return "custom-08"
    return f"scene-{no:02d}"


def article_text(no):
    """記事に載せる文面（場面20は作業メモを除いた最後の文面）"""
    t = (P / f"{source(no)}.run1.txt").read_text(encoding="utf-8").strip()
    if no == 20:
        t = t[t.rindex("**要約**"):]
    return t


def numbers(s):
    s = re.sub(r"(?m)^\s*\d+[\.．]\s", "", s)   # 番号つきの行の番号
    s = re.sub(r"〔[^〕]*〕", "", s)
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", s)}


def syms(s):
    return set(re.findall(r"〔[^〕]+〕", s)) - {"〔 〕"}


DROP = re.compile(r"^(件名[：:].*|〔[^〕]+〕(様|さん)?|〔[^〕]+〕〔[^〕]+〕|[^\s、。]+の皆さん|全社員各位|総務　〔氏名〕|経理 〔氏名〕)$")


def body_len(text, no):
    """件名・宛名・署名の行と、書式の記号（**）を除いた本文の字数。場面10は1通ずつ、場面20は返信部分"""
    def strip(block):
        lines = [l.replace("**", "").strip() for l in block.splitlines() if l.strip()]
        lines = [l for l in lines if not DROP.match(l)]
        return len(re.sub(r"\s", "", "".join(lines)))
    if no == 10:
        return [strip(b) for b in text.split("\n\n") if b.strip()]
    if no == 20:
        return [strip(text.split("件名", 1)[1].split("\n", 1)[1])]
    if no == 19:
        return [strip(text.split("\n---")[0])]
    return [strip(text)]


def note_outside(text, no):
    """頼んでいない前置き・後書き（場面19の「変えた点」、場面20の要約と返信の区切りは頼んだもの）"""
    if no in (19, 20):
        return False
    return bool(re.search(r"(?m)^---$", text)) or text.startswith(("以下", "承知", "こちら"))


lines = ["# 201 記事に載せる出力例の点検（独立実行 claude -p、各1回）", "",
         "点検：check_indep_article.py（2026-11-13）。観点は check.py と同じ。本文の字数は、件名・宛名・署名の行と「**」を除いて数えた", ""]
tot = {k: 0 for k in ["曜日", "数字", "消えた記号", "増えた記号", "言い換え", "強い", "二重敬語", "説明", "字数"]}
for no in list(range(1, 21)) + ["改造"]:
    prompt = (P / f"{source(no)}.prompt.txt").read_text(encoding="utf-8")
    inp = prompt.split("\n\n", 1)[1]
    t = article_text(no)
    body = re.sub(r"```\w*\n?", "", t)
    bad = [f"{m}/{d}（{w}）" for y, m, d, w in DATE.findall(body) if W[dt.date(int(y or 2026), int(m), int(d)).weekday()] != w]
    extra = sorted(numbers(body) - numbers(inp), key=lambda x: int(x))
    lost = sorted(syms(inp) - syms(body))
    new = sorted(x for x in syms(body) - syms(inp) if not OK_NEW.fullmatch(x))
    rel = sorted(set(re.findall(RELATIVE, body)) - set(re.findall(RELATIVE, inp)))
    strong = sorted({m.group() for m in re.finditer(STRONG, body)} - {m.group() for m in re.finditer(STRONG, inp)})
    dbl = sorted(set(re.findall(DOUBLE, body)))
    note = note_outside(t, no)
    lens = body_len(t, no)
    over = bool(limits[no]) and any(n > limits[no] for n in lens)
    flags = {"曜日": bad, "数字": extra, "消えた記号": lost, "増えた記号": new, "言い換え": rel, "強い": strong, "二重敬語": dbl, "説明": note, "字数": over}
    for k, v in flags.items():
        if v:
            tot[k] += 1
    label = f"場面{no}" if no != "改造" else "改造の例（場面8）"
    lines.append(f"- {label}（{source(no)}）：日付{len(DATE.findall(body))}か所（曜日の誤り{len(bad)}）／本文{'・'.join(map(str, lens))}字（上限{limits[no] or 'なし'}）"
                 f"／入力にない数字{extra or 'なし'}／消えた記号{lost or 'なし'}／増えた記号{new or 'なし'}／言い換え{rel or 'なし'}"
                 f"／強い言い方{strong or 'なし'}／二重敬語{dbl or 'なし'}／頼んでいない前後の説明{'あり' if note else 'なし'}")
lines += ["", "## 問題があった場面の数（20場面＋改造の例）"] + [f"- {k}: {v}" for k, v in tot.items()]
lines += ["", "## 機械の点検に出ない点（目視）",
          "- 場面20：最後の文面の前に、AIの作業メモ（英語と日本語の下書き、字数の見積もり）が出た。記事には「**要約**」以降だけを載せ、その旨を本文に書いた。作業メモの中の数字（字数の見積もり）は点検の対象外",
          "- 場面19：scene-19（11/9）と scene-19b（11/13、「強調の言葉は足さずに」を追加）は、どちらも元の文にない強調の言葉（必ず）を足した。scene-19c（11/13、必要なことを理由で伝えるよう【形式】を直した版）では足されなかった",
          "- 場面12・18・20：見出しや要約に「**」（太字の記号）が付いた。チャット画面では太字として表示され、メールに貼ると記号が残ることがある（記事の確認点に書いた）",
          "- 改造の例：件名なし。1行目が「11月分の交通費精算の申請と領収書の提出を、12月3日（木）17時までにお願いします。」で、最初の1行に「何を・いつまでに」がある。最後に「分からない点は総務まで。」がある"]
(here / "check_indep_article-result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

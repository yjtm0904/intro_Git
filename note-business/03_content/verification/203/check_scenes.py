#!/usr/bin/env python3
"""203 完成例（Claudeの出力）を、場面ごとに点検する。

点検すること
1. 件名があるか。本文（件名を除く。空白・改行は数えない）が150〜250字か
2. 曜日つきの日付がカレンダーと合うか（11〜12月は2026年、1〜4月は2027年。年が書いてあればその年）
3. その場面の【条件】にない日付・数字が足されていないか／曜日のない日付がないか
4. 法律・税・社会保険・医療の決まりや義務を書いていないか、「必ず」などの強い言い方がないか
5. 【要確認】の有無、条件にない〔　〕の記号（参考）
6. 101・102の記事の文例と、30字以上同じ文が続いていないか（企画書：101・102と同じ文面を使わない。定型の言い回しは除くため30字）

使い方: python3 -I -B check_scenes.py outputs_v2.md [--summary]
"""
import datetime
import difflib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEEK = "月火水木金土日"
DATE_RE = re.compile(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日(?:[（(]([月火水木金土日])[）)])?")
ASSERT_RE = re.compile(
    r"法令|法律|法人税|安全衛生法|労働基準法|義務|所得税|税額|確定申告|住宅ローン|社会保険|雇用保険|年金|"
    r"休日出勤|勤怠|医師|感染症|発熱|度以上|保存期間|必ず|絶対|以降は飲食|即戦力|期待されて")


def load_blocks(path):
    text = open(path, encoding="utf-8").read()
    blocks = {}
    for m in re.finditer(r"^=== (\d+)\n(.*?)(?=^=== \d+\n|\Z)", text, flags=re.S | re.M):
        blocks[int(m.group(1))] = m.group(2).strip("\n")
    return blocks


def load_scenes():
    scenes = {}
    for no, block in load_blocks(os.path.join(HERE, "scenes.md")).items():
        head, prompt = block.split("--- プロンプト", 1)
        meta = dict(re.findall(r"^(月|名前|時期|確認点): (.*)$", head, flags=re.M))
        meta["prompt"] = prompt.strip()
        scenes[no] = meta
    return scenes


def year_of(month):
    return 2026 if month >= 11 else 2027


def dates_in(text):
    out = []
    for m in DATE_RE.finditer(text):
        y, mo, d, w = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        yy = int(y) if y else year_of(mo)
        out.append((m.group(0), yy, mo, d, w))
    return out


def reference_texts():
    refs = []  # (記事ID, 文例の全文)
    # 101・102の記事に載せている文例（第1ラウンドの修正後は、独立実行の出力）と比べる
    p102 = os.path.join(HERE, "..", "102", "prompts", "v2.run1.article.txt")
    p101 = os.path.join(HERE, "..", "101", "prompts", "create_v2.run1.article.txt")
    for p in (p102, p101):
        if os.path.exists(p):
            refs.append((p.split(os.sep)[-3], open(p, encoding="utf-8").read()))
    return refs


def longest_common(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sm.find_longest_match(0, len(a), 0, len(b))
    return a[m.a:m.a + m.size]


def check_one(no, out, scene, refs):
    issues, notes = [], []
    lines = out.splitlines()
    subj = next((l for l in lines if l.startswith("件名：")), None)
    body = "\n".join(lines[lines.index(subj) + 1:]) if subj else out
    n = len(re.sub(r"\s", "", body))
    if subj is None:
        issues.append("件名がない")
    if not (150 <= n <= 250):
        issues.append(f"本文の字数が150〜250字の範囲外（{n}字）")
    prompt = scene["prompt"]
    allowed = {(yy, mo, d) for _, yy, mo, d, _ in dates_in(prompt)}
    for s, yy, mo, d, w in dates_in(out):
        real = WEEK[datetime.date(yy, mo, d).weekday()]
        if w is None:
            issues.append(f"曜日のない日付「{s}」")
        elif w != real:
            issues.append(f"曜日の誤り「{s}」（正しくは{real}）")
        if (yy, mo, d) not in allowed:
            issues.append(f"条件にない日付「{s}」")
    no_dates = re.sub(r"^\s*\d+[.．）)]", "", DATE_RE.sub("", out), flags=re.M)  # 行頭の箇条書きの番号は数えない
    nums_in = set(re.findall(r"\d+(?:\.\d+)?", DATE_RE.sub("", prompt)))
    for x in sorted(set(re.findall(r"\d+(?:\.\d+)?", no_dates)) - nums_in):
        issues.append(f"条件にない数字「{x}」")
    for m in ASSERT_RE.finditer(out):
        s = max(0, m.start() - 12)
        issues.append(f"決まり・断定・誇張の語「{m.group(0)}」…{out[s:m.end() + 12]}…".replace("\n", " "))
    if "【要確認" in out:
        notes.append("【要確認】あり")
    extra_ph = sorted(set(re.findall(r"〔[^〕]+〕", out)) - set(re.findall(r"〔[^〕]+〕", prompt)))
    if extra_ph:
        notes.append("条件にない〔　〕: " + "、".join(extra_ph))
    # 日付そのもの（101と同じ休業期間の例など）と、宛名だけの行（〔取引先会社名〕〔ご担当者名〕様）は
    # 文面の重なりに数えない
    def strip_for_overlap(t):
        t = "\n".join(l for l in t.splitlines() if not re.fullmatch(r"(〔[^〕]+〕)+様?", l.strip()))
        return re.sub(r"\s", "", DATE_RE.sub("", t))
    flat = strip_for_overlap(out)
    for name, ref in refs:
        lc = longest_common(flat, strip_for_overlap(ref))
        # 「（内線100）までお問い合わせください。」のような定型の言い回し（20〜22字）は数えず、30字以上の一致を見る
        if len(lc) >= 30:
            issues.append(f"{name}の文例と30字以上一致「{lc}」")
    return n, issues, notes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scenes, refs = load_scenes(), reference_texts()
    for path in args:
        outs = load_blocks(path)
        print(f"\n==== {path}（{len(outs)}場面）")
        total, lengths, ndates = 0, [], 0
        for no in sorted(outs):
            n, issues, notes = check_one(no, outs[no], scenes[no], refs)
            lengths.append(n)
            ndates += len([1 for x in dates_in(outs[no]) if x[4]])
            total += len(issues)
            head = f"-- 場面{no} {scenes[no]['名前']}｜本文 {n}字"
            print(head + ("" if issues else "｜問題なし") + (f"｜参考: {' / '.join(notes)}" if notes else ""))
            for x in issues:
                print(f"   要確認: {x}")
        print(f"== 要確認の合計: {total}件／曜日つきの日付 {ndates}件／本文の字数 最小{min(lengths)}・最大{max(lengths)}・平均{sum(lengths)/len(lengths):.0f}")


if __name__ == "__main__":
    main()

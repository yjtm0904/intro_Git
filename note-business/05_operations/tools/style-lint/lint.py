#!/usr/bin/env python3
"""文体チェッカー（style-lint）：「AIっぽさ」を減らす編集の工程1（機械チェック）

根拠: 02_strategy/style-guide.md（文体ルールS1〜S15、§4 工程1、§5 採点基準）、
      01_research/ai-likeness-research.md §6.5（patterns.json の使い方と限界）

使い方:
    python3 -I -B lint.py [--free-only] <原稿.md> ...
    python3 -I -B lint.py --self-test
終了コード: warn が1件でもあれば1（info は人が目で確認する）。使い方の誤りは2。

点検の対象（compliance-lint と同じく、YAMLのメタ情報・コードブロックを除く。加えてHTMLコメントも除く）
- 末尾の定型文（本文の最後の区切り線「---」から後）は常に除く。
- --free-only: 有料ライン（「ここから有料」の行）の手前までを見る。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATTERNS_PATH = os.path.join(HERE, "patterns.json")

PAID_MARK = "ここから有料"
# 「定番の決まり文句」（style-guide §5 の点1の目安）に当たる warn。残りの warn（ラベル見出し・工程用語・
# 太字・絵文字・体験や数字の創作リスク）は、決まり文句ではなく型・内部用語・要確認として扱う。
STOCK_IDS = {
    "open-many-people", "open-this-article", "open-conclusion-from", "open-sonna-keiken",
    "close-ikaga", "close-saiwai", "close-cheer", "end-important", "end-ieru", "end-nodehanai",
    "hedge-shisa", "abstract-effect", "hype", "conj-kokode", "self-answer", "empathy",
}
# この id は patterns.json の正規表現の代わりに、下の文の長さの計測で判定する（S9：URLを数えない、
# かっこの中の句点で文を切らない）。why・suggest・severity は patterns.json のものを使う。
LONG_ID = "long-sentence"
LONG_LIMIT = 80
RUN_LIMIT = 4  # 同じ文末がこの数以上続いたら報告（S14：3文まで）

OPEN_BR = "（(「『【［"
CLOSE_BR = "）)」』】］"
PAIR = {"）": "（", ")": "(", "」": "「", "』": "『", "】": "【", "］": "［"}
TERMINATORS = "。！？"

MD_LINK = re.compile(r"\[([^\]]*)\]\([^)\s]*\)")
BARE_URL = re.compile(r"https?://[A-Za-z0-9\-._~:/?#@!$&'*+,;=%]+")
INLINE_CODE = re.compile(r"`[^`]*`")
WEEKDAY_PAREN = re.compile(r"[（(][月火水木金土日](?:曜日?)?(?:・?祝日?)?[）)]")
FUNC_PAREN = re.compile(r"(?<=[A-Za-z0-9_$.])\(")  # FILTER( などの関数の引数
FIGURE = re.compile(r"^\s*［(?:図解|画像)[：:].*］\s*$")
HEADING = re.compile(r"^#{1,6}\s")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
LABEL_HEADING = re.compile(r"^#{2,3}\s*(結論|まとめ)[：:]")
OTHER_LABEL_HEADING = re.compile(r"^#{2,3}\s*[^\s：:#]{1,8}[：:]")
ENDINGS = ("ませんでした", "ました", "ません", "ます", "でした", "でしょう", "です", "ください")


# ---------------------------------------------------------------- 行の分類

def classify(lines, free_only=False):
    """各行の種類と、点検の対象かどうかを返す。

    kinds: front / comment / fence / code / hr / paid / blank / heading / list / quote / figure / prose
    """
    kinds = []
    in_front = bool(lines) and lines[0].strip() == "---"
    in_code = False
    in_comment = False
    for no, line in enumerate(lines):
        s = line.strip()
        if in_front:
            kinds.append("front")
            if no > 0 and s == "---":
                in_front = False
            continue
        if in_comment:
            kinds.append("comment")
            if "-->" in line:
                in_comment = False
            continue
        if s.startswith("```"):
            in_code = not in_code
            kinds.append("fence")
            continue
        if in_code:
            kinds.append("code")
            continue
        if s.startswith("<!--"):
            kinds.append("comment")
            in_comment = "-->" not in s[4:]
            continue
        if s == "---":
            kinds.append("hr")
        elif PAID_MARK in line:
            kinds.append("paid")
        elif not s:
            kinds.append("blank")
        elif HEADING.match(line):
            kinds.append("heading")
        elif FIGURE.match(line):
            kinds.append("figure")
        elif LIST_ITEM.match(line):
            kinds.append("list")
        elif s.startswith(">"):
            kinds.append("quote")
        else:
            kinds.append("prose")
    hrs = [i for i, k in enumerate(kinds) if k == "hr"]
    boiler = hrs[-1] if hrs else None  # 末尾の定型文の始まり（最後の区切り線）
    paids = [i for i, k in enumerate(kinds) if k == "paid"]
    paid = paids[0] if paids else None
    stop = len(lines)
    if boiler is not None:
        stop = boiler
    if free_only and paid is not None:
        stop = min(stop, paid)
    return kinds, stop, boiler, paid


def strip_urls(line):
    """リンクは表示される文字だけを残し、URLを消す（読者に見えない・S9で数えない）。"""
    return BARE_URL.sub("", MD_LINK.sub(r"\1", line))


def to_plain(line, kind):
    """計測用の、読者に見える文字だけの形にする（見出し・箇条書きの記号、太字の記号、URLを消す）。"""
    t = strip_urls(line)
    if kind == "heading":
        t = HEADING.sub("", t)
    elif kind == "list":
        t = LIST_ITEM.sub("", t)
    elif kind == "quote":
        t = re.sub(r"^\s*>\s?", "", t)
    t = t.replace("**", "").replace("__", "")
    return t.strip()


# ---------------------------------------------------------------- 文の分割と文末

def split_sentences(text):
    """句点・！・？で文に分ける。かっこ（（）「」『』【】［］）の中の句点では切らない。
    返り値: [(文, 句点で終わったか)]。行の終わりの句点のない部分も1文として返す。"""
    out, buf, depth = [], [], 0
    for ch in text:
        buf.append(ch)
        if ch in OPEN_BR:
            depth += 1
        elif ch in CLOSE_BR:
            depth = max(0, depth - 1)
        elif ch in TERMINATORS and depth == 0:
            out.append(("".join(buf).strip(), True))
            buf = []
    rest = "".join(buf).strip()
    if rest:
        out.append((rest, False))
    return out


def sentence_length(sentence):
    """文の長さ（句点と空白を除き、URLはすでに除いた文字数）。"""
    t = sentence.rstrip(TERMINATORS)
    return len(re.sub(r"\s", "", t))


def core_of(sentence):
    """文末の（…）【…】［…］の補足と句点を外した文を返す。"""
    t = sentence.strip().rstrip(TERMINATORS).rstrip()
    while t and t[-1] in "）)】］":
        close = t[-1]
        opener = PAIR[close]
        depth, i = 0, len(t) - 1
        while i >= 0:
            if t[i] == close:
                depth += 1
            elif t[i] == opener:
                depth -= 1
                if depth == 0:
                    break
            i -= 1
        if i <= 0:
            break
        t = t[:i].rstrip()
    return t


def ending_of(sentence):
    """文末の形（ます・です・ました…）を返す。文末の（…）【…】の補足は外して判定する。"""
    t = core_of(sentence)
    for e in ENDINGS:
        if t.endswith(e):
            return e
    if t.endswith("か"):
        return "か"
    return "その他「" + t[-1:] + "」"


# ---------------------------------------------------------------- 点検

def load_patterns(path=PATTERNS_PATH):
    pats = json.load(open(path, encoding="utf-8"))
    for p in pats:
        p["re"] = re.compile(p["regex"])
    return pats


def analyze(text, patterns, free_only=False):
    lines = text.split("\n")
    kinds, stop, boiler, paid = classify(lines, free_only)
    long_pat = next((p for p in patterns if p["id"] == LONG_ID), None)
    hits = []          # (行番号, severity, id, 行, 補足)
    chars = 0
    parens = {"count": 0, "weekday": 0, "func": 0, "lines": []}
    heading_parens = []
    longs = []         # (行番号, 字数, 文)
    runs = []          # (開始行, 終了行, 文末, [文末の抜粋])
    labels, other_labels = [], []
    cur = []           # 続いている同じ文末の文 [(行番号, 文末, 文)]

    def flush():
        if len(cur) >= RUN_LIMIT:
            runs.append((cur[0][0], cur[-1][0], cur[0][1], [s for _, _, s in cur]))
        cur.clear()

    body = [i for i in range(stop) if kinds[i] in ("heading", "list", "quote", "figure", "prose")]
    for i in range(stop):
        k = kinds[i]
        if k in ("heading", "list", "hr", "paid", "figure"):
            flush()  # 見出し・箇条書き・区切りで、同じ文末の数え直し（コードブロック・空行・コメントはまたぐ）
        if k not in ("heading", "list", "quote", "figure", "prose"):
            continue
        no, line = i + 1, lines[i]
        mtext = strip_urls(line)
        for p in patterns:
            if p["id"] == LONG_ID:
                continue
            if p["re"].search(mtext):
                hits.append((no, p["severity"], p["id"], line, ""))
        if k == "figure":
            continue  # ［図解：…］［画像：…］の印は公開時に画像になるので、字数・かっこ・文の計測に入れない
        plain = to_plain(line, k)
        chars += len(re.sub(r"\s", "", plain))
        # 丸かっこ（曜日・関数の引数・インラインコードを除く）
        ptext = INLINE_CODE.sub("", plain)
        wd = len(WEEKDAY_PAREN.findall(ptext))
        fn = len(FUNC_PAREN.findall(ptext))
        n = len(re.findall(r"[（(]", ptext)) - wd - fn
        parens["weekday"] += wd
        parens["func"] += fn
        if n > 0:
            parens["count"] += n
            parens["lines"].append((no, n))
            if k == "heading":
                heading_parens.append((no, n))
        if k == "heading":
            if LABEL_HEADING.match(line):
                labels.append(no)
            elif OTHER_LABEL_HEADING.match(line):
                other_labels.append(no)
            continue
        for sent, _terminated in split_sentences(plain):
            ln = sentence_length(sent)
            if ln > LONG_LIMIT:
                longs.append((no, ln, sent))
                if long_pat:
                    hits.append((no, long_pat["severity"], LONG_ID, line, f"{ln}字"))
            if k == "list":
                continue  # 箇条書きは並列が自然なので、同じ文末の数に入れない
            e = ending_of(sent)
            if cur and cur[-1][1] != e:
                flush()
            cur.append((no, e, sent))
    flush()
    hits.sort(key=lambda h: (h[0], h[1] != "warn", h[2]))
    density = round(parens["count"] * 1000 / chars, 1) if chars else 0.0
    warn_hits = [h for h in hits if h[1] == "warn"]
    score, reasons = estimate_score(warn_hits, density, len(longs))
    body_range = (body[0] + 1, body[-1] + 1) if body else None
    return {
        "lines": lines, "kinds": kinds, "stop": stop, "boiler": boiler, "paid": paid,
        "body_range": body_range, "hits": hits, "chars": chars, "parens": parens,
        "density": density, "heading_parens": heading_parens, "longs": longs, "runs": runs,
        "labels": labels, "other_labels": other_labels, "score": score, "reasons": reasons,
    }


def estimate_score(warn_hits, density, long_count):
    """style-guide §5 の「機械の目安」だけで点数を推定する（人の目安は別に確かめる）。"""
    stock = [h for h in warn_hits if h[2] in STOCK_IDS]
    warn = len(warn_hits)
    if len(stock) >= 2:
        return 1, [f"定番の決まり文句 {len(stock)}件 → 1"]
    cap_w = 5 if warn == 0 else (3 if warn <= 2 else 2)
    cap_p = 5 if density <= 4 else (4 if density <= 6 else (3 if density <= 9 else 2))
    cap_l = 5 if long_count == 0 else 4
    reasons = [f"warn {warn}件 → {cap_w}以下", f"丸かっこ {density}/1,000字 → {cap_p}以下",
               f"80字超の文 {long_count} → {cap_l}以下"]
    return min(cap_w, cap_p, cap_l), reasons


# ---------------------------------------------------------------- 表示

def snip(s, n=44):
    s = s.strip()
    return s if len(s) <= n else s[:n] + "…"


def report(path, r, patterns):
    by_id = {p["id"]: p for p in patterns}
    out = []
    lines, kinds = r["lines"], r["kinds"]
    excl = []
    nfront = kinds.count("front")
    if nfront:
        excl.append(f"メタ情報 L1〜{nfront}")
    nfence = kinds.count("fence") // 2
    if nfence:
        excl.append(f"コードブロック {nfence}か所")
    ncom = sum(1 for i, k in enumerate(kinds) if k == "comment" and (i == 0 or kinds[i - 1] != "comment"))
    if ncom:
        excl.append(f"HTMLコメント {ncom}か所")
    if r["paid"] is not None and r["stop"] <= r["paid"]:
        excl.append(f"有料ライン L{r['paid'] + 1} から後")
    elif r["paid"] is not None:
        excl.append(f"有料ラインの行 L{r['paid'] + 1}")
    if r["boiler"] is not None and r["stop"] == r["boiler"]:
        last = max(i for i, ln in enumerate(lines) if ln.strip()) + 1
        excl.append(f"末尾の定型文 L{r['boiler'] + 1}〜{last}")
    rng = f"L{r['body_range'][0]}〜{r['body_range'][1]}" if r["body_range"] else "なし"
    warns = [h for h in r["hits"] if h[1] == "warn"]
    infos = [h for h in r["hits"] if h[1] != "warn"]
    out.append(f"== {path}")
    out.append(f"   対象：{rng}（除外：{'、'.join(excl) if excl else 'なし'}）")
    out.append(f"-- 行ごとの検出：warn {len(warns)} / info {len(infos)}")
    for no, sev, pid, line, extra in r["hits"]:
        head = f"  L{no:<4} {sev:4} {pid}"
        out.append(f"{head}: {extra + ' ' if extra else ''}{snip(line)}")
        if sev == "warn":
            out.append(f"         → {by_id[pid]['suggest']}")

    def tally(hs):
        c = {}
        for h in hs:
            c[h[2]] = c.get(h[2], 0) + 1
        return "、".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0]))) or "なし"
    out.append(f"   warn の内訳：{tally(warns)}")
    out.append(f"   info の内訳：{tally(infos)}")
    p = r["parens"]
    out.append("-- 計測値")
    out.append(f"   本文の字数：{r['chars']:,}字（空白・見出しや箇条書きの記号・太字の記号・URLを除く）")
    out.append(f"   丸かっこ：{p['count']}個 ＝ {r['density']} / 1,000字"
               f"（除外：曜日 {p['weekday']}・関数の引数 {p['func']}。目安 S5：4以下）")
    hp = r["heading_parens"]
    out.append(f"   見出しの丸かっこ：{sum(n for _, n in hp)}"
               + (f"（{'、'.join(f'L{no}' for no, _ in hp)}）" if hp else "") + "（S10：2まで）")
    out.append(f"   80字超の文：{len(r['longs'])}（URLは数えない。S9）")
    for no, ln, s in r["longs"]:
        out.append(f"     L{no} {ln}字：{snip(s, 50)}")
    lb = r["labels"]
    out.append(f"   「結論：」「まとめ：」のラベル見出し：{len(lb)}"
               + (f"（{'、'.join(f'L{n}' for n in lb)}）" if lb else "") + "（S2：0）")
    if r["other_labels"]:
        out.append(f"     参考：ほかの「〇〇：」見出し {len(r['other_labels'])}"
                   f"（{'、'.join(f'L{n}' for n in r['other_labels'])}）")
    out.append(f"   同じ文末が{RUN_LIMIT}文以上続く箇所：{len(r['runs'])}（S14：3文まで）")
    for a, b, e, sents in r["runs"]:
        tails = "／".join("…" + core_of(s)[-8:] for s in sents)
        where = f"L{a}" if a == b else f"L{a}〜{b}"
        out.append(f"     {where}「{e}」{len(sents)}文：{tails}")
    out.append(f"-- 点数の推定（style-guide §5 の機械の目安だけ）：{r['score']}")
    out.append(f"   {'／'.join(r['reasons'])}")
    out.append("   人の目安（1文目が場面か、見出しは結論の文か、同じ注意は1回か、判断の足跡が前半にあるか、"
               "検証ログにない体験・数字がないか）は別に確かめる")
    return "\n".join(out)


# ---------------------------------------------------------------- 自己テスト

def self_test(patterns):
    ok = 0
    fails = []

    def check(name, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fails.append(name)

    def ids(text, free_only=False):
        return [h[2] for h in analyze(text, patterns, free_only)["hits"]]

    # 1. パターンの検出・非検出（patterns.json を読んでいること）
    check("ラベル見出しを拾う", "heading-label-conclusion" in ids("## 結論：回収は管理表で回す"))
    check("「まとめて送る」は見出しとして拾わない", "heading-matome" not in ids("まとめて送ると早く終わります。"))
    check("工程用語を拾う", "process-jargon" in ids("文例は、執筆とは別の新しい実行で動かした出力です。"))
    check("読者の言葉の書き方は工程用語にしない",
          "process-jargon" not in ids("記事を書いた会話とは別の新しい会話で2回試しました。"))
    check("決まり文句を拾う", "end-important" in ids("送る前に確認することが重要です。"))
    # 2. 除外（メタ情報・コードブロック・HTMLコメント・末尾の定型文・有料ライン）
    doc = "\n".join([
        "---", "title: \"## 結論：メタ情報\"", "---", "",
        "本文です。", "", "```", "することが重要です。", "```", "",
        "<!-- いかがでしたか", "複数行のコメント -->", "<!-- 1行のコメント：いかがでしたか -->", "",
        "**━━ ここから有料（noteの有料ラインをこの位置に設定）━━**", "",
        "有料部分です。送る前に確認することが重要です。", "",
        "---", "本記事は情報提供を目的としており、成果を保証するものではありません。",
    ])
    got = ids(doc)
    check("メタ情報を除く", "heading-label-conclusion" not in got)
    check("コードブロック・コメントを除き、有料部分は通常どおり見る", got == ["end-important"])
    check("--free-only で有料ラインから後を除く", ids(doc, free_only=True) == [])
    check("末尾の定型文を除く", "guarantee" not in got)
    # 3. 丸かっこ（曜日・関数の引数・リンクのURLを除く）
    r = analyze("期限は11月27日（金）です（社内の期限）。式は=COUNTIF(G2:G21,\"未提出\")です。"
                "[国税庁のページ](https://www.nta.go.jp/x)を見ます。", patterns)
    check("丸かっこは曜日・関数・URLを除いて1個", r["parens"]["count"] == 1 and r["parens"]["weekday"] == 1
          and r["parens"]["func"] == 1)
    # 4. 80字超の文（URLを数えない・かっこの中の句点で切らない）
    s70 = "あ" * 70 + "です"
    r = analyze(f"{s70}（[出典](https://example.com/{'x' * 60})）。", patterns)
    check("URLは文の長さに数えない", len(r["longs"]) == 0)
    r = analyze("い" * 85 + "。", patterns)
    check("85字の文を拾う", len(r["longs"]) == 1 and "long-sentence" in [h[2] for h in r["hits"]])
    r = analyze("う" * 50 + "です（" + "え" * 20 + "。" + "お" * 20 + "）。", patterns)
    check("かっこの中の句点で文を切らない", len(r["longs"]) == 1)
    # 5. 同じ文末の連続（コードブロック・空行はまたぎ、見出し・箇条書きで数え直す）
    four = "包みます。\n\n```\n=FILTER(A2:A21)\n```\n\nなります。使います。並びます（補足）。"
    r = analyze(four, patterns)
    check("「ます」4文を拾う（コードブロックをまたぐ）", len(r["runs"]) == 1 and r["runs"][0][2] == "ます")
    r = analyze("包みます。なります。\n\n## 見出し\n\n使います。並びます。", patterns)
    check("見出しをまたいだら数えない", r["runs"] == [])
    r = analyze("包みます。なります。使います。届きました。", patterns)
    check("3文までは拾わない", r["runs"] == [])
    # 6. 点数の推定（style-guide §5）
    check("点5", estimate_score([], 3.0, 0)[0] == 5)
    check("点4（丸かっこ6以下）", estimate_score([], 5.5, 0)[0] == 4)
    check("点4（80字超あり）", estimate_score([], 3.0, 1)[0] == 4)
    check("点3（warn 2）", estimate_score([(1, "warn", "process-jargon", "", "")] * 2, 3.0, 0)[0] == 3)
    check("点2（丸かっこ9超）", estimate_score([], 9.5, 0)[0] == 2)
    check("点1（決まり文句が複数）",
          estimate_score([(1, "warn", "close-ikaga", "", ""), (2, "warn", "end-important", "", "")], 3.0, 0)[0] == 1)
    print(f"self-test: {ok}/{ok + len(fails)} 件成功")
    for f in fails:
        print(f"  失敗: {f}")
    return not fails


def main():
    args = sys.argv[1:]
    try:
        patterns = load_patterns()
    except (OSError, ValueError) as e:
        print(f"patterns.json を読めません: {e}", file=sys.stderr)
        sys.exit(2)
    if "--self-test" in args:
        sys.exit(0 if self_test(patterns) else 1)
    free_only = "--free-only" in args
    paths = [a for a in args if a != "--free-only"]
    if not paths or any(p.startswith("--") for p in paths):
        print("usage: lint.py [--free-only] <原稿.md> ... | --self-test", file=sys.stderr)
        sys.exit(2)
    any_warn = False
    for i, p in enumerate(paths):
        r = analyze(open(p, encoding="utf-8").read(), patterns, free_only)
        if i:
            print()
        print(report(p, r, patterns))
        any_warn = any_warn or any(h[1] == "warn" for h in r["hits"])
    sys.exit(1 if any_warn else 0)


if __name__ == "__main__":
    main()

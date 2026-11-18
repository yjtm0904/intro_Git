#!/usr/bin/env python3
"""106 検証: 置換表で置き換えたあと、元の語・名字・略称・連絡先の形が残っていないかを検索する。

使い方: python3 -I -B mask_check.py <置換表.csv> [--patterns] [--edits manual-edits.csv] [--order long|short] [--out DIR]
- 置換表: 元の語,置き換え後,種類,使う文書（1行目は見出し）
- --patterns: 電話番号・メールアドレスなどを「形だけ残す」置き換えも行う（手順2）
- --edits: 人が読んで消す・言い換える文（文書,元の文,直した文）
- --drop-cols: 顧客リストから、作業に要らない列を消す（例: 住所,振込名義）
- --order: 置き換えの順番。long=長い語から（推奨）、short=短い語から（失敗例の再現用）
"""
import csv, re, sys, pathlib, argparse

HERE = pathlib.Path(__file__).parent
DOCS = ["doc1-invoice-email.txt", "doc2-customer-list.csv", "doc3-minutes-excerpt.txt"]

# 検索で確かめる語（置換表の元の語に加えて、名字・略称・半角カナ・社外秘の語）。
# 読者が「名字や会社名の一部で検索する」ことに当たる。
WATCH_WORDS = [
    # 会社名の中心部分（略称で書かれた場合も拾う）
    "サンプル商事", "見本物流", "テスト電機", "ダミー建設", "例示デザイン", "見本フーズ",
    "サンプル印刷", "架空化学", "テスト不動産", "ダミー商会", "テスト工業",
    # 名字（敬称なしで検索する）
    "山田", "田中", "高橋", "伊藤", "渡辺", "小林", "加藤", "吉田", "山本", "中村",
    "佐藤", "田村", "木下", "森",
    # 名前（下の名前。短い語を先に置き換えたときの残りを拾う。1字の名前は誤検出が多いので除く）
    "太郎", "一郎", "美咲", "由美", "花子", "直子", "拓也", "健太",
    # 社外秘・業務上の機密として人が判断する語
    "産休", "3,200万円", "社外未発表", "Kari2026!", "サンプル銀行", "見本支店",
]
PATTERNS = {
    "メールアドレス": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    "電話番号": r"0\d{1,4}-\d{1,4}-\d{3,4}",
    "郵便番号": r"〒\s?\d{3}-\d{4}|(?<![\d-])\d{3}-\d{4}(?![\d-])",
    "口座番号（普通・当座＋数字）": r"(?:普通|当座)[\s　]*\d{6,8}",
    "金額（円・桁区切り）": r"\d{1,3}(?:,\d{3})+万?円|\d+万円",
    "金額（CSVの5桁以上）": r"(?<=,)\d{5,}(?=,|$)",
    "URL": r"https?://[\w./?=&%:-]+",
    "半角カナ": r"[ｦ-ﾟ]{3,}",
    "住所（都道府県＋市区町村）": r"(?:東京都|北海道|大阪府|京都府|[^\s,、]{2,3}県)[^\s,、]{1,8}?[市区町村]",
}

def mask_patterns(text):
    """手順2: 数字は桁と形だけ残す。連絡先は記号にする。"""
    text = re.sub(PATTERNS["メールアドレス"], "〔メールアドレス〕", text)
    text = re.sub(PATTERNS["URL"], "〔社内URL〕", text)
    text = re.sub(PATTERNS["電話番号"], lambda m: re.sub(r"\d", "X", m.group()), text)
    text = re.sub(PATTERNS["郵便番号"], lambda m: re.sub(r"\d", "X", m.group()), text)
    text = re.sub(PATTERNS["金額（円・桁区切り）"], lambda m: re.sub(r"\d", "X", m.group()), text)
    text = re.sub(PATTERNS["金額（CSVの5桁以上）"], lambda m: "X" * len(m.group()), text, flags=re.M)
    text = re.sub(PATTERNS["口座番号（普通・当座＋数字）"], lambda m: re.sub(r"\d", "X", m.group()), text)
    return text

def load_table(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [(r["元の語"], r["置き換え後"]) for r in rows if r["元の語"]]

def apply_table(text, table, order):
    key = (lambda p: -len(p[0])) if order == "long" else (lambda p: len(p[0]))
    for src, dst in sorted(table, key=key):
        text = text.replace(src, dst)
    return text

def check(text):
    found = []
    for w in WATCH_WORDS:
        n = text.count(w)
        if n:
            found.append(("語", w, n))
    for name, pat in PATTERNS.items():
        hits = re.findall(pat, text, flags=re.M)
        if hits:
            found.append(("形:" + name, " / ".join(sorted(set(hits)))[:120], len(hits)))
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("--patterns", action="store_true")
    ap.add_argument("--edits")
    ap.add_argument("--order", default="long", choices=["long", "short"])
    ap.add_argument("--out")
    ap.add_argument("--drop-cols", default="")
    a = ap.parse_args()
    table = load_table(a.table)
    edits = []
    if a.edits:
        with open(a.edits, encoding="utf-8") as f:
            edits = [(r["文書"], r["元の文"], r["直した文"]) for r in csv.DictReader(f)]
    drop = [c for c in a.drop_cols.split(",") if c]
    print(f"置換表: {a.table}（{len(table)}語）／形の置き換え: {'あり' if a.patterns else 'なし'}／人の修正: {len(edits)}件／消した列: {drop or 'なし'}／順番: {a.order}")
    total = 0
    for name in DOCS:
        text = (HERE / "docs" / name).read_text(encoding="utf-8")
        if drop and name.endswith(".csv"):  # 手順0: 作業に要らない列を消す
            rows = list(csv.reader(text.splitlines()))
            keep = [i for i, h in enumerate(rows[0]) if h not in drop]
            text = "\n".join(",".join(r[i] for i in keep) for r in rows) + "\n"
        for doc, src, dst in edits:  # 人が読んで消す・言い換える（置換の前に行う）
            if doc != name:
                continue
            if src not in text:
                print(f"  注意: 修正対象の文が見つからない: {src[:30]}")
            text = text.replace(src, dst)
        text = apply_table(text, table, a.order)
        if a.patterns:
            text = mask_patterns(text)
        if a.out:
            out = HERE / a.out
            out.mkdir(exist_ok=True)
            (out / name).write_text(text, encoding="utf-8")
        found = check(text)
        n = sum(c for _, _, c in found)
        total += n
        print(f"\n[{name}] 残り {n}か所")
        for kind, what, c in found:
            print(f"  - {kind}「{what}」×{c}")
    print(f"\n合計: 残り {total}か所")

if __name__ == "__main__":
    main()

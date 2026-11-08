#!/usr/bin/env python3
"""原稿のコンプライアンス・書式チェッカー（公開前の機械チェック）

根拠: 01_research/platform-rules-legal.md §7（チェックリスト）・§8（機械チェック用NGワード）、
      05_operations/writing-format-spec.md（noteで再現できない書式の禁止）

使い方:
    python3 -I lint.py note-business/03_content/articles/*.md
終了コード: 要修正（ERROR）が1件でもあれば1。WARNは人が文脈を確認する。
"""
import re
import sys

# 見つかったら人が文脈を確認する語（§8）。カテゴリ: [(パターン, 許容する文脈の正規表現 or None)]
NG = {
    "収益系": [r"必ず", r"絶対", r"確実", r"誰でも", r"簡単に", r"放置で", r"不労所得", r"自動で稼", r"爆益",
             r"月収\d+万", r"元が取れ"],
    "保証系": [r"保証", r"100\s*%", r"完全", r"失敗しない", r"リスクなし"],
    "最上級系": [r"No\.?\s*1", r"ナンバーワン", r"日本一", r"業界初", r"最高", r"最強", r"唯一"],
    "限定系": [r"今だけ", r"本日限り", r"限定\d+名", r"残りわずか", r"二度と手に入らない"],
    "健康・投資系": [r"治る", r"痩せる", r"若返", r"免疫", r"買い時", r"必ず上がる", r"倍になる"],
    "誤認系": [r"公式", r"認定", r"社推奨", r"プロが全部書いた", r"全文書き下ろし"],
    "煽り系": [r"乗り遅れ", r"一生後悔", r"今すぐ", r"知らないと損"],
}
# 正当な用法として許容する文脈（その行にこれが含まれていれば、該当語の警告を出さない）
ALLOW = {
    r"保証": r"保証するものではありません|保証しません|保証はありません|動作を保証",
    r"公式": r"公式(ヘルプ|ドキュメント|サイト|ページ|ブログ|発表|情報|の(説明|ヘルプ|手順))|とは関係ありません|非公式",
    r"必ず": r"必ず(確認|バックアップ|テスト|保存|社内ルール|上長|人が|目視)",
    r"絶対": r"絶対参照",
    r"完全": r"完全一致",
}

PAID_LINE = "ここから有料"
AI_DISCLOSURE = re.compile(r"生成AI.{0,40}(検証|確認|編集)")
# 未記入・確認待ちの印（R3）。公開前チェック（--publish）ではERROR
PLACEHOLDER = re.compile(r"【(オーナー確認待ち|要記入|記入|実機確認後に記入)[^】]*】|［リンク[:：][^］]*］|\d{4}-\d{2}-XX")
# 根拠が必要な時間の数字（審査の改善提案3b）
TIME_CLAIM = re.compile(r"\d+\s*(秒|分|時間)(で|に|→|から|短縮|削減)")
# コードブロック（文例・プロンプト）の中の強い表現（参考表示）
STRONG_IN_CODE = re.compile(r"必ず|至急|期限厳守|法的措置|遅延損害金")
PUBLISH = False  # --publish で True


def lint(path):
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    errors, warns = [], []
    in_code = False
    in_front = lines[:1] == ["---"]
    meta = {}
    for no, line in enumerate(lines, 1):
        if in_front:
            if no > 1 and line.strip() == "---":
                in_front = False
            m = re.match(r"(\w+):\s*(.*)", line)
            if m:
                meta[m.group(1)] = m.group(2).strip().strip('"')
            continue
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if PLACEHOLDER.search(line):
            (errors if PUBLISH else warns).append((no, "未記入", "確認待ち・未記入の印が残っている（公開前に解消する）", line))
        if in_code:
            if STRONG_IN_CODE.search(line):
                warns.append((no, "文例の表現", "文例・プロンプト内の強い表現（意図どおりか確認）", line))
            continue
        if TIME_CLAIM.search(line):
            warns.append((no, "数字の根拠", "時間の数字には検証条件か根拠が必要", line))
        if re.match(r"^\s*\|.*\|\s*$", line):
            errors.append((no, "書式", "表（テーブル）はnoteで再現できない。箇条書きに置き換える", line))
        if re.match(r"^####", line):
            errors.append((no, "書式", "4段階目以降の見出しは使わない", line))
        for cat, pats in NG.items():
            for pat in pats:
                if re.search(pat, line):
                    allow = ALLOW.get(pat)
                    if allow and re.search(allow, line):
                        continue
                    warns.append((no, cat, f"NGワード候補「{pat}」— 文脈を確認", line))
    is_paid = meta.get("type") == "paid"
    # 特定商取引法の表記など法定の表示ページは、AI活用の定型文・検証日の対象外（D-010）
    is_legal_notice = meta.get("lint_profile") == "legal-notice" or "<!-- lint: legal-notice -->" in text
    if is_paid and PAID_LINE not in text:
        errors.append((0, "販売設計", "有料記事なのに有料ラインの印（ここから有料）がない", ""))
    if not is_legal_notice and not AI_DISCLOSURE.search(text):
        errors.append((0, "表示", "生成AIの活用と検証についての表記がない（法務§4-2）", ""))
    if not is_legal_notice and not re.search(r"検証日|確認日|最終確認", text):
        warns.append((0, "正確性", "検証日・確認日の記載が見当たらない", ""))
    return errors, warns


def main():
    global PUBLISH
    args = sys.argv[1:]
    if "--publish" in args:
        PUBLISH = True
        args.remove("--publish")
    paths = args
    if not paths:
        sys.exit("usage: lint.py [--publish] <file.md> ...")
    total_err = 0
    for p in paths:
        errors, warns = lint(p)
        total_err += len(errors)
        print(f"\n== {p}: ERROR {len(errors)} / WARN {len(warns)}")
        for no, cat, msg, line in errors + warns:
            kind = "ERROR" if (no, cat, msg, line) in errors else "WARN "
            loc = f"L{no}" if no else "全体"
            snippet = (line.strip()[:70] + "…") if len(line.strip()) > 70 else line.strip()
            print(f"  {kind} {loc} [{cat}] {msg}" + (f"\n        > {snippet}" if snippet else ""))
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()

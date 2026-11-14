# 201 原稿の組み立て用ファイル

- `build.py`：検証ログ（`../scenes_part*.json`・`../preface-v2.txt`・`../prompts/` の独立実行の出力）と下の断片から、`03_content/articles/201-office-ai-request-templates.md` を組み立てる。`--out <パス>` で別の場所に書き出せる
- `free_part.md`・`free_rest.md`・`paid_head.md`・`paid_tail.md`：無料部分・有料部分の手書きの断片（第1ラウンドの修正を反映済み。2026-11-13）
- `count_chars.py`：審査と同じ数え方（空白だけを除く）で字数を数える

## 状況（2026-11-13）

第1ラウンドの修正は完了。独立実行の残り（ng-14、場面19の直し、改造後の依頼文の実行）を行い、出力例・NG例を独立実行の出力に差し替えた。場面18のNG例は3回とも比べられる文面が出なかったため載せていない（`../check_ng_indep-result.md`）。オーナーの作業は `../owner-check.md`。

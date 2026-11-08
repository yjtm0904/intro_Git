# 101 検証ログ（年末年始の休業案内メール）

- 検証日：2026-11-08／担当：ライターC（Claude Opus 5.5／claude-opus-5-5）
- 原稿：`03_content/articles/101-year-end-closure-email.md`
- 入力はすべて架空。会社名・担当者名・連絡先は〔　〕の置き換え記号で入れ、実在の情報は入れていない

## 1. 日付と曜日
- `check_dates.py` → `check_dates_result.txt`：2026-12-29（火）、2027-01-04（月）、2027-01-05（火）を照合して一致。休業は7日間、最終日の翌日が営業開始日
- `check_article_dates.py` → `check_article_dates_result.txt`：原稿の曜日つきの日付30件をすべて照合し、誤り0件

## 2. 作成用プロンプト（初版→改善版）
- `prompt_create_v1.md` → `output_create_v1.md` → 点検 `check_create_v1.txt`・`review_create_v1.md`
  - 日付・曜日の誤りはなし。件名だけ曜日なし、Web告知に条件にない「ご注文」、自動返信197字、助言に根拠のない「1〜2週間前」、文面2の「本日」を確認
- `prompt_create_v2.md`（記事に載せる版）→ `output_create_v2.md`（記事の文例1〜4）→ 点検 `check_create_v2.txt`
  - 上の問題はすべて解消。字数は269・207・194・199字。194字と199字は目安をわずかに下回ったが採用（理由は review_create_v1.md 末尾）

## 3. 調整用プロンプト（初版→改善版）
- `prompt_adjust_v1.md` → `output_adjust_v1.md`：日付・〔　〕は保たれたが、「お返事いたします」→「お返事します」に崩れ、変更点の説明なし
- `prompt_adjust_v2.md`（記事に載せる版）→ `output_adjust_v2.md`：日付・〔　〕は一致、崩れた語尾なし、変更点の一覧あり
- 点検 `check_adjust.py` → `check_adjust_v1_v2.txt`

## 4. Gmailの不在通知
- WebSearch（support.google.com に限定、2026-11-08）で、Gmailヘルプ「不在時に自動返信を送信する」https://support.google.com/mail/answer/25922?hl=ja を確認。パソコンでは 設定→すべての設定を表示→全般→不在通知 で期間・件名・メッセージを入れて保存、連絡先にだけ返信する設定がある、という概要だけを記事に載せた
- 本環境のネットワーク設定では support.google.com を直接開けないため、検索結果のページ名・URL・要約で確かめた

## 5. 実行方法の注記とオーナー確認
- 出力は執筆担当のClaudeがこの作業セッション内で、依頼文だけを入力として作成した。新しいチャットでの実行ではない
- 公開前にオーナーが確認すること（約5分）
  1. 自分のClaudeで作成用プロンプト（改善版）を1回実行し、同じ形の4つの文面が出るかを見る
  2. Gmailヘルプのリンクを開き、手順の概要（設定→すべての設定を表示→全般→不在通知）が画面と合っているかを見る

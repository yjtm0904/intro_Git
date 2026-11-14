# 101 検証ログ（年末年始の休業案内メール）

- 検証日：2026-11-08／担当：ライターC（Claude Opus 5.5／claude-opus-5-5）
- 原稿：`03_content/articles/101-year-end-closure-email.md`
- 入力はすべて架空。会社名・担当者名・連絡先は〔　〕の置き換え記号で入れ、実在の情報は入れていない

## 1. 日付と曜日
- `check_dates.py` → `check_dates_result.txt`：2026-12-29（火）、2027-01-04（月）、2027-01-05（火）を照合して一致。休業は7日間、最終日の翌日が営業開始日
- `check_article_dates.py` → `check_article_dates_result.txt`：原稿の曜日つきの日付30件をすべて照合し、誤り0件

## 2. 独立実行（第1ラウンドの修正。R2）

- `prompts/run_independent.py` で、依頼文を `claude -p --tools "" --no-session-persistence --output-format json` に標準入力で渡し、作成用・調整用の初版と改善版を各2回実行した（2026-11-08。モデル claude-opus-5-5。JSONと本文を `prompts/` に保存）
- 作成用（`check_outputs.py` → `prompts/check_create_independent.txt`）
  - 初版 run1・run2：2回とも件名の日付に曜日なし、文例2が「本日1月5日（火）より」、依頼文にない「ご注文」（文面1）、根拠を示せない送る時期（run1「遅くとも休業の2週間前」、run2「12月10日前後」）、条件にない「年内最終営業日 2026年12月28日（月）」、本文が350字超。以前の記録にあった「Web告知に『ご注文』」は、独立実行では文面1に出た
  - 改善版 run1・run2：2回とも要確認0件（本文241〜327字。日付は条件の3つだけで曜日も一致、「本日」なし、条件にない連絡先・サービス内容なし）
- 調整用（`prompts/check_adjust_independent.py` → `prompts/check_adjust_independent.txt`。【文面】には作成用改善版 run1 の文例1を貼った）
  - 初版 run1・run2：2回とも本文の日付から年を省いた（「1月5日（火）」）、「ご不便をおかけいたしますが」→「ご不便をおかけしますが」。変えた箇所の説明は2回とも付いた（以前の記録の「説明がない」は再現しなかったため、本文から削った）
  - 改善版 run1・run2：2回とも日付・〔　〕は元と同じ、敬語の崩れなし、変えた箇所の一覧あり
- 記事の文例1〜4は作成用改善版 run1（`prompts/create_v2.run1.article.txt`。`**` を外し、文例3の小見出し `###` を【　】の形にした。文面は変えていない）。調整の出力例は調整用改善版 run1 から、変わった文と変えた箇所の説明を抜き出した
- 以前の執筆セッション内の出力（下の§3以降）は記録として残すが、記事には使っていない

## 3. 執筆セッション内で作った出力（第1ラウンドの審査前。記事には使っていない）

### 作成用プロンプト（初版→改善版）
- `prompt_create_v1.md` → `output_create_v1.md` → 点検 `check_create_v1.txt`・`review_create_v1.md`
  - 日付・曜日の誤りはなし。件名だけ曜日なし、Web告知に条件にない「ご注文」、自動返信197字、助言に根拠のない「1〜2週間前」、文面2の「本日」を確認
- `prompt_create_v2.md`（記事に載せる版）→ `output_create_v2.md`（記事の文例1〜4）→ 点検 `check_create_v2.txt`
  - 上の問題はすべて解消。字数は269・207・194・199字。194字と199字は目安をわずかに下回ったが採用（理由は review_create_v1.md 末尾）

### 調整用プロンプト（初版→改善版）
- `prompt_adjust_v1.md` → `output_adjust_v1.md`：日付・〔　〕は保たれたが、「お返事いたします」→「お返事します」に崩れ、変更点の説明なし
- `prompt_adjust_v2.md`（記事に載せる版）→ `output_adjust_v2.md`：日付・〔　〕は一致、崩れた語尾なし、変更点の一覧あり
- 点検 `check_adjust.py` → `check_adjust_v1_v2.txt`

## 4. Gmailの不在通知
- WebSearch（support.google.com に限定、2026-11-08）で、Gmailヘルプ「不在時に自動返信を送信する」https://support.google.com/mail/answer/25922?hl=ja を確認。パソコンでは 設定→すべての設定を表示→全般→不在通知 で期間・件名・メッセージを入れて保存、連絡先にだけ返信する設定がある、という概要だけを記事に載せた
- 本環境のネットワーク設定では support.google.com を直接開けないため、検索結果のページ名・URL・要約で確かめた

## 5. オーナーの確認

- `owner-check.md` にチェックボックスで列挙した

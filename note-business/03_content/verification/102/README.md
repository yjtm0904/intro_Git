# 102 検証ログ（年末調整の回収と催促）

- 検証日：2026-11-08／担当：ライターC（Claude Opus 5.5／claude-opus-5-5）
- 原稿：`03_content/articles/102-year-end-adjustment-reminders.md`
- データはすべて架空（社員番号E001〜E020と日付・記号だけ。氏名・申告の中身は作っていない）

## 1. 管理表と関数

ファイル
- `sample_data.csv`：架空の20名分の提出状況（2026-11-30時点の想定。社内の期限は11/27（金）という架空の設定）
- `check_table.py`：Pythonで期待値を求め、LibreOfficeの計算結果と照合する → `check_table_result.txt`
- `lo_verify.py`：LibreOffice Calc 24.2.7.2 にUNO経由で同じ式を入れて calculateAll() する → `lo_result.csv`、`lo_formulas.txt`、`kanrihyo_sample.xlsx`
- `lo_filter_check.txt`：FILTERを同版に入れた結果（#NAME?、エラーコード525。未対応）

結果
- 状況（G列）20行、COUNTIF 4種、COUNTBLANK 3列、Excel 2019以前向けの補助列（H列）とINDEX/MATCHの一覧（J列）：Python と LibreOffice で全項目一致（不一致0件）
- 期待値：完了9・未提出5・差し戻し3・確認待ち3／空欄 B列4・C列3・D列4／未提出の一覧 E003, E006, E009, E014, E017
- FILTER：LibreOffice 24.2では計算できないため、Pythonの期待値（上の一覧と同じ並び）だけを載せた

## 2. 文例を作るプロンプト（初版→改善版）

- `prompt_v1.md` → `output_v1.md` → 点検 `check_outputs_v1.txt`・`review_v1.md`
  - 字数・日付・曜日は問題なし。文例3に税の扱いの断定（確定申告・還付）、文例1・4に入力にない申告書の中身（控除証明書、扶養親族のマイナンバー）が入った
- `prompt_v2.md`（記事に載せる版）→ `output_v2.md` → 点検 `check_outputs_v2.txt`：要確認0件（本文212〜240字、日付は条件の3つだけで曜日も一致）
- 実行方法の注記：出力は執筆担当のClaudeがこの作業セッション内で依頼文だけを入力として作成した。新しいチャットでの実行ではないため、公開前にオーナーが自分のClaudeで改善版を1回実行し、同じ形の4通が出るかを見ることを推奨する

## 3. 制度・様式の確認（一次情報）

- 本環境のネットワーク設定では www.nta.go.jp に接続できない（curl・WebFetch とも不可）ため、WebSearch（nta.go.jp に限定、2026-11-08、2回）の検索結果のページ名・URL・要約で確かめた
- 「年末調整がよくわかるページ（令和8年分）」：検索結果の要約で令和8年分のページの公開を確認。下位ページ「給与所得者（従業員）の方へ（令和８年分）」https://www.nta.go.jp/users/gensen/nencho/index/kyuyosyotokusya.htm 、「源泉徴収義務者（給与の支払者）の方へ（令和８年分）」https://www.nta.go.jp/users/gensen/nencho/index/gimusya.htm が同じ階層にある。記事のリンクは企画書どおり https://www.nta.go.jp/users/gensen/nencho/index.htm
- 様式名の照合（「各種申告書・記載例（扶養控除等申告書など）」https://www.nta.go.jp/users/gensen/nencho/shinkokusyo/index.htm ほか）
  - 給与所得者の扶養控除等（異動）申告書（「A2-1 給与所得者の扶養控除等の（異動）申告」のページ名で確認）
  - 基礎控除・配偶者控除等・特定親族特別控除・所得金額調整控除の申告書を1枚にした兼用様式（検索結果の要約で確認）
  - 給与所得者の保険料控除申告書（「令和８年分 給与所得者の保険料控除申告書の記載例」の名称で確認）
- 記事では、表の列名を「扶養控除等申告書」「基礎控除申告書など（兼用様式）」「保険料控除申告書」と短くして使い、制度の説明はしていない

## 4. オーナーに確認してほしいこと（公開前、約10分）

1. Googleスプレッドシートに `sample_data.csv` を読み込み（またはkanrihyo_sample.xlsx を開き）、G2に記事の式を入れて21行目までコピーし、空いたセルに `=IFERROR(FILTER(A2:A21,G2:G21="未提出"),"該当なし")` を入れる。E003, E006, E009, E014, E017 が縦に並べばOK。Excel（Microsoft 365）が使える場合は `=FILTER(A2:A21,G2:G21="未提出","該当なし")` も同様に確認する
2. 確認できたら、記事の【検証情報】の「【要記入】」を確認日に置き換える
3. 記事のリンク https://www.nta.go.jp/users/gensen/nencho/index.htm を開き、ページ名が「年末調整がよくわかるページ（令和8年分）」であること、上の3つの様式名があることを確かめる

# 記事103 実機確認の手順書（オーナー用・約12分）

対象：記事 `03_content/articles/103-spreadsheet-errors-ask-ai.md`／確認用ブック `03_content/verification/103/103-check.xlsx`（架空データのみ）
目的：この環境の LibreOffice 24.2 では再現できない「配列が展開できない」エラー（Excelの #SPILL!、スプレッドシートの #REF!）と、画面の表示を、Excel（Microsoft 365）とGoogleスプレッドシートで確かめる。
ほかの6種（#N/A・#VALUE!・#REF!・#DIV/0!・#NAME?・合計のずれ）は、LibreOffice 24.2 で実際に起こし、修正前後の値がPythonの期待値と57件一致することを確認済み（`check-result.txt`）。

記事では、画面の文言は断定せず「画面で確かめてください」と書いている。ここで見た表示は、記事を直すときの参考にする。

---

## 1. Excel（Microsoft 365）で確かめる（6分）

1. `103-check.xlsx` をダウンロードして、Excel（Microsoft 365）で開く。
   - Excelの版（「ファイル」→「アカウント」で見える表示）：＿＿＿＿＿＿
2. 「E6_SPILL」シート
   - [ ] F2 に #SPILL! と出る（F5 に「メモ：要確認」がある）
   - F2 を選んだときに出るエラーの印（!）の説明と、選べる項目の名前を書き写す：＿＿＿＿＿＿
   - [ ] F5 の文字を消すと、F2〜F11 に C-001 から C-010 までの10個が並ぶ
3. 「E3_REF」シート
   - J2 を選び、数式バーの表示を確かめる（=G2*H2）。H列を選んで右クリック→「削除」。
   - [ ] 金額の列が I列にずれ、I2 が #REF!、数式バーが「=G2*#REF!」になる（表示：＿＿＿＿）
   - Ctrl+Z で元に戻す。
4. 「E1_NA」「E2_VALUE」「E4_DIV0」「E5_NAME」「E7_SUM」シート（見るだけ）
   - [ ] E1_NA の D4 が #N/A、N4 と O4 が「株式会社見本デザイン」、L4 が 6
   - [ ] E2_VALUE の J7 が #VALUE!、M7 と N7 が 4320
   - [ ] E4_DIV0 の D5・D6 が #DIV/0!、E5・E6（直した式）が空欄
   - [ ] E5_NAME の D3（打ち間違い）が #NAME?。D2（XLOOKUP）は、Microsoft 365 なら「株式会社サンプル商事」と出る（Excel 2019 では #NAME? になる、という記事の説明の確認はできない）
   - [ ] E7_SUM の J22 が 160055、K22 が 2、L22 と O22 が 162015

## 2. Googleスプレッドシートで確かめる（5分）

1. Googleドライブに `103-check.xlsx` をアップロードし、Googleスプレッドシートで開く。
2. 「E6_SPILL」シート
   - [ ] F2 に #REF! と出る
   - F2 にカーソルを合わせたときの説明を書き写す：＿＿＿＿＿＿（記事では「展開先のセルにデータがある、という趣旨の説明が出る」と書いている）
   - [ ] F5 の文字を消すと、F2〜F11 に10個が並ぶ
3. 「E4_DIV0」シート（記事の #DIV/0! の例はスプレッドシートでの相談）
   - [ ] D5・D6 が #DIV/0!、E〜G列（直した式）の5行目・6行目が空欄、ほかの行は前月比の数字
4. 「E7_SUM」シート
   - [ ] J22 が 160055、O22（配列の式）が 162015。O22 が違う値やエラーのときは表示を記録：＿＿＿＿

## 3. 報告

次を事業責任者（Claude）に伝える。記事の検証情報（確認日）と、配列のエラーの節を、見えた表示に合わせて直す。
- 確認日、Excelの版、スプレッドシートを使ったアカウントの種類（個人／Google Workspace）
- 手順1-2・2-2で書き写した表示
- チェックが付かなかった項目と、そのときの表示

## 参考：出典（確認日 2026-11-08）

- Microsoft サポート「#SPILL! エラーを修正する方法」 https://support.microsoft.com/ja-jp/excel/how-to-correct-a-spill-error
- Google ドキュメント エディタ ヘルプ「Google スプレッドシートで配列を使用する」 https://support.google.com/docs/answer/6208276?hl=ja
- Microsoft サポート「Excel で数式のエラーを検出する」 https://support.microsoft.com/ja-jp/excel/detect-formula-errors-in-excel

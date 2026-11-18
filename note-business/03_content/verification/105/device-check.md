# 記事105 実機確認の手順書（オーナー用・約15分）

対象：記事 `03_content/articles/105-lookup-formulas-ask-ai.md`／確認用ブック `03_content/verification/105/105-check.xlsx`（架空データのみ）
目的：この環境の LibreOffice 24.2 では計算できない XLOOKUP（6式）と、スプレッドシート用の式（FILTER など）を、Excel（Microsoft 365）とGoogleスプレッドシートで確かめる。
VLOOKUP・INDEX/MATCH・IFNA・SUMPRODUCT・COUNTIF は、LibreOffice 24.2 で実際に計算し、Pythonの期待値と239件一致を確認済み（`check-result.txt`）。

---

## 1. Excel（Microsoft 365）で確かめる（6分）

1. `105-check.xlsx` をダウンロードして、Excel（Microsoft 365）で開く。「編集を有効にする」が出たら押す。
   - Excelの版（「ファイル」→「アカウント」で見える表示）：＿＿＿＿＿＿
2. 「XLOOKUP確認」シートを開く。
   - [ ] F2〜F7 の6つがすべて「一致」（D列がXLOOKUPの結果、E列が期待する結果）
   - 「不一致」やエラーのものがあれば、その行の例の名前とD列の表示を記録：＿＿＿＿
3. 「請求明細」シートを開く。
   - [ ] N15（4番目の引数を省いたVLOOKUP。C-011は未登録）が「株式会社サンプル企画」（エラーにならず、違う行の値が返る）
   - [ ] L15 が #N/A、D15 と O15 と P15 が「未登録」
   - [ ] J19（未登録の商品 P-11 の金額）が #N/A
4. 「逆引き」シートを開く。
   - [ ] B2〜B4 が C-005／C-010／未登録
   - [ ] F2〜F4 が 14850／37378／未登録（Excel 2019以前向けの2条件の式）
   - [ ] G2〜G4 が 1／1／0（SUMPRODUCTで件数を数える式）

## 2. Googleスプレッドシートで確かめる（7分）

1. Googleドライブに `105-check.xlsx` をアップロードし、右クリック→「アプリで開く」→「Googleスプレッドシート」で開く（Googleスプレッドシートの形式で保存されたコピーで作業してよい）。
2. 「XLOOKUP確認」シート
   - [ ] F2〜F6 が「一致」
   - F7（2つの条件のXLOOKUP）の表示：＿＿＿＿（「一致」でなくてもよい。スプレッドシートでは次の手順3の式を記事に載せている）
3. 「逆引き」シートの J2 に次の式を入れ、J4 までコピーする（記事の「取引先と月の2つの条件で引きたい」のスプレッドシート版）。

```
=IFNA(FILTER(送付記録!$G$2:$G$11,送付記録!$C$2:$C$11=D2,送付記録!$D$2:$D$11=E2),"未登録")
```

   - [ ] J2〜J4 が 14850／37378／未登録
4. 同じく K2 に次の式を入れ、K4 までコピーする（XLOOKUPを配列として計算させる書き方。記事には載せていない。結果だけ記録する）。

```
=ARRAYFORMULA(XLOOKUP(1,(送付記録!$C$2:$C$11=D2)*(送付記録!$D$2:$D$11=E2),送付記録!$G$2:$G$11,"未登録"))
```

   - K2〜K4 の表示：＿＿＿＿
5. 「請求明細」シート
   - [ ] N15 が「株式会社サンプル企画」（スプレッドシートでも、4番目の引数を省くと近似一致になる）
   - [ ] D15・O15・P15 が「未登録」、L15 が #N/A
6. 「逆引き」シート
   - [ ] F2〜F4 が 14850／37378／未登録（スプレッドシートでも Excel 2019以前向けの式が動くか）。動かない場合の表示：＿＿＿＿
   - [ ] G2〜G4 が 1／1／0

## 3. 報告

次を事業責任者（Claude）に伝える。記事の検証情報と、XLOOKUP・FILTERの式の「実機確認」の表記を書き換える。
- 確認日、Excelの版、スプレッドシートを使ったアカウントの種類（個人／Google Workspace）
- チェックが付かなかった項目と、そのときの表示（エラーの文言はそのまま）
- 手順2-2のF7と、手順2-4のK2〜K4の表示（記事のスプレッドシート版の式を変えるかの判断に使う）

## 参考：出典（確認日 2026-11-08）

- Microsoft サポート「XLOOKUP 関数」：XLOOKUPは Excel 2016・Excel 2019 では使えない旨の注記 https://support.microsoft.com/ja-jp/excel/functions/xlookup-function
- Microsoft サポート「Excel 2021 for Windows の新機能」：XLOOKUP・動的配列を含む https://support.microsoft.com/en-us/excel/what-s-new-in-excel-2021-for-windows
- Microsoft サポート「IFNA 関数」 https://support.microsoft.com/ja-jp/excel/functions/ifna-function
- Google ドキュメント エディタ ヘルプ「XLOOKUP 関数」 https://support.google.com/docs/answer/12405947?hl=ja

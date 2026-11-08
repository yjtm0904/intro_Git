# GASロジック検証用モック（Node.js）

記事で配布するGoogle Apps Script（GAS）のコードを、Google環境なしでテストするためのモック。「検証済み」と書くための検証ログを作る。

## 検証の2段階

1. **ロジック検証（エージェント）**: このモックで、読み取り・条件分岐・書き込み・メール送信の呼び出しをテストする。テストコードと実行結果は `03_content/verification/<記事ID>/` に保存する。
2. **実機確認（オーナー、公開前）**: 自分のGoogleアカウントで、権限の承認、実際のメール送信（自分宛て）、PDF化、トリガーを確認する。手順書は記事ごとに `03_content/verification/<記事ID>/device-check.md` に用意する。

## 使い方

```js
const { createGasEnv } = require('../../05_operations/tools/gas-mock');
const env = createGasEnv({
  now: '2026-11-30T10:00:00+09:00',               // new Date() を固定（任意）
  sheets: { '請求一覧': [['請求番号', '会社名', 'メール', '金額', '送信日']] },
  scriptProperties: { FOLDER_ID: 'xxx' },
});
env.load('Code.gs');        // 配布するコードを読み込む
env.ctx.createInvoices();   // 関数を実行
env.GmailApp.sent;          // 送信記録 [{to, subject, body, options}]
env.DriveApp.files;         // 作成ファイル [{folderId, name, blob}]
env.sheet('請求一覧').getRange('E2').getValue();
```

テストは Node 標準のテストランナーで実行する: `node --test <テストファイル>`（見本: `example.test.js`）

## 対応範囲と注意

- SpreadsheetApp / Sheet / Range（A1表記・行列指定、getValues/setValues ほか）、GmailApp、MailApp、DriveApp、Utilities（formatDate・newBlob）、Logger、PropertiesService、Session、LockService、MimeType、UrlFetchApp/ScriptApp（呼び出しを記録するだけ）。
- PDFの中身・レイアウト、権限ダイアログ、送信数の上限、実行時間の上限（6分）は検証できない。これらは実機確認の対象にする。
- 未対応のメソッドを呼ぶとエラーになる。必要になったら `index.js` に追加する。
- 2026-11-08追加：`Sheet.copyTo`・`setName`、`Spreadsheet.deleteSheet`、UIの `alert`（ボタンと戻り値。`env.ui.responses` に積んだ順に返す）とメニューの記録（`env.ui.menus`）、`SpreadsheetApp.create` の記録（`env.created`）、`DriveApp` の `setTrashed`（`env.DriveApp.trashed`）、`getAs` が返すBlobの `snapshot`（PDF化した時点のシートの中身）、書式設定メソッドの空実装。

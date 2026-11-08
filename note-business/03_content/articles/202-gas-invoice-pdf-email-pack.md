---
id: "202"
title: "月末の請求書をPDF化してメール下書きまで作るGAS業務パック｜コード全文・引き継ぎ書つき"
type: paid
price: 1980
target_reader: "月末の締めのあと、取引先10〜50社分の請求書をひな形に写し、PDFにして1通ずつメールで送っている経理・総務。業務でGoogleスプレッドシートを使い、GASは未経験か、AIに書かせて動かなかった"
primary_keyword: "GAS 請求書 PDF メール"
hashtags: ["#GAS", "#スプレッドシート", "#請求書", "#経理", "#業務効率化"]
magazine: "請求と集計の自動化｜スプレッドシート・Excel・GAS（W6から「事務・経理・総務の業務テンプレ集」にも追加）"
cta_to: ["107", "105", "108", "103", "106", "201"]
status: draft
---

最終更新日：2026-11-08／動作確認日：【実機確認後に記入】／対応：Googleスプレッドシート、Google Apps Script（2026年11月時点）／確認環境：【実機確認したアカウントの種類（個人のGoogleアカウント／Google Workspace）を記入】

締めの翌日、請求書のひな形に取引先ごとの明細を写し、PDFにして1通ずつメールに添付していませんか。取引先が30社あれば、写す・PDFにする・添付するという作業を30回くり返します。このパックのコードを使うと、請求明細を埋めてメニューを押せば、取引先ごとの請求書PDFとメールの下書きができます。送るのは、下書きを確かめてからです。

【検証情報】検証日：2026-11-08／使ったツール：Claude（2026年11月時点）、Node.js 22、Python 3.13
検証方法：Googleのサービスを再現するテスト用の仕組み（Node.js）で、架空30社・明細100行のデータを流し、26件のテストがすべて成功。消費税の集計は、3つの端数処理それぞれでPythonの別計算と一致を確認。Googleの実際の環境での確認（承認の画面・PDFの見た目・下書き）は、筆者の検証用アカウントで実施（実機確認日：【記入】）

このパックは、生成AI（Claude）と一緒にコードを書き、架空のデータでテストしてから公開しています。書いているのは、検証で実際に確かめたことだけです。テストの記録と、Googleの環境で確かめる手順は、改訂のたびに更新します。

## この記事で手に入るもの

- コード全文（Google Apps Script、約390行）：メニュー追加・設定の読み込み・明細の集計・請求書シートの作成・PDF化と保存・下書き作成と送信・二重送信の防止と送付記録・テストモードの8つの関数に、確認用と準備用の関数を加えたもの
- シートのひな形5枚：取引先マスタ・請求明細・請求書レイアウト・送付記録・設定の列構成。メニューの「準備」で自動で作れます
- 設定手順書：コードを貼る、承認する、テストする、本番に切り替えるまで
- 権限の説明：初回の承認で何を許可するのか、なぜ必要か
- エラー対処表：16項目（止まったときの表示→原因→直し方）
- 引き継ぎ書の雛形：担当が替わっても毎月回すための1枚
- 自社用に改造する依頼文3本：列を足す・CCを付ける・文面を変える。Claudeで実行し、出力されたコードが動くことをテストで確かめています

ほかに、適格請求書の記載項目のチェックリスト（国税庁の資料をもとに作成）と、導入時の確認チェックリストが付きます。

## 向いている人・向いていない人・扱わないこと

### 向いている人

- 毎月、取引先10〜50社ほどの請求書を、スプレッドシートのひな形から作り、PDFにしてメールで送っている経理・総務の方
- 業務でGoogleアカウント（Gmail・ドライブ・スプレッドシート）を使っている方
- GASは初めて、またはAIに書かせたコードが動かなかった方。コードを読めなくても、手順どおりに貼って試せる方

### 向いていない人

- 業務でGoogleアカウントを使えない方（Excelだけの職場など）
- 会計ソフトや請求書発行サービスで請求書を出している方。そのサービスの機能を使う方が早く済みます
- 勤務先がスクリプト（GAS）の利用を認めていない方、または確かめられない方

### この記事で扱わないこと

- 税務の判断（端数処理の方式の選び方、記載内容が要件を満たすかどうか）。方式は設定で選べるようにしてあります。どれにするかは、社内の経理責任者や税理士に確かめてください
- 入金消込、会計ソフトとの連携、郵送での送付
- 副業で稼ぐ方法

## 用意するもの・前提（アカウント・権限・送信の上限）

- Googleアカウント：個人のアカウントでも、Google Workspaceでも、コードは同じです。勤務先のWorkspaceでは、管理者がスクリプトの利用を制限していることがあります
- 社内ルールの確認：スクリプトを使うこと、取引先の情報をスプレッドシートで扱うことを、情報システムの担当者か上長に確かめておきます。生成AIを使う場合は、AIの利用ルールも確かめます
- 初回の承認：コードが使うGmail・ドライブ・スプレッドシートの権限を、自分のアカウントで許可します（有料部分の「権限の説明」で、何を許可するかを説明しています）
- 送信の上限：Googleの公式ページ「Quotas for Google Services」（確認日：2026-11-08）には、次の値が載っています
  - メールの受信者数：1日あたり、個人のアカウントは100人、Google Workspaceは1,500人
  - 1回の実行時間：6分まで（このコードは、4分30秒か30件で止め、続きは再実行で作ります）
  - 1通あたりの添付：250個まで、合計25MBまで
- 上限は予告なく変わることがあると、同じページに書かれています。使う前に[公式ページ](https://developers.google.com/apps-script/guides/services/quotas)で確かめてください
- テスト用の架空データ：有料部分に3社分を用意しています。実在の取引先のデータで試すのは、テストが終わってからにします
- 時間：初回は、テストまでで30分ほどを見込んでください（筆者が実機確認に使う手順を、30分で終わる分量にしています）

## 全体像：7つのステップと収録物

［図解：5枚のシートとデータの流れ／取引先マスタ＋請求明細 →（取引先・税率ごとに集計）→ 請求書レイアウト → PDF（ドライブに保存）→ メールの下書き（Gmail）→ 送付記録］

7つのステップ

1. 5枚のシートを作る（このあと無料で全文を載せます）
2. コードを貼る（全文）。初回の承認で許可する権限
3. 設定シートを埋める（端数処理・件名・本文）
4. テストモードで架空データを流す
5. 請求書PDFを作る（レイアウトの直し方、記載項目のチェックリスト）
6. メールの下書きを作り、確かめて送る
7. 毎月の運用（締め日から送付記録まで）

コードの関数（全24個）

- 主な関数8つ
  - onOpen：メニュー「請求書」を追加する
  - loadSettings_：設定シートを読み、空欄や形式の誤りをまとめて知らせる
  - aggregateInvoices_：明細を取引先ごと・税率ごとに集計する（消費税の端数処理は、請求書1枚につき税率ごとに1回）
  - buildInvoiceSheet_：レイアウトの {{項目名}} に値を入れ、明細を並べる
  - savePdf_：一時ファイルをPDFにして、指定のフォルダに保存する
  - deliverMail_：メールの下書きを作る（設定で「送信」にしたときだけ送る）
  - deliveryLog_：送付記録を読み書きし、同じ月・同じ取引先の請求書を二度作らない
  - applyTestMode_：テストモードのとき、宛先を自分にし、件名とファイル名に【テスト】を付ける
- メニューから呼ぶ関数3つ：previewInvoices（①内容を確認する）、createInvoices（②PDFとメールを作成する）、setupSheets（準備：5枚のシートを作る）
- 補助の関数13個：plan_、summary_、linePos_、readTable_、calcTax_、fill_、toMonth_、toDate_、toRate_、isDate_、isEmail_、yen_、sheet_

関数のほかの収録物

- 権限の説明、テスト用の架空データ（3社）と期待する結果、導入時の確認チェックリスト
- 適格請求書の記載項目のチェックリスト
- エラー対処表（16項目）、引き継ぎ書の雛形、自社用に改造する依頼文3本、改訂履歴

仕組みの考え方だけを先に知りたい方は、無料の記事「スプレッドシートで請求書を自動作成する仕組みの全体像」（［リンク：107の記事］）をご覧ください。シートの考え方と、1社分の請求書シートを作る最小のコードを載せています。

## 無料サンプル：ステップ1 5枚のシートを作る

新しいスプレッドシートに、次の5枚のシートを作ります。シート名と1行目の見出しは、このとおりにしてください。コードは見出しの名前で列を探すので、列の順番を変えたり、右に列を足したりしても動きます。

有料部分のコードを貼ったあとは、メニューの「準備：5枚のシートを作る」で、このとおりのシートが自動でできます。手で作っておいた場合は、そのシートを残して、足りないシートだけを作ります。

### 取引先マスタ（1社1行）

- A列 取引先コード：例 C-001。重複させない
- B列 取引先名：例 株式会社サンプル商事（請求書の宛名とメールに入る）
- C列 部署：例 経理部（空欄でよい）
- D列 メール：例 sample-shoji@example.com。空欄なら「メール未登録」として、PDFだけを作る

### 請求明細（明細1件で1行）

- A列 対象月：例 2026-11（設定の「対象月」と同じ行だけを集計する）
- B列 取引日：例 2026/11/05
- C列 取引先コード：取引先マスタと同じコード
- D列 取引先名：表示用（コードは読まない）
- E列 商品コード：表示用・任意
- F列 品目：例 月額保守サービス
- G列 数量：数値
- H列 単価：税抜の数値
- I列 税率：10% か 8%
- J列 金額：表示用（コードは数量×単価で計算し直す）

D列とJ列は、数式で表示しておくと入力を確かめやすくなります。

```
D2：=IFNA(VLOOKUP(C2,取引先マスタ!$A$2:$D$200,2,FALSE),"未登録")
J2：=IF(G2="","",G2*H2)
```

取引先マスタから値を引く数式の頼み方は、VLOOKUP・XLOOKUPの記事で詳しく扱います（公開後にリンクを追記します）。

### 請求書レイアウト（A4縦の1枚）

値を入れたい場所に {{項目名}} と書いておくと、コードがその場所に値を入れます。セルの配置は次のとおりです。

- A1：請求書（A1からF1を結合）
- A3：{{取引先名}} 御中／A4：{{部署}}
- E3：請求書番号／F3：{{請求書番号}}
- E4：発行日／F4：{{発行日}}
- A6：下記のとおりご請求申し上げます。
- E6：{{発行者名}}／E7：{{発行者住所}}／E8：登録番号 {{登録番号}}
- A7：件名／B7：{{対象月}}分のご請求
- A8：ご請求金額（税込）／B8：{{合計}}
- A9：お支払期限／B9：{{支払期限}}
- A10：お振込先／B10：{{振込先}}
- 12行目（明細の見出し）：取引日・品目・税率・数量・単価・金額（税抜）
- 13行目（明細）：{{明細:取引日}}・{{明細:品目}}・{{明細:税率}}・{{明細:数量}}・{{明細:単価}}・{{明細:金額}}。ここから下の15行が明細欄で、何も書かずに空けておく
- D29〜D33とF29〜F33：10%対象（税抜）{{10%対象}}／消費税（10%）{{10%消費税}}／8%対象（税抜）{{8%対象}}／消費税（8%）{{8%消費税}}／合計（税込）{{合計}}
- A35：※税率の欄に「8%※」とある品目は、軽減税率の対象です。
- A36：{{備考}}

### 送付記録（コードが1社1行ずつ書き足す）

- A 記録日時／B モード（テスト・本番）／C 対象月／D 取引先コード／E 取引先名／F 請求書番号／G 合計（税込）／H 宛先／I 状態／J PDFファイル名／K PDFのURL／L メモ

### 設定（A列 項目／B列 値／C列 説明）

A列の2行目から順に、次の17項目を入れます。

- 対象月／発行日／支払期限／端数処理／発行者名／発行者住所／登録番号／振込先／備考／PDF保存フォルダID／件名／本文／差出人名／送信方法（既定：下書き）／テストモード（既定：ON）／テスト用の宛先／1回の上限件数（既定：30）

### コードの冒頭（メニュー追加と設定の読み込み）

コードの最初の部分を全文で載せます。この部分だけでは動きません（補助の関数が要るため）。全文は有料部分のステップ2にあります。

```
/**
 * 請求書PDF・メール下書き作成スクリプト v1.0（2026-11-08）事務の型紙「GAS請求書パック」
 * 流れ：請求明細を取引先ごと・税率ごとに集計 → 請求書PDFをドライブに保存 → メールの下書き → 送付記録
 * 安全のための既定：テストモード ON・下書き。同じ月・同じ取引先の請求書は二度作らない。
 */
const SHEET = { master: '取引先マスタ', details: '請求明細', layout: '請求書レイアウト', log: '送付記録', settings: '設定' };
const LOG_HEAD = ['記録日時', 'モード', '対象月', '取引先コード', '取引先名', '請求書番号', '合計（税込）', '宛先', '状態', 'PDFファイル名', 'PDFのURL', 'メモ'];
const BLOCK = ['処理中', '下書き済み', '送信済み', 'メール未登録', '要確認']; // この状態の記録があれば作らない
const LINE_KEYS = ['取引日', '品目', '税率', '数量', '単価', '金額'];          // 明細に差し込める項目
const MAX_LINES = 15;               // 請求書レイアウトの明細欄の行数
const TIME_LIMIT = 4.5 * 60 * 1000; // 実行時間の上限（6分）の手前で止める

/** 1 メニュー追加：スプレッドシートを開くと「請求書」メニューが出る */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('請求書')
    .addItem('① 内容を確認する（作成しない）', 'previewInvoices')
    .addItem('② PDFとメールを作成する', 'createInvoices')
    .addSeparator()
    .addItem('準備：5枚のシートを作る', 'setupSheets')
    .addToUi();
}

/** 2 設定の読み込み：空欄や形式の誤りは、まとめて知らせて止める */
function loadSettings_() {
  const v = {};
  sheet_(SHEET.settings).getDataRange().getValues().slice(1).forEach(r => { if (r[0] !== '') v[String(r[0]).trim()] = r[1]; });
  const text = k => (v[k] === undefined || v[k] === null ? '' : String(v[k]).trim());
  const test = text('テストモード').toUpperCase();
  const s = {
    month: toMonth_(v['対象月']), issueDate: text('発行日') ? toDate_(v['発行日']) : new Date(), dueDate: toDate_(v['支払期限']),
    rounding: text('端数処理'), issuer: text('発行者名'), address: text('発行者住所'), regNo: text('登録番号'),
    bank: text('振込先'), note: text('備考'), folderId: text('PDF保存フォルダID'),
    subject: text('件名'), body: text('本文'), senderName: text('差出人名'), mailMode: text('送信方法') || '下書き',
    test: test !== 'OFF' && test !== 'FALSE', testTo: text('テスト用の宛先'), maxPerRun: Number(v['1回の上限件数']) || 30,
  };
  const e = [];
  if (!s.month) e.push('対象月：「2026-11」のように入れてください');
  if (!s.issueDate) e.push('発行日：日付を入れてください（空欄なら実行した日）');
  if (!s.dueDate) e.push('支払期限：日付を入れてください');
  if (['切り捨て', '四捨五入', '切り上げ'].indexOf(s.rounding) < 0) e.push('端数処理：「切り捨て」「四捨五入」「切り上げ」のどれかを、社内のルールに合わせて入れてください');
  if (!s.issuer) e.push('発行者名：請求書に載せる自社名を入れてください');
  if (s.regNo && !/^T\d{13}$/.test(s.regNo)) e.push('登録番号：「T」と13桁の数字で入れてください');
  if (!s.folderId) e.push('PDF保存フォルダID：PDFを保存するフォルダのIDを入れてください');
  if (!s.subject || !s.body) e.push('件名・本文：メールの件名と本文を入れてください');
  if (['下書き', '送信'].indexOf(s.mailMode) < 0) e.push('送信方法：「下書き」か「送信」を入れてください');
  if (['', 'ON', 'OFF', 'TRUE', 'FALSE'].indexOf(test) < 0) e.push('テストモード：「ON」か「OFF」を入れてください');
  if (s.test && !isEmail_(s.testTo)) e.push('テスト用の宛先：テストのときに届く自分のメールアドレスを入れてください');
  if (e.length) throw new Error('設定シートを直してください（まだ何も作っていません）。\n・' + e.join('\n・'));
  return s;
}
```

## 事故を防ぐ設計（下書きで確認・二重送信の防止・テストモード）

請求書のメールは、宛先や金額を間違えると取り消せません。このコードは、次の6つの仕組みで事故を防ぎます。

- 下書きが既定：設定の「送信方法」は「下書き」から始まります。Gmailの下書きを1通ずつ開いて確かめてから送ります
- 送る前に件数を確認：作成の前に、件数・合計・宛先の一覧を出し、「はい」を押すまで何も作りません。「送信」にしたときは「メールはすぐに送信され、取り消せません」と表示します
- 二重送信の防止：作る前に送付記録へ「処理中」と書き、同じモード・同じ月・同じ取引先の記録があれば作りません。途中で止まって、送ったかどうか分からないものは、自動で作り直しません
- テストモードが既定：テストモードが「ON」のあいだは、メールはすべて自分のアドレスに届き、件名とファイル名に【テスト】が付きます
- 作る前に止める：設定の空欄、マスタにない取引先コード、数値でない数量、10%・8%以外の税率、15行を超える明細、使えない差し込み項目を見つけると、何も作らずに行番号つきで知らせます
- 二重起動と時間切れの防止：メニューを続けて押しても、2つ目の実行は止まります。6分の上限の手前（4分30秒か30件）で止め、続きは再実行で作ります

テストでは、次のようなことを確かめました（26件の一部）。

- 架空30社・明細100行で、取引先ごと・税率ごとの合計と消費税が、別に計算した値と一致する
- 同じ月にもう一度実行すると、PDFも下書きも増えない
- 送信の確認で「いいえ」を押すと、何も作らない
- メール作成の途中で失敗した取引先は「要確認」になり、再実行しても作り直さない

## よくある質問

### 無料のGoogleアカウントで動きますか？

コードは、個人のアカウントでもGoogle Workspaceでも同じです。違うのは上限で、メールの受信者数は1日あたり個人が100人、Workspaceが1,500人です（公式ページ、確認日：2026-11-08）。勤務先のWorkspaceでは、管理者の設定でスクリプトが使えないことがあります。筆者は【個人／Workspace】のアカウントで実機確認しています。

### Excelで使えますか？

使えません。GASはGoogleのサービスの中で動くため、Googleスプレッドシートが必要です。Excelの明細をスプレッドシートに取り込めば使えます。

### 誤って送ってしまいませんか？

既定は下書きなので、作成しただけでは送られません。テストモードのあいだは、宛先がすべて自分になります。同じ月・同じ取引先は二度作りません。ただし、設定を「送信」にして確認で「はい」を押すと、すぐに送られます。最初の数か月は下書きで運用し、1通ずつ確かめて送ることをおすすめします。

### インボイス（適格請求書）に対応していますか？

登録番号、取引日、税率ごとの合計と消費税、軽減税率の印、宛名の欄があります。消費税の端数処理は、国税庁の資料にあるとおり、請求書1枚につき税率ごとに1回です。ただし、自社の請求書が要件を満たすかどうかは、この記事では判断しません。社内の経理責任者や税理士に確かめてください。

### 取引先が増えても動きますか？

1回の実行は6分までなので、このコードは30件か4分30秒で止め、もう一度実行すると続きから作ります。明細は、1社あたりレイアウトの15行までです。増やす方法は有料部分のエラー対処表に書いています。送信に切り替える場合は、1日の受信者数の上限にも気をつけてください。

## 価格について

価格は1,980円です。取引先30社の場合、写す・PDFにする・添付するという30回の作業を、毎月メニュー2回（確認と作成）と下書きの確認に置き換える道具です。毎月この作業にかけている時間と比べて、ご判断ください。

デジタルコンテンツのため、原則として返品はできません。コードとひな形は購入後すぐに持ち帰れる内容のため、返金の申請は受け付けない設定にしています。内容に重大な誤りがあった場合はご連絡ください。

購入後も、この記事の最新版を読めます。誤りやGoogleの仕様の変更に合わせて改訂し、末尾の改訂履歴に残します。使ってみての感想や追加してほしい機能は、購入者限定のコメント欄で受け付けます。

**━━━━━━ ここから有料（noteの有料ラインをこの位置に設定）━━━━━━**

## ステップ2 コードを貼る（全文）

ステップ1のスプレッドシートを開いて、次の順に進めます。

1. メニューの「拡張機能」→「Apps Script」を開く
2. 最初からある function myFunction() { } を消し、下のコードを全文貼って保存する（Ctrl+S、Macは⌘+S）
3. 左の「プロジェクトの設定」（歯車の形）で、タイムゾーンが「(GMT+09:00) 日本標準時 - 東京」になっているかを確かめる。違うと、発行日などが1日ずれることがある
4. スプレッドシートのタブに戻って、ページを再読み込みする。数秒で、メニューに「請求書」が出る
5. 「請求書」→「準備：5枚のシートを作る」を実行する。初回は承認の画面が出る（次の節）。承認が終わったら、もう一度実行する

```
/**
 * 請求書PDF・メール下書き作成スクリプト v1.0（2026-11-08）事務の型紙「GAS請求書パック」
 * 流れ：請求明細を取引先ごと・税率ごとに集計 → 請求書PDFをドライブに保存 → メールの下書き → 送付記録
 * 安全のための既定：テストモード ON・下書き。同じ月・同じ取引先の請求書は二度作らない。
 */
const SHEET = { master: '取引先マスタ', details: '請求明細', layout: '請求書レイアウト', log: '送付記録', settings: '設定' };
const LOG_HEAD = ['記録日時', 'モード', '対象月', '取引先コード', '取引先名', '請求書番号', '合計（税込）', '宛先', '状態', 'PDFファイル名', 'PDFのURL', 'メモ'];
const BLOCK = ['処理中', '下書き済み', '送信済み', 'メール未登録', '要確認']; // この状態の記録があれば作らない
const LINE_KEYS = ['取引日', '品目', '税率', '数量', '単価', '金額'];          // 明細に差し込める項目
const MAX_LINES = 15;               // 請求書レイアウトの明細欄の行数
const TIME_LIMIT = 4.5 * 60 * 1000; // 実行時間の上限（6分）の手前で止める

/** 1 メニュー追加：スプレッドシートを開くと「請求書」メニューが出る */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('請求書')
    .addItem('① 内容を確認する（作成しない）', 'previewInvoices')
    .addItem('② PDFとメールを作成する', 'createInvoices')
    .addSeparator()
    .addItem('準備：5枚のシートを作る', 'setupSheets')
    .addToUi();
}

/** 2 設定の読み込み：空欄や形式の誤りは、まとめて知らせて止める */
function loadSettings_() {
  const v = {};
  sheet_(SHEET.settings).getDataRange().getValues().slice(1).forEach(r => { if (r[0] !== '') v[String(r[0]).trim()] = r[1]; });
  const text = k => (v[k] === undefined || v[k] === null ? '' : String(v[k]).trim());
  const test = text('テストモード').toUpperCase();
  const s = {
    month: toMonth_(v['対象月']), issueDate: text('発行日') ? toDate_(v['発行日']) : new Date(), dueDate: toDate_(v['支払期限']),
    rounding: text('端数処理'), issuer: text('発行者名'), address: text('発行者住所'), regNo: text('登録番号'),
    bank: text('振込先'), note: text('備考'), folderId: text('PDF保存フォルダID'),
    subject: text('件名'), body: text('本文'), senderName: text('差出人名'), mailMode: text('送信方法') || '下書き',
    test: test !== 'OFF' && test !== 'FALSE', testTo: text('テスト用の宛先'), maxPerRun: Number(v['1回の上限件数']) || 30,
  };
  const e = [];
  if (!s.month) e.push('対象月：「2026-11」のように入れてください');
  if (!s.issueDate) e.push('発行日：日付を入れてください（空欄なら実行した日）');
  if (!s.dueDate) e.push('支払期限：日付を入れてください');
  if (['切り捨て', '四捨五入', '切り上げ'].indexOf(s.rounding) < 0) e.push('端数処理：「切り捨て」「四捨五入」「切り上げ」のどれかを、社内のルールに合わせて入れてください');
  if (!s.issuer) e.push('発行者名：請求書に載せる自社名を入れてください');
  if (s.regNo && !/^T\d{13}$/.test(s.regNo)) e.push('登録番号：「T」と13桁の数字で入れてください');
  if (!s.folderId) e.push('PDF保存フォルダID：PDFを保存するフォルダのIDを入れてください');
  if (!s.subject || !s.body) e.push('件名・本文：メールの件名と本文を入れてください');
  if (['下書き', '送信'].indexOf(s.mailMode) < 0) e.push('送信方法：「下書き」か「送信」を入れてください');
  if (['', 'ON', 'OFF', 'TRUE', 'FALSE'].indexOf(test) < 0) e.push('テストモード：「ON」か「OFF」を入れてください');
  if (s.test && !isEmail_(s.testTo)) e.push('テスト用の宛先：テストのときに届く自分のメールアドレスを入れてください');
  if (e.length) throw new Error('設定シートを直してください（まだ何も作っていません）。\n・' + e.join('\n・'));
  return s;
}

/** 3 明細の集計：対象月の明細を取引先ごと・税率ごとに合計する。消費税の端数処理は請求書1枚につき税率ごとに1回 */
function aggregateInvoices_(s) {
  const clients = {}, groups = {}, e = [];
  readTable_(SHEET.master, ['取引先コード', '取引先名', '部署', 'メール']).forEach(r => {
    const c = { code: String(r['取引先コード']).trim(), name: String(r['取引先名']).trim(), dept: String(r['部署']).trim(), email: String(r['メール']).trim() };
    if (!c.code) return e.push('取引先マスタ ' + r.row + '行目：取引先コードが空欄です');
    if (clients[c.code]) e.push('取引先マスタ ' + r.row + '行目：取引先コード「' + c.code + '」が重複しています');
    if (c.email && !isEmail_(c.email)) e.push('取引先マスタ ' + r.row + '行目：メールアドレスの形式を確かめてください');
    clients[c.code] = c;
  });
  readTable_(SHEET.details, ['対象月', '取引日', '取引先コード', '品目', '数量', '単価', '税率']).forEach(r => {
    if (toMonth_(r['対象月']) !== s.month) return;            // 対象月の明細だけを使う
    const code = String(r['取引先コード']).trim(), qty = r['数量'], price = r['単価'];
    const line = { date: toDate_(r['取引日']), item: String(r['品目']).trim(), qty: qty, price: price, rate: toRate_(r['税率']), amount: Math.round(qty * price * 1e6) / 1e6 };
    const bad = [];
    if (!clients[code]) bad.push('取引先コード「' + code + '」が取引先マスタにありません');
    if (!line.date) bad.push('取引日が日付ではありません');
    if (typeof qty !== 'number' || typeof price !== 'number') bad.push('数量と単価は数値で入れてください');
    else if (!Number.isInteger(line.amount)) bad.push('金額（数量×単価）に1円未満の端数があります');
    if (!line.rate) bad.push('税率は10%か8%にしてください');
    if (bad.length) e.push('請求明細 ' + r.row + '行目：' + bad.join('／'));
    else (groups[code] = groups[code] || []).push(line);
  });
  const invoices = Object.keys(groups).sort().map(code => {
    const c = clients[code], lines = groups[code].sort((a, b) => a.date - b.date); // 取引日の順（同じ日は入力順）
    const base = { 10: 0, 8: 0 };
    lines.forEach(l => { base[l.rate] += l.amount; });
    if (lines.length > MAX_LINES) e.push('取引先 ' + code + '：明細が' + lines.length + '行あります（請求書レイアウトの明細欄は' + MAX_LINES + '行まで）');
    if (base[10] < 0 || base[8] < 0) e.push('取引先 ' + code + '：税率ごとの合計がマイナスです（値引き・返品の扱いは社内で確認してください）');
    const tax = { 10: calcTax_(base[10], 10, s.rounding), 8: calcTax_(base[8], 8, s.rounding) };
    const inv = { code: code, name: c.name, dept: c.dept, email: c.email, number: 'INV-' + s.month.replace('-', '') + '-' + code,
      lines: lines, base: base, tax: tax, total: base[10] + tax[10] + base[8] + tax[8] };
    inv.fields = {
      '取引先コード': code, '取引先名': c.name, '部署': c.dept, '請求書番号': inv.number, '対象月': s.month.replace(/^(\d{4})-0?(\d+)$/, '$1年$2月'),
      '発行日': s.issueDate, '支払期限': s.dueDate, '発行者名': s.issuer, '発行者住所': s.address, '登録番号': s.regNo, '振込先': s.bank, '備考': s.note,
      '10%対象': base[10], '10%消費税': tax[10], '8%対象': base[8], '8%消費税': tax[8],
      '税抜合計': base[10] + base[8], '消費税合計': tax[10] + tax[8], '合計': inv.total,
    };
    return inv;
  });
  if (e.length) throw new Error('データを直してください（まだ何も作っていません）。\n・' + e.slice(0, 15).join('\n・') + (e.length > 15 ? '\n…ほか' + (e.length - 15) + '件' : ''));
  return { invoices: invoices, idle: Object.keys(clients).filter(code => !groups[code]) };
}

/** 4 請求書シートの作成：レイアウトの {{項目名}} に値を入れ、{{明細:…}} の行から下へ明細を並べる */
function buildInvoiceSheet_(sheet, layout, inv) {
  const pos = linePos_(layout);
  const out = layout.map(row => row.map(v => {
    if (typeof v !== 'string' || v.indexOf('{{') < 0 || v.indexOf('{{明細:') === 0) return v;
    const one = v.match(/^\{\{([^{}]+)\}\}$/), x = one ? inv.fields[one[1]] : undefined;
    return x !== undefined && typeof x !== 'string' ? x : fill_(v, inv.fields); // 数値・日付はそのまま入れて表示形式を生かす
  }));
  while (out.length < pos.top + MAX_LINES) out.push(out[0].map(() => ''));
  for (let i = 0; i < MAX_LINES; i++) {
    const l = inv.lines[i];
    const val = l ? { 取引日: l.date, 品目: l.item, 税率: l.rate === 8 ? '8%※' : '10%', 数量: l.qty, 単価: l.price, 金額: l.amount } : {};
    pos.cols.forEach((key, j) => { if (key) out[pos.top + i][j] = l ? val[key] : ''; });
  }
  sheet.getRange(1, 1, out.length, out[0].length).setValues(out);
}

/** 5 PDF化と保存：一時ファイルをPDFで取り出し、設定のフォルダに保存する（公開されているメソッドだけを使う） */
function savePdf_(tmp, fileName, folderId) {
  SpreadsheetApp.flush();                                   // 書き込みを反映してからPDFにする
  const blob = tmp.getAs(MimeType.PDF).setName(fileName);  // 名前は最後に付け直す（「.」を含む社名の欠けを防ぐ）
  return { blob: blob, file: DriveApp.getFolderById(folderId).createFile(blob) };
}

/** 6 下書き作成・送信：既定は下書き。設定の送信方法が「送信」のときだけ送る */
function deliverMail_(mail, blob, s) {
  const options = { attachments: [blob] };
  if (s.senderName) options.name = s.senderName;
  if (s.mailMode === '送信') {
    GmailApp.sendEmail(mail.to, mail.subject, mail.body, options);
    return '送信済み';
  }
  GmailApp.createDraft(mail.to, mail.subject, mail.body, options);
  return '下書き済み';
}

/** 7 二重送信の防止と送付記録：同じモード・月・取引先の記録があれば作らない。作る前に「処理中」と書いておく */
function deliveryLog_(s) {
  const sh = sheet_(SHEET.log), data = sh.getDataRange().getValues();
  if (data[0].join('|') !== LOG_HEAD.join('|')) throw new Error('送付記録の1行目の見出しが変わっています。列の順番を元に戻してください（まだ何も作っていません）');
  const mode = s.test ? 'テスト' : '本番', seen = {};
  data.slice(1).forEach(r => {
    if (r[1] === mode && toMonth_(r[2]) === s.month && BLOCK.indexOf(String(r[8]).trim()) >= 0) seen[String(r[3]).trim()] = String(r[8]).trim();
  });
  return {
    status: code => seen[code] || '',
    start: (inv, to) => {
      sh.appendRow([new Date(), mode, s.month, inv.code, inv.name, inv.number, inv.total, to, '処理中', '', '', '']);
      SpreadsheetApp.flush();
      return sh.getLastRow();
    },
    finish: (row, status, pdfName, url, memo) => {
      sh.getRange(row, 9, 1, 4).setValues([[status, pdfName || '', url || '', memo || '']]);
      SpreadsheetApp.flush();
    },
  };
}

/** 8 テストモード：宛先を自分に、件名とファイル名に【テスト】、本文の先頭に本来の宛先を書く */
function applyTestMode_(mail, s) {
  if (!s.test) return mail;
  return {
    to: s.testTo,
    subject: '【テスト】' + mail.subject,
    body: '※テスト用です。本番の宛先：' + mail.to + '\n\n' + mail.body,
    fileName: '【テスト】' + mail.fileName,
  };
}

/** メニュー① 内容を確認する：何も作らずに、作るもの・作らないものの一覧を出す */
function previewInvoices() {
  const ui = SpreadsheetApp.getUi();
  try {
    ui.alert('内容の確認（まだ何も作っていません）', summary_(plan_()), ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('止まりました', e.message, ui.ButtonSet.OK);
  }
}

/** メニュー② PDFとメールを作成する：件数を確かめてから、PDF → 下書き（または送信）→ 送付記録 */
function createInvoices() {
  const ui = SpreadsheetApp.getUi(), lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return ui.alert('ほかの実行が進んでいます。終わってから、もう一度実行してください。');
  try {
    const p = plan_(), s = p.s, count = {}, started = Date.now();
    if (!p.todo.length) return ui.alert('作るものはありません', summary_(p), ui.ButtonSet.OK);
    const title = (s.test ? '【テスト】' : '【本番】') + s.mailMode + 'で' + p.todo.length + '件を作成します。よろしいですか？';
    const warn = s.mailMode === '送信' ? '\n\nメールはすぐに送信され、取り消せません。' : '';
    if (ui.alert(title, summary_(p) + warn, ui.ButtonSet.YES_NO) !== ui.Button.YES) return ui.alert('中止しました。何も作っていません。');
    const tmp = SpreadsheetApp.create('作成中_請求書_' + s.month); // 一時ファイル（最後にゴミ箱へ移す）
    try {
      const sheet = sheet_(SHEET.layout).copyTo(tmp).setName('請求書');
      tmp.getSheets().forEach(x => { if (x.getName() !== '請求書') tmp.deleteSheet(x); });
      for (let i = 0; i < p.todo.length; i++) {
        if (i >= s.maxPerRun || Date.now() - started > TIME_LIMIT) { count['残り（もう一度②を実行すると続きから作ります）'] = p.todo.length - i; break; }
        const inv = p.todo[i];
        const mail = applyTestMode_({ to: inv.email, subject: fill_(s.subject, inv.fields), body: fill_(s.body, inv.fields),
          fileName: (inv.number + '_' + inv.name).replace(/[\\/:*?"<>|]/g, '_') + '.pdf' }, s);
        const row = p.log.start(inv, inv.email ? mail.to : '');
        let pdf = null, step = 'PDF作成';
        try {
          buildInvoiceSheet_(sheet, p.layout, inv);
          pdf = savePdf_(tmp, mail.fileName, s.folderId);
          step = 'メール作成';
          const status = inv.email ? deliverMail_(mail, pdf.blob, s) : 'メール未登録';
          p.log.finish(row, status, mail.fileName, pdf.file.getUrl());
          count[status] = (count[status] || 0) + 1;
        } catch (e) {
          p.log.finish(row, step === 'メール作成' ? '要確認' : 'エラー', pdf ? mail.fileName : '', pdf ? pdf.file.getUrl() : '', e.message);
          throw new Error(inv.code + ' の' + step + 'で止まりました：' + e.message + '\n（それより前の分は作成済みです。送付記録を確かめてください）');
        }
      }
    } finally {
      DriveApp.getFileById(tmp.getId()).setTrashed(true);
    }
    ui.alert('終わりました', Object.keys(count).map(k => k + '：' + count[k] + '件').join('\n'), ui.ButtonSet.OK);
  } catch (e) {
    ui.alert('止まりました', e.message, ui.ButtonSet.OK);
  } finally {
    lock.releaseLock();
  }
}

/** メニュー 準備：足りないシートを作る（同じ名前のシートがあれば、そのままにする） */
function setupSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet(), made = [];
  const make = (name, rows, widths) => {
    if (ss.getSheetByName(name)) return null;
    const sh = ss.insertSheet(name);
    sh.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    (widths || []).forEach((w, i) => sh.setColumnWidth(i + 1, w));
    made.push(name);
    return sh;
  };
  [[SHEET.master, ['取引先コード', '取引先名', '部署', 'メール']],
    [SHEET.details, ['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']],
    [SHEET.log, LOG_HEAD]].forEach(([name, head]) => {
    const sh = make(name, [head]);
    if (sh) { sh.setFrozenRows(1); sh.getRange(1, 1, 1, head.length).setFontWeight('bold'); }
    if (sh && name !== SHEET.master) sh.getRange(2, name === SHEET.log ? 3 : 1, 999, 1).setNumberFormat('@'); // 対象月を文字のまま残す
  });
  const st = make(SHEET.settings, [
    ['項目', '値', '説明'],
    ['対象月', '', '例：2026-11（請求明細の「対象月」がこの月の行だけを集計する）'],
    ['発行日', '', '空欄なら実行した日'],
    ['支払期限', '', '例：2026-12-31'],
    ['端数処理', '', '「切り捨て」「四捨五入」「切り上げ」のどれか（社内のルールで決める）'],
    ['発行者名', '', '請求書に載せる自社名'],
    ['発行者住所', '', ''],
    ['登録番号', '', '適格請求書発行事業者の登録番号（T＋13桁）'],
    ['振込先', '', '例：〇〇銀行 〇〇支店 普通 0000000'],
    ['備考', '', '請求書の下に載せる一文（空欄でよい）'],
    ['PDF保存フォルダID', '', 'ドライブでフォルダを開いたときのURLの「folders/」より後ろの文字'],
    ['件名', '【請求書】{{対象月}}分のご請求（{{発行者名}}）', '{{項目名}} の場所に値が入る'],
    ['本文', '{{取引先名}}\n{{部署}} ご担当者様\n\nいつもお世話になっております。{{発行者名}}です。\n{{対象月}}分の請求書をお送りします。\n\n請求書番号：{{請求書番号}}\nご請求金額：{{合計}}円（税込）\nお支払期限：{{支払期限}}\n\nご確認のほど、よろしくお願いいたします。', 'PDFは自動で添付される'],
    ['差出人名', '', 'メールの差出人に表示する名前（空欄ならGmailの設定のまま）'],
    ['送信方法', '下書き', '「下書き」か「送信」'],
    ['テストモード', 'ON', 'ONのあいだは、すべて「テスト用の宛先」に届く'],
    ['テスト用の宛先', '', 'テストのときに届く自分のメールアドレス'],
    ['1回の上限件数', 30, '1回の実行で作る最大の件数（残りは、もう一度実行すると続きから作る）'],
  ], [130, 360, 380]);
  if (st) st.getRange('B2').setNumberFormat('@');
  const cells = {
    A1: '請求書', A3: '{{取引先名}} 御中', E3: '請求書番号', F3: '{{請求書番号}}', A4: '{{部署}}', E4: '発行日', F4: '{{発行日}}',
    A6: '下記のとおりご請求申し上げます。', E6: '{{発行者名}}', A7: '件名', B7: '{{対象月}}分のご請求', E7: '{{発行者住所}}',
    A8: 'ご請求金額（税込）', B8: '{{合計}}', E8: '登録番号 {{登録番号}}', A9: 'お支払期限', B9: '{{支払期限}}', A10: 'お振込先', B10: '{{振込先}}',
    A12: '取引日', B12: '品目', C12: '税率', D12: '数量', E12: '単価', F12: '金額（税抜）',
    A13: '{{明細:取引日}}', B13: '{{明細:品目}}', C13: '{{明細:税率}}', D13: '{{明細:数量}}', E13: '{{明細:単価}}', F13: '{{明細:金額}}',
    D29: '10%対象（税抜）', F29: '{{10%対象}}', D30: '消費税（10%）', F30: '{{10%消費税}}', D31: '8%対象（税抜）', F31: '{{8%対象}}',
    D32: '消費税（8%）', F32: '{{8%消費税}}', D33: '合計（税込）', F33: '{{合計}}',
    A35: '※税率の欄に「8%※」とある品目は、軽減税率の対象です。', A36: '{{備考}}',
  };
  const grid = Array.from({ length: 36 }, () => ['', '', '', '', '', '']);
  Object.keys(cells).forEach(a => { grid[Number(a.slice(1)) - 1][a.charCodeAt(0) - 65] = cells[a]; });
  const lay = make(SHEET.layout, grid, [110, 160, 50, 50, 80, 100]);
  if (lay) {
    lay.setHiddenGridlines(true);
    lay.getRange('A1:F1').merge().setFontSize(16).setFontWeight('bold').setHorizontalAlignment('center');
    ['A3:C3', 'A4:C4', 'A6:C6', 'E6:F6', 'E7:F7', 'E8:F8', 'B10:F10', 'A35:F35', 'A36:F36'].forEach(a => lay.getRange(a).merge());
    ['D29:E29', 'D30:E30', 'D31:E31', 'D32:E32', 'D33:E33'].forEach(a => lay.getRange(a).merge());
    lay.getRange('A3').setFontSize(12).setFontWeight('bold');
    lay.getRange('B8').setFontSize(13).setFontWeight('bold').setNumberFormat('#,##0"円"');
    lay.getRange('F4').setNumberFormat('yyyy"年"m"月"d"日"');
    lay.getRange('B9').setNumberFormat('yyyy"年"m"月"d"日"');
    lay.getRange('E7').setWrap(true);
    lay.getRange('A12:F12').setFontWeight('bold').setBackground('#eeeeee');
    lay.getRange('A12:F27').setBorder(true, true, true, true, true, true);
    lay.getRange('A13:A27').setNumberFormat('yyyy/mm/dd');
    lay.getRange('B13:B27').setWrap(true).setNumberFormat('@');
    lay.getRange('D13:F27').setNumberFormat('#,##0');
    lay.getRange('D29:F33').setBorder(true, true, true, true, true, true);
    lay.getRange('F29:F33').setNumberFormat('#,##0');
    lay.getRange('D33:F33').setFontWeight('bold');
  }
  SpreadsheetApp.getUi().alert(made.length ? '作成しました：' + made.join('、') : '5枚ともあります。何も変えていません。');
}

/** 補助：設定・明細・送付記録を読んで、作るものと作らないものに分ける（ここまでは何も作らない） */
function plan_() {
  const s = loadSettings_(), agg = aggregateInvoices_(s);
  if (!agg.invoices.length) throw new Error('対象月（' + s.month + '）の明細が0件です。設定の「対象月」と、請求明細の「対象月」の列を確かめてください（まだ何も作っていません）');
  DriveApp.getFolderById(s.folderId).getName();             // フォルダIDの誤りは、作る前にここで止まる
  const layout = sheet_(SHEET.layout).getDataRange().getValues();
  linePos_(layout);
  const f = agg.invoices[0].fields;
  const left = [s.subject, s.body].concat(layout.flat()).map(v => (String(v).indexOf('{{明細:') === 0 ? '' : fill_(v, f))).join('\n').match(/\{\{[^{}]+\}\}/g);
  if (left) throw new Error('使えない差し込み項目があります：' + left.join(' ') + '\n（件名・本文・請求書レイアウトを確かめてください。使える項目：' + Object.keys(f).join('・') + '）');
  const log = deliveryLog_(s), p = { s: s, log: log, layout: layout, idle: agg.idle, todo: [], skip: [] };
  agg.invoices.forEach(inv => (log.status(inv.code) ? p.skip : p.todo).push(inv));
  return p;
}

/** 補助：確認用の一覧（件数・合計・状態） */
function summary_(p) {
  const s = p.s, out = [
    '対象月：' + s.month + '／' + (s.test ? 'テストモード（宛先はすべて ' + s.testTo + '）' : '本番') + '／' + s.mailMode,
    '作成する：' + p.todo.length + '件（合計 ' + yen_(p.todo.reduce((a, i) => a + i.total, 0)) + '円）うちメール未登録（PDFだけ作る）' + p.todo.filter(i => !i.email).length + '件',
    '記録があるため作らない：' + p.skip.length + '件' + (p.skip.length ? '（' + p.skip.map(i => i.code + ' ' + p.log.status(i.code)).join('、') + '）' : ''),
    '明細のない取引先：' + p.idle.length + '社' + (p.idle.length ? '（' + p.idle.join('、') + '）' : ''),
  ];
  if (p.skip.some(i => ['処理中', '要確認'].indexOf(p.log.status(i.code)) >= 0)) out.push('※「処理中」「要確認」は前回の実行が途中で止まった可能性があります。Gmailの下書き・送信済みとドライブのPDFを確かめてください');
  if (!s.regNo) out.push('※設定の「登録番号」が空欄です');
  out.push('----');
  p.todo.slice(0, 40).forEach(i => out.push(i.code + ' ' + i.name + '　' + yen_(i.total) + '円　' + (i.email || 'メール未登録')));
  if (p.todo.length > 40) out.push('…ほか' + (p.todo.length - 40) + '件');
  return out.join('\n');
}

/** 補助：レイアウトの明細の行（{{明細:…}}）を探し、明細欄にほかの文字がないかを確かめる */
function linePos_(layout) {
  const top = layout.findIndex(row => row.some(v => String(v).indexOf('{{明細:') === 0));
  if (top < 0) throw new Error('請求書レイアウトに {{明細:品目}} などの明細の行がありません');
  const cols = layout[top].map(v => { const m = String(v).match(/^\{\{明細:([^{}]+)\}\}$/); return m ? m[1] : ''; });
  const bad = cols.filter(k => k && LINE_KEYS.indexOf(k) < 0);
  if (bad.length) throw new Error('請求書レイアウトの明細に使えない項目があります：' + bad.join('、') + '（使えるのは ' + LINE_KEYS.join('・') + '）');
  for (let i = top + 1; i < Math.min(top + MAX_LINES, layout.length); i++) {
    if (cols.some((k, j) => k && layout[i][j] !== '')) throw new Error('請求書レイアウトの明細欄（{{明細:…}} の行から' + MAX_LINES + '行）に、ほかの文字があります（' + (i + 1) + '行目）');
  }
  return { top: top, cols: cols };
}

/** 補助：見出し（1行目）の名前で列を探して読む。列の順番が変わっても動く */
function readTable_(name, need) {
  const values = sheet_(name).getDataRange().getValues(), head = values[0].map(h => String(h).trim());
  const lost = need.filter(h => head.indexOf(h) < 0), twice = need.filter(h => head.indexOf(h) !== head.lastIndexOf(h));
  if (lost.length) throw new Error(name + 'に「' + lost.join('」「') + '」の列が見つかりません（1行目の見出しを確かめてください）');
  if (twice.length) throw new Error(name + 'に「' + twice.join('」「') + '」の列が2つ以上あります（1行目の見出しを確かめてください）');
  return values.slice(1).map((r, i) => {
    const o = { row: i + 2 };
    head.forEach((h, j) => { if (h) o[h] = r[j]; });
    return o;
  }).filter(o => need.some(h => o[h] !== '' && o[h] !== null));
}

/** 補助：消費税の端数処理（税率ごとの合計×税率を、設定の方式で1円未満を処理する。整数で計算して誤差を出さない） */
function calcTax_(base, rate, rounding) {
  const x = base * rate, q = Math.floor(x / 100), r = x - q * 100; // x は税額の100倍
  if (rounding === '切り捨て' || r === 0) return q;
  if (rounding === '切り上げ') return q + 1;
  return r >= 50 ? q + 1 : q;                                     // 四捨五入
}

/** 補助：{{項目名}} を値に置き換える（金額は3桁区切り、日付は「2026年11月30日」） */
function fill_(text, f) {
  return String(text).replace(/\{\{([^{}]+)\}\}/g, (all, k) => {
    const x = f[k];
    if (x === undefined) return all;                                // 知らない項目は残す（確認の段階で止める）
    if (isDate_(x)) return Utilities.formatDate(x, Session.getScriptTimeZone(), 'yyyy年M月d日');
    return typeof x === 'number' ? yen_(x) : String(x);
  });
}

/** 補助：値の読み替え（月・日付・税率・メール・3桁区切り）と、シートの取得 */
function toMonth_(v) {
  if (isDate_(v)) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM'); // 「2026-11」が日付に変わっていても読める
  const m = String(v === undefined || v === null ? '' : v).trim().match(/^(\d{4})\D{0,2}(\d{1,2})月?$/);
  return m && +m[2] >= 1 && +m[2] <= 12 ? m[1] + '-' + ('0' + m[2]).slice(-2) : '';
}
function toDate_(v) {
  if (isDate_(v)) return v;
  const m = String(v === undefined || v === null ? '' : v).trim().match(/^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$/);
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
}
function toRate_(v) {
  let n = Number(String(v).replace(/[%％\s]/g, ''));
  if (n > 0 && n < 1) n = n * 100;                                 // 「10%」と入れたセルは 0.1 と読まれる
  n = Math.round(n * 100) / 100;
  return n === 10 || n === 8 ? n : 0;
}
function isDate_(v) { return Object.prototype.toString.call(v) === '[object Date]' && !isNaN(v.getTime()); }
function isEmail_(t) { return String(t).split(',').every(m => /^[^@\s,]+@[^@\s,]+\.[^@\s,]+$/.test(m.trim())); }
function yen_(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function sheet_(name) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sh) throw new Error('「' + name + '」シートがありません（メニューの「準備：5枚のシートを作る」で作れます）');
  return sh;
}
```

直してよいのは、上のほうにある定数のうち、MAX_LINES（明細欄の行数）とTIME_LIMIT（止める時間）だけです。MAX_LINESを変えるときは、請求書レイアウトの明細欄の行数も合わせます。ほかの部分は、末尾の「自社用に改造する依頼文」を使って直すと、テストモードなどの安全の仕組みを崩さずに済みます。

### 初回の承認で許可する権限

初めて実行すると、Googleアカウントを選ぶ画面と、権限の一覧が出ます。自分で作ったスクリプトは、Googleの確認を受けていないため、「確認されていません」という趣旨の警告が出ることがあります。その場合は、詳細を開いてプロジェクト名が自分のものかを確かめてから進みます。勤務先のルールで認められていない場合は、ここで止めてください。

このコードが使う権限は3つです。必要な権限は、Googleのリファレンス（各メソッドの説明）に書かれています（確認日：2026-11-08）。

- Gmail（GmailApp）：メールの下書きを作るために使います。GmailAppは「https://mail.google.com/」という権限を使い、メールの閲覧・作成・送信・削除まで含む広い範囲を許可することになります
- Googleドライブ（DriveApp）：PDFを指定のフォルダに保存し、作業用の一時ファイルをゴミ箱へ移すために使います
- Googleスプレッドシート（SpreadsheetApp）：このシートを読み書きし、PDFにするための一時ファイルを作るために使います

送信専用のMailAppを使えば、Gmailの権限は「メールの送信」だけに狭められます（「https://www.googleapis.com/auth/script.send_mail」）。ただし、MailAppには下書きを作る機能がありません。このパックは「下書きで確かめてから送る」を既定にしているため、GmailAppを使っています（出典：[Class GmailApp](https://developers.google.com/apps-script/reference/gmail/gmail-app)、[Class MailApp](https://developers.google.com/apps-script/reference/mail/mail-app)。確認日：2026-11-08）。

筆者の実機確認で表示された権限の一覧は、次のとおりです。

- 【実機確認で表示された文言を記入】

許可を取り消したいときは、Googleアカウントの管理画面（セキュリティの項目）から、このスクリプトへのアクセスを削除できます。画面の名前は変わることがあります。

## ステップ3 設定シートを埋める（端数処理・件名・本文）

設定シートのB列に値を入れます。空欄や形式の誤りがあると、作る前に止まり、直す項目をまとめて表示します。

- 対象月：例 2026-11。請求明細のA列と同じ月だけを集計します
- 発行日：空欄なら実行した日になります
- 支払期限：例 2026/12/31
- 端数処理：「切り捨て」「四捨五入」「切り上げ」のどれか（次の項で説明）
- 発行者名・発行者住所・振込先・備考：請求書に載る自社の情報。備考は空欄でかまいません
- 登録番号：適格請求書発行事業者の登録番号（Tと13桁の数字）。空欄だと、確認の画面で知らせます
- PDF保存フォルダID：ドライブでフォルダを開いたときのURLの、「folders/」より後ろの文字
- 件名・本文：{{項目名}} の場所に値が入ります
- 差出人名：メールの差出人に出す名前。空欄ならGmailの設定のままです
- 送信方法・テストモード・テスト用の宛先：ステップ6までは「下書き」「ON」、自分のアドレスのままにします
- 1回の上限件数：既定は30です

### 端数処理は「請求書1枚につき税率ごとに1回」

国税庁のQ&Aでは、適格請求書に書く消費税額に1円未満の端数が出る場合、端数の処理は「一の適格請求書につき、税率ごとに1回」と説明されています。切上げ・切捨て・四捨五入のどれにするかは任意とされ、商品ごとに端数を処理して合計する方法は認められないとされています（出典：[国税庁「適格請求書に記載する消費税額等の端数処理」（Q&A 問57）](https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/pdf/qa/57.pdf)、確認日：2026-11-08）。

このコードは、取引先ごとに10%と8%の対象額を合計し、それぞれに税率をかけてから、設定の方式で1回だけ端数を処理します。どの方式にするかは、社内のルールで決めてください。テストでは、架空28社分の請求額の合計が、切り捨てで3,654,641円、四捨五入で3,654,659円、切り上げで3,654,676円になりました。方式によって請求額が変わるので、途中で変えないことも大切です。

### 件名・本文に使える差し込み項目

件名・本文・請求書レイアウトでは、次の項目を {{ }} で囲んで使えます。知らない項目名があると、作る前に止まって知らせます。

```
{{取引先コード}} {{取引先名}} {{部署}} {{請求書番号}} {{対象月}}
{{発行日}} {{支払期限}} {{発行者名}} {{発行者住所}} {{登録番号}}
{{振込先}} {{備考}} {{10%対象}} {{10%消費税}} {{8%対象}} {{8%消費税}}
{{税抜合計}} {{消費税合計}} {{合計}}
```

金額は「53,949」のように3桁で区切り、日付は「2026年12月31日」の形で入ります。準備メニューで入る本文の例は次のとおりです。送付の文面を自社用に整えたいときは、請求書の送付メールの文例の記事（［リンク：108の記事］）も参考にしてください。

```
{{取引先名}}
{{部署}} ご担当者様

いつもお世話になっております。{{発行者名}}です。
{{対象月}}分の請求書をお送りします。

請求書番号：{{請求書番号}}
ご請求金額：{{合計}}円（税込）
お支払期限：{{支払期限}}

ご確認のほど、よろしくお願いいたします。
```

## ステップ4 テストモードで架空データを流す

本番のデータを入れる前に、架空の3社で一通り動かします。会社名とアドレスはすべて架空です。

### テスト用のデータを貼る

取引先マスタのA2を選んで、次の3行を貼ります。続けて、A列を選んだまま「データ」→「テキストを列に分割」を選び、区切り文字を「カンマ」にします。

```
C-001,株式会社サンプル商事,経理部,sample-shoji@example.com
C-002,サンプル工業株式会社,総務部,sample-kogyo@example.com
C-003,株式会社見本デザイン,,
```

請求明細のA2にも、同じ手順で次の8行を貼ります。最後の行は前月分で、集計に入らないことを確かめるための行です。

```
2026-11,2026/11/05,C-001,,P-01,月額保守サービス,1,33000,10%,
2026-11,2026/11/12,C-001,,P-02,作業費（1時間）,3,4500,10%,
2026-11,2026/11/19,C-001,,P-05,コーヒー豆（軽減税率）,2,1296,8%,
2026-11,2026/11/06,C-002,,P-03,名刺印刷（100枚）,2,1650,10%,
2026-11,2026/11/06,C-002,,P-04,送料,1,980,10%,
2026-11,2026/11/20,C-002,,P-06,お弁当（軽減税率）,5,864,8%,
2026-11,2026/11/25,C-003,,P-07,消耗品,3,1234,10%,
2026-10,2026/10/30,C-001,,P-02,前月分の作業費（集計に入らない）,1,9999,10%,
```

設定シートには、対象月「2026-11」、支払期限「2026/12/31」、端数処理「切り捨て」、発行者名「株式会社見本サービス」、登録番号「T0000000000000」（架空）、PDF保存フォルダID、テスト用の宛先（自分のアドレス）を入れます。

### 期待する結果

端数処理を「切り捨て」にしたときの結果です。テスト用の仕組みで、この値になることを確かめています。

- C-001 株式会社サンプル商事：10%対象 46,500円、消費税 4,650円、8%対象 2,592円、消費税 207円、合計 53,949円
- C-002 サンプル工業株式会社：10%対象 4,280円、消費税 428円、8%対象 4,320円、消費税 345円、合計 9,373円
- C-003 株式会社見本デザイン：10%対象 3,702円、消費税 370円、合計 4,072円（メール未登録なので、PDFだけを作る）
- 3社の合計：67,394円（四捨五入なら67,395円、切り上げなら67,397円）

### 導入時の確認チェックリスト

1. 「①内容を確認する」で「作成する：3件（合計 67,394円）うちメール未登録（PDFだけ作る）1件」と出る。この時点では何も増えていない
2. 「②PDFとメールを作成する」で「【テスト】下書きで3件を作成します。よろしいですか？」と出る
3. 「はい」のあと、「下書き済み：2件」「メール未登録：1件」と出る
4. ドライブのフォルダに、【テスト】で始まるPDFが3つできている
5. PDFを開くと、A4の1ページに収まり、{{ }} のままの箇所がない。C-001の合計が53,949円、コーヒー豆の税率が「8%※」
6. Gmailの下書きが2通。宛先は自分で、件名は【テスト】で始まり、本文の1行目に本番の宛先が書いてある。PDFが添付されている
7. 送付記録に3行。モードは「テスト」、状態は「下書き済み」が2行と「メール未登録」が1行
8. もう一度「②」を実行すると、「作るものはありません」と出て、PDFも下書きも増えない
9. マイドライブに「作成中_請求書_2026-11」が残っていない（ゴミ箱に移っている）

テストが終わったら、テストの下書きとPDFを消します。送付記録のテストの行は、本番の作成を止めないので、残しておいてもかまいません。

## ステップ5 請求書PDFを作る

「②PDFとメールを作成する」を押すと、コードは次の順に動きます。

1. マイドライブに一時ファイル（作成中_請求書_対象月）を作り、請求書レイアウトのシートをコピーする
2. 取引先ごとに、{{項目名}} の場所へ値を入れ、明細を取引日の順に並べる
3. 一時ファイルをPDFにして、設定のフォルダに「INV-202611-C-001_株式会社サンプル商事.pdf」のような名前で保存する
4. 全社が終わったら、一時ファイルをゴミ箱へ移す（ゴミ箱のファイルは、30日たつとドライブから消えます）

PDFは、Googleのリファレンスに載っているメソッド（ファイルをPDFの形式で取り出す機能）だけで作っています。

### レイアウトを自社用に直すときの決まり

- 文字の大きさ、罫線、列の幅、ロゴ以外の文言は自由に変えてかまいません
- {{項目名}} は、セルを動かしても、その位置に値が入ります
- 明細の行（{{明細:…}}）から下の15行は、明細の列に何も書かないでください。書くと止まります
- 数式は入れないでください。一時ファイルにコピーするため、ほかのシートを参照する数式は壊れます
- 1ページに収まっているかは、テストのPDFで確かめます

### 用紙の大きさについて

この方法では、用紙の大きさや余白を、コードから指定できません。筆者の実機確認では【用紙の大きさと、1ページに収まったかを記入】。

A4にならない場合は、スプレッドシートの「ファイル」→「ダウンロード」→「PDF」で、用紙を選んで手で出す方法があります。スプレッドシートの書き出し用のURLを使えばコードから用紙を指定できますが、公式ドキュメントに載っていない使い方で、予告なく変わることがあります。外部への接続の権限も増えるため、このパックのコードには入れていません。

### 記載項目のチェックリスト（国税庁の資料をもとに）

国税庁のタックスアンサー「No.6625 適格請求書等の記載事項」（確認日：2026-11-08）では、適格請求書の記載事項として次の6つが挙がっています。右の矢印は、このパックのレイアウトで対応する欄です。

1. 適格請求書発行事業者の氏名または名称と、登録番号 → {{発行者名}}、登録番号 {{登録番号}}
2. 取引年月日 → 明細の取引日
3. 取引内容（軽減税率の対象品目である場合はその旨）→ 明細の品目と、税率の「8%※」、A35の注記
4. 税率ごとに区分して合計した対価の額と、適用税率 → 10%対象・8%対象と、明細の税率
5. 税率ごとに区分した消費税額等 → 消費税（10%）・消費税（8%）
6. 書類の交付を受ける事業者の氏名または名称 → {{取引先名}} 御中

欄があることと、自社の請求書が要件を満たすことは別の話です。登録番号の正しさ、品目の書き方、値引きや返品の扱いなどは、社内の経理責任者や税理士に確かめてください（出典：[国税庁 No.6625](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shohi/6625.htm)）。

## ステップ6 メールの下書きを作り、確かめて送る

テストが終わったら、設定の「テストモード」を「OFF」にします。送信方法は「下書き」のままです。「①内容を確認する」で件数と合計を確かめてから、「②」を実行します。

下書きは、Gmailの「下書き」に1社1通ずつできます。送る前に、次の4点を1通ずつ見ます。

- 宛先：取引先マスタのアドレスと同じか
- 件名と本文：取引先名、対象月、金額、支払期限が正しいか
- 添付：PDFが1つ付いていて、開くと宛名と金額が本文と同じか
- 送信の前の最終確認：ほかの取引先のPDFが付いていないか

確かめた下書きから、Gmailの送信ボタンで送ります。送付記録の状態は「下書き済み」のままなので、送った日をメモ欄に書いておくと、あとで探しやすくなります。

### 「送信」に切り替える場合

下書きでの運用に慣れて、毎月の内容が安定してから切り替えます。

1. 設定の「送信方法」を「送信」にする
2. 「①内容を確認する」で、件数と宛先の一覧を確かめる
3. 「②」を実行すると、「【本番】送信で◯件を作成します」「メールはすぐに送信され、取り消せません」と出る。件数が正しければ「はい」
4. 送付記録の状態が「送信済み」になる

送信では、1日の受信者数の上限（個人100人、Workspace 1,500人）に数えられます。テストで送った分も数えられるので、同じ日にテストと本番をくり返さないようにします。

## ステップ7 毎月の運用（締め日から送付記録まで）

毎月の作業は次の8つです。引き継ぎ書の雛形にも、同じ手順を入れています。

1. 締め日の翌日：請求明細に当月分を入れる（対象月の列に「2026-12」のように入れる）
2. 設定の「対象月」と「支払期限」を、その月の値に書き換える
3. 「①内容を確認する」で、件数・合計・メール未登録・明細のない取引先を確かめる
4. 明細のない取引先が、本当に請求のない取引先かを確かめる（入れ忘れに気づける）
5. 「②PDFとメールを作成する」を実行する。「残り」と出たら、もう一度実行する
6. 下書きを1通ずつ確かめて送る（ステップ6）
7. メール未登録の取引先は、PDFを郵送やほかの方法で届ける（このパックの範囲外）
8. 送付記録で、全社が「下書き済み」か「送信済み」になったかを確かめる

### 請求書を作り直すとき

明細の誤りを直して作り直すときは、次の順にします。

1. Gmailの古い下書きと、ドライブの古いPDFを消す（送ってしまった場合は、取引先への連絡を先にする）
2. 送付記録のその取引先の行の「状態」を「取消」に書き換える
3. 「②」を実行すると、その取引先だけを作り直す

「処理中」「要確認」の行は、前回の実行が途中で止まったことを表します。Gmailの下書きと送信済み、ドライブのPDFを確かめてから「取消」にします。

## エラー対処表

止まったときは、画面に出た文言で探します。

1. メニューに「請求書」が出ない → コードを保存していないか、再読み込みをしていない → 保存してから、スプレッドシートを再読み込みする。出ないときは、Apps Scriptの画面で関数「onOpen」を選んで実行する
2. 「設定シートを直してください」→ 設定に空欄や形式の誤りがある → 表示された項目を直す（端数処理の空欄が多い）
3. 「対象月（2026-11）の明細が0件です」→ 設定と請求明細で対象月が違う → 請求明細のA列が「2026-11」の形か確かめる。日付に変わっていても読めるが、年や月の誤りは読めない
4. 「取引先コード「C-012」が取引先マスタにありません」→ 入力の誤りか、マスタへの登録漏れ → コードの前後の空白、全角と半角のハイフンを確かめる
5. 「数量と単価は数値で入れてください」→ 「3個」のような文字や、数値に見える文字が入っている → 数値だけにする。CSVから貼った列は、文字になっていることがある
6. 「税率は10%か8%にしてください」→ 「5%」や空欄 → 10%か8%に直す。非課税の項目は、このパックでは扱えない
7. 「金額（数量×単価）に1円未満の端数があります」→ 単価や数量に小数がある → 金額が1円単位になるように、社内で単価を決め直す
8. 「明細が16行あります（請求書レイアウトの明細欄は15行まで）」→ 1社の明細がレイアウトに入らない → 明細をまとめるか、定数MAX_LINESとレイアウトの明細欄を同じ行数だけ増やす（PDFが1ページに収まるかも確かめる）
9. 「「メール」の列が見つかりません」「列が2つ以上あります」→ 1行目の見出しの名前が違う、または同じ見出しが2つある → ひな形と同じ見出しにする
10. 「使えない差し込み項目があります：{{担当者名}}」→ {{ }} の中の名前の誤り、または使えない項目 → 表示された「使える項目」から選ぶ。新しい項目を足すときは、改造の依頼文を使う
11. 「請求書レイアウトの明細欄…ほかの文字があります」→ 明細欄に「小計」などを書いた → 明細欄の外へ動かす
12. 「送付記録の1行目の見出しが変わっています」→ 送付記録の列を動かした → ひな形の順番に戻す
13. 「ほかの実行が進んでいます」→ メニューを続けて押した → 1つ目の実行が終わってから、送付記録を見て、必要なら実行する
14. 「C-003 のPDF作成で止まりました」→ フォルダIDの誤り、フォルダへの権限がない、ドライブの容量不足 → 原因を直して「②」を実行する（状態が「エラー」の取引先は作り直す）
15. 「C-003 のメール作成で止まりました」→ Gmailの一時的なエラーなど。状態は「要確認」になる → Gmailの下書きと送信済みを確かめ、できていなければ状態を「取消」にして「②」を実行する
16. 送信で「上限」や「too many」を含むエラーが出る → 1日の受信者数などの上限に達した → 24時間ほど待つ。急ぐ分は下書きで作り、手で送る

このほか、発行日などが1日ずれるときは、ステップ2のタイムゾーンを確かめます。マイドライブに「作成中_請求書_…」が残っているときは、実行が途中で止まっています。ゴミ箱へ移してから、送付記録を確かめてください。エラーの意味が分からないときは、表示をそのままAIに聞く方法も使えます（Excel・スプレッドシートのエラーをAIに聞く記事を準備しています。公開後にリンクを追記します）。

## 引き継ぎ書の雛形

担当が替わっても毎月回るように、次の雛形を埋めて、スプレッドシートと同じフォルダに置いておきます。

```
【請求書PDF・メール下書きの引き継ぎ書】
最終更新：　　年　月　日／作成者：

1. この仕組みでやること
・毎月、請求明細から取引先ごとの請求書PDFとメールの下書きを作る
・送るのは、下書きを確かめた人（担当：　　　　）

2. 使うもの
・スプレッドシート：（名前・場所）
・PDFの保存フォルダ：（名前・場所）
・スクリプトを承認したアカウント：（アカウント名）
・コードの版：v1.0（改造した場合は、その内容と日付）

3. 毎月の手順（締め日：毎月　日）
①請求明細に当月分を入れる（入力の担当：　　　　）
②設定の「対象月」「支払期限」を書き換える
③メニュー「①内容を確認する」で件数・合計を確かめる
④メニュー「②PDFとメールを作成する」を実行する
⑤下書きを1通ずつ確かめて送る（確認の担当：　　　　）
⑥メール未登録の取引先に、別の方法で届ける
⑦送付記録で全社がそろったか確かめる

4. 変えてはいけないところ
・シート名、1行目の見出し、送付記録の列の順番
・設定の「テストモード」「送信方法」（変えるときは上長に相談）
・請求書レイアウトの明細欄（15行）

5. 困ったとき
・エラー対処表：（記事・資料の場所）
・相談先：（社内の担当者）
・税務の判断（端数処理・記載内容）：（経理責任者・税理士）

6. 担当が替わるときにやること
・新しい担当のアカウントで、スクリプトを承認し直す
・下書きは、実行した人のGmailにできる。送る人と実行する人を決める
・PDFの保存フォルダを、新しい担当と共有する
・前の担当のアカウントの承認を取り消すか、管理者に確かめる
```

スクリプトは、承認した人のアカウントの権限で動きます。下書きも、実行した人のGmailにできます。担当が替わるときは、6の項目を前任者と一緒に確かめてください。

## 自社用に改造する依頼文3本

列を足したい、CCを付けたいといった変更は、AIに依頼文を渡して直してもらえます。使う前に、次の3点を守ってください。

- AIに貼るのは、コードと依頼文だけにします。取引先名・金額・アドレスなどの実データは貼りません（コードには実データは入っていません）
- 勤務先の生成AIの利用ルールを確かめ、認められたAIを使います
- 直す前に、今のコードを全文コピーして、テキストファイルに保存しておきます

依頼文は、3本とも次の形です。【やりたいこと】の部分だけが違います。最後の「（ここに…）」の位置に、Code.gsの全文を貼ります。

### 依頼文1：列を足す（請求明細に注文番号を足して、明細に表示する）

```
次のGoogle Apps Script（スプレッドシートの請求明細から、取引先ごとの請求書PDFとメールの下書きを作るコード）を、自社の運用に合わせて直してください。

【やりたいこと】
請求明細に「注文番号」の列を足して、請求書の明細の欄に注文番号も表示したい。
- 請求明細の見出しは「注文番号」。空欄の行があってもよい（空欄なら何も表示しない）
- 請求書レイアウトでは {{明細:注文番号}} と書いた列に表示したい

【守ること】
- テストモード（宛先をすべて自分にする仕組み）、メールは下書きが既定であること、送付記録による二重作成の防止は、今と同じに動くようにする
- 変更は必要な関数と定数だけにし、ほかは変えない
- 日本語の短い説明を付ける

【出してほしいもの】
1. 変更した関数・定数の全文（そのまま置き換えられる形）
2. スプレッドシート側で必要な作業（列の追加、レイアウトへの差し込みなど）
3. 変更後にテストモードで確かめる手順

【コード】
（ここにCode.gsの全文を貼る）
```

### 依頼文2：CCを付ける（本番だけCCに入れ、記録に残す）

```
次のGoogle Apps Script（スプレッドシートの請求明細から、取引先ごとの請求書PDFとメールの下書きを作るコード）を、自社の運用に合わせて直してください。

【やりたいこと】
取引先マスタに「CC」の列を足し、空欄でなければ、そのアドレスをメールのCCに入れたい。
- CCは複数のとき「,」で区切って入れる
- テストモードのときは、CCを付けない（テスト用の宛先だけに届くようにする）
- 送付記録のメモ欄に、本番でCCに入れたアドレスを残したい

【守ること】
- テストモード（宛先をすべて自分にする仕組み）、メールは下書きが既定であること、送付記録による二重作成の防止は、今と同じに動くようにする
- 変更は必要な関数と定数だけにし、ほかは変えない
- 日本語の短い説明を付ける

【出してほしいもの】
1. 変更した関数・定数の全文（そのまま置き換えられる形）
2. スプレッドシート側で必要な作業（列の追加、レイアウトへの差し込みなど）
3. 変更後にテストモードで確かめる手順

【コード】
（ここにCode.gsの全文を貼る）
```

### 依頼文3：文面を変える（取引先ごとの一言を本文に足す）

```
次のGoogle Apps Script（スプレッドシートの請求明細から、取引先ごとの請求書PDFとメールの下書きを作るコード）を、自社の運用に合わせて直してください。

【やりたいこと】
取引先ごとに、メール本文の最後に一言を足したい。
- 取引先マスタに「ひとこと」の列を足し、本文の {{ひとこと}} の場所に差し込む
- 空欄の取引先では何も入れない（{{ひとこと}} の行だけが空になる）
- 件名には使わない

【守ること】
- テストモード（宛先をすべて自分にする仕組み）、メールは下書きが既定であること、送付記録による二重作成の防止は、今と同じに動くようにする
- 変更は必要な関数と定数だけにし、ほかは変えない
- 日本語の短い説明を付ける

【出してほしいもの】
1. 変更した関数・定数の全文（そのまま置き換えられる形）
2. スプレッドシート側で必要な作業（列の追加、レイアウトへの差し込みなど）
3. 変更後にテストモードで確かめる手順

【コード】
（ここにCode.gsの全文を貼る）
```

### 実行して確かめたこと

3本の依頼文を、コード全文を付けてClaudeで実行しました（2026-11-08。依頼文2と3は2回ずつ、計5回）。出力された関数をコードに当てはめ、テスト用の仕組みで動かしたところ、5回とも次のようになりました。

- 頼んだ変更が動いた（注文番号が明細に出る、本番だけCCが付く、一言が本文に入る）
- テストモード、下書きが既定であること、同じ月の二重作成の防止は、元のまま動いた
- 足した列は、なくてはならない列として扱われ、列がないと作る前に止まる作りになった（依頼文には書いていない判断です）

一方で、変える関数の数は回によって違いました（依頼文3は、1回目が3つ、2回目が4つ）。次は、依頼文2の出力に含まれていた関数の一部です。テストモードのときにCCを付けない処理が入っています。出力例はClaudeで生成しています。AIの出力は毎回少しずつ変わります。

```
function deliverMail_(mail, blob, s) {
  const options = { attachments: [blob] };
  if (s.senderName) options.name = s.senderName;
  if (mail.cc && !s.test) options.cc = mail.cc;            // ★ テストモードではCCを付けない（applyTestMode_ と二重の歯止め）
  if (s.mailMode === '送信') {
    GmailApp.sendEmail(mail.to, mail.subject, mail.body, options);
    return '送信済み';
  }
  GmailApp.createDraft(mail.to, mail.subject, mail.body, options);
  return '下書き済み';
}
```

### 出力を当てはめたあとに確かめること

1. Apps Scriptの画面で、出力と同じ名前の関数を、説明の行（/** で始まる行）から最後の } まで選び、出力の関数に置き換える。定数は1行ごと置き換える
2. 出力の「スプレッドシート側で必要な作業」をする（列の追加など）
3. テストモードのまま、ステップ4の手順を最初からやり直す。CCを足した場合は、下書きにCCが付いていないことも確かめる
4. 動かないときは、エラーの文言と、置き換えた関数をAIに渡して直してもらう。直らないときは、保存しておいた元のコードに戻す

ChatGPTやGeminiなど、ほかの生成AIでも同じ形で依頼できます。ただし、筆者が動作を確かめたのはClaudeの出力だけです。

## 改訂履歴

- 2026-11-08 v1.0：初版（公開日：【記入】）

## まとめと関連記事

このパックで、締めのあとの「写す・PDFにする・添付する」作業を、請求明細の入力と、メニュー2回、下書きの確認に置き換えられます。最初はテストモードと下書きで動かし、送付記録を見ながら毎月の手順に慣れてください。

- 仕組みの考え方と最小のコード：「スプレッドシートで請求書を自動作成する仕組みの全体像」（［リンク：107の記事］）
- 送付・入金確認のメールの文面：「請求書の送付・入金確認メール文例」（［リンク：108の記事］）
- AIに入れてはいけない情報と置き換え方：「生成AIに入力してはいけない情報と、マスキングのやり方」（［リンク：106の記事］）
- 事務のほかの場面の依頼文：「事務のAI依頼文20場面」（［リンク：201の記事］）
- 取引先マスタから値を引く数式の頼み方、エラーをAIに聞く方法：それぞれの記事の公開後に、ここにリンクを追記します

---
この記事は、生成AIで下書きと出力例を作成し、内容と動作を筆者が確認・編集して公開しています（最終確認日：2026-11-08）。AIの出力やツールの画面は、今後のアップデートで変わることがあります。
本記事は情報提供を目的としており、成果を保証するものではありません。社内での利用は、勤務先のルールに従ってください。
ChatGPTはOpenAI、ClaudeはAnthropic、Gemini・Gmail・Googleスプレッドシート・Googleドライブ・Google Workspace・Google Apps ScriptはGoogle、ExcelはMicrosoftの商標または登録商標です。本記事は各社とは関係ありません。

<!-- 変更理由: (1) コード全文（約2.1万字）を載せたため、全体の字数が企画書の目標（1.8〜2.2万字）を超えた。コードを短くするより、止まったときの日本語の表示、作る前の入力チェック、シートを自動で作る準備の関数を優先した。(2) コードの関数は企画書の8関数に、メニューから呼ぶ関数3つ（確認・作成・準備）と補助の関数13個を加えた（全24個）。8つの役割はそのまま。(3) エラー対処表は16項目（企画書は12項目以上）。(4) 記載項目のチェックリストはステップ5の中に、導入時の確認チェックリストはステップ4の中に置いた。(5) 見出しに「まとめと関連記事」を足した（writing-format-spec の有料記事の構成8）。(6) 105・103へのリンクは、両記事の公開後（12/8・12/10）に追記する（editorial-plan §3）。107・108・106・201は202より先に公開されるため、［リンク：…］の位置にURLを入れる。(7) 用紙の大きさは公開されているメソッドでは指定できないため、書き出しURLの方法は説明だけにし、コードには入れていない（企画書§6）。 -->
<!-- 公開前の確認（オーナー）: verification/202/device-check.md の手順で実機確認をして、冒頭の「動作確認日」「確認環境」、検証情報の実機確認日、FAQ1の【個人／Workspace】、ステップ2の権限の一覧、ステップ5の用紙の大きさ、改訂履歴の公開日を書き換える。［リンク：107の記事］などをURLに差し替える。noteの返金設定は「許可しない」、購入者限定コメントを有効にする。 -->

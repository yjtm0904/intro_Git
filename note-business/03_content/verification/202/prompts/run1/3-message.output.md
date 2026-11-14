# 取引先ごとの「ひとこと」をメール本文に差し込む変更

## 変更の考え方

- 取引先マスタの「ひとこと」を読み、差し込み項目に `{{ひとこと}}` を足します。空欄なら空の文字が入るので、その行だけが空になります。
- `{{ひとこと}}` は本文だけで使えます。件名や請求書レイアウトに書くと、①の確認の段階で「使えない差し込み項目」として止まります。
- 「ひとこと」の列は必須にします。列名の打ち間違い（例：「一言」）に気づかず、ひとことが黙って抜けるのを防ぐためです。
- テストモード、下書きの既定、送付記録による二重作成の防止は、関数に手を入れていないので今と同じに動きます（`createInvoices`、`applyTestMode_`、`deliverMail_`、`deliveryLog_`）。

変更するのは **`aggregateInvoices_`・`plan_`・`setupSheets`** の3つです。定数の変更はありません。

---

## 1. 変更した関数の全文

### `aggregateInvoices_`
変更点は次の3つです（★の行）。
- マスタの読み込みに「ひとこと」を追加
- 「{{」「}}」を含むひとことはエラーにする
- 差し込み項目に「ひとこと」を追加

```javascript
/** 3 明細の集計：対象月の明細を取引先ごと・税率ごとに合計する。消費税の端数処理は請求書1枚につき税率ごとに1回 */
function aggregateInvoices_(s) {
  const clients = {}, groups = {}, e = [];
  readTable_(SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'ひとこと']).forEach(r => { // ★「ひとこと」の列を読む（列がなければ止まる）
    const c = { code: String(r['取引先コード']).trim(), name: String(r['取引先名']).trim(), dept: String(r['部署']).trim(), email: String(r['メール']).trim(),
      comment: String(r['ひとこと']).trim() };                                                         // ★空欄なら ''（本文の {{ひとこと}} が空になる）
    if (!c.code) return e.push('取引先マスタ ' + r.row + '行目：取引先コードが空欄です');
    if (clients[c.code]) e.push('取引先マスタ ' + r.row + '行目：取引先コード「' + c.code + '」が重複しています');
    if (c.email && !isEmail_(c.email)) e.push('取引先マスタ ' + r.row + '行目：メールアドレスの形式を確かめてください');
    if (/\{\{|\}\}/.test(c.comment)) e.push('取引先マスタ ' + r.row + '行目：ひとことに「{{」「}}」は使えません'); // ★差し込みの記号と取り違えないように
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
      'ひとこと': c.comment,                                   // ★本文だけで使う（件名・レイアウトに書くと plan_ で止める）
    };
    return inv;
  });
  if (e.length) throw new Error('データを直してください（まだ何も作っていません）。\n・' + e.slice(0, 15).join('\n・') + (e.length > 15 ? '\n…ほか' + (e.length - 15) + '件' : ''));
  return { invoices: invoices, idle: Object.keys(clients).filter(code => !groups[code]) };
}
```

### `plan_`
件名とレイアウトは「ひとこと」を除いた項目で確かめ、本文だけ「ひとこと」込みで確かめます（★の行）。

```javascript
/** 補助：設定・明細・送付記録を読んで、作るものと作らないものに分ける（ここまでは何も作らない） */
function plan_() {
  const s = loadSettings_(), agg = aggregateInvoices_(s);
  if (!agg.invoices.length) throw new Error('対象月（' + s.month + '）の明細が0件です。設定の「対象月」と、請求明細の「対象月」の列を確かめてください（まだ何も作っていません）');
  DriveApp.getFolderById(s.folderId).getName();             // フォルダIDの誤りは、作る前にここで止まる
  const layout = sheet_(SHEET.layout).getDataRange().getValues();
  linePos_(layout);
  const f = agg.invoices[0].fields, g = Object.assign({}, f);
  delete g['ひとこと'];                                      // ★件名・レイアウトでは {{ひとこと}} を使わない
  const left = [s.subject].concat(layout.flat()).map(v => (String(v).indexOf('{{明細:') === 0 ? '' : fill_(v, g)))
    .concat(fill_(s.body, f)).join('\n').match(/\{\{[^{}]+\}\}/g); // ★本文だけ {{ひとこと}} を使える
  if (left) throw new Error('使えない差し込み項目があります：' + left.join(' ') + '\n（件名・本文・請求書レイアウトを確かめてください。使える項目：' + Object.keys(g).join('・') + '。{{ひとこと}} は本文だけで使えます）');
  const log = deliveryLog_(s), p = { s: s, log: log, layout: layout, idle: agg.idle, todo: [], skip: [] };
  agg.invoices.forEach(inv => (log.status(inv.code) ? p.skip : p.todo).push(inv));
  return p;
}
```

### `setupSheets`
新しく準備するときも「ひとこと」の列ができるように、取引先マスタの見出しだけを変えました（★の行）。ほかは元のままです。

```javascript
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
  [[SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'ひとこと']], // ★「ひとこと」を追加
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
```

---

## 2. スプレッドシート側で必要な作業

1. **取引先マスタに列を追加する**
   - 1行目の見出しに「ひとこと」と入れます。場所は空いている列ならどこでもかまいません（見出しの名前で探すため）。
   - 「一言」「ひとこと 」（後ろに空白）などでは見つかりません。列がないまま①を実行すると「取引先マスタに「ひとこと」の列が見つかりません」と出て止まります。これは意図した動きです。**コードを置き換える前に列を足しておく**と、運用が途切れません。
   - 一言がない取引先は空欄のままでかまいません。セル内の改行（Ctrl+Enter／⌘+Enter）は、そのまま本文の改行になります。前後の空白は取り除かれます。
2. **設定シートの「本文」に `{{ひとこと}}` を入れる**
   - 本文の最後に1行足します。例：
     ```
     ご確認のほど、よろしくお願いいたします。

     {{ひとこと}}
     ```
   - 空欄の取引先では、この行が空になります。本文の最後が空行になるだけなので、見た目の問題はほぼありません。
3. **件名と請求書レイアウトには何もしません**
   - どちらかに `{{ひとこと}}` を書くと、①で「使えない差し込み項目があります」と出て止まります。

---

## 3. 変更後にテストモードで確かめる手順

**準備**
1. 設定シートを次のようにします。
   - テストモード：`ON`
   - 送信方法：`下書き`
   - テスト用の宛先：自分のアドレス
2. 取引先マスタで、テスト対象の月に明細がある取引先のうち、1社は「ひとこと」を入力し、もう1社は空欄にします。改行入りのひとことも1社あると確実です。
3. 同じ対象月で以前にテストしたことがある場合は、送付記録に**モードが「テスト」の行**が残っていて、作成がスキップされます。その行だけを削除してください。**「本番」の行は消さないでください。**

**確認**
4. **①内容を確認する**を実行します。
   - 「テストモード（宛先はすべて 自分のアドレス）／下書き」と表示され、作成件数が想定どおりであることを確かめます。
5. **止まることの確認**（任意ですが、おすすめします）
   - 件名に `{{ひとこと}}` を一時的に足して①を実行し、「使えない差し込み項目」で止まることを確かめます。確かめたら元に戻します。
   - 取引先マスタの見出しを一時的に「一言」に変えて①を実行し、列が見つからないと出て止まることを確かめます。確かめたら元に戻します。
6. **②PDFとメールを作成する**を実行し、確認画面のタイトルが「【テスト】下書きで…」になっていることを確かめてから「はい」を押します。
7. Gmailの下書きを開いて、次の点を確かめます。
   - 宛先が自分で、件名の先頭に「【テスト】」がある
   - 本文の先頭に「※テスト用です。本番の宛先：…」とある
   - 入力した取引先では、本文の最後にひとことが入っている（改行も反映されている）
   - 空欄の取引先では、その行が空になっていて、`{{ひとこと}}` の文字が残っていない
   - 件名にひとことが入っていない
   - 添付のPDFが今までどおりで、ひとことが載っていない
8. 送付記録で、モードが「テスト」、状態が「下書き済み」になっていることを確かめます。
9. もう一度②を実行し、「作るものはありません」となり「記録があるため作らない」に並ぶことを確かめます（二重作成の防止）。

**後片付け**
10. テストの下書きを削除し、保存フォルダの「【テスト】」付きPDFを削除します。送付記録の「テスト」行は、残しても本番の作成には影響しません。
11. 本番に切り替えるときは、テストモードを `OFF` にしてから①で内容を確かめ、②を実行します。送信方法は `下書き` のままにしておくと、送る前に下書きを目で確かめられます。
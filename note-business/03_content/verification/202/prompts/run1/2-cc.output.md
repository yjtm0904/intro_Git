# CC列への対応

## 変更の概要

- **取引先マスタの読み込み**（`aggregateInvoices_`）：「CC」列を読みます。前後の空白と空の要素は取り除き、「,」区切りの形にそろえます。そのうえで形式を確かめます。CCがあってメールが空欄の行は、入力ミスとして止めます。
- **テストモード**（`applyTestMode_`）：CCを空にします。その代わりに、テストメールの本文の先頭に「本番のCC」を書きます。
- **メール作成**（`deliverMail_`）：本番でCCがあるときだけ `cc` を付けます。テストモードでは、念のためここでもCCを付けません。
- **送付記録**（`createInvoices`）：本番でCCを付けたとき、メモ欄に「CC：…」を残します。
- **準備**（`setupSheets`）：これから作る取引先マスタの見出しに「CC」を足します。

テストモード、下書きが既定であること、送付記録による二重作成の防止は変えていません。ほかの関数と定数もそのままです。

---

## 1. 変更した関数（そのまま置き換えてください）

### `aggregateInvoices_`（3 明細の集計）

```javascript
/** 3 明細の集計：対象月の明細を取引先ごと・税率ごとに合計する。消費税の端数処理は請求書1枚につき税率ごとに1回 */
function aggregateInvoices_(s) {
  const clients = {}, groups = {}, e = [];
  readTable_(SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'CC']).forEach(r => {
    const c = { code: String(r['取引先コード']).trim(), name: String(r['取引先名']).trim(), dept: String(r['部署']).trim(), email: String(r['メール']).trim(),
      cc: String(r['CC'] === undefined || r['CC'] === null ? '' : r['CC']).split(',').map(m => m.trim()).filter(m => m).join(',') }; // CCは「,」区切りにそろえる
    if (!c.code) return e.push('取引先マスタ ' + r.row + '行目：取引先コードが空欄です');
    if (clients[c.code]) e.push('取引先マスタ ' + r.row + '行目：取引先コード「' + c.code + '」が重複しています');
    if (c.email && !isEmail_(c.email)) e.push('取引先マスタ ' + r.row + '行目：メールアドレスの形式を確かめてください');
    if (c.cc && !isEmail_(c.cc)) e.push('取引先マスタ ' + r.row + '行目：CCのメールアドレスの形式を確かめてください（複数のときは半角の「,」で区切る）');
    if (c.cc && !c.email) e.push('取引先マスタ ' + r.row + '行目：CCが入っていますが、メールが空欄です');
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
    const inv = { code: code, name: c.name, dept: c.dept, email: c.email, cc: c.cc, number: 'INV-' + s.month.replace('-', '') + '-' + code,
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
```

### `deliverMail_`（6 下書き作成・送信）

```javascript
/** 6 下書き作成・送信：既定は下書き。設定の送信方法が「送信」のときだけ送る。CCは本番でだけ付ける */
function deliverMail_(mail, blob, s) {
  const options = { attachments: [blob] };
  if (s.senderName) options.name = s.senderName;
  if (mail.cc && !s.test) options.cc = mail.cc;            // テストモードでは、ここでもCCを付けない（二重の安全策）
  if (s.mailMode === '送信') {
    GmailApp.sendEmail(mail.to, mail.subject, mail.body, options);
    return '送信済み';
  }
  GmailApp.createDraft(mail.to, mail.subject, mail.body, options);
  return '下書き済み';
}
```

### `applyTestMode_`（8 テストモード）

```javascript
/** 8 テストモード：宛先を自分に、CCは外す。件名とファイル名に【テスト】、本文の先頭に本来の宛先とCCを書く */
function applyTestMode_(mail, s) {
  if (!s.test) return mail;
  return {
    to: s.testTo,
    cc: '',
    subject: '【テスト】' + mail.subject,
    body: '※テスト用です。本番の宛先：' + mail.to + (mail.cc ? '／本番のCC：' + mail.cc : '') + '\n\n' + mail.body,
    fileName: '【テスト】' + mail.fileName,
  };
}
```

### `createInvoices`（メニュー②）

```javascript
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
        const mail = applyTestMode_({ to: inv.email, cc: inv.cc, subject: fill_(s.subject, inv.fields), body: fill_(s.body, inv.fields),
          fileName: (inv.number + '_' + inv.name).replace(/[\\/:*?"<>|]/g, '_') + '.pdf' }, s);
        const ccMemo = !s.test && inv.email && mail.cc ? 'CC：' + mail.cc : ''; // 本番でCCに入れたアドレスをメモに残す
        const row = p.log.start(inv, inv.email ? mail.to : '');
        let pdf = null, step = 'PDF作成';
        try {
          buildInvoiceSheet_(sheet, p.layout, inv);
          pdf = savePdf_(tmp, mail.fileName, s.folderId);
          step = 'メール作成';
          const status = inv.email ? deliverMail_(mail, pdf.blob, s) : 'メール未登録';
          p.log.finish(row, status, mail.fileName, pdf.file.getUrl(), ccMemo);
          count[status] = (count[status] || 0) + 1;
        } catch (e) {
          p.log.finish(row, step === 'メール作成' ? '要確認' : 'エラー', pdf ? mail.fileName : '', pdf ? pdf.file.getUrl() : '',
            [step === 'メール作成' ? ccMemo : '', e.message].filter(x => x).join('／'));
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
```

### `setupSheets`（メニュー 準備）

変えたのは、取引先マスタの見出しに `'CC'` を足した1か所だけです。

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
  [[SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'CC']],
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

**定数は変更していません。** `LOG_HEAD` もそのままで、CCは既存の「メモ」列に書きます。そのため、送付記録の見出しチェックにも影響しません。

---

## 2. スプレッドシート側で必要な作業

1. **取引先マスタの1行目に「CC」列を足す**
   - 見出しは半角大文字の `CC` にしてください。「ＣＣ」（全角）や「cc」では見つかりません。
   - 列の位置はどこでもかまいません（見出しの名前で探します）。
   - この列がないと、①・②とも「CCの列が見つかりません」と出て止まります。何も作らないうちに止まるので、安全です。
2. **CCの書き方**
   - 1件のとき：`keiri@example.co.jp`
   - 複数のとき：`keiri@example.co.jp,bucho@example.co.jp`（半角の「,」で区切ります。前後の空白はかまいません）
   - 「、」「，」や空白だけで区切ると、形式エラーとして止まります。
   - CCを使わない取引先は空欄のままにしてください。
3. **請求書レイアウトへの差し込みは不要です。** CCは請求書（PDF）には載せません。差し込み項目も増やしていないので、件名・本文・レイアウトはそのままで動きます。
4. **設定シートと送付記録シートは変更不要です。**

---

## 3. テストモードで確かめる手順

**準備**

1. 設定シートで、**テストモード：ON**、**送信方法：下書き** になっていることを確かめます。テスト用の宛先には自分のアドレスを入れておきます。

**エラーの確認**

2. 取引先マスタの1社に、わざと誤ったCC（例：`a@example.jp、b@example.jp`）を入れて、**①内容を確認する** を実行します。
   →「CCのメールアドレスの形式を確かめてください」と出て止まればOKです。
3. 誤ったCCを正しい形（`a@example.jp,b@example.jp`）に直します。CCありの取引先とCCなしの取引先が、両方あるようにしておきます。

**作成の確認**

4. **①内容を確認する** で、エラーが出ず、作成件数がこれまでどおりであることを確かめます。
5. **②PDFとメールを作成する** を実行し、Gmailの下書きを開いて次を確かめます。
   - 宛先が「テスト用の宛先」だけで、**CC欄が空**であること
   - 本文の先頭に「※テスト用です。本番の宛先：…／本番のCC：…」とあり、CCが正しく並んでいること（CCなしの取引先には「本番のCC」が出ないこと）
   - 件名とPDF名に【テスト】が付いていること
6. 送付記録で、モードが「テスト」、状態が「下書き済み」になっていることを確かめます。**メモ欄は空**のはずです（テストではCCを付けていないため）。

**二重作成の防止の確認**

7. もう一度 **②** を実行します。
   →「作るものはありません」と出て、同じ下書きが増えなければOKです。

**後片付け**

8. テストの下書きと、ドライブの【テスト】PDFを削除します。テストをやり直すときは、送付記録の「テスト」の行も消してください。

**（任意）CCが本当に付くかを、取引先に届けずに確かめる方法**

自分宛ての確認用の取引先を1件、仮に作ります（メールとCCの両方に自分のアドレスを入れます）。そのうえで、**テストモードOFF・下書き** で実行し、下書きのCC欄と送付記録のメモ「CC：…」を確かめます。

ただし、本番モードなので、その月のほかの取引先の下書きも作られます。作られた下書きは送らずに削除し、送付記録の「本番」の行も消してから、テストモードをONに戻してください。対象月の明細をその1社だけにしておくと安全です。

---

※ この環境ではGASを実行できないため、コードは動かしていません。上の手順3で動作を確かめてください。
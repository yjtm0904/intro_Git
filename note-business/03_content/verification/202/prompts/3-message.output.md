# 変更内容：取引先ごとの「ひとこと」をメール本文に差し込む

## 変更の考え方

- 取引先マスタの「ひとこと」は、メール本文の差し込みにだけ使います。
- そのため、件名と請求書レイアウトで使う `inv.fields` には入れません。本文用に `inv.mailFields` を別に用意します。
- 件名やレイアウトに `{{ひとこと}}` を書いた場合は、①の確認の段階で「使えない差し込み項目があります」と出て止まります。これで「件名には使わない」ことがコード側でも守られます。
- 「ひとこと」が空欄の取引先では空の文字が入ります。`{{ひとこと}}` の行は空行として残ります。
- 次の部分には手を入れていません。
  - `applyTestMode_`（テストモード）
  - `deliverMail_`（下書きが既定）
  - `deliveryLog_`（送付記録による二重作成の防止）
  - 定数

**変更する関数は4つです：** `aggregateInvoices_`、`createInvoices`、`plan_`、`setupSheets`

---

## 1. 変更した関数の全文

### aggregateInvoices_（取引先マスタから「ひとこと」を読み、本文用の差し込み項目を作る）

変更点は次のとおりです。
- 読む列に「ひとこと」を追加
- `c.note` を追加
- `inv.note` と `inv.mailFields` を追加

```javascript
/** 3 明細の集計：対象月の明細を取引先ごと・税率ごとに合計する。消費税の端数処理は請求書1枚につき税率ごとに1回 */
function aggregateInvoices_(s) {
  const clients = {}, groups = {}, e = [];
  readTable_(SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'ひとこと']).forEach(r => {
    const c = { code: String(r['取引先コード']).trim(), name: String(r['取引先名']).trim(), dept: String(r['部署']).trim(), email: String(r['メール']).trim(),
      note: String(r['ひとこと']).trim() }; // 本文の {{ひとこと}} に入れる一言（空欄なら何も入れない）
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
    const inv = { code: code, name: c.name, dept: c.dept, email: c.email, note: c.note, number: 'INV-' + s.month.replace('-', '') + '-' + code,
      lines: lines, base: base, tax: tax, total: base[10] + tax[10] + base[8] + tax[8] };
    inv.fields = {
      '取引先コード': code, '取引先名': c.name, '部署': c.dept, '請求書番号': inv.number, '対象月': s.month.replace(/^(\d{4})-0?(\d+)$/, '$1年$2月'),
      '発行日': s.issueDate, '支払期限': s.dueDate, '発行者名': s.issuer, '発行者住所': s.address, '登録番号': s.regNo, '振込先': s.bank, '備考': s.note,
      '10%対象': base[10], '10%消費税': tax[10], '8%対象': base[8], '8%消費税': tax[8],
      '税抜合計': base[10] + base[8], '消費税合計': tax[10] + tax[8], '合計': inv.total,
    };
    inv.mailFields = Object.assign({}, inv.fields, { 'ひとこと': c.note }); // 本文だけで使う項目（件名・請求書レイアウトには入れない）
    return inv;
  });
  if (e.length) throw new Error('データを直してください（まだ何も作っていません）。\n・' + e.slice(0, 15).join('\n・') + (e.length > 15 ? '\n…ほか' + (e.length - 15) + '件' : ''));
  return { invoices: invoices, idle: Object.keys(clients).filter(code => !groups[code]) };
}
```

### createInvoices（本文だけ `inv.mailFields` で差し込む）

変更は `body:` の1か所だけです。件名は今までどおり `inv.fields` を使います。

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
        const mail = applyTestMode_({ to: inv.email, subject: fill_(s.subject, inv.fields), body: fill_(s.body, inv.mailFields), // 本文だけ {{ひとこと}} を使える
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
```

### plan_（差し込み項目の確認：本文だけ {{ひとこと}} を認める）

変更点は次のとおりです。
- 件名と請求書レイアウトは、今までどおりの項目で確かめます。件名やレイアウトに `{{ひとこと}}` があると、ここで止まります。
- 本文は「ひとこと」を空として確かめます。取引先が書いた一言の中身で誤って止まらないようにするためです。
- エラー文に「{{ひとこと}} は本文だけで使える」と添えます。

```javascript
/** 補助：設定・明細・送付記録を読んで、作るものと作らないものに分ける（ここまでは何も作らない） */
function plan_() {
  const s = loadSettings_(), agg = aggregateInvoices_(s);
  if (!agg.invoices.length) throw new Error('対象月（' + s.month + '）の明細が0件です。設定の「対象月」と、請求明細の「対象月」の列を確かめてください（まだ何も作っていません）');
  DriveApp.getFolderById(s.folderId).getName();             // フォルダIDの誤りは、作る前にここで止まる
  const layout = sheet_(SHEET.layout).getDataRange().getValues();
  linePos_(layout);
  const f = agg.invoices[0].fields;
  const bodyCheck = fill_(s.body, Object.assign({}, f, { 'ひとこと': '' })); // {{ひとこと}} は本文だけで使える（件名・レイアウトでは止める）
  const left = [fill_(s.subject, f), bodyCheck].concat(layout.flat().map(v => (String(v).indexOf('{{明細:') === 0 ? '' : fill_(v, f)))).join('\n').match(/\{\{[^{}]+\}\}/g);
  if (left) throw new Error('使えない差し込み項目があります：' + left.join(' ') + '\n（件名・本文・請求書レイアウトを確かめてください。使える項目：' + Object.keys(f).join('・') + '。{{ひとこと}} は本文だけで使えます）');
  const log = deliveryLog_(s), p = { s: s, log: log, layout: layout, idle: agg.idle, todo: [], skip: [] };
  agg.invoices.forEach(inv => (log.status(inv.code) ? p.skip : p.todo).push(inv));
  return p;
}
```

### setupSheets（新しく作るときの取引先マスタの見出しと、本文の例）

変更は次の2か所だけです。
- 取引先マスタの見出しに「ひとこと」を追加し、その列を文字の形式にする
- 設定の「本文」の例の最後に `{{ひとこと}}` の行を追加する

すでにあるシートは今までどおり変えません。

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
  [[SHEET.master, ['取引先コード', '取引先名', '部署', 'メール', 'ひとこと']],
    [SHEET.details, ['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']],
    [SHEET.log, LOG_HEAD]].forEach(([name, head]) => {
    const sh = make(name, [head]);
    if (sh) { sh.setFrozenRows(1); sh.getRange(1, 1, 1, head.length).setFontWeight('bold'); }
    if (sh && name !== SHEET.master) sh.getRange(2, name === SHEET.log ? 3 : 1, 999, 1).setNumberFormat('@'); // 対象月を文字のまま残す
    if (sh && name === SHEET.master) sh.getRange(2, 5, 999, 1).setNumberFormat('@').setWrap(true);           // ひとことを文字のまま残す
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
    ['本文', '{{取引先名}}\n{{部署}} ご担当者様\n\nいつもお世話になっております。{{発行者名}}です。\n{{対象月}}分の請求書をお送りします。\n\n請求書番号：{{請求書番号}}\nご請求金額：{{合計}}円（税込）\nお支払期限：{{支払期限}}\n\nご確認のほど、よろしくお願いいたします。\n{{ひとこと}}', 'PDFは自動で添付される。{{ひとこと}} には取引先マスタの「ひとこと」が入る（本文だけで使える。空欄の取引先では何も入らない）'],
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

すでに5枚のシートがある場合は、次の作業を手で行ってください（「準備」メニューは既存のシートを変えません）。

1. **取引先マスタに「ひとこと」列を足す**
   - 1行目の空いている列に、見出し `ひとこと` を入れます。
   - 列の場所はどこでもかまいません（見出しの名前で読みます）。
   - この列がないと、①・②の実行時に「取引先マスタに「ひとこと」の列が見つかりません」と出て止まります。
   - 列全体を「表示形式 → 数字 → 書式なしテキスト」にしておくと安全です。数字や日付のように見える一言が、別の形に変わるのを防げます。
   - 一言の中で改行したいときは、セル内で Ctrl+Enter（Mac は ⌘+Enter）を使います。

2. **設定シートの「本文」に `{{ひとこと}}` の行を足す**
   - 「ご確認のほど、よろしくお願いいたします。」の後で改行し、`{{ひとこと}}` だけの行を足します（例：Ctrl+Enter で改行）。
   - 空欄の取引先では、この行が空行になります。

3. **件名と請求書レイアウトには差し込まない**
   - 請求書レイアウトへの差し込み作業は不要です。
   - 件名やレイアウトに `{{ひとこと}}` を書くと、①の確認で「使えない差し込み項目があります」と出て止まります。

補足：「ひとこと」だけを入れて取引先コードが空の行があると、「取引先コードが空欄です」と知らせて止まります。残っている書きかけの行に気づけるようにするためです。

---

## 3. テストモードで確かめる手順

1. **設定を確かめる**
   - 「テストモード」が `ON` になっていること
   - 「テスト用の宛先」が自分のアドレスであること
   - 「送信方法」が `下書き` であること

2. **確認用のデータを用意する**
   - 対象月に明細がある取引先のうち、1社には「ひとこと」を入れます（例：「年末年始は12/28〜1/5休業いたします。」）。
   - もう1社は空欄のままにします。

3. **①「内容を確認する」を実行する**
   - エラーが出ずに一覧が出ることを確かめます。
   - 件名や本文の差し込みに誤りがあれば、ここで止まります。

4. **（任意）件名で止まることを確かめる**
   - 件名の末尾に一時的に `{{ひとこと}}` を足して①を実行します。
   - 「使えない差し込み項目があります：{{ひとこと}}」と出て止まれば正しい動きです。
   - 確かめたら件名を元に戻します。

5. **②「PDFとメールを作成する」を実行する**
   - 確認の画面の題名が「【テスト】下書きで○件を作成します」になっていることを確かめてから「はい」を押します。

6. **Gmail の下書きを確かめる**
   - 宛先がすべて自分になっていること
   - 件名が「【テスト】」で始まり、ひとことが入っていないこと
   - 本文の先頭に「※テスト用です。本番の宛先：…」があること
   - 一言を入れた取引先は、本文の最後にその一言が入っていること
   - 空欄の取引先は、その行が空行になっていて、`{{ひとこと}}` の文字が残っていないこと
   - PDF（ファイル名が「【テスト】」で始まる）が添付されていること

7. **送付記録を確かめる**
   - モードが「テスト」、状態が「下書き済み」で記録されていることを確かめます。

8. **二重作成の防止を確かめる**
   - もう一度①を実行し、「記録があるため作らない」に同じ件数が出ることを確かめます。
   - ②を実行すると「作るものはありません」と出ることも確かめます。

9. **片付け**
   - テストの下書きを削除します。
   - 保存フォルダの「【テスト】」PDFを削除します。
   - 一言を直してもう一度テストしたいときは、送付記録のモード「テスト」の行を消してから②を実行します。
   - 本番は記録のモードが別なので、テストの記録が残っていても本番の作成は止まりません。
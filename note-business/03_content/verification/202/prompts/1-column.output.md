# 注文番号を請求書の明細に表示する変更

変更するのは **定数 `LINE_KEYS`** と、**関数 `aggregateInvoices_`・`buildInvoiceSheet_`** の3か所です。ほかの関数（テストモード、下書きの既定、送付記録による二重作成の防止など）は変えていないので、今と同じように動きます。

## 1. 変更した定数と関数（全文）

### 定数 `LINE_KEYS`
最後に `'注文番号'` を足しました。これで、レイアウトに `{{明細:注文番号}}` と書いてもエラーになりません。

```javascript
const LINE_KEYS = ['取引日', '品目', '税率', '数量', '単価', '金額', '注文番号']; // 明細に差し込める項目
```

### 関数 `aggregateInvoices_`
変更点は2つです。
- 請求明細から読む列に「注文番号」を足しました。見出しの書き間違いや列の付け忘れがあると、何も作らずに止まります。
- 明細の各行に注文番号（`order`）を持たせました。空欄の行は空の文字として扱い、エラーにはしません。

```javascript
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
  readTable_(SHEET.details, ['対象月', '取引日', '取引先コード', '品目', '数量', '単価', '税率', '注文番号']).forEach(r => {
    if (toMonth_(r['対象月']) !== s.month) return;            // 対象月の明細だけを使う
    const code = String(r['取引先コード']).trim(), qty = r['数量'], price = r['単価'];
    const order = r['注文番号'] === undefined || r['注文番号'] === null ? '' : String(r['注文番号']).trim(); // 空欄でもよい
    const line = { date: toDate_(r['取引日']), item: String(r['品目']).trim(), qty: qty, price: price, rate: toRate_(r['税率']), amount: Math.round(qty * price * 1e6) / 1e6, order: order };
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
```

### 関数 `buildInvoiceSheet_`
明細に差し込む値に「注文番号」を足しました。空欄の行は空欄のまま表示されます。

```javascript
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
    const val = l ? { 取引日: l.date, 品目: l.item, 税率: l.rate === 8 ? '8%※' : '10%', 数量: l.qty, 単価: l.price, 金額: l.amount, 注文番号: l.order } : {};
    pos.cols.forEach((key, j) => { if (key) out[pos.top + i][j] = l ? val[key] : ''; });
  }
  sheet.getRange(1, 1, out.length, out[0].length).setValues(out);
}
```

## 2. スプレッドシート側で必要な作業

### 請求明細シート
1. 好きな位置に列を1つ足し、1行目の見出しを **「注文番号」** にします。列は見出しの名前で探すので、どこに置いてもかまいません。
   - 見出しが「注文番号」と完全に一致しないと止まります（「注文No」や前後の全角スペースなどに注意してください）。
   - 「注文番号」の列が2つあっても止まります。
2. 注文番号の列を **書式なしテキスト** にします（表示形式 → 数字 → 書式なしテキスト）。
   - こうしないと「00123」が「123」になったり、「2026-11」のような番号が日付に変わったりします。
3. 注文番号のない行は空欄のままでかまいません。

### 請求書レイアウトシート（例：品目の左に注文番号を入れる場合）
1. **B列** を右クリックして「左に1列挿入」を選びます。結合セルや下の合計欄は、自動で右にずれます。
2. 新しいB列に次を入れます。
   - B12：`注文番号`（見出し）
   - B13：`{{明細:注文番号}}`
3. B13〜B27 を **書式なしテキスト** にします。PDFでも先頭の0が消えないようにするためです。
4. 罫線を A12:G27 に引き直し、列幅を調整します。
5. B14〜B27 には何も書かないでください。明細欄にほかの文字があると止まります。
6. 列が増えた分、PDFの横幅がはみ出すことがあります。「ファイル → ダウンロード → PDF」のプレビューで1ページに収まるか確かめ、収まらなければ品目の列幅などを狭めてください。

### 注意（変えていないところ）
- 送付記録シートの列は **変えないでください**（見出しの照合で止まります）。
- メニューの「準備：5枚のシートを作る」で今後シートを新しく作り直す場合、請求明細に「注文番号」の列は自動では入りません。そのときは手で足してください。

## 3. テストモードで確かめる手順

1. **設定を確認します。**
   - テストモード：`ON`
   - 送信方法：`下書き`
   - テスト用の宛先：自分のアドレス
   - 対象月：テストに使う月
2. **請求明細に試しのデータを入れます。** 同じ取引先で、次の3種類の行を用意します。
   - 注文番号ありの行（例：`PO-001`）
   - 先頭が0の番号の行（例：`00123`）
   - 注文番号が空欄の行
3. **メニュー「① 内容を確認する」を実行します。** エラーが出ず、件数と合計がいつもどおりなら大丈夫です。
4. **メニュー「② PDFとメールを作成する」を実行します。** 確認画面のタイトルが「【テスト】下書きで○件…」になっていることを確かめてから「はい」を押します。
5. **結果を確かめます。**
   - **PDF**（保存フォルダ）
     - ファイル名が【テスト】で始まる
     - 注文番号が正しい行に出ている
     - 空欄の行は空欄のまま
     - `00123` の0が消えていない
     - 金額・消費税・合計が前と変わらない
   - **Gmailの下書き**
     - 宛先が自分
     - 件名が【テスト】で始まる
     - 本文の先頭に「本番の宛先：…」がある
     - PDFが添付されている
     - 送信はされていない
   - **送付記録**
     - モードが「テスト」
     - 状態が「下書き済み」
6. **二重作成の防止を確かめます。** もう一度②を実行すると、「作るものはありません」「記録があるため作らない：○件」と出れば、今までどおり動いています。
7. **（できれば）止まるかどうかを確かめます。**
   - 請求明細の見出しを一時的に「注文No」に変えて①を実行し、「『注文番号』の列が見つかりません」で止まるか確かめます。確認後は見出しを元に戻してください。
8. **後片付けをします。**
   - 送付記録の「テスト」の行を消します。テストと本番は記録が分かれているので、残しても本番の作成は妨げません。
   - テストの下書きとPDFを削除します。
   - 本番に切り替えるときは、テストモードを `OFF` にします。
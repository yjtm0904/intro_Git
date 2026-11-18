/**
 * 請求書PDF・メール下書き作成スクリプト v1.1（2026-11-08）事務の型紙「GAS請求書パック」
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
  const ymd = d => Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyyMMdd');
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
  else if (s.issueDate && ymd(s.dueDate) < ymd(s.issueDate)) e.push('支払期限：発行日より前の日付です（月の書き換え忘れがないか確かめてください）');
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
    ['本文', '{{取引先名}} {{部署}}\nご担当者様\n\nいつもお世話になっております。{{発行者名}}です。\n{{対象月}}分の請求書をお送りします。\n\n請求書番号：{{請求書番号}}\nご請求金額：{{合計}}円（税込）\nお支払期限：{{支払期限}}\n\nご確認のほど、よろしくお願いいたします。', 'PDFは自動で添付される'],
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
  const lay = make(SHEET.layout, grid, [130, 160, 50, 50, 80, 120]);
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

// 記事202「GAS請求書パック」Code.gs のロジック検証（Node.js標準のテストランナー）
// 実行: TZ=Asia/Tokyo node --test code.test.js
// Googleのサービスは 05_operations/tools/gas-mock のモック。PDFの見た目・権限画面・送信の上限は実機確認（device-check.md）で確かめる。
'use strict';
process.env.TZ = 'Asia/Tokyo';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { createGasEnv } = require('../../../05_operations/tools/gas-mock/index.js');

const CODE = path.join(__dirname, 'Code.gs');
const D = (y, m, d) => new Date(y, m - 1, d);
const ROUNDINGS = ['切り捨て', '四捨五入', '切り上げ'];

// ---- 架空のテストデータ（30社・明細100行）。会社名はすべて架空、メールは example.com ----
const NAMES = [
  '株式会社サンプル商事', 'サンプル工業株式会社', '株式会社見本デザイン', '架空物流株式会社', '株式会社テスト食品',
  'サンプル建設株式会社', '有限会社見本印刷', '株式会社架空システム', 'テスト電機株式会社', '株式会社サンプル企画',
  '見本不動産株式会社', '株式会社架空出版', 'サンプル薬品株式会社', '株式会社テスト運輸', '見本製作所株式会社',
  '株式会社サンプル広告', '架空化学株式会社', '株式会社見本商会', 'テスト設備株式会社', '株式会社サンプル農園',
  '見本観光株式会社', '株式会社架空教育', 'サンプル繊維株式会社', '株式会社テスト技研', '見本金属株式会社',
  '株式会社サンプル通信', '架空衛生株式会社', '株式会社見本住宅', 'テスト精機株式会社', '株式会社サンプル総研',
];
const ITEMS = [ // [品目, 単価（税抜）, 税率]
  ['月額保守サービス', 33000, 10], ['作業費（1時間）', 4500, 10], ['名刺印刷（100枚）', 1650, 10], ['送料', 980, 10],
  ['コーヒー豆（軽減税率）', 1296, 8], ['お弁当（軽減税率）', 864, 8], ['消耗品', 1234, 10], ['ソフトウェア利用料', 12345, 10],
  ['飲料（軽減税率）', 157, 8], ['コピー用紙', 553, 10],
];
const code3 = (i) => 'C-' + String(i).padStart(3, '0');
function rng(seed) { let x = seed >>> 0; return () => (x = (Math.imul(x, 1664525) + 1013904223) >>> 0) / 4294967296; }
// 税率のセルは、入力のしかたで 0.1（「10%」と表示）・10・'10%' のどれにもなりうる
const rateCell = (rate, i) => [rate / 100, rate, rate + '%'][i % 3];

function makeData({ clients = 30, lines = 100, active = 28, seed = 20261108 } = {}) {
  const r = rng(seed);
  const master = [['取引先コード', '取引先名', '部署', 'メール']];
  for (let i = 1; i <= clients; i++) master.push([code3(i), NAMES[i - 1], i % 3 ? '経理部' : '', i === 7 ? '' : 'billing' + String(i).padStart(3, '0') + '@example.com']);
  const details = [['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']];
  for (let i = 0; i < lines; i++) {
    const c = i < active ? i + 1 : 1 + Math.floor(r() * active); // C-001〜C-028 に必ず1行以上。C-029・C-030 は明細なし
    const it = ITEMS[Math.floor(r() * ITEMS.length)];
    const qty = 1 + Math.floor(r() * 12);
    details.push(['2026-11', D(2026, 11, 1 + Math.floor(r() * 28)), code3(c), '', 'P-' + String(ITEMS.indexOf(it) + 1).padStart(2, '0'), it[0], qty, it[1], rateCell(it[2], i), qty * it[1]]);
  }
  // 前月の明細（集計に入らないこと）
  for (let i = 1; i <= 10; i++) details.push(['2026-10', D(2026, 10, i), code3(i), '', '', '前月の作業費', 1, 99999, 0.1, 99999]);
  return { master, details };
}

// ---- 独立した検算（BigIntで計算し、コードとは別の書き方で端数処理する） ----
function oracle(data, month, rounding) {
  const res = {};
  data.details.slice(1).forEach((row) => {
    if (row[0] !== month) return;
    const rate = Math.round((typeof row[8] === 'string' ? parseFloat(row[8]) : row[8] < 1 ? row[8] * 100 : row[8]));
    const o = (res[row[2]] = res[row[2]] || { base10: 0n, base8: 0n, lines: 0 });
    o['base' + rate] += BigInt(row[6]) * BigInt(row[7]);
    o.lines++;
  });
  const div = (a, b) => { const q = a / b, rem = a % b; if (rem === 0n || rounding === '切り捨て') return q; if (rounding === '切り上げ') return q + 1n; return rem * 2n >= b ? q + 1n : q; };
  Object.values(res).forEach((o) => {
    o.tax10 = div(o.base10 * 10n, 100n); o.tax8 = div(o.base8 * 8n, 100n);
    o.total = o.base10 + o.tax10 + o.base8 + o.tax8;
    ['base10', 'base8', 'tax10', 'tax8', 'total'].forEach((k) => { o[k] = Number(o[k]); });
  });
  return res;
}

// ---- テスト用の環境を作る（準備メニューで5枚を作り、データと設定を入れる） ----
function setup({ data = makeData(), settings = {}, responses = [] } = {}) {
  const env = createGasEnv({ now: '2026-11-30T10:00:00+09:00', sheets: { 'シート1': [] } });
  env.load(CODE);
  env.ctx.setupSheets();
  env.ui.alerts.length = 0;
  env.ui.responses.push(...responses);                 // 確認ダイアログへの答え（「はい」「いいえ」）
  put(env.sheet('取引先マスタ'), data.master);
  put(env.sheet('請求明細'), data.details);
  setSettings(env, Object.assign({
    対象月: '2026-11', 支払期限: D(2026, 12, 31), 端数処理: '切り捨て', 発行者名: '株式会社見本サービス', 発行者住所: '東京都架空区見本町1-2-3',
    登録番号: 'T0000000000000', 振込先: '見本銀行 本店 普通 0000000', PDF保存フォルダID: 'FOLDER_TEST', テスト用の宛先: 'owner@example.com',
  }, settings));
  return env;
}
function put(sheet, rows) { sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows); }
function setSettings(env, kv) {
  const sh = env.sheet('設定'), keys = sh.getDataRange().getValues().map((r) => r[0]);
  Object.entries(kv).forEach(([k, v]) => { const i = keys.indexOf(k); assert.ok(i > 0, '設定に項目がない: ' + k); sh.getRange(i + 1, 2).setValue(v); });
}
const logRows = (env) => env.sheet('送付記録').getDataRange().getValues().slice(1).filter((r) => r[0] !== '');
const lastAlert = (env) => env.ui.alerts[env.ui.alerts.length - 1];
const cell = (data, a1) => data[Number(a1.slice(1)) - 1][a1.charCodeAt(0) - 65];
const pdfSheet = (file) => file.blob.snapshot.find((s) => s.name === '請求書').data;

// ================= テスト =================

test('01 メニュー：開くと「請求書」メニューに3つの項目が出て、呼び出す関数がある', () => {
  const env = setup();
  env.ctx.onOpen();
  const m = env.ui.menus[0];
  assert.equal(m.name, '請求書');
  const items = m.items.filter((x) => !x.separator);
  assert.deepEqual(items.map((x) => x.fn), ['previewInvoices', 'createInvoices', 'setupSheets']);
  items.forEach((x) => assert.equal(typeof env.ctx[x.fn], 'function'));
});

test('02 準備：5枚のシートと見出し・設定項目・レイアウトを作り、2回目は何も変えない', () => {
  const env = createGasEnv({ sheets: { 'シート1': [] } });
  env.load(CODE);
  env.ctx.setupSheets();
  ['取引先マスタ', '請求明細', '請求書レイアウト', '送付記録', '設定'].forEach((n) => assert.ok(env.sheet(n), n));
  assert.deepEqual(env.sheet('取引先マスタ').getDataRange().getValues()[0], ['取引先コード', '取引先名', '部署', 'メール']);
  assert.deepEqual(env.sheet('請求明細').getDataRange().getValues()[0], ['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']);
  assert.equal(env.sheet('送付記録').getDataRange().getValues()[0].length, 12);
  const keys = env.sheet('設定').getDataRange().getValues().slice(1).map((r) => r[0]);
  assert.equal(keys.length, 17);
  const st = Object.fromEntries(env.sheet('設定').getDataRange().getValues().slice(1).map((r) => [r[0], r[1]]));
  assert.equal(st['テストモード'], 'ON');     // 既定はテストモード
  assert.equal(st['送信方法'], '下書き');     // 既定は下書き
  assert.equal(st['端数処理'], '');           // 端数処理は選ばない（社内で決める）
  const lay = env.sheet('請求書レイアウト').getDataRange().getValues();
  assert.equal(cell(lay, 'A13'), '{{明細:取引日}}');
  env.sheet('取引先マスタ').getRange('A2').setValue('C-001');
  env.ctx.setupSheets();
  assert.equal(env.sheet('取引先マスタ').getRange('A2').getValue(), 'C-001');
  assert.match(lastAlert(env).prompt, /5枚ともあります/);
});

test('03 設定の誤り：空欄や形式の誤りをまとめて知らせ、何も作らない', () => {
  const env = setup({ settings: { 端数処理: '', 支払期限: '', PDF保存フォルダID: '', 登録番号: '1234', テスト用の宛先: 'owner' } });
  env.ctx.createInvoices();
  const a = lastAlert(env);
  assert.equal(a.title, '止まりました');
  ['端数処理', '支払期限', 'PDF保存フォルダID', '登録番号', 'テスト用の宛先'].forEach((k) => assert.match(a.prompt, new RegExp(k)));
  assert.equal(env.created.length, 0);
  assert.equal(env.DriveApp.files.length + env.GmailApp.drafts.length + env.GmailApp.sent.length, 0);
});

test('04 集計：架空30社・明細100行を、3つの端数処理それぞれで独立の検算と一致させる', () => {
  const data = makeData();
  assert.equal(data.details.slice(1).filter((r) => r[0] === '2026-11').length, 100);
  const out = {};
  ROUNDINGS.forEach((rounding) => {
    const env = setup({ data, settings: { 端数処理: rounding } });
    const s = env.ctx.loadSettings_();
    const agg = env.ctx.aggregateInvoices_(s);
    const exp = oracle(data, '2026-11', rounding);
    assert.equal(agg.invoices.length, 28);                         // 明細のある28社だけ
    assert.deepEqual(Array.from(agg.idle), ['C-029', 'C-030']);    // 明細のない取引先
    assert.equal(agg.invoices.reduce((n, i) => n + i.lines.length, 0), 100); // 前月の10行は入らない
    agg.invoices.forEach((inv) => {
      const e = exp[inv.code];
      assert.deepEqual([inv.base[10], inv.base[8], inv.tax[10], inv.tax[8], inv.total, inv.lines.length],
        [e.base10, e.base8, e.tax10, e.tax8, e.total, e.lines], inv.code + ' ' + rounding);
      assert.equal(inv.number, 'INV-202611-' + inv.code);
    });
    out[rounding] = agg.invoices.map((i) => ({ code: i.code, base10: i.base[10], tax10: i.tax[10], base8: i.base[8], tax8: i.tax[8], total: i.total }));
  });
  // Python（Decimal）での検算用に、データと結果を保存する（crosscheck.py が読む）
  const ser = (v) => (v instanceof Date ? v.toISOString() : v);
  fs.writeFileSync(path.join(__dirname, 'dataset.json'), JSON.stringify({ master: data.master, details: data.details.map((r) => r.map(ser)) }, null, 1));
  fs.writeFileSync(path.join(__dirname, 'gas-output.json'), JSON.stringify(out, null, 1));
});

test('05 端数処理は「請求書1枚につき税率ごとに1回」：明細ごとに丸めた合計とは違う値になる', () => {
  const data = { master: [['取引先コード', '取引先名', '部署', 'メール'], ['C-001', '株式会社サンプル商事', '経理部', 'a@example.com']],
    details: [['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額'],
      ['2026-11', D(2026, 11, 1), 'C-001', '', '', 'A', 1, 105, 0.1, 105], ['2026-11', D(2026, 11, 2), 'C-001', '', '', 'B', 1, 105, 0.1, 105],
      ['2026-11', D(2026, 11, 3), 'C-001', '', '', 'C', 1, 105, 0.1, 105], ['2026-11', D(2026, 11, 4), 'C-001', '', '', 'D', 1, 1013, 0.08, 1013]] };
  // 10%：315円×10%＝31.5円（明細ごとに切り捨てると10円×3＝30円になるが、正しくは1回だけ処理する）／8%：1,013円×8%＝81.04円
  const expect = { 切り捨て: [31, 81], 四捨五入: [32, 81], 切り上げ: [32, 82] };
  ROUNDINGS.forEach((rounding) => {
    const env = setup({ data, settings: { 端数処理: rounding } });
    const inv = env.ctx.aggregateInvoices_(env.ctx.loadSettings_()).invoices[0];
    assert.deepEqual([inv.tax[10], inv.tax[8]], expect[rounding], rounding);
    assert.equal(inv.total, 315 + 1013 + expect[rounding][0] + expect[rounding][1]);
  });
});

test('06 テストモード（既定）：30社分のPDFと下書きを作り、宛先はすべて自分。送付記録を残し、一時ファイルを消す', () => {
  const data = makeData();
  const env = setup({ data });
  env.ctx.createInvoices();
  const confirm = env.ui.alerts.find((a) => a.buttons === 'YES_NO');
  assert.match(confirm.title, /【テスト】下書きで28件/);
  assert.equal(lastAlert(env).title, '終わりました');
  assert.match(lastAlert(env).prompt, /下書き済み：27件/);
  assert.match(lastAlert(env).prompt, /メール未登録：1件/);
  assert.equal(env.DriveApp.files.length, 28);
  assert.ok(env.DriveApp.files.every((f) => f.name.startsWith('【テスト】INV-202611-') && f.folderId === 'FOLDER_TEST'));
  assert.equal(env.GmailApp.drafts.length, 27);
  assert.equal(env.GmailApp.sent.length, 0);                       // 送信はしない
  assert.ok(env.GmailApp.drafts.every((d) => d.to === 'owner@example.com' && d.subject.startsWith('【テスト】')));
  assert.ok(env.GmailApp.drafts.every((d) => /※テスト用です。本番の宛先：billing\d{3}@example\.com/.test(d.body)));
  assert.ok(env.GmailApp.drafts.every((d) => d.options.attachments.length === 1 && d.options.attachments[0].getName().endsWith('.pdf')));
  const rows = logRows(env);
  assert.equal(rows.length, 28);
  assert.equal(rows.filter((r) => r[1] === 'テスト' && r[8] === '下書き済み').length, 27);
  assert.deepEqual(rows.filter((r) => r[8] === 'メール未登録').map((r) => r[3]), ['C-007']);
  assert.deepEqual(env.DriveApp.trashed, env.created.map((s) => s.getId())); // 一時ファイルはゴミ箱へ
  assert.equal(env.created.length, 1);
  // PDFにした時点のシートの中身：差し込み漏れがなく、合計と明細が検算と一致する
  const exp = oracle(data, '2026-11', '切り捨て');
  env.DriveApp.files.forEach((f) => {
    const sh = pdfSheet(f), code = f.name.match(/C-\d{3}/)[0], e = exp[code];
    assert.ok(!JSON.stringify(sh).includes('{{'), '差し込み漏れ ' + code);
    assert.deepEqual([cell(sh, 'F29'), cell(sh, 'F30'), cell(sh, 'F31'), cell(sh, 'F32'), cell(sh, 'F33'), cell(sh, 'B8')],
      [e.base10, e.tax10, e.base8, e.tax8, e.total, e.total], code);
    const lines = sh.slice(12, 27).filter((r) => r[1] !== '');
    assert.equal(lines.length, e.lines, code);
    assert.ok(lines.every((r) => (r[2] === '8%※' || r[2] === '10%') && r[5] === r[3] * r[4]));
    assert.equal(cell(sh, 'A3'), NAMES[Number(code.slice(2)) - 1] + ' 御中');
  });
});

test('07 同じ月の再実行：記録がある取引先は作らない（PDF・下書きが増えない）', () => {
  const env = setup();
  env.ctx.createInvoices();
  const before = [env.DriveApp.files.length, env.GmailApp.drafts.length, logRows(env).length];
  env.ctx.createInvoices();
  assert.deepEqual([env.DriveApp.files.length, env.GmailApp.drafts.length, logRows(env).length], before);
  assert.equal(lastAlert(env).title, '作るものはありません');
  assert.match(lastAlert(env).prompt, /記録があるため作らない：28件/);
  assert.equal(env.created.length, 1);                              // 2回目は一時ファイルも作らない
});

test('08 本番・下書き：取引先のアドレスあてに下書きを作る。テストの記録は本番を止めない。再実行で増えない', () => {
  const env = setup();
  env.ctx.createInvoices();                                          // テストモードで1回
  setSettings(env, { テストモード: 'OFF' });
  env.ctx.createInvoices();
  const prod = env.GmailApp.drafts.slice(27);
  assert.equal(prod.length, 27);
  assert.ok(prod.every((d) => /^billing\d{3}@example\.com$/.test(d.to) && d.subject === '【請求書】2026年11月分のご請求（株式会社見本サービス）'));
  assert.ok(!prod.some((d) => d.body.includes('テスト用')));
  assert.equal(env.DriveApp.files.filter((f) => !f.name.startsWith('【テスト】')).length, 28);
  assert.equal(logRows(env).filter((r) => r[1] === '本番').length, 28);
  env.ctx.createInvoices();
  assert.equal(env.GmailApp.drafts.length, 54);
  assert.equal(lastAlert(env).title, '作るものはありません');
});

test('09 送信モード：件数と「取り消せません」を示して確認し、いいえなら何もしない。はいなら送信し、再実行では送らない', () => {
  const env = setup({ settings: { テストモード: 'OFF', 送信方法: '送信' }, responses: ['NO'] });
  env.ctx.createInvoices();
  const ask = env.ui.alerts.find((a) => a.buttons === 'YES_NO');
  assert.match(ask.title, /【本番】送信で28件を作成します/);
  assert.match(ask.prompt, /取り消せません/);
  assert.match(lastAlert(env).prompt, /中止しました/);
  assert.equal(env.GmailApp.sent.length + env.DriveApp.files.length + logRows(env).length + env.created.length, 0);
  env.ctx.createInvoices();                                          // 2回目は「はい」
  assert.equal(env.GmailApp.sent.length, 27);
  assert.equal(env.GmailApp.drafts.length, 0);
  assert.equal(logRows(env).filter((r) => r[8] === '送信済み').length, 27);
  env.ctx.createInvoices();
  assert.equal(env.GmailApp.sent.length, 27);                         // 二重送信しない
});

test('10 明細0件の月：止めて知らせ、何も作らない', () => {
  const env = setup({ settings: { 対象月: '2026-12' } });
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /明細が0件/);
  assert.equal(env.created.length + env.DriveApp.files.length + env.GmailApp.drafts.length + logRows(env).length, 0);
});

test('11 メール未登録：PDFだけ作る。後で登録しても自動では作り直さず、状態を「取消」にすると作り直す', () => {
  const env = setup();
  env.ctx.createInvoices();
  env.sheet('取引先マスタ').getRange('D8').setValue('billing007@example.com'); // C-007 にメールを登録
  env.ctx.createInvoices();
  assert.equal(lastAlert(env).title, '作るものはありません');
  const sh = env.sheet('送付記録'), rows = sh.getDataRange().getValues();
  const i = rows.findIndex((r) => r[3] === 'C-007');
  sh.getRange(i + 1, 9).setValue('取消');
  env.ctx.createInvoices();
  assert.equal(env.GmailApp.drafts.length, 28);
  assert.match(env.GmailApp.drafts[27].body, /本番の宛先：billing007@example\.com/);
  assert.equal(env.DriveApp.files.length, 29);
});

test('12 前回が途中で止まった（処理中のまま）：その取引先は作らず、確認を促す', () => {
  const env = setup();
  env.sheet('送付記録').appendRow([D(2026, 11, 30), 'テスト', '2026-11', 'C-005', '株式会社テスト食品', 'INV-202611-C-005', 0, 'owner@example.com', '処理中', '', '', '']);
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /記録があるため作らない：1件（C-005 処理中）/);
  assert.match(lastAlert(env).prompt, /途中で止まった可能性/);
  env.ctx.createInvoices();
  assert.equal(env.DriveApp.files.length, 27);
  assert.ok(!env.DriveApp.files.some((f) => f.name.includes('C-005')));
});

test('13 明細の誤り：行番号つきでまとめて知らせ、何も作らない', () => {
  const data = makeData();
  data.details[3][2] = 'C-099';                // 取引先マスタにないコード（4行目）
  data.details[5][6] = '3個';                  // 数量が文字（6行目）
  data.details[8][8] = '5%';                   // 税率の誤り（9行目）
  data.details[10][6] = 1.5; data.details[10][7] = 101; // 151.5円（11行目）
  const env = setup({ data });
  env.ctx.createInvoices();
  const msg = lastAlert(env).prompt;
  assert.match(msg, /請求明細 4行目：取引先コード「C-099」が取引先マスタにありません/);
  assert.match(msg, /請求明細 6行目：数量と単価は数値で入れてください/);
  assert.match(msg, /請求明細 9行目：税率は10%か8%にしてください/);
  assert.match(msg, /請求明細 11行目：金額（数量×単価）に1円未満の端数があります/);
  assert.equal(env.created.length + env.DriveApp.files.length + env.GmailApp.drafts.length, 0);
});

test('14 明細が16行ある取引先：レイアウトの15行を超えるので止める', () => {
  const data = makeData({ lines: 28 });
  for (let i = 0; i < 15; i++) data.details.push(['2026-11', D(2026, 11, 10), 'C-002', '', '', '追加', 1, 100, 10, 100]);
  const env = setup({ data });
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /取引先 C-002：明細が16行あります/);
  assert.equal(env.DriveApp.files.length, 0);
});

test('15 列の見出し：必要な列がなければ知らせる。列を足したり順番を変えたりしても同じ結果になる', () => {
  const data = makeData();
  const broken = JSON.parse(JSON.stringify(data.master));
  broken[0][3] = 'メールアドレス';
  let env = setup({ data: { master: broken, details: data.details } });
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /取引先マスタに「メール」の列が見つかりません/);
  const dup = JSON.parse(JSON.stringify(data.master));
  dup.forEach((r, i) => r.push(i === 0 ? '取引先名' : 'コピーした列'));
  env = setup({ data: { master: dup, details: data.details } });
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /取引先マスタに「取引先名」の列が2つ以上あります/);
  // 請求明細の先頭に「メモ」列を足し、品目と数量の順番を入れ替える
  const order = [0, 1, 2, 3, 4, 6, 5, 7, 8, 9];
  const moved = data.details.map((r, i) => [i === 0 ? 'メモ' : '確認済み'].concat(order.map((j) => r[j])));
  env = setup({ data: { master: data.master, details: moved } });
  const agg = env.ctx.aggregateInvoices_(env.ctx.loadSettings_());
  const exp = oracle(data, '2026-11', '切り捨て');
  agg.invoices.forEach((inv) => assert.equal(inv.total, exp[inv.code].total, inv.code));
});

test('16 件名・本文・レイアウトに使えない差し込み項目があれば、作る前に止める', () => {
  const env = setup({ settings: { 件名: '【請求書】{{担当者名}}様' } });
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /使えない差し込み項目があります：\{\{担当者名\}\}/);
  assert.equal(env.created.length, 0);
});

test('17 二重起動の防止：ほかの実行が進んでいるときは何もしない', () => {
  const env = setup();
  env.ctx.LockService = { getScriptLock: () => ({ tryLock: () => false, releaseLock() {} }) };
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /ほかの実行が進んでいます/);
  assert.equal(env.created.length + env.DriveApp.files.length, 0);
});

test('18 1回の上限件数：10件ずつ作り、3回目で28件そろう。重複しない', () => {
  const env = setup({ settings: { '1回の上限件数': 10 } });
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /残り（もう一度②を実行すると続きから作ります）：18件/);
  env.ctx.createInvoices();
  env.ctx.createInvoices();
  assert.equal(env.DriveApp.files.length, 28);
  const codes = logRows(env).map((r) => r[3]);
  assert.equal(new Set(codes).size, 28);
});

test('19 対象月が日付に変わっていても読める（「2026-11」と入れると日付になる場合）', () => {
  const data = makeData();
  data.details.slice(1).forEach((r) => { if (r[0] === '2026-11') r[0] = D(2026, 11, 1); });
  const env = setup({ data, settings: { 対象月: D(2026, 11, 1) } });
  const agg = env.ctx.aggregateInvoices_(env.ctx.loadSettings_());
  assert.equal(agg.invoices.length, 28);
  assert.equal(agg.invoices.reduce((n, i) => n + i.lines.length, 0), 100);
});

test('20 メール作成で失敗：その取引先は「要確認」で止め、再実行でも作らない（二重送信を避ける）。一時ファイルは消す', () => {
  const env = setup();
  const real = env.GmailApp.createDraft.bind(env.GmailApp);
  let n = 0;
  env.GmailApp.createDraft = (...a) => { if (++n === 3) throw new Error('Gmailの一時的なエラー'); return real(...a); };
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /C-003 のメール作成で止まりました/);
  assert.deepEqual(logRows(env).map((r) => r[8]), ['下書き済み', '下書き済み', '要確認']);
  assert.equal(env.DriveApp.trashed.length, 1);
  env.ctx.createInvoices();
  assert.ok(!env.GmailApp.drafts.some((d) => d.body.includes('billing003@example.com')));
  assert.equal(env.GmailApp.drafts.length, 2 + 24);                 // C-003 とメール未登録の C-007 以外の残り
});

test('21 PDFの保存で失敗：「エラー」と記録して止める。原因を直して再実行すると作る', () => {
  const env = setup();
  const folder = env.DriveApp._folder.bind(env.DriveApp);
  let fail = true;
  env.DriveApp.getFolderById = (id) => { const f = folder(id); const create = f.createFile; f.createFile = (b) => { if (fail) throw new Error('ドライブの容量が不足しています'); return create(b); }; return f; };
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /C-001 のPDF作成で止まりました/);
  assert.deepEqual(logRows(env).map((r) => r[8]), ['エラー']);
  fail = false;
  env.ctx.createInvoices();
  assert.equal(env.DriveApp.files.length, 28);
  assert.equal(logRows(env).filter((r) => r[3] === 'C-001').map((r) => r[8]).join(), 'エラー,下書き済み');
});

test('22 ファイル名：社名の「.」は残し、「/」などファイル名に使えない文字は「_」にする', () => {
  const data = makeData({ clients: 1, lines: 1, active: 1 });
  data.master[1][1] = 'Sample Co., Ltd./Tokyo';
  const env = setup({ data });
  env.ctx.createInvoices();
  assert.equal(env.DriveApp.files[0].name, '【テスト】INV-202611-C-001_Sample Co., Ltd._Tokyo.pdf');
});

test('23 レイアウトの誤り：明細欄にほかの文字がある・使えない明細の項目があると止める', () => {
  let env = setup();
  env.sheet('請求書レイアウト').getRange('B20').setValue('小計');
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /明細欄.*ほかの文字があります（20行目）/);
  env = setup();
  env.sheet('請求書レイアウト').getRange('C13').setValue('{{明細:商品コード}}');
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /明細に使えない項目があります：商品コード/);
});

test('24 送付記録の見出しが変わっていたら止める', () => {
  const env = setup();
  env.sheet('送付記録').getRange('I1').setValue('ステータス');
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /送付記録の1行目の見出しが変わっています/);
  assert.equal(env.created.length, 0);
});

test('25 税率の書き方：0.1・10・「10%」・0.08・8・「8%」を読み、ほかは誤りにする', () => {
  const env = setup();
  [[0.1, 10], [10, 10], ['10%', 10], ['10％', 10], [0.08, 8], [8, 8], ['8%', 8], ['5%', 0], ['', 0], ['十', 0]].forEach(([v, want]) => assert.equal(env.ctx.toRate_(v), want, String(v)));
  ['2026-11', '2026/11', '202611', '2026年11月', D(2026, 11, 15)].forEach((v) => assert.equal(env.ctx.toMonth_(v), '2026-11', String(v)));
  ['2026-13', '11月', ''].forEach((v) => assert.equal(env.ctx.toMonth_(v), '', String(v)));
});

test('26 実機確認用の3社（templates.md のデータ）：手順書の期待値と一致する', () => {
  const md = fs.readFileSync(path.join(__dirname, 'templates.md'), 'utf8');
  const block = (name) => md.split('<!-- testdata:' + name + ' -->')[1].split('```')[1].trim().split('\n');
  // スプレッドシートに貼って「テキストを列に分割」したときと同じように読む（請求明細のA列と設定のB2は書式なしテキスト）
  const parse = (v, keepText) => {
    if (keepText || v === '') return v;
    let m;
    if ((m = v.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/))) return D(+m[1], +m[2], +m[3]);
    if ((m = v.match(/^(\d+(?:\.\d+)?)%$/))) return Number(m[1]) / 100;
    return /^\d+(\.\d+)?$/.test(v) ? Number(v) : v;
  };
  const master = [['取引先コード', '取引先名', '部署', 'メール']].concat(block('master').map((l) => l.split(',').map((v) => parse(v))));
  const details = [['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']]
    .concat(block('details').map((l) => l.split(',').map((v, j) => parse(v, j === 0))));
  const settings = Object.fromEntries(block('settings').map((l) => l.split(',')).map(([k, v]) => [k, parse(v, k === '対象月')]));
  settings['PDF保存フォルダID'] = 'FOLDER_OWNER'; settings['テスト用の宛先'] = 'owner@example.com';
  const total = { 切り捨て: 67394, 四捨五入: 67395, 切り上げ: 67397 };
  ROUNDINGS.forEach((rounding) => {
    const env = setup({ data: { master, details }, settings: Object.assign({}, settings, { 端数処理: rounding }) });
    env.ctx.previewInvoices();
    assert.match(lastAlert(env).prompt, new RegExp('作成する：3件（合計 ' + total[rounding].toLocaleString('en-US') + '円）うちメール未登録（PDFだけ作る）1件'), rounding);
  });
  const env = setup({ data: { master, details }, settings });
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /C-001 株式会社サンプル商事　53,949円[\s\S]*C-002 サンプル工業株式会社　9,373円[\s\S]*C-003 株式会社見本デザイン　4,072円　メール未登録/);
  env.ctx.createInvoices();
  assert.match(env.ui.alerts.find((a) => a.buttons === 'YES_NO').title, /【テスト】下書きで3件を作成します/);
  assert.match(lastAlert(env).prompt, /下書き済み：2件\nメール未登録：1件/);
  const sh = pdfSheet(env.DriveApp.files[0]);
  assert.equal(env.DriveApp.files[0].name, '【テスト】INV-202611-C-001_株式会社サンプル商事.pdf');
  assert.deepEqual(['F29', 'F30', 'F31', 'F32', 'F33'].map((a) => cell(sh, a)), [46500, 4650, 2592, 207, 53949]);
  assert.deepEqual(sh.slice(12, 15).map((r) => [r[1], r[2]]), [['月額保守サービス', '10%'], ['作業費（1時間）', '10%'], ['コーヒー豆（軽減税率）', '8%※']]);
  const c2 = pdfSheet(env.DriveApp.files[1]), c3 = pdfSheet(env.DriveApp.files[2]);
  assert.deepEqual(['F29', 'F30', 'F31', 'F32', 'F33'].map((a) => cell(c2, a)), [4280, 428, 4320, 345, 9373]);
  assert.deepEqual(['F29', 'F30', 'F31', 'F32', 'F33'].map((a) => cell(c3, a)), [3702, 370, 0, 0, 4072]);
  assert.equal(env.GmailApp.drafts[0].subject, '【テスト】【請求書】2026年11月分のご請求（株式会社見本サービス）');
  assert.ok(env.GmailApp.drafts[0].body.startsWith('※テスト用です。本番の宛先：sample-shoji@example.com'));
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /記録があるため作らない：3件/);
  assert.equal(env.DriveApp.files.length, 3);
});

test('27 支払期限が発行日より前なら止める（月の書き換え忘れ）。同じ日ならよい', () => {
  let env = setup({ settings: { 発行日: D(2026, 11, 30), 支払期限: D(2026, 10, 31) } });
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /支払期限：発行日より前の日付です/);
  assert.equal(env.created.length + env.DriveApp.files.length, 0);
  env = setup({ settings: { 発行日: D(2026, 11, 30), 支払期限: D(2026, 11, 30) } });
  env.ctx.previewInvoices();
  assert.equal(lastAlert(env).title, '内容の確認（まだ何も作っていません）');
});

test('28 既定の本文：部署が空欄の取引先でも、行の先頭に空白が入らない', () => {
  const env = setup();
  env.ctx.createInvoices();
  const noDept = env.GmailApp.drafts.find((d) => d.body.includes('株式会社見本デザイン'));      // C-003 は部署が空欄
  assert.ok(noDept, 'C-003 の下書きがない');
  assert.ok(!/^[ 　]/m.test(noDept.body), '行頭に空白がある');
  assert.match(noDept.body, /株式会社見本デザイン\s*\nご担当者様\n/);
  const withDept = env.GmailApp.drafts.find((d) => d.body.includes('株式会社サンプル商事'));
  assert.match(withDept.body, /株式会社サンプル商事 経理部\nご担当者様\n/);
});

test('29 （任意）A4に指定する版の savePdf_ に置き換えても、PDF・下書き・送付記録は同じように作る。書き出しの失敗は「エラー」で止める', () => {
  const base = fs.readFileSync(CODE, 'utf8');
  const a4 = fs.readFileSync(path.join(__dirname, 'PdfA4.gs'), 'utf8');
  const start = base.indexOf('/** 5 PDF化と保存');
  const end = base.indexOf('\n}\n', start) + 3;
  assert.ok(start > 0 && end > start, 'savePdf_ が見つからない');
  const replaced = base.slice(0, start) + a4.trim() + '\n' + base.slice(end);       // 読者がコードの中で置き換えるのと同じ
  const file = path.join(fs.mkdtempSync(path.join(require('os').tmpdir(), 'gas202a4-')), 'Code.gs');
  fs.writeFileSync(file, replaced);
  const env = createGasEnv({ now: '2026-11-30T10:00:00+09:00', sheets: { 'シート1': [] } });
  env.load(file);
  assert.ok(!/getAs\(MimeType\.PDF\)/.test(env.ctx.savePdf_.toString()), '置き換わっていない');
  env.ctx.setupSheets();
  put(env.sheet('取引先マスタ'), makeData().master);
  put(env.sheet('請求明細'), makeData().details);
  setSettings(env, { 対象月: '2026-11', 支払期限: D(2026, 12, 31), 端数処理: '切り捨て', 発行者名: '株式会社見本サービス', PDF保存フォルダID: 'FOLDER_TEST', テスト用の宛先: 'owner@example.com' });
  env.ctx.createInvoices();
  assert.equal(lastAlert(env).title, '終わりました', lastAlert(env).prompt);
  assert.equal(env.fetched.length, 28);
  const tmpId = env.created[0].getId();
  env.fetched.forEach((f) => {
    assert.ok(f.url.startsWith('https://docs.google.com/spreadsheets/d/' + tmpId + '/export?format=pdf&size=A4&portrait=true'), f.url);
    assert.match(f.url, /&gid=\d+$/);
    assert.equal(f.params.headers.Authorization, 'Bearer TEST_TOKEN');
  });
  assert.equal(env.DriveApp.files.length, 28);
  assert.ok(env.DriveApp.files.every((x) => /^【テスト】INV-202611-C-\d{3}_.+\.pdf$/.test(x.name)));
  assert.equal(env.GmailApp.drafts.length, 27);
  assert.deepEqual(env.DriveApp.trashed, [tmpId]);
  // 書き出しが失敗したとき（混み合っているときなど）：その取引先は「エラー」で止まり、再実行で作り直せる
  const env2 = createGasEnv({ now: '2026-11-30T10:00:00+09:00', sheets: { 'シート1': [] } });
  env2.load(file);
  env2.ctx.setupSheets();
  put(env2.sheet('取引先マスタ'), makeData().master);
  put(env2.sheet('請求明細'), makeData().details);
  setSettings(env2, { 対象月: '2026-11', 支払期限: D(2026, 12, 31), 端数処理: '切り捨て', 発行者名: '株式会社見本サービス', PDF保存フォルダID: 'FOLDER_TEST', テスト用の宛先: 'owner@example.com' });
  const realFetch = env2.ctx.UrlFetchApp;
  env2.ctx.UrlFetchApp = { fetch: () => ({ getResponseCode: () => 429, getBlob: () => null, getContentText: () => '' }) };
  env2.ctx.createInvoices();
  assert.match(lastAlert(env2).prompt, /C-001 のPDF作成で止まりました：PDFの書き出しに失敗しました（応答 429）/);
  assert.deepEqual(logRows(env2).map((r) => r[8]), ['エラー']);
  env2.ctx.UrlFetchApp = realFetch;
  env2.ctx.createInvoices();
  assert.equal(env2.DriveApp.files.length, 28);
});

test('30 実機確認（任意）の30社データ（sample30-*.csv、対象月2026-12）：作成する件数と合計が手順書の期待値と一致する', () => {
  const parse = (v) => {
    let m;
    if ((m = v.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/))) return D(+m[1], +m[2], +m[3]);
    if ((m = v.match(/^(\d+(?:\.\d+)?)%$/))) return Number(m[1]) / 100;
    return /^\d+(\.\d+)?$/.test(v) ? Number(v) : v;
  };
  const csv = (f, keepFirst) => fs.readFileSync(path.join(__dirname, f), 'utf8').trim().split('\n').map((l) => l.split(',').map((v, j) => (keepFirst && j === 0 ? v : parse(v))));
  const master = [['取引先コード', '取引先名', '部署', 'メール']].concat(csv('sample30-master.csv'));
  const details = [['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']].concat(csv('sample30-details.csv', true));
  const env = setup({ data: { master, details }, settings: { 対象月: '2026-12', 支払期限: D(2027, 1, 31) } });
  env.ctx.previewInvoices();
  assert.match(lastAlert(env).prompt, /作成する：28件（合計 3,654,641円）うちメール未登録（PDFだけ作る）1件/);
  env.ctx.createInvoices();
  assert.match(lastAlert(env).prompt, /下書き済み：27件\nメール未登録：1件/);
});

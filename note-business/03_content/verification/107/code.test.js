// 記事107「スプレッドシートで請求書を自動作成する仕組みの全体像」最小コード（Code.gs）のロジック検証
// 実行: TZ=Asia/Tokyo node --test code.test.js
// Googleのサービスは 05_operations/tools/gas-mock のモック。見た目と承認の画面は実機確認（device-check.md）で確かめる。
'use strict';
process.env.TZ = 'Asia/Tokyo';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createGasEnv } = require('../../../05_operations/tools/gas-mock/index.js');

const CODE_FILE = path.join(__dirname, 'Code.gs');
const CODE = fs.readFileSync(CODE_FILE, 'utf8');
const read = (f) => fs.readFileSync(path.join(__dirname, f), 'utf8').trim().split('\n');

// 端数処理などの定数を書き換えたコードを読み込む（読者がコードの1行目〜を書き換えるのと同じ）
function load({ rounding = '切り捨て', month = '2026-11', code = 'C-001', monthAsDate = false, extraLines = [] } = {}) {
  const src = CODE.replace("const ROUNDING = '';", "const ROUNDING = '" + rounding + "';")
    .replace("const TARGET_MONTH = '2026-11';", "const TARGET_MONTH = '" + month + "';")
    .replace("const TARGET_CODE = 'C-001';", "const TARGET_CODE = '" + code + "';");
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gas107-')), 'Code.gs');
  fs.writeFileSync(file, src);
  const env = createGasEnv({ sheets: { '取引先マスタ': [], '請求明細': [], '請求書レイアウト': [], '送付記録': [] } });
  env.load(file);
  const VmDate = env.run('Date'); // スプレッドシートの日付のセルと同じく、GASの側の Date で作る
  // CSVを貼って「テキストを列に分割」したときのように読む（日付・パーセント・数値に変わる）
  const parse = (v) => {
    let m;
    if ((m = v.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/))) return new VmDate(+m[1], +m[2] - 1, +m[3]);
    if ((m = v.match(/^(\d+(?:\.\d+)?)%$/))) return Number(m[1]) / 100;
    return /^\d+(\.\d+)?$/.test(v) ? Number(v) : v;
  };
  const rows = (lines) => lines.map((l) => l.split(',').map(parse));
  const put = (name, data) => env.sheet(name).getRange(1, 1, data.length, data[0].length).setValues(data);
  put('取引先マスタ', rows(read('sample-master.csv')));                 // 1行目は見出し
  const details = rows(read('sample-details.csv').concat(extraLines));
  if (monthAsDate) details.slice(1).forEach((r) => { const [y, mo] = r[0].split('-'); r[0] = new VmDate(+y, +mo - 1, 1); });
  put('請求明細', details);
  put('請求書レイアウト', read('layout.csv').map((l) => l.split(',')));
  put('送付記録', [['記録日時', 'モード', '対象月', '取引先コード', '取引先名', '請求書番号', '合計（税込）', '宛先', '状態', 'PDFファイル名', 'PDFのURL', 'メモ']]);
  return env;
}
const cell = (sh, a1) => sh.getRange(a1).getValue();
const totals = (sh) => ['F29', 'F30', 'F31', 'F32', 'F33'].map((a) => cell(sh, a));

test('1 C-001の請求書シートを作り、宛名・番号・税率ごとの合計・明細を入れる（前月の明細は入らない）', () => {
  const env = load();
  env.ctx.createOneInvoice();
  const sh = env.sheet('請求書_C-001_2026-11');
  assert.ok(sh, 'シートができていない');
  assert.equal(cell(sh, 'A3'), '株式会社サンプル商事 御中');
  assert.equal(cell(sh, 'A4'), '経理部');
  assert.equal(cell(sh, 'F3'), 'INV-202611-C-001');
  assert.equal(Object.prototype.toString.call(cell(sh, 'F4')), '[object Date]');  // 発行日（実行した日）
  assert.equal(cell(sh, 'B7'), '2026-11分のご請求');
  assert.equal(cell(sh, 'B8'), 53949);
  assert.equal(cell(sh, 'B9'), '2026年12月31日');
  assert.deepEqual(totals(sh), [46500, 4650, 2592, 207, 53949]);
  const lines = sh.getRange(13, 1, 4, 6).getValues().map((r) => r.slice(1));
  assert.deepEqual(lines, [['月額保守サービス', '10%', 1, 33000, 33000], ['作業費（1時間）', '10%', 3, 4500, 13500],
    ['コーヒー豆（軽減税率）', '8%※', 2, 1296, 2592], ['', '', '', '', '']]);
  assert.equal(cell(sh, 'E6'), '（自社名）');                     // 自社の情報はひな形に直接書く
  assert.ok(!JSON.stringify(sh.getDataRange().getValues()).includes('{{'));
  assert.equal(env.sheet('請求書レイアウト').getRange('A3').getValue(), '{{取引先名}} 御中'); // ひな形は変わらない
});

test('2 端数処理の3方式：手順書の期待値と一致する（C-001は8%の消費税207.36円の処理で差が出る）', () => {
  const expect = { 'C-001': [53949, 53949, 53950], 'C-002': [1078, 1078, 1078] };
  Object.entries(expect).forEach(([code, want]) => {
    ['切り捨て', '四捨五入', '切り上げ'].forEach((rounding, i) => {
      const env = load({ rounding, code });
      env.ctx.createOneInvoice();
      assert.equal(cell(env.sheet('請求書_' + code + '_2026-11'), 'F33'), want[i], code + ' ' + rounding);
    });
  });
  const env = load({ code: 'C-002' });
  env.ctx.createOneInvoice();
  assert.deepEqual(totals(env.sheet('請求書_C-002_2026-11')), [980, 98, 0, 0, 1078]);
});

test('3 端数処理を選んでいないと止まり、何も作らない', () => {
  const env = load({ rounding: '' });
  assert.throws(() => env.ctx.createOneInvoice(), /ROUNDING に端数処理の方式を入れてください/);
  assert.equal(env.ss.getSheets().length, 4);
});

test('4 同じ取引先・同じ月のシートがあれば止まる（二重に作らない）', () => {
  const env = load();
  env.ctx.createOneInvoice();
  assert.throws(() => env.ctx.createOneInvoice(), /もうあります/);
  assert.equal(env.ss.getSheets().length, 5);
});

test('5 取引先マスタにないコード・明細のない月・16行以上の明細は止まる', () => {
  assert.throws(() => load({ code: 'C-099' }).ctx.createOneInvoice(), /取引先マスタに C-099 がありません/);
  assert.throws(() => load({ month: '2026-12' }).ctx.createOneInvoice(), /明細が 0 行です/);
  const extra = Array.from({ length: 13 }, (_, i) => '2026-11,2026/11/' + (10 + i) + ',C-001,,,追加,1,100,10%,');
  const env = load({ extraLines: extra });
  assert.throws(() => env.ctx.createOneInvoice(), /明細が 16 行です/);
  assert.equal(env.ss.getSheets().length, 4);
});

test('9 税率が10%・8%以外（5%・空欄）の明細があると、品目名を示して止まり、シートを作らない（黙って合計から外さない）', () => {
  [['5%', '消耗品（税率5%）'], ['', '印刷（税率が空欄）']].forEach(([rate, item]) => {
    const env = load({ extraLines: ['2026-11,2026/11/20,C-001,,P-07,' + item + ',1,1234,' + rate + ','] });
    assert.throws(() => env.ctx.createOneInvoice(), new RegExp('税率は10%か8%にしてください（' + item.replace(/[()（）%]/g, '.') + '）'));
    assert.equal(env.ss.getSheets().length, 4, 'シートを作らない');
  });
  const ok = load({ extraLines: ['2026-11,2026/11/20,C-001,,P-07,消耗品,1,1234,10,'] }); // 「10」と入れた税率は10%として読む
  ok.ctx.createOneInvoice();
  assert.equal(cell(ok.sheet('請求書_C-001_2026-11'), 'F29'), 46500 + 1234);
});

test('6 対象月の列が日付に変わっていても読める', () => {
  const env = load({ monthAsDate: true });
  env.ctx.createOneInvoice();
  assert.deepEqual(totals(env.sheet('請求書_C-001_2026-11')), [46500, 4650, 2592, 207, 53949]);
});

test('7 最小コードの範囲：50行以内、このファイルだけの権限（@OnlyCurrentDoc）、PDF化・メール送付をしない', () => {
  assert.ok(CODE.trim().split('\n').length <= 50, '行数 ' + CODE.trim().split('\n').length);
  assert.match(CODE, /@OnlyCurrentDoc/);
  ['GmailApp', 'MailApp', 'DriveApp', 'UrlFetchApp', 'getAs('].forEach((w) => assert.ok(!CODE.includes(w), w));
});

test('8 記事の本文のコード・ひな形・データが、検証に使ったファイルと同じ', (t) => {
  const art = path.join(__dirname, '../../articles/107-gas-invoice-overview.md');
  if (!fs.existsSync(art)) return t.skip('記事がまだない');
  const md = fs.readFileSync(art, 'utf8');
  const blocks = [...md.matchAll(/```\n([\s\S]*?)\n```/g)].map((m) => m[1]);
  assert.ok(blocks.includes(CODE.trim()), 'コード');
  ['layout.csv', 'sample-master.csv', 'sample-details.csv'].forEach((f) => assert.ok(blocks.includes(read(f).join('\n')), f));
});

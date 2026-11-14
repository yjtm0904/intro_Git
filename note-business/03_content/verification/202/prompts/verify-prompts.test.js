// 記事202「自社用に改造する依頼文3本」の検証：Claudeの出力（*.output.md）のコードを Code.gs のコピーに当てはめ、
// 頼んだ変更が動くか・テストモードと二重作成の防止が保たれるかを gas-mock で確かめる。
// 実行: TZ=Asia/Tokyo node --test verify-prompts.test.js
'use strict';
process.env.TZ = 'Asia/Tokyo';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createGasEnv } = require('../../../../05_operations/tools/gas-mock/index.js');

const BASE = fs.readFileSync(path.join(__dirname, '..', 'Code.gs'), 'utf8');
const D = (y, m, d) => new Date(y, m - 1, d);

// 出力のコードブロック（関数・定数）を、元のコードの同じ名前の部分と入れ替える
function apply(outputFile) {
  const md = fs.readFileSync(path.join(__dirname, outputFile), 'utf8');
  const blocks = [...md.matchAll(/```(?:javascript|js)\n([\s\S]*?)```/g)].map((m) => m[1].replace(/\n$/, ''));
  let lines = BASE.split('\n');
  const replaced = [];
  blocks.forEach((b) => {
    const constName = (b.match(/^const (\w+)\s*=/) || [])[1];
    const fnName = (b.match(/^function (\w+)\(/m) || [])[1];
    if (constName && !fnName) {
      const i = lines.findIndex((l) => l.startsWith('const ' + constName + ' '));
      assert.ok(i >= 0, '定数が見つからない: ' + constName);
      lines.splice(i, 1, ...b.split('\n'));
      replaced.push(constName);
      return;
    }
    assert.ok(fnName, 'コードブロックに関数がない');
    const start0 = lines.findIndex((l) => l.startsWith('function ' + fnName + '('));
    assert.ok(start0 >= 0, '関数が見つからない: ' + fnName);
    const start = lines[start0 - 1] && lines[start0 - 1].startsWith('/**') ? start0 - 1 : start0;
    const end = lines.findIndex((l, i) => i > start0 && l === '}');
    lines.splice(start, end - start + 1, ...b.split('\n'));
    replaced.push(fnName);
  });
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gas202-')), 'Code.gs');
  fs.writeFileSync(file, lines.join('\n'));
  return { file, replaced };
}

function setup(codeFile, { masterHead, master, detailHead, details, settings = {} }) {
  const env = createGasEnv({ now: '2026-11-30T10:00:00+09:00', sheets: { 'シート1': [] } });
  env.load(codeFile);
  env.ctx.setupSheets();
  env.ui.alerts.length = 0;
  const putRows = (name, rows) => { const sh = env.sheet(name); sh.clear(); sh.getRange(1, 1, rows.length, rows[0].length).setValues(rows); };
  putRows('取引先マスタ', [masterHead].concat(master));
  putRows('請求明細', [detailHead].concat(details));
  const sh = env.sheet('設定'), keys = sh.getDataRange().getValues().map((r) => r[0]);
  Object.entries(Object.assign({ 対象月: '2026-11', 支払期限: D(2026, 12, 31), 端数処理: '切り捨て', 発行者名: '株式会社見本サービス',
    PDF保存フォルダID: 'FOLDER_TEST', テスト用の宛先: 'owner@example.com' }, settings)).forEach(([k, v]) => sh.getRange(keys.indexOf(k) + 1, 2).setValue(v));
  return env;
}
const last = (env) => env.ui.alerts[env.ui.alerts.length - 1];
const DETAIL_HEAD = ['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額'];
const LINES = [
  ['2026-11', D(2026, 11, 5), 'C-001', '', '', '月額保守サービス', 1, 33000, 0.1, ''],
  ['2026-11', D(2026, 11, 19), 'C-001', '', '', 'コーヒー豆（軽減税率）', 2, 1296, 0.08, ''],
  ['2026-11', D(2026, 11, 6), 'C-002', '', '', '送料', 1, 980, 0.1, ''],
];
const SET_SETTING = (env, k, v) => { const sh = env.sheet('設定'); sh.getRange(sh.getDataRange().getValues().map((r) => r[0]).indexOf(k) + 1, 2).setValue(v); };

test('依頼文1（列）：請求明細の「注文番号」を請求書の明細に表示できる。合計・テストモード・二重作成の防止は変わらない', (t) => {
  const { file, replaced } = apply('1-column.output.md');
  t.diagnostic('出力で置き換えた関数・定数: ' + replaced.join(', '));
  const env = setup(file, {
    masterHead: ['取引先コード', '取引先名', '部署', 'メール'],
    master: [['C-001', '株式会社サンプル商事', '経理部', 'sample-shoji@example.com'], ['C-002', 'サンプル工業株式会社', '', 'sample-kogyo@example.com']],
    detailHead: DETAIL_HEAD.concat(['注文番号']),
    details: [LINES[0].concat(['PO-001']), LINES[1].concat(['00123']), LINES[2].concat([''])],
  });
  env.sheet('請求書レイアウト').getRange('G12').setValue('注文番号');
  env.sheet('請求書レイアウト').getRange('G13').setValue('{{明細:注文番号}}');
  env.ctx.createInvoices();
  assert.equal(last(env).title, '終わりました', last(env).prompt);
  const sh = env.DriveApp.files[0].blob.snapshot[0].data;
  assert.deepEqual(sh.slice(12, 14).map((r) => [r[1], r[6]]), [['月額保守サービス', 'PO-001'], ['コーヒー豆（軽減税率）', '00123']]);
  assert.equal(sh[32][5], 33000 + 3300 + 2592 + 207);                     // 合計は変わらない
  assert.ok(env.GmailApp.drafts.every((d) => d.to === 'owner@example.com')); // テストモードのまま
  env.ctx.createInvoices();
  assert.equal(last(env).title, '作るものはありません');
  assert.equal(env.DriveApp.files.length, 2);
});

test('依頼文2（CC）：本番だけCCを付けてメモに残し、テストモードではCCを付けない。再実行で増えない', (t) => {
  const { file, replaced } = apply(process.env.OUTPUT2 || '2-cc.output.md');
  t.diagnostic('出力で置き換えた関数・定数: ' + replaced.join(', '));
  const env = setup(file, {
    masterHead: ['取引先コード', '取引先名', '部署', 'メール', 'CC'],
    master: [['C-001', '株式会社サンプル商事', '経理部', 'sample-shoji@example.com', 'cc1@example.com, cc2@example.com'], ['C-002', 'サンプル工業株式会社', '', 'sample-kogyo@example.com', '']],
    detailHead: DETAIL_HEAD, details: LINES,
  });
  env.ctx.createInvoices();                                                  // テストモード
  assert.equal(last(env).title, '終わりました', last(env).prompt);
  assert.ok(env.GmailApp.drafts.every((d) => d.to === 'owner@example.com' && !d.options.cc));
  assert.match(env.GmailApp.drafts[0].body, /本番のCC：cc1@example\.com,cc2@example\.com/);
  SET_SETTING(env, 'テストモード', 'OFF');
  env.ctx.createInvoices();                                                  // 本番・下書き
  const prod = env.GmailApp.drafts.slice(2);
  assert.equal(prod[0].to, 'sample-shoji@example.com');
  assert.equal(prod[0].options.cc, 'cc1@example.com,cc2@example.com');
  assert.equal(prod[1].options.cc, undefined);
  const log = env.sheet('送付記録').getDataRange().getValues().slice(1);
  assert.equal(log.find((r) => r[1] === '本番' && r[3] === 'C-001')[11], 'CC：cc1@example.com,cc2@example.com');
  env.ctx.createInvoices();
  assert.equal(last(env).title, '作るものはありません');
  assert.equal(env.GmailApp.drafts.length, 4);
  // 誤ったCC（全角の読点で区切る）は、作る前に止まる
  env.sheet('取引先マスタ').getRange('E2').setValue('a@example.com、b@example.com');
  env.ctx.previewInvoices();
  assert.match(last(env).prompt, /CCのメールアドレスの形式/);
});

test('依頼文3（文面）：取引先ごとの「ひとこと」を本文に差し込み、空欄なら何も入れない。件名には使えない', (t) => {
  const { file, replaced } = apply(process.env.OUTPUT3 || '3-message.output.md');
  t.diagnostic('出力で置き換えた関数・定数: ' + replaced.join(', '));
  const body = '{{取引先名}}\nご担当者様\n\n{{対象月}}分の請求書をお送りします。\n{{ひとこと}}\n\nよろしくお願いいたします。';
  const env = setup(file, {
    masterHead: ['取引先コード', '取引先名', '部署', 'メール', 'ひとこと'],
    master: [['C-001', '株式会社サンプル商事', '経理部', 'sample-shoji@example.com', '年末年始は12月29日から1月4日まで休業します。'], ['C-002', 'サンプル工業株式会社', '', 'sample-kogyo@example.com', '']],
    detailHead: DETAIL_HEAD, details: LINES, settings: { 本文: body },
  });
  env.ctx.createInvoices();
  assert.equal(last(env).title, '終わりました', last(env).prompt);
  assert.match(env.GmailApp.drafts[0].body, /お送りします。\n年末年始は12月29日から1月4日まで休業します。\n/);
  assert.match(env.GmailApp.drafts[1].body, /お送りします。\n\n\nよろしく/);
  assert.ok(!env.GmailApp.drafts.some((d) => d.body.includes('{{')));
  assert.ok(env.GmailApp.drafts.every((d) => d.to === 'owner@example.com'));
  env.ctx.createInvoices();
  assert.equal(last(env).title, '作るものはありません');
  SET_SETTING(env, '件名', '【請求書】{{ひとこと}}');
  env.ctx.previewInvoices();
  assert.match(last(env).prompt, /使えない差し込み項目があります：\{\{ひとこと\}\}/);
});

// 記事202の「完成イメージ」を、テストと同じ仕組み（gas-mock）の出力から作る。
// 1. templates.md の架空3社のデータで Code.gs を動かし、C-001 の請求書シートの中身（PDFにした時点）とメール下書きを取り出す
// 2. 下書きの文面を sample-draft.txt に保存する（記事の無料部分に載せる）
// 3. 請求書シートの中身を、レイアウトの列幅・結合・表示形式どおりにHTMLで並べ、PNG（見本（イメージ））にする
//    実際のPDFではない。オーナーの実機確認のあと、実際の画面に差し替える（owner-check.md）
// 実行: TZ=Asia/Tokyo node render_sample.js   （Playwright と header-image のフォントを使う）
'use strict';
process.env.TZ = 'Asia/Tokyo';
const fs = require('fs');
const path = require('path');
const { createGasEnv } = require('../../../05_operations/tools/gas-mock/index.js');

const OUT_PNG = path.join(__dirname, '../../images/202-sample-invoice.png');
const FONT_DIR = path.join(__dirname, '../../../05_operations/tools/header-image/node_modules/@fontsource/noto-sans-jp/files');
const D = (y, m, d) => new Date(y, m - 1, d);

function run() {
  const md = fs.readFileSync(path.join(__dirname, 'templates.md'), 'utf8');
  const block = (name) => md.split('<!-- testdata:' + name + ' -->')[1].split('```')[1].trim().split('\n');
  const parse = (v, keepText) => {
    if (keepText || v === '') return v;
    let m;
    if ((m = v.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/))) return D(+m[1], +m[2], +m[3]);
    if ((m = v.match(/^(\d+(?:\.\d+)?)%$/))) return Number(m[1]) / 100;
    return /^\d+(\.\d+)?$/.test(v) ? Number(v) : v;
  };
  const env = createGasEnv({ now: '2026-11-30T10:00:00+09:00', sheets: { 'シート1': [] } });
  env.load(path.join(__dirname, 'Code.gs'));
  env.ctx.setupSheets();
  const put = (name, rows) => env.sheet(name).getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  put('取引先マスタ', [['取引先コード', '取引先名', '部署', 'メール']].concat(block('master').map((l) => l.split(',').map((v) => parse(v)))));
  put('請求明細', [['対象月', '取引日', '取引先コード', '取引先名', '商品コード', '品目', '数量', '単価', '税率', '金額']]
    .concat(block('details').map((l) => l.split(',').map((v, j) => parse(v, j === 0)))));
  const st = env.sheet('設定'), keys = st.getDataRange().getValues().map((r) => r[0]);
  const settings = Object.fromEntries(block('settings').map((l) => l.split(',')).map(([k, v]) => [k, parse(v, k === '対象月')]));
  settings['PDF保存フォルダID'] = 'FOLDER_SAMPLE';
  settings['テスト用の宛先'] = 'owner@example.com';
  Object.entries(settings).forEach(([k, v]) => st.getRange(keys.indexOf(k) + 1, 2).setValue(v));
  env.ctx.createInvoices();
  const file = env.DriveApp.files[0];
  const draft = env.GmailApp.drafts[0];
  if (!file || !draft) throw new Error('サンプルが作れなかった: ' + JSON.stringify(env.ui.alerts.slice(-1)));
  return { sheet: file.blob.snapshot.find((s) => s.name === '請求書').data, fileName: file.name, draft };
}

const yen = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
const ymdJa = (d) => `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
const ymdSlash = (d) => `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// setupSheets の書式（Code.gs）を写したもの
const WIDTHS = [130, 160, 50, 50, 80, 120];
const MERGES = ['A1:F1', 'A3:C3', 'A4:C4', 'A6:C6', 'E6:F6', 'E7:F7', 'E8:F8', 'B10:F10', 'A35:F35', 'A36:F36', 'D29:E29', 'D30:E30', 'D31:E31', 'D32:E32', 'D33:E33'];
function fmt(r, c, v) {
  if (v === '' || v === null || v === undefined) return '';
  const isDate = Object.prototype.toString.call(v) === '[object Date]';
  if ((r === 4 && c === 6) || (r === 9 && c === 2)) return isDate ? ymdJa(v) : v;      // F4・B9
  if (r === 8 && c === 2) return typeof v === 'number' ? yen(v) + '円' : v;             // B8
  if (r >= 13 && r <= 27 && c === 1) return isDate ? ymdSlash(v) : v;                  // A13:A27
  if (((r >= 13 && r <= 27) && c >= 4) || (r >= 29 && r <= 33 && c === 6)) return typeof v === 'number' ? yen(v) : v;
  return isDate ? ymdSlash(v) : v;
}
function html(sheet) {
  const span = {}, covered = {};
  MERGES.forEach((a) => {
    const [, c1, r1, c2, r2] = a.match(/^([A-F])(\d+):([A-F])(\d+)$/);
    const cs = c2.charCodeAt(0) - c1.charCodeAt(0) + 1;
    span[`${r1},${c1.charCodeAt(0) - 64}`] = cs;
    for (let c = c1.charCodeAt(0) - 63; c <= c2.charCodeAt(0) - 64; c++) covered[`${r1},${c}`] = true;
  });
  const S = 1.25; // 見やすさのための拡大
  let rows = '';
  for (let r = 1; r <= 36; r++) {
    let tds = '';
    for (let c = 1; c <= 6; c++) {
      if (covered[`${r},${c}`]) continue;
      const v = (sheet[r - 1] || [])[c - 1];
      const cls = [];
      if (r === 1) cls.push('title');
      if (r === 3 && c === 1) cls.push('to');
      if (r === 8 && c === 2) cls.push('amount');
      if (r === 12) cls.push('head');
      if ((r >= 12 && r <= 27) || (r >= 29 && r <= 33 && c >= 4)) cls.push('grid');
      if (r === 33 && c >= 4) cls.push('bold');
      const num = typeof v === 'number' || (r >= 13 && r <= 27 && c >= 4) || (r >= 29 && c === 6);
      if (num && r !== 12) cls.push('num');
      if (r === 7 && c === 5) cls.push('wrap');
      tds += `<td${span[`${r},${c}`] ? ` colspan="${span[`${r},${c}`]}"` : ''} class="${cls.join(' ')}">${esc(fmt(r, c, v))}</td>`;
    }
    rows += `<tr>${tds}</tr>`;
  }
  const faces = ['400', '700'].map((w) => {
    const f = path.join(FONT_DIR, `noto-sans-jp-japanese-${w}-normal.woff2`);
    const l = path.join(FONT_DIR, `noto-sans-jp-latin-${w}-normal.woff2`);
    return `@font-face{font-family:'NotoJP';font-weight:${w};src:url('file://${l}') format('woff2'),url('file://${f}') format('woff2');}` +
      `@font-face{font-family:'NotoJPj';font-weight:${w};src:url('file://${f}') format('woff2');}`;
  }).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><style>${faces}
body{margin:0;background:#e5e7eb;font-family:'NotoJP','NotoJPj',sans-serif;color:#111}
.page{position:relative;width:794px;height:1123px;margin:24px auto;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.18);overflow:hidden}
.inner{position:absolute;left:${(794 - WIDTHS.reduce((a, b) => a + b, 0) * S) / 2}px;top:56px}
table{border-collapse:collapse;table-layout:fixed;width:${WIDTHS.reduce((a, b) => a + b, 0) * S}px;font-size:${10 * S}pt}
td{box-sizing:border-box;height:${21 * S}px;padding:0 ${4 * S}px;white-space:nowrap;overflow:hidden;vertical-align:middle;line-height:1.2}
td.title{font-size:${16 * S}pt;font-weight:700;text-align:center;height:${30 * S}px}
td.to{font-size:${12 * S}pt;font-weight:700}
td.amount{font-size:${13 * S}pt;font-weight:700}
td.head{font-weight:700;background:#eeeeee}
td.grid{border:1px solid #444}
td.num{text-align:right}
td.bold{font-weight:700}
td.wrap{white-space:normal}
.badge{position:absolute;right:24px;top:16px;background:#b91c1c;color:#fff;font-weight:700;font-size:15px;padding:6px 14px;border-radius:6px}
.note{position:absolute;left:24px;right:24px;bottom:22px;text-align:center;color:#6b7280;font-size:12px}
.mark{position:absolute;left:50%;top:52%;transform:translate(-50%,-50%) rotate(-24deg);font-size:150px;font-weight:700;color:rgba(185,28,28,.07);letter-spacing:.2em}
</style></head><body><div class="page"><div class="mark">見本</div><div class="badge">見本（イメージ）</div>
<div class="inner"><table><colgroup>${WIDTHS.map((w) => `<col style="width:${w * S}px">`).join('')}</colgroup>${rows}</table></div>
<div class="note">テストの出力（架空のデータ）をレイアウトどおりに並べた見本です。実際のPDFの画面ではありません</div>
</div></body></html>`;
}

async function main() {
  const { sheet, fileName, draft } = run();
  const att = draft.options.attachments.map((b) => b.getName()).join('、');
  const txt = [`宛先：${draft.to}`, `件名：${draft.subject}`, `添付：${att}`, '', draft.body].join('\n');
  fs.writeFileSync(path.join(__dirname, 'sample-draft.txt'), txt + '\n');
  fs.writeFileSync(path.join(__dirname, 'sample-invoice.html'), html(sheet));
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 842, height: 1171 }, deviceScaleFactor: 1.5 });
  await page.setContent(html(sheet), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.locator('.page').screenshot({ path: OUT_PNG });
  await browser.close();
  console.log('PDFの名前（テストの出力）:', fileName);
  console.log('画像:', OUT_PNG);
  console.log(txt);
}
main().catch((e) => { console.error(e); process.exit(1); });

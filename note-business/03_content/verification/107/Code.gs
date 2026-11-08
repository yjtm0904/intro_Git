/**
 * @OnlyCurrentDoc
 * 1社分の請求書シートを作る（最小版。PDF化・メール送付はしない）事務の型紙 107 v1.0（2026-11-08）
 */
const TARGET_MONTH = '2026-11'; // 対象月
const TARGET_CODE = 'C-001';    // 取引先コード
const DUE_DATE = '2026年12月31日'; // 支払期限
const ROUNDING = '';            // 端数処理：「切り捨て」「四捨五入」「切り上げ」から、社内のルールで選んで入れる

function createOneInvoice() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const round = { 切り捨て: Math.floor, 四捨五入: Math.round, 切り上げ: Math.ceil }[ROUNDING];
  if (!round) throw new Error('ROUNDING に端数処理の方式を入れてください');
  const name = '請求書_' + TARGET_CODE + '_' + TARGET_MONTH;
  if (ss.getSheetByName(name)) throw new Error('「' + name + '」はもうあります（二重に作らないように止めました）');
  const client = ss.getSheetByName('取引先マスタ').getDataRange().getValues().find(r => r[0] === TARGET_CODE);
  if (!client) throw new Error('取引先マスタに ' + TARGET_CODE + ' がありません');
  const lines = ss.getSheetByName('請求明細').getDataRange().getValues().slice(1)
    .filter(r => monthOf(r[0]) === TARGET_MONTH && r[2] === TARGET_CODE);
  if (lines.length === 0 || lines.length > 15) throw new Error('明細が ' + lines.length + ' 行です（1〜15行で作れます）');
  const base = { 10: 0, 8: 0 };
  lines.forEach(r => { base[rateOf(r[8])] += r[6] * r[7]; });               // 数量×単価を税率ごとに合計
  const tax10 = round(base[10] * 10 / 100), tax8 = round(base[8] * 8 / 100); // 端数処理は税率ごとに1回
  const f = { 取引先名: client[1], 部署: client[2], 請求書番号: 'INV-' + TARGET_MONTH.replace('-', '') + '-' + TARGET_CODE,
    発行日: new Date(), 支払期限: DUE_DATE, 対象月: TARGET_MONTH, '10%対象': base[10], '10%消費税': tax10,
    '8%対象': base[8], '8%消費税': tax8, 合計: base[10] + tax10 + base[8] + tax8 };
  const sheet = ss.getSheetByName('請求書レイアウト').copyTo(ss).setName(name);
  const range = sheet.getDataRange();
  const values = range.getValues().map(row => row.map(v => {
    if (typeof v !== 'string' || v.indexOf('{{明細:') === 0) return v;
    const one = v.match(/^\{\{([^{}]+)\}\}$/);
    if (one && one[1] in f) return f[one[1]];                                 // 1つだけなら数値・日付のまま入れる
    return v.replace(/\{\{([^{}]+)\}\}/g, (m, k) => (k in f ? f[k] : m));
  }));
  range.setValues(values);
  const top = values.findIndex(row => String(row[0]).indexOf('{{明細:') === 0) + 1; // 明細を書き始める行
  sheet.getRange(top, 1, lines.length, 6).setValues(lines.map(r =>
    [r[1], r[5], rateOf(r[8]) === 8 ? '8%※' : '10%', r[6], r[7], r[6] * r[7]]));
  ss.setActiveSheet(sheet);
}

function monthOf(v) { // 「2026-11」が日付に変わっていても読む
  return v instanceof Date ? Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM') : String(v).trim();
}
function rateOf(v) { // 「10%」のセルは 0.1 と読まれるので 10 に直す
  const n = Number(String(v).replace('%', ''));
  return n < 1 ? Math.round(n * 100) : n;
}

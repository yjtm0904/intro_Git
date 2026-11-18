// gas-mock の使い方の見本（node --test で実行）
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { createGasEnv } = require('./index.js');

// 記事で配布する想定の小さなGAS（未送信の行だけメールを送り、送信日時を書き込む）
const GAS_CODE = `
function sendPending() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('送信リスト');
  var values = sh.getRange(2, 1, sh.getLastRow() - 1, 3).getValues();
  values.forEach(function (row, i) {
    var name = row[0], email = row[1], sentAt = row[2];
    if (!email || sentAt) return;
    GmailApp.sendEmail(email, '【ご案内】' + name + '様', name + '様\\nいつもお世話になっております。');
    sh.getRange(i + 2, 3).setValue(Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm'));
  });
}`;

test('未送信の行だけ送信し、送信日時を記録する', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gas-')), 'Code.gs');
  fs.writeFileSync(file, GAS_CODE);
  const env = createGasEnv({
    now: '2026-11-08T09:30:00+09:00',
    sheets: { '送信リスト': [['名前', 'メール', '送信日時'], ['A社', 'a@example.com', ''], ['B社', 'b@example.com', '2026-11-01 10:00'], ['C社', '', '']] },
  });
  env.load(file);
  env.ctx.sendPending();
  assert.strictEqual(env.GmailApp.sent.length, 1);
  assert.strictEqual(env.GmailApp.sent[0].to, 'a@example.com');
  assert.strictEqual(env.sheet('送信リスト').getRange('C2').getValue(), '2026-11-08 09:30');
  assert.strictEqual(env.sheet('送信リスト').getRange('C3').getValue(), '2026-11-01 10:00');
});

test('範囲と配列の大きさが違うとエラーになる（GASと同じ挙動）', () => {
  const env = createGasEnv({ sheets: { 'S': [['a']] } });
  assert.throws(() => env.sheet('S').getRange(1, 1, 1, 2).setValues([[1]]));
});

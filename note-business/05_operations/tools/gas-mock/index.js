/*
 * GAS（Google Apps Script）ロジック検証用のモック（Node.js）
 *
 * 目的: 記事で配布するGASコードのロジックを、Google環境なしでテストし「検証ログ」を残す。
 *       Google上での実機確認（権限承認・実際のメール送信・PDF化）は、公開前にオーナーが行う。
 *
 * 使い方（テストファイル側）:
 *   const { createGasEnv } = require('<このファイル>');
 *   const env = createGasEnv({ sheets: { '請求先': [['会社名','メール'], ['A社','a@example.com']] } });
 *   env.load('/path/to/Code.gs');            // .gs を読み込む（関数は env.ctx に定義される）
 *   env.ctx.main();                           // 関数を実行
 *   env.GmailApp.sent                          // 送信されたメールの記録を検証
 *
 * 対応範囲: SpreadsheetApp / Sheet / Range（A1表記・行列指定）, GmailApp, MailApp, DriveApp, Utilities,
 *           Logger, PropertiesService, Session, LockService, MimeType, UrlFetchApp/ScriptApp（記録のみ）
 * 未対応の機能を呼ぶとエラーになる（＝テストで気づける）。
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

function colToNum(col) {
  return col.toUpperCase().split('').reduce((n, c) => n * 26 + (c.charCodeAt(0) - 64), 0);
}
function numToCol(n) {
  let s = '';
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

class Blob {
  constructor(data, contentType, name) { this.data = data; this.contentType = contentType || 'text/plain'; this.name = name || ''; }
  getName() { return this.name; }
  setName(n) { this.name = n; return this; }
  getContentType() { return this.contentType; }
  getDataAsString() { return String(this.data); }
  getBytes() { return Buffer.from(String(this.data)); }
  getAs(type) { return new Blob(this.data, type, this.name); }
}

class Range {
  constructor(sheet, row, col, numRows, numCols) {
    Object.assign(this, { sheet, row, col, numRows, numCols });
  }
  _ensure() {
    const d = this.sheet.data;
    while (d.length < this.row + this.numRows - 1) d.push([]);
    for (let r = this.row - 1; r < this.row - 1 + this.numRows; r++) {
      while (d[r].length < this.col + this.numCols - 1) d[r].push('');
    }
  }
  getValues() {
    const out = [];
    for (let r = 0; r < this.numRows; r++) {
      const src = this.sheet.data[this.row - 1 + r] || [];
      const rowVals = [];
      for (let c = 0; c < this.numCols; c++) {
        const v = src[this.col - 1 + c];
        rowVals.push(v === undefined ? '' : v);
      }
      out.push(rowVals);
    }
    return out;
  }
  getDisplayValues() { return this.getValues().map((r) => r.map((v) => (v instanceof Date ? v.toISOString() : String(v)))); }
  getValue() { return this.getValues()[0][0]; }
  setValues(values) {
    if (values.length !== this.numRows || values.some((r) => r.length !== this.numCols)) {
      throw new Error(`setValues: 範囲(${this.numRows}x${this.numCols})と配列(${values.length}x${values[0] && values[0].length})の大きさが一致しません`);
    }
    this._ensure();
    values.forEach((r, i) => r.forEach((v, j) => { this.sheet.data[this.row - 1 + i][this.col - 1 + j] = v; }));
    return this;
  }
  setValue(v) { this._ensure(); this.sheet.data[this.row - 1][this.col - 1] = v; return this; }
  clearContent() {
    this._ensure();
    for (let r = 0; r < this.numRows; r++) for (let c = 0; c < this.numCols; c++) this.sheet.data[this.row - 1 + r][this.col - 1 + c] = '';
    return this;
  }
  getRow() { return this.row; }
  getColumn() { return this.col; }
  getNumRows() { return this.numRows; }
  getNumColumns() { return this.numCols; }
  getA1Notation() {
    const a = `${numToCol(this.col)}${this.row}`;
    return this.numRows === 1 && this.numCols === 1 ? a : `${a}:${numToCol(this.col + this.numCols - 1)}${this.row + this.numRows - 1}`;
  }
  setNumberFormat() { return this; }
  setFontWeight() { return this; }
  setBackground() { return this; }
}

class Sheet {
  constructor(name, data, parent) { this.name = name; this.data = (data || []).map((r) => r.slice()); this.parent = parent; }
  getName() { return this.name; }
  getParent() { return this.parent; }
  getLastRow() {
    for (let r = this.data.length - 1; r >= 0; r--) if (this.data[r].some((v) => v !== '' && v !== null && v !== undefined)) return r + 1;
    return 0;
  }
  getLastColumn() { return this.data.reduce((m, r) => { let c = r.length; while (c > 0 && (r[c - 1] === '' || r[c - 1] == null)) c--; return Math.max(m, c); }, 0); }
  getRange(a, b, c, d) {
    if (typeof a === 'string') {
      const m = a.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/i);
      if (!m) throw new Error(`getRange: 未対応のA1表記 ${a}`);
      const r1 = +m[2], c1 = colToNum(m[1]);
      const r2 = m[4] ? +m[4] : r1, c2 = m[3] ? colToNum(m[3]) : c1;
      return new Range(this, r1, c1, r2 - r1 + 1, c2 - c1 + 1);
    }
    if (a < 1 || b < 1) throw new Error(`getRange: 行・列は1以上です（row=${a}, col=${b}）`);
    if (c !== undefined && c < 1) throw new Error(`getRange: 行数は1以上です（numRows=${c}）`);
    return new Range(this, a, b, c || 1, d || 1);
  }
  getDataRange() { return new Range(this, 1, 1, Math.max(this.getLastRow(), 1), Math.max(this.getLastColumn(), 1)); }
  appendRow(row) { this.data.splice(this.getLastRow(), 0, row.slice()); return this; }
  clear() { this.data = []; return this; }
  getSheetId() { return this.name.length; }
}

class Spreadsheet {
  constructor(id, name, sheets) {
    this.id = id; this.name = name;
    this.sheets = Object.entries(sheets || {}).map(([n, d]) => new Sheet(n, d, this));
  }
  getId() { return this.id; }
  getName() { return this.name; }
  getUrl() { return `https://docs.google.com/spreadsheets/d/${this.id}/edit`; }
  getSheets() { return this.sheets; }
  getSheetByName(n) { return this.sheets.find((s) => s.name === n) || null; }
  insertSheet(n) { const s = new Sheet(n, [], this); this.sheets.push(s); return s; }
  getActiveSheet() { return this.sheets[0]; }
  getAs(type) { return new Blob(`[PDF of ${this.name}]`, type, `${this.name}.pdf`); }
  getBlob() { return this.getAs('application/pdf'); }
}

function formatDate(date, tz, fmt) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: tz || 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).map((p) => [p.type, p.value]));
  return fmt.replace(/yyyy|MM|dd|HH|mm|ss|M|d/g, (t) => ({
    yyyy: parts.year, MM: parts.month, dd: parts.day, HH: parts.hour, mm: parts.minute, ss: parts.second,
    M: String(+parts.month), d: String(+parts.day),
  }[t]));
}

function createGasEnv(opts = {}) {
  const ss = new Spreadsheet(opts.spreadsheetId || 'TEST_SPREADSHEET_ID', opts.spreadsheetName || 'テスト用スプレッドシート', opts.sheets);
  const others = {};
  const props = { ...(opts.scriptProperties || {}) };
  const log = [];
  const GmailApp = {
    sent: [], drafts: [],
    sendEmail(to, subject, body, options) { this.sent.push({ to, subject, body, options: options || {} }); },
    createDraft(to, subject, body, options) { const d = { to, subject, body, options: options || {} }; this.drafts.push(d); return { getId: () => `draft-${this.drafts.length}` }; },
  };
  const DriveApp = {
    files: [],
    _folder(id) {
      return {
        getId: () => id,
        createFile: (blob) => { const f = { folderId: id, name: blob.getName(), blob }; DriveApp.files.push(f); return { getId: () => `file-${DriveApp.files.length}`, getName: () => blob.getName(), getUrl: () => `https://drive.google.com/file/d/file-${DriveApp.files.length}` }; },
      };
    },
    getFolderById(id) { return this._folder(id); },
    getRootFolder() { return this._folder('root'); },
    createFile(blob) { return this._folder('root').createFile(blob); },
    getFileById(id) { return { getId: () => id, getAs: (t) => new Blob(`[file ${id}]`, t, `${id}.pdf`), getBlob: () => new Blob(`[file ${id}]`, 'application/pdf', `${id}.pdf`) }; },
  };
  const fetched = [];
  const ctx = {
    console,
    SpreadsheetApp: {
      getActiveSpreadsheet: () => ss,
      getActive: () => ss,
      openById: (id) => { if (id === ss.id) return ss; if (others[id]) return others[id]; throw new Error(`openById: 存在しないID ${id}`); },
      create: (name) => { const s = new Spreadsheet(`NEW_${Object.keys(others).length + 1}`, name, { 'シート1': [] }); others[s.id] = s; return s; },
      getUi: () => ({ alert: (m) => log.push(`[UI.alert] ${m}`), createMenu: () => ({ addItem() { return this; }, addToUi() {} }) }),
      flush: () => {},
    },
    GmailApp,
    MailApp: { sendEmail: (...a) => GmailApp.sendEmail(...(typeof a[0] === 'object' ? [a[0].to, a[0].subject, a[0].body, a[0]] : a)), getRemainingDailyQuota: () => 100 },
    DriveApp,
    Utilities: {
      formatDate, sleep: () => {},
      newBlob: (data, type, name) => new Blob(data, type, name),
    },
    MimeType: { PDF: 'application/pdf', CSV: 'text/csv', PLAIN_TEXT: 'text/plain' },
    Logger: { log: (...a) => { log.push(a.join(' ')); } },
    PropertiesService: { getScriptProperties: () => ({ getProperty: (k) => (k in props ? props[k] : null), setProperty: (k, v) => { props[k] = String(v); }, deleteProperty: (k) => { delete props[k]; } }) },
    Session: { getScriptTimeZone: () => opts.timeZone || 'Asia/Tokyo', getActiveUser: () => ({ getEmail: () => 'owner@example.com' }), getEffectiveUser: () => ({ getEmail: () => 'owner@example.com' }) },
    LockService: { getScriptLock: () => ({ waitLock() {}, tryLock: () => true, releaseLock() {} }) },
    UrlFetchApp: { fetch: (url, params) => { fetched.push({ url, params }); return { getResponseCode: () => 200, getBlob: () => new Blob(`[fetched ${url}]`, 'application/pdf', 'export.pdf'), getContentText: () => '' }; } },
    ScriptApp: { getOAuthToken: () => 'TEST_TOKEN', newTrigger: () => ({ timeBased() { return this; }, everyDays() { return this; }, atHour() { return this; }, onMonthDay() { return this; }, create() { return {}; } }), getProjectTriggers: () => [] },
  };
  if (opts.now) {
    const fixed = new Date(opts.now).getTime();
    const RealDate = Date;
    ctx.Date = class extends RealDate { constructor(...a) { super(...(a.length ? a : [fixed])); } static now() { return fixed; } };
  }
  vm.createContext(ctx);
  return {
    ctx, ss, GmailApp, DriveApp, log, props, fetched,
    load(file) { vm.runInContext(fs.readFileSync(file, 'utf8'), ctx, { filename: file }); return this; },
    run(code) { return vm.runInContext(code, ctx); },
    sheet(name) { return ss.getSheetByName(name); },
  };
}

module.exports = { createGasEnv, colToNum, numToCol, formatDate };

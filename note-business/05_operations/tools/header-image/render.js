#!/usr/bin/env node
/*
 * note見出し画像ジェネレーター（1280x670px）
 *
 * 使い方:
 *   cd note-business/05_operations/tools/header-image
 *   npm install            # 初回のみ（フォント @fontsource/noto-sans-jp を取得）
 *   node render.js <specs.json> <出力ディレクトリ> [--scale 2]
 *
 * specs.json の形式:
 * {
 *   "brand": "シリーズ名・ペンネーム",
 *   "theme": {"bg":"#0f172a","fg":"#f8fafc","accent":"#38bdf8","muted":"#94a3b8","pillFg":"#0f172a"},
 *   "images": [
 *     {"id":"001","label":"無料","kicker":"小見出し","title":"タイトル\n改行は\\nで指定","sub":"サブコピー"}
 *   ]
 * }
 * 画像ごとに "theme" を上書きできる。タイトルは枠に収まるまで自動で文字サイズを縮める。
 * Playwright（chromium）が必要。
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const FONT_DIR = path.join(__dirname, 'node_modules', '@fontsource', 'noto-sans-jp', 'files');
const DEFAULT_THEME = { bg: '#0f172a', fg: '#f8fafc', accent: '#38bdf8', muted: '#94a3b8', pillFg: '#0f172a' };

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function fontFaces() {
  const faces = [];
  for (const w of [400, 700, 900]) {
    for (const subset of ['japanese', 'latin']) {
      const file = path.join(FONT_DIR, `noto-sans-jp-${subset}-${w}-normal.woff2`);
      if (fs.existsSync(file)) {
        faces.push(`@font-face{font-family:'NotoJP';font-weight:${w};font-style:normal;src:url('file://${file}') format('woff2');}`);
      }
    }
  }
  if (faces.length === 0) throw new Error('フォントが見つかりません。先に npm install を実行してください。');
  return faces.join('\n');
}

function html(spec, brand, theme) {
  const t = { ...DEFAULT_THEME, ...theme };
  const title = esc(spec.title).replace(/\\n|\n/g, '<br>');
  return `<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
${fontFaces()}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1280px;height:670px;overflow:hidden}
body{font-family:'NotoJP',sans-serif;background:${t.bg};color:${t.fg};position:relative}
.frame{position:absolute;inset:0;padding:64px 88px 56px;display:flex;flex-direction:column}
.bar{position:absolute;left:0;top:0;bottom:0;width:18px;background:${t.accent}}
.top{display:flex;align-items:center;gap:20px;height:56px}
.pill{background:${t.accent};color:${t.pillFg};font-weight:900;font-size:28px;padding:6px 22px;border-radius:999px;letter-spacing:.04em}
.kicker{color:${t.accent};font-weight:700;font-size:32px;letter-spacing:.02em}
.titlebox{flex:1;display:flex;align-items:center;min-height:0}
.title{font-weight:900;line-height:1.28;letter-spacing:.01em;overflow-wrap:anywhere;line-break:strict}
.sub{color:${t.muted};font-weight:700;font-size:32px;margin-bottom:22px}
.brand{display:flex;align-items:center;gap:16px;border-top:3px solid ${t.muted}55;padding-top:18px;color:${t.muted};font-weight:700;font-size:28px}
.dot{width:14px;height:14px;border-radius:50%;background:${t.accent}}
</style></head><body>
<div class="bar"></div>
<div class="frame">
  <div class="top">${spec.label ? `<span class="pill">${esc(spec.label)}</span>` : ''}${spec.kicker ? `<span class="kicker">${esc(spec.kicker)}</span>` : ''}</div>
  <div class="titlebox"><h1 class="title" id="title">${title}</h1></div>
  ${spec.sub ? `<div class="sub">${esc(spec.sub)}</div>` : ''}
  <div class="brand"><span class="dot"></span>${esc(brand)}</div>
</div>
<script>
  // 枠に収まるまで文字サイズを縮める
  (async () => {
    await document.fonts.ready;
    const el = document.getElementById('title');
    const box = el.parentElement;
    let size = 78;
    el.style.fontSize = size + 'px';
    while ((el.scrollHeight > box.clientHeight || el.scrollWidth > box.clientWidth) && size > 36) {
      size -= 2; el.style.fontSize = size + 'px';
    }
    document.body.dataset.ready = '1';
  })();
</script>
</body></html>`;
}

async function main() {
  const args = process.argv.slice(2);
  const scaleIdx = args.indexOf('--scale');
  const scale = scaleIdx >= 0 ? Number(args[scaleIdx + 1]) : 1;
  const positional = scaleIdx >= 0 ? args.filter((_, i) => i !== scaleIdx && i !== scaleIdx + 1) : args;
  const [specPath, outDir] = positional;
  if (!specPath || !outDir) {
    console.error('usage: node render.js <specs.json> <outDir> [--scale 2]');
    process.exit(1);
  }
  const specs = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 670 }, deviceScaleFactor: scale });
  const tmp = path.join(__dirname, '.tmp-render.html');
  try {
    for (const spec of specs.images) {
      fs.writeFileSync(tmp, html(spec, spec.brand || specs.brand || '', { ...specs.theme, ...spec.theme }));
      await page.goto('file://' + tmp);
      await page.waitForSelector('body[data-ready="1"]', { timeout: 15000 });
      const out = path.join(outDir, `${spec.id}.png`);
      await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1280, height: 670 } });
      console.log('wrote', out);
    }
  } finally {
    if (fs.existsSync(tmp)) fs.unlinkSync(tmp);
    await browser.close();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });

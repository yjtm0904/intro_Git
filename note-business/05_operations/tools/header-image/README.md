# note見出し画像ジェネレーター

noteの推奨サイズ1280×670pxの見出し画像を、JSONの指定から一括生成する。

## 使い方

```bash
cd note-business/05_operations/tools/header-image
npm install                     # 初回のみ（日本語フォント Noto Sans JP を取得。node_modules はコミットしない）
node render.js specs.json ../../../03_content/images
```

- 実行には Playwright（Chromium）が必要（Claudeのクラウド環境にはインストール済み）。
- `--scale 2` を付けると2倍解像度（2560×1340）で出力する。

## specs.json の例

```json
{
  "brand": "シリーズ名・ペンネーム",
  "theme": {"bg":"#0f172a","fg":"#f8fafc","accent":"#38bdf8","muted":"#94a3b8","pillFg":"#0f172a"},
  "images": [
    {"id":"001","label":"有料","kicker":"小見出し","title":"1行目\n2行目","sub":"サブコピー"}
  ]
}
```

- `title` の `\n` で改行位置を指定する（日本語は手動改行のほうが読みやすい）。指定しなければ自動で折り返す。
- タイトルが枠からはみ出す場合は、文字サイズを自動で縮める（最小36px）。
- 画像ごとに `theme` を上書きできる（例: 無料記事と有料記事で色を変える）。

## デザイン上の注意

- noteの一覧表示では画像が小さく表示されるため、タイトルは3行・20字程度までに収め、文字は太く大きくする。
- 重要な文字は上下左右の余白の内側に置く（一覧で端が切れても読めるようにする）。

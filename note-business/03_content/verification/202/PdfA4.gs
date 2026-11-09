/**
 * 5 PDF化と保存（A4縦に指定する版・任意）v1.1（2026-11-08）
 * 実機確認でPDFがA4にならなかったときだけ、Code.gs の savePdf_ をこの関数に置き換えて使う。
 * スプレッドシートの書き出し用のURLを使う。このURLと引数は公式ドキュメントに載っていない使い方で、予告なく変わることがある。
 * 置き換えると、承認の画面に「外部サービスへの接続」（UrlFetchApp）の権限が加わる。
 */
function savePdf_(tmp, fileName, folderId) {
  SpreadsheetApp.flush();                                   // 書き込みを反映してからPDFにする
  const url = 'https://docs.google.com/spreadsheets/d/' + tmp.getId() + '/export?format=pdf&size=A4&portrait=true&fitw=true'
    + '&gridlines=false&printtitle=false&sheetnames=false&pagenum=UNDEFINED&gid=' + tmp.getSheets()[0].getSheetId();
  const res = UrlFetchApp.fetch(url, { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('PDFの書き出しに失敗しました（応答 ' + res.getResponseCode() + '）。少し待ってから②をもう一度実行してください');
  const blob = res.getBlob().setName(fileName);
  return { blob: blob, file: DriveApp.getFolderById(folderId).createFile(blob) };
}

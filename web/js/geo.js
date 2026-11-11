// geo.js - 範囲（多角形）を作る・調べるための関数（教員が用意。課題で自由に使ってよい）
// 計算には Turf.js（地図の計算のためのライブラリ。グローバル変数 turf）を使う。

// 市区町村の範囲を km だけ広げた範囲を作る（バッファー）。km が 0 なら範囲そのもの
export function bufferArea(boundary, km) {
  if (!km) return boundary;
  return turf.buffer(boundary, km, { units: "kilometers" });
}

// 中心 {lng, lat} から半径 km の円（多角形）を作る
export function circleArea(center, km) {
  return turf.circle([center.lng, center.lat], km, { units: "kilometers", steps: 96 });
}

// 範囲（Feature）を囲む四角形 [最小経度, 最小緯度, 最大経度, 最大緯度]
export function bboxOf(area) {
  return turf.bbox(area);
}

// 2 つの四角形 [minX, minY, maxX, maxY] が重なっているか
export function bboxesOverlap(a, b) {
  return a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
}

// 点 [経度, 緯度] が範囲（Feature）の中にあるか
export function isInside(coordinates, area) {
  return turf.booleanPointInPolygon(coordinates, area);
}

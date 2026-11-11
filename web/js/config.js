// config.js - 地図の初期位置・色・表示ラベルなどの設定
// 見た目や文言を変えたいときは、まずこのファイルを見てください。

export const CONFIG = {
  // 現在地が取れないときの基準地点（柏駅）[経度, 緯度]
  defaultOrigin: { lng: 139.9709, lat: 35.8622, label: "柏駅" },
  initialZoom: 13,

  // 対象地域の中心と半径（km）。これより遠い現在地には注意を表示する
  areaCenter: { lng: 139.976, lat: 35.868 },
  areaRadiusKm: 25,

  // 背景地図（国土地理院 淡色地図）
  basemap: {
    url: "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
    attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank">地理院タイル</a>',
  },

  // データの場所（プロジェクトの data/static/。web/ から見た相対パス）
  regionsUrl: "../data/static/regions.json",                                   // 都道府県・市区町村の一覧
  prefSheltersUrl: (prefCode) => `../data/static/shelters/${prefCode}.geojson`, // 都道府県ごとの避難所
  boundariesUrl: (prefCode) => `../data/static/admin_boundaries/${prefCode}.geojson`, // 市区町村の範囲

  // 最初に選ばれている地域
  defaultPref: "千葉県",
  defaultCity: "柏市",

  // 「市区町村＋周辺」の距離（km）。0 は市区町村の範囲だけ
  cityBufferOptions: [0, 5, 10, 20],
  defaultCityBuffer: 5,
  // 「現在地から半径」の距離（km）
  gpsRadiusOptions: [5, 10, 20],
  defaultGpsRadius: 5,

  // 一覧に表示する件数
  listSize: 10,

  // 色
  colors: {
    flood: "#0b8a6a", // 洪水に対応する指定緊急避難場所（現在地の青い点と区別するため緑系）
    other: "#8a929a", // それ以外
    area: "#7a4fd1",  // 検索範囲
    boundary: "#40474d", // 市区町村の範囲
  },

  // 災害種別の表示名（GeoJSON の hazards のキー → 表示名）
  hazardLabels: {
    flood: "洪水",
    inland: "内水氾濫",
    landslide: "土砂災害",
    quake: "地震",
    fire: "大規模な火事",
    surge: "高潮",
    tsunami: "津波",
    volcano: "火山現象",
  },
};

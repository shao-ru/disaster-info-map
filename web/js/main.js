// main.js - 地図の表示と全体の流れ（教員が用意）
//
// 全体の流れ
//   ① 画面で選ぶ ………… 県・市区町村＋周辺 ○ km、または 現在地＋半径 ○ km
//   ② 地域を決める ……… 課題 1  getRegion()        （js/student/region.js）
//   ③ 範囲を作る ………… 市区町村の範囲を広げる（バッファー）／現在地の円（geo.js）
//   ④ 県を調べる ………… 課題 2  findPrefectures()  （js/student/search.js）
//   ⑤ 避難所を選ぶ ……… 課題 3  filterInArea()     （js/student/search.js）
//   ⑥ 地図と一覧に表示 … showResult()（このファイル）
//
// ②④⑤ は今は「仮の実装」です。課題を完成させると、選んだ地域の結果が正しく表示されます。

import { CONFIG } from "./config.js";
import { loadRegions, loadShelters, loadBoundary } from "./data.js";
import { bufferArea, circleArea, bboxOf, bboxesOverlap, isInside } from "./geo.js";
import { FILTERS, nearest } from "./shelters.js";
import { distanceKm } from "./shelters.js";
import { buildPopup } from "./popup.js";
import { renderList } from "./list.js";
import { getRegion } from "./student/region.js";
import { findPrefectures, filterInArea } from "./student/search.js";

const state = {
  regions: null,
  features: [],                         // いま表示している避難所
  filter: "all",
  origin: { ...CONFIG.defaultOrigin },  // 距離の基準
  gps: null,                            // 現在地 {lng, lat}
};
const EMPTY = { type: "FeatureCollection", features: [] };
const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- 地図
const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [CONFIG.basemap.url],
        tileSize: 256,
        maxzoom: 18,
        attribution: CONFIG.basemap.attribution,
      },
    },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  },
  center: [CONFIG.defaultOrigin.lng, CONFIG.defaultOrigin.lat],
  zoom: CONFIG.initialZoom,
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

const geolocate = new maplibregl.GeolocateControl({
  positionOptions: { enableHighAccuracy: true },
  trackUserLocation: true,
  showAccuracyCircle: true,
});
map.addControl(geolocate, "top-right");
geolocate.on("geolocate", (e) => {
  state.gps = { lng: e.coords.longitude, lat: e.coords.latitude };
  state.origin = { ...state.gps, label: "現在地" };
  $("near-btn").disabled = false;
  updateList();
});
geolocate.on("error", () => setStatus("現在地を取得できませんでした。位置情報の許可を確認してください。", "warn"));

let popup = null;
function showPopup(feature) {
  const [lng, lat] = feature.geometry.coordinates;
  if (popup) popup.remove();
  popup = new maplibregl.Popup({ maxWidth: "300px" })
    .setLngLat([lng, lat])
    .setDOMContent(buildPopup(feature.properties, distanceKm(state.origin, { lng, lat }), state.origin.label))
    .addTo(map);
}

map.on("load", async () => {
  // 検索範囲・市区町村の範囲・避難所の 3 つのレイヤー（下から順に重なる）
  map.addSource("area", { type: "geojson", data: EMPTY });
  map.addSource("boundary", { type: "geojson", data: EMPTY });
  map.addSource("shelters", { type: "geojson", data: EMPTY });
  map.addLayer({ id: "area-fill", type: "fill", source: "area",
    paint: { "fill-color": CONFIG.colors.area, "fill-opacity": 0.08 } });
  map.addLayer({ id: "area-line", type: "line", source: "area",
    paint: { "line-color": CONFIG.colors.area, "line-width": 2 } });
  map.addLayer({ id: "boundary-line", type: "line", source: "boundary",
    paint: { "line-color": CONFIG.colors.boundary, "line-width": 1.5, "line-dasharray": [2, 2] } });
  map.addLayer({
    id: "shelters", type: "circle", source: "shelters",
    paint: {
      "circle-color": ["case", ["get", "flood"], CONFIG.colors.flood, CONFIG.colors.other],
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 12, 4, 15, 7, 17, 10],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": ["case", ["get", "shelter"], 2, 0.8],
    },
  });
  // MapLibre が返す地物は配列が文字列になるため、元のデータを id で引く
  map.on("click", "shelters", (e) => {
    const f = state.features.find((x) => x.properties.id === e.features[0].properties.id);
    if (f) showPopup(f);
  });
  map.on("mouseenter", "shelters", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "shelters", () => (map.getCanvas().style.cursor = ""));

  try {
    state.regions = await loadRegions();
  } catch (err) {
    setStatus(err.message, "warn");
    return;
  }
  setupPicker();
  setupFilters();
  await runCity(); // 最初は柏市＋周辺を表示
});

// ---------------------------------------------------------------- ① 画面で選ぶ
function setupPicker() {
  const prefSel = $("pref");
  const citySel = $("city");
  for (const p of state.regions.prefectures) prefSel.append(new Option(p.name, p.name));
  prefSel.value = CONFIG.defaultPref;
  const fillCities = () => {
    citySel.textContent = "";
    for (const c of state.regions.cities.filter((c) => c.pref === prefSel.value)) {
      citySel.append(new Option(c.name, c.name));
    }
  };
  fillCities();
  citySel.value = CONFIG.defaultCity;
  prefSel.addEventListener("change", fillCities);

  for (const km of CONFIG.cityBufferOptions) {
    $("city-buffer").append(new Option(km ? `＋周辺 ${km} km` : "市区町村の中だけ", km));
  }
  $("city-buffer").value = String(CONFIG.defaultCityBuffer);
  for (const km of CONFIG.gpsRadiusOptions) $("gps-radius").append(new Option(`半径 ${km} km`, km));
  $("gps-radius").value = String(CONFIG.defaultGpsRadius);

  $("city-btn").addEventListener("click", runCity);
  $("near-btn").addEventListener("click", runNear);
}

// ---------------------------------------------------------------- ②③ 県・市区町村で探す
async function runCity() {
  const prefName = $("pref").value;
  const cityName = $("city").value;
  const km = Number($("city-buffer").value);

  const region = getRegion(prefName, cityName, state.regions);            // ② 課題 1
  if (!region) {
    setStatus(`「${prefName}${cityName}」が見つかりませんでした`, "warn");
    return;
  }
  if (region.fullName !== prefName + cityName) {
    devNote(`課題 1：「${prefName}${cityName}」を選びましたが、「${region.fullName}」が返っています`);
  }

  const boundary = await loadBoundary(region);
  const area = bufferArea(boundary, km);                                   // ③
  if (!state.gps) state.origin = { lng: region.center[0], lat: region.center[1], label: `${region.name}の中心` };
  const title = km ? `${region.fullName}＋周辺 ${km} km` : `${region.fullName}`;
  await search(area, title, boundary);
}

// ---------------------------------------------------------------- ③ 現在地の周辺で探す
async function runNear() {
  if (!state.gps) {
    setStatus("先に地図右上の現在地ボタン（◎）を押してください。", "warn");
    return;
  }
  const km = Number($("gps-radius").value);
  const area = circleArea(state.gps, km);                                  // ③
  state.origin = { ...state.gps, label: "現在地" };
  await search(area, `現在地から半径 ${km} km`, null);
}

// ---------------------------------------------------------------- ④⑤ 避難所を探す
async function search(area, title, boundary) {
  setStatus("読み込み中…");
  const prefCodes = findPrefectures(area, state.regions);                  // ④ 課題 2
  const all = await loadShelters(prefCodes);
  const shelters = filterInArea(all, area);                                // ⑤ 課題 3

  // 課題の状態を調べる（画面には出さず、開発者ツールの Console に出す）
  const box = bboxOf(area);
  const needed = new Set(state.regions.cities.filter((c) => bboxesOverlap(c.bbox, box)).map((c) => c.prefCode));
  const missing = [...needed].filter((code) => !prefCodes.includes(code));
  if (missing.length) {
    const names = missing.map((code) => state.regions.prefectures.find((p) => p.code === code)?.name || code);
    devNote(`課題 2：範囲にかかる ${names.join("・")} のデータが読み込まれていません`);
  }
  const outside = shelters.filter((f) => !isInside(f.geometry.coordinates, area)).length;
  if (outside) devNote(`課題 3：範囲の外の避難所が ${outside} 件含まれています`);

  showResult(title, shelters, area, boundary);                             // ⑥
  setStatus("");
}

// 課題の確認メッセージ：開発者ツール（F12）の Console に表示する。画面には出さない
function devNote(text) {
  console.warn(`[課題チェック] ${text}`);
}

// ---------------------------------------------------------------- ⑥ 地図と一覧に表示
function showResult(title, shelters, area, boundary) {
  state.features = shelters;
  map.getSource("area").setData(area);
  map.getSource("boundary").setData(boundary || EMPTY);
  map.getSource("shelters").setData({ type: "FeatureCollection", features: shelters });
  if (popup) popup.remove();

  const flood = shelters.filter((f) => f.properties.flood).length;
  $("result-title").textContent = title;
  $("count").textContent = `${shelters.length} 施設（洪水に対応 ${flood}）`;
  $("approx-note").hidden = !(boundary && boundary.properties.approx);

  const [x0, y0, x1, y1] = bboxOf(area);
  map.fitBounds([[x0, y0], [x1, y1]], { padding: 30, maxZoom: 15, duration: 800 });
  updateList();
}

// ---------------------------------------------------------------- 絞り込みと一覧
function setupFilters() {
  const box = $("filters");
  for (const [key, f] of Object.entries(FILTERS)) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = f.label;
    btn.dataset.key = key;
    btn.setAttribute("aria-pressed", String(key === state.filter));
    btn.addEventListener("click", () => {
      state.filter = key;
      box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.key === key)));
      map.setFilter("shelters", FILTERS[key].expr);
      updateList();
    });
    box.append(btn);
  }
}

function updateList() {
  $("origin-label").textContent = `${state.origin.label}から近い順`;
  const items = nearest(state.features, state.origin, state.filter, CONFIG.listSize);
  renderList($("list"), items, (feature) => {
    map.flyTo({ center: feature.geometry.coordinates, zoom: Math.max(map.getZoom(), 15) });
    showPopup(feature);
  });
}

// ---------------------------------------------------------------- 状態表示
function setStatus(text, kind = "") {
  const s = $("status");
  s.textContent = text;
  s.className = "banner" + (kind ? ` banner-${kind}` : "");
  s.hidden = !text;
}

function updateOnline() {
  $("offline").hidden = navigator.onLine;
}
window.addEventListener("online", updateOnline);
window.addEventListener("offline", updateOnline);
updateOnline();

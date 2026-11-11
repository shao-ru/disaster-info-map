// data.js - データを読み込むための共通の関数（教員が用意。課題で自由に使ってよい）

import { CONFIG } from "./config.js";

const cache = new Map();

// URL の JSON を読み込む（同じ URL は 2 回目から読み込み済みのものを返す）
export async function loadJSON(url) {
  if (!cache.has(url)) {
    cache.set(url, fetch(url).then((res) => {
      if (!res.ok) throw new Error(`${url} を読み込めません（${res.status}）`);
      return res.json();
    }));
  }
  return cache.get(url);
}

// 都道府県・市区町村の一覧（regions.json）を読み込む
export function loadRegions() {
  return loadJSON(CONFIG.regionsUrl);
}

// ある都道府県の避難所をすべて読み込み、地物（Feature）の配列で返す
//   例：await loadPrefectureShelters("12")  → 千葉県の避難所の配列
export async function loadPrefectureShelters(prefCode) {
  const geojson = await loadJSON(CONFIG.prefSheltersUrl(prefCode));
  return geojson.features;
}

// いくつかの都道府県の避難所を読み込み、1 つの配列にまとめて返す
//   例：await loadShelters(["12", "08"])  → 千葉県と茨城県の避難所
export async function loadShelters(prefCodes) {
  const lists = await Promise.all(prefCodes.map((code) => loadPrefectureShelters(code)));
  return lists.flat();
}

// ある市区町村の範囲（多角形の Feature）を読み込む
export async function loadBoundary(region) {
  const geojson = await loadJSON(CONFIG.boundariesUrl(region.prefCode));
  return geojson.features.find((f) => f.properties.code === region.code) || null;
}

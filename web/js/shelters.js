// shelters.js - 避難所データの読み込み・絞り込み・距離計算

import { CONFIG } from "./config.js";

// 絞り込みの種類
export const FILTERS = {
  all: { label: "すべて", test: () => true, expr: null },
  flood: {
    label: "洪水に対応",
    test: (p) => p.flood,
    expr: ["==", ["get", "flood"], true],
  },
  shelter: {
    label: "指定避難所",
    test: (p) => p.shelter,
    expr: ["==", ["get", "shelter"], true],
  },
};

// GeoJSON を読み込む
export async function loadShelters() {
  const res = await fetch(CONFIG.dataUrl);
  if (!res.ok) throw new Error(`避難所データを読み込めません（${res.status}）`);
  return res.json();
}

// 2 地点間の距離（km）。地球を球とみなした近似（ハバーサイン公式）
export function distanceKm(a, b) {
  const R = 6371;
  const rad = (d) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

// 基準地点から近い順に n 件を返す（絞り込み条件つき）
export function nearest(features, origin, filterKey, n) {
  const test = FILTERS[filterKey].test;
  return features
    .filter((f) => test(f.properties))
    .map((f) => {
      const [lng, lat] = f.geometry.coordinates;
      return { feature: f, km: distanceKm(origin, { lng, lat }) };
    })
    .sort((x, y) => x.km - y.km)
    .slice(0, n);
}

// 距離の表示（1 km 未満は m）
export function formatDistance(km) {
  return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`;
}

// shelters.js - 避難所の値（attrs）の整理と、距離の計算

// 避難所の項目（attrs のキー）
export const PEOPLE_KEYS = ["elderly", "disabled", "infant", "pet", "welfare"];
// 災害の順番は、国土地理院の指定緊急避難場所データ（mergeFromCity_2.csv）の列と同じ
export const HAZARD_KEYS = ["flood", "landslide", "surge", "quake", "tsunami", "fire", "inland", "volcano"];
export const ATTR_KEYS = ["access", ...PEOPLE_KEYS, ...HAZARD_KEYS];

// GeoJSON の attrs には「分かっている項目」だけが入っている。
// 値は "可"・"条件付き"・"不可" の文字列。分からない項目を null（不明）で埋めて、すべての項目がそろったオブジェクトにする
export function fullAttrs(props) {
  const a = props.attrs || {};
  return Object.fromEntries(ATTR_KEYS.map((k) => [k, a[k] ?? null]));
}

// 値の出どころ："survey"（調査）・"auto"（備考などから推定）・"gsi"（国土地理院の指定）・null（不明）
export function sourceOf(props, key) {
  if (props.attrs?.[key] == null) return null;
  return props.src?.[key] || "gsi";
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

// 基準地点から近い順に n 件を返す
export function nearest(features, origin, n) {
  return features
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

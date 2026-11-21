// flood.js - 洪水浸水想定区域（浸水深）の図層
//
// データ：data/static/flood/<規模>/<z>/<x>/<y>.png（地図タイル）と meta.json
//         code/build_flood.py で国土数値情報（A31b）から作る（教員）
// 画面：「地図に重ねる情報」の欄に、表示の切り替え・濃さ・凡例を出す

import { CONFIG } from "./config.js";

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

// 透明な 256×256 の PNG（データの無いタイルの代わり）
async function emptyTile() {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const blob = await new Promise((resolve) => c.toBlob(resolve, "image/png"));
  return blob.arrayBuffer();
}

// map: MapLibre の地図、box: 画面の欄（div）、beforeId: この図層の下に入れる（避難所などより下にする）
export async function setupFlood(map, box, beforeId) {
  let meta;
  try {
    const res = await fetch(CONFIG.flood.metaUrl);
    if (!res.ok) throw new Error(res.status);
    meta = await res.json();
  } catch {
    box.hidden = true;           // データがまだ無いときは、欄ごと出さない
    return;
  }

  // タイルの読み込み：浸水しない所（川から遠い所など）はタイルのファイルが無い。
  // そのまま読みにいくと「404（見つからない）」のエラーが Console に並ぶので、
  // meta.json のタイルの一覧に無いものは読みにいかず、透明な画像を返す（flood:// という独自の読み方）
  const base = new URL(CONFIG.flood.tilesDir, location.href).href;
  const have = new Set(Object.entries(meta.tiles || {}).flatMap(([z, list]) => list.map((xy) => `${z}/${xy}`)));
  const empty = await emptyTile();
  maplibregl.addProtocol("flood", async (params, abort) => {
    const key = params.url.replace("flood://", "");
    if (meta.tiles && !have.has(key)) return { data: empty };
    const res = await fetch(`${base}${key}.png`, { signal: abort.signal });
    if (!res.ok) return { data: empty };
    return { data: await res.arrayBuffer() };
  });
  map.addSource("flood", {
    type: "raster",
    tiles: ["flood://{z}/{x}/{y}"],
    tileSize: 256,
    minzoom: meta.minzoom,
    maxzoom: meta.maxzoom,          // これより拡大すると、最大ズームのタイルを拡大して使う
    bounds: meta.bounds,            // この範囲の外のタイルは読みにいかない
    attribution: "洪水浸水想定：国土数値情報（国土交通省）",
  });
  map.addLayer({
    id: "flood", type: "raster", source: "flood",
    layout: { visibility: CONFIG.flood.visible ? "visible" : "none" },
    paint: { "raster-opacity": CONFIG.flood.opacity, "raster-resampling": "nearest" },
  }, beforeId);

  // ---- 画面の欄
  box.textContent = "";
  const head = el("label", "layer-head");
  const check = el("input");
  check.type = "checkbox";
  check.checked = CONFIG.flood.visible;
  head.append(check, el("span", null, `洪水の浸水深（${meta.name.replace(/^.*（|）$/g, "")}）`));

  const body = el("div", "layer-body");
  const opacity = el("label", "layer-opacity");
  const range = el("input");
  Object.assign(range, { type: "range", min: "0.2", max: "1", step: "0.1", value: String(CONFIG.flood.opacity) });
  opacity.append("濃さ", range);

  const legend = el("div", "flood-legend");
  for (const item of meta.legend) {
    const row = el("span");
    const sw = el("i", "swatch");
    sw.style.background = item.color;
    row.append(sw, item.label);
    legend.append(row);
  }
  const area = meta.cities.map((c) => c.replace(/^(.+?[都道府県])/, "")).join("・");
  const note = el("p", "layer-note",
    `表示範囲：${area}とその周辺。川が氾濫したときに想定される浸水の深さです（内水氾濫・高潮は含みません）。` +
    `出典：${meta.source}`);
  body.append(opacity, legend, note);
  body.hidden = !check.checked;
  box.append(head, body);

  check.addEventListener("change", () => {
    map.setLayoutProperty("flood", "visibility", check.checked ? "visible" : "none");
    body.hidden = !check.checked;
  });
  range.addEventListener("input", () => map.setPaintProperty("flood", "raster-opacity", Number(range.value)));
}

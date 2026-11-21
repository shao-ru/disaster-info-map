// weather.js - 気象観測所（アメダス）の図層と、雨量・気温などのグラフ
//
// 使うデータ
//   観測所の一覧     data/static/weather/stations.geojson     code/weather.py stations で作る
//   過去の記録（日） data/static/weather/daily/<地点コード>.csv  code/weather.py history で作る
//   リアルタイム     気象庁ホームページのアメダスの JSON（10 分ごとに更新。ブラウザーから直接読む）
//                    ※公式 API ではないので、形が変わったり読めなくなったりすることがある
//
// 画面
//   地図：観測所ごとに、最新の 1 時間降水量と気温の札を出す（雨の強さで色が変わる）
//   欄　：観測時刻・自動更新の状態。読めなかったときは注意を出す
//   札を押す：「直近 24 時間（10 分ごと）」と「過去の記録（日ごと）」のグラフ（Chart.js）

import { CONFIG } from "./config.js";

const JMA = CONFIG.weather.jmaUrl;

// 1 時間降水量の色（気象庁のアメダスの凡例に近い色）
const RAIN_COLORS = [
  [80, "#b40068", "#fff"], [50, "#ff2800", "#fff"], [30, "#ff9900", "#000"], [20, "#faf500", "#000"],
  [10, "#0041ff", "#fff"], [5, "#218cff", "#fff"], [1, "#a0d2ff", "#000"], [0.5, "#f2f2ff", "#000"],
];

// 直近 24 時間のグラフの項目（10 分ごとの値。JSON のキー）
const RECENT = [
  { id: "precip", key: "precipitation10m", label: "降水量（10 分間）", unit: "mm", type: "bar", agg: "sum", color: "#2f7fd8" },
  { id: "temp", key: "temp", label: "気温", unit: "℃", type: "line", agg: "mean", color: "#d9534f" },
  { id: "sun", key: "sun10m", label: "日照（10 分間）", unit: "分", type: "bar", agg: "sum", color: "#f0b429" },
  { id: "wind", key: "wind", label: "風速", unit: "m/s", type: "line", agg: "mean", color: "#5f6b73" },
  { id: "humidity", key: "humidity", label: "湿度", unit: "%", type: "line", agg: "mean", color: "#46a0a0" },
  { id: "snow", key: "snow", label: "積雪の深さ", unit: "cm", type: "line", agg: "max", color: "#7aa6c2" },
];

// 過去の記録のグラフの項目（CSV の列）
const HISTORY = [
  { id: "precip", cols: ["precip"], label: "降水量（日合計）", unit: "mm", type: "bar", agg: "sum", colors: ["#2f7fd8"] },
  { id: "precip_max1h", cols: ["precip_max1h"], label: "最大 1 時間降水量", unit: "mm", type: "bar", agg: "max", colors: ["#1f4f8f"] },
  { id: "temp", cols: ["temp_max", "temp_avg", "temp_min"], names: ["最高", "平均", "最低"], label: "気温（最高・平均・最低）", unit: "℃", type: "line", agg: "mean", colors: ["#d9534f", "#e39b3a", "#3a7bd5"] },
  { id: "sun", cols: ["sun"], label: "日照時間", unit: "h", type: "bar", agg: "sum", colors: ["#f0b429"] },
  { id: "snowfall", cols: ["snowfall"], label: "降雪の深さ（日合計）", unit: "cm", type: "bar", agg: "sum", colors: ["#7aa6c2"] },
  { id: "snow_depth", cols: ["snow_depth"], label: "最深積雪", unit: "cm", type: "line", agg: "max", colors: ["#4f7f99"] },
  { id: "wind_avg", cols: ["wind_avg"], label: "平均風速", unit: "m/s", type: "line", agg: "mean", colors: ["#5f6b73"] },
  { id: "humidity", cols: ["humidity"], label: "湿度（平均）", unit: "%", type: "line", agg: "mean", colors: ["#46a0a0"] },
];
const PERIODS = [[30, "直近 30 日"], [90, "直近 90 日"], [365, "直近 1 年"], [0, "全期間"]];

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

// ---------------------------------------------------------------- 時刻（日本時間）
const pad = (n) => String(n).padStart(2, "0");
// Date → 日本時間の { y, mo, d, h, mi }
function jst(date) {
  const t = new Date(date.getTime() + 9 * 3600e3);
  return { y: t.getUTCFullYear(), mo: t.getUTCMonth() + 1, d: t.getUTCDate(), h: t.getUTCHours(), mi: t.getUTCMinutes() };
}
const stamp = (p) => `${p.y}${pad(p.mo)}${pad(p.d)}${pad(p.h)}${pad(p.mi)}00`;      // 20261121102000
const hhmm = (p) => `${pad(p.h)}:${pad(p.mi)}`;
const fromStamp = (s) => new Date(`${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}T${s.slice(8, 10)}:${s.slice(10, 12)}:00+09:00`);

// 気象庁の値 [値, 品質]：品質 0（正常）のときだけ使う
const val = (v) => (Array.isArray(v) && v[0] != null && v[1] === 0 ? v[0] : null);

async function getJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function latestTime() {
  const res = await fetch(`${JMA}/data/latest_time.txt`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status}`);
  return new Date((await res.text()).trim());
}

// ---------------------------------------------------------------- 図層と欄
export async function setupWeather(map, box, dialog) {
  let stations;
  try {
    stations = await getJson(CONFIG.weather.stationsUrl);
  } catch {
    box.hidden = true;           // 観測所の一覧がまだ無いときは、欄ごと出さない
    return;
  }

  const state = { visible: CONFIG.weather.visible, timer: null, latest: null, values: {}, markers: [] };

  // ---- 欄
  box.textContent = "";
  const head = el("label", "layer-head");
  const check = el("input");
  check.type = "checkbox";
  check.checked = state.visible;
  head.append(check, el("span", null, `気象観測所（${stations.features.length} 地点）`));
  const body = el("div", "layer-body");
  const status = el("p", "wx-status");
  status.setAttribute("role", "status");
  const reload = el("button", "wx-reload", "今すぐ更新");
  reload.type = "button";
  const legend = el("div", "wx-legend");
  legend.append(el("span", "muted", "1 時間の雨（mm）"));
  for (const [min, bg, fg] of [...RAIN_COLORS].reverse()) {
    const s = el("span", "wx-chip", min < 1 ? "0.5" : String(min));
    Object.assign(s.style, { background: bg, color: fg });
    legend.append(s);
  }
  body.append(status, reload, legend,
    el("p", "layer-note", "札を押すと、直近 24 時間と過去の記録のグラフが見られます。出典：気象庁"));
  body.hidden = !state.visible;
  box.append(head, body);

  // ---- 地図の札（観測所の数は少ないので、HTML のマーカーで出す）
  for (const f of stations.features) {
    const p = f.properties;
    const m = el("button", "wx-marker");
    m.type = "button";
    m.title = `${p.name}（地点コード ${p.code}）`;
    m.append(el("b", null, p.name), el("span", "wx-value", "…"));
    m.addEventListener("click", (e) => {
      e.stopPropagation();
      openStation(dialog, p, state);
    });
    const marker = new maplibregl.Marker({ element: m, anchor: "bottom" }).setLngLat(f.geometry.coordinates);
    state.markers.push({ marker, el: m, props: p });
  }

  function paint() {
    for (const { el: m, props } of state.markers) {
      const v = state.values[props.code];
      const span = m.querySelector(".wx-value");
      if (!v) {
        span.textContent = "−";
        m.style.removeProperty("--wx-bg");
        m.style.removeProperty("--wx-fg");
        continue;
      }
      const parts = [];
      if (v.rain1h != null) parts.push(`${v.rain1h.toFixed(1)} mm`);
      if (v.temp != null) parts.push(`${v.temp.toFixed(1)}℃`);
      span.textContent = parts.join("　") || "−";
      const c = RAIN_COLORS.find(([min]) => (v.rain1h ?? 0) >= min);
      m.style.setProperty("--wx-bg", c ? c[1] : "#fff");
      m.style.setProperty("--wx-fg", c ? c[2] : "var(--ink)");
    }
  }

  async function refresh() {
    status.className = "wx-status";
    status.textContent = "気象庁のデータを読み込み中…";
    try {
      const t = await latestTime();
      const data = await getJson(`${JMA}/data/map/${stamp(jst(t))}.json`);
      state.latest = t;
      state.values = {};
      for (const { props } of state.markers) {
        const r = data[props.code];
        if (r) state.values[props.code] = { rain1h: val(r.precipitation1h), temp: val(r.temp) };
      }
      paint();
      const p = jst(t);
      const old = Date.now() - t.getTime() > 40 * 60e3;
      status.className = "wx-status" + (old ? " wx-status-warn" : "");
      status.textContent = `観測時刻 ${p.mo}/${p.d} ${hhmm(p)}` +
        (old ? "（データが古い可能性があります）" : `（${CONFIG.weather.refreshMinutes} 分ごとに自動更新）`);
    } catch {
      // 読めなかったとき：前の値は残し、注意を出す。次の自動更新でもう一度試す
      const now = jst(new Date());
      status.className = "wx-status wx-status-warn";
      status.textContent = `⚠ 気象庁のリアルタイムのデータを読み込めませんでした（${hhmm(now)}）。` +
        (state.latest ? `表示は ${hhmm(jst(state.latest))} の値です。` : "") +
        "自動で再試行します。過去の記録は見られます。";
      paint();
    }
  }

  function show(on) {
    state.visible = on;
    body.hidden = !on;
    for (const { marker } of state.markers) on ? marker.addTo(map) : marker.remove();
    clearInterval(state.timer);
    state.timer = null;
    if (on) {
      refresh();
      state.timer = setInterval(refresh, CONFIG.weather.refreshMinutes * 60e3);
    }
  }
  check.addEventListener("change", () => show(check.checked));
  reload.addEventListener("click", refresh);
  window.addEventListener("online", () => state.visible && refresh());
  setupDialog(dialog);
  show(state.visible);
}

// ---------------------------------------------------------------- 観測所のダイアログ
let chart = null;

function setupDialog(dialog) {
  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => { chart?.destroy(); chart = null; });
}

function openStation(dialog, p, state) {
  dialog.querySelector("h2").textContent = `${p.name}（${p.kana}）`;
  const body = dialog.querySelector(".dialog-body");
  body.textContent = "";

  const sub = el("p", "muted", `地点コード ${p.code}・標高 ${p.alt} m・中心から ${p.km} km`);
  const tabs = el("div", "wx-tabs");
  tabs.setAttribute("role", "tablist");
  const tabRecent = el("button", null, "直近 24 時間（10 分ごと）");
  const tabHistory = el("button", null, "過去の記録（日ごと）");
  for (const b of [tabRecent, tabHistory]) { b.type = "button"; b.setAttribute("role", "tab"); tabs.append(b); }

  const controls = el("div", "wx-controls");
  const elemSel = el("select");
  const periodSel = el("select");
  for (const [days, label] of PERIODS) periodSel.append(new Option(label, days));
  periodSel.value = "90";
  const l1 = el("label", null, "項目 ");
  l1.append(elemSel);
  const l2 = el("label", null, "期間 ");
  l2.append(periodSel);
  controls.append(l1, l2);

  const msg = el("p", "wx-msg");
  msg.setAttribute("role", "status");
  const box = el("div", "wx-chart");
  const canvas = el("canvas");
  box.append(canvas);
  const summary = el("p", "wx-summary");
  const source = el("p", "notice", "出典：気象庁（直近 24 時間はアメダスのリアルタイムの値、過去の記録は「過去の気象データ検索」の値）。");
  body.append(sub, tabs, controls, msg, box, summary, source);

  let mode = "recent";
  let recent = null;    // { labels, series: {key: [...]}, error }
  let history = null;   // { rows, cols, error }

  async function render() {
    tabRecent.setAttribute("aria-selected", mode === "recent");
    tabHistory.setAttribute("aria-selected", mode === "history");
    l2.hidden = mode !== "history";
    msg.textContent = "読み込み中…";
    msg.className = "wx-msg";
    summary.textContent = "";
    if (typeof Chart === "undefined") {
      msg.textContent = "グラフの部品（Chart.js）を読み込めませんでした。ネットワークを確かめてください。";
      msg.className = "wx-msg wx-msg-ng";
      return;
    }
    if (mode === "recent") {
      recent ??= await loadRecent(p.code, state.latest);
      if (recent.error) return fail(recent.error);
      const items = RECENT.filter((it) => recent.series[it.key]?.some((v) => v != null));
      fillSelect(items);
      const it = items.find((x) => x.id === elemSel.value) || items[0];
      if (!it) return fail("この観測所の直近のデータがありません。");
      msg.textContent = recent.partial ? "一部の時間のデータを読み込めませんでした。" : "";
      draw(it.type, recent.labels, [{ label: it.label, data: recent.series[it.key], color: it.color }], it.unit);
      summary.textContent = summarize(it, recent.labels, [recent.series[it.key]]);
    } else {
      history ??= await loadHistory(p.code);
      if (history.error) return fail(history.error);
      const items = HISTORY.filter((it) => history.cols.includes(it.cols[0]));
      fillSelect(items);
      const it = items.find((x) => x.id === elemSel.value) || items[0];
      const days = Number(periodSel.value);
      const rows = days ? history.rows.slice(-days) : history.rows;
      const labels = rows.map((r) => r.date);
      const sets = it.cols.filter((c) => history.cols.includes(c)).map((c, i) => ({
        label: it.names ? it.names[it.cols.indexOf(c)] : it.label,
        data: rows.map((r) => (r[c] === "" ? null : Number(r[c]))),
        color: it.colors[it.cols.indexOf(c)] || it.colors[i],
      }));
      msg.textContent = `${history.rows[0].date} 〜 ${history.rows.at(-1).date} の記録があります。`;
      draw(it.type, labels, sets, it.unit);
      summary.textContent = summarize(it, labels, sets.map((s) => s.data));
    }
  }

  function fail(text) {
    msg.textContent = text;
    msg.className = "wx-msg wx-msg-ng";
    chart?.destroy();
    chart = null;
  }

  function fillSelect(items) {
    const keep = elemSel.value;
    elemSel.textContent = "";
    for (const it of items) elemSel.append(new Option(it.label, it.id));
    if (items.some((it) => it.id === keep)) elemSel.value = keep;
  }

  function draw(type, labels, sets, unit) {
    chart?.destroy();
    chart = new Chart(canvas, {
      type,
      data: {
        labels,
        datasets: sets.map((s) => ({
          label: s.label, data: s.data, backgroundColor: s.color, borderColor: s.color,
          borderWidth: type === "line" ? 1.5 : 0, pointRadius: 0, spanGaps: false,
        })),
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: sets.length > 1 },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}：${c.parsed.y ?? "−"} ${unit}` } },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8, maxRotation: 0 } },
          y: { title: { display: true, text: unit }, beginAtZero: type === "bar" },
        },
      },
    });
  }

  tabRecent.addEventListener("click", () => { mode = "recent"; render(); });
  tabHistory.addEventListener("click", () => { mode = "history"; render(); });
  elemSel.addEventListener("change", render);
  periodSel.addEventListener("change", render);
  dialog.showModal();
  render();
}

// 直近 24 時間の 10 分ごとの値（3 時間ごとのファイルを 9 つ読む）
async function loadRecent(code, latest) {
  let t;
  try {
    t = latest || (await latestTime());
  } catch {
    return { error: "気象庁のデータを読み込めませんでした。ネットワークを確かめるか、しばらくしてから開き直してください。" };
  }
  const end = t.getTime();
  const start = end - 24 * 3600e3;
  const files = [];
  for (let x = start - 3 * 3600e3; x <= end; x += 3 * 3600e3) {
    const p = jst(new Date(x));
    const name = `${p.y}${pad(p.mo)}${pad(p.d)}_${pad(Math.floor(p.h / 3) * 3)}`;
    if (!files.includes(name)) files.push(name);
  }
  const results = await Promise.allSettled(files.map((f) => getJson(`${JMA}/data/point/${code}/${f}.json`)));
  const ok = results.filter((r) => r.status === "fulfilled").map((r) => r.value);
  if (!ok.length) {
    return { error: "気象庁のデータを読み込めませんでした。ネットワークを確かめるか、しばらくしてから開き直してください。" };
  }
  const records = Object.assign({}, ...ok);
  const keys = Object.keys(records).filter((k) => {
    const x = fromStamp(k).getTime();
    return x > start && x <= end;
  }).sort();
  const series = {};
  for (const it of RECENT) series[it.key] = keys.map((k) => val(records[k][it.key]));
  return { labels: keys.map((k) => `${k.slice(6, 8)}日 ${k.slice(8, 10)}:${k.slice(10, 12)}`), series, partial: ok.length < files.length };
}

// 過去の記録（CSV）
async function loadHistory(code) {
  let text;
  try {
    const res = await fetch(`${CONFIG.weather.dailyDir}${code}.csv`);
    if (!res.ok) throw new Error(res.status);
    text = await res.text();
  } catch {
    return { error: "この観測所の過去の記録は、まだありません（code/weather.py history で作ります）。" };
  }
  const [header, ...lines] = text.trim().split(/\r?\n/);
  const cols = header.split(",");
  const rows = lines.map((line) => Object.fromEntries(line.split(",").map((v, i) => [cols[i], v])));
  if (!rows.length) return { error: "この観測所の過去の記録は、まだありません。" };
  return { rows, cols };
}

// グラフの下の一言（合計・平均・最大など）
function summarize(it, labels, seriesList) {
  const fmt = (v) => (Math.round(v * 10) / 10).toString();
  const first = seriesList[0].map((v, i) => [v, labels[i]]).filter(([v]) => v != null);
  if (!first.length) return "この期間の値はありません。";
  const max = first.reduce((a, b) => (b[0] > a[0] ? b : a));
  if (it.agg === "sum") {
    const sum = first.reduce((s, [v]) => s + v, 0);
    if (!max[0]) return `この期間の合計 0 ${it.unit}`;
    return `この期間の合計 ${fmt(sum)} ${it.unit}（いちばん多かったのは ${max[1]} の ${fmt(max[0])} ${it.unit}）`;
  }
  if (it.agg === "max") return `この期間の最大 ${fmt(max[0])} ${it.unit}（${max[1]}）`;
  const last = seriesList.at(-1).map((v, i) => [v, labels[i]]).filter(([v]) => v != null);
  const min = (last.length ? last : first).reduce((a, b) => (b[0] < a[0] ? b : a));
  // 気温のように 3 本（最高・平均・最低）あるときは、平均は真ん中の線から
  const mid = (seriesList.length === 3 ? seriesList[1] : seriesList[0]).filter((v) => v != null);
  const mean = mid.reduce((s, v) => s + v, 0) / (mid.length || 1);
  return `平均 ${fmt(mean)} ${it.unit}・最高 ${fmt(max[0])}（${max[1]}）・最低 ${fmt(min[0])}（${min[1]}）`;
}

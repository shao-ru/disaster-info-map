// test.js - 課題の自動チェック（教員が用意。書き換えないこと）

import { loadRegions, loadShelters, loadBoundary } from "./data.js";
import { bufferArea, circleArea, bboxOf, bboxesOverlap, isInside } from "./geo.js";
import { getRegion } from "./student/region.js";
import { findPrefectures, filterInArea } from "./student/search.js";
import { isOk, matchesConditions } from "./student/conditions.js";
import { ATTR_KEYS } from "./shelters.js";

const out = document.getElementById("out");
out.textContent = "";

function section(title) {
  const h = document.createElement("h2");
  h.textContent = title;
  const sum = document.createElement("p");
  sum.className = "sum";
  out.append(h, sum);
  return { sum, passed: 0, total: 0 };
}

function report(sec, name, ok, hint) {
  sec.total++;
  if (ok) sec.passed++;
  const p = document.createElement("div");
  p.className = "case " + (ok ? "ok" : "ng");
  p.textContent = `${ok ? "✅" : "❌"} ${name}`;
  out.append(p);
  if (!ok && hint) {
    const h = document.createElement("div");
    h.className = "hint";
    h.textContent = hint;
    out.append(h);
  }
  sec.sum.textContent = `${sec.passed} / ${sec.total} 合格` + (sec.passed === sec.total ? "　🎉 完成！" : "");
}

async function safe(fn) {
  try { return { value: await fn() }; } catch (e) { return { error: e }; }
}

const regions = await loadRegions();
const city = (pref, name) => regions.cities.find((c) => c.pref === pref && c.name === name);
const prefName = (code) => regions.prefectures.find((p) => p.code === code)?.name || code;

// 共通で使う範囲
const kashiwa = city("千葉県", "柏市");
const areas = [
  { label: "柏市＋周辺 5 km", area: bufferArea(await loadBoundary(kashiwa), 5) },
  { label: "取手駅から半径 10 km（千葉・茨城の県境）", area: circleArea({ lng: 140.0626, lat: 35.8957 }, 10) },
  { label: "東京駅から半径 20 km", area: circleArea({ lng: 139.7671, lat: 35.6812 }, 20) },
  { label: "大阪駅から半径 10 km", area: circleArea({ lng: 135.4959, lat: 34.7024 }, 10) },
];
// 正解の準備：四角形が重なる県（候補）と、実際に避難所が範囲内にある県
for (const a of areas) {
  const box = bboxOf(a.area);
  a.candidates = [...new Set(regions.cities.filter((c) => bboxesOverlap(c.bbox, box)).map((c) => c.prefCode))];
  a.inside = (await loadShelters(a.candidates)).filter((f) => isInside(f.geometry.coordinates, a.area));
  a.truth = [...new Set(a.inside.map((f) => f.properties.prefCode))];
}

// ---------------- 課題 1 ----------------
{
  const sec = section("課題 1  getRegion()  ★☆☆☆☆");
  const cases = [city("千葉県", "柏市"), city("千葉県", "流山市"), city("茨城県", "取手市"),
    regions.cities.find((c) => c.pref === "北海道"), regions.cities.filter((c) => c.pref === "沖縄県").at(-1)];
  for (const exp of cases) {
    const r = await safe(() => getRegion(exp.pref, exp.name, regions));
    const ok = !r.error && r.value && r.value.code === exp.code;
    report(sec, `「${exp.pref}」「${exp.name}」→ ${exp.fullName} を返す`, ok,
      r.error ? `エラー：${r.error.message}` : `返ってきたのは ${r.value ? r.value.fullName : r.value} です`);
  }
  const r = await safe(() => getRegion("千葉県", "存在しない市", regions));
  report(sec, "存在しない市のときは null を返す", !r.error && r.value === null,
    r.error ? `エラー：${r.error.message}`
      : `返ってきたのは ${r.value && r.value.fullName ? r.value.fullName : r.value} です（find は見つからないと undefined を返します）`);
}

// ---------------- 課題 2 ----------------
{
  const sec = section("課題 2  findPrefectures()  ★★☆☆☆");
  for (const a of areas) {
    const r = await safe(() => findPrefectures(a.area, regions));
    if (r.error) { report(sec, a.label, false, `エラー：${r.error.message}`); continue; }
    const got = r.value || [];
    const missing = a.truth.filter((c) => !got.includes(c));
    report(sec, `${a.label}：${a.truth.map(prefName).join("・")} が含まれている`, missing.length === 0,
      `${missing.map(prefName).join("・")} が足りません（返ってきたのは [${got.join(", ")}]）`);
    const dup = got.length !== new Set(got).size;
    report(sec, `${a.label}：重複がなく、関係のない県を含まない`, !dup && got.length <= a.candidates.length,
      dup ? "同じ県コードが 2 回以上入っています" : `関係のない県まで含まれています（${got.length} 件）`);
  }
}

// ---------------- 課題 3 ----------------
{
  const sec = section("課題 3  filterInArea()  ★★☆☆☆");
  for (const a of areas.slice(0, 3)) {
    const all = await loadShelters(a.candidates);
    const r = await safe(() => filterInArea(all, a.area));
    if (r.error) { report(sec, a.label, false, `エラー：${r.error.message}`); continue; }
    const got = new Set((r.value || []).map((f) => f.properties.id));
    const exp = new Set(a.inside.map((f) => f.properties.id));
    const extra = [...got].filter((id) => !exp.has(id)).length;
    const missing = [...exp].filter((id) => !got.has(id)).length;
    report(sec, `${a.label}：範囲内の ${exp.size} 件ちょうど`, extra === 0 && missing === 0,
      `範囲の外の避難所が ${extra} 件入っていて、範囲の中の避難所が ${missing} 件足りません`);
  }
}

// ---------------- 課題 4-1 ----------------
{
  const sec = section("課題 4-1  isOk()  ★★☆☆☆");
  const show = (v) => (v === null ? "null（不明）" : `"${v}"`);
  const cases = [
    ["可", { conditional: false, unknown: false }, true],
    ["不可", { conditional: true, unknown: true }, false],
    ["条件付き", { conditional: true, unknown: false }, true],
    ["条件付き", { conditional: false, unknown: true }, false],
    [null, { conditional: false, unknown: true }, true],
    [null, { conditional: true, unknown: false }, false],
  ];
  for (const [value, opt, exp] of cases) {
    const r = await safe(() => isOk(value, opt));
    report(sec, `値 ${show(value)}・条件付き ${opt.conditional ? "OK" : "NG"}・不明 ${opt.unknown ? "OK" : "NG"} → ${exp}`,
      !r.error && r.value === exp, r.error ? `エラー：${r.error.message}` : `返ってきたのは ${r.value} です`);
  }
}

// ---------------- 課題 4-2 ----------------
{
  const sec = section("課題 4-2  matchesConditions()  ★★★☆☆");
  const attrs = (v) => ({ ...Object.fromEntries(ATTR_KEYS.map((k) => [k, null])), ...v });
  const cond = (c) => ({ hazards: [], people: [], restricted: false, conditional: true, unknown: true, ...c });
  const cases = [
    ["何も選ばず、値はすべて不明（不明 OK）", attrs({}), cond({}), true],
    ["利用条件が「不可」（直接行けない）", attrs({ access: "不可", flood: "可" }), cond({ restricted: true }), false],
    ["利用条件が「条件付き」（対象者のみ）で、「対象者限定も含める」なし", attrs({ access: "条件付き" }), cond({}), false],
    ["利用条件が「条件付き」（対象者のみ）で、「対象者限定も含める」あり", attrs({ access: "条件付き" }), cond({ restricted: true }), true],
    ["洪水を選び、洪水が「条件付き」、条件付き OK", attrs({ access: "可", flood: "条件付き" }), cond({ hazards: ["flood"] }), true],
    ["洪水を選び、洪水が「条件付き」、条件付き NG", attrs({ access: "可", flood: "条件付き" }), cond({ hazards: ["flood"], conditional: false }), false],
    ["洪水と地震を選び、洪水「可」・地震「不可」", attrs({ access: "可", flood: "可", quake: "不可" }), cond({ hazards: ["flood", "quake"] }), false],
    ["選んでいない災害は関係ない（洪水「不可」でも、何も選ばなければ合う）", attrs({ access: "可", flood: "不可" }), cond({}), true],
    ["高齢者とペットを選び、高齢者「可」・ペット 不明、不明 NG", attrs({ access: "可", elderly: "可" }), cond({ people: ["elderly", "pet"], unknown: false }), false],
    ["高齢者とペットを選び、高齢者「可」・ペット「可」", attrs({ access: "可", elderly: "可", pet: "可" }), cond({ people: ["elderly", "pet"], unknown: false }), true],
    ["利用条件が不明で、不明 NG", attrs({ flood: "可" }), cond({ hazards: ["flood"], unknown: false }), false],
  ];
  for (const [name, a, c, exp] of cases) {
    const r = await safe(() => matchesConditions(a, c));
    report(sec, `${name} → ${exp}`, !r.error && r.value === exp,
      r.error ? `エラー：${r.error.message}` : `返ってきたのは ${r.value} です`);
  }
}

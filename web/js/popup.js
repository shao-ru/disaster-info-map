// popup.js - 避難所をクリックしたときに表示する吹き出しの中身を作る
// （データの文字はすべて textContent で入れる。HTML として解釈させない）

import { CONFIG } from "./config.js";
import { formatDistance } from "./shelters.js";

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

export function buildPopup(props, km, originLabel) {
  const box = el("div", "popup");
  box.append(el("h3", null, props.name));

  // 種別バッジ
  const badges = el("div", "badges");
  if (props.shelter) badges.append(el("span", "badge badge-shelter", "指定避難所"));
  if (props.emergency) badges.append(el("span", "badge badge-emergency", "指定緊急避難場所"));
  box.append(badges);

  // 洪水への対応
  let floodText = "情報なし（指定緊急避難場所ではない）";
  if (props.emergency) floodText = props.flood ? "対応" : "対応していない";
  const flood = el("p", props.flood ? "flood-ok" : "flood-ng");
  flood.append(el("b", null, "洪水："), document.createTextNode(floodText));
  box.append(flood);

  // 対応する災害
  if (props.hazards && props.hazards.length) {
    const names = props.hazards.map((h) => CONFIG.hazardLabels[h] || h).join("、");
    const p = el("p");
    p.append(el("b", null, "対応する災害："), document.createTextNode(names));
    box.append(p);
  }

  // 受入対象者・備考
  if (props.target) {
    const p = el("p");
    p.append(el("b", null, "受入対象者："), document.createTextNode(props.target));
    box.append(p);
  }
  if (props.note) box.append(el("p", "muted", props.note));

  box.append(el("p", "muted", props.address));
  if (km != null) box.append(el("p", null, `${originLabel}から直線で ${formatDistance(km)}`));
  box.append(el("p", "popup-id", `共通ID：${(props.ids || [props.id]).join(" / ")}`)); // データを直すとき、_refine.csv をこの ID で検索する

  return box;
}

// popup.js - 避難所をクリックしたときに表示する吹き出しの中身を作る
// （データの文字はすべて textContent で入れる。HTML として解釈させない）

import { CONFIG } from "./config.js";
import { formatDistance, fullAttrs, sourceOf, HAZARD_KEYS } from "./shelters.js";
import { isLocalServer, renderPhotos } from "./photos.js";

const MARK = { "可": "○", "条件付き": "△", "不可": "×" };
const CLASS = { "可": "ok", "条件付き": "cond", "不可": "ng" };
const SOURCE = { survey: "調査で確認", auto: "備考・受入対象者から推定", gsi: "国土地理院の指定" };
const POPUP_PEOPLE = ["elderly", "disabled", "infant", "pet"];

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

// 値の一覧（○ △ × ？）
function marks(props, attrs, keys, labels) {
  const box = el("div", "marks");
  for (const key of keys) {
    const v = attrs[key];
    const src = sourceOf(props, key);
    const span = el("span", `mark mark-${CLASS[v] || "unknown"}${src === "survey" ? " mark-survey" : ""}`);
    span.append(el("b", null, v == null ? "？" : MARK[v]), labels[key]);
    span.title = v == null ? "不明" : `${v}（${SOURCE[src]}）`;
    box.append(span);
  }
  return box;
}

function accessLine(props, attrs) {
  const note = props.accessNote || "";
  const lines = {
    "可": ["access-ok", "だれでも利用できます"],
    "条件付き": ["access-limited", `対象者のみ${note ? "：" + note : ""}`],
    "不可": ["access-no", `直接は行けません（二次避難所など）${note ? "：" + note : ""}`],
  };
  const [cls, text] = lines[attrs.access] || ["access-unknown", "利用条件：不明"];
  return el("p", `access ${cls}`, text);
}

// feature：避難所、km：基準地点からの距離、opts.onAddPhoto(feature, refresh)：「写真を追加」を押したとき
export function buildPopup(feature, km, originLabel, opts = {}) {
  const props = feature.properties;
  const attrs = fullAttrs(props);
  const box = el("div", "popup");
  box.append(el("h3", null, props.name));

  // 種別バッジ
  const badges = el("div", "badges");
  if (props.shelter) badges.append(el("span", "badge badge-shelter", "指定避難所"));
  if (props.emergency) badges.append(el("span", "badge badge-emergency", "指定緊急避難場所"));
  if (attrs.welfare === "可") badges.append(el("span", "badge badge-welfare", "福祉避難所"));
  box.append(badges);

  box.append(accessLine(props, attrs));
  box.append(el("p", "marks-title", "災害"), marks(props, attrs, HAZARD_KEYS, CONFIG.hazardLabels));
  box.append(el("p", "marks-title", "受入れ"), marks(props, attrs, POPUP_PEOPLE, CONFIG.peopleLabels));
  box.append(el("p", "marks-legend", "○ 可　△ 条件付き　× 不可　？ 不明　（太字の枠：調査で確認）"));

  if (props.survey) {
    const p = el("p", "muted", `調査：${props.survey.by || "—"}　根拠：`);
    if (/^https?:\/\//.test(props.survey.source)) {
      const a = el("a", null, props.survey.source);
      a.href = props.survey.source;
      a.target = "_blank";
      a.rel = "noopener";
      p.append(a);
    } else {
      p.append(props.survey.source);
    }
    box.append(p);
  }
  if (props.target && props.target !== props.accessNote) {
    const p = el("p");
    p.append(el("b", null, "受入対象者："), document.createTextNode(props.target));
    box.append(p);
  }
  if (props.note) box.append(el("p", "muted", props.note));

  // 写真（あとから読み込む）
  const photos = el("div", "photos");
  photos.hidden = true;
  box.append(photos);
  renderPhotos(photos, props.id);
  isLocalServer().then((local) => {
    if (!local || !opts.onAddPhoto) return;
    const btn = el("button", "add-photo", "📷 写真を追加");
    btn.type = "button";
    btn.addEventListener("click", () => opts.onAddPhoto(feature, () => renderPhotos(photos, props.id)));
    photos.after(btn);
  });

  box.append(el("p", "muted", props.address));
  if (km != null) box.append(el("p", null, `${originLabel}から直線で ${formatDistance(km)}`));
  box.append(el("p", "popup-id", `共通ID：${(props.ids || [props.id]).join(" / ")}`)); // データを直すとき、_refine.csv や attrs をこの ID で検索する
  return box;
}

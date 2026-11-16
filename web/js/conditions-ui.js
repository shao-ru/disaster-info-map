// conditions-ui.js - 画面の「条件」（利用対象・災害・受入れ・チェック）を作り、選んだ内容を返す（教員が用意）

import { CONFIG } from "./config.js";
import { HAZARD_KEYS, PEOPLE_KEYS } from "./shelters.js";

function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text != null) e.textContent = text;
  return e;
}

// container の中に条件の画面を作る。条件が変わるたびに onChange(conditions) を呼ぶ
export function setupConditions(container, onChange) {
  const c = structuredClone(CONFIG.defaultConditions);
  const changed = () => onChange(structuredClone(c));

  const row = (label) => {
    const r = el("div", "cond-row");
    r.append(el("span", "cond-label", label));
    const body = el("div", "cond-body");
    r.append(body);
    container.append(r);
    return body;
  };

  // 利用対象（どちらか 1 つ）
  const access = row("利用");
  for (const [value, text] of [[false, "だれでも使える所"], [true, "対象者限定も含める"]]) {
    const label = el("label", "cond-radio");
    const input = Object.assign(document.createElement("input"), { type: "radio", name: "cond-access", checked: c.restricted === value });
    input.addEventListener("change", () => { c.restricted = value; changed(); });
    label.append(input, text);
    access.append(label);
  }

  // 災害・受入れ（いくつでも選べるボタン）
  const chips = (body, keys, labels, list) => {
    for (const key of keys) {
      const b = el("button", "chip", labels[key]);
      b.type = "button";
      b.setAttribute("aria-pressed", String(c[list].includes(key)));
      b.addEventListener("click", () => {
        const on = !c[list].includes(key);
        c[list] = on ? [...c[list], key] : c[list].filter((k) => k !== key);
        b.setAttribute("aria-pressed", String(on));
        changed();
      });
      body.append(b);
    }
  };
  chips(row("災害"), HAZARD_KEYS, CONFIG.hazardLabels, "hazards");
  chips(row("受入れ"), PEOPLE_KEYS, CONFIG.peopleLabels, "people");

  // チェック
  const checks = row("");
  for (const [key, text] of [["conditional", "条件付き（2 階以上など）も合うとみなす"], ["unknown", "不明も合うとみなす"]]) {
    const label = el("label", "cond-check");
    const input = Object.assign(document.createElement("input"), { type: "checkbox", checked: c[key] });
    input.addEventListener("change", () => { c[key] = input.checked; changed(); });
    label.append(input, text);
    checks.append(label);
  }
  return structuredClone(c);
}

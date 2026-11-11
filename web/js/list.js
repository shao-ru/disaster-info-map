// list.js - 近い避難所の一覧を表示する

import { formatDistance } from "./shelters.js";

// items: nearest() の結果、onSelect: 項目を押したときの処理
export function renderList(container, items, onSelect) {
  container.textContent = "";
  if (!items.length) {
    container.append(Object.assign(document.createElement("p"), { textContent: "該当する避難所がありません" }));
    return;
  }
  const ol = document.createElement("ol");
  ol.className = "shelter-list";
  for (const { feature, km } of items) {
    const p = feature.properties;
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";

    const dot = document.createElement("span");
    dot.className = "dot " + (p.flood ? "dot-flood" : "dot-other");
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = p.name;
    const dist = document.createElement("span");
    dist.className = "dist";
    dist.textContent = formatDistance(km);

    btn.append(dot, name, dist);
    btn.addEventListener("click", () => onSelect(feature, km));
    li.append(btn);
    ol.append(li);
  }
  container.append(ol);
}

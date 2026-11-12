// contributors.js - 「参加者」ボタン：CONTRIBUTORS.md を読み込んで、ダイアログに表示する
//
// Markdown の一部（見出し・段落・箇条書き・表・太字・コード・リンク）だけを、HTML に変換します。
// 文字はすべて textContent で入れる（HTML として解釈させない）。

const MD_URL = "../CONTRIBUTORS.md";
const REPO = "https://github.com/shao-ru/disaster-info-map/blob/main/"; // 相対リンクの行き先

function el(tag, text) {
  const e = document.createElement(tag);
  if (text != null) e.textContent = text;
  return e;
}

// 1 行の中の **太字**、`コード`、[文字](URL) を変換する
function inline(parent, text) {
  const re = /\*\*(.+?)\*\*|`(.+?)`|\[(.+?)\]\((.+?)\)/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    parent.append(text.slice(last, m.index));
    if (m[1]) parent.append(el("strong", m[1]));
    else if (m[2]) parent.append(el("code", m[2]));
    else {
      const a = el("a", m[3]);
      a.href = /^https?:/.test(m[4]) ? m[4] : REPO + m[4];
      a.target = "_blank";
      a.rel = "noopener";
      parent.append(a);
    }
    last = m.index + m[0].length;
  }
  parent.append(text.slice(last));
}

const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

function renderTable(lines) {
  const table = el("table");
  const head = cells(lines[0]);
  const ghCol = head.indexOf("GitHub");
  const tr = el("tr");
  head.forEach((h) => tr.append(el("th", h)));
  table.append(el("thead"));
  table.tHead.append(tr);
  const body = el("tbody");
  for (const line of lines.slice(2)) {           // 2 行目は |---|---| なので飛ばす
    const row = el("tr");
    cells(line).forEach((c, i) => {
      const td = el("td");
      if (i === ghCol && /^[\w-]+$/.test(c)) {     // GitHub ユーザー名はプロフィールへのリンクにする
        const a = el("a", c);
        a.href = `https://github.com/${c}`;
        a.target = "_blank";
        a.rel = "noopener";
        td.append(a);
      } else {
        inline(td, c);
      }
      row.append(td);
    });
    body.append(row);
  }
  table.append(body);
  return table;
}

function renderMarkdown(md) {
  const box = document.createDocumentFragment();
  const lines = md.replace(/\r/g, "").split("\n");
  // 最初の「# 見出し」は、ダイアログのタイトルと同じなので表示しない
  const first = lines.findIndex((l) => l.trim());
  if (first >= 0 && /^#\s/.test(lines[first])) lines.splice(first, 1);
  for (let i = 0; i < lines.length; ) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const h = line.match(/^(#{1,3})\s+(.*)/);
    if (h) {
      const e = el(`h${h[1].length + 2}`);          // # → h3（ダイアログの中なので小さめに）
      inline(e, h[2]);
      box.append(e);
      i++;
    } else if (line.startsWith("|")) {
      const block = [];
      while (i < lines.length && lines[i].startsWith("|")) block.push(lines[i++]);
      box.append(renderTable(block));
    } else if (/^[-*]\s/.test(line)) {
      const ul = el("ul");
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        const li = el("li");
        inline(li, lines[i++].replace(/^[-*]\s+/, ""));
        ul.append(li);
      }
      box.append(ul);
    } else {
      const p = el("p");
      const block = [];
      while (i < lines.length && lines[i].trim() && !/^(#|\||[-*]\s)/.test(lines[i])) block.push(lines[i++]);
      inline(p, block.join(" "));
      box.append(p);
    }
  }
  return box;
}

export function setupContributors(button, dialog) {
  const body = dialog.querySelector(".dialog-body");
  button.addEventListener("click", async () => {
    body.textContent = "読み込み中…";
    dialog.showModal();
    try {
      const res = await fetch(MD_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`${res.status}`);
      body.textContent = "";
      body.append(renderMarkdown(await res.text()));
    } catch (err) {
      body.textContent = `CONTRIBUTORS.md を読み込めませんでした（${err.message}）`;
    }
  });
  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
  // ダイアログの外側（暗い部分）をクリックしても閉じる
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
}

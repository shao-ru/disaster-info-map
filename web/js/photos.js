// photos.js - 避難所の写真：一覧の読み込み・表示・「写真を追加」（教員が用意）
//
// 「写真を追加」は、手元で serve.py を動かしているときだけ使えます（公開中のサイトでは表示されません）。
// 写真はブラウザーの中で次のように処理してから、serve.py に送ります。
//   1. 撮影日と撮影場所を写真から読む（撮影日は入力欄に入れる。場所は避難所から離れていないかの確認だけに使う）
//   2. 長い辺を 1600 px 以下に小さくし、JPEG で作り直す（このとき位置情報などは消える）

import { CONFIG } from "./config.js";
import { distanceKm } from "./shelters.js";

const FAR_KM = 0.3;   // 撮影場所が避難所からこれ以上離れていたら注意する
const USER_RE = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/;

// ---------------------------------------------------------------- 写真の一覧
let indexPromise = null;
export function loadPhotoIndex(force = false) {
  if (force || !indexPromise) {
    indexPromise = fetch(CONFIG.photoIndexUrl, { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : {}))
      .catch(() => ({}));
  }
  return indexPromise;
}

// 手元の serve.py で開いているか（そのときだけ「写真を追加」を出す）
let localPromise = null;
export function isLocalServer() {
  if (!["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) return Promise.resolve(false);
  if (!localPromise) {
    localPromise = fetch("../api/ping", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : {}))
      .then((d) => d.local === true)
      .catch(() => false);
  }
  return localPromise;
}

// container に、その避難所の写真を並べる
export async function renderPhotos(container, id) {
  const list = (await loadPhotoIndex())[id] || [];
  container.textContent = "";
  for (const p of list) {
    const a = document.createElement("a");
    a.href = CONFIG.photosDir + p.file;
    a.target = "_blank";
    a.rel = "noopener";
    a.title = [p.taken, p.by, p.note].filter(Boolean).join("　");
    const img = document.createElement("img");
    img.src = CONFIG.photosDir + p.file;
    img.alt = p.note || "避難所の写真";
    img.loading = "lazy";
    a.append(img);
    container.append(a);
  }
  container.hidden = list.length === 0;
}

// ---------------------------------------------------------------- 写真の中の撮影日・撮影場所（EXIF）を読む
function readExif(buffer) {
  const v = new DataView(buffer);
  if (v.byteLength < 4 || v.getUint16(0) !== 0xffd8) return {};
  let off = 2;
  while (off + 10 < v.byteLength) {
    const marker = v.getUint16(off);
    if ((marker & 0xff00) !== 0xff00) break;
    if (marker === 0xffe1 && v.getUint32(off + 4) === 0x45786966) return readTiff(v, off + 10);
    off += 2 + v.getUint16(off + 2);
  }
  return {};
}

function readTiff(v, t) {
  const le = v.getUint16(t) === 0x4949;
  const u16 = (o) => v.getUint16(o, le);
  const u32 = (o) => v.getUint32(o, le);
  const ifd = (o) => {
    const tags = {};
    const n = u16(o);
    for (let i = 0; i < n; i++) {
      const e = o + 2 + i * 12;
      tags[u16(e)] = { count: u32(e + 4), at: e + 8 };
    }
    return tags;
  };
  const ascii = (tag) => {
    const o = tag.count > 4 ? t + u32(tag.at) : tag.at;
    let s = "";
    for (let i = 0; i < tag.count - 1; i++) s += String.fromCharCode(v.getUint8(o + i));
    return s;
  };
  const rationals = (tag) => {
    const o = t + u32(tag.at);
    return Array.from({ length: tag.count }, (_, i) => u32(o + i * 8) / u32(o + i * 8 + 4));
  };
  const out = {};
  const ifd0 = ifd(t + u32(t + 4));
  if (ifd0[0x8769]) {                                   // Exif：撮影日時
    const ex = ifd(t + u32(ifd0[0x8769].at));
    const d = ex[0x9003] || ex[0x9004];
    if (d) out.taken = ascii(d);
  }
  if (!out.taken && ifd0[0x0132]) out.taken = ascii(ifd0[0x0132]);
  if (ifd0[0x8825]) {                                   // GPS：撮影場所
    const g = ifd(t + u32(ifd0[0x8825].at));
    if (g[2] && g[4]) {
      const deg = (a) => a[0] + a[1] / 60 + a[2] / 3600;
      let lat = deg(rationals(g[2]));
      let lng = deg(rationals(g[4]));
      if (g[1] && ascii(g[1]) === "S") lat = -lat;
      if (g[3] && ascii(g[3]) === "W") lng = -lng;
      if (Number.isFinite(lat) && Number.isFinite(lng)) out.gps = { lat, lng };
    }
  }
  if (out.taken) {
    const m = out.taken.match(/^(\d{4}):(\d{2}):(\d{2})/);
    out.taken = m ? `${m[1]}-${m[2]}-${m[3]}` : undefined;
  }
  return out;
}

export function exifOf(buffer) {
  try { return readExif(buffer); } catch { return {}; }
}

// ---------------------------------------------------------------- 小さくして JPEG に作り直す（位置情報などは消える）
async function shrink(file, maxSide = 1600) {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const s = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * s);
  canvas.height = Math.round(bmp.height * s);
  canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
  for (const q of [0.85, 0.75, 0.6]) {
    const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", q));
    if (blob && blob.size <= 950_000) return blob;
  }
  throw new Error("写真を小さくできませんでした");
}

const toBase64 = (blob) => new Promise((resolve, reject) => {
  const r = new FileReader();
  r.onload = () => resolve(String(r.result).split(",")[1]);
  r.onerror = () => reject(r.error);
  r.readAsDataURL(blob);
});

const today = () => new Date().toLocaleDateString("sv-SE");   // 2026-11-16 の形

function remembered(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key) || "";
    localStorage.setItem(key, value);
  } catch { /* 保存できない環境では何もしない */ }
  return value || "";
}

// ---------------------------------------------------------------- 「写真を追加」ダイアログ
export function setupPhotoDialog(dialog) {
  const $ = (sel) => dialog.querySelector(sel);
  const form = $("form");
  let current = null;   // { feature, onSaved }
  let blob = null;
  let far = false;      // 撮影場所が遠いと注意したか

  const msg = (text, kind = "") => {
    $(".photo-msg").textContent = text;
    $(".photo-msg").className = "photo-msg" + (kind ? ` photo-msg-${kind}` : "");
  };

  $(".dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });

  $("#photo-file").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    blob = null;
    far = false;
    $("#photo-preview").hidden = true;
    $(".photo-gps").textContent = "";
    msg("");
    if (!file) return;
    msg("写真を読み込んでいます…");
    const exif = exifOf(await file.arrayBuffer());
    if (exif.taken) $("#photo-taken").value = exif.taken;
    try {
      blob = await shrink(file);
    } catch {
      msg("この写真は読み込めませんでした。JPEG か PNG にしてから選んでください（iPhone の HEIC は、写真アプリで JPEG に書き出せます）", "ng");
      return;
    }
    $("#photo-preview").src = URL.createObjectURL(blob);
    $("#photo-preview").hidden = false;
    const [lng, lat] = current.feature.geometry.coordinates;
    if (exif.gps) {
      const km = distanceKm(exif.gps, { lng, lat });
      far = km > FAR_KM;
      $(".photo-gps").textContent = `撮影した場所は、この避難所から約 ${km < 1 ? Math.round(km * 1000) + " m" : km.toFixed(1) + " km"} です。`;
      if (far) msg("撮影した場所が避難所から離れています。別の避難所の写真ではありませんか？ よければ、もう一度「保存」を押してください。", "warn");
      else msg("");
    } else {
      $(".photo-gps").textContent = "写真に撮影場所の記録がないため、場所の確認はできません。";
      msg("");
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const by = $("#photo-by").value.trim();
    if (!blob) return msg("写真を選んでください", "ng");
    if (!USER_RE.test(by)) return msg("GitHub のユーザー名を、英数字とハイフンで入れてください", "ng");
    if (!$("#photo-taken").value) return msg("撮影日を入れてください", "ng");
    if (far) { far = false; return; }   // 1 回目は注意だけ（もう一度押すと保存）
    remembered("photoBy", by);
    $("#photo-save").disabled = true;
    msg("保存しています…");
    try {
      const res = await fetch("../api/photos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: current.feature.properties.id, by, taken: $("#photo-taken").value,
          note: $("#photo-note").value.trim(), image: await toBase64(blob),
        }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.error || `${res.status}`);
      msg(`保存しました：data/static/photos/${d.file}　コミットして Pull Request を出してください。`, "ok");
      blob = null;
      form.reset();
      $("#photo-by").value = by;
      $("#photo-preview").hidden = true;
      $(".photo-gps").textContent = "";
      await loadPhotoIndex(true);
      current.onSaved?.();
    } catch (err) {
      msg(`保存できませんでした（${err.message}）`, "ng");
    } finally {
      $("#photo-save").disabled = false;
    }
  });

  // 避難所を指定して開く
  return (feature, onSaved) => {
    current = { feature, onSaved };
    blob = null;
    far = false;
    form.reset();
    $("#photo-target").textContent = `${feature.properties.name}（${feature.properties.id}）`;
    $("#photo-taken").value = today();
    $("#photo-by").value = remembered("photoBy");
    $("#photo-preview").hidden = true;
    $(".photo-gps").textContent = "";
    msg("");
    dialog.showModal();
  };
}

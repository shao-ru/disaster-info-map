"""
build_shelters.py  -  避難所の CSV から、アプリ用の GeoJSON を作るツール

  data/raw/避難所/mergeFromCity_1/mergeFromCity_1.csv     … 元データ（国土地理院）。書き換えない
  data/raw/避難所/mergeFromCity_2/mergeFromCity_2.csv
        │  （最初に 1 回だけ、そのままコピー： --init）
        ▼
  data/static/shelters/mergeFromCity_1_refine.csv        … 指定避難所（みんなで直す）
  data/static/shelters/mergeFromCity_2_refine.csv        … 指定緊急避難場所（みんなで直す）
        │  このツール
        ▼
  data/static/shelters/<県コード>.geojson                 … アプリが読み込む
  data/static/regions.json の施設数（count）

■ 直し方
  _refine.csv を直接直します（列は国土地理院のデータと同じ）。
  - 施設を探す：アプリで施設をクリック → 吹き出しの一番下の「共通ID」で検索
  - 削除：その行を消す　　追加：行を足す（共通ID は重ならないように）
  - 編集には VS Code（拡張機能 Rainbow CSV）を使う。Excel は使わない
    （Excel で保存すると、ファイル全体の書き方が変わり、Git の差分が読めなくなるため）

■ 1 つの施設にまとめる方法
  指定避難所と指定緊急避難場所の両方に指定されている施設は、2 つのファイルに 1 行ずつある。
  「共通ID の先頭 11 文字（E＋市区町村コード 5 桁＋番号 5 桁）」と「施設名」が同じ行を、
  同じ施設としてまとめる。共通ID の先頭 11 文字だけでは、同じ住所の別の施設
  （例：○○小学校 と ○○まちづくりセンター）まで 1 つになってしまうので、施設名も使う。

エラーがあると、どのファイルの何行目かを表示して、何も書き換えずに終了します。

使い方（プロジェクトのフォルダーで）：
  uv run ./code/build_shelters.py
  uv run ./code/build_shelters.py --init     … raw から _refine.csv を作る（教員・最初の 1 回だけ）
"""

import argparse
import csv
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = {1: ROOT / "data/raw/避難所/mergeFromCity_1/mergeFromCity_1.csv",
       2: ROOT / "data/raw/避難所/mergeFromCity_2/mergeFromCity_2.csv"}
OUT_DIR = ROOT / "data/static/shelters"
SRC = {1: OUT_DIR / "mergeFromCity_1_refine.csv",    # 指定避難所
       2: OUT_DIR / "mergeFromCity_2_refine.csv"}    # 指定緊急避難場所
REGIONS = ROOT / "data/static/regions.json"

# 指定緊急避難場所の災害種別（CSV の列名 → GeoJSON のキー）
HAZARDS = {
    "洪水": "flood", "内水氾濫": "inland", "崖崩れ、土石流及び地滑り": "landslide",
    "地震": "quake", "大規模な火事": "fire", "高潮": "surge", "津波": "tsunami", "火山現象": "volcano",
}
COMMON = ["共通ID", "都道府県名及び市町村名", "施設・場所名", "住所", "緯度", "経度", "備考"]
REQUIRED = {1: COMMON + ["受入対象者"], 2: COMMON + list(HAZARDS)}
LAT_RANGE, LON_RANGE = (20.0, 46.0), (122.0, 154.0)   # 日本のおおよその範囲
PREF_RE = re.compile(r"^(北海道|.{2,3}?[都府県])")
ID_RE = re.compile(r"E\d{12}[0-9A-Z]")   # 末尾が英字の ID もある（例：E206020000520A）


def split_name(full):
    """「千葉県柏市」→（"千葉県", "柏市"）"""
    m = PREF_RE.match(full)
    return (m.group(1), full[m.end():]) if m else ("", full)


def norm(name):
    """施設名の比較用：全角・半角をそろえ、空白を消す"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", name))


def read(kind, errors, seen):
    """_refine.csv を読み、チェックして、正しい行だけ返す"""
    path = SRC[kind]
    raw = path.read_bytes()
    if not raw.startswith(b"\xef\xbb\xbf"):
        errors.append(f"{path.name}：BOM 付き UTF-8 ではありません。Excel で保存しましたか？（VS Code で保存し直してください）")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        errors.append(f"{path.name}：UTF-8 で読めません（Excel で保存すると Shift_JIS になることがあります）")
        return []
    rows = list(csv.DictReader(text.splitlines()))
    if rows and (missing := [c for c in REQUIRED[kind] if c not in rows[0]]):
        errors.append(f"{path.name}：列が足りません：{', '.join(missing)}")
        return []
    good = []
    for i, r in enumerate(rows, start=2):   # 1 行目は見出し
        where = f"{path.name} {i} 行目"
        cid = (r["共通ID"] or "").strip()
        ok = True
        if not ID_RE.fullmatch(cid):
            errors.append(f"{where}：共通ID「{cid}」は「E＋数字 12 桁＋数字か英字 1 文字」にしてください")
            ok = False
        elif cid in seen:
            errors.append(f"{where}：共通ID「{cid}」が {seen[cid]} と重複しています")
            ok = False
        seen[cid] = where
        if not (r["施設・場所名"] or "").strip():
            errors.append(f"{where}：施設・場所名が空です")
        try:
            lat, lon = float(r["緯度"]), float(r["経度"])
            if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
                errors.append(f"{where}：位置（緯度={lat}, 経度={lon}）が日本の外です。緯度と経度が逆かも？")
                ok = False
        except (TypeError, ValueError):
            errors.append(f"{where}：緯度・経度が数値ではありません（「{r['緯度']}」「{r['経度']}」）")
            ok = False
        if kind == 2:
            for col in HAZARDS:
                if (r[col] or "").strip() not in ("", "1"):
                    errors.append(f"{where}：「{col}」は 1 か空にしてください（今は「{r[col]}」）")
        if ok:
            good.append(r)
    return good


def facility(r):
    cid = r["共通ID"].strip()
    pref, city = split_name(r["都道府県名及び市町村名"].strip())
    return {"id": cid, "ids": [cid], "name": r["施設・場所名"].strip(), "address": (r["住所"] or "").strip(),
            "prefCode": cid[1:3], "cityCode": cid[1:6], "pref": pref, "city": city,
            "lat": float(r["緯度"]), "lon": float(r["経度"]),
            "shelter": False, "emergency": False, "hazards": [], "target": "", "note": ""}


def build(rows1, rows2):
    facilities = []
    # 指定避難所を、（共通ID 先頭 11 文字, 施設名）ごとに並べておく
    waiting = defaultdict(list)
    for r in rows1:
        f = facility(r)
        f["shelter"] = True
        f["target"] = (r["受入対象者"] or "").strip()
        f["note"] = (r["備考"] or "").strip()
        facilities.append(f)
        waiting[(f["id"][:11], norm(f["name"]))].append(f)
    # 指定緊急避難場所：同じ施設があればまとめる。なければ新しい施設
    for r in rows2:
        key = (r["共通ID"].strip()[:11], norm(r["施設・場所名"]))
        if waiting[key]:
            f = waiting[key].pop(0)
            f["ids"].append(r["共通ID"].strip())
        else:
            f = facility(r)
            facilities.append(f)
        f["emergency"] = True
        f["hazards"] = [k for col, k in HAZARDS.items() if (r[col] or "").strip() == "1"]
        if not f["note"]:
            f["note"] = (r["備考"] or "").strip()
    return facilities


def to_feature(f):
    p = {k: v for k, v in f.items() if k not in ("lat", "lon")}
    p["flood"] = "flood" in f["hazards"]
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(f["lon"], 6), round(f["lat"], 6)]},
            "properties": p}


def main():
    ap = argparse.ArgumentParser(description="避難所の CSV からアプリ用の GeoJSON を作る")
    ap.add_argument("--init", action="store_true",
                    help="raw の元データを _refine.csv としてコピーする（みんなの修正が消えるので注意）")
    args = ap.parse_args()

    if args.init:
        for k in (1, 2):
            if SRC[k].exists():
                raise SystemExit(f"{SRC[k].name} はすでにあります。上書きすると修正が消えるので、消してからやり直してください")
            shutil.copyfile(RAW[k], SRC[k])
            print(f"コピー：{RAW[k].relative_to(ROOT)} → {SRC[k].relative_to(ROOT)}")
    for k in (1, 2):
        if not SRC[k].exists():
            raise SystemExit(f"{SRC[k].relative_to(ROOT)} がありません（教員が --init で作ります）")

    errors, seen = [], {}
    rows1, rows2 = read(1, errors, seen), read(2, errors, seen)
    if errors:
        print(f"❌ エラー {len(errors)} 件。何も書き換えていません。直してからもう一度実行してください。")
        for e in errors[:30]:
            print(f"   {e}")
        if len(errors) > 30:
            print(f"   …ほか {len(errors) - 30} 件")
        sys.exit(1)

    facilities = build(rows1, rows2)
    both = sum(1 for f in facilities if f["shelter"] and f["emergency"])
    print(f"指定避難所 {len(rows1)} 行・指定緊急避難場所 {len(rows2)} 行 → {len(facilities)} 施設（両方に指定 {both}）")

    by_pref = defaultdict(list)
    for f in sorted(facilities, key=lambda f: f["id"]):
        by_pref[f["prefCode"]].append(to_feature(f))
    for code, feats in sorted(by_pref.items()):
        gj = {"type": "FeatureCollection",
              "source": "国土地理院 指定緊急避難場所・指定避難所データ（shelters/*_refine.csv から作成）",
              "features": feats}
        (OUT_DIR / f"{code}.geojson").write_text(
            json.dumps(gj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✅ shelters/<県コード>.geojson：{len(by_pref)} 都道府県")

    if REGIONS.exists():   # 市区町村ごとの施設数を更新
        regions = json.loads(REGIONS.read_text(encoding="utf-8"))
        counts = Counter(f["cityCode"] for f in facilities)
        for c in regions["cities"]:
            c["count"] = counts.get(c["code"], 0)
        unknown = sorted(set(counts) - {c["code"] for c in regions["cities"]})
        if unknown:
            print(f"注意：regions.json に無い市区町村コード：{', '.join(unknown)}")
        REGIONS.write_text(json.dumps(regions, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("✅ regions.json の施設数を更新")


if __name__ == "__main__":
    main()

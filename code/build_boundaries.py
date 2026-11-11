"""
行政区域（市区町村の境界）を作るスクリプト（教員用）

入力： data/raw/admin_map/A002005212020DDSWC{01..47}.zip
       （e-Stat 2020年国勢調査 小地域（町丁・字等）境界データ、Shapefile、JGD2000）
出力： data/static/admin_boundaries/<県コード>.geojson … 市区町村ごとの多角形
       data/static/regions.json                  … 各市区町村の center / bbox を実際の境界で更新

処理の流れ：
  1. 町丁・字のポリゴンを読み込む（水面 HCODE=8154 は除く）
  2. 市区町村コード（県2桁＋市3桁）ごとに融合（dissolve）
     ※ 政令市の「区」（例：12101 千葉市中央区）は、避難所データに合わせて
       市全体のコード（12100 千葉市）にまとめる
  3. 形を簡略化して（約30m）、GeoJSON に書き出す

regions.json（市区町村の一覧）を読んで更新するため、regions.json があることが前提。

実行例（geopandas が必要）：
  uv run --with geopandas --with pyogrio python code/build_boundaries.py
  uv run --with geopandas --with pyogrio python code/build_boundaries.py --pref 12
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
from shapely import make_valid
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/admin_map"
STATIC = ROOT / "data/static"
SIMPLIFY_DEG = 0.0003   # 約30m。小さくすると精密だがファイルが大きくなる
WATER = "8154"          # HCODE：水面


def round_coords(obj, nd=5):
    """座標を小数点以下 nd 桁に丸める（ファイルを小さくするため）"""
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(v, nd) for v in obj]
        return [round_coords(o, nd) for o in obj]
    return obj


def build_pref(pcode, known):
    zp = RAW / f"A002005212020DDSWC{pcode}.zip"
    g = gpd.read_file(f"zip://{zp}!r2ka{pcode}.shp", encoding="cp932")
    g = g[(g["HCODE"] != WATER) & g["CITY_NAME"].notna()]  # 所属未定地などは除く
    g["code"] = g["PREF"] + g["CITY"]
    # 政令市の区 → 市のコードへ（避難所データ側に区のコードが無い場合だけ）
    def to_known(c):
        if c in known:
            return c
        # 政令市のコードは 1x0（例：14100 横浜市、14130 川崎市）。区は 1xx。
        # 区より小さい政令市コードのうち、一番近いものが親
        if c[2] == "1":
            cands = [k for k in known if k[:3] == c[:3] and k.endswith("0") and k <= c]
            if cands:
                return max(cands)
        return c
    g["code"] = g["code"].map(to_known)
    g["geometry"] = g.geometry.map(make_valid)
    d = g.dissolve(by="code", as_index=False, aggfunc={"CITY_NAME": "first"})
    d["geometry"] = d.geometry.simplify(SIMPLIFY_DEG, preserve_topology=True)
    feats, info = [], {}
    for _, row in d.iterrows():
        code = row["code"]
        name = known[code]["name"] if code in known else row["CITY_NAME"]
        geom = mapping(row.geometry)
        feats.append({"type": "Feature",
                      "properties": {"code": code, "name": name, "approx": False},
                      "geometry": {"type": geom["type"], "coordinates": round_coords(geom["coordinates"])}})
        p = row.geometry.representative_point()
        info[code] = {"name": name, "center": [round(p.x, 5), round(p.y, 5)],
                      "bbox": [round(v, 5) for v in row.geometry.bounds]}
    return feats, info


def main():
    ap = argparse.ArgumentParser(description="e-Stat 小地域境界から市区町村の境界を作る")
    ap.add_argument("--pref", nargs="*", help="県コード（例：12 13）。省略時は全国")
    args = ap.parse_args()
    regions = json.loads((STATIC / "regions.json").read_text(encoding="utf-8"))
    known = {c["code"]: c for c in regions["cities"]}
    prefs = args.pref or [f"{i:02d}" for i in range(1, 48)]
    total, missing = 0, []
    for pcode in prefs:
        feats, info = build_pref(pcode, known)
        # 境界が見つからない市区町村（避難所データにだけある）は、従来の凸包を残す
        out = STATIC / f"admin_boundaries/{pcode}.geojson"
        old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"features": []}
        have = {f["properties"]["code"] for f in feats}
        for f in old["features"]:
            if f["properties"].get("approx") and f["properties"]["code"] not in have:
                feats.append(f)
                missing.append(f["properties"]["code"])
        out.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                  ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for c in regions["cities"]:
            if c["code"] in info:
                c.update({k: v for k, v in info[c["code"]].items() if k != "name"})
        # 避難所データに無い市区町村（例：伊勢原市）も、選べるように追加する（count=0）
        pref_name = next(p["name"] for p in regions["prefectures"] if p["code"] == pcode)
        for code, v in info.items():
            if code not in known:
                c = {"code": code, "prefCode": pcode, "pref": pref_name, "name": v["name"],
                     "fullName": pref_name + v["name"], "center": v["center"], "bbox": v["bbox"], "count": 0}
                regions["cities"].append(c)
                known[code] = c
        regions["cities"].sort(key=lambda c: c["code"])
        total += len(info)
        print(f"{pcode}: {len(info)} 市区町村  {out.stat().st_size/1e6:.1f} MB")
    (STATIC / "regions.json").write_text(json.dumps(regions, ensure_ascii=False, separators=(",", ":")),
                                         encoding="utf-8")
    print(f"合計 {total} 市区町村。境界データが無く凸包のまま：{missing or 'なし'}")


if __name__ == "__main__":
    main()

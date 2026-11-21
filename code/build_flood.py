# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "geopandas>=1.0",
#     "numpy",
#     "pillow",
#     "pyogrio>=0.13.0",
#     "rasterio",
# ]
# ///
"""
洪水浸水想定区域（浸水深）の地図タイル（PNG）を作るスクリプト（教員用）

入力： data/raw/洪水浸水想定区域データ/洪水浸水想定区域（1次メッシュ単位）/A31b-25_{10,20}_<メッシュ>_GEOJSON.zip
       国土数値情報「洪水浸水想定区域（1次メッシュ単位）」A31b
         _10_ … 洪水予報河川・水位周知河川　　_20_ … その他の河川
出力： data/static/flood/<規模>/<z>/<x>/<y>.png   … 地図タイル（256×256、色は浸水深のランク）
       data/static/flood/<規模>/meta.json         … 範囲・ズーム・凡例・出典・タイルの一覧（アプリが読む）

元データについて：
  - ポリゴンの形をしているが、中身は約 5 m の格子（経度 1/16000 度 × 緯度 1/24000 度）。
    同じランクの隣り合う格子を 1 つの多角形にまとめたもの（ラスターをベクターにしたもの）
  - 属性は浸水深のランク 1 つだけ（A31b_201 など）。複数の河川は合成ずみで、重なる所は深い方
  - ランク：1 = 0〜0.5 m　2 = 0.5〜3 m　3 = 3〜5 m　4 = 5〜10 m　5 = 10〜20 m　6 = 20 m 以上

処理の流れ：
  1. 対象の市区町村（regions.json の bbox）＋余白から、範囲と必要な 1 次メッシュを決める
  2. 2 種類の河川（_10_・_20_）のポリゴンを読み、最大ズーム（既定 14、1 画素 約 8 m）の
     画像に焼き込む（ランクの小さい順に描くので、重なる所は深い方が残る）
  3. 2×2 画素の最大値をとって 1 段ずつ縮小し、小さいズームの画像を作る
  4. 256×256 に切ってタイルにする（何も無いタイルは作らない）

実行例（geopandas・rasterio などは、下の script の dependencies から uv が自動で入れる）：
  uv run ./code/build_flood.py                       … 柏市と周辺 4 市、想定最大規模
  uv run ./code/build_flood.py --scale plan          … 計画規模
  uv run ./code/build_flood.py --city 千葉県柏市 --margin 5 --maxzoom 15
"""
import argparse
import json
import math
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_origin

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/洪水浸水想定区域データ/洪水浸水想定区域（1次メッシュ単位）"
STATIC = ROOT / "data/static"

# 規模 → 元データの種類（ZIP の中のフォルダー番号）と属性名
SCALES = {
    "max": {"type": "20", "attr": "A31b_201", "label": "想定最大規模"},
    "plan": {"type": "10", "attr": "A31b_101", "label": "計画規模"},
}
RIVER_CLASSES = {"10": "洪水予報河川・水位周知河川", "20": "その他の河川"}

# 浸水深ランクの色（国土交通省「水害ハザードマップ作成の手引き」の標準の色）
LEGEND = [
    {"rank": 1, "label": "0.5 m 未満", "color": "#F7F5A9"},
    {"rank": 2, "label": "0.5〜3 m", "color": "#FFD8C0"},
    {"rank": 3, "label": "3〜5 m", "color": "#FFB7B7"},
    {"rank": 4, "label": "5〜10 m", "color": "#FF9191"},
    {"rank": 5, "label": "10〜20 m", "color": "#F285C9"},
    {"rank": 6, "label": "20 m 以上", "color": "#DC7ADC"},
]
DEFAULT_CITIES = ["千葉県柏市", "千葉県流山市", "千葉県我孫子市", "千葉県松戸市", "千葉県野田市"]

TILE = 256
EARTH = 6378137.0
WORLD = 2 * math.pi * EARTH          # Web メルカトルの世界の幅（m）
ORIGIN = WORLD / 2                    # 左上の座標 = (-ORIGIN, +ORIGIN)


def lonlat_to_tile(lon, lat, z):
    """経度・緯度 → その点を含むタイル番号 (x, y)"""
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    r = math.radians(lat)
    y = int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * n)
    return x, y


def tile_to_lonlat(x, y, z):
    """タイルの左上の角の経度・緯度"""
    n = 2 ** z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def mesh_codes(bbox):
    """範囲にかかる 1 次メッシュのコード（緯度×1.5 の整数 2 桁 ＋ 経度−100 の整数 2 桁。例：5339）"""
    x0, y0, x1, y1 = bbox
    return [f"{p}{q}" for p in range(int(y0 * 1.5), int(y1 * 1.5) + 1)
            for q in range(int(x0) - 100, int(x1) - 100 + 1)]


def find_zip(cls, mesh):
    """A31b-<年度>_<河川>_<メッシュ>_GEOJSON.zip のうち、いちばん新しい年度のもの"""
    files = sorted(RAW.glob(f"A31b-*_{cls}_{mesh}_GEOJSON.zip"))
    return files[-1] if files else None


def read_polygons(bbox, scale):
    """範囲にかかるポリゴンを、2 種類の河川・必要なメッシュすべてから読む"""
    want = f"A31b-{SCALES[scale]['type']}-"
    frames = []
    for mesh in mesh_codes(bbox):
        for cls, cls_name in RIVER_CLASSES.items():
            zp = find_zip(cls, mesh)
            if zp is None:
                print(f"  メッシュ {mesh}・{cls_name}：ファイルなし（スキップ）")
                continue
            inner = [n for n in zipfile.ZipFile(zp).namelist() if n.split("/")[-1].startswith(want)]
            if not inner:
                print(f"  メッシュ {mesh}・{cls_name}：{SCALES[scale]['label']}のデータなし")
                continue
            t = time.time()
            g = gpd.read_file(f"/vsizip/{zp.as_posix()}/{inner[0]}", bbox=tuple(bbox), engine="pyogrio")
            print(f"  メッシュ {mesh}・{cls_name}：{len(g):,} 件（{time.time() - t:.0f} 秒）")
            if len(g):
                frames.append(g[[SCALES[scale]["attr"], "geometry"]].rename(columns={SCALES[scale]["attr"]: "rank"}))
    if not frames:
        sys.exit("範囲にデータがありません。data/raw の ZIP と範囲を確かめてください")
    g = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    g["rank"] = g["rank"].astype(int)
    return g


def burn(g, z, tx0, ty0, tx1, ty1):
    """ポリゴンを、ズーム z・タイル範囲 [tx0..tx1]×[ty0..ty1] の 1 枚の画像（ランクの配列）に焼き込む"""
    res = WORLD / (TILE * 2 ** z)                       # 1 画素の大きさ（m）
    w, h = (tx1 - tx0 + 1) * TILE, (ty1 - ty0 + 1) * TILE
    transform = from_origin(-ORIGIN + tx0 * TILE * res, ORIGIN - ty0 * TILE * res, res, res)
    merc = g.to_crs(3857).sort_values("rank")          # 小さいランクから描く → 深い方が上書きで残る
    print(f"  画像 {w:,}×{h:,} 画素（1 画素 {res:.1f} m）に焼き込み中…")
    return rasterize(zip(merc.geometry, merc["rank"]), out_shape=(h, w), transform=transform,
                     fill=0, dtype="uint8")


def shrink(a):
    """2×2 画素の最大値で 1/2 に縮小する（浸水は深い方を残す）"""
    h, w = a.shape
    return a.reshape(h // 2, 2, w // 2, 2).max(axis=(1, 3))


def palette_image(block):
    """ランクの配列 → 色付き PNG（0 は透明）"""
    img = Image.fromarray(block, mode="P")
    pal = [0, 0, 0]
    for item in LEGEND:
        c = item["color"].lstrip("#")
        pal += [int(c[i:i + 2], 16) for i in (0, 2, 4)]
    img.putpalette(pal + [0, 0, 0] * (256 - len(pal) // 3))
    return img


def main():
    ap = argparse.ArgumentParser(description="洪水浸水想定区域のタイルを作る")
    ap.add_argument("--scale", choices=SCALES, default="max", help="max＝想定最大規模（既定）、plan＝計画規模")
    ap.add_argument("--city", action="append", help="対象の市区町村（例：千葉県柏市）。何度でも指定可。既定は柏市と周辺 4 市")
    ap.add_argument("--margin", type=float, default=3, help="市区町村の範囲の周りの余白（km、既定 3）")
    ap.add_argument("--minzoom", type=int, default=9)
    ap.add_argument("--maxzoom", type=int, default=14, help="最大ズーム（既定 14 ≒ 1 画素 8 m。15 で約 4 m、データ量は約 3 倍）")
    a = ap.parse_args()

    regions = json.loads((STATIC / "regions.json").read_text(encoding="utf-8"))
    names = a.city or DEFAULT_CITIES
    cities = [c for c in regions["cities"] if c["fullName"] in names]
    if len(cities) != len(names):
        found = {c["fullName"] for c in cities}
        sys.exit(f"regions.json に見つからない市区町村：{[n for n in names if n not in found]}")
    dlat = a.margin / 111.0
    dlon = a.margin / (111.0 * math.cos(math.radians(36)))
    bbox = [min(c["bbox"][0] for c in cities) - dlon, min(c["bbox"][1] for c in cities) - dlat,
            max(c["bbox"][2] for c in cities) + dlon, max(c["bbox"][3] for c in cities) + dlat]
    print(f"{SCALES[a.scale]['label']}　対象：{'、'.join(c['name'] for c in cities)}＋{a.margin:g} km")
    print(f"範囲 {[round(v, 4) for v in bbox]}　1 次メッシュ {mesh_codes(bbox)}")

    g = read_polygons(bbox, a.scale)

    # 最大ズームのタイル範囲を、最小ズームのタイルの境目にそろえる（縮小で 2 で割り切れるように）
    k = 2 ** (a.maxzoom - a.minzoom)
    tx0, ty0 = lonlat_to_tile(bbox[0], bbox[3], a.minzoom)
    tx1, ty1 = lonlat_to_tile(bbox[2], bbox[1], a.minzoom)
    raster = burn(g, a.maxzoom, tx0 * k, ty0 * k, (tx1 + 1) * k - 1, (ty1 + 1) * k - 1)

    out = STATIC / "flood" / a.scale
    total_files = total_bytes = 0
    tiles = {}          # {ズーム: ["x/y", ...]}（アプリは、ここに無いタイルを読みにいかない）
    for z in range(a.maxzoom, a.minzoom - 1, -1):
        s = 2 ** (z - a.minzoom)
        x0, y0 = tx0 * s, ty0 * s
        nx, ny = raster.shape[1] // TILE, raster.shape[0] // TILE
        n = size = 0
        for j in range(ny):
            for i in range(nx):
                block = raster[j * TILE:(j + 1) * TILE, i * TILE:(i + 1) * TILE]
                path = out / str(z) / str(x0 + i) / f"{y0 + j}.png"
                if not block.any():
                    path.unlink(missing_ok=True)      # 前回の古いタイルが残らないように
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                palette_image(block).save(path, optimize=True, transparency=0)
                n += 1
                size += path.stat().st_size
                tiles.setdefault(str(z), []).append(f"{x0 + i}/{y0 + j}")
        print(f"  z{z}: {n:,} 枚　{size / 1024 / 1024:.2f} MB")
        total_files += n
        total_bytes += size
        if z > a.minzoom:
            raster = shrink(raster)

    west, north = tile_to_lonlat(tx0, ty0, a.minzoom)
    east, south = tile_to_lonlat(tx1 + 1, ty1 + 1, a.minzoom)
    meta = {
        "name": f"洪水浸水想定区域（{SCALES[a.scale]['label']}）",
        "scale": a.scale,
        "generated": date.today().isoformat(),
        "cities": [c["fullName"] for c in cities],
        "bounds": [round(west, 5), round(south, 5), round(east, 5), round(north, 5)],
        "dataBounds": [round(v, 5) for v in bbox],
        "minzoom": a.minzoom,
        "maxzoom": a.maxzoom,
        "legend": LEGEND,
        "source": "国土数値情報「洪水浸水想定区域（1次メッシュ単位）」（国土交通省）を加工して作成",
        "sourceUrl": "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31b-2025.html",
        "note": "洪水予報河川・水位周知河川とその他の河川を重ね、深い方を表示。内水氾濫・高潮などは含まない",
        "tiles": {z: sorted(v) for z, v in sorted(tiles.items(), key=lambda kv: int(kv[0]))},
    }
    # タイルの一覧（長い）は 1 行にまとめ、ほかの項目は読みやすく改行して書く
    head = json.dumps({k: v for k, v in meta.items() if k != "tiles"}, ensure_ascii=False, indent=1)
    text = head[:-2] + ',\n "tiles": ' + json.dumps(meta["tiles"], separators=(",", ":")) + "\n}\n"
    (out / "meta.json").write_text(text, encoding="utf-8", newline="\n")
    print(f"✅ {out.relative_to(ROOT).as_posix()}：{total_files:,} 枚　{total_bytes / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()

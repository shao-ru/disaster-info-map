# data/raw（元データ）

ダウンロードした元のデータを、そのまま置くフォルダーです。
ファイルが大きいため **Git には入れません**（この README.md だけ入れます）。
必要な人は、下の出典からダウンロードして、同じ場所に置いてください。

| フォルダー | データ | 出典 | 使うスクリプト |
|---|---|---|---|
| `避難所/` | 指定緊急避難場所（mergeFromCity_2）・指定避難所（mergeFromCity_1）、全国 | [国土地理院](https://www.gsi.go.jp/bousaichiri/hinanbasho.html) | `code/build_shelters.py --init`（最初の 1 回だけ。以後は data/static/shelters/*_refine.csv を直す） |
| `admin_map/` | 2020 年国勢調査 小地域（町丁・字等）境界、Shapefile（世界測地系・緯度経度）、都道府県ごと `A002005212020DDSWC{01〜47}.zip` | [e-Stat 統計GIS「境界データ」](https://www.e-stat.go.jp/gis) | `code/build_boundaries.py` |
| `洪水浸水想定区域データ/洪水浸水想定区域（1次メッシュ単位）/` | 洪水浸水想定区域 A31b（2025 年度、1 次メッシュ 5339・5340・5439・5440、GeoJSON） | [国土数値情報](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31b-2025.html) | `code/build_flood.py` |
| `洪水浸水想定区域データ/洪水浸水想定区域（河川単位）/` | 洪水浸水想定区域 A31a（2025 年度、埼玉県） | [国土数値情報](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31a-2025.html) | （これから） |
| `気象データ/` | 船橋の時別値（2024〜2026 年） | [気象庁 過去の気象データ・ダウンロード](https://www.data.jma.go.jp/risk/obsdl/) | （これから） |
| `amedas/` | `code/amedas_rain.py history` で取得した降水量 | [気象庁 過去の気象データ検索](https://www.data.jma.go.jp/stats/etrn/) | `code/amedas_rain.py` |

ファイルを追加・削除したら、次を実行して下の一覧を更新してください。

```
uv run ./code/list_raw_files.py
```

<!-- FILE LIST -->

## ファイル一覧（自動生成）

### admin_map/  （48 ファイル、308.3 MB）

```
A002005212020DDSWC01.zip  (15.4 MB)
A002005212020DDSWC02.zip  (7.1 MB)
A002005212020DDSWC03.zip  (7.5 MB)
A002005212020DDSWC04.zip  (8.2 MB)
A002005212020DDSWC05.zip  (6.2 MB)
A002005212020DDSWC06.zip  (6.9 MB)
A002005212020DDSWC07.zip  (9.9 MB)
A002005212020DDSWC08.zip  (7.1 MB)
A002005212020DDSWC09.zip  (3.6 MB)
A002005212020DDSWC10.zip  (4.2 MB)
A002005212020DDSWC11.zip  (5.5 MB)
A002005212020DDSWC12.zip  (9.7 MB)
A002005212020DDSWC13.zip  (5.4 MB)
A002005212020DDSWC14.zip  (4.8 MB)
A002005212020DDSWC15.zip  (9.8 MB)
…ほか 33 ファイル
```

### amedas/  （1 ファイル、32.0 KB）

```
history_hourly_1236_船橋_2025-07-01_2025-07-31.csv  (32.0 KB)
```

### 気象データ/  （9 ファイル、7.2 MB）

```
data.csv  (1.1 MB)
merge_header.py  (505 B)
origin.zip  (278.7 KB)
船橋-2024.csv  (1009.0 KB)
船橋-2025.csv  (1.0 MB)
船橋-2026.csv  (904.2 KB)
船橋_2024_header_merged.csv  (1009.1 KB)
船橋_2025_header_merged.csv  (1.0 MB)
船橋_2026_header_merged.csv  (904.3 KB)
```

### 洪水浸水想定区域データ/  （162 ファイル、1.2 GB）

```
info.md  (3.0 KB)
Screenshot 2026-11-20 215317.png  (74.4 KB)
Screenshot 2026-11-20 221115.png  (81.0 KB)
国土数値情報（洪水浸水想定区域）（河川単位）製品仕様書  -v4_2.pdf  (510.7 KB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_10_5339_GEOJSON.zip  (109.9 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_10_5340_GEOJSON.zip  (103.9 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_10_5439_GEOJSON.zip  (183.8 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_10_5440_GEOJSON.zip  (39.2 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_20_5339_GEOJSON.zip  (33.1 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_20_5340_GEOJSON.zip  (13.9 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_20_5439_GEOJSON.zip  (53.0 MB)
洪水浸水想定区域（1次メッシュ単位）/A31b-25_20_5440_GEOJSON.zip  (12.3 MB)
洪水浸水想定区域（河川単位）/A31a-25_11_10_SHP/10_計画規模/A31a-10-25_11_8303030339_10.dbf  (31.5 MB)
洪水浸水想定区域（河川単位）/A31a-25_11_10_SHP/10_計画規模/A31a-10-25_11_8303030339_10.prj  (145 B)
洪水浸水想定区域（河川単位）/A31a-25_11_10_SHP/10_計画規模/A31a-10-25_11_8303030339_10.shp  (101.2 MB)
…ほか 147 ファイル
```

### 避難所/  （11 ファイル、336.5 MB）

```
mergeFromCity_1/mergeFromCity_1.csv  (11.2 MB)
mergeFromCity_1/mergeFromCity_1.geojson  (49.7 MB)
mergeFromCity_1/mergeFromCity_1.gpkg  (16.9 MB)
mergeFromCity_1/ご利用上の注意.txt  (1.5 KB)
mergeFromCity_1.zip  (60.8 MB)
mergeFromCity_2/mergeFromCity_2.csv  (16.2 MB)
mergeFromCity_2/mergeFromCity_2.geojson  (82.7 MB)
mergeFromCity_2/ご利用上の注意.txt  (1.5 KB)
mergeFromCity_2.zip  (98.9 MB)
水害統計調査.docx  (13.8 KB)
避難所等データダウンロードサイト.docx  (13.7 KB)
```

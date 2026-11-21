# web/ ― 避難所マップ（試作版）

都道府県・市区町村（＋周辺 ○ km）、または現在地から半径 ○ km の範囲を指定して、避難所を地図と一覧に表示する試作版です（全国）。
この段階ではまだ**オンライン専用**です（オフライン対応は次の段階）。

## 動かし方（自分の PC で）

プロジェクトのフォルダー（`disaster-info-map`）で次を実行し、ブラウザーで http://localhost:8000/web/ を開きます。
（データは `data/static/` にあるため、プロジェクトのフォルダー全体を公開します）

```
uv run ./code/serve.py
```

- `index.html` をダブルクリックで直接開くと動きません。必ず上のコマンドで開いてください。
- 課題のチェックは http://localhost:8000/web/test.html

## 全体の流れ

```
① 画面で選ぶ ………… 県・市区町村＋周辺 ○ km、または 現在地＋半径 ○ km
② 地域を決める ……… 課題 1  getRegion()        js/student/region.js
③ 範囲を作る ………… 市区町村の範囲を広げる（バッファー）／現在地の円   js/geo.js
④ 県を調べる ………… 課題 2  findPrefectures()  js/student/search.js
⑤ 避難所を選ぶ ……… 課題 3  filterInArea()     js/student/search.js
⑥ 地図と一覧に表示 … main.js の showResult()
⑦ 条件で色分け ……… 課題 4  matchesConditions()  js/student/conditions.js
```

②④⑤⑦ は今「仮の実装」です。課題を完成させると、選んだ範囲・条件の避難所が正しく表示されるようになります。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | 画面の骨組み |
| `test.html` | 課題の自動チェック |
| `css/style.css` | 見た目 |
| `js/config.js` | 初期位置・色・表示名などの設定 |
| `js/student/region.js` | **課題 1** |
| `js/student/search.js` | **課題 2・3** |
| `js/student/conditions.js` | **課題 4-1・4-2**（条件に合う避難所を緑にする） |
| `js/data.js` | データ読み込みの共通関数（課題で使ってよい） |
| `js/geo.js` | 範囲を作る・調べる共通関数（Turf.js を使用。課題で使ってよい） |
| `js/shelters.js` | 避難所の値（attrs）の整理・距離計算 |
| `js/conditions-ui.js` | 画面の「条件」（災害・受入れなど） |
| `js/photos.js` | 写真の表示と「写真を追加」（手元の serve.py のときだけ） |
| `js/flood.js` | 洪水の浸水深の図層（表示の切り替え・濃さ・凡例） |
| `js/weather.js` | 気象観測所の図層（リアルタイムの雨量・気温）と、直近 24 時間・過去の記録のグラフ（Chart.js） |
| `js/list.js` / `js/popup.js` / `js/contributors.js` | 一覧 / 吹き出し / 参加者 |
| `js/main.js` | 地図の表示と全体の流れ |
| `js/test.js` | 課題チェックの中身（書き換えない） |
| `../data/static/regions.json` | 都道府県・市区町村の一覧（自動生成） |
| `../data/static/shelters/*_refine.csv` | 避難所の元データ（国土地理院のデータをみんなで直したもの） |
| `../data/static/shelters/<県コード>.geojson` | 上の CSV と `attrs/*.csv` から `code/build_shelters.py` で自動生成 |
| `../data/static/photos/` | 避難所の写真（吹き出しの「写真を追加」で保存） |
| `../data/static/admin_boundaries/*.geojson` | 市区町村の範囲（e-Stat の境界データから自動生成） |
| `../data/static/flood/max/` | 洪水の浸水深の地図タイル（`code/build_flood.py` で生成） |
| `../data/static/weather/` | 気象観測所の一覧と過去の記録（`code/weather.py` で生成） |

## データの作り直し

避難所のデータ（`data/static/shelters/*_refine.csv`）を直したら：

```
uv run ./code/build_shelters.py
```

詳しくは `data/README.md` を見てください。

## 出典

- 避難所：国土地理院「指定緊急避難場所・指定避難所データ」
- 洪水の浸水深：国土数値情報「洪水浸水想定区域（1次メッシュ単位）」（国土交通省）
- 気象観測所・雨量など：気象庁
- 背景地図：地理院タイル（淡色地図）
- ライブラリ：MapLibre GL JS（地図）、Turf.js（範囲の計算）、Chart.js（グラフ）

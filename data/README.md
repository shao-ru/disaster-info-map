# data/

| フォルダー | 中身 | 変わるか | Git |
|---|---|---|---|
| `raw/` | ダウンロードした元のデータ（そのまま保存） | ほとんど変わらない | 入れない（大きいため） |
| `static/` | Python で処理した、アプリが読み込むデータ | 元データを更新したときだけ作り直す | 入れる（GitHub Pages で公開） |
| `cache/` | その都度ネットから取ってくるデータ（雨量の最新値など） | よく変わる | 入れない |
| `output/` | 集計・分析の結果 | 課題ごとに変わる | 必要に応じて |

## raw/ の出典

| フォルダー | データ | 出典 |
|---|---|---|
| `raw/避難所/` | 指定緊急避難場所・指定避難所データ（全国） | 国土地理院 |
| `raw/洪水浸水想定区域データ（河川単位）/` | 洪水浸水想定区域（A31a、2025 年度、埼玉県） | 国土数値情報（国土交通省） |
| `raw/気象データ/` | 船橋の時別値（2024〜2026 年） | 気象庁「過去の気象データ・ダウンロード」 |
| `raw/admin_map/` | 小地域（町丁・字等）境界（2020 年国勢調査、全国） | e-Stat（総務省統計局） |
| `raw/amedas/` | `code/amedas_rain.py history` で取得した降水量 | 気象庁「過去の気象データ検索」 |

## 避難所データの流れ

```
raw/避難所/mergeFromCity_1.csv, mergeFromCity_2.csv    元データ（国土地理院）。書き換えない
        │  最初に 1 回だけコピー（教員：build_shelters.py --init）
        ▼
static/shelters/mergeFromCity_1_refine.csv              指定避難所　　　　 ← みんなで直す
static/shelters/mergeFromCity_2_refine.csv              指定緊急避難場所　 ← みんなで直す
static/shelters/attrs/<市区町村コード>.csv                利用条件・受入れ・災害ごとの可否 ← みんなで調べて書く
        │  uv run ./code/build_shelters.py（自動の推定：code/shelter_attrs.py）
        ▼
static/shelters/<県コード>.geojson                       アプリが読み込む
static/regions.json の施設数
```

直し方：

1. アプリで施設をクリックし、吹き出しの一番下の「共通ID」を確かめる
2. `_refine.csv` をその共通ID で検索して直す（列は国土地理院のデータと同じ）。削除は行を消す、追加は行を足す
3. `uv run ./code/build_shelters.py` を実行（エラーがあれば行番号が出て、何も書き換えない）
4. アプリで確かめて、Pull Request を出す（`_refine.csv` と `.geojson` の両方）

- 編集は **VS Code（拡張機能 Rainbow CSV）** で。**Excel は使わない**（保存するとファイル全体の書き方が変わり、Git で何を直したかわからなくなるため）
- 何をなぜ直したかは、Pull Request の説明に書く（根拠の URL など）
- 利用条件などの調査（`attrs/`）の書き方は [doc/避難所の調査と写真.md](../doc/避難所の調査と写真.md)
- Pull Request を出すと、GitHub Actions が `build_shelters.py` を実行し、CSV と GeoJSON が合っているかを自動でチェックする

## 写真

```
static/photos/<施設ID>_<GitHubユーザー名>_<番号>.jpg / .json    写真と説明（アプリの「写真を追加」で保存）
static/photos/index.json                                      写真の一覧（自動。Git に入れない）
```

- `index.json` は、手元では `serve.py` が読まれるたびに作り、公開サイトでは GitHub Actions（`.github/workflows/pages.yml`）が公開のときに作る
- チェック：`uv run ./code/build_photos.py`
- 公開の設定（初回だけ・管理者）：GitHub の Settings → Pages → Source を「GitHub Actions」にする

## 市区町村の境界（最初に 1 回だけ・教員）

```
uv run --with geopandas --with pyogrio python ./code/build_boundaries.py
```

`admin_boundaries/<県コード>.geojson`（e-Stat の境界）を作り、`regions.json` の市区町村の中心・範囲を更新します。

raw のファイルを増やしたら `uv run ./code/list_raw_files.py` で `raw/README.md` の一覧を更新します。

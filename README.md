# 避難所マップ（disaster-info-map）

都道府県・市区町村を選ぶか現在地から、周辺の避難所を地図に表示する Web アプリです（試作版）。
大学の授業で、学生と一緒に作っています。今後、洪水ハザードマップや雨量の情報を加え、オフラインでも使えるアプリ（PWA）にする予定です。

- アプリ：https://＜ユーザー名＞.github.io/disaster-info-map/
- 参加する人へ：[参加ガイド](doc/参加ガイド.md) ／ [しくみの説明](doc/しくみの説明.md)

## 自分の PC で動かす

[uv](https://docs.astral.sh/uv/) をインストールしてから、このフォルダーで：

```
uv run ./code/serve.py
```

ブラウザーで http://localhost:8000/web/ を開きます。

## フォルダー

| フォルダー | 中身 |
|---|---|
| `web/` | アプリ（HTML・JavaScript） |
| `data/static/` | アプリが読み込むデータ（処理済み） |
| `code/` | データを作る Python スクリプト |
| `doc/` | 説明書 |

## 出典

- 避難所：[国土地理院「指定緊急避難場所・指定避難所データ」](https://www.gsi.go.jp/bousaichiri/hinanbasho.html)を加工して作成
- 市区町村の境界：[政府統計の総合窓口（e-Stat）「2020 年国勢調査 小地域（町丁・字等）境界データ」](https://www.e-stat.go.jp/gis)を加工して作成
- 背景地図：[地理院タイル](https://maps.gsi.go.jp/development/ichiran.html)

このアプリの情報は参考用です。実際の避難は、お住まいの市区町村の情報と現地の状況に従ってください。

## ライセンス

研究・教育など、**営利を目的としない利用** に限り、自由に使えます。営利目的での利用はできません。

| 対象 | ライセンス |
|---|---|
| プログラム（`web/`、`code/` など） | [PolyForm Noncommercial License 1.0.0](LICENSE) |
| 説明書（`doc/`、各 README） | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.ja)（表示 − 非営利） |
| データ（`data/static/`） | 元データ（国土地理院・e-Stat）の利用規約に従います。上の「出典」を表示してください |

このリポジトリに Pull Request を出した人は、その内容を上と同じライセンスで公開することに同意したものとします。


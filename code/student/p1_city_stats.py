"""
課題 P1  市区町村ごとの避難所の集計                          難易度 ★★☆☆☆

都道府県ごとの避難所データ（data/static/shelters/<県コード>.geojson）を読み込み、
市区町村ごとに「避難所の数」と「洪水に対応する避難所の数」を数えて CSV に書き出します。

使い方（プロジェクトのフォルダーで）：
  uv run ./code/student/p1_city_stats.py 12        ← 12 は千葉県のコード
出力：
  data/output/city_stats_12.csv
  列：city_code, city, shelters, flood, flood_ratio

確認方法：
  uv run ./code/student/check_p1.py
  すべて ✅ になれば完成です。

あなたが書くのは count_by_city() だけです。
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_features(pref_code):
    """都道府県の避難所（Feature のリスト）を読み込む（用意済み）"""
    path = ROOT / f"data/static/shelters/{pref_code}.geojson"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["features"]


# =====================================================================
# ここを書く
# =====================================================================
def count_by_city(features):
    """
    市区町村コードごとに、避難所の数と洪水に対応する数を数える。

    引数
      features : 避難所のリスト。1 件は次のような辞書です。
        {
          "type": "Feature",
          "geometry": {...},
          "properties": {"cityCode": "12217", "city": "柏市", "flood": True, ...}
        }

    戻り値
      次のような辞書
        {
          "12217": {"city": "柏市", "shelters": 146, "flood": 120},
          "12220": {"city": "流山市", "shelters": 83, "flood": 50},
          ...
        }

    ヒント
      for f in features: で 1 件ずつ取り出し、p = f["properties"] で中身を見る。
      その市がまだ辞書になければ {"city": ..., "shelters": 0, "flood": 0} を作り、数を足していく。
      p["flood"] は True / False です。
    """
    # ---- 仮の実装：何も数えずに空の辞書を返す（ここを書き換える） ----
    return {}


# =====================================================================
# ここから下は用意済み
# =====================================================================
def write_csv(stats, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city_code", "city", "shelters", "flood", "flood_ratio"])
        for code in sorted(stats):
            s = stats[code]
            ratio = s["flood"] / s["shelters"] if s["shelters"] else 0
            w.writerow([code, s["city"], s["shelters"], s["flood"], f"{ratio:.3f}"])


def main():
    pref_code = sys.argv[1] if len(sys.argv) > 1 else "12"
    stats = count_by_city(load_features(pref_code))
    out = ROOT / f"data/output/city_stats_{pref_code}.csv"
    write_csv(stats, out)
    print(f"{len(stats)} 市区町村を書き出しました → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

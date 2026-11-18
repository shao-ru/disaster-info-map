"""
make_attrs_template.py  -  調査用のファイル（attrs/<市区町村コード>.csv）のひな形を作る

その市区町村のすべての避難所を 1 行ずつ並べ、id・name・住所 を入れた CSV を作ります。
ほかの列は空（＝不明）なので、調べた項目だけ書き込みます。

すでにファイルがある場合は、まだ書かれていない施設の行だけを、最後に追加します（書いた内容は消えません）。

使い方（プロジェクトのフォルダーで）：
  uv run ./code/make_attrs_template.py 12217          … 柏市
  uv run ./code/make_attrs_template.py 12220 12222    … 流山市と我孫子市
市区町村コードは data/static/regions.json で調べられます（例：柏市 = 12217）。
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shelter_attrs import ATTR_COLUMNS, COLUMN_NAMES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SHELTERS = ROOT / "data/static/shelters"
ATTRS = SHELTERS / "attrs"


def main():
    ap = argparse.ArgumentParser(description="調査用ファイル attrs/<市区町村コード>.csv のひな形を作る")
    ap.add_argument("city", nargs="+", help="市区町村コード 5 桁（例：12217）")
    args = ap.parse_args()
    ATTRS.mkdir(parents=True, exist_ok=True)
    for code in args.city:
        if len(code) != 5 or not code.isdigit():
            raise SystemExit(f"市区町村コードは数字 5 桁です（今は「{code}」）")
        feats = json.loads((SHELTERS / f"{code[:2]}.geojson").read_text(encoding="utf-8"))["features"]
        items = sorted((f["properties"] for f in feats if f["properties"]["cityCode"] == code), key=lambda p: p["id"])
        if not items:
            raise SystemExit(f"{code} の避難所が見つかりません")
        path = ATTRS / f"{code}.csv"
        have = set()
        if path.exists():
            with open(path, encoding="utf-8-sig", newline="") as f:
                have = {r["id"].strip() for r in csv.DictReader(f)}
        new = [p for p in items if p["id"] not in have and not (set(p["ids"]) & have)]
        mode = "a" if path.exists() else "w"
        with open(path, mode, encoding="utf-8-sig" if mode == "w" else "utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=ATTR_COLUMNS, lineterminator="\n")
            if mode == "w":
                w.writeheader()
            for p in new:
                w.writerow({"id": p["id"], "name": p["name"], COLUMN_NAMES["address"]: p["address"]})
        print(f"attrs/{code}.csv：{items[0]['pref']}{items[0]['city']}　{len(new)} 行を追加（全部で {len(items)} 施設）")


if __name__ == "__main__":
    main()

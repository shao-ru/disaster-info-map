#!/usr/bin/env python3
"""
weather.py - 地域の気象観測所（アメダス）と、過去の気象データ（日ごと）を集める（Python 標準ライブラリのみ）

アプリ（web/）は、ここで作ったファイルを読み込んで「気象観測所」の図層と「過去の記録」を表示します。
リアルタイムの値（10 分ごと）は、アプリが気象庁のホームページから直接読み込みます（このスクリプトは不要）。

サブコマンド：
  stations  対象地域の観測所の一覧を作る
            → data/static/weather/stations.geojson
  history   一覧の観測所の、過去の日ごとの値（降水量・気温・日照時間・降雪・積雪・風速・湿度）を集める
            → data/static/weather/daily/<地点コード>.csv
            取得元：気象庁「過去の気象データ検索」のページ（1 地点・1 か月ごとに 1 ページ）

使用例：
  # 柏市の中心から 25 km 以内の観測所
  uv run ./code/weather.py stations --city 千葉県柏市 --radius 25

  # 2024 年 1 月〜今月までの日ごとの値（すでにある月は飛ばし、最後の月だけ取り直す）
  uv run ./code/weather.py history --start 2024-01

  # 1 地点だけ、期間を指定して取り直す
  uv run ./code/weather.py history --code 45136 --start 2025-07 --end 2025-09 --force

注意：
  - どちらの取得元も公式 API ではありません。ページや JSON の形が変わったら直す必要があります
  - リクエストの間隔（1 秒）は短くしないでください
  - 値の出典は「気象庁」です。アプリや資料に使うときは出典を書いてください
"""

import argparse
import csv
import json
import math
import re
import sys
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from amedas_rain import BOSAI, ETRN, SLEEP, etrn_stations, fetch_json, fetch_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/static/weather"

# アメダス地点表（amedastable.json）の elems：1 文字ずつ、その観測をしているか
ELEMS = ["temp", "precip", "wind", "wind2", "sun", "snow", "humidity", "pressure"]

# CSV の列：(列名, 表示名, 単位, 見出しに含まれる言葉)
COLUMNS = [
    ("precip", "降水量（合計）", "mm", ["降水量", "合計"]),
    ("precip_max1h", "降水量（最大 1 時間）", "mm", ["降水量", "1時間"]),
    ("temp_avg", "気温（平均）", "℃", ["気温", "平均"]),
    ("temp_max", "気温（最高）", "℃", ["気温", "最高"]),
    ("temp_min", "気温（最低）", "℃", ["気温", "最低"]),
    ("sun", "日照時間", "h", ["日照時間"]),
    ("snowfall", "降雪の深さ（合計）", "cm", ["雪", "降雪"]),
    ("snow_depth", "最深積雪", "cm", ["最深積雪"]),
    ("wind_avg", "平均風速", "m/s", ["平均風速"]),
    ("humidity", "湿度（平均）", "%", ["湿度", "平均"]),
]


# ---------------------------------------------------------------- 観測所の一覧
def km_between(lon1, lat1, lon2, lat2):
    r = math.radians
    a = (math.sin(r(lat2 - lat1) / 2) ** 2
         + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def cmd_stations(a):
    regions = json.loads((ROOT / "data/static/regions.json").read_text(encoding="utf-8"))
    city = next((c for c in regions["cities"] if c["fullName"] == a.city), None)
    if not city:
        sys.exit(f"regions.json に「{a.city}」が見つかりません（例：千葉県柏市）")
    lon0, lat0 = city["center"]

    table = fetch_json(f"{BOSAI}/const/amedastable.json")
    if not table:
        sys.exit("気象庁のアメダス地点表を取得できませんでした")
    near = []
    for code, s in table.items():
        lat = s["lat"][0] + s["lat"][1] / 60
        lon = s["lon"][0] + s["lon"][1] / 60
        km = km_between(lon0, lat0, lon, lat)
        if km <= a.radius:
            near.append((km, code, s, lon, lat))
    near.sort()

    # 過去データのページで使う番号（prec_no・block_no）を、地点名で対応づける
    # アメダス地点コードの先頭 2 桁 ＝ 過去データの都府県番号（prec_no）
    etrn = {}
    for pref in sorted({code[:2] for _, code, *_ in near}):
        etrn[pref] = etrn_stations(pref)
        time.sleep(SLEEP)

    features = []
    for km, code, s, lon, lat in near:
        e = etrn.get(code[:2], {}).get(s["kjName"])
        has = {k: s["elems"][i] != "0" for i, k in enumerate(ELEMS) if i < len(s["elems"])}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            "properties": {
                "code": code, "name": s["kjName"], "kana": s["knName"], "alt": s["alt"],
                "km": round(km, 1),
                "elems": [k for k in ("temp", "precip", "wind", "sun", "snow", "humidity") if has.get(k)],
                "prec_no": code[:2] if e else None,
                "block_no": e["block_no"] if e else None,
                "kind": e["kind"] if e else None,          # s＝気象台など、a＝アメダス
            },
        })
        mark = "" if e else "　※過去データのページが見つからない"
        print(f"  {code} {s['kjName']:<6} {km:5.1f} km  {''.join('○' if has.get(k) else '・' for k in ('temp', 'precip', 'wind', 'sun', 'snow'))}{mark}")

    OUT.mkdir(parents=True, exist_ok=True)
    geo = {
        "type": "FeatureCollection",
        "generated": date.today().isoformat(),
        "center": {"name": city["fullName"], "lng": lon0, "lat": lat0}, "radiusKm": a.radius,
        "source": "気象庁 アメダス地点表",
        "features": features,
    }
    path = OUT / "stations.geojson"
    path.write_text(json.dumps(geo, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"✅ {len(features)} 地点 → {path.relative_to(ROOT).as_posix()}（気温・降水・風・日照・雪 の ○ は観測あり）")


# ---------------------------------------------------------------- 過去データ（etrn のページ）
class GridParser(HTMLParser):
    """id="tablefix1" の表を、rowspan・colspan を展開した 2 次元の表（文字列のリストのリスト）にする"""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.rows = []          # [[(text, rowspan, colspan), ...], ...]
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        at = dict(attrs)
        if tag == "table" and (self.depth or at.get("id") == "tablefix1"):
            self.depth += 1
        if not self.depth:
            return
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = [[], int(at.get("rowspan") or 1), int(at.get("colspan") or 1)]

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(("".join(self.cell[0]).strip(), self.cell[1], self.cell[2]))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[0].append(data)

    def grid(self):
        out, pending = [], {}            # pending[(行, 列)] = rowspan で下に伸びる文字列
        for i, row in enumerate(self.rows):
            line, j = [], 0
            cells = iter(row)
            while True:
                if (i, j) in pending:
                    line.append(pending.pop((i, j)))
                    j += 1
                    continue
                c = next(cells, None)
                if c is None:
                    break
                text, rs, cs = c
                for k in range(cs):
                    line.append(text)
                    for d in range(1, rs):
                        pending[(i + d, j + k)] = text
                j += cs
            out.append(line)
        return out


def parse_daily(html):
    """1 か月分のページ → {日: {列名: 文字列}}"""
    p = GridParser()
    p.feed(html)
    g = p.grid()
    head = [r for r in g if r and not r[0].isdigit()]
    body = [r for r in g if r and r[0].isdigit()]
    if not head or not body:
        return {}
    ncol = max(len(r) for r in head)
    names = []
    for j in range(ncol):
        parts = []
        for r in head:
            t = r[j] if j < len(r) else ""
            t = re.sub(r"\(.*?\)|（.*?）", "", t).replace(" ", "")
            if t and t not in parts:
                parts.append(t)
        names.append("/".join(parts))
    cols = {}
    for key, _, _, words in COLUMNS:
        for j, n in enumerate(names):
            if all(w in n for w in words) and j not in cols.values():
                cols[key] = j
                break
    return {int(r[0]): {k: (r[j] if j < len(r) else "") for k, j in cols.items()} for r in body}


def clean(raw):
    """値の文字列 → 数値の文字列（使えない値は空）。
    -- は現象なし（0）、) は準正常値（使う）、] は資料不足・# は疑問値・/// と × は観測なし（空）"""
    s = raw.replace("　", " ").strip()
    if s == "--":
        return "0"
    if not s or "]" in s or "#" in s or "/" in s or "×" in s:
        return ""
    m = re.search(r"-?\d+(\.\d+)?", s)
    return m.group(0) if m else ""


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def ym(text):
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if not m:
        raise argparse.ArgumentTypeError("YYYY-MM の形で指定してください（例：2025-07）")
    return int(m.group(1)), int(m.group(2))


def cmd_history(a):
    path = OUT / "stations.geojson"
    if not path.exists():
        sys.exit("先に stations で観測所の一覧を作ってください")
    stations = [f["properties"] for f in json.loads(path.read_text(encoding="utf-8"))["features"]]
    if a.code:
        stations = [s for s in stations if s["code"] in a.code]
    stations = [s for s in stations if s["block_no"]]
    today = date.today()
    end = a.end or (today.year, today.month)
    keys = [c[0] for c in COLUMNS]
    (OUT / "daily").mkdir(parents=True, exist_ok=True)

    for s in stations:
        csv_path = OUT / "daily" / f"{s['code']}.csv"
        rows = {}
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                rows = {r["date"]: r for r in csv.DictReader(f)}
        have = {d[:7] for d in rows}
        last = max(have) if have else None
        todo = [(y, m) for y, m in months(a.start, end)
                if a.force or f"{y}-{m:02d}" not in have or f"{y}-{m:02d}" == last]
        print(f"{s['code']} {s['name']}：{len(todo)} か月分を取得")
        for y, m in todo:
            page = "daily_s1" if s["kind"] == "s" else "daily_a1"
            url = (f"{ETRN}/view/{page}.php?prec_no={s['prec_no']}&block_no={s['block_no']}"
                   f"&year={y}&month={m}&day=&view=")
            html = fetch_text(url)
            time.sleep(SLEEP)
            days = parse_daily(html) if html else {}
            if not days:
                print(f"  {y}-{m:02d}：データなし")
                continue
            for d, vals in days.items():
                key = f"{y}-{m:02d}-{d:02d}"
                if key >= today.isoformat():      # 今日と先の日（今月のページには空の行がある）は入れない
                    rows.pop(key, None)
                    continue
                rows[key] = {"date": key, **{k: clean(vals.get(k, "")) for k in keys}}
            print(f"  {y}-{m:02d}：{len(days)} 日")
        # 1 つも値がない列（その観測をしていない）は書かない
        used = [k for k in keys if any(r.get(k) for r in rows.values())]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["date"] + used)
            for k in sorted(rows):
                w.writerow([k] + [rows[k].get(c, "") for c in used])
        print(f"  → {csv_path.relative_to(ROOT).as_posix()}（{len(rows)} 日、列：{', '.join(used)}）")

    meta = {
        "generated": today.isoformat(),
        "columns": [{"key": k, "label": lab, "unit": u} for k, lab, u, _ in COLUMNS],
        "source": "気象庁「過去の気象データ検索」",
        "sourceUrl": "https://www.data.jma.go.jp/stats/etrn/",
    }
    (OUT / "daily" / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("✅ 完了")


def main():
    ap = argparse.ArgumentParser(description="地域の気象観測所と過去の気象データを集める")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stations", help="対象地域の観測所の一覧を作る")
    s.add_argument("--city", default="千葉県柏市", help="中心の市区町村（既定：千葉県柏市）")
    s.add_argument("--radius", type=float, default=25, help="中心からの距離（km、既定 25）")
    h = sub.add_parser("history", help="過去の日ごとの値を集める")
    h.add_argument("--start", type=ym, required=True, help="最初の月（例：2024-01）")
    h.add_argument("--end", type=ym, help="最後の月（既定：今月。途中の月は、次に実行したときに取り直す）")
    h.add_argument("--code", action="append", help="地点コード（何度でも指定可。既定は一覧のすべて）")
    h.add_argument("--force", action="store_true", help="すでにある月も取り直す")
    a = ap.parse_args()
    {"stations": cmd_stations, "history": cmd_history}[a.cmd](a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
amedas_rain.py  -  気象庁 AMeDAS 降水量データ取得ツール（Python 標準ライブラリのみ使用）

サブコマンド：
  stations  都道府県内の観測地点を一覧表示（地点名、過去データ用の block_no、
            リアルタイム用の AMeDAS 地点コード、緯度・経度）
  history   過去の降水量を一括ダウンロード（1 時間 / 10 分 / 日）
            取得元：気象庁「過去の気象データ検索」のページ
  realtime  リアルタイムの降水量を取得（10 分ごとに更新）
            取得元：気象庁ホームページのアメダス JSON

使用例：
  # 観測地点を調べる（千葉県、地点名に「船橋」を含むもの）
  uv run ./code/amedas_rain.py stations --pref 45 --name 船橋

  # リアルタイムデータ：最新値を取得し、直近 6 時間分もさかのぼって取得
  uv run ./code/amedas_rain.py realtime --pref 45 --station 船橋 --hours 6

  # リアルタイムデータ：10 分ごとに取得し続ける（Ctrl+C で停止）
  uv run ./code/amedas_rain.py realtime --pref 45 --station 船橋 --watch 600

  # 過去データ：2025 年 7 月の 1 時間降水量
  uv run ./code/amedas_rain.py history --pref 45 --station 船橋 --start 2025-07-01 --end 2025-07-31 --freq hourly

  # 過去データ：複数地点の日降水量（1 年分）
  uv run ./code/amedas_rain.py history --pref 43 --station 熊谷 --station さいたま --start 2025-01-01 --end 2025-12-31 --freq daily

  # 各サブコマンドのオプションを確認する
  uv run ./code/amedas_rain.py realtime -h

都府県番号（--pref）：埼玉 43、東京 44、千葉 45、神奈川 46。
  その他の都道府県は https://www.data.jma.go.jp/stats/etrn/select/prefecture00.php で
  都道府県をクリックし、URL の prec_no を確認してください。

出力：
  既定では、過去データは data/raw/amedas、リアルタイムは data/cache/amedas に保存します（プロジェクトのフォルダーで実行した場合。--out で変更可）。
  CSV は UTF-8（BOM 付き）なので、Excel でそのまま開けます。

注意：
  - どちらの取得元も公式 API ではありません。ページや JSON の構造が変わった場合は修正が必要です。
  - リクエスト間隔（既定 1 秒）は短くしないでください。大量の同時アクセスは避けてください。
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

ETRN = "https://www.data.jma.go.jp/stats/etrn"
BOSAI = "https://www.jma.go.jp/bosai/amedas"
UA = "Mozilla/5.0 (amedas_rain.py; research use)"
SLEEP = 1.0  # リクエスト間隔（秒）


# ---------------------------------------------------------------- HTTP
def fetch(url, retries=3):
    """URL を取得してバイト列を返す。404 の場合は None。一時的なエラーは再試行する。"""
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == retries - 1:
                raise
        except urllib.error.URLError:
            if i == retries - 1:
                raise
        time.sleep(2 * (i + 1))


def fetch_text(url):
    b = fetch(url)
    return None if b is None else b.decode("utf-8", "replace")


def fetch_json(url):
    b = fetch(url)
    return None if b is None else json.loads(b.decode("utf-8"))


# ---------------------------------------------------------------- 観測地点
# 都道府県ページの地図に埋め込まれた viewPoint('種別','block_no','地点名','カナ','緯度度','緯度分','経度度','経度分','標高',...)
VIEWPOINT = re.compile(r"viewPoint\('([as])','(\d+)','([^']*)','([^']*)','(\d+)','([\d.]+)','(\d+)','([\d.]+)','([-\d.]*)'")


def etrn_stations(pref):
    """過去データ用の観測地点一覧 {地点名: {...}} を返す。kind: s = 気象台等、a = アメダス。"""
    html = fetch_text(f"{ETRN}/select/prefecture.php?prec_no={pref}&block_no=&year=&month=&day=&view=")
    if not html:
        sys.exit(f"都府県番号 {pref} の観測地点ページが見つかりません。")
    out = {}
    for m in VIEWPOINT.finditer(html):
        kind, block, name, kana, la, lam, lo, lom, alt = m.groups()
        if name in out:
            continue
        out[name] = {
            "name": name, "kana": kana, "kind": kind, "block_no": block,
            "lat": round(int(la) + float(lam) / 60, 5), "lon": round(int(lo) + float(lom) / 60, 5),
            "alt": alt,
        }
    return out


_amedas_table = None


def amedas_table():
    """リアルタイム用の地点表 {AMeDAS 地点コード: {...}} を返す（初回のみ取得）。"""
    global _amedas_table
    if _amedas_table is None:
        _amedas_table = fetch_json(f"{BOSAI}/const/amedastable.json") or {}
    return _amedas_table


def amedas_code_for(pref, name):
    """地点名から AMeDAS 地点コード（5 桁）を探す。コードの先頭 2 桁は都府県番号と一致する。"""
    for code, s in amedas_table().items():
        if code.startswith(str(pref)) and s.get("kjName") == name:
            return code
    return None


def resolve_history_stations(pref, names):
    table = etrn_stations(pref)
    out = []
    for n in names:
        hit = table.get(n) or next((s for s in table.values() if s["block_no"] == n), None)
        if not hit:
            sys.exit(f"都府県番号 {pref} に観測地点「{n}」が見つかりません。"
                     f"先に次のコマンドで地点名を確認してください：amedas_rain.py stations --pref {pref}")
        out.append(hit)
    return out


def cmd_stations(a):
    table = etrn_stations(a.pref)
    rows = [s for s in table.values() if not a.name or a.name in s["name"]]
    print(f"{'地点名':<8}{'種別':<8}{'block_no':<10}{'地点コード':<12}{'緯度':>10}{'経度':>11}")
    for s in rows:
        code = amedas_code_for(a.pref, s["name"]) or "-"
        kind = "気象台等" if s["kind"] == "s" else "アメダス"
        print(f"{s['name']:<8}{kind:<8}{s['block_no']:<10}{code:<12}{s['lat']:>10}{s['lon']:>11}")
    print(f"\n{len(rows)} 地点。history では地点名または block_no、realtime では地点名または地点コードを指定します。")


# ---------------------------------------------------------------- 過去データ（etrn の HTML）
class TableParser(HTMLParser):
    """id="tablefix1" の表を読み取り、[[(文字列, colspan, 見出しかどうか), ...], ...] を返す。"""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        at = dict(attrs)
        if tag == "table":
            if self.depth or at.get("id") == "tablefix1":
                self.depth += 1
        if not self.depth:
            return
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = [tag == "th", int(at.get("colspan", 1) or 1), []]

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(("".join(self.cell[2]).strip(), self.cell[1], self.cell[0]))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[2].append(data)


def parse_precip(html):
    """表から「降水量」の列を探し、[(行ラベル, 降水量の元の文字列), ...] を返す。"""
    p = TableParser()
    p.feed(html)
    if not p.rows:
        return []
    col = None
    for r in p.rows:
        if r and all(c[2] for c in r):  # 見出し行
            idx = 0
            for text, span, _ in r:
                if "降水量" in text:
                    col = idx
                    break
                idx += span
            if col is not None:
                break
    if col is None:
        raise RuntimeError("表に「降水量」の列が見つかりません。ページの構造が変わった可能性があります。")
    out = []
    for r in p.rows:
        if r and not r[0][2] and len(r) > col:
            out.append((r[0][0], r[col][0]))
    return out


# 気象庁の値に付く記号 → 品質の区分
FLAGS = {")": "quasi", "]": "insufficient", "#": "doubtful", "*": "latest"}


def clean(raw):
    """値の文字列を (数値, 品質) に変換する。'--' は「現象なし」なので 0 とする。"""
    s = raw.replace("　", " ").strip()
    if s in ("", "///", "×", "#"):
        return "", "missing"
    if s == "--":
        return 0.0, "no_phenomenon"
    q = "ok"
    for mark, name in FLAGS.items():
        if mark in s:
            q = name
    m = re.search(r"-?\d+(\.\d+)?", s)
    return (float(m.group(0)), q) if m else ("", "missing")


def page_url(freq, kind, pref, block, d):
    base = {"hourly": "hourly", "10min": "10min", "daily": "daily"}[freq]
    page = f"{base}_{kind}1.php"
    day = d.day if freq != "daily" else ""
    return f"{ETRN}/view/{page}?prec_no={pref}&block_no={block}&year={d.year}&month={d.month}&day={day}&view="


def to_time(freq, d, label):
    """表の行ラベルを観測時刻（その時間帯の終わりの時刻）に変換する。気象庁の 24 時は翌日 0 時。"""
    if freq == "hourly":
        return datetime(d.year, d.month, d.day) + timedelta(hours=int(label))
    if freq == "10min":
        h, m = label.split(":")
        return datetime(d.year, d.month, d.day) + timedelta(hours=int(h), minutes=int(m))
    return date(d.year, d.month, int(label))


def periods(freq, start, end):
    """ダウンロードするページの単位：日値は 1 か月ごと、それ以外は 1 日ごと。"""
    if freq == "daily":
        d = date(start.year, start.month, 1)
        while d <= end:
            yield d
            d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    else:
        d = start
        while d <= end:
            yield d
            d += timedelta(days=1)


def cmd_history(a):
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    if end < start:
        sys.exit("--end が --start より前の日付です。")
    os.makedirs(a.out, exist_ok=True)
    unit = {"hourly": "1 時間", "10min": "10 分", "daily": "日"}[a.freq]
    for st in resolve_history_stations(a.pref, a.station):
        path = os.path.join(a.out, f"history_{a.freq}_{st['block_no']}_{st['name']}_{a.start}_{a.end}.csv")
        n_req = len(list(periods(a.freq, start, end)))
        print(f"{st['name']}（block_no {st['block_no']}）：{unit}値、リクエスト {n_req} 回 → {path}")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["station", "block_no", "time", "precip_mm", "quality", "raw"])
            for i, d in enumerate(periods(a.freq, start, end), 1):
                html = fetch_text(page_url(a.freq, st["kind"], a.pref, st["block_no"], d))
                rows = parse_precip(html) if html else []
                for label, raw in rows:
                    try:
                        t = to_time(a.freq, d, label)
                    except ValueError:
                        continue
                    if a.freq == "daily" and not (start <= t <= end):
                        continue
                    v, q = clean(raw)
                    w.writerow([st["name"], st["block_no"], t.isoformat(sep=" ") if isinstance(t, datetime) else t.isoformat(), v, q, raw])
                print(f"\r  {i}/{n_req} {d.isoformat()}", end="", flush=True)
                time.sleep(SLEEP)
        print("\n  完了")


# ---------------------------------------------------------------- リアルタイム（アメダス JSON）
FIELDS = ["precipitation10m", "precipitation1h", "precipitation3h", "precipitation24h", "temp"]


def resolve_codes(a):
    codes = list(a.code or [])
    for n in a.station or []:
        if not a.pref:
            sys.exit("--station を使う場合は --pref も指定してください。")
        c = amedas_code_for(a.pref, n)
        if not c:
            sys.exit(f"観測地点「{n}」の地点コードが見つかりません。"
                     f"先に次のコマンドで確認してください：amedas_rain.py stations --pref {a.pref}")
        codes.append(c)
    if not codes:
        sys.exit("--code、または --pref と --station で観測地点を指定してください。")
    return codes


def rt_row(obs_time, code, rec):
    """JSON の 1 レコードを CSV の 1 行にする。品質フラグが 0（正常）以外の値は空欄にする。"""
    name = amedas_table().get(code, {}).get("kjName", "")
    row = [obs_time, code, name]
    for k in FIELDS:
        v = rec.get(k)
        row.append(v[0] if v and v[0] is not None and v[1] == 0 else "")
    return row


def load_seen(path):
    """既存 CSV に書き込み済みの (時刻, 地点コード) を読み込む（重複書き込み防止）。"""
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                seen.add((r["time"], r["code"]))
    return seen


def append_rows(path, rows, seen):
    new = [r for r in rows if (r[0], r[1]) not in seen]
    if not new:
        return 0
    first = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig" if first else "utf-8") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["time", "code", "name"] + [k + ("_degC" if k == "temp" else "_mm") for k in FIELDS])
        w.writerows(sorted(new))
    seen.update((r[0], r[1]) for r in new)
    return len(new)


def latest_time():
    """最新の観測時刻を取得する。"""
    t = fetch_text(f"{BOSAI}/data/latest_time.txt")
    return datetime.fromisoformat(t.strip()).replace(tzinfo=None)


def cmd_realtime(a):
    codes = resolve_codes(a)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "amedas_realtime.csv")
    seen = load_seen(path)
    fmt = lambda dt: dt.strftime("%Y-%m-%d %H:%M")

    if a.hours:  # 直近 N 時間の 10 分値をさかのぼって取得（3 時間ごとのファイル）
        now = latest_time()
        t0 = now - timedelta(hours=a.hours)
        block = t0.replace(hour=t0.hour // 3 * 3, minute=0, second=0)
        rows = []
        while block <= now:
            for c in codes:
                data = fetch_json(f"{BOSAI}/data/point/{c}/{block:%Y%m%d}_{block.hour:02d}.json") or {}
                for k, rec in data.items():
                    t = datetime.strptime(k, "%Y%m%d%H%M%S")
                    if t0 < t <= now:
                        rows.append(rt_row(fmt(t), c, rec))
                time.sleep(SLEEP)
            block += timedelta(hours=3)
        print(f"直近 {a.hours} 時間：{append_rows(path, rows, seen)} 行を追加 → {path}")

    while True:
        t = latest_time()
        data = fetch_json(f"{BOSAI}/data/map/{t:%Y%m%d%H%M%S}.json") or {}
        rows = [rt_row(fmt(t), c, data[c]) for c in codes if c in data]
        n = append_rows(path, rows, seen)
        print(f"{fmt(t)}  {n} 行を追加  " + "  ".join(f"{r[2]} {r[4] if r[4] != '' else '-'}mm/h" for r in rows))
        if not a.watch:
            break
        time.sleep(a.watch)


# ---------------------------------------------------------------- コマンドライン
class JpArgumentParser(argparse.ArgumentParser):
    """argparse のエラーメッセージ（英語）を日本語に置き換える。"""
    MSG = [
        ("the following arguments are required", "次の引数が必要です"),
        ("invalid choice", "選択肢にない値です"),
        ("choose from", "選択肢"),
        ("invalid int value", "整数ではありません"),
        ("unrecognized arguments", "不明な引数です"),
        ("expected one argument", "値を 1 つ指定してください"),
        ("argument ", "引数 "),
    ]

    def error(self, message):
        for en, ja in self.MSG:
            message = message.replace(en, ja)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: エラー: {message}\n（使用例は引数なしで実行すると表示されます）\n")


def jp_parser(parser):
    """argparse の既定の英語表示（見出し・-h の説明）を日本語にする。"""
    parser._positionals.title = "サブコマンド"
    parser._optionals.title = "オプション"
    parser.add_argument("-h", "--help", action="help", help="このヘルプを表示して終了")
    return parser


def main():
    # 引数なしで実行したときは、使用例を含む説明を表示する
    if len(sys.argv) == 1:
        print(__doc__)
        return

    ap = jp_parser(JpArgumentParser(
        description="気象庁 AMeDAS 降水量データ取得（過去データ＋リアルタイム）",
        epilog="使用例は引数なしで実行すると表示されます：uv run ./code/amedas_rain.py",
        add_help=False))
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{stations,history,realtime}")
    mk = lambda name, help_: jp_parser(sub.add_parser(name, help=help_, description=help_, add_help=False))

    s = mk("stations", "都道府県内の観測地点を一覧表示")
    s.add_argument("--pref", type=int, required=True, help="都府県番号（例：埼玉 43、千葉 45）")
    s.add_argument("--name", help="地点名で絞り込み（部分一致）")
    s.set_defaults(func=cmd_stations)

    h = mk("history", "過去の降水量をダウンロード")
    h.add_argument("--pref", type=int, required=True, help="都府県番号")
    h.add_argument("--station", action="append", required=True, help="地点名または block_no（複数指定可）")
    h.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    h.add_argument("--end", required=True, help="終了日 YYYY-MM-DD（この日を含む）")
    h.add_argument("--freq", choices=["hourly", "10min", "daily"], default="hourly", help="時間間隔（既定：hourly）")
    h.add_argument("--out", default="data/raw/amedas", help="出力フォルダー（既定：data/raw/amedas）")
    h.set_defaults(func=cmd_history)

    r = mk("realtime", "リアルタイムの降水量を取得")
    r.add_argument("--pref", type=int, help="都府県番号（--station と一緒に指定）")
    r.add_argument("--station", action="append", help="地点名（複数指定可、--pref が必要）")
    r.add_argument("--code", action="append", help="AMeDAS 地点コード（5 桁、複数指定可）")
    r.add_argument("--hours", type=int, default=0, help="直近 N 時間の 10 分値もさかのぼって取得")
    r.add_argument("--watch", type=int, default=0, help="N 秒ごとに取得し続ける（推奨 600）。Ctrl+C で停止")
    r.add_argument("--out", default="data/cache/amedas", help="出力フォルダー（既定：data/cache/amedas）")
    r.set_defaults(func=cmd_realtime)

    a = ap.parse_args()
    try:
        a.func(a)
    except KeyboardInterrupt:
        print("\n停止しました。")


if __name__ == "__main__":
    main()
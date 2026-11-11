"""
check_p1.py  -  課題 P1 の自動チェック（教員が用意。書き換えないこと）

使い方：uv run ./code/student/check_p1.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1_city_stats import ROOT, count_by_city, load_features  # noqa: E402

regions = json.loads((ROOT / "data/static/regions.json").read_text(encoding="utf-8"))
passed = total = 0


def report(name, ok, hint=""):
    global passed, total
    total += 1
    passed += ok
    print(("✅ " if ok else "❌ ") + name)
    if not ok and hint:
        print("    " + hint)


for pref in ["12", "13"]:
    feats = load_features(pref)
    try:
        stats = count_by_city(feats)
    except Exception as e:  # noqa: BLE001
        report(f"県コード {pref}：エラーなく実行できる", False, f"エラー：{e!r}")
        continue
    cities = [c for c in regions["cities"] if c["prefCode"] == pref]
    report(f"県コード {pref}：{len(cities)} 市区町村がそろっている", len(stats) == len(cities),
           f"返ってきたのは {len(stats)} 市区町村です")
    wrong = [c["fullName"] for c in cities if stats.get(c["code"], {}).get("shelters") != c["count"]]
    report(f"県コード {pref}：各市区町村の避難所の数が正しい", not wrong,
           f"数が合わない市区町村：{', '.join(wrong[:5])}{' …' if len(wrong) > 5 else ''}")
    flood = {}
    for f in feats:
        p = f["properties"]
        flood[p["cityCode"]] = flood.get(p["cityCode"], 0) + (1 if p["flood"] else 0)
    wrong = [code for code, n in flood.items() if stats.get(code, {}).get("flood") != n]
    report(f"県コード {pref}：洪水に対応する数が正しい", not wrong,
           f"数が合わない市区町村コード：{', '.join(wrong[:5])}")

print(f"\n{passed} / {total} 合格" + ("　🎉 完成！" if passed == total else ""))

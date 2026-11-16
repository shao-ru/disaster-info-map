"""
build_photos.py  -  避難所の写真をチェックし、写真の一覧（index.json）を作る

写真は data/static/photos/ に、写真と説明ファイルを 1 組で置きます（アプリの「写真を追加」で自動で作られます）。

    E1221700001111_taro_01.jpg     写真（長い辺 1600 px 以下、位置情報なし）
    E1221700001111_taro_01.json    説明 {"id": "E1221700001111", "taken": "2026-11-15", "by": "taro", "note": "正門から"}

    ファイル名：<施設の ID>_<GitHub ユーザー名>_<2 桁の番号>.jpg

index.json（写真の一覧）は Git に入れません。次のときに自動で作られます。
  - 手元：serve.py が、アプリから読まれるたびに作る
  - 公開：GitHub Actions が、公開するときに作る

使い方（プロジェクトのフォルダーで）：
  uv run ./code/build_photos.py            … チェックだけ
  uv run ./code/build_photos.py --index    … チェックして index.json を作る
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "data/static/photos"
SHELTERS = ROOT / "data/static/shelters"
NAME_RE = re.compile(r"^(E\d{12}[0-9A-Z])_([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))_(\d{2})\.jpg$")
USER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
MAX_BYTES = 1_000_000   # 1 枚 1 MB まで


def read_meta(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def scan(check=False, known_ids=None):
    """
    写真を調べて、(index, errors) を返す。
      index  : {施設の ID: [{"file", "taken", "by", "note"}, …]}
      check  : True なら細かくチェックする（サイズ・日付など）
    """
    index, errors = {}, []
    if not PHOTOS.exists():
        return index, errors
    files = {p.name for p in PHOTOS.iterdir() if p.is_file()}
    for name in sorted(files):
        if name in ("index.json", "README.md", ".gitkeep"):
            continue
        p = PHOTOS / name
        if name.endswith(".json"):
            if name[:-5] + ".jpg" not in files:
                errors.append(f"{name}：対になる写真（{name[:-5]}.jpg）がありません")
            continue
        m = NAME_RE.match(name)
        if not m:
            errors.append(f"{name}：ファイル名は「施設ID_GitHubユーザー名_2桁の番号.jpg」にしてください（例：E1221700001111_taro_01.jpg）")
            continue
        fid, user, _ = m.groups()
        meta_path = PHOTOS / (name[:-4] + ".json")
        if not meta_path.exists():
            errors.append(f"{name}：説明ファイル（{meta_path.name}）がありません")
            continue
        try:
            meta = read_meta(meta_path)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"{meta_path.name}：JSON として読めません（{e}）")
            continue
        if check:
            if meta.get("id") != fid:
                errors.append(f"{meta_path.name}：id がファイル名の ID（{fid}）と違います")
            if meta.get("by") != user:
                errors.append(f"{meta_path.name}：by がファイル名のユーザー名（{user}）と違います")
            try:
                date.fromisoformat(str(meta.get("taken", "")))
            except ValueError:
                errors.append(f"{meta_path.name}：taken（撮影日）は 2026-11-15 の形にしてください")
            if p.stat().st_size > MAX_BYTES:
                errors.append(f"{name}：{p.stat().st_size / 1e6:.1f} MB あります。1 MB 以下にしてください（アプリの「写真を追加」を使うと自動で小さくなります）")
            if p.read_bytes()[:2] != b"\xff\xd8":
                errors.append(f"{name}：JPEG ではありません")
            if known_ids is not None and fid not in known_ids:
                errors.append(f"{name}：ID「{fid}」の避難所がありません")
        index.setdefault(fid, []).append({
            "file": name, "taken": str(meta.get("taken", "")), "by": user, "note": str(meta.get("note", ""))[:200],
        })
    return index, errors


def shelter_ids():
    """避難所の ID の一覧（アプリで表示される ID）"""
    ids = set()
    for p in SHELTERS.glob("[0-9][0-9].geojson"):
        ids.update(f["properties"]["id"] for f in json.loads(p.read_text(encoding="utf-8"))["features"])
    return ids


def main():
    ap = argparse.ArgumentParser(description="避難所の写真をチェックし、index.json を作る")
    ap.add_argument("--index", action="store_true", help="index.json を作る")
    args = ap.parse_args()
    index, errors = scan(check=True, known_ids=shelter_ids())
    n = sum(len(v) for v in index.values())
    if errors:
        print(f"❌ エラー {len(errors)} 件")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    print(f"✅ 写真 {n} 枚（{len(index)} 施設）")
    if args.index:
        PHOTOS.mkdir(parents=True, exist_ok=True)
        (PHOTOS / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print("✅ data/static/photos/index.json を作りました")


if __name__ == "__main__":
    main()

"""
serve.py  -  開発用の Web サーバー

python -m http.server との違い：
  - 自分の PC からだけ開ける（127.0.0.1）。同じネットワークのほかの PC からは見えない
  - 公開するのはアプリに必要な web/ と data/static/ だけ。
    .git や doc(cn) など、ほかのフォルダーやファイルの一覧は見えない
  - http://localhost:8000/ を開くと、アプリ（/web/）に移動する
  - ブラウザーにファイルをキャッシュさせない（直したファイルがすぐ反映される）
  - 避難所の写真の登録（アプリの「写真を追加」）を受け付け、data/static/photos/ に保存する
  - 写真の一覧（data/static/photos/index.json）を、読まれるたびに作る

使い方（どのフォルダーからでも可）：
  uv run ./code/serve.py
  → http://localhost:8000/web/  を開く（課題チェックは http://localhost:8000/web/test.html）
"""
import base64
import http.server
import json
import re
import socket
import sys
import threading
import posixpath
from datetime import date
from urllib.parse import unquote
from functools import partial
from pathlib import Path

HOST = "127.0.0.1"   # 自分の PC だけ（IPv6 の ::1 でも待ち受ける）
PORT = 8000
ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ("/web/", "/data/static/")   # 公開するフォルダー
ALLOWED_FILES = ("/CONTRIBUTORS.md",)  # 公開するファイル（「参加者」ボタンで表示）
PHOTO_INDEX = "/data/static/photos/index.json"
MAX_UPLOAD = 4_000_000                 # 受け付ける大きさの上限（写真は送る前にブラウザーで小さくしてある）

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_photos  # noqa: E402


def json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def save_photo(data):
    """アプリから送られた写真を保存する。保存したファイル名を返す（おかしいときは ValueError）"""
    fid = str(data.get("id", ""))
    user = str(data.get("by", ""))
    taken = str(data.get("taken", ""))
    note = str(data.get("note", ""))[:200]
    if not re.fullmatch(r"E\d{12}[0-9A-Z]", fid):
        raise ValueError("施設の ID がおかしいです")
    if not build_photos.USER_RE.fullmatch(user):
        raise ValueError("GitHub のユーザー名は、英数字とハイフンで書いてください")
    try:
        date.fromisoformat(taken)
    except ValueError:
        raise ValueError("撮影日がおかしいです") from None
    image = base64.b64decode(str(data.get("image", "")), validate=True)
    if image[:2] != b"\xff\xd8" or len(image) > build_photos.MAX_BYTES:
        raise ValueError("写真は 1 MB 以下の JPEG にしてください")
    build_photos.PHOTOS.mkdir(parents=True, exist_ok=True)
    for n in range(1, 100):   # まだ使われていない番号を探す
        base = f"{fid}_{user}_{n:02d}"
        jpg = build_photos.PHOTOS / f"{base}.jpg"
        if not jpg.exists():
            jpg.write_bytes(image)
            meta = {"id": fid, "taken": taken, "by": user, "note": note}
            (build_photos.PHOTOS / f"{base}.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return jpg.name
    raise ValueError("この施設の写真が多すぎます")


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, status, obj):
        body = json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":                      # アプリが「手元のサーバーか」を確かめる
            return self.send_json(200, {"local": True})
        if path == PHOTO_INDEX:                      # 写真の一覧はその場で作る
            index, _ = build_photos.scan()
            return self.send_json(200, index)
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/photos":
            return self.send_error(404, "Not Found")
        # ほかのサイトから勝手に送られないように、このアプリからの送信だけを受け付ける
        origin = self.headers.get("Origin", "")
        if not re.fullmatch(r"http://(localhost|127\.0\.0\.1|\[::1\]):%d" % PORT, origin) \
                or not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.send_json(403, {"error": "このアプリからの送信ではありません"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_UPLOAD:
            return self.send_json(413, {"error": "大きすぎます"})
        try:
            name = save_photo(json.loads(self.rfile.read(length)))
        except (ValueError, json.JSONDecodeError) as e:
            return self.send_json(400, {"error": str(e)})
        print(f"写真を保存しました：data/static/photos/{name}", flush=True)
        return self.send_json(200, {"file": name})

    def send_head(self):
        raw = unquote(self.path.split("?", 1)[0].split("#", 1)[0])
        # 「/web/../.git」のような書き方で、許可していないフォルダーに入れないようにする
        path = posixpath.normpath(raw) + ("/" if raw.endswith("/") else "")
        if raw in ("/", "/web"):
            self.send_response(302)
            self.send_header("Location", "/web/")
            self.end_headers()
            return None
        if not (path.startswith(ALLOWED) or path in ALLOWED_FILES):
            self.send_error(404, "Not Found")
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404, "Not Found")   # フォルダーの中身の一覧は出さない
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    print("サーバーを起動しています…", flush=True)
    handler = partial(Handler, directory=str(ROOT))
    try:
        server = http.server.ThreadingHTTPServer((HOST, PORT), handler)
    except OSError as e:
        raise SystemExit(f"ポート {PORT} を使えません（{e}）。\n"
                         "前に起動したサーバーが動いたままかもしれません。そのウィンドウで Ctrl+C を押すか、PC を再起動してください。")
    # Mac の Safari などは localhost を IPv6（::1）で開こうとするので、::1 でも待ち受ける
    try:
        class V6Server(http.server.ThreadingHTTPServer):
            address_family = socket.AF_INET6
        v6 = V6Server(("::1", PORT), handler)
        threading.Thread(target=v6.serve_forever, daemon=True).start()
    except OSError:
        pass   # IPv6 が使えない PC では 127.0.0.1 だけで動かす
    print(f"公開しているフォルダー：{ROOT}", flush=True)
    print(f"http://localhost:{PORT}/web/  を開いてください（止めるときは Ctrl+C）", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("停止しました")

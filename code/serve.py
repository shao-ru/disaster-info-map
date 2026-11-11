"""
serve.py  -  開発用の Web サーバー

python -m http.server との違い：
  - 自分の PC からだけ開ける（127.0.0.1）。同じネットワークのほかの PC からは見えない
  - 公開するのはアプリに必要な web/ と data/static/ だけ。
    .git や doc(cn) など、ほかのフォルダーやファイルの一覧は見えない
  - http://localhost:8000/ を開くと、アプリ（/web/）に移動する
  - ブラウザーにファイルをキャッシュさせない（直したファイルがすぐ反映される）

使い方（どのフォルダーからでも可）：
  uv run ./code/serve.py
  → http://localhost:8000/web/  を開く（課題チェックは http://localhost:8000/web/test.html）
"""
import http.server
import posixpath
from urllib.parse import unquote
from functools import partial
from pathlib import Path

HOST = "127.0.0.1"   # 自分の PC だけ
PORT = 8000
ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ("/web/", "/data/static/")   # 公開するフォルダー


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        raw = unquote(self.path.split("?", 1)[0].split("#", 1)[0])
        # 「/web/../.git」のような書き方で、許可していないフォルダーに入れないようにする
        path = posixpath.normpath(raw) + ("/" if raw.endswith("/") else "")
        if raw in ("/", "/web"):
            self.send_response(302)
            self.send_header("Location", "/web/")
            self.end_headers()
            return None
        if not path.startswith(ALLOWED):
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
    try:
        server = http.server.ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(ROOT)))
    except OSError as e:
        raise SystemExit(f"ポート {PORT} を使えません（{e}）。\n"
                         "前に起動したサーバーが動いたままかもしれません。そのウィンドウで Ctrl+C を押すか、PC を再起動してください。")
    print(f"公開しているフォルダー：{ROOT}", flush=True)
    print(f"http://localhost:{PORT}/web/  を開いてください（止めるときは Ctrl+C）", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("停止しました")

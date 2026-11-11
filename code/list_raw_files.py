"""
data/raw/README.md の「ファイル一覧」を作り直すスクリプト

data/raw/ は大きいので Git に入れない。代わりに、何がどこにあるかを
README.md に書いて Git に入れる。raw にファイルを追加・削除したら実行する。

README.md の「<!-- FILE LIST -->」より上（説明・出典）は手で書き、
下（ファイル一覧）はこのスクリプトが自動で書き換える。

実行例：
  uv run ./code/list_raw_files.py
"""
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data/raw"
README = RAW / "README.md"
MARK = "<!-- FILE LIST -->"
MAX_FILES = 15   # 1 フォルダーで表示するファイル数の上限（多いときは省略）


def human(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def main():
    head = README.read_text(encoding="utf-8").split(MARK)[0] if README.exists() else "# data/raw\n\n"
    lines = [MARK, "", "## ファイル一覧（自動生成）", ""]
    for d in sorted(p for p in RAW.iterdir() if p.is_dir()):
        files = sorted(f for f in d.rglob("*") if f.is_file())
        size = sum(f.stat().st_size for f in files)
        lines += [f"### {d.name}/  （{len(files)} ファイル、{human(size)}）", "", "```"]
        for f in files[:MAX_FILES]:
            lines.append(f"{f.relative_to(d).as_posix()}  ({human(f.stat().st_size)})")
        if len(files) > MAX_FILES:
            lines.append(f"…ほか {len(files) - MAX_FILES} ファイル")
        lines += ["```", ""]
    README.write_text(head + "\n".join(lines), encoding="utf-8")
    print(f"書き出し：{README}")


if __name__ == "__main__":
    main()

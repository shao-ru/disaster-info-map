"""
shelter_attrs.py  -  避難所の「利用条件・受入れ・災害ごとの可否」を決める（build_shelters.py から使う）

■ 値（すべての項目で共通。文字列）
    "可"　　"条件付き"（例：洪水のときは 2 階以上）　　"不可"　　None（空）= 不明

■ 項目
    （かっこ内は attrs/*.csv の列名）
    access     利用条件（利用条件）　可=だれでも利用できる　条件付き=対象者のみ（条件は「利用条件の説明」）
                                     不可=直接は行けない（二次避難所など）
    elderly（高齢者）　disabled（障害者）　infant（乳幼児・妊産婦）　pet（ペット）
    welfare（福祉避難所）　可=福祉避難所である　不可=ちがう
    flood（洪水）　landslide（崖崩れ、土石流及び地滑り）　surge（高潮）　quake（地震）
    tsunami（津波）　fire（大規模な火事）　inland（内水氾濫）　volcano（火山現象）
    ※ 災害の列名と順番は、国土地理院の mergeFromCity_2.csv と同じ

■ 値の決め方（上ほど優先）
    ① 調査：data/static/shelters/attrs/<市区町村コード>.csv に書いた値（人が調べたもの）
    ② 自動：国土地理院のデータから推定
         - 指定緊急避難場所の「洪水」などの列：1 → 可、空 → 不可（その災害には指定されていない）
         ※ attrs に何も書かなければ、この推定（なければ不明）のまま
         - 「受入対象者」「備考」の文字から推定（下の RULES）
    ③ どれにもなければ 不明

自動の推定ルール（auto_attrs）は、だれでも改善できます。
改善したら build_shelters.py を実行し、件数の変化（最後に表示されます）を確かめてください。
"""

import csv
import re
from pathlib import Path

PEOPLE = ["elderly", "disabled", "infant", "welfare", "pet"]
# 災害の順番は、国土地理院の指定緊急避難場所データ（mergeFromCity_2.csv）の列と同じ
HAZARDS = ["flood", "landslide", "surge", "quake", "tsunami", "fire", "inland", "volcano"]
KEYS = ["access", *PEOPLE, *HAZARDS]
# attrs/*.csv の列名（日本語） ← プログラムの中の名前（GeoJSON・アプリでは英語の名前を使う）
COLUMN_NAMES = {
    "id": "id", "name": "name", "address": "住所",
    "access": "利用条件", "access_note": "利用条件の説明",
    "elderly": "高齢者", "disabled": "障害者", "infant": "乳幼児・妊産婦", "welfare": "福祉避難所", "pet": "ペット",
    # 災害の列名と順番は、国土地理院の mergeFromCity_2.csv と同じ
    "flood": "洪水", "landslide": "崖崩れ、土石流及び地滑り", "surge": "高潮", "quake": "地震",
    "tsunami": "津波", "fire": "大規模な火事", "inland": "内水氾濫", "volcano": "火山現象",
    "source": "根拠", "by": "調査者", "memo": "memo",
}
ATTR_COLUMNS = list(COLUMN_NAMES.values())
OK, COND, NG = "可", "条件付き", "不可"
# attrs/*.csv に書ける値（同じ意味の書き方もいくつか受け付ける）
VALUES = {"可": OK, "○": OK, "〇": OK,
          "条件付き": COND, "条件付": COND, "△": COND,
          "不可": NG, "×": NG}
RESET = "不明"   # 「不明」と書くと、自動の推定を消して不明にする（ふつうは空のままでよい）

# 文章の中で、災害を表すことば
HAZARD_WORDS = {
    "flood": ["洪水", "大雨"],
    "inland": ["内水", "大雨"],
    "landslide": ["土砂", "崖崩れ", "がけ崩れ", "土石流", "地滑り", "地すべり"],
    "quake": ["地震"],
    "fire": ["大規模な火事", "大規模火災", "火事", "火災"],
    "tsunami": ["津波"],
    "surge": ["高潮"],
    "volcano": ["火山"],
}
MARKS = {"〇": OK, "○": OK, "◯": OK, "△": COND, "×": NG, "✕": NG, "✖": NG, "Ｘ": NG}
NEAR = r"[^。\n、,，]{0,12}"   # ことばの近く（同じ文の 12 文字以内）

CARE = ["要配慮", "要援護", "要支援", "配慮を要する", "配慮が必要"]
PEOPLE_WORDS = {
    "elderly": ["高齢"],
    "disabled": ["障害", "障がい", "障碍"],
    "infant": ["乳幼児", "乳児", "幼児", "妊産婦", "妊婦"],
}


def auto_attrs(target, notes, designated):
    """
    国土地理院のデータから自動で推定する。
      target     : 受入対象者（文字列）
      notes      : 備考（文字列のリスト。指定避難所と指定緊急避難場所の両方）
      designated : 指定緊急避難場所の災害ごとの指定 {"flood": True, …}。指定緊急避難場所でなければ None
    戻り値 : ({項目: 値}, {項目: "gsi" または "auto"})　値が決まらない項目は入れない
    """
    values, src = {}, {}

    def put(key, value, how):
        values[key] = value
        src[key] = how

    # ① 指定緊急避難場所の指定（国土地理院）
    if designated is not None:
        for key in HAZARDS:
            put(key, OK if designated.get(key) else NG, "gsi")

    text = " ".join(notes)
    # ② 備考の記号：「洪水〇」「地震○」「土砂△」「津波×」
    for key, words in HAZARD_WORDS.items():
        for w in words:
            # 「土砂災害〇」「火山噴火×」「崖崩れ等〇」のように、間に 3 文字までは入ってよい
            for m in re.finditer(re.escape(w) + r"[^\s〇○◯△×✕✖Ｘ、。:：]{0,3}[:：]?[^\S\n]*([〇○◯△×✕✖Ｘ])", text):
                put(key, MARKS[m.group(1)], "auto")
    # ③ 「洪水時使用不可」「洪水の際は使用できない」→ 不可
    for key, words in HAZARD_WORDS.items():
        for w in words:
            if re.search(re.escape(w) + NEAR + r"(使用不可|利用不可|使用できな|利用できな|避難不可)", text):
                put(key, NG, "auto")
    # ④ 「『洪水』では2階以上に避難」「【洪水：2階以上】」→ 条件付き
    for key, words in HAZARD_WORDS.items():
        for w in words:
            if re.search(re.escape(w) + NEAR + r"[2-9２-９]\s*階以上", text) and values.get(key) != NG:
                put(key, COND, "auto")

    # ⑤ 受入対象者：書いてあれば「対象者のみ」の福祉避難所
    who = target.strip()
    if who:
        put("access", COND, "auto")
        put("welfare", OK, "auto")
        if any(w in who for w in CARE):
            for key in ("elderly", "disabled", "infant"):
                put(key, OK, "auto")
        for key, words in PEOPLE_WORDS.items():
            if any(w in who for w in words):
                put(key, OK, "auto")
    if "福祉避難所" in text:
        put("welfare", OK, "auto")
        if "access" not in values:
            put("access", COND, "auto")
    if re.search(r"二次避難所|直接" + NEAR + r"(避難|来所|来場)" + NEAR + r"(不可|できません|できない)", text):
        put("access", NG, "auto")

    # ⑥ ペット
    if re.search(r"ペット" + NEAR + r"(不可|できません|できない|禁止)", text):
        put("pet", NG, "auto")
    elif re.search(r"ペット" + NEAR + r"(可|受入|受け入れ|同行避難)", text):
        put("pet", OK, "auto")
    return values, src


# ------------------------------------------------------------------ 調査の結果（attrs/*.csv）
def read_attrs(attrs_dir, ids, errors, warnings=None):
    """
    attrs/<市区町村コード>.csv を読む。
      ids      : {共通ID: 施設の代表 ID}（施設のどちらの共通ID で書いてもよい）
      errors   : まちがい（あると止まる）を入れるリスト
      warnings : 注意（止まらない。例：根拠が空）を入れるリスト
    戻り値 : {代表 ID: {"values": {項目: 値 or None}, "access_note": …, "source": …, "by": …}}
    """
    result = {}
    for path in sorted(Path(attrs_dir).glob("*.csv")):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            errors.append(f"attrs/{path.name}：UTF-8 で読めません（Excel で保存した？ VS Code で保存し直してください）")
            continue
        rows = list(csv.DictReader(text.splitlines()))
        need = [COLUMN_NAMES[k] for k in ("id", *KEYS, "access_note", "source", "by")]
        if rows and (missing := [c for c in need if c not in rows[0]]):
            errors.append(f"attrs/{path.name}：列が足りません：{', '.join(missing)}")
            continue
        for i, row in enumerate(rows, start=2):
            # 日本語の列名 → プログラムの中の名前
            r = {key: row.get(col) for key, col in COLUMN_NAMES.items()}
            where = f"attrs/{path.name} {i} 行目"
            fid = (r.get("id") or "").strip()
            if not fid:
                continue
            if fid not in ids:
                errors.append(f"{where}：共通ID「{fid}」の施設がありません")
                continue
            if fid[1:6] != path.stem:
                errors.append(f"{where}：共通ID「{fid}」はこのファイル（{path.stem}）の市区町村ではありません")
            main = ids[fid]
            if main in result:
                errors.append(f"{where}：同じ施設（{main}）がすでに書かれています")
                continue
            values = {}
            for key in KEYS:
                v = (r.get(key) or "").strip()
                if v == "":
                    continue
                if v == RESET:
                    values[key] = None
                elif v in VALUES:
                    values[key] = VALUES[v]
                else:
                    errors.append(f"{where}：「{COLUMN_NAMES[key]}」は 可・条件付き・不可 のどれかか、空にしてください（今は「{v}」）")
            note = (r.get("access_note") or "").strip()
            source = (r.get("source") or "").strip()
            if (values or note) and not source:
                if warnings is not None:   # 根拠がなくても止めない（注意だけ出す）
                    warnings.append(f"{where}：「根拠」（調べたページの URL や資料名）が空です")
            if values or note:
                result[main] = {"values": values, "access_note": note, "source": source,
                                "by": (r.get("by") or "").strip()}
    return result


def merge(auto_values, auto_src, survey):
    """自動の推定に、調査の結果を上書きする。戻り値：(attrs, src)　値が不明の項目は入れない"""
    attrs, src = dict(auto_values), dict(auto_src)
    if survey:
        for key, v in survey["values"].items():
            if v is None:
                attrs.pop(key, None)
                src.pop(key, None)
            else:
                attrs[key] = v
                src[key] = "survey"
    return attrs, src

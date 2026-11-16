// 条件による絞り込み（課題 4-1・4-2）
//
// 画面の「条件」で選んだ内容に、避難所が合うかどうかを判断します。
// 合う（true）避難所は地図で緑、合わない（false）避難所は灰色になり、一覧には合うものだけが出ます。
//
// 避難所の「attrs」（項目ごとの値）
//   {
//     access: 1,     利用条件　1=だれでも利用可　2=対象者のみ　0=直接行けない（二次避難所など）
//     elderly: null, 高齢者　　disabled: 障害者　　infant: 乳幼児・妊産婦　　welfare: 福祉避難所　　pet: ペット
//     flood: 2,      洪水　　inland: 内水氾濫　　landslide: 土砂災害　　quake: 地震
//     fire: 1,       大規模な火事　　tsunami: 津波　　surge: 高潮　　volcano: 火山
//   }
//   値の意味（access 以外）：1 = 可　2 = 条件付き（例：2 階以上）　0 = 不可　null = 不明（まだ分からない）
//
// 画面で選んだ条件（conditions）
//   {
//     hazards: ["flood", "quake"],   選んだ災害（何も選ばなければ []）
//     people: ["elderly"],           選んだ受入れ（何も選ばなければ []）
//     restricted: false,             「対象者限定も含める」を選んだら true
//     conditional: true,             「条件付きも合うとみなす」にチェックがあれば true
//     unknown: true,                 「不明も合うとみなす」にチェックがあれば true
//   }

// =====================================================================
// 課題 4-1  1 つの値が「合う」かどうか                    難易度 ★★☆☆☆
// =====================================================================
//
// 引数
//   value   : 1・2・0・null のどれか
//   options : { conditional: true/false, unknown: true/false }（conditions をそのまま渡してよい）
// 戻り値
//   合うなら true、合わないなら false
//     1    → いつも true
//     0    → いつも false
//     2    → options.conditional が true なら true
//     null → options.unknown が true なら true
//
// ヒント：if 文で value ごとに分けて考える。null かどうかは value === null で調べる
// 確認方法：test.html の「課題 4-1」がすべて ✅ になれば完成です。
// =====================================================================

export function isOk(value, options) {
  // ---- 仮の実装：何でも「合う」にする（ここを書き換える） ----
  return true;
}

// =====================================================================
// 課題 4-2  避難所が条件に合うかどうか                    難易度 ★★★☆☆
// =====================================================================
//
// 引数
//   attrs      : 避難所の値（上の説明）
//   conditions : 画面で選んだ条件（上の説明）
// 戻り値
//   次の 1〜3 をすべて満たせば true、1 つでも満たさなければ false
//     1. 利用条件（attrs.access）
//          0 → 合わない
//          2 → conditions.restricted が true のときだけ合う
//          1・null → isOk(attrs.access, conditions) で判断する
//     2. conditions.hazards で選んだ災害が、すべて isOk
//     3. conditions.people で選んだ受入れが、すべて isOk
//
// ヒント
//   ・attrs[key] と書くと、key に入っている名前の項目を取り出せる（例：key が "flood" なら attrs.flood）
//   ・「配列の全部が条件を満たすか」は every が便利
//       [1, 2, 3].every((n) => n > 0)  → true
//   ・課題 4-1 の isOk を使う
// 確認方法：test.html の「課題 4-2」がすべて ✅ になれば完成です。
// =====================================================================

export function matchesConditions(attrs, conditions) {
  // ---- 仮の実装：どの避難所も「合う」にする（ここを書き換える） ----
  return true;
}
